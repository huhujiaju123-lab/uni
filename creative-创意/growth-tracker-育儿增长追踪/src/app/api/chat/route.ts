/**
 * Chat API
 *
 * POST /api/chat - 发送消息并获取回复
 * GET /api/chat - 获取对话列表
 */

import { NextRequest, NextResponse } from 'next/server'
import {
  runChat,
  getChatContext,
  getConversationHistory,
  saveMessage,
  createConversation,
  updateConversationTitle,
  listConversations,
} from '@/lib/agents/chat'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, conversationId } = body

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: '缺少消息内容' },
        { status: 400 }
      )
    }

    // 如果没有 conversationId，创建新对话
    let convId = conversationId
    let isNewConversation = false

    if (!convId) {
      const conversation = await createConversation()
      convId = conversation.id
      isNewConversation = true
    }

    // 获取对话历史
    const history = await getConversationHistory(convId)

    // 获取上下文（最近记录、相关记录等）
    const context = await getChatContext(message)

    // 保存用户消息
    await saveMessage(convId, 'user', message)

    // 调用 Chat Agent
    const result = await runChat(message, history, context)

    if (!result.success || !result.reply) {
      return NextResponse.json(
        { error: result.error || '生成回复失败' },
        { status: 500 }
      )
    }

    // 保存 AI 回复
    await saveMessage(convId, 'assistant', result.reply, result.referencedEntryIds)

    // 如果是新对话，根据第一条消息生成标题
    if (isNewConversation) {
      const title = generateTitle(message)
      await updateConversationTitle(convId, title)
    }

    return NextResponse.json({
      success: true,
      conversationId: convId,
      reply: result.reply,
      referencedEntryIds: result.referencedEntryIds,
      isNewConversation,
    })
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error('POST /api/chat error:', errorMessage)
    return NextResponse.json({ error: errorMessage }, { status: 500 })
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')

    const conversations = await listConversations(limit)

    return NextResponse.json({
      success: true,
      conversations: conversations.map(conv => ({
        id: conv.id,
        title: conv.title || '新对话',
        lastMessage: conv.messages[0]?.content.slice(0, 50) || '',
        updatedAt: conv.updatedAt,
      })),
    })
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error('GET /api/chat error:', errorMessage)
    return NextResponse.json({ error: errorMessage }, { status: 500 })
  }
}

/**
 * 根据消息内容生成对话标题
 */
function generateTitle(message: string): string {
  // 简单实现：取前 20 个字符
  const cleaned = message.replace(/\n/g, ' ').trim()
  if (cleaned.length <= 20) {
    return cleaned
  }
  return cleaned.slice(0, 20) + '...'
}
