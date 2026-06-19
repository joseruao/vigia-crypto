// frontend/src/app/layout.tsx
import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'
import { ChatHistoryProvider } from '@/lib/ChatHistoryProvider'
import { LangProvider } from '@/lib/LangContext'

export const metadata: Metadata = {
  title: 'Vigia Crypto — On-chain Intelligence',
  description: 'AI trained on insider wallets, market maker flows and listing radar signals. Built by José Ruão.',
}

export const dynamic = 'force-dynamic'

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen bg-white text-black antialiased overflow-hidden" suppressHydrationWarning>
        <LangProvider>
          <ChatHistoryProvider>
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-y-auto">{children}</div>
          </ChatHistoryProvider>
        </LangProvider>
      </body>
    </html>
  )
}

