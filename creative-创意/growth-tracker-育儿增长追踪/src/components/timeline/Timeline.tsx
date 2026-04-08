'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, AlertTriangle, Lightbulb, Eye, BookOpen } from 'lucide-react'
import type { EntryWithAnalysis } from '@/lib/types'

interface TimelineProps {
  entries: EntryWithAnalysis[]
}

export function Timeline({ entries }: TimelineProps) {
  if (entries.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>还没有记录</p>
        <p className="text-sm mt-1">开始记录孩子的成长吧</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {entries.map((entry) => (
        <EntryCard key={entry.id} entry={entry} />
      ))}
    </div>
  )
}

function EntryCard({ entry }: { entry: EntryWithAnalysis }) {
  const [expanded, setExpanded] = useState(false)

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('zh-CN', {
      month: 'long',
      day: 'numeric',
      weekday: 'short',
    })
  }

  return (
    <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-hidden animate-fade-in">
      {/* 头部 - 日期和摘要 */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium text-gray-900">
                {formatDate(entry.entryDate)}
              </span>
              {entry.childAge && (
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                  {entry.childAge}
                </span>
              )}
            </div>
            <p className="text-gray-700">
              {entry.factCard?.oneLine || entry.rawText.slice(0, 100)}
            </p>
          </div>
          <button className="text-gray-400 hover:text-gray-600 p-1">
            {expanded ? (
              <ChevronUp className="w-5 h-5" />
            ) : (
              <ChevronDown className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* 标签 */}
        {entry.factCard?.tags && entry.factCard.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {entry.factCard.tags.map((tag) => (
              <span key={tag} className={`tag ${getTagClass(tag)}`}>
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 展开内容 */}
      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-4 bg-gray-50/50">
          {/* 原始记录 */}
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
              原始记录
            </h4>
            <p className="text-sm text-gray-600 whitespace-pre-wrap">
              {entry.rawText}
            </p>
          </div>

          {/* 事件列表 */}
          {entry.factCard?.events && entry.factCard.events.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">
                识别的事件
              </h4>
              <div className="space-y-2">
                {entry.factCard.events.map((event, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 text-sm"
                  >
                    <span className={`tag ${getEventTypeClass(event.type)}`}>
                      {event.type}
                    </span>
                    <span className="text-gray-700">{event.description}</span>
                    {event.emotion && (
                      <span className={`text-xs ${getEmotionClass(event.emotion)}`}>
                        {event.emotion === 'positive' ? '😊' :
                         event.emotion === 'negative' ? '😢' :
                         event.emotion === 'mixed' ? '😐' : ''}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 专家分析 */}
          {entry.factCard?.expertAnalysis && (
            <div className="space-y-3">
              {/* 解读 */}
              <div>
                <h4 className="text-xs font-medium text-gray-500 uppercase mb-2 flex items-center gap-1">
                  <BookOpen className="w-3 h-3" />
                  专家解读
                </h4>
                <p className="text-sm text-gray-700">
                  {entry.factCard.expertAnalysis.interpretation}
                </p>
              </div>

              {/* 建议 */}
              {entry.factCard.expertAnalysis.suggestions.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 uppercase mb-2 flex items-center gap-1">
                    <Lightbulb className="w-3 h-3" />
                    建议
                  </h4>
                  <div className="space-y-2">
                    {entry.factCard.expertAnalysis.suggestions.map((sug, i) => (
                      <div
                        key={i}
                        className={`text-sm p-2 rounded ${getSuggestionClass(sug.category)}`}
                      >
                        <span className="font-medium">{getCategoryLabel(sug.category)}：</span>
                        {sug.content}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 风险提示 */}
              {entry.factCard.expertAnalysis.riskFlags.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-amber-600 uppercase mb-2 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    关注点
                  </h4>
                  <ul className="text-sm text-amber-700 space-y-1">
                    {entry.factCard.expertAnalysis.riskFlags.map((flag, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-amber-500">•</span>
                        {flag}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 模式识别 */}
              {entry.factCard.expertAnalysis.patterns && entry.factCard.expertAnalysis.patterns.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 uppercase mb-2 flex items-center gap-1">
                    <Eye className="w-3 h-3" />
                    识别的模式
                  </h4>
                  <div className="space-y-1">
                    {entry.factCard.expertAnalysis.patterns.map((pattern, i) => (
                      <div key={i} className="text-sm text-gray-600">
                        <span className="text-primary-600">●</span> {pattern.pattern}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// 样式辅助函数
function getTagClass(tag: string): string {
  if (tag.includes('睡') || tag.includes('眠')) return 'tag-sleep'
  if (tag.includes('情绪') || tag.includes('开心') || tag.includes('焦虑')) return 'tag-emotion'
  if (tag.includes('行为') || tag.includes('打') || tag.includes('咬')) return 'tag-behavior'
  if (tag.includes('社交') || tag.includes('同伴')) return 'tag-social'
  if (tag.includes('健康') || tag.includes('生病')) return 'tag-health'
  return 'tag-default'
}

function getEventTypeClass(type: string): string {
  const map: Record<string, string> = {
    sleep: 'tag-sleep',
    emotion: 'tag-emotion',
    behavior: 'tag-behavior',
    social: 'tag-social',
    health: 'tag-health',
    milestone: 'bg-purple-100 text-purple-700',
    cognitive: 'bg-blue-100 text-blue-700',
    language: 'bg-cyan-100 text-cyan-700',
    motor: 'bg-teal-100 text-teal-700',
    feeding: 'bg-orange-100 text-orange-700',
  }
  return map[type] || 'tag-default'
}

function getEmotionClass(emotion: string): string {
  const map: Record<string, string> = {
    positive: 'text-green-600',
    negative: 'text-red-600',
    neutral: 'text-gray-500',
    mixed: 'text-amber-600',
  }
  return map[emotion] || ''
}

function getSuggestionClass(category: string): string {
  const map: Record<string, string> = {
    action: 'bg-green-50 text-green-800',
    observation: 'bg-blue-50 text-blue-800',
    resource: 'bg-purple-50 text-purple-800',
    caution: 'bg-amber-50 text-amber-800',
  }
  return map[category] || 'bg-gray-50 text-gray-800'
}

function getCategoryLabel(category: string): string {
  const map: Record<string, string> = {
    action: '行动建议',
    observation: '观察建议',
    resource: '学习资源',
    caution: '注意事项',
  }
  return map[category] || category
}
