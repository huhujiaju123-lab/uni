import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '成长日记 - 育儿记录助手',
  description: 'AI驱动的智能育儿日志与成长分析系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="h-screen overflow-hidden bg-gray-100">
        {children}
      </body>
    </html>
  )
}
