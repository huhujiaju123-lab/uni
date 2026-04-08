'use client'

interface RecursiveIconProps {
  className?: string
  size?: number
}

export function RecursiveIcon({ className = '', size = 24 }: RecursiveIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* 外层循环箭头 */}
      <path d="M12 3C7.03 3 3 7.03 3 12" />
      <path d="M3 12c0 4.97 4.03 9 9 9" />
      <path d="M12 21c4.97 0 9-4.03 9-9" />
      <path d="M21 12c0-4.97-4.03-9-9-9" />

      {/* 箭头头部 - 顺时针方向 */}
      <polyline points="8,1 12,3 8,5" />

      {/* 内层小循环 - 表示递归深度 */}
      <circle cx="12" cy="12" r="3" strokeWidth="1.5" />
      <path d="M12 9v0.5" strokeWidth="1.5" />
      <path d="M14.12 10.88l-0.35 0.35" strokeWidth="1.5" />
    </svg>
  )
}

// 简化版 - 螺旋递归
export function RecursiveSpiralIcon({ className = '', size = 24 }: RecursiveIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* 螺旋向内 - 代表递归积累 */}
      <path d="M12 2C6.48 2 2 6.48 2 12" />
      <path d="M2 12c0 5.52 4.48 10 10 10" />
      <path d="M12 22c4.42 0 8-3.58 8-8" />
      <path d="M20 14c0-3.31-2.69-6-6-6" />
      <path d="M14 8c-2.21 0-4 1.79-4 4" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />

      {/* 入口箭头 */}
      <polyline points="9,1 12,2 9,4" />
    </svg>
  )
}

// 无限循环版 - 莫比乌斯环风格
export function RecursiveLoopIcon({ className = '', size = 24 }: RecursiveIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* 上半环 */}
      <path d="M4 12c0-4.4 3.6-8 8-8s8 3.6 8 8" />
      {/* 下半环 - 内层 */}
      <path d="M8 12c0 2.2 1.8 4 4 4s4-1.8 4-4" />
      {/* 连接线 - 形成递归感 */}
      <path d="M4 12h4" />
      <path d="M16 12h4" />
      {/* 箭头 */}
      <polyline points="18,9 20,12 18,15" />
      <polyline points="6,9 4,12 6,15" />
    </svg>
  )
}

// 默认导出最常用的版本
export default RecursiveSpiralIcon
