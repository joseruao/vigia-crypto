// frontend/middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  // Verifica se tem session cookie (autenticação básica)
  const session = req.cookies.get('sb-access-token')
  
  // Se não está autenticado e tenta aceder a páginas protegidas, redireciona para login
  if (!session && req.nextUrl.pathname !== '/login') {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  // Se está autenticado e tenta aceder ao login, redireciona para a página principal
  if (session && req.nextUrl.pathname === '/login') {
    return NextResponse.redirect(new URL('/', req.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}