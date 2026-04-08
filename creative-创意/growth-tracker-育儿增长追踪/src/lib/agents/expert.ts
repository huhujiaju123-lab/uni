/**
 * Expert Agent
 *
 * 职责：基于 FactCard 和历史上下文，提供专业的育儿建议
 *
 * 输入：
 * - 当前 FactCard
 * - 历史上下文（最近记录 + 相似记录）
 * - 策略库（已验证的有效/无效策略）
 *
 * 输出：ExpertAnalysis JSON
 */

import { callAgentWithRetry } from './base'
import { ExpertOutputSchema, type ExpertOutput, type FactCardOutput, type RetrievalContext } from '@/lib/types'

export interface ExpertInput {
  factCard: FactCardOutput
  entryId: string
  context?: RetrievalContext
}

export interface ExpertResult {
  success: boolean
  analysis?: ExpertOutput
  error?: string
  promptVersion: string
}

/**
 * 运行 Expert Agent
 */
export async function runExpert(input: ExpertInput): Promise<ExpertResult> {
  // 构建用户消息
  const userMessage = buildUserMessage(input)

  // 调用 Agent
  const result = await callAgentWithRetry<ExpertOutput>('expert', userMessage)

  if (!result.success || !result.data) {
    return {
      success: false,
      error: result.error,
      promptVersion: result.promptVersion,
    }
  }

  // 验证输出格式
  const validation = ExpertOutputSchema.safeParse(result.data)
  if (!validation.success) {
    console.error('ExpertOutput validation failed:', validation.error)
    return {
      success: false,
      error: `Invalid ExpertOutput format: ${validation.error.message}`,
      promptVersion: result.promptVersion,
    }
  }

  return {
    success: true,
    analysis: validation.data,
    promptVersion: result.promptVersion,
  }
}

/**
 * 构建发送给 Expert Agent 的用户消息
 */
function buildUserMessage(input: ExpertInput): string {
  const { factCard, context } = input

  let message = `## 当前记录 (FactCard)\n\n`
  message += `**一句话摘要**: ${factCard.oneLine}\n\n`
  message += `**事件列表**:\n`
  factCard.events.forEach((event, i) => {
    message += `${i + 1}. [${event.type}] ${event.description}`
    if (event.emotion) message += ` (情绪: ${event.emotion})`
    if (event.context) message += ` - 情境: ${event.context}`
    message += '\n'
  })
  message += `\n**标签**: ${factCard.tags.join(', ')}\n`
  if (factCard.ageBucket) {
    message += `**年龄段**: ${factCard.ageBucket}\n`
  }

  // 添加历史上下文
  if (context) {
    if (context.recentEntries.length > 0) {
      message += `\n---\n\n## 最近记录 (最近 ${context.recentEntries.length} 条)\n\n`
      context.recentEntries.forEach((entry, i) => {
        if (entry.factCard) {
          message += `### ${i + 1}. ${formatDate(entry.entryDate)}\n`
          message += `${entry.factCard.oneLine}\n`
          message += `标签: ${entry.factCard.tags.join(', ')}\n\n`
        }
      })
    }

    if (context.similarEntries.length > 0) {
      message += `\n---\n\n## 相似记录 (语义相关)\n\n`
      context.similarEntries.forEach((entry, i) => {
        if (entry.factCard) {
          message += `### ${i + 1}. ${formatDate(entry.entryDate)}\n`
          message += `${entry.factCard.oneLine}\n`
          message += `标签: ${entry.factCard.tags.join(', ')}\n\n`
        }
      })
    }

    if (context.strategies.length > 0) {
      message += `\n---\n\n## 策略库参考\n\n`
      context.strategies.forEach((strategy, i) => {
        message += `${i + 1}. [${strategy.category}] ${strategy.description}\n`
        if (strategy.conditions) {
          message += `   适用条件: ${strategy.conditions}\n`
        }
      })
    }
  }

  message += `\n---\n\n请基于以上信息，提供专业的解读和建议。`

  return message
}

function formatDate(date: Date): string {
  return new Date(date).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}
