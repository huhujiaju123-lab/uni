/**
 * Entry API
 *
 * POST /api/entry - 创建新日志
 * GET /api/entry - 获取日志列表
 */

import { NextRequest, NextResponse } from 'next/server'
import { processEntry, listEntries } from '@/lib/agents'
import type { CreateEntryRequest } from '@/lib/types'

export async function POST(request: NextRequest) {
  try {
    const body: CreateEntryRequest = await request.json()

    // 验证必填字段
    if (!body.rawText || !body.entryDate) {
      return NextResponse.json(
        { error: '缺少必填字段: rawText, entryDate' },
        { status: 400 }
      )
    }

    // 处理日志
    const result = await processEntry(body)

    if (!result.success) {
      return NextResponse.json(
        { error: result.error, stages: result.stages },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      entry: result.entry,
      stages: result.stages,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error'
    console.error('POST /api/entry error:', message)
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)

    const limit = parseInt(searchParams.get('limit') || '20')
    const offset = parseInt(searchParams.get('offset') || '0')
    const tags = searchParams.get('tags')?.split(',').filter(Boolean)
    const startDate = searchParams.get('startDate')
    const endDate = searchParams.get('endDate')

    const entries = await listEntries({
      limit,
      offset,
      tags,
      startDate: startDate ? new Date(startDate) : undefined,
      endDate: endDate ? new Date(endDate) : undefined,
    })

    return NextResponse.json({
      success: true,
      entries,
      pagination: {
        limit,
        offset,
        hasMore: entries.length === limit,
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error'
    console.error('GET /api/entry error:', message)
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
