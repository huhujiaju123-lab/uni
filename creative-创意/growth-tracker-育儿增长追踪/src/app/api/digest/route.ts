import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

// GET /api/digest - 获取每日沉淀列表
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '30')
    const offset = parseInt(searchParams.get('offset') || '0')

    const digests = await prisma.dailyDigest.findMany({
      orderBy: { date: 'desc' },
      take: limit,
      skip: offset,
    })

    return NextResponse.json(digests)
  } catch (error) {
    console.error('获取每日沉淀列表失败:', error)
    return NextResponse.json(
      { error: '获取每日沉淀列表失败' },
      { status: 500 }
    )
  }
}

// POST /api/digest - 创建新的每日沉淀
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { date, recordSummary, aiAnalysis, discussionPoints, conclusions, openQuestions, entryIds } = body

    if (!date) {
      return NextResponse.json(
        { error: '日期是必填项' },
        { status: 400 }
      )
    }

    // 检查是否已存在该日期的沉淀
    const existingDigest = await prisma.dailyDigest.findUnique({
      where: { date: new Date(date) }
    })

    if (existingDigest) {
      return NextResponse.json(
        { error: '该日期的沉淀已存在，请使用更新接口' },
        { status: 409 }
      )
    }

    const digest = await prisma.dailyDigest.create({
      data: {
        date: new Date(date),
        recordSummary: recordSummary || [],
        aiAnalysis: aiAnalysis || [],
        discussionPoints: discussionPoints || [],
        conclusions: conclusions || [],
        openQuestions: openQuestions || [],
        entryIds: entryIds || [],
        relatedDigestIds: [],
        learningIds: [],
      }
    })

    return NextResponse.json(digest, { status: 201 })
  } catch (error) {
    console.error('创建每日沉淀失败:', error)
    return NextResponse.json(
      { error: '创建每日沉淀失败' },
      { status: 500 }
    )
  }
}
