import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

interface RouteParams {
  params: Promise<{ id: string }>
}

// GET /api/questions/[id] - 获取问题详情
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params

    const question = await prisma.parentingQuestion.findUnique({
      where: { id },
      include: {
        observations: {
          orderBy: { createdAt: 'desc' },
        },
        discussions: {
          orderBy: { createdAt: 'asc' },
        },
      },
    })

    if (!question) {
      return NextResponse.json(
        { success: false, error: 'Question not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({
      success: true,
      question,
    })
  } catch (error) {
    console.error('Failed to fetch question:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch question' },
      { status: 500 }
    )
  }
}

// PATCH /api/questions/[id] - 更新问题
export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params
    const body = await request.json()

    const { question, stage, currentConclusion, conclusionSource, displayOrder } = body

    const updateData: Record<string, unknown> = {}

    if (question !== undefined) updateData.question = question
    if (stage !== undefined) updateData.stage = stage
    if (currentConclusion !== undefined) updateData.currentConclusion = currentConclusion
    if (conclusionSource !== undefined) updateData.conclusionSource = conclusionSource
    if (displayOrder !== undefined) updateData.displayOrder = displayOrder

    const updatedQuestion = await prisma.parentingQuestion.update({
      where: { id },
      data: updateData,
      include: {
        observations: {
          orderBy: { createdAt: 'desc' },
        },
        discussions: {
          orderBy: { createdAt: 'asc' },
        },
      },
    })

    return NextResponse.json({
      success: true,
      question: updatedQuestion,
    })
  } catch (error) {
    console.error('Failed to update question:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to update question' },
      { status: 500 }
    )
  }
}

// DELETE /api/questions/[id] - 删除问题
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params

    await prisma.parentingQuestion.delete({
      where: { id },
    })

    return NextResponse.json({
      success: true,
    })
  } catch (error) {
    console.error('Failed to delete question:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to delete question' },
      { status: 500 }
    )
  }
}
