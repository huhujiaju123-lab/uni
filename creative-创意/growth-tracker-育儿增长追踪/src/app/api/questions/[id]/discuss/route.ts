import { NextRequest, NextResponse } from 'next/server'
import OpenAI from 'openai'
import prisma from '@/lib/db'
import { getAgentPrompt } from '@/lib/prompts/registry'

interface RouteParams {
  params: Promise<{ id: string }>
}

// OpenAI 客户端
let openaiClient: OpenAI | null = null

function getOpenAIClient(): OpenAI {
  if (!openaiClient) {
    const apiKey = process.env.OPENAI_API_KEY
    if (!apiKey) {
      throw new Error('OPENAI_API_KEY environment variable is not set')
    }
    openaiClient = new OpenAI({ apiKey })
  }
  return openaiClient
}

// POST /api/questions/[id]/discuss - 与专家讨论问题
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params
    const body = await request.json()
    const { message } = body

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { success: false, error: 'Message is required' },
        { status: 400 }
      )
    }

    // 获取问题详情
    const question = await prisma.parentingQuestion.findUnique({
      where: { id },
      include: {
        observations: {
          orderBy: { createdAt: 'desc' },
          take: 10,
        },
        discussions: {
          orderBy: { createdAt: 'asc' },
          take: 20,
        },
      },
    })

    if (!question) {
      return NextResponse.json(
        { success: false, error: 'Question not found' },
        { status: 404 }
      )
    }

    // 获取孩子档案
    const childProfile = await prisma.childProfile.findFirst()

    // 获取专家 prompt
    const { prompt: systemPrompt } = await getAgentPrompt('expert')

    // 构建上下文
    const contextPrompt = buildQuestionContext(question, childProfile)

    // 构建消息历史
    const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
      { role: 'system', content: systemPrompt + '\n\n' + contextPrompt },
      // 添加历史讨论
      ...question.discussions.map((d) => ({
        role: d.role as 'user' | 'assistant',
        content: d.content,
      })),
      { role: 'user', content: message },
    ]

    // 调用 OpenAI
    const client = getOpenAIClient()
    const response = await client.chat.completions.create({
      model: 'gpt-4o',
      messages,
      max_tokens: 2000,
      temperature: 0.7,
    })

    const reply = response.choices[0]?.message?.content
    if (!reply) {
      return NextResponse.json(
        { success: false, error: 'Empty response from AI' },
        { status: 500 }
      )
    }

    // 保存用户消息
    const userMessage = await prisma.questionDiscussion.create({
      data: {
        questionId: id,
        role: 'user',
        content: message.trim(),
      },
    })

    // 保存 AI 回复
    const assistantMessage = await prisma.questionDiscussion.create({
      data: {
        questionId: id,
        role: 'assistant',
        content: reply,
      },
    })

    // 尝试提取结论建议
    const suggestedConclusion = extractConclusionSuggestion(reply)

    return NextResponse.json({
      success: true,
      userMessage,
      assistantMessage,
      suggestedConclusion,
    })
  } catch (error) {
    console.error('Failed to discuss question:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to discuss question' },
      { status: 500 }
    )
  }
}

// 构建问题上下文
function buildQuestionContext(
  question: {
    question: string
    stage: string
    currentConclusion: string | null
    observations: Array<{ content: string; createdAt: Date }>
  },
  childProfile: { name: string; birthday: Date } | null
): string {
  let context = '## 当前讨论的问题\n\n'
  context += `**问题**: ${question.question}\n`
  context += `**阶段**: ${getStageLabel(question.stage)}\n`

  if (question.currentConclusion) {
    context += `**当前结论**: ${question.currentConclusion}\n`
  }

  if (childProfile) {
    const age = calculateAge(childProfile.birthday)
    context += `\n**孩子信息**: ${childProfile.name}, ${age}\n`
  }

  if (question.observations.length > 0) {
    context += '\n### 相关观察记录\n\n'
    question.observations.forEach((obs, i) => {
      const date = new Date(obs.createdAt).toLocaleDateString('zh-CN')
      context += `${i + 1}. [${date}] ${obs.content}\n`
    })
  }

  context += '\n---\n'
  context += '请基于以上信息回答用户的问题。如果有合适的结论建议，可以在回复中提出。\n'

  return context
}

function getStageLabel(stage: string): string {
  const labels: Record<string, string> = {
    observing: '🔴 观察期',
    experimenting: '🟡 实验期',
    internalized: '🟢 已内化',
  }
  return labels[stage] || stage
}

function calculateAge(birthday: Date): string {
  const now = new Date()
  const birth = new Date(birthday)
  const months =
    (now.getFullYear() - birth.getFullYear()) * 12 +
    (now.getMonth() - birth.getMonth())
  const years = Math.floor(months / 12)
  const remainingMonths = months % 12

  if (years === 0) {
    return `${remainingMonths}个月`
  }
  return `${years}岁${remainingMonths}个月`
}

// 尝试从回复中提取结论建议
function extractConclusionSuggestion(reply: string): string | null {
  // 简单的启发式方法：查找"建议"、"结论"等关键词后的内容
  const patterns = [
    /(?:建议|结论|总结)[:：]\s*([^\n]+)/,
    /(?:可以考虑|你可以)[:：]?\s*([^\n]+)/,
  ]

  for (const pattern of patterns) {
    const match = reply.match(pattern)
    if (match && match[1]) {
      return match[1].trim()
    }
  }

  return null
}
