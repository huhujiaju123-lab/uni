/**
 * 获取或创建日志对应的对话
 * GET /api/entry/[id]/conversation
 */

import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/db'

interface RouteParams {
  params: Promise<{ id: string }>
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { id: entryId } = await params

    // 查找日志
    const entry = await prisma.entry.findUnique({
      where: { id: entryId },
      include: {
        factCard: {
          include: {
            expertAnalysis: true
          }
        }
      }
    })

    if (!entry) {
      return NextResponse.json(
        { error: '日志不存在' },
        { status: 404 }
      )
    }

    // 查找或创建对话
    let conversation = await prisma.conversation.findFirst({
      where: { entryId },
      include: {
        messages: {
          orderBy: { createdAt: 'asc' }
        }
      }
    })

    if (!conversation) {
      // 创建新对话，并添加初始的 AI 分析作为第一条消息
      const analysis = entry.factCard?.expertAnalysis
      const factCard = entry.factCard

      let initialContent = ''
      if (factCard?.oneLine) {
        initialContent += `📝 记录摘要\n${factCard.oneLine}\n\n`
      }
      if (analysis?.interpretation) {
        initialContent += `🔍 专家解读\n${analysis.interpretation}\n\n`
      }
      if (analysis?.suggestions && Array.isArray(analysis.suggestions)) {
        initialContent += `💡 建议\n`
        ;(analysis.suggestions as Array<{ content: string }>).forEach((s, i) => {
          initialContent += `${i + 1}. ${s.content}\n`
        })
        initialContent += '\n'
      }
      initialContent += '有什么想继续讨论的吗？'

      conversation = await prisma.conversation.create({
        data: {
          entryId,
          title: factCard?.oneLine || entry.rawText.slice(0, 30),
          messages: {
            create: [
              {
                role: 'user',
                content: `我记录了：${entry.rawText}`,
              },
              {
                role: 'assistant',
                content: initialContent,
              }
            ]
          }
        },
        include: {
          messages: {
            orderBy: { createdAt: 'asc' }
          }
        }
      })
    }

    return NextResponse.json({
      success: true,
      conversation,
      entry: {
        id: entry.id,
        rawText: entry.rawText,
        entryDate: entry.entryDate,
        factCard: entry.factCard ? {
          oneLine: entry.factCard.oneLine,
          tags: entry.factCard.tags,
          expertAnalysis: entry.factCard.expertAnalysis
        } : null
      }
    })
  } catch (error) {
    console.error('获取日志对话失败:', error)
    return NextResponse.json(
      { error: '获取日志对话失败' },
      { status: 500 }
    )
  }
}
