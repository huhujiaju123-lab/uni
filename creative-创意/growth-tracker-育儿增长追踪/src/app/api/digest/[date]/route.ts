import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

interface RouteParams {
  params: Promise<{ date: string }>
}

// GET /api/digest/[date] - 获取指定日期的沉淀
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { date } = await params
    const dateObj = new Date(date)

    const digest = await prisma.dailyDigest.findUnique({
      where: { date: dateObj }
    })

    if (!digest) {
      return NextResponse.json(
        { error: '未找到该日期的沉淀' },
        { status: 404 }
      )
    }

    return NextResponse.json(digest)
  } catch (error) {
    console.error('获取每日沉淀失败:', error)
    return NextResponse.json(
      { error: '获取每日沉淀失败' },
      { status: 500 }
    )
  }
}

// PUT /api/digest/[date] - 更新指定日期的沉淀
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const { date } = await params
    const dateObj = new Date(date)
    const body = await request.json()

    const {
      recordSummary,
      aiAnalysis,
      discussionPoints,
      conclusions,
      openQuestions,
      entryIds,
      relatedDigestIds,
      learningIds
    } = body

    // 构建更新数据
    const updateData: Record<string, unknown> = {}
    if (recordSummary !== undefined) updateData.recordSummary = recordSummary
    if (aiAnalysis !== undefined) updateData.aiAnalysis = aiAnalysis
    if (discussionPoints !== undefined) updateData.discussionPoints = discussionPoints
    if (conclusions !== undefined) updateData.conclusions = conclusions
    if (openQuestions !== undefined) updateData.openQuestions = openQuestions
    if (entryIds !== undefined) updateData.entryIds = entryIds
    if (relatedDigestIds !== undefined) updateData.relatedDigestIds = relatedDigestIds
    if (learningIds !== undefined) updateData.learningIds = learningIds

    const digest = await prisma.dailyDigest.update({
      where: { date: dateObj },
      data: updateData
    })

    return NextResponse.json(digest)
  } catch (error) {
    console.error('更新每日沉淀失败:', error)
    return NextResponse.json(
      { error: '更新每日沉淀失败' },
      { status: 500 }
    )
  }
}

// DELETE /api/digest/[date] - 删除指定日期的沉淀
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const { date } = await params
    const dateObj = new Date(date)

    await prisma.dailyDigest.delete({
      where: { date: dateObj }
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('删除每日沉淀失败:', error)
    return NextResponse.json(
      { error: '删除每日沉淀失败' },
      { status: 500 }
    )
  }
}
