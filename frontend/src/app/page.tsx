"use client"

import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import { PredictionsPanel } from "@/components/PredictionsPanel"
import { ChatWindow } from "@/components/ChatWindow"

export default function Page() {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) window.location.href = "/login"
      else setReady(true)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => {
      if (!s) window.location.href = "/login"
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  if (!ready) return null

  return (
    <main className="relative min-h-screen bg-white">
      <PredictionsPanel />
      <div className="max-w-3xl mx-auto px-4 py-8">
        <ChatWindow />
      </div>
    </main>
  )
}
