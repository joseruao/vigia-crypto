// frontend/src/components/Sidebar.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export function Sidebar() {
  const pathname = usePathname()

  const linkCls = (href: string) =>
    `block px-3 py-2 rounded-lg text-sm transition ${
      pathname === href
        ? 'bg-blue-600 text-white font-semibold'
        : 'text-gray-700 hover:bg-gray-100'
    }`

  return (
    <aside className="w-64 shrink-0 bg-gray-50 border-r border-gray-200 p-4 flex flex-col">
      <div className="mb-4">
        <h2 className="text-lg font-semibold leading-tight">Vigia Crypto</h2>
        <p className="text-xs text-gray-500">joseruao.com</p>
      </div>

      <nav className="space-y-2">
        <Link href="/" className={linkCls('/')}>Dashboard</Link>
        <Link href="/wallets" className={linkCls('/wallets')}>Wallets</Link>
        <Link href="/holdings" className={linkCls('/holdings')}>Holdings</Link>
      </nav>
    </aside>
  )
}
