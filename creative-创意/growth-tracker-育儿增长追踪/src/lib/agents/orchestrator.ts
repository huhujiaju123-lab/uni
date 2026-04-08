/**
 * Orchestrator - Agent 编排器
 *
 * 负责协调整个处理流水线：
 * 1. 接收用户输入
 * 2. 调用 Recorder 生成 FactCard
 * 3. 检索历史上下文
 * 4. 调用 Expert 生成分析
 * 5. 持久化所有数据
 */

import prisma from '@/lib/db'
import { runRecorder } from './recorder'
import { runExpert } from './expert'
import { retrieveContext } from './retrieval'
import type { CreateEntryRequest, EntryWithAnalysis, FactCardOutput, ExpertOutput } from '@/lib/types'

export interface ProcessResult {
  success: boolean
  entry?: EntryWithAnalysis
  error?: string
  stages: {
    recorder: { success: boolean; error?: string; promptVersion?: string }
    expert: { success: boolean; error?: string; promptVersion?: string }
  }
}

/**
 * 处理新的育儿日志
 *
 * 完整流程：
 * rawText → Recorder → FactCard → 检索上下文 → Expert → 分析结果 → 存储
 */
export async function processEntry(request: CreateEntryRequest): Promise<ProcessResult> {
  const stages: ProcessResult['stages'] = {
    recorder: { success: false },
    expert: { success: false },
  }

  try {
    // 1. 创建 Entry 记录
    const entry = await prisma.entry.create({
      data: {
        rawText: request.rawText,
        entryDate: new Date(request.entryDate),
        childAge: request.childAge,
      },
    })

    // 2. 运行 Recorder Agent
    const recorderResult = await runRecorder({
      rawText: request.rawText,
      childAge: request.childAge,
      entryDate: request.entryDate,
    })

    stages.recorder = {
      success: recorderResult.success,
      error: recorderResult.error,
      promptVersion: recorderResult.promptVersion,
    }

    if (!recorderResult.success || !recorderResult.factCard) {
      return {
        success: false,
        error: `Recorder failed: ${recorderResult.error}`,
        stages,
      }
    }

    // 3. 保存 FactCard
    const factCard = await prisma.factCard.create({
      data: {
        entryId: entry.id,
        oneLine: recorderResult.factCard.oneLine,
        events: recorderResult.factCard.events,
        tags: recorderResult.factCard.tags,
        missingInfo: recorderResult.factCard.missingInfo,
        ageBucket: recorderResult.factCard.ageBucket,
      },
    })

    // 4. 检索历史上下文
    const context = await retrieveContext({
      currentFactCard: recorderResult.factCard,
      currentEntryId: entry.id,
      limit: 6,
    })

    // 5. 运行 Expert Agent
    const expertResult = await runExpert({
      factCard: recorderResult.factCard,
      entryId: entry.id,
      context,
    })

    stages.expert = {
      success: expertResult.success,
      error: expertResult.error,
      promptVersion: expertResult.promptVersion,
    }

    // 6. 保存 Expert 分析结果（即使失败也继续）
    let expertAnalysis = null
    if (expertResult.success && expertResult.analysis) {
      expertAnalysis = await prisma.expertAnalysis.create({
        data: {
          factCardId: factCard.id,
          interpretation: expertResult.analysis.interpretation,
          suggestions: expertResult.analysis.suggestions,
          patterns: expertResult.analysis.patterns || [],
          riskFlags: expertResult.analysis.riskFlags,
        },
      })
    }

    // 7. 返回完整结果
    const fullEntry: EntryWithAnalysis = {
      id: entry.id,
      rawText: entry.rawText,
      entryDate: entry.entryDate,
      childAge: entry.childAge,
      createdAt: entry.createdAt,
      factCard: {
        id: factCard.id,
        oneLine: factCard.oneLine,
        events: factCard.events as EntryWithAnalysis['factCard'] extends { events: infer E } ? E : never,
        tags: factCard.tags,
        missingInfo: factCard.missingInfo,
        ageBucket: factCard.ageBucket,
        expertAnalysis: expertAnalysis ? {
          interpretation: expertAnalysis.interpretation,
          suggestions: expertAnalysis.suggestions as any,
          patterns: expertAnalysis.patterns as any,
          riskFlags: expertAnalysis.riskFlags,
        } : null,
      },
    }

    return {
      success: true,
      entry: fullEntry,
      stages,
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error('Orchestrator error:', errorMessage)
    return {
      success: false,
      error: errorMessage,
      stages,
    }
  }
}

/**
 * 获取单个 Entry 的完整数据
 */
export async function getEntryWithAnalysis(entryId: string): Promise<EntryWithAnalysis | null> {
  const entry = await prisma.entry.findUnique({
    where: { id: entryId },
    include: {
      factCard: {
        include: {
          expertAnalysis: true,
        },
      },
    },
  })

  if (!entry) return null

  return {
    id: entry.id,
    rawText: entry.rawText,
    entryDate: entry.entryDate,
    childAge: entry.childAge,
    createdAt: entry.createdAt,
    factCard: entry.factCard ? {
      id: entry.factCard.id,
      oneLine: entry.factCard.oneLine,
      events: entry.factCard.events as any,
      tags: entry.factCard.tags,
      missingInfo: entry.factCard.missingInfo,
      ageBucket: entry.factCard.ageBucket,
      expertAnalysis: entry.factCard.expertAnalysis ? {
        interpretation: entry.factCard.expertAnalysis.interpretation,
        suggestions: entry.factCard.expertAnalysis.suggestions as any,
        patterns: entry.factCard.expertAnalysis.patterns as any,
        riskFlags: entry.factCard.expertAnalysis.riskFlags,
      } : null,
    } : null,
  }
}

/**
 * 获取 Entry 列表
 */
export async function listEntries(options: {
  limit?: number
  offset?: number
  tags?: string[]
  startDate?: Date
  endDate?: Date
}): Promise<EntryWithAnalysis[]> {
  const { limit = 20, offset = 0, tags, startDate, endDate } = options

  const where: any = {}

  if (startDate || endDate) {
    where.entryDate = {}
    if (startDate) where.entryDate.gte = startDate
    if (endDate) where.entryDate.lte = endDate
  }

  if (tags && tags.length > 0) {
    where.factCard = {
      tags: {
        hasEvery: tags,
      },
    }
  }

  const entries = await prisma.entry.findMany({
    where,
    include: {
      factCard: {
        include: {
          expertAnalysis: true,
        },
      },
    },
    orderBy: { entryDate: 'desc' },
    take: limit,
    skip: offset,
  })

  return entries.map((entry) => ({
    id: entry.id,
    rawText: entry.rawText,
    entryDate: entry.entryDate,
    childAge: entry.childAge,
    createdAt: entry.createdAt,
    factCard: entry.factCard ? {
      id: entry.factCard.id,
      oneLine: entry.factCard.oneLine,
      events: entry.factCard.events as any,
      tags: entry.factCard.tags,
      missingInfo: entry.factCard.missingInfo,
      ageBucket: entry.factCard.ageBucket,
      expertAnalysis: entry.factCard.expertAnalysis ? {
        interpretation: entry.factCard.expertAnalysis.interpretation,
        suggestions: entry.factCard.expertAnalysis.suggestions as any,
        patterns: entry.factCard.expertAnalysis.patterns as any,
        riskFlags: entry.factCard.expertAnalysis.riskFlags,
      } : null,
    } : null,
  }))
}
