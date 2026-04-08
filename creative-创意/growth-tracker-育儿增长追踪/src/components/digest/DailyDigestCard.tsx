'use client'

import { useState } from 'react'
import { DailyDigest, EditableItem, OpenQuestion } from '@/lib/types'
import { EditableList } from './EditableList'

interface DailyDigestCardProps {
  digest: DailyDigest
  onUpdate: (digest: DailyDigest) => void
  onDelete?: () => void
  expanded?: boolean
}

export function DailyDigestCard({ digest, onUpdate, onDelete, expanded = false }: DailyDigestCardProps) {
  const [isExpanded, setIsExpanded] = useState(expanded)

  const formatDate = (date: Date) => {
    const d = new Date(date)
    return d.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'short'
    })
  }

  const handleUpdateField = (field: keyof DailyDigest, value: EditableItem[] | OpenQuestion[]) => {
    onUpdate({ ...digest, [field]: value })
  }

  // 计算今日要点数量
  const itemCount =
    digest.recordSummary.filter(i => !i.deleted).length +
    digest.aiAnalysis.filter(i => !i.deleted).length +
    digest.conclusions.filter(i => !i.deleted).length

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* 头部 - 点击展开/收起 */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">📅</span>
          <div>
            <h3 className="font-medium text-gray-800">{formatDate(digest.date)}</h3>
            <p className="text-xs text-gray-500">{itemCount} 条记录</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {digest.openQuestions.filter(q => !q.resolved).length > 0 && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">
              {digest.openQuestions.filter(q => !q.resolved).length} 个待解决
            </span>
          )}
          <span className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </div>

      {/* 展开内容 */}
      {isExpanded && (
        <div className="px-4 py-4 border-t border-gray-100">
          <EditableList
            title="记录摘要"
            icon="📝"
            items={digest.recordSummary}
            onUpdate={(items) => handleUpdateField('recordSummary', items)}
            placeholder="添加今日记录..."
          />

          <EditableList
            title="AI 分析"
            icon="🤖"
            items={digest.aiAnalysis}
            onUpdate={(items) => handleUpdateField('aiAnalysis', items)}
            placeholder="添加分析要点..."
          />

          <EditableList
            title="讨论要点"
            icon="💬"
            items={digest.discussionPoints}
            onUpdate={(items) => handleUpdateField('discussionPoints', items)}
            placeholder="添加讨论内容..."
          />

          <EditableList
            title="今日结论"
            icon="✅"
            items={digest.conclusions}
            onUpdate={(items) => handleUpdateField('conclusions', items)}
            placeholder="添加结论..."
          />

          {/* 开放问题 */}
          <div className="border-t border-gray-100 pt-4 mt-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">❓</span>
              <h4 className="font-medium text-gray-700">待解决问题</h4>
            </div>
            <OpenQuestionList
              questions={digest.openQuestions}
              onUpdate={(questions) => handleUpdateField('openQuestions', questions)}
            />
          </div>

          {/* 删除按钮 */}
          {onDelete && (
            <div className="mt-4 pt-4 border-t border-gray-100 flex justify-end">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (confirm('确定要删除这天的沉淀吗？')) {
                    onDelete()
                  }
                }}
                className="text-xs text-red-500 hover:text-red-700"
              >
                删除此沉淀
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// 开放问题列表组件
function OpenQuestionList({
  questions,
  onUpdate
}: {
  questions: OpenQuestion[]
  onUpdate: (questions: OpenQuestion[]) => void
}) {
  const [newQuestion, setNewQuestion] = useState('')

  const handleToggleResolved = (id: string) => {
    const updated = questions.map(q =>
      q.id === id ? { ...q, resolved: !q.resolved } : q
    )
    onUpdate(updated)
  }

  const handleDelete = (id: string) => {
    onUpdate(questions.filter(q => q.id !== id))
  }

  const handleAdd = () => {
    if (!newQuestion.trim()) return
    const newQ: OpenQuestion = {
      id: `q-${Date.now()}`,
      content: newQuestion.trim(),
      resolved: false
    }
    onUpdate([...questions, newQ])
    setNewQuestion('')
  }

  return (
    <div className="space-y-2">
      {questions.map(q => (
        <div key={q.id} className="group flex items-center gap-2">
          <input
            type="checkbox"
            checked={q.resolved}
            onChange={() => handleToggleResolved(q.id)}
            className="rounded"
          />
          <span className={`flex-1 text-sm ${q.resolved ? 'text-gray-400 line-through' : 'text-gray-600'}`}>
            {q.content}
          </span>
          <button
            onClick={() => handleDelete(q.id)}
            className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-red-500"
          >
            删除
          </button>
        </div>
      ))}

      <div className="flex gap-2">
        <input
          type="text"
          value={newQuestion}
          onChange={e => setNewQuestion(e.target.value)}
          placeholder="添加待解决问题..."
          className="flex-1 px-2 py-1 border border-dashed border-gray-300 rounded text-sm"
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
        />
        <button
          onClick={handleAdd}
          disabled={!newQuestion.trim()}
          className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
        >
          + 添加
        </button>
      </div>
    </div>
  )
}
