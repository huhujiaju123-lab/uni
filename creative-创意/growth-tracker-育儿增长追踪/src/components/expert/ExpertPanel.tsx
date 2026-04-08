'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, MessageCircle } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface ExpertPanelProps {
  conversationId: string | null
  onConversationCreated?: (id: string) => void
  latestEntry?: {
    id: string
    rawText: string
    factCard?: {
      oneLine: string
      tags: string[]
    } | null
    expertAnalysis?: {
      interpretation: string
      suggestions: Array<{ category: string; content: string; priority: string }>
    } | null
  } | null
}

export function ExpertPanel({ conversationId, onConversationCreated, latestEntry }: ExpertPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const lastProcessedEntryRef = useRef<string | null>(null)

  // 加载对话历史
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId)
    } else {
      setMessages([])
    }
  }, [conversationId])

  // 当有新记录时，自动显示 AI 分析
  useEffect(() => {
    if (!latestEntry) return
    if (latestEntry.id === lastProcessedEntryRef.current) return

    // 检查是否有分析结果
    const factCard = latestEntry.factCard
    const analysis = latestEntry.expertAnalysis

    if (!factCard?.oneLine && !analysis?.interpretation) return

    lastProcessedEntryRef.current = latestEntry.id
    console.log('🔔 自动显示 AI 分析:', latestEntry.id)

    // 构建 AI 回复内容
    let aiResponse = ''

    if (factCard?.oneLine) {
      aiResponse += `📝 记录摘要\n${factCard.oneLine}\n\n`
    }

    if (analysis?.interpretation) {
      aiResponse += `🔍 专家解读\n${analysis.interpretation}\n\n`
    }

    if (analysis?.suggestions && analysis.suggestions.length > 0) {
      aiResponse += `💡 建议\n`
      analysis.suggestions.forEach((s, i) => {
        aiResponse += `${i + 1}. ${s.content}\n`
      })
      aiResponse += '\n'
    }

    aiResponse += '想继续讨论吗？'

    // 添加消息到面板
    const userMsg: Message = {
      id: `entry-${latestEntry.id}`,
      role: 'user',
      content: `我记录了：${latestEntry.rawText.slice(0, 100)}${latestEntry.rawText.length > 100 ? '...' : ''}`
    }

    const aiMsg: Message = {
      id: `ai-${latestEntry.id}`,
      role: 'assistant',
      content: aiResponse
    }

    setMessages(prev => [...prev, userMsg, aiMsg])
  }, [latestEntry])

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadConversation = async (id: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/chat/${id}`)
      const data = await res.json()
      if (data.success) {
        setMessages(data.conversation.messages)
      }
    } catch (error) {
      console.error('Failed to load conversation:', error)
    } finally {
      setLoading(false)
    }
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || sending) return

    const userMessage = input.trim()
    setInput('')
    setSending(true)

    // 添加用户消息
    const userMsgId = `user-${Date.now()}`
    const userMsg: Message = {
      id: userMsgId,
      role: 'user',
      content: userMessage,
    }
    setMessages(prev => [...prev, userMsg])

    // 添加 AI 消息占位
    const aiMsgId = `ai-${Date.now()}`
    const aiMsg: Message = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
    }
    setMessages(prev => [...prev, aiMsg])

    try {
      // 使用流式 API
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversationId,
          entryContext: latestEntry ? {
            rawText: latestEntry.rawText,
            analysis: latestEntry.expertAnalysis?.interpretation || latestEntry.factCard?.oneLine,
          } : null,
        }),
      })

      if (!res.ok) throw new Error('Stream failed')

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) throw new Error('No reader')

      let fullContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.content) {
                fullContent += data.content
                // 实时更新消息内容
                setMessages(prev =>
                  prev.map(m => m.id === aiMsgId ? { ...m, content: fullContent } : m)
                )
              }
              if (data.done) {
                break
              }
            } catch {
              // 忽略解析错误
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error)
      // 显示错误消息
      setMessages(prev =>
        prev.map(m => m.id === aiMsgId ? { ...m, content: '抱歉，发生了错误，请重试。' } : m)
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 标题 */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">专家讨论</h3>
      </div>

      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <MessageCircle className="w-10 h-10 mb-3 text-gray-300" />
            <p className="text-sm font-medium">和专家聊聊</p>
            <p className="text-xs mt-1 text-gray-400">问问育儿问题，寻求专业建议</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map(message => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 ${
                    message.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  <div className="whitespace-pre-wrap text-sm">{message.content}</div>
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

      {/* 输入区域 */}
      <div className="border-t border-gray-200 p-3">
        <form onSubmit={sendMessage} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入你的问题..."
            className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
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
  )
}
