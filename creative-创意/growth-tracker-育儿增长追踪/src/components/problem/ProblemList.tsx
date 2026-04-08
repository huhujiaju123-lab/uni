'use client'

import { useState } from 'react'
import { ProblemCard } from './ProblemCard'
import type { ParentingQuestion } from '@/lib/types'

interface ProblemListProps {
  questions: ParentingQuestion[]
  selectedId: string | null
  onSelect: (id: string | null) => void
  onAddNew: () => void
}

type FilterTab = 'active' | 'internalized'

export function ProblemList({ questions, selectedId, onSelect, onAddNew }: ProblemListProps) {
  const [filter, setFilter] = useState<FilterTab>('active')
  const [isExpanded, setIsExpanded] = useState(false)

  // 根据筛选条件过滤问题
  const filteredQuestions = questions.filter((q) => {
    if (filter === 'active') {
      return q.stage === 'observing' || q.stage === 'experimenting'
    }
    return q.stage === 'internalized'
  })

  // 按显示顺序排序
  const sortedQuestions = [...filteredQuestions].sort((a, b) => a.displayOrder - b.displayOrder)

  // 只显示前 5 个，除非展开
  const displayedQuestions = isExpanded ? sortedQuestions : sortedQuestions.slice(0, 5)
  const hasMore = sortedQuestions.length > 5

  return (
    <div className="bg-white border-b border-gray-200">
      {/* 标题和筛选 */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-sm font-semibold text-gray-900">问题清单</h2>
          <div className="flex gap-1">
            <button
              onClick={() => setFilter('active')}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                filter === 'active'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              攻克中
            </button>
            <button
              onClick={() => setFilter('internalized')}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                filter === 'internalized'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              已内化
            </button>
          </div>
        </div>
        <button
          onClick={onAddNew}
          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
        >
          <span>+</span>
          <span>新问题</span>
        </button>
      </div>

      {/* 问题卡片网格 */}
      <div className="px-4 pb-3">
        {sortedQuestions.length === 0 ? (
          <div className="text-center py-6 text-gray-500 text-sm">
            {filter === 'active' ? '暂无正在攻克的问题' : '暂无已内化的问题'}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-5 gap-3">
              {displayedQuestions.map((question) => (
                <ProblemCard
                  key={question.id}
                  question={question}
                  isSelected={selectedId === question.id}
                  onClick={() => onSelect(selectedId === question.id ? null : question.id)}
                />
              ))}
            </div>

            {/* 展开/收起按钮 */}
            {hasMore && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="mt-3 w-full py-2 text-sm text-gray-500 hover:text-gray-700 flex items-center justify-center gap-1"
              >
                {isExpanded ? (
                  <>
                    <span>收起</span>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                    </svg>
                  </>
                ) : (
                  <>
                    <span>展开更多 ({sortedQuestions.length - 5})</span>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </>
                )}
              </button>
            )}
          </>
        )}
      </div>

      {/* 当前选中的问题提示 */}
      {selectedId && (
        <div className="px-4 py-2 bg-blue-50 border-t border-blue-100 flex items-center justify-between">
          <span className="text-sm text-blue-700">
            当前选中: {questions.find((q) => q.id === selectedId)?.question}
          </span>
          <button
            onClick={() => onSelect(null)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            返回日志
          </button>
        </div>
      )}
    </div>
  )
}
