import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  // 临时跳过认证检查
  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/login/:path*', '/'],
}
