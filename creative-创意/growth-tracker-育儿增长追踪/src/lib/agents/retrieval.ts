/**
 * 检索模块
 *
 * 负责为 Expert Agent 检索相关的历史上下文：
 * 1. 最近 N 条记录（时间相关）
 * 2. 语义相似的记录（pgvector）
 * 3. 相关策略
 */

import prisma from '@/lib/db'
import type { FactCardOutput, RetrievalContext, EntryWithAnalysis } from '@/lib/types'

export interface RetrievalOptions {
  currentFactCard: FactCardOutput
  currentEntryId: string
  limit?: number // 总共返回的条目数
}

/**
 * 检索历史上下文
 *
 * 策略：最近 N/2 条 + 相似 N/2 条（去重）
 */
export async function retrieveContext(options: RetrievalOptions): Promise<RetrievalContext> {
  const { currentFactCard, currentEntryId, limit = 6 } = options

  const recentLimit = Math.ceil(limit / 2)
  const similarLimit = Math.floor(limit / 2)

  // 1. 获取最近的记录
  const recentEntries = await getRecentEntries(currentEntryId, recentLimit)

  // 2. 获取标签相似的记录（暂时用标签匹配代替向量检索）
  const similarEntries = await getSimilarByTags(
    currentFactCard.tags,
    currentEntryId,
    recentEntries.map((e) => e.id),
    similarLimit
  )

  // 3. 获取相关策略
  const strategies = await getRelevantStrategies(currentFactCard.tags)

  return {
    recentEntries,
    similarEntries,
    strategies,
  }
}

/**
 * 获取最近的 Entry
 */
async function getRecentEntries(excludeId: string, limit: number): Promise<EntryWithAnalysis[]> {
  const entries = await prisma.entry.findMany({
    where: {
      id: { not: excludeId },
    },
    include: {
      factCard: {
        include: {
          expertAnalysis: true,
        },
      },
    },
    orderBy: { entryDate: 'desc' },
    take: limit,
  })

  return entries.map(mapEntryToResult)
}

/**
 * 基于标签获取相似记录
 * TODO: 后续改为 pgvector 向量检索
 */
async function getSimilarByTags(
  tags: string[],
  excludeId: string,
  excludeIds: string[],
  limit: number
): Promise<EntryWithAnalysis[]> {
  if (tags.length === 0) return []

  const allExcludeIds = [excludeId, ...excludeIds]

  // 查找有相同标签的记录
  const entries = await prisma.entry.findMany({
    where: {
      id: { notIn: allExcludeIds },
      factCard: {
        tags: {
          hasSome: tags,
        },
      },
    },
    include: {
      factCard: {
        include: {
          expertAnalysis: true,
        },
      },
    },
    orderBy: { entryDate: 'desc' },
    take: limit * 2, // 多取一些，后面按相关度排序
  })

  // 按标签匹配数量排序
  const scored = entries.map((entry) => {
    const matchCount = entry.factCard?.tags.filter((t) => tags.includes(t)).length || 0
    return { entry, matchCount }
  })

  scored.sort((a, b) => b.matchCount - a.matchCount)

  return scored.slice(0, limit).map((s) => mapEntryToResult(s.entry))
}

/**
 * 获取相关策略
 */
async function getRelevantStrategies(tags: string[]) {
  // 从标签推断相关的策略类别
  const categories = inferCategories(tags)

  const strategies = await prisma.strategy.findMany({
    where: {
      status: 'active',
      category: { in: categories },
    },
    select: {
      category: true,
      description: true,
      conditions: true,
    },
    take: 5,
  })

  return strategies
}

/**
 * 从标签推断策略类别
 */
function inferCategories(tags: string[]): string[] {
  const categoryMap: Record<string, string[]> = {
    sleep: ['睡眠', '入睡', '夜醒', '午睡', '早醒', '睡眠倒退'],
    emotion: ['情绪', '发脾气', '焦虑', '害怕', '开心', '分离焦虑'],
    behavior: ['行为', '打人', '咬人', '分享', '冲突'],
    feeding: ['吃饭', '喂养', '挑食', '辅食'],
    social: ['社交', '同伴', '互动', '幼儿园'],
  }

  const categories = new Set<string>()

  for (const tag of tags) {
    for (const [category, keywords] of Object.entries(categoryMap)) {
      if (keywords.some((k) => tag.includes(k) || k.includes(tag))) {
        categories.add(category)
      }
    }
  }

  return Array.from(categories)
}

/**
 * 映射数据库记录到返回类型
 */
function mapEntryToResult(entry: any): EntryWithAnalysis {
  return {
    id: entry.id,
    rawText: entry.rawText,
    entryDate: entry.entryDate,
    childAge: entry.childAge,
    createdAt: entry.createdAt,
    factCard: entry.factCard ? {
      id: entry.factCard.id,
      oneLine: entry.factCard.oneLine,
      events: entry.factCard.events,
      tags: entry.factCard.tags,
      missingInfo: entry.factCard.missingInfo,
      ageBucket: entry.factCard.ageBucket,
      expertAnalysis: entry.factCard.expertAnalysis ? {
        interpretation: entry.factCard.expertAnalysis.interpretation,
        suggestions: entry.factCard.expertAnalysis.suggestions,
        patterns: entry.factCard.expertAnalysis.patterns,
        riskFlags: entry.factCard.expertAnalysis.riskFlags,
      } : null,
    } : null,
  }
}

// ============================================
// 向量检索相关（预留接口）
// ============================================

/**
 * 生成文本的 embedding
 * TODO: 实现 OpenAI embedding 调用
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  // 占位实现，后续接入 OpenAI embedding API
  console.warn('generateEmbedding not implemented yet')
  return []
}

/**
 * 向量相似度检索
 * TODO: 使用 pgvector 实现
 */
export async function searchByVector(
  embedding: number[],
  excludeIds: string[],
  limit: number
): Promise<EntryWithAnalysis[]> {
  // 占位实现，后续使用原生 SQL 查询 pgvector
  console.warn('searchByVector not implemented yet')
  return []
}
