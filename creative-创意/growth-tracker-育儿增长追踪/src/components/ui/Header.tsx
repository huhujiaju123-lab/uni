'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BookOpen, MessageCircle, PenLine } from 'lucide-react'

export function Header() {
  const pathname = usePathname()

  return (
    <header className="flex items-center justify-between">
      <Link href="/" className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary-100">
          <BookOpen className="w-5 h-5 text-primary-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">成长日记</h1>
          <p className="text-sm text-gray-500">记录每一个珍贵的成长瞬间</p>
        </div>
      </Link>

      <nav className="flex items-center gap-2">
        <NavLink href="/" icon={<PenLine className="w-4 h-4" />} active={pathname === '/'}>
          记录
        </NavLink>
        <NavLink href="/chat" icon={<MessageCircle className="w-4 h-4" />} active={pathname === '/chat'}>
          聊聊
        </NavLink>
      </nav>
    </header>
  )
}

function NavLink({
  href,
  icon,
  active,
  children,
}: {
  href: string
  icon: React.ReactNode
  active: boolean
  children: React.ReactNode
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
        active
          ? 'bg-primary-100 text-primary-700'
          : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {icon}
      <span className="text-sm font-medium">{children}</span>
    </Link>
  )
}
