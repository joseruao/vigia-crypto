// frontend/middleware.ts
import { NextResponse } from 'next/server'

export const config = { matcher: [] }

export function middleware() {
  return NextResponse.next()
}
