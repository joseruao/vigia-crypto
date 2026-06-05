// frontend/src/app/page.tsx
import { ChatWindow } from '@/components/ChatWindow'
import { IntelPanel } from '@/components/IntelPanel'

export default function Home() {
  return (
    <>
      <ChatWindow />
      <IntelPanel />
    </>
  )
}
