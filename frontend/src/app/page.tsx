// frontend/src/app/login/page.tsx
"use client"

import { useState } from "react"
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

  async function loginGoogle() {
    setErr(null)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/` }
    })
    if (error) setErr(error.message)
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
      if (mode === "signin") window.location.href = "/"
      else alert("Conta criada. Verifica o teu email para confirmar.")
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col">
      {/* Header limpo e moderno */}
      <header className="w-full">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">JR</span>
            </div>
            <span className="font-semibold text-gray-900 text-lg">VigiaCrypto</span>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          {/* Card moderno */}
          <div className="rounded-2xl bg-white shadow-xl border border-gray-200 p-8">
            <div className="flex flex-col items-center text-center space-y-3 mb-8">
              <div className="h-12 w-12 rounded-xl bg-blue-600 flex items-center justify-center">
                <span className="text-white font-bold text-lg">🔍</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">Bem-vindo</h1>
              <p className="text-sm text-gray-600">
                {mode === "signin" ? "Entra na tua conta" : "Cria uma nova conta"}
              </p>
            </div>

            {/* Botão Google elegante */}
            <button
              onClick={loginGoogle}
              className="w-full inline-flex items-center justify-center gap-3 rounded-xl bg-white text-gray-700 font-medium py-3.5 hover:bg-gray-50 transition-all border border-gray-300 shadow-sm hover:shadow-md mb-6"
            >
              <GoogleLogo />
              Continuar com Google
            </button>

            {/* Separador */}
            <div className="flex items-center gap-3 mb-6">
              <div className="h-px flex-1 bg-gray-300" />
              <span className="text-sm text-gray-500">ou</span>
              <div className="h-px flex-1 bg-gray-300" />
            </div>

            {/* Toggle email/password */}
            {!showEmail ? (
              <button
                onClick={() => setShowEmail(true)}
                className="w-full text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors py-2"
              >
                Usar email e password
              </button>
            ) : (
              <form onSubmit={handleEmail} className="space-y-4">
                <div>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="Endereço de email"
                    required
                    className="w-full rounded-xl bg-gray-50 text-gray-900 placeholder-gray-500 px-4 py-3.5 outline-none border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  />
                </div>
                <div>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Palavra-passe"
                    required
                    className="w-full rounded-xl bg-gray-50 text-gray-900 placeholder-gray-500 px-4 py-3.5 outline-none border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  />
                </div>
                <button
                  disabled={loading}
                  className="w-full rounded-xl bg-blue-600 text-white font-semibold py-3.5 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md"
                >
                  {mode === "signin" 
                    ? (loading ? "A entrar..." : "Entrar") 
                    : (loading ? "A criar conta..." : "Criar conta")
                  }
                </button>
                
                <div className="text-sm text-gray-600 text-center pt-2">
                  {mode === "signin" ? (
                    <>Não tens conta?{" "}
                      <button 
                        type="button" 
                        onClick={() => setMode("signup")}
                        className="text-blue-600 hover:text-blue-700 font-medium underline"
                      >
                        Regista-te
                      </button>
                    </>
                  ) : (
                    <>Já tens conta?{" "}
                      <button 
                        type="button" 
                        onClick={() => setMode("signin")}
                        className="text-blue-600 hover:text-blue-700 font-medium underline"
                      >
                        Entrar
                      </button>
                    </>
                  )}
                </div>
              </form>
            )}

            {err && (
              <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200">
                <p className="text-red-700 text-sm text-center">{err}</p>
              </div>
            )}
          </div>

          {/* Rodapé */}
          <p className="text-xs text-center text-gray-500 mt-8">
            © {new Date().getFullYear()} VigiaCrypto · Todos os direitos reservados
          </p>
        </div>
      </main>
    </div>
  )
}