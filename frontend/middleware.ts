// frontend/middleware.ts
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()

  const supabase = createMiddlewareClient({ req, res })
  await supabase.auth.getSession()

  return res
}

export const config = {
  matcher: [
    // Protege tudo exceto login e assets públicos
    '/((?!api|_next/static|_next/image|favicon.ico|login).*)',
  ],
}
