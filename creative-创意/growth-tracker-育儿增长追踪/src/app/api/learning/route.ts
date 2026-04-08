import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

// GET /api/learning - 获取认知列表
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status') // hypothesis | validated | invalidated
    const topic = searchParams.get('topic')
    const limit = parseInt(searchParams.get('limit') || '50')
    const offset = parseInt(searchParams.get('offset') || '0')

    const where: Record<string, unknown> = {}
    if (status) where.status = status
    if (topic) where.topic = topic

    const learnings = await prisma.learning.findMany({
      where,
      orderBy: [
        { status: 'asc' }, // hypothesis -> validated -> invalidated
        { confidence: 'desc' },
        { updatedAt: 'desc' }
      ],
      take: limit,
      skip: offset,
    })

    return NextResponse.json(learnings)
  } catch (error) {
    console.error('获取认知列表失败:', error)
    return NextResponse.json(
      { error: '获取认知列表失败' },
      { status: 500 }
    )
  }
}

// POST /api/learning - 创建新认知
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { topic, insight, status, confidence, evidence, source, sourceDigestId } = body

    if (!topic || !insight) {
      return NextResponse.json(
        { error: '主题和认知内容是必填项' },
        { status: 400 }
      )
    }

    const learning = await prisma.learning.create({
      data: {
        topic,
        insight,
        status: status || 'hypothesis',
        confidence: confidence ?? 0.5,
        evidence: evidence || [],
        source: source || 'user',
        sourceDigestId: sourceDigestId || null,
      }
    })

    return NextResponse.json(learning, { status: 201 })
  } catch (error) {
    console.error('创建认知失败:', error)
    return NextResponse.json(
      { error: '创建认知失败' },
      { status: 500 }
    )
  }
}
