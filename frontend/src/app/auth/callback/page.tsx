'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export default function Callback() {
  const router = useRouter()

  useEffect(() => {
    const checkSession = async () => {
      const {
        data: { session },
        error
      } = await supabase.auth.getSession()

      if (session) {
        router.push('/')
      } else {
        // Força revalidação da sessão — importante para cookies cross-domain
        const { data: { user }, error } = await supabase.auth.getUser()

        if (user) {
          router.push('/')
        } else {
          router.push('/login')
        }
      }
    }

    checkSession()
  }, [router])

  return <p className="p-6 text-sm">A processar login...</p>
}
