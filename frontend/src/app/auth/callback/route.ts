// app/auth/callback/route.ts
import { cookies } from 'next/headers'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')

  if (!code) {
    return NextResponse.redirect(`${requestUrl.origin}/login`)
  }

  const supabase = createRouteHandlerClient({ cookies })
  await supabase.auth.exchangeCodeForSession(code)

  // Redireciona após login — podes trocar para /dashboard, etc.
  return NextResponse.redirect(`${requestUrl.origin}/`)
}
