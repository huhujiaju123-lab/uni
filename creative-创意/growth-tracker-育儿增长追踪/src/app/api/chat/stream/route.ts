/**
 * 流式聊天 API
 * POST /api/chat/stream
 */

import { NextRequest } from 'next/server'
import OpenAI from 'openai'
import prisma from '@/lib/db'
import { getAgentPrompt } from '@/lib/prompts/registry'

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
})

export async function POST(request: NextRequest) {
  const { message, conversationId, entryContext } = await request.json()

  if (!message) {
    return new Response('Missing message', { status: 400 })
  }

  // 获取 chat prompt
  const { prompt: systemPrompt } = await getAgentPrompt('chat')

  // 构建上下文
  let contextMessage = ''

  // 如果有日志上下文
  if (entryContext) {
    contextMessage = `
用户刚记录了：
"${entryContext.rawText}"

AI 分析：
${entryContext.analysis || '分析中...'}

请基于这个记录回复用户。
---
`
  }

  // 获取对话历史
  let history: Array<{ role: 'user' | 'assistant'; content: string }> = []
  if (conversationId) {
    const messages = await prisma.message.findMany({
      where: { conversationId },
      orderBy: { createdAt: 'asc' },
      take: 10,
    })
    history = messages.map(m => ({
      role: m.role as 'user' | 'assistant',
      content: m.content,
    }))
  }

  // 创建流式响应
  const stream = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: [
      { role: 'system', content: systemPrompt },
      ...history,
      { role: 'user', content: contextMessage + message },
    ],
    max_tokens: 2000,
    temperature: 0.7,
    stream: true,
  })

  // 转换为 SSE 格式
  const encoder = new TextEncoder()

  const readableStream = new ReadableStream({
    async start(controller) {
      let fullContent = ''

      try {
        for await (const chunk of stream) {
          const content = chunk.choices[0]?.delta?.content || ''
          if (content) {
            fullContent += content
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ content })}\n\n`))
          }
        }

        // 流结束，保存消息到数据库
        if (conversationId && fullContent) {
          // 保存用户消息
          await prisma.message.create({
            data: {
              conversationId,
              role: 'user',
              content: message,
            },
          })

          // 保存 AI 回复
          await prisma.message.create({
            data: {
              conversationId,
              role: 'assistant',
              content: fullContent,
            },
          })
        }

        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ done: true })}\n\n`))
        controller.close()
      } catch (error) {
        console.error('Stream error:', error)
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: 'Stream error' })}\n\n`))
        controller.close()
      }
    },
  })

  return new Response(readableStream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}
