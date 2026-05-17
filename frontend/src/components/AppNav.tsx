'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { MessageSquare, BookOpen, Files, Cpu } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/', icon: MessageSquare, label: 'Chat' },
  { href: '/catalog', icon: BookOpen, label: 'Catalog' },
  { href: '/multi-doc', icon: Files, label: 'Multi-Doc' },
]

export function AppNav() {
  const pathname = usePathname()
  return (
    <nav className="w-16 flex flex-col items-center py-4 gap-2 border-r border-border bg-card">
      <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary mb-4">
        <Cpu className="w-5 h-5 text-primary-foreground" />
      </div>
      {navItems.map(({ href, icon: Icon, label }) => (
        <Link
          key={href}
          href={href}
          title={label}
          className={cn(
            'flex flex-col items-center gap-1 p-3 rounded-lg w-12 transition-colors',
            pathname === href
              ? 'bg-primary/20 text-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          )}
        >
          <Icon className="w-5 h-5" />
          <span className="text-[10px] font-medium">{label}</span>
        </Link>
      ))}
    </nav>
  )
}
