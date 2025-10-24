// frontend/src/app/auth/callback/page.tsx
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'

export default function AuthCallback() {
  const router = useRouter()

  useEffect(() => {
    // Verifica se já está autenticado
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      
      if (session) {
        // Se tem session, redireciona para a página principal
        router.push('/')
      } else {
        // Se não tem session, espera pelo evento de auth
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
          (event: string, session: any) => {
            if (event === 'SIGNED_IN' && session) {
              router.push('/')
            }
          }
        )

        // Timeout de segurança
        setTimeout(() => {
          subscription.unsubscribe()
          router.push('/')
        }, 5000)
      }
    }

    checkAuth()
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-lg">
        A processar login... Se não redirecionar,{' '}
        <a href="/" className="text-blue-600 underline">
          clica aqui
        </a>
      </div>
    </div>
  )
}