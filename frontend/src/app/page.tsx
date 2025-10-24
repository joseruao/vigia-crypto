// frontend/src/app/page.tsx
import { ChatWindow } from '@/components/ChatWindow'
import { PredictionsPanel } from '@/components/PredictionsPanel'

export default function Home() {
  return (
    <>
      <ChatWindow />
      <PredictionsPanel />
    </>
  )
}