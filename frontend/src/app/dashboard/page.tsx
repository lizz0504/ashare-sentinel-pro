"use client"

import React, { useState, useEffect } from "react"
import { DecisionMatrix } from "@/components/dashboard/DecisionMatrix"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Sparkles } from "lucide-react"
import { addAnalysisRecord } from "@/lib/utils/analysisHistory"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004"
const DASHBOARD_CACHE_KEY = 'dashboard_analysis_cache'
const IC_MEETING_SHARE_KEY = 'ic_meeting_shared_data'

// 带超时控制的 fetch 函数
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 120000) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  try {
    console.log('[FETCH] Starting request to:', url)
    console.log('[FETCH] Options:', options)
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    })
    clearTimeout(id)
    console.log('[FETCH] Response received:', response.status)
    return response
  } catch (error) {
    clearTimeout(id)
    console.error('[FETCH] Request failed:', error)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('请求超时，AI 分析需要 40-60 秒，请稍后重试')
    }
    throw error
  }
}

interface ICMMeetingResult {
  symbol: string
  stock_name: string
  current_price: number
  technical_score: number
  fundamental_score: number
  verdict_chinese: string
  conviction_stars: string
  // NEW: AI投委会角色评分和Dashboard坐标
  agent_scores?: {
    cathie_wood?: { score: number; reasoning: string; verdict: string }
    nancy_pelosi?: { score: number; reasoning: string; verdict: string }
    warren_buffett?: { score: number; reasoning: string; verdict: string }
  }
  dashboard_position?: {
    final_x: number  // 基本面坐标 (Warren×0.6 + Nancy×0.4)
    final_y: number  // 趋势坐标 (Cathie×0.5 + Tech×0.5)
  }
}

export default function DashboardPage() {
  const [symbol, setSymbol] = useState("002050")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ICMMeetingResult | null>(null)

  // 从 localStorage 加载缓存数据
  useEffect(() => {
    try {
      const cached = localStorage.getItem(DASHBOARD_CACHE_KEY)
      if (cached) {
        const data = JSON.parse(cached)
        // 检查缓存是否在1小时内
        const oneHour = 60 * 60 * 1000
        if (Date.now() - data.timestamp < oneHour) {
          setResult(data.result)
          setSymbol(data.symbol)
        } else {
          localStorage.removeItem(DASHBOARD_CACHE_KEY)
        }
      }
    } catch (err) {
      console.error('Failed to load cache:', err)
    }
  }, [])

  // 保存结果到 localStorage（同时保存 Dashboard 缓存和 IC 投委会共享数据）
  useEffect(() => {
    if (result) {
      try {
        const cacheData = {
          result,
          symbol,
          timestamp: Date.now()
        }
        // 保存 Dashboard 缓存
        localStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(cacheData))
        // 同时保存完整的 IC meeting 数据供 IC 投委会页面使用
        localStorage.setItem(IC_MEETING_SHARE_KEY, JSON.stringify({
          ...result,
          timestamp: Date.now()
        }))
      } catch (err) {
        console.error('Failed to save cache:', err)
      }
    }
  }, [result, symbol])

  const handleAnalyze = async () => {
    if (!symbol.trim()) {
      setError("请输入股票代码")
      return
    }

    if (!/^\d{6}$/.test(symbol.trim())) {
      setError("无效的 A 股代码格式，必须是 6 位数字")
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetchWithTimeout(`${API_BASE}/api/v1/ic/meeting`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: symbol.trim() })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "未知错误" }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const data = await response.json()
      setResult(data)

      // 自动保存到复盘历史记录
      addAnalysisRecord({
        type: 'dashboard',
        symbol: data.symbol,
        stock_name: data.stock_name,
        current_price: data.current_price,
        technical_score: data.technical_score,
        fundamental_score: data.fundamental_score,
        verdict_chinese: data.verdict_chinese,
        conviction_stars: data.conviction_stars
      })
    } catch (err) {
      console.error("Analysis failed:", err)
      let errorMessage = "分析失败，请重试"

      if (err instanceof Error) {
        if (err.message.includes('Failed to fetch')) {
          errorMessage = "无法连接到后端服务，请确保后端正在运行 (http://localhost:8004)"
        } else if (err.message.includes('超时')) {
          errorMessage = err.message
        } else {
          errorMessage = err.message
        }
      }

      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearCache = () => {
    localStorage.removeItem(DASHBOARD_CACHE_KEY)
    localStorage.removeItem(IC_MEETING_SHARE_KEY)
    setResult(null)
    setError(null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-100">Dashboard</h1>
        <p className="mt-2 text-slate-400">投资决策分析仪表盘</p>
      </div>

      {/* Input Card */}
      <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100 text-lg">
            <Sparkles className="w-5 h-5 text-blue-400" />
            股票分析
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-center">
            <Input
              placeholder="股票代码 (如: 002050)"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={isLoading}
              className="bg-slate-950/50 border-slate-700 text-slate-100 max-w-xs"
              onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
            />
            <Button
              onClick={handleAnalyze}
              disabled={!symbol.trim() || isLoading}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-medium"
            >
              {isLoading ? (
                <React.Fragment>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  分析中...
                </React.Fragment>
              ) : (
                "开始分析"
              )}
            </Button>
            {result && !isLoading && (
              <Button
                onClick={handleClearCache}
                variant="outline"
                className="border-slate-700 text-slate-400 hover:bg-slate-800"
              >
                清除
              </Button>
            )}
          </div>

          {error && (
            <div className="mt-4 text-red-400 text-sm">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-8">
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="w-12 h-12 animate-spin text-blue-400" />
              <p className="text-slate-300">AI 投委会正在分析中，请稍候...</p>
              <p className="text-sm text-slate-500">预计等待时间 40-60 秒</p>
              <p className="text-xs text-slate-600 mt-2">4 位 AI 专家正在独立分析</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && !isLoading && (
        <div className="space-y-6">
          {/* Stock Info Card */}
          <Card className="bg-slate-900/50 border-slate-800">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-slate-100">
                    {result.stock_name} ({result.symbol})
                  </h2>
                  <p className="text-slate-400 mt-1">
                    当前价格: ¥{result.current_price.toFixed(2)}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-sm text-slate-400">AI 投委会判决</div>
                  <div className="text-lg font-semibold text-slate-100">
                    {result.verdict_chinese} {result.conviction_stars}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Decision Matrix - 使用新的AI投委会加权坐标 */}
          <div className="bg-slate-900/30 border border-slate-800 rounded-lg p-6">
            <DecisionMatrix
              technical={result.dashboard_position?.final_y ?? result.technical_score}
              fundamental={result.dashboard_position?.final_x ?? result.fundamental_score}
            />
          </div>
        </div>
      )}

      {/* Initial State */}
      {!result && !error && !isLoading && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="py-16 text-center">
            <Sparkles className="w-16 h-16 mx-auto mb-4 text-slate-600" />
            <p className="text-slate-400">输入股票代码，开始投资分析</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
