'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, MessageCircle, Plus, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt?: string
}

interface Conversation {
  id: string
  title: string
  lastMessage: string
  updatedAt: string
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 加载对话列表
  useEffect(() => {
    loadConversations()
  }, [])

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadConversations = async () => {
    try {
      const res = await fetch('/api/chat')
      const data = await res.json()
      if (data.success) {
        setConversations(data.conversations)
      }
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }

  const loadConversation = async (conversationId: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/chat/${conversationId}`)
      const data = await res.json()
      if (data.success) {
        setCurrentConversationId(conversationId)
        setMessages(data.conversation.messages)
      }
    } catch (error) {
      console.error('Failed to load conversation:', error)
    } finally {
      setLoading(false)
    }
  }

  const startNewConversation = () => {
    setCurrentConversationId(null)
    setMessages([])
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || sending) return

    const userMessage = input.trim()
    setInput('')
    setSending(true)

    // 乐观更新：先显示用户消息
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
    }
    setMessages(prev => [...prev, tempUserMessage])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversationId: currentConversationId,
        }),
      })

      const data = await res.json()

      if (data.success) {
        // 如果是新对话，更新对话 ID
        if (data.isNewConversation) {
          setCurrentConversationId(data.conversationId)
          loadConversations() // 刷新对话列表
        }

        // 添加 AI 回复
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.reply,
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        // 错误处理：移除乐观更新的消息
        setMessages(prev => prev.filter(m => m.id !== tempUserMessage.id))
        alert(data.error || '发送失败')
      }
    } catch (error) {
      setMessages(prev => prev.filter(m => m.id !== tempUserMessage.id))
      alert('网络错误，请重试')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] -mx-4 -mt-8">
      {/* 左侧：对话列表 */}
      <div className="w-64 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <Link href="/" className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4">
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">返回首页</span>
          </Link>
          <button
            onClick={startNewConversation}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>新对话</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="p-4 text-center text-gray-500 text-sm">
              还没有对话记录
            </div>
          ) : (
            <div className="p-2">
              {conversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className={`w-full text-left p-3 rounded-lg mb-1 transition-colors ${
                    currentConversationId === conv.id
                      ? 'bg-primary-50 text-primary-700'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <div className="font-medium text-sm truncate">{conv.title}</div>
                  <div className="text-xs text-gray-500 truncate mt-1">
                    {conv.lastMessage || '暂无消息'}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 右侧：对话内容 */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <MessageCircle className="w-12 h-12 mb-4 text-gray-300" />
              <p className="text-lg font-medium">和专家聊聊</p>
              <p className="text-sm mt-2">问问孩子的发展情况、育儿困惑，或者任何问题</p>
            </div>
          ) : (
            <div className="space-y-4 max-w-3xl mx-auto">
              {messages.map(message => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-primary-500 text-white'
                        : 'bg-white border border-gray-200 text-gray-700'
                    }`}
                  >
                    <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                    <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="border-t border-gray-200 bg-white p-4">
          <form onSubmit={sendMessage} className="max-w-3xl mx-auto">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入你的问题..."
                className="flex-1 px-4 py-3 border border-gray-200 rounded-lg focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
                disabled={sending}
              />
              <button
                type="submit"
                disabled={!input.trim() || sending}
                className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {sending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
