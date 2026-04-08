'use client'

import { useState, useRef } from 'react'
import { Send, Loader2, Calendar, Sparkles } from 'lucide-react'
import type { EntryWithAnalysis } from '@/lib/types'

interface JournalPanelProps {
  entries: EntryWithAnalysis[]
  selectedEntryId?: string | null
  onEntryCreated: (entry: EntryWithAnalysis) => void
  onEntryOptimistic?: (tempEntry: EntryWithAnalysis) => void
  onEntryConfirmed?: (tempId: string, confirmedEntry: EntryWithAnalysis) => void
  onEntryFailed?: (tempId: string) => void
  onEntryClick?: (entry: EntryWithAnalysis) => void
  onEntryDelete?: (entryId: string) => void
}

export function JournalPanel({
  entries,
  selectedEntryId,
  onEntryCreated,
  onEntryOptimistic,
  onEntryConfirmed,
  onEntryFailed,
  onEntryClick,
  onEntryDelete,
}: JournalPanelProps) {
  const [rawText, setRawText] = useState('')
  const [entryDate, setEntryDate] = useState(new Date().toISOString().split('T')[0])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aiProcessing, setAiProcessing] = useState<string | null>(null) // 正在处理的临时ID

  // 防止重复提交
  const isSubmittingRef = useRef(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!rawText.trim()) return

    // 防止重复提交
    if (isSubmittingRef.current || submitting) return
    isSubmittingRef.current = true
    setSubmitting(true)
    setError(null)

    const text = rawText.trim()
    const date = entryDate

    // 乐观更新：立即显示
    const tempId = `temp-${Date.now()}`
    const tempEntry: EntryWithAnalysis = {
      id: tempId,
      rawText: text,
      entryDate: new Date(date),
      childAge: null,
      createdAt: new Date(),
      factCard: null, // AI 还没处理
    }

    // 立即清空输入框，提升响应速度
    setRawText('')

    // 添加到列表
    if (onEntryOptimistic) {
      onEntryOptimistic(tempEntry)
    }

    setAiProcessing(tempId)

    try {
      const res = await fetch('/api/entry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rawText: text,
          entryDate: date,
        }),
      })

      const data = await res.json()

      if (data.success) {
        // 替换临时数据为真实数据
        if (onEntryConfirmed) {
          onEntryConfirmed(tempId, data.entry)
        } else {
          onEntryCreated(data.entry)
        }
      } else {
        setError(data.error || '提交失败')
        // 失败时移除临时数据
        if (onEntryFailed) {
          onEntryFailed(tempId)
        }
        // 恢复输入框内容
        setRawText(text)
      }
    } catch {
      setError('网络错误，请重试')
      if (onEntryFailed) {
        onEntryFailed(tempId)
      }
      setRawText(text)
    } finally {
      setSubmitting(false)
      setAiProcessing(null)
      isSubmittingRef.current = false
    }
  }

  // 格式化日期
  const formatDate = (date: Date | string) => {
    const d = new Date(date)
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  // 检查是否是临时条目
  const isTempEntry = (id: string) => id.startsWith('temp-')

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 输入区域 */}
      <div className="p-4 border-b border-gray-200 bg-white">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">记录今天</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Calendar className="w-3 h-3" />
            <input
              type="date"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              className="bg-transparent border-b border-gray-200 focus:border-blue-500 focus:outline-none py-1"
              disabled={submitting}
            />
          </div>
          <div className="relative">
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="记录孩子的表现..."
              rows={3}
              className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none resize-none"
              disabled={submitting}
            />
            <button
              type="submit"
              disabled={!rawText.trim() || submitting}
              className="absolute right-2 bottom-2 p-1.5 rounded-full bg-blue-500 text-white hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Send className="w-3 h-3" />
              )}
            </button>
          </div>
          {error && (
            <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
              {error}
            </div>
          )}
        </form>
      </div>

      {/* 历史记录列表 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">历史记录</h3>
          {entries.length === 0 ? (
            <p className="text-sm text-gray-500">暂无记录</p>
          ) : (
            <div className="space-y-2">
              {entries.map((entry) => {
                const isTemp = isTempEntry(entry.id)
                const isProcessing = aiProcessing === entry.id
                const isSelected = selectedEntryId === entry.id

                return (
                  <div
                    key={entry.id}
                    className={`relative group w-full text-left p-3 rounded-lg border transition-colors cursor-pointer ${
                      isTemp
                        ? 'bg-blue-50 border-blue-200'
                        : isSelected
                        ? 'bg-blue-50 border-blue-500 ring-1 ring-blue-500'
                        : 'bg-white border-gray-200 hover:border-blue-300'
                    }`}
                    onClick={() => !isTemp && onEntryClick?.(entry)}
                  >
                    {/* 删除按钮 */}
                    {!isTemp && onEntryDelete && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('确定要删除这条记录吗？')) {
                            onEntryDelete(entry.id)
                          }
                        }}
                        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}

                    <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                      <span>{formatDate(entry.entryDate)}</span>
                      {entry.childAge && <span>· {entry.childAge}</span>}
                      {isProcessing && (
                        <span className="flex items-center gap-1 text-blue-600">
                          <Sparkles className="w-3 h-3 animate-pulse" />
                          AI 分析中...
                        </span>
                      )}
                    </div>
                    {/* 显示原文，不做概括 */}
                    <p className="text-sm text-gray-900 line-clamp-3">
                      {entry.rawText}
                    </p>
                    {entry.factCard?.tags && entry.factCard.tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {entry.factCard.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
