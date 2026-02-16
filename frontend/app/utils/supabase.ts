// ============================================
// Supabase 客户端配置
// ============================================

import { createBrowserClient } from '@supabase/ssr'

/**
 * 创建客户端组件用的 Supabase 客户端
 * 用于在 React Client Components 中使用
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
