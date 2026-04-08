// 核心类型定义

import { z } from 'zod'

// ============================================
// FactCard 事件结构
// ============================================

export const EventSchema = z.object({
  type: z.enum(['behavior', 'emotion', 'milestone', 'health', 'social', 'cognitive', 'language', 'motor', 'sleep', 'feeding', 'other']),
  description: z.string(),
  emotion: z.enum(['positive', 'negative', 'neutral', 'mixed']).optional(),
  context: z.string().optional(),
})

export type Event = z.infer<typeof EventSchema>

// ============================================
// Recorder Agent 输出
// ============================================

export const FactCardOutputSchema = z.object({
  oneLine: z.string().max(100),
  events: z.array(EventSchema),
  tags: z.array(z.string()),
  missingInfo: z.array(z.string()),
  ageBucket: z.enum(['0-6m', '6-12m', '1-2y', '2-3y', '3-4y', '4-5y', '5-6y']).optional(),
})

export type FactCardOutput = z.infer<typeof FactCardOutputSchema>

// ============================================
// Expert Agent 输出
// ============================================

export const SuggestionSchema = z.object({
  category: z.enum(['action', 'observation', 'resource', 'caution']),
  content: z.string(),
  priority: z.enum(['high', 'medium', 'low']),
})

export const PatternSchema = z.object({
  pattern: z.string(),
  evidence: z.array(z.string()), // entry IDs
})

export const ExpertOutputSchema = z.object({
  interpretation: z.string(),
  suggestions: z.array(SuggestionSchema),
  patterns: z.array(PatternSchema).optional(),
  riskFlags: z.array(z.string()),
})

export type ExpertOutput = z.infer<typeof ExpertOutputSchema>

// ============================================
// API 请求/响应
// ============================================

export interface CreateEntryRequest {
  rawText: string
  entryDate: string // ISO date string
  childAge?: string
}

export interface EntryWithAnalysis {
  id: string
  rawText: string
  entryDate: Date
  childAge: string | null
  createdAt: Date
  factCard: {
    id: string
    oneLine: string
    events: Event[]
    tags: string[]
    missingInfo: string[]
    ageBucket: string | null
    expertAnalysis: {
      interpretation: string
      suggestions: Array<{
        category: string
        content: string
        priority: string
      }>
      patterns: Array<{
        pattern: string
        evidence: string[]
      }> | null
      riskFlags: string[]
    } | null
  } | null
}

// ============================================
// Agent 类型
// ============================================

export type AgentName = 'recorder' | 'expert' | 'values' | 'orchestrator' | 'chat' | 'mentor'

export interface AgentConfig {
  name: AgentName
  model: string
  maxTokens: number
  temperature: number
}

// ============================================
// 检索相关
// ============================================

export interface RetrievalContext {
  recentEntries: EntryWithAnalysis[]
  similarEntries: EntryWithAnalysis[]
  strategies: Array<{
    category: string
    description: string
    conditions: string | null
  }>
}

// ============================================
// 育儿问题追踪
// ============================================

export type QuestionStage = 'observing' | 'experimenting' | 'internalized'

export interface QuestionObservation {
  id: string
  questionId: string
  content: string
  source: 'entry' | 'manual'
  entryId: string | null
  createdAt: Date
}

export interface QuestionDiscussion {
  id: string
  questionId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: Date
}

export interface ParentingQuestion {
  id: string
  question: string
  stage: QuestionStage
  currentConclusion: string | null
  conclusionSource: 'ai' | 'user' | 'ai_modified' | null
  displayOrder: number
  relatedEntryIds: string[]
  createdAt: Date
  updatedAt: Date
  observations?: QuestionObservation[]
  discussions?: QuestionDiscussion[]
}

// ============================================
// 递归上下文系统
// ============================================

// 可编辑项（用于 DailyDigest 的各个字段）
export interface EditableItem {
  id: string
  content: string
  source: 'ai' | 'user'
  deleted: boolean
}

// 开放问题项
export interface OpenQuestion {
  id: string
  content: string
  resolved: boolean
}

// 每日沉淀
export interface DailyDigest {
  id: string
  date: Date
  recordSummary: EditableItem[]
  aiAnalysis: EditableItem[]
  discussionPoints: EditableItem[]
  conclusions: EditableItem[]
  openQuestions: OpenQuestion[]
  entryIds: string[]
  relatedDigestIds: string[]
  learningIds: string[]
  createdAt: Date
  updatedAt: Date
}

// 认知状态
export type LearningStatus = 'hypothesis' | 'validated' | 'invalidated'

// 证据项
export interface EvidenceItem {
  id: string
  date: string
  type: 'observation' | 'experiment' | 'discussion'
  content: string
  entryId?: string
  digestId?: string
}

// 认知
export interface Learning {
  id: string
  topic: string
  insight: string
  status: LearningStatus
  confidence: number
  evidence: EvidenceItem[]
  invalidReason: string | null
  source: 'ai' | 'user'
  sourceDigestId: string | null
  createdAt: Date
  updatedAt: Date
}

// API 请求类型
export interface CreateDailyDigestRequest {
  date: string // ISO date string
  recordSummary?: EditableItem[]
  aiAnalysis?: EditableItem[]
  discussionPoints?: EditableItem[]
  conclusions?: EditableItem[]
  openQuestions?: OpenQuestion[]
  entryIds?: string[]
}

export interface UpdateDailyDigestRequest {
  recordSummary?: EditableItem[]
  aiAnalysis?: EditableItem[]
  discussionPoints?: EditableItem[]
  conclusions?: EditableItem[]
  openQuestions?: OpenQuestion[]
  entryIds?: string[]
  relatedDigestIds?: string[]
  learningIds?: string[]
}

export interface CreateLearningRequest {
  topic: string
  insight: string
  status?: LearningStatus
  confidence?: number
  evidence?: EvidenceItem[]
  source?: 'ai' | 'user'
  sourceDigestId?: string
}

export interface UpdateLearningRequest {
  topic?: string
  insight?: string
  status?: LearningStatus
  confidence?: number
  evidence?: EvidenceItem[]
  invalidReason?: string
}
