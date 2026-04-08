'use client'

import { useState } from 'react'
import { Send, Loader2, Calendar, User } from 'lucide-react'
import type { EntryWithAnalysis } from '@/lib/types'

interface EntryFormProps {
  onSuccess: (entry: EntryWithAnalysis) => void
}

export function EntryForm({ onSuccess }: EntryFormProps) {
  const [rawText, setRawText] = useState('')
  const [childAge, setChildAge] = useState('')
  const [entryDate, setEntryDate] = useState(
    new Date().toISOString().split('T')[0]
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!rawText.trim()) return

    setSubmitting(true)
    setError(null)

    try {
      const res = await fetch('/api/entry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rawText: rawText.trim(),
          childAge: childAge.trim() || undefined,
          entryDate,
        }),
      })

      const data = await res.json()

      if (data.success) {
        setRawText('')
        onSuccess(data.entry)
      } else {
        setError(data.error || '提交失败')
      }
    } catch (err) {
      setError('网络错误，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 日期和年龄输入 */}
      <div className="flex gap-4">
        <div className="flex items-center gap-2 text-sm">
          <Calendar className="w-4 h-4 text-gray-400" />
          <input
            type="date"
            value={entryDate}
            onChange={(e) => setEntryDate(e.target.value)}
            className="bg-transparent border-b border-gray-200 focus:border-primary-500 focus:outline-none py-1"
          />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <User className="w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={childAge}
            onChange={(e) => setChildAge(e.target.value)}
            placeholder="年龄（如：2岁3个月）"
            className="bg-transparent border-b border-gray-200 focus:border-primary-500 focus:outline-none py-1 w-36"
          />
        </div>
      </div>

      {/* 主文本输入 */}
      <div className="relative">
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="今天发生了什么？记录孩子的表现、你的观察、特别的时刻..."
          rows={4}
          className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none resize-none"
          disabled={submitting}
        />
        <button
          type="submit"
          disabled={!rawText.trim() || submitting}
          className="absolute right-3 bottom-3 p-2 rounded-full bg-primary-500 text-white hover:bg-primary-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
          {error}
        </div>
      )}

      {/* 处理中提示 */}
      {submitting && (
        <div className="text-sm text-gray-500 flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>AI 正在分析记录...</span>
        </div>
      )}
    </form>
  )
}
