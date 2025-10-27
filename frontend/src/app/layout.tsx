// frontend/src/app/layout.tsx
import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'
import { ChatHistoryProvider } from '@/lib/ChatHistoryProvider'
// Se quiseres, podes remover completamente o supabase aqui enquanto debugas

export const metadata: Metadata = {
  title: 'joseruao.com',
  description: 'Vigia Crypto',
}

export const dynamic = 'force-dynamic'

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Durante debug: não lê sessão no servidor
  const session = null

  return (
    <html lang="pt">
      <body className="flex min-h-screen bg-white text-black antialiased">
        <ChatHistoryProvider>
          <Sidebar userSession={session} />
          <div className="flex-1 flex flex-col">{children}</div>
        </ChatHistoryProvider>
      </body>
    </html>
  )
}
