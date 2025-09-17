import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'joseruao.io',
  description: 'Vigia Crypto',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <body className="flex min-h-screen bg-white text-black antialiased">
        <Sidebar />
        <div className="flex-1 flex flex-col">{children}</div>
      </body>
    </html>
  );
}
