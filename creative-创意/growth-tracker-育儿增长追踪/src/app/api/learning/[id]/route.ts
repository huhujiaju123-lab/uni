import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

interface RouteParams {
  params: Promise<{ id: string }>
}

// GET /api/learning/[id] - 获取指定认知
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params

    const learning = await prisma.learning.findUnique({
      where: { id }
    })

    if (!learning) {
      return NextResponse.json(
        { error: '未找到该认知' },
        { status: 404 }
      )
    }

    return NextResponse.json(learning)
  } catch (error) {
    console.error('获取认知失败:', error)
    return NextResponse.json(
      { error: '获取认知失败' },
      { status: 500 }
    )
  }
}

// PUT /api/learning/[id] - 更新认知
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params
    const body = await request.json()

    const { topic, insight, status, confidence, evidence, invalidReason } = body

    // 构建更新数据
    const updateData: Record<string, unknown> = {}
    if (topic !== undefined) updateData.topic = topic
    if (insight !== undefined) updateData.insight = insight
    if (status !== undefined) updateData.status = status
    if (confidence !== undefined) updateData.confidence = confidence
    if (evidence !== undefined) updateData.evidence = evidence
    if (invalidReason !== undefined) updateData.invalidReason = invalidReason

    const learning = await prisma.learning.update({
      where: { id },
      data: updateData
    })

    return NextResponse.json(learning)
  } catch (error) {
    console.error('更新认知失败:', error)
    return NextResponse.json(
      { error: '更新认知失败' },
      { status: 500 }
    )
  }
}

// DELETE /api/learning/[id] - 删除认知
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params

    await prisma.learning.delete({
      where: { id }
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('删除认知失败:', error)
    return NextResponse.json(
      { error: '删除认知失败' },
      { status: 500 }
    )
  }
}

// PATCH /api/learning/[id] - 部分更新（用于快速操作如升级/降级状态）
export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params
    const body = await request.json()
    const { action, ...data } = body

    let updateData: Record<string, unknown> = {}

    switch (action) {
      case 'upgrade':
        // 从 hypothesis 升级到 validated
        updateData = { status: 'validated' }
        break
      case 'downgrade':
        // 从 validated 降级到 hypothesis
        updateData = { status: 'hypothesis' }
        break
      case 'invalidate':
        // 标记为已否定
        updateData = {
          status: 'invalidated',
          invalidReason: data.invalidReason || null
        }
        break
      case 'restore':
        // 从 invalidated 恢复到 hypothesis
        updateData = {
          status: 'hypothesis',
          invalidReason: null
        }
        break
      case 'updateConfidence':
        // 更新信心度
        updateData = { confidence: data.confidence }
        break
      case 'addEvidence':
        // 添加证据
        const learning = await prisma.learning.findUnique({ where: { id } })
        if (learning) {
          const currentEvidence = learning.evidence as unknown[]
          updateData = {
            evidence: [...currentEvidence, data.evidence],
            // 添加证据时自动增加信心度（最高到0.9）
            confidence: Math.min((learning.confidence || 0.5) + 0.1, 0.9)
          }
        }
        break
      default:
        // 普通部分更新
        updateData = data
    }

    const updatedLearning = await prisma.learning.update({
      where: { id },
      data: updateData
    })

    return NextResponse.json(updatedLearning)
  } catch (error) {
    console.error('部分更新认知失败:', error)
    return NextResponse.json(
      { error: '部分更新认知失败' },
      { status: 500 }
    )
  }
}
