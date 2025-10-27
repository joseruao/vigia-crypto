// frontend/src/components/Sidebar.tsx
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { Session } from '@supabase/auth-helpers-nextjs'

type Props = {
  userSession: Session | null
  /** enquanto estás a debuggar sem auth, deixa a false */
  authEnabled?: boolean
}

export function Sidebar({ userSession, authEnabled = false }: Props) {
  const pathname = usePathname()
  const router = useRouter()
  const supabase = createClientComponentClient()
  const [session, setSession] = useState<Session | null>(userSession)

  // Só subscreve ao estado se a auth estiver ativa
  useEffect(() => {
    if (!authEnabled) return
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub?.subscription?.unsubscribe()
  }, [authEnabled, supabase])

  const logout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

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

      {/* separador */}
      <div className="my-4 h-px bg-gray-200" />

      {/* Secção auth: só mostra se authEnabled=true */}
      {authEnabled ? (
        session ? (
          <div className="mt-auto">
            <div className="text-xs text-gray-600 mb-2 truncate">
              {session.user.email}
            </div>
            <button
              onClick={logout}
              className="w-full text-sm px-3 py-2 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 transition"
            >
              Sair
            </button>
          </div>
        ) : (
          <div className="mt-auto">
            <Link
              href="/login"
              className="block text-center text-sm px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
            >
              Entrar
            </Link>
          </div>
        )
      ) : null}
    </aside>
  )
}

