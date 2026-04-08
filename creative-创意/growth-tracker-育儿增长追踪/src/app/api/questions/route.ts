import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

// GET /api/questions - 获取问题列表
export async function GET() {
  try {
    const questions = await prisma.parentingQuestion.findMany({
      orderBy: [
        { displayOrder: 'asc' },
        { createdAt: 'desc' },
      ],
      include: {
        observations: {
          orderBy: { createdAt: 'desc' },
          take: 5,
        },
        discussions: {
          orderBy: { createdAt: 'desc' },
          take: 1,
        },
      },
    })

    return NextResponse.json({
      success: true,
      questions,
    })
  } catch (error) {
    console.error('Failed to fetch questions:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch questions' },
      { status: 500 }
    )
  }
}

// POST /api/questions - 创建新问题
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { question } = body

    if (!question || typeof question !== 'string') {
      return NextResponse.json(
        { success: false, error: 'Question is required' },
        { status: 400 }
      )
    }

    // 获取当前最大的 displayOrder
    const maxOrder = await prisma.parentingQuestion.aggregate({
      _max: { displayOrder: true },
    })

    const newQuestion = await prisma.parentingQuestion.create({
      data: {
        question: question.trim(),
        stage: 'observing',
        displayOrder: (maxOrder._max.displayOrder || 0) + 1,
      },
      include: {
        observations: true,
        discussions: true,
      },
    })

    return NextResponse.json({
      success: true,
      question: newQuestion,
    })
  } catch (error) {
    console.error('Failed to create question:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to create question' },
      { status: 500 }
    )
  }
}
