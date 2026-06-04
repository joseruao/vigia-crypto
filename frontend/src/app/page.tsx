// frontend/src/app/page.tsx
import { ChatWindow } from '@/components/ChatWindow'
import { PredictionsPanel } from '@/components/PredictionsPanel'
import { Top100Panel } from '@/components/Top100Panel'

export default function Home() {
  return (
    <>
      <ChatWindow />
      <PredictionsPanel />
      <Top100Panel />
    </>
  )
}
