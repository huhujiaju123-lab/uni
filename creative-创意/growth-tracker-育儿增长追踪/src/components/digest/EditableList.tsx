'use client'

import { useState } from 'react'
import { EditableItem } from '@/lib/types'

interface EditableListProps {
  title: string
  icon: string
  items: EditableItem[]
  onUpdate: (items: EditableItem[]) => void
  placeholder?: string
}

export function EditableList({ title, icon, items, onUpdate, placeholder }: EditableListProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [newContent, setNewContent] = useState('')

  // 过滤掉已删除的项
  const visibleItems = items.filter(item => !item.deleted)

  const handleEdit = (item: EditableItem) => {
    setEditingId(item.id)
    setEditContent(item.content)
  }

  const handleSaveEdit = (id: string) => {
    const updatedItems = items.map(item =>
      item.id === id ? { ...item, content: editContent, source: 'user' as const } : item
    )
    onUpdate(updatedItems)
    setEditingId(null)
    setEditContent('')
  }

  const handleDelete = (id: string) => {
    const updatedItems = items.map(item =>
      item.id === id ? { ...item, deleted: true } : item
    )
    onUpdate(updatedItems)
  }

  const handleAdd = () => {
    if (!newContent.trim()) return
    const newItem: EditableItem = {
      id: `user-${Date.now()}`,
      content: newContent.trim(),
      source: 'user',
      deleted: false
    }
    onUpdate([...items, newItem])
    setNewContent('')
  }

  return (
    <div className="border-b border-gray-100 pb-4 mb-4 last:border-b-0 last:mb-0 last:pb-0">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <h4 className="font-medium text-gray-700">{title}</h4>
      </div>

      <div className="space-y-2">
        {visibleItems.map(item => (
          <div key={item.id} className="group flex items-start gap-2">
            {editingId === item.id ? (
              <div className="flex-1 flex gap-2">
                <input
                  type="text"
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  className="flex-1 px-2 py-1 border rounded text-sm"
                  autoFocus
                />
                <button
                  onClick={() => handleSaveEdit(item.id)}
                  className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  保存
                </button>
                <button
                  onClick={() => setEditingId(null)}
                  className="px-2 py-1 text-xs bg-gray-200 text-gray-600 rounded hover:bg-gray-300"
                >
                  取消
                </button>
              </div>
            ) : (
              <>
                <span className="text-gray-400 mt-1">·</span>
                <span className="flex-1 text-gray-600 text-sm">{item.content}</span>
                {item.source === 'ai' && (
                  <span className="text-xs text-blue-400 bg-blue-50 px-1.5 py-0.5 rounded">AI</span>
                )}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                  <button
                    onClick={() => handleEdit(item)}
                    className="text-xs text-gray-400 hover:text-blue-500"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="text-xs text-gray-400 hover:text-red-500"
                  >
                    删除
                  </button>
                </div>
              </>
            )}
          </div>
        ))}

        {/* 添加新项 */}
        <div className="flex gap-2 mt-2">
          <input
            type="text"
            value={newContent}
            onChange={e => setNewContent(e.target.value)}
            placeholder={placeholder || '添加新内容...'}
            className="flex-1 px-2 py-1 border border-dashed border-gray-300 rounded text-sm placeholder:text-gray-400"
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
          />
          <button
            onClick={handleAdd}
            disabled={!newContent.trim()}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            + 添加
          </button>
        </div>
      </div>
    </div>
  )
}
