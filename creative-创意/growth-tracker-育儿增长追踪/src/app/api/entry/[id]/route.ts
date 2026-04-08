/**
 * 单条日志 API
 * DELETE /api/entry/[id] - 删除日志
 */

import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

interface RouteParams {
  params: Promise<{ id: string }>
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params

    // 删除日志（关联的 FactCard、ExpertAnalysis、Conversation 会级联删除）
    await prisma.entry.delete({
      where: { id }
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('删除日志失败:', error)
    return NextResponse.json(
      { error: '删除日志失败' },
      { status: 500 }
    )
  }
}
