'use client'

import type { ParentingQuestion, QuestionStage } from '@/lib/types'

interface ProblemCardProps {
  question: ParentingQuestion
  isSelected: boolean
  onClick: () => void
}

const stageConfig: Record<QuestionStage, { icon: string; label: string; bgColor: string; borderColor: string }> = {
  observing: {
    icon: '🔴',
    label: '观察期',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200 hover:border-red-300',
  },
  experimenting: {
    icon: '🟡',
    label: '实验期',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200 hover:border-yellow-300',
  },
  internalized: {
    icon: '🟢',
    label: '已内化',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200 hover:border-green-300',
  },
}

export function ProblemCard({ question, isSelected, onClick }: ProblemCardProps) {
  const config = stageConfig[question.stage]

  return (
    <button
      onClick={onClick}
      className={`
        w-full p-3 rounded-lg border-2 text-left transition-all cursor-pointer
        ${config.bgColor} ${config.borderColor}
        ${isSelected ? 'ring-2 ring-blue-500 ring-offset-1' : ''}
      `}
    >
      <div className="flex items-start gap-2">
        <span className="text-sm flex-shrink-0">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 line-clamp-2">
            {question.question}
          </p>
          <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
            <span>{config.label}</span>
            {question.observations && question.observations.length > 0 && (
              <span>· {question.observations.length} 条观察</span>
            )}
          </div>
        </div>
      </div>
    </button>
  )
}
