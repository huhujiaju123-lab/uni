/**
 * Chat Agent - 对话专家
 *
 * 综合三个角色（记录者、专家、价值观导师）进行多轮对话
 * 支持：答疑解惑、深入讨论、追问澄清
 */

import OpenAI from 'openai'
import prisma from '@/lib/db'
import { getAgentPrompt } from '@/lib/prompts/registry'

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

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatContext {
  recentEntries: Array<{
    date: string
    oneLine: string
    tags: string[]
  }>
  relevantEntries: Array<{
    date: string
    oneLine: string
    tags: string[]
  }>
  childProfile?: {
    name: string
    age: string
  }
  valuesPrinciples: string[]
}

export interface ChatResult {
  success: boolean
  reply?: string
  referencedEntryIds?: string[]
  error?: string
}

/**
 * 运行 Chat Agent
 */
export async function runChat(
  userMessage: string,
  conversationHistory: ChatMessage[],
  context: ChatContext
): Promise<ChatResult> {
  try {
    // 获取 Chat Agent 的 prompt
    const { prompt: systemPrompt } = await getAgentPrompt('chat')

    // 构建带上下文的系统消息
    const contextualSystemPrompt = buildContextualPrompt(systemPrompt, context)

    // 构建消息列表
    const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
      { role: 'system', content: contextualSystemPrompt },
      ...conversationHistory.map(msg => ({
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
      })),
      { role: 'user', content: userMessage },
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
      return {
        success: false,
        error: 'Empty response from LLM',
      }
    }

    // 提取引用的日志 ID（如果回复中提到了具体日期）
    const referencedEntryIds = extractReferencedEntries(reply, context)

    return {
      success: true,
      reply,
      referencedEntryIds,
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error('Chat Agent error:', errorMessage)
    return {
      success: false,
      error: errorMessage,
    }
  }
}

/**
 * 构建带上下文的系统提示词
 */
function buildContextualPrompt(basePrompt: string, context: ChatContext): string {
  let contextSection = '\n\n## 当前上下文\n'

  // 孩子信息
  if (context.childProfile) {
    contextSection += `\n### 孩子信息\n`
    contextSection += `- 名字：${context.childProfile.name}\n`
    contextSection += `- 年龄：${context.childProfile.age}\n`
  }

  // 最近记录
  if (context.recentEntries.length > 0) {
    contextSection += `\n### 最近记录（最近 ${context.recentEntries.length} 条）\n`
    context.recentEntries.forEach((entry, i) => {
      contextSection += `${i + 1}. [${entry.date}] ${entry.oneLine}\n`
      contextSection += `   标签：${entry.tags.join('、')}\n`
    })
  }

  // 相关记录
  if (context.relevantEntries.length > 0) {
    contextSection += `\n### 相关历史记录\n`
    context.relevantEntries.forEach((entry, i) => {
      contextSection += `${i + 1}. [${entry.date}] ${entry.oneLine}\n`
      contextSection += `   标签：${entry.tags.join('、')}\n`
    })
  }

  // 价值观原则
  if (context.valuesPrinciples.length > 0) {
    contextSection += `\n### 家长的育儿原则\n`
    context.valuesPrinciples.forEach((principle, i) => {
      contextSection += `${i + 1}. ${principle}\n`
    })
  }

  return basePrompt + contextSection
}

/**
 * 从回复中提取引用的日志
 */
function extractReferencedEntries(reply: string, context: ChatContext): string[] {
  // 简单实现：检查回复中是否提到了上下文中的日期
  const referencedIds: string[] = []

  // 这里可以进一步实现更精确的匹配
  // 目前返回空数组，后续可以增强

  return referencedIds
}

/**
 * 获取对话上下文
 */
export async function getChatContext(userMessage: string): Promise<ChatContext> {
  // 获取最近的记录
  const recentEntries = await prisma.entry.findMany({
    take: 5,
    orderBy: { entryDate: 'desc' },
    include: {
      factCard: true,
    },
  })

  // 获取价值观原则
  const principles = await prisma.valuesPrinciple.findMany({
    where: { isActive: true },
    select: { principle: true },
  })

  // 获取孩子档案
  const childProfile = await prisma.childProfile.findFirst()

  // 基于用户消息检索相关记录（简单的标签匹配）
  const relevantEntries = await searchRelevantEntries(userMessage)

  return {
    recentEntries: recentEntries.map(e => ({
      date: formatDate(e.entryDate),
      oneLine: e.factCard?.oneLine || e.rawText.slice(0, 50),
      tags: e.factCard?.tags || [],
    })),
    relevantEntries: relevantEntries.map(e => ({
      date: formatDate(e.entryDate),
      oneLine: e.factCard?.oneLine || e.rawText.slice(0, 50),
      tags: e.factCard?.tags || [],
    })),
    childProfile: childProfile ? {
      name: childProfile.name,
      age: calculateAge(childProfile.birthday),
    } : undefined,
    valuesPrinciples: principles.map(p => p.principle),
  }
}

/**
 * 搜索相关记录
 */
async function searchRelevantEntries(query: string) {
  // 简单实现：提取关键词匹配标签
  const keywords = extractKeywords(query)

  if (keywords.length === 0) {
    return []
  }

  const entries = await prisma.entry.findMany({
    where: {
      factCard: {
        tags: {
          hasSome: keywords,
        },
      },
    },
    take: 5,
    orderBy: { entryDate: 'desc' },
    include: {
      factCard: true,
    },
  })

  return entries
}

/**
 * 提取关键词
 */
function extractKeywords(text: string): string[] {
  const keywordMap: Record<string, string[]> = {
    '睡': ['睡眠', '入睡', '夜醒', '午睡'],
    '哭': ['情绪', '哭闹', '发脾气'],
    '吃': ['饮食', '吃饭', '喂养'],
    '玩': ['游戏', '玩耍', '社交'],
    '说': ['语言', '说话', '表达'],
    '走': ['运动', '大运动'],
    '焦虑': ['分离焦虑', '焦虑', '情绪'],
    '脾气': ['发脾气', '情绪', '行为'],
  }

  const keywords: string[] = []

  for (const [key, values] of Object.entries(keywordMap)) {
    if (text.includes(key)) {
      keywords.push(...values)
    }
  }

  return Array.from(new Set(keywords))
}

function formatDate(date: Date): string {
  return new Date(date).toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
  })
}

function calculateAge(birthday: Date): string {
  const now = new Date()
  const birth = new Date(birthday)
  const months = (now.getFullYear() - birth.getFullYear()) * 12 + (now.getMonth() - birth.getMonth())
  const years = Math.floor(months / 12)
  const remainingMonths = months % 12

  if (years === 0) {
    return `${remainingMonths}个月`
  }
  return `${years}岁${remainingMonths}个月`
}

/**
 * 获取对话历史
 */
export async function getConversationHistory(conversationId: string): Promise<ChatMessage[]> {
  const messages = await prisma.message.findMany({
    where: { conversationId },
    orderBy: { createdAt: 'asc' },
    take: 20, // 最多取最近 20 条
  })

  return messages.map(m => ({
    role: m.role as 'user' | 'assistant',
    content: m.content,
  }))
}

/**
 * 保存消息
 */
export async function saveMessage(
  conversationId: string,
  role: 'user' | 'assistant',
  content: string,
  referencedEntryIds: string[] = []
) {
  return prisma.message.create({
    data: {
      conversationId,
      role,
      content,
      referencedEntryIds,
    },
  })
}

/**
 * 创建新对话
 */
export async function createConversation(title?: string) {
  return prisma.conversation.create({
    data: {
      title,
      status: 'active',
    },
  })
}

/**
 * 更新对话标题
 */
export async function updateConversationTitle(conversationId: string, title: string) {
  return prisma.conversation.update({
    where: { id: conversationId },
    data: { title },
  })
}

/**
 * 获取对话列表
 */
export async function listConversations(limit = 20) {
  return prisma.conversation.findMany({
    where: { status: 'active' },
    orderBy: { updatedAt: 'desc' },
    take: limit,
    include: {
      messages: {
        take: 1,
        orderBy: { createdAt: 'desc' },
      },
    },
  })
}
