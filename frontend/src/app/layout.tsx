// frontend/src/app/layout.tsx
import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { ChatHistoryProvider } from '@/lib/ChatHistoryProvider';

export const metadata: Metadata = {
  title: 'joseruao.com',
  description: 'Vigia Crypto',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <body className="flex min-h-screen bg-white text-black antialiased">
        <ChatHistoryProvider>
          <Sidebar />
          <div className="flex-1 flex flex-col">{children}</div>
        </ChatHistoryProvider>
      </body>
    </html>
  );
}