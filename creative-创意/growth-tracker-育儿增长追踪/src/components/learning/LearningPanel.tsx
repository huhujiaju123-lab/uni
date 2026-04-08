'use client'

import { useState } from 'react'
import { Learning, LearningStatus } from '@/lib/types'
import { LearningCard } from './LearningCard'

interface LearningPanelProps {
  learnings: Learning[]
  onUpdate: (id: string, learning: Learning) => void
  onDelete: (id: string) => void
  onStatusChange: (id: string, status: LearningStatus, invalidReason?: string) => void
  onCreate: (topic: string, insight: string) => void
}

export function LearningPanel({
  learnings,
  onUpdate,
  onDelete,
  onStatusChange,
  onCreate
}: LearningPanelProps) {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newTopic, setNewTopic] = useState('')
  const [newInsight, setNewInsight] = useState('')
  const [filter, setFilter] = useState<LearningStatus | 'all'>('all')

  // 按状态分组
  const validated = learnings.filter(l => l.status === 'validated')
  const hypothesis = learnings.filter(l => l.status === 'hypothesis')
  const invalidated = learnings.filter(l => l.status === 'invalidated')

  // 筛选
  const filteredLearnings = filter === 'all' ? learnings : learnings.filter(l => l.status === filter)

  const handleCreate = () => {
    if (!newTopic.trim() || !newInsight.trim()) return
    onCreate(newTopic.trim(), newInsight.trim())
    setNewTopic('')
    setNewInsight('')
    setShowCreateForm(false)
  }

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">认知库</h2>
          <span className="text-sm text-gray-500">({learnings.length})</span>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          + 新增认知
        </button>
      </div>

      {/* 统计 */}
      <div className="flex gap-4 mb-4 text-sm">
        <button
          onClick={() => setFilter('all')}
          className={`flex items-center gap-1 ${filter === 'all' ? 'text-blue-600 font-medium' : 'text-gray-500'}`}
        >
          全部 <span className="bg-gray-100 px-1.5 rounded">{learnings.length}</span>
        </button>
        <button
          onClick={() => setFilter('validated')}
          className={`flex items-center gap-1 ${filter === 'validated' ? 'text-green-600 font-medium' : 'text-gray-500'}`}
        >
          🟢 已验证 <span className="bg-green-50 px-1.5 rounded">{validated.length}</span>
        </button>
        <button
          onClick={() => setFilter('hypothesis')}
          className={`flex items-center gap-1 ${filter === 'hypothesis' ? 'text-yellow-600 font-medium' : 'text-gray-500'}`}
        >
          🟡 假设中 <span className="bg-yellow-50 px-1.5 rounded">{hypothesis.length}</span>
        </button>
        <button
          onClick={() => setFilter('invalidated')}
          className={`flex items-center gap-1 ${filter === 'invalidated' ? 'text-red-600 font-medium' : 'text-gray-500'}`}
        >
          🔴 已否定 <span className="bg-red-50 px-1.5 rounded">{invalidated.length}</span>
        </button>
      </div>

      {/* 认知列表 */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {filteredLearnings.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            {filter === 'all' ? '还没有任何认知，点击「新增认知」添加' : '没有符合条件的认知'}
          </div>
        ) : (
          filteredLearnings.map(learning => (
            <LearningCard
              key={learning.id}
              learning={learning}
              onUpdate={(updated) => onUpdate(learning.id, updated)}
              onDelete={() => onDelete(learning.id)}
              onStatusChange={(status, reason) => onStatusChange(learning.id, status, reason)}
            />
          ))
        )}
      </div>

      {/* 创建表单弹窗 */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 w-96">
            <h3 className="font-medium mb-4">新增认知</h3>

            <div className="mb-3">
              <label className="block text-sm text-gray-600 mb-1">主题标签</label>
              <input
                type="text"
                value={newTopic}
                onChange={e => setNewTopic(e.target.value)}
                placeholder="如：睡眠、情绪、饮食..."
                className="w-full px-3 py-2 border rounded"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm text-gray-600 mb-1">认知内容</label>
              <textarea
                value={newInsight}
                onChange={e => setNewInsight(e.target.value)}
                placeholder="描述你的认知或假设..."
                className="w-full px-3 py-2 border rounded"
                rows={4}
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                disabled={!newTopic.trim() || !newInsight.trim()}
                className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
