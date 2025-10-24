// frontend/src/app/login/page.tsx
"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabaseClient"

function GoogleLogo() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" className="w-5 h-5">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.6 32.6 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20c10 0 19-7.3 19-20 0-1.2-.1-2.3-.4-3.5z"/>
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 16.5 18.9 14 24 14c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6 29.3 4 24 4 15.4 4 8.2 8.9 6.3 14.7z"/>
      <path fill="#4CAF50" d="M24 44c5.1 0 9.9-1.9 13.4-5.1l-6.2-5.1C29.1 35.6 26.7 36 24 36c-5.2 0-9.6-3.4-11.2-8.1l-6.5 5.1C8.2 39.1 15.4 44 24 44z"/>
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-1.1 3.3-3.6 6-6.7 7.3l6.2 5.1C37.1 37.9 40 31.8 40 24c0-1.2-.1-2.3-.4-3.5z"/>
    </svg>
  )
}

export default function LoginPage() {
  const [showEmail, setShowEmail] = useState(false)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [mode, setMode] = useState<"signin"|"signup">("signin")
  const router = useRouter()

  // Redireciona se já estiver autenticado
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.push("/")
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: string, session: any) => {
      if (session) {
        router.push("/")
      }
    })

    return () => subscription.unsubscribe()
  }, [router])

  async function loginGoogle() {
    setErr(null)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { 
        redirectTo: `https://joseruao.vercel.app/auth/callback`,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        }
      }
    })
    if (error) {
      setErr(error.message)
      console.error('Login error:', error)
    }
  }

  async function handleEmail(e: React.FormEvent) {
    e.preventDefault()
    setErr(null); setLoading(true)
    const fn = mode === "signin"
      ? supabase.auth.signInWithPassword({ email, password })
      : supabase.auth.signUp({ email, password })
    const { error } = await fn
    setLoading(false)
    if (error) setErr(error.message)
    else {
      if (mode === "signin") {
        router.push("/")
      } else {
        alert("Conta criada. Verifica o teu email para confirmar.")
      }
    }
  }

  return (
    <div className="min-h-screen bg-white text-black flex flex-col">
      {/* header minimal estilo limpo */}
      <header className="w-full border-b border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded bg-blue-600" />
            <span className="font-semibold tracking-tight">joseruao.com</span>
          </div>
          <span className="text-xs text-gray-500">Vigia Crypto</span>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          {/* card central limpo */}
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-8">
            <div className="flex flex-col items-center text-center space-y-2 mb-6">
              <h1 className="text-2xl font-semibold">Entrar no Vigia Crypto</h1>
              <p className="text-sm text-gray-600">Usa a tua conta Google ou email.</p>
            </div>

            {/* botão Google */}
            <button
              onClick={loginGoogle}
              className="w-full inline-flex items-center justify-center gap-3 rounded-lg bg-white text-gray-700 font-medium py-3 hover:bg-gray-50 transition border border-gray-300 shadow-sm"
            >
              <GoogleLogo />
              Continuar com Google
            </button>

            {/* separador */}
            <div className="flex items-center gap-3 my-6">
              <div className="h-px flex-1 bg-gray-200" />
              <span className="text-xs text-gray-500">ou</span>
              <div className="h-px flex-1 bg-gray-200" />
            </div>

            {/* toggle email */}
            {!showEmail ? (
              <button
                onClick={() => setShowEmail(true)}
                className="w-full text-sm text-blue-600 hover:text-blue-700 transition font-medium"
              >
                Usar email e password
              </button>
            ) : (
              <form onSubmit={handleEmail} className="space-y-4">
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="Email"
                  required
                  className="w-full rounded-lg bg-gray-50 text-gray-900 placeholder-gray-500 px-4 py-3 outline-none border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                />
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Password"
                  required
                  className="w-full rounded-lg bg-gray-50 text-gray-900 placeholder-gray-500 px-4 py-3 outline-none border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                />
                <button
                  disabled={loading}
                  className="w-full rounded-lg bg-blue-600 text-white font-semibold py-3 hover:bg-blue-700 disabled:opacity-60 transition-colors"
                >
                  {mode === "signin" ? (loading ? "A entrar…" : "Entrar") : (loading ? "A criar…" : "Criar conta")}
                </button>
                <div className="text-xs text-gray-600 text-center">
                  {mode === "signin" ? (
                    <>Ainda não tens conta?{" "}
                      <button type="button" onClick={() => setMode("signup")} className="text-blue-600 hover:text-blue-700 font-medium">
                        Criar conta
                      </button>
                    </>
                  ) : (
                    <>Já tens conta?{" "}
                      <button type="button" onClick={() => setMode("signin")} className="text-blue-600 hover:text-blue-700 font-medium">
                        Entrar
                      </button>
                    </>
                  )}
                </div>
              </form>
            )}

            {err && <p className="text-red-600 text-sm mt-4 text-center">{err}</p>}
          </div>

          {/* rodapé */}
          <p className="text-xs text-center text-gray-500 mt-6">
            © {new Date().getFullYear()} joseruao.com · Vigia Crypto
          </p>
        </div>
      </main>
    </div>
  )
}