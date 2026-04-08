'use client'

import { useState } from 'react'
import { Learning, LearningStatus, EvidenceItem } from '@/lib/types'

interface LearningCardProps {
  learning: Learning
  onUpdate: (learning: Learning) => void
  onDelete: () => void
  onStatusChange: (status: LearningStatus, invalidReason?: string) => void
}

export function LearningCard({ learning, onUpdate, onDelete, onStatusChange }: LearningCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editTopic, setEditTopic] = useState(learning.topic)
  const [editInsight, setEditInsight] = useState(learning.insight)
  const [showEvidence, setShowEvidence] = useState(false)
  const [invalidReason, setInvalidReason] = useState('')
  const [showInvalidModal, setShowInvalidModal] = useState(false)

  const statusConfig = {
    hypothesis: { label: '假设中', color: 'yellow', icon: '🟡' },
    validated: { label: '已验证', color: 'green', icon: '🟢' },
    invalidated: { label: '已否定', color: 'red', icon: '🔴' }
  }

  const config = statusConfig[learning.status]

  const handleSave = () => {
    onUpdate({
      ...learning,
      topic: editTopic,
      insight: editInsight
    })
    setIsEditing(false)
  }

  const handleConfidenceChange = (delta: number) => {
    const newConfidence = Math.max(0, Math.min(1, learning.confidence + delta))
    onUpdate({ ...learning, confidence: newConfidence })
  }

  const handleInvalidate = () => {
    onStatusChange('invalidated', invalidReason)
    setShowInvalidModal(false)
    setInvalidReason('')
  }

  const confidencePercent = Math.round(learning.confidence * 100)

  return (
    <div className={`bg-white rounded-lg border shadow-sm overflow-hidden ${
      learning.status === 'invalidated' ? 'opacity-60' : ''
    }`}>
      {/* 头部 */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>{config.icon}</span>
            {isEditing ? (
              <input
                type="text"
                value={editTopic}
                onChange={e => setEditTopic(e.target.value)}
                className="px-2 py-1 border rounded text-sm font-medium"
                placeholder="主题标签"
              />
            ) : (
              <span className="text-sm font-medium text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
                {learning.topic}
              </span>
            )}
          </div>
          <span className={`text-xs px-2 py-0.5 rounded bg-${config.color}-100 text-${config.color}-700`}>
            {config.label}
          </span>
        </div>
      </div>

      {/* 内容 */}
      <div className="px-4 py-3">
        {isEditing ? (
          <textarea
            value={editInsight}
            onChange={e => setEditInsight(e.target.value)}
            className="w-full px-2 py-1 border rounded text-sm"
            rows={3}
            placeholder="认知内容"
          />
        ) : (
          <p className={`text-gray-600 ${learning.status === 'invalidated' ? 'line-through' : ''}`}>
            {learning.insight}
          </p>
        )}

        {/* 否定原因 */}
        {learning.status === 'invalidated' && learning.invalidReason && (
          <p className="mt-2 text-sm text-red-500">
            否定原因：{learning.invalidReason}
          </p>
        )}

        {/* 信心度 */}
        {learning.status !== 'invalidated' && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>信心度</span>
              <span>{confidencePercent}%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full bg-${config.color}-500 transition-all`}
                  style={{ width: `${confidencePercent}%` }}
                />
              </div>
              <button
                onClick={() => handleConfidenceChange(-0.1)}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                -
              </button>
              <button
                onClick={() => handleConfidenceChange(0.1)}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                +
              </button>
            </div>
          </div>
        )}

        {/* 证据 */}
        {learning.evidence.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              {showEvidence ? '▼' : '▶'} 证据 ({learning.evidence.length})
            </button>
            {showEvidence && (
              <div className="mt-2 space-y-1 pl-4 border-l-2 border-gray-200">
                {(learning.evidence as EvidenceItem[]).map((e, i) => (
                  <div key={e.id || i} className="text-xs text-gray-500">
                    <span className="text-gray-400">{e.date}</span> - {e.content}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 flex justify-between">
        <div className="flex gap-2">
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                className="text-xs text-blue-500 hover:text-blue-700"
              >
                保存
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                取消
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              编辑
            </button>
          )}
        </div>

        <div className="flex gap-2">
          {/* 状态操作 */}
          {learning.status === 'hypothesis' && (
            <button
              onClick={() => onStatusChange('validated')}
              className="text-xs text-green-500 hover:text-green-700"
            >
              升级
            </button>
          )}
          {learning.status === 'validated' && (
            <button
              onClick={() => onStatusChange('hypothesis')}
              className="text-xs text-yellow-500 hover:text-yellow-700"
            >
              降级
            </button>
          )}
          {learning.status !== 'invalidated' && (
            <button
              onClick={() => setShowInvalidModal(true)}
              className="text-xs text-red-400 hover:text-red-600"
            >
              否定
            </button>
          )}
          {learning.status === 'invalidated' && (
            <button
              onClick={() => onStatusChange('hypothesis')}
              className="text-xs text-blue-500 hover:text-blue-700"
            >
              恢复
            </button>
          )}
          <button
            onClick={() => {
              if (confirm('确定要删除这条认知吗？')) {
                onDelete()
              }
            }}
            className="text-xs text-red-400 hover:text-red-600"
          >
            删除
          </button>
        </div>
      </div>

      {/* 否定原因弹窗 */}
      {showInvalidModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 w-80">
            <h3 className="font-medium mb-3">否定这条认知</h3>
            <textarea
              value={invalidReason}
              onChange={e => setInvalidReason(e.target.value)}
              placeholder="请说明否定的原因（可选）"
              className="w-full px-2 py-1 border rounded text-sm mb-3"
              rows={3}
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowInvalidModal(false)}
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={handleInvalidate}
                className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
              >
                确认否定
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
