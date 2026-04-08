/**
 * Recorder Agent
 *
 * 职责：将用户的原始育儿日志文本转换为结构化的 FactCard
 *
 * 输入：原始文本 + 可选的年龄信息
 * 输出：FactCard JSON
 */

import { callAgentWithRetry } from './base'
import { FactCardOutputSchema, type FactCardOutput } from '@/lib/types'

export interface RecorderInput {
  rawText: string
  childAge?: string
  entryDate: string
}

export interface RecorderResult {
  success: boolean
  factCard?: FactCardOutput
  error?: string
  promptVersion: string
}

/**
 * 运行 Recorder Agent
 */
export async function runRecorder(input: RecorderInput): Promise<RecorderResult> {
  // 构建用户消息
  const userMessage = buildUserMessage(input)

  // 调用 Agent
  const result = await callAgentWithRetry<FactCardOutput>('recorder', userMessage)

  if (!result.success || !result.data) {
    return {
      success: false,
      error: result.error,
      promptVersion: result.promptVersion,
    }
  }

  // 验证输出格式
  const validation = FactCardOutputSchema.safeParse(result.data)
  if (!validation.success) {
    console.error('FactCard validation failed:', validation.error)
    return {
      success: false,
      error: `Invalid FactCard format: ${validation.error.message}`,
      promptVersion: result.promptVersion,
    }
  }

  return {
    success: true,
    factCard: validation.data,
    promptVersion: result.promptVersion,
  }
}

/**
 * 构建发送给 Agent 的用户消息
 */
function buildUserMessage(input: RecorderInput): string {
  let message = `## 日志日期\n${input.entryDate}\n\n`

  if (input.childAge) {
    message += `## 孩子年龄\n${input.childAge}\n\n`
  }

  message += `## 原始记录\n${input.rawText}`

  return message
}
