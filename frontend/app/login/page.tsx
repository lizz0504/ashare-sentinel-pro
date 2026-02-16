'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '../utils/supabase'
import { Loader2, Mail, Lock, TrendingUp, BarChart3, Shield, Sparkles, ArrowRight } from 'lucide-react'

type AuthMode = 'login' | 'signup'

export default function LoginPage() {
  const router = useRouter()
  const supabase = useState(() => createClient())[0]
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      if (mode === 'signup') {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        })
        if (error) throw error
        setSuccess('注册成功！正在跳转到Dashboard...')
        // 注册成功后自动登录并跳转
        setTimeout(() => {
          router.push('/dashboard')
          router.refresh()
        }, 1000)
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error
        router.push('/dashboard')
        router.refresh()
      }
    } catch (err: any) {
      setError(err.message || '操作失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-12 bg-slate-950">
      {/* 左侧品牌区 - 桌面端占 4 列 (1/3) */}
      <div className="hidden lg:flex lg:col-span-4 relative overflow-hidden">
        {/* 深蓝渐变背景 */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900"></div>

        {/* 背景装饰网格 */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.1)_1px,transparent_1px)] bg-[size:60px_60px]"></div>
        </div>

        {/* 装饰性数据可视化元素 */}
        <svg className="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="50%" stopColor="#06b6d4" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
          </defs>
          {/* K线图装饰 */}
          <g transform="translate(60, 200)">
            <rect x="0" y="30" width="8" height="40" fill="url(#lineGradient)" opacity="0.6" />
            <line x1="4" y1="20" x2="4" y2="80" stroke="url(#lineGradient)" strokeWidth="1" opacity="0.4" />
            <rect x="20" y="10" width="8" height="60" fill="url(#lineGradient)" opacity="0.7" />
            <line x1="24" y1="5" x2="24" y2="75" stroke="url(#lineGradient)" strokeWidth="1" opacity="0.4" />
            <rect x="40" y="40" width="8" height="30" fill="#ef4444" opacity="0.5" />
            <line x1="44" y1="35" x2="44" y2="75" stroke="#ef4444" strokeWidth="1" opacity="0.3" />
            <rect x="60" y="20" width="8" height="50" fill="url(#lineGradient)" opacity="0.8" />
            <line x1="64" y1="10" x2="64" y2="75" stroke="url(#lineGradient)" strokeWidth="1" opacity="0.5" />
            <rect x="80" y="5" width="8" height="65" fill="url(#lineGradient)" opacity="0.9" />
            <line x1="84" y1="0" x2="84" y2="75" stroke="url(#lineGradient)" strokeWidth="1" opacity="0.6" />
          </g>
          {/* 趋势线 */}
          <path d="M 60 350 Q 120 300 180 320 T 300 280" stroke="url(#lineGradient)" strokeWidth="3" fill="none" opacity="0.4" />
        </svg>

        {/* 品牌内容 */}
        <div className="relative z-10 flex flex-col justify-center h-full px-8 xl:px-12">
          {/* Logo */}
          <div className="mb-6">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">AShare</span>
            </div>
            <div className="h-0.5 w-16 bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full"></div>
          </div>

          {/* Slogan */}
          <h1 className="text-3xl xl:text-4xl font-bold text-white mb-4 leading-tight">
            洞察 A 股底层逻辑
            <br />
            <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400 bg-clip-text text-transparent">
              赋能理性投资
            </span>
          </h1>

          <p className="text-slate-400 text-base mb-10 leading-relaxed">
            基于多源数据融合的智能投研平台
          </p>

          {/* 特性卡片 - 纵向排列 */}
          <div className="space-y-3">
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-3.5">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-blue-400 flex-shrink-0" />
                <div>
                  <div className="text-sm font-medium text-slate-300">数据安全</div>
                  <div className="text-xs text-slate-500">企业级加密</div>
                </div>
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-3.5">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-cyan-400 flex-shrink-0" />
                <div>
                  <div className="text-sm font-medium text-slate-300">深度分析</div>
                  <div className="text-xs text-slate-500">AI 投委会</div>
                </div>
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-3.5">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                <div>
                  <div className="text-sm font-medium text-slate-300">实时监控</div>
                  <div className="text-xs text-slate-500">7x24 服务</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 底部信息 */}
        <div className="absolute bottom-6 left-8 xl:left-12 text-slate-500 text-xs">
          V1.4 · 智能投研决策系统
        </div>
      </div>

      {/* 右侧表单区 - 桌面端占 8 列 (2/3) */}
      <div className="col-span-1 lg:col-span-8 flex items-center justify-center p-6 lg:p-12 bg-slate-950 relative">
        {/* 背景装饰 */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"></div>
          <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"></div>
        </div>

        {/* 表单容器 */}
        <div className="relative w-full max-w-md">
          {/* 移动端 Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">LofX Capital</span>
          </div>

          {/* 表单卡片 */}
          <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl p-8">
            {/* 标题 */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">
                {mode === 'login' ? '欢迎回来' : '创建账户'}
              </h2>
              <p className="text-slate-400">
                {mode === 'login' ? '登录以访问您的投资Dashboard' : '开始您的智能投研之旅'}
              </p>
            </div>

            {/* 表单 */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* 邮箱输入 */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  邮箱地址
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    required
                    className="w-full pl-11 pr-4 py-3 bg-slate-950/50 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  />
                </div>
              </div>

              {/* 密码输入 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-slate-300">
                    密码
                  </label>
                  {mode === 'login' && (
                    <button
                      type="button"
                      className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      忘记密码?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="•••••••••"
                    required
                    minLength={6}
                    className="w-full pl-11 pr-4 py-3 bg-slate-950/50 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  />
                </div>
              </div>

              {/* 错误提示 */}
              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              {/* 成功提示 */}
              {success && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                  <p className="text-sm text-emerald-400">{success}</p>
                </div>
              )}

              {/* 提交按钮 */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    {mode === 'login' ? '登录中...' : '注册中...'}
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    {mode === 'login' ? '登录账户' : '创建账户'}
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </span>
                )}
              </button>
            </form>

            {/* 分割线 */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-700"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-slate-900 text-slate-500">或</span>
              </div>
            </div>

            {/* 切换登录/注册 */}
            <button
              type="button"
              onClick={() => {
                setMode(mode === 'login' ? 'signup' : 'login')
                setError(null)
                setSuccess(null)
              }}
              className="w-full py-3 bg-slate-800/50 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white rounded-xl transition-all font-medium"
            >
              {mode === 'login' ? '还没有账号？立即注册' : '已有账号？直接登录'}
            </button>
          </div>

          {/* 移动端底部信息 */}
          <div className="lg:hidden mt-6 text-center text-slate-600 text-xs">
            LofX Capital Pro V1.4 · 智能投研决策系统
          </div>
        </div>
      </div>
    </div>
  )
}
