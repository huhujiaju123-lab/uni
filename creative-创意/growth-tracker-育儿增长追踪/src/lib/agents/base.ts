/**
 * Agent 基础框架
 *
 * 提供统一的 LLM 调用接口，支持：
 * - 多 LLM 提供商（当前支持 OpenAI）
 * - 结构化输出（JSON mode）
 * - 错误处理和重试
 * - 调用日志（可选）
 */

import OpenAI from 'openai'
import type { AgentName, AgentConfig } from '@/lib/types'
import { getAgentPrompt } from '@/lib/prompts/registry'

// 默认配置
const DEFAULT_CONFIGS: Record<AgentName, AgentConfig> = {
  recorder: {
    name: 'recorder',
    model: 'gpt-4o',
    maxTokens: 2000,
    temperature: 0.3, // 低温度，保持输出稳定
  },
  expert: {
    name: 'expert',
    model: 'gpt-4o',
    maxTokens: 3000,
    temperature: 0.5,
  },
  values: {
    name: 'values',
    model: 'gpt-4o',
    maxTokens: 1500,
    temperature: 0.5,
  },
  orchestrator: {
    name: 'orchestrator',
    model: 'gpt-4o',
    maxTokens: 500,
    temperature: 0.2,
  },
  chat: {
    name: 'chat',
    model: 'gpt-4o',
    maxTokens: 2000,
    temperature: 0.7,
  },
  mentor: {
    name: 'mentor',
    model: 'gpt-4o',
    maxTokens: 2000,
    temperature: 0.5,
  },
}

// OpenAI 客户端单例
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

export interface AgentCallResult<T> {
  success: boolean
  data?: T
  error?: string
  promptVersion: string
  usage?: {
    promptTokens: number
    completionTokens: number
    totalTokens: number
  }
}

/**
 * 调用 Agent
 *
 * @param agentName Agent 名称
 * @param userMessage 用户消息（用户输入或上一个 Agent 的输出）
 * @param configOverrides 配置覆盖
 */
export async function callAgent<T>(
  agentName: AgentName,
  userMessage: string,
  configOverrides?: Partial<AgentConfig>
): Promise<AgentCallResult<T>> {
  try {
    // 获取 prompt
    const { prompt: systemPrompt, version: promptVersion } = await getAgentPrompt(agentName)

    // 合并配置
    const config = { ...DEFAULT_CONFIGS[agentName], ...configOverrides }

    // 调用 OpenAI
    const client = getOpenAIClient()
    const response = await client.chat.completions.create({
      model: config.model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userMessage },
      ],
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      response_format: { type: 'json_object' },
    })

    const content = response.choices[0]?.message?.content
    if (!content) {
      return {
        success: false,
        error: 'Empty response from LLM',
        promptVersion,
      }
    }

    // 解析 JSON
    const data = JSON.parse(content) as T

    return {
      success: true,
      data,
      promptVersion,
      usage: response.usage ? {
        promptTokens: response.usage.prompt_tokens,
        completionTokens: response.usage.completion_tokens,
        totalTokens: response.usage.total_tokens,
      } : undefined,
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error(`Agent ${agentName} error:`, errorMessage)
    return {
      success: false,
      error: errorMessage,
      promptVersion: 'error',
    }
  }
}

/**
 * 带重试的 Agent 调用
 */
export async function callAgentWithRetry<T>(
  agentName: AgentName,
  userMessage: string,
  maxRetries = 2,
  configOverrides?: Partial<AgentConfig>
): Promise<AgentCallResult<T>> {
  let lastError: string | undefined

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const result = await callAgent<T>(agentName, userMessage, configOverrides)

    if (result.success) {
      return result
    }

    lastError = result.error
    console.warn(`Agent ${agentName} attempt ${attempt + 1} failed: ${lastError}`)

    // 最后一次尝试不等待
    if (attempt < maxRetries) {
      await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)))
    }
  }

  return {
    success: false,
    error: lastError || 'Max retries exceeded',
    promptVersion: 'error',
  }
}
