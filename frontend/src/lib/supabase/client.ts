/**
 * Supabase Client Configuration
 *
 * 单例模式的 Supabase 客户端，用于前端与 Supabase 的交互
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { Database } from '@/types/supabase'

// ============================================
// Environment Variables
// ============================================
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// ============================================
// Validation
// ============================================
if (!supabaseUrl) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_URL')
}

if (!supabaseAnonKey) {
  throw new Error('Missing env.NEXT_PUBLIC_SUPABASE_ANON_KEY')
}

// ============================================
// Singleton Pattern
// ============================================
/**
 * 全局单例实例缓存
 * 在浏览器端，确保只有一个 Supabase 客户端实例
 */
let globalForSupabase: SupabaseClient<Database> | undefined = undefined

/**
 * 获取 Supabase 客户端实例（单例模式）
 *
 * @returns Supabase 客户端实例
 *
 * @example
 * ```ts
 * import { supabase } from '@/lib/supabase/client'
 *
 * const { data, error } = await supabase
 *   .from('users')
 *   .select('*')
 * ```
 */
export const supabase = (() => {
  if (globalForSupabase) {
    return globalForSupabase
  }

  globalForSupabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
    auth: {
      // 自动刷新 token
      autoRefreshToken: true,
      // 检测会话变化
      detectSessionInUrl: true,
      // 会话持久化
      persistSession: true,
    },
  })

  return globalForSupabase
})()

/**
 * 类型导出
 * 可用于在其他文件中引用 Database 类型
 */
export type { Database }
