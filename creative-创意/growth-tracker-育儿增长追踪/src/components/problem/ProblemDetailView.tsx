'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, Plus, Check, Edit2 } from 'lucide-react'
import type { ParentingQuestion, QuestionObservation, QuestionDiscussion, QuestionStage } from '@/lib/types'

interface ProblemDetailViewProps {
  question: ParentingQuestion
  onUpdate: (question: ParentingQuestion) => void
}

const stageLabels: Record<QuestionStage, { icon: string; label: string }> = {
  observing: { icon: '🔴', label: '观察期' },
  experimenting: { icon: '🟡', label: '实验期' },
  internalized: { icon: '🟢', label: '已内化' },
}

export function ProblemDetailView({ question, onUpdate }: ProblemDetailViewProps) {
  const [observations, setObservations] = useState<QuestionObservation[]>(question.observations || [])
  const [discussions, setDiscussions] = useState<QuestionDiscussion[]>(question.discussions || [])
  const [newObservation, setNewObservation] = useState('')
  const [discussionInput, setDiscussionInput] = useState('')
  const [currentConclusion, setCurrentConclusion] = useState(question.currentConclusion || '')
  const [isEditingConclusion, setIsEditingConclusion] = useState(false)
  const [sending, setSending] = useState(false)
  const [addingObservation, setAddingObservation] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 当问题变化时更新状态
  useEffect(() => {
    setObservations(question.observations || [])
    setDiscussions(question.discussions || [])
    setCurrentConclusion(question.currentConclusion || '')
  }, [question])

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [discussions])

  const handleAddObservation = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newObservation.trim() || addingObservation) return

    setAddingObservation(true)
    try {
      const res = await fetch(`/api/questions/${question.id}/observations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newObservation.trim() }),
      })

      const data = await res.json()
      if (data.success) {
        setObservations(prev => [data.observation, ...prev])
        setNewObservation('')
        // 更新父组件
        onUpdate({ ...question, observations: [data.observation, ...observations] })
      }
    } catch (error) {
      console.error('Failed to add observation:', error)
    } finally {
      setAddingObservation(false)
    }
  }

  const handleSendDiscussion = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!discussionInput.trim() || sending) return

    const userMessage = discussionInput.trim()
    setDiscussionInput('')
    setSending(true)

    // 乐观更新
    const tempUserMessage: QuestionDiscussion = {
      id: `temp-${Date.now()}`,
      questionId: question.id,
      role: 'user',
      content: userMessage,
      createdAt: new Date(),
    }
    setDiscussions(prev => [...prev, tempUserMessage])

    try {
      const res = await fetch(`/api/questions/${question.id}/discuss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      })

      const data = await res.json()

      if (data.success) {
        // 替换临时消息并添加回复
        setDiscussions(prev => [
          ...prev.filter(m => m.id !== tempUserMessage.id),
          data.userMessage,
          data.assistantMessage,
        ])

        // 如果 AI 建议了新结论
        if (data.suggestedConclusion) {
          setCurrentConclusion(data.suggestedConclusion)
        }
      } else {
        setDiscussions(prev => prev.filter(m => m.id !== tempUserMessage.id))
      }
    } catch {
      setDiscussions(prev => prev.filter(m => m.id !== tempUserMessage.id))
    } finally {
      setSending(false)
    }
  }

  const handleSaveConclusion = async () => {
    try {
      const res = await fetch(`/api/questions/${question.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          currentConclusion,
          conclusionSource: 'user',
        }),
      })

      const data = await res.json()
      if (data.success) {
        setIsEditingConclusion(false)
        onUpdate({ ...question, currentConclusion, conclusionSource: 'user' })
      }
    } catch (error) {
      console.error('Failed to save conclusion:', error)
    }
  }

  const formatDate = (date: Date | string) => {
    const d = new Date(date)
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  const stageInfo = stageLabels[question.stage]

  return (
    <div className="h-full flex">
      {/* 左侧：观察记录 */}
      <div className="w-[320px] border-r border-gray-200 flex flex-col bg-gray-50">
        {/* 新观察输入 */}
        <div className="p-4 border-b border-gray-200 bg-white">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">新观察</h3>
          <form onSubmit={handleAddObservation} className="space-y-2">
            <textarea
              value={newObservation}
              onChange={(e) => setNewObservation(e.target.value)}
              placeholder="记录新的观察..."
              rows={2}
              className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none resize-none"
              disabled={addingObservation}
            />
            <button
              type="submit"
              disabled={!newObservation.trim() || addingObservation}
              className="w-full py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {addingObservation ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  <span>添加观察</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* 观察时间线 */}
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            观察记录 ({observations.length})
          </h3>
          {observations.length === 0 ? (
            <p className="text-sm text-gray-500">暂无观察记录</p>
          ) : (
            <div className="space-y-3">
              {observations.map((obs) => (
                <div key={obs.id} className="bg-white rounded-lg p-3 border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">
                    {formatDate(obs.createdAt)}
                    {obs.source === 'entry' && (
                      <span className="ml-2 px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">
                        来自日志
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700">{obs.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 右侧：结论和讨论 */}
      <div className="flex-1 flex flex-col bg-white">
        {/* 问题标题和状态 */}
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <span>{stageInfo.icon}</span>
            <span className="text-xs text-gray-500">{stageInfo.label}</span>
          </div>
          <h2 className="text-base font-medium text-gray-900 mt-1">{question.question}</h2>
        </div>

        {/* 当前结论 */}
        <div className="px-4 py-3 border-b border-gray-200 bg-yellow-50">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">当前结论</h3>
            {!isEditingConclusion && (
              <button
                onClick={() => setIsEditingConclusion(true)}
                className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <Edit2 className="w-3 h-3" />
                <span>编辑</span>
              </button>
            )}
          </div>
          {isEditingConclusion ? (
            <div className="space-y-2">
              <textarea
                value={currentConclusion}
                onChange={(e) => setCurrentConclusion(e.target.value)}
                placeholder="输入你的结论..."
                rows={3}
                className="w-full px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none resize-none"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSaveConclusion}
                  className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-1"
                >
                  <Check className="w-3 h-3" />
                  <span>保存</span>
                </button>
                <button
                  onClick={() => {
                    setCurrentConclusion(question.currentConclusion || '')
                    setIsEditingConclusion(false)
                  }}
                  className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-700">
              {currentConclusion || '暂无结论，和专家讨论后 AI 会给出建议'}
            </p>
          )}
        </div>

        {/* 讨论区域 */}
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">讨论</h3>
          {discussions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-500">
              <p className="text-sm">还没有讨论</p>
              <p className="text-xs mt-1 text-gray-400">问问专家的看法</p>
            </div>
          ) : (
            <div className="space-y-3">
              {discussions.map(msg => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-3 py-2 ${
                      msg.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-3 py-2">
                    <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 讨论输入 */}
        <div className="border-t border-gray-200 p-3">
          <form onSubmit={handleSendDiscussion} className="flex gap-2">
            <input
              type="text"
              value={discussionInput}
              onChange={(e) => setDiscussionInput(e.target.value)}
              placeholder="问问专家..."
              className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={!discussionInput.trim() || sending}
              className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
