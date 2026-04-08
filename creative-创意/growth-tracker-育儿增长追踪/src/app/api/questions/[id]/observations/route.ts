import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

interface RouteParams {
  params: Promise<{ id: string }>
}

// POST /api/questions/[id]/observations - 添加观察记录
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params
    const body = await request.json()
    const { content, entryId } = body

    if (!content || typeof content !== 'string') {
      return NextResponse.json(
        { success: false, error: 'Content is required' },
        { status: 400 }
      )
    }

    // 验证问题存在
    const question = await prisma.parentingQuestion.findUnique({
      where: { id },
    })

    if (!question) {
      return NextResponse.json(
        { success: false, error: 'Question not found' },
        { status: 404 }
      )
    }

    // 创建观察记录
    const observation = await prisma.questionObservation.create({
      data: {
        questionId: id,
        content: content.trim(),
        source: entryId ? 'entry' : 'manual',
        entryId: entryId || null,
      },
    })

    // 检查是否需要更新阶段
    // 如果观察记录达到 3 条且当前是观察期，考虑提示用户
    const observationCount = await prisma.questionObservation.count({
      where: { questionId: id },
    })

    let stageUpdate = null
    if (question.stage === 'observing' && observationCount >= 3) {
      // 检查内容是否包含"尝试"类关键词
      const experimentKeywords = ['试了', '尝试', '试着', '实验', '测试']
      const contentHasKeyword = experimentKeywords.some((keyword) =>
        content.includes(keyword)
      )
      const historyHasKeyword = await checkRecentObservationsForKeywords(
        id,
        experimentKeywords
      )
      const hasExperimentContent = contentHasKeyword || historyHasKeyword

      if (hasExperimentContent) {
        stageUpdate = 'experimenting'
        await prisma.parentingQuestion.update({
          where: { id },
          data: { stage: 'experimenting' },
        })
      }
    }

    return NextResponse.json({
      success: true,
      observation,
      stageUpdate,
    })
  } catch (error) {
    console.error('Failed to add observation:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to add observation' },
      { status: 500 }
    )
  }
}

// 检查最近的观察记录是否包含关键词
async function checkRecentObservationsForKeywords(
  questionId: string,
  keywords: string[]
): Promise<boolean> {
  const recentObservations = await prisma.questionObservation.findMany({
    where: { questionId },
    orderBy: { createdAt: 'desc' },
    take: 5,
    select: { content: true },
  })

  return recentObservations.some((obs) =>
    keywords.some((keyword) => obs.content.includes(keyword))
  )
}
