'use client'

import { useState, useEffect, useRef } from 'react'
import { Loader2 } from 'lucide-react'
import { ProblemList } from '@/components/problem/ProblemList'
import { ProblemDetailView } from '@/components/problem/ProblemDetailView'
import { JournalPanel } from '@/components/journal/JournalPanel'
import { ExpertPanel } from '@/components/expert/ExpertPanel'
import { DailyDigestCard } from '@/components/digest'
import { LearningPanel } from '@/components/learning'
import { RecursiveSpiralIcon } from '@/components/icons/RecursiveIcon'
import type { EntryWithAnalysis, ParentingQuestion, DailyDigest, Learning, LearningStatus } from '@/lib/types'

type ViewMode = 'journal' | 'digest'

export default function Home() {
  // 视图模式
  const [viewMode, setViewMode] = useState<ViewMode>('journal')

  // 问题清单
  const [questions, setQuestions] = useState<ParentingQuestion[]>([])
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null)

  // 日志
  const [entries, setEntries] = useState<EntryWithAnalysis[]>([])
  const [loadingEntries, setLoadingEntries] = useState(true)
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null)

  // 对话
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loadingConversation, setLoadingConversation] = useState(false)

  // 当前对话关联的日志（用于 ExpertPanel 显示上下文）
  const [currentEntryContext, setCurrentEntryContext] = useState<EntryWithAnalysis | null>(null)

  // 每日沉淀
  const [digests, setDigests] = useState<DailyDigest[]>([])
  const [loadingDigests, setLoadingDigests] = useState(false)

  // 认知库
  const [learnings, setLearnings] = useState<Learning[]>([])
  const [loadingLearnings, setLoadingLearnings] = useState(false)

  // 新问题弹窗
  const [showNewQuestion, setShowNewQuestion] = useState(false)
  const [newQuestionText, setNewQuestionText] = useState('')
  const [creatingQuestion, setCreatingQuestion] = useState(false)

  // 防止重复提交
  const isCreatingRef = useRef(false)

  // 加载数据
  useEffect(() => {
    loadEntries()
    loadQuestions()
    loadDigests()
    loadLearnings()
  }, [])

  const loadEntries = async () => {
    try {
      setLoadingEntries(true)
      const res = await fetch('/api/entry?limit=50')
      const data = await res.json()
      if (data.success) {
        setEntries(data.entries)
      }
    } catch (error) {
      console.error('Failed to load entries:', error)
    } finally {
      setLoadingEntries(false)
    }
  }

  const loadQuestions = async () => {
    try {
      const res = await fetch('/api/questions')
      const data = await res.json()
      if (data.success) {
        setQuestions(data.questions)
      }
    } catch (error) {
      console.error('Failed to load questions:', error)
    }
  }

  const loadDigests = async () => {
    try {
      setLoadingDigests(true)
      const res = await fetch('/api/digest?limit=30')
      const data = await res.json()
      setDigests(data)
    } catch (error) {
      console.error('Failed to load digests:', error)
    } finally {
      setLoadingDigests(false)
    }
  }

  const loadLearnings = async () => {
    try {
      setLoadingLearnings(true)
      const res = await fetch('/api/learning')
      const data = await res.json()
      setLearnings(data)
    } catch (error) {
      console.error('Failed to load learnings:', error)
    } finally {
      setLoadingLearnings(false)
    }
  }

  // 每日沉淀 CRUD
  const handleUpdateDigest = async (digest: DailyDigest) => {
    try {
      const dateStr = new Date(digest.date).toISOString().split('T')[0]
      await fetch(`/api/digest/${dateStr}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(digest)
      })
      setDigests(prev => prev.map(d => d.id === digest.id ? digest : d))
    } catch (error) {
      console.error('Failed to update digest:', error)
    }
  }

  const handleDeleteDigest = async (id: string, date: Date) => {
    try {
      const dateStr = new Date(date).toISOString().split('T')[0]
      await fetch(`/api/digest/${dateStr}`, { method: 'DELETE' })
      setDigests(prev => prev.filter(d => d.id !== id))
    } catch (error) {
      console.error('Failed to delete digest:', error)
    }
  }

  // 认知库 CRUD
  const handleUpdateLearning = async (id: string, learning: Learning) => {
    try {
      await fetch(`/api/learning/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(learning)
      })
      setLearnings(prev => prev.map(l => l.id === id ? learning : l))
    } catch (error) {
      console.error('Failed to update learning:', error)
    }
  }

  const handleDeleteLearning = async (id: string) => {
    try {
      await fetch(`/api/learning/${id}`, { method: 'DELETE' })
      setLearnings(prev => prev.filter(l => l.id !== id))
    } catch (error) {
      console.error('Failed to delete learning:', error)
    }
  }

  const handleLearningStatusChange = async (id: string, status: LearningStatus, invalidReason?: string) => {
    try {
      const action = status === 'validated' ? 'upgrade'
                   : status === 'invalidated' ? 'invalidate'
                   : status === 'hypothesis' ? 'restore' : null

      await fetch(`/api/learning/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, invalidReason })
      })

      setLearnings(prev => prev.map(l =>
        l.id === id ? { ...l, status, invalidReason: invalidReason || null } : l
      ))
    } catch (error) {
      console.error('Failed to change learning status:', error)
    }
  }

  const handleCreateLearning = async (topic: string, insight: string) => {
    try {
      const res = await fetch('/api/learning', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, insight, source: 'user' })
      })
      const newLearning = await res.json()
      setLearnings(prev => [newLearning, ...prev])
    } catch (error) {
      console.error('Failed to create learning:', error)
    }
  }

  const handleEntryCreated = (newEntry: EntryWithAnalysis) => {
    setEntries(prev => [newEntry, ...prev])
  }

  // 优化：乐观更新 + 防重复
  const handleEntryOptimistic = (tempEntry: EntryWithAnalysis) => {
    setEntries(prev => [tempEntry, ...prev])
  }

  const handleEntryConfirmed = (tempId: string, confirmedEntry: EntryWithAnalysis) => {
    setEntries(prev =>
      prev.map(e => (e.id === tempId ? confirmedEntry : e))
    )
    // 自动选中新记录，加载对话
    handleEntryClick(confirmedEntry)
  }

  const handleEntryFailed = (tempId: string) => {
    setEntries(prev => prev.filter(e => e.id !== tempId))
  }

  // 点击日志，加载对应的对话
  const handleEntryClick = async (entry: EntryWithAnalysis) => {
    if (entry.id.startsWith('temp-')) return // 临时记录不处理

    setSelectedEntryId(entry.id)
    setCurrentEntryContext(entry)
    setLoadingConversation(true)

    try {
      const res = await fetch(`/api/entry/${entry.id}/conversation`)
      const data = await res.json()

      if (data.success) {
        setConversationId(data.conversation.id)
      }
    } catch (error) {
      console.error('加载对话失败:', error)
    } finally {
      setLoadingConversation(false)
    }
  }

  // 删除日志
  const handleEntryDelete = async (entryId: string) => {
    try {
      const res = await fetch(`/api/entry/${entryId}`, {
        method: 'DELETE'
      })

      if (res.ok) {
        // 从列表中移除
        setEntries(prev => prev.filter(e => e.id !== entryId))
        // 如果删除的是当前选中的，清空选中状态
        if (selectedEntryId === entryId) {
          setSelectedEntryId(null)
          setConversationId(null)
          setCurrentEntryContext(null)
        }
      }
    } catch (error) {
      console.error('删除日志失败:', error)
    }
  }

  const handleAddNewQuestion = async () => {
    if (!newQuestionText.trim()) return

    // 防止重复提交
    if (isCreatingRef.current || creatingQuestion) return
    isCreatingRef.current = true
    setCreatingQuestion(true)

    const questionText = newQuestionText.trim()

    // 乐观更新：立即显示
    const tempId = `temp-${Date.now()}`
    const tempQuestion: ParentingQuestion = {
      id: tempId,
      question: questionText,
      stage: 'observing',
      currentConclusion: null,
      conclusionSource: null,
      displayOrder: 0,
      relatedEntryIds: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      observations: [],
      discussions: [],
    }
    setQuestions(prev => [tempQuestion, ...prev])
    setNewQuestionText('')
    setShowNewQuestion(false)

    try {
      const res = await fetch('/api/questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: questionText }),
      })

      const data = await res.json()
      if (data.success) {
        // 替换临时数据为真实数据
        setQuestions(prev =>
          prev.map(q => (q.id === tempId ? data.question : q))
        )
      } else {
        // 失败时移除
        setQuestions(prev => prev.filter(q => q.id !== tempId))
      }
    } catch (error) {
      console.error('Failed to create question:', error)
      setQuestions(prev => prev.filter(q => q.id !== tempId))
    } finally {
      setCreatingQuestion(false)
      isCreatingRef.current = false
    }
  }

  const handleQuestionUpdate = (updatedQuestion: ParentingQuestion) => {
    setQuestions(prev =>
      prev.map(q => (q.id === updatedQuestion.id ? updatedQuestion : q))
    )
  }

  // 获取选中的问题详情
  const selectedQuestion = questions.find(q => q.id === selectedQuestionId)

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* 顶部：问题清单区 (约 20%) */}
      <div className="flex-shrink-0">
        <ProblemList
          questions={questions}
          selectedId={selectedQuestionId}
          onSelect={setSelectedQuestionId}
          onAddNew={() => setShowNewQuestion(true)}
        />
      </div>

      {/* 底部：主内容区 (约 80%) */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 视图切换标签 */}
        {!selectedQuestion && (
          <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4">
            <div className="flex gap-4">
              <button
                onClick={() => setViewMode('journal')}
                className={`py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
                  viewMode === 'journal'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                📝 日志模式
              </button>
              <button
                onClick={() => setViewMode('digest')}
                className={`py-3 px-1 border-b-2 text-sm font-medium transition-colors ${
                  viewMode === 'digest'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <RecursiveSpiralIcon size={16} className="inline-block mr-1" /> 沉淀模式
              </button>
            </div>
          </div>
        )}

        <div className="flex-1 flex overflow-hidden">
          {selectedQuestion ? (
            // 问题详情视图
            <ProblemDetailView
              question={selectedQuestion}
              onUpdate={handleQuestionUpdate}
            />
          ) : viewMode === 'journal' ? (
            // 日志模式：日志 + 专家讨论
            <>
              {/* 左侧：日志记录 */}
              <div className="w-[320px] border-r border-gray-200">
                <JournalPanel
                  entries={entries}
                  selectedEntryId={selectedEntryId}
                  onEntryCreated={handleEntryCreated}
                  onEntryOptimistic={handleEntryOptimistic}
                  onEntryConfirmed={handleEntryConfirmed}
                  onEntryFailed={handleEntryFailed}
                  onEntryClick={handleEntryClick}
                  onEntryDelete={handleEntryDelete}
                />
              </div>

              {/* 右侧：专家讨论 */}
              <div className="flex-1">
                {loadingConversation ? (
                  <div className="h-full flex items-center justify-center">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                  </div>
                ) : (
                  <ExpertPanel
                    conversationId={conversationId}
                    onConversationCreated={setConversationId}
                    latestEntry={currentEntryContext ? {
                      id: currentEntryContext.id,
                      rawText: currentEntryContext.rawText,
                      factCard: currentEntryContext.factCard ? {
                        oneLine: currentEntryContext.factCard.oneLine,
                        tags: currentEntryContext.factCard.tags
                      } : null,
                      expertAnalysis: currentEntryContext.factCard?.expertAnalysis ? {
                        interpretation: currentEntryContext.factCard.expertAnalysis.interpretation,
                        suggestions: currentEntryContext.factCard.expertAnalysis.suggestions as Array<{ category: string; content: string; priority: string }>
                      } : null
                    } : null}
                  />
                )}
              </div>
            </>
          ) : (
            // 沉淀模式：每日沉淀 + 认知库
            <>
              {/* 左侧：每日沉淀列表 */}
              <div className="w-[400px] border-r border-gray-200 bg-white overflow-y-auto">
                <div className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">每日沉淀</h2>
                    <span className="text-sm text-gray-500">{digests.length} 条</span>
                  </div>

                  {loadingDigests ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                  ) : digests.length === 0 ? (
                    <div className="text-center text-gray-400 py-8">
                      <p>还没有沉淀记录</p>
                      <p className="text-sm mt-1">日志记录后会自动生成</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {digests.map(digest => (
                        <DailyDigestCard
                          key={digest.id}
                          digest={digest}
                          onUpdate={handleUpdateDigest}
                          onDelete={() => handleDeleteDigest(digest.id, digest.date)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 右侧：认知库 */}
              <div className="flex-1 bg-gray-50 overflow-hidden">
                <div className="h-full p-4">
                  {loadingLearnings ? (
                    <div className="flex items-center justify-center h-full">
                      <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                    </div>
                  ) : (
                    <LearningPanel
                      learnings={learnings}
                      onUpdate={handleUpdateLearning}
                      onDelete={handleDeleteLearning}
                      onStatusChange={handleLearningStatusChange}
                      onCreate={handleCreateLearning}
                    />
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 新问题弹窗 */}
      {showNewQuestion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">添加新问题</h3>
            <textarea
              value={newQuestionText}
              onChange={(e) => setNewQuestionText(e.target.value)}
              placeholder="描述你的育儿问题..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none resize-none"
              autoFocus
              disabled={creatingQuestion}
            />
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => {
                  setShowNewQuestion(false)
                  setNewQuestionText('')
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                disabled={creatingQuestion}
              >
                取消
              </button>
              <button
                onClick={handleAddNewQuestion}
                disabled={!newQuestionText.trim() || creatingQuestion}
                className="px-4 py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {creatingQuestion && <Loader2 className="w-4 h-4 animate-spin" />}
                {creatingQuestion ? '添加中...' : '添加'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
