"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Sparkles, Gavel, TrendingUp, Landmark, Scale } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { addAnalysisRecord } from "@/lib/utils/analysisHistory"

// ============================================
// Interfaces
// ============================================

interface ICMeetingRequest {
  symbol: string
  stock_name?: string
  current_price?: number
  industry?: string
  market_cap?: string
  pe_ratio?: string
  revenue_growth?: string
}

interface ICMeetingResult {
  symbol: string
  stock_name: string
  current_price: number
  technical_score: number | null
  fundamental_score: number | null
  verdict_chinese: string
  conviction_stars: string
  cathie_wood: string
  nancy_pelosi: string
  warren_buffett: string
  final_verdict: {
    final_verdict: string
    conviction_level: number
    key_considerations: string[]
    invert_risks: string[]
    munger_wisdom: string
    synthesis: string
  }
  summary: string
}

// ============================================
// Loading Messages for Each Stage
// ============================================

const LOADING_STAGES = [
  { icon: <TrendingUp className="w-5 h-5" />, text: "正在连线 Cathie Wood (ARK)..." },
  { icon: <Landmark className="w-5 h-5" />, text: "正在接入国会山数据..." },
  { icon: <Gavel className="w-5 h-5" />, text: "正在呼叫奥马哈..." },
  { icon: <Scale className="w-5 h-5" />, text: "查理·芒格正在整理决议..." },
]

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004"

// ============================================
// Component
// ============================================

export default function ICMeetingPage() {
  const [symbol, setSymbol] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [currentStage, setCurrentStage] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ICMeetingResult | null>(null)
  const [fromDashboard, setFromDashboard] = useState(false)

  // ============================================
  // 检查从 Dashboard 传递过来的数据
  // ============================================

  useEffect(() => {
    try {
      const sharedData = localStorage.getItem('ic_meeting_shared_data')
      if (sharedData) {
        const data = JSON.parse(sharedData)
        // 检查数据是否在1小时内
        const oneHour = 60 * 60 * 1000
        if (Date.now() - data.timestamp < oneHour) {
          setResult(data)
          setSymbol(data.symbol)
          setFromDashboard(true)
        } else {
          localStorage.removeItem('ic_meeting_shared_data')
        }
      }
    } catch (err) {
      console.error('Failed to load shared data:', err)
    }
  }, [])

  // ============================================
  // Dynamic Loading Stage Effect
  // ============================================

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null

    if (isLoading) {
      // Start from stage 0
      setCurrentStage(0)

      // Advance to next stage every 5 seconds
      interval = setInterval(() => {
        setCurrentStage(prev => {
          const next = prev + 1
          // Loop back to stage 0 if we exceed the array
          return next >= LOADING_STAGES.length ? 0 : next
        })
      }, 5000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isLoading])

  // ============================================
  // Action Handler
  // ============================================

  const handleConductMeeting = async () => {
    if (!symbol.trim()) {
      alert("请输入股票代码")
      return
    }

    // Validate A-share code format
    const trimmedSymbol = symbol.trim()
    if (!/^\d{6}$/.test(trimmedSymbol)) {
      alert("无效的 A 股代码格式\n\nA 股代码必须是 6 位数字\n例如：600519（贵州茅台）、000001（平安银行）")
      return
    }

    // 如果来自 Dashboard 的数据，清除它以重新分析
    if (fromDashboard) {
      localStorage.removeItem('ic_meeting_shared_data')
      setFromDashboard(false)
    }

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const requestBody: ICMeetingRequest = {
        symbol: trimmedSymbol.toUpperCase(),
      }

      const response = await fetch(`${API_BASE}/api/v1/ic/meeting`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "未知错误" }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const data = await response.json()
      setResult(data)

      // 自动保存到复盘历史记录
      addAnalysisRecord({
        type: 'ic_meeting',
        symbol: data.symbol,
        stock_name: data.stock_name,
        current_price: data.current_price,
        technical_score: data.technical_score,
        fundamental_score: data.fundamental_score,
        verdict_chinese: data.verdict_chinese,
        conviction_stars: data.conviction_stars,
        full_report: JSON.stringify(data, null, 2)
      })
    } catch (err) {
      console.error("IC meeting failed:", err)
      const errorMessage = err instanceof Error ? err.message : "未知错误"
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  // ============================================
  // UI Helper Functions
  // ============================================

  const getVerdictBadgeColor = (verdict: string) => {
    switch (verdict) {
      case "强烈买入":
        return "bg-emerald-500 text-white border-emerald-600"
      case "买入":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/50"
      case "持有":
        return "bg-blue-500/20 text-blue-400 border-blue-500/50"
      case "卖出":
        return "bg-red-500/20 text-red-400 border-red-500/50"
      case "强烈卖出":
        return "bg-red-500 text-white border-red-600"
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/50"
    }
  }

  const getAnalystColor = (analyst: string) => {
    switch (analyst) {
      case "cathie_wood":
        return "border-pink-500/30 bg-pink-500/5"
      case "nancy_pelosi":
        return "border-purple-500/30 bg-purple-500/5"
      case "warren_buffett":
        return "border-amber-500/30 bg-amber-500/5"
      case "charlie_munger":
        return "border-blue-500/30 bg-blue-500/5"
      default:
        return "border-slate-700 bg-slate-900/50"
    }
  }

  const getAnalystName = (key: string) => {
    const names: Record<string, string> = {
      cathie_wood: "Cathie Wood (成长与颠覆)",
      nancy_pelosi: "Nancy Pelosi (权力与政策)",
      warren_buffett: "Warren Buffett (深度价值)",
      charlie_munger: "Charlie Munger (最终裁决)",
    }
    return names[key] || key
  }

  const getAnalystIcon = (key: string) => {
    switch (key) {
      case "cathie_wood":
        return <TrendingUp className="w-5 h-5 text-pink-400" />
      case "nancy_pelosi":
        return <Landmark className="w-5 h-5 text-purple-400" />
      case "warren_buffett":
        return <Gavel className="w-5 h-5 text-amber-400" />
      case "charlie_munger":
        return <Scale className="w-5 h-5 text-blue-400" />
      default:
        return <Sparkles className="w-5 h-5 text-slate-400" />
    }
  }

  // ============================================
  // Render
  // ============================================

  return (
    <div className="space-y-6">
      {/* ========================================
          Header
          ======================================== */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
          <Gavel className="w-8 h-8 text-amber-400" />
          AI 投委会
        </h1>
        <p className="mt-2 text-slate-400">
          Investment Committee - 四大投资名人多视角分析
        </p>
      </div>

      {/* ========================================
          Input Card
          ======================================== */}
      <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100 text-lg">
            <Sparkles className="w-5 h-5 text-blue-400" />
            召开投委会会议
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="股票代码 (如: 600519)"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={isLoading}
              className="bg-slate-950/50 border-slate-700 text-slate-100 max-w-xs"
              onKeyDown={(e) => e.key === "Enter" && handleConductMeeting()}
            />
            <Button
              onClick={handleConductMeeting}
              disabled={!symbol.trim() || isLoading}
              className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-medium"
            >
              {isLoading ? (
                <React.Fragment>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  会议进行中...
                </React.Fragment>
              ) : (
                <React.Fragment>
                  <Gavel className="w-4 h-4 mr-2" />
                  召开会议
                </React.Fragment>
              )}
            </Button>
          </div>

          {/* Dashboard 数据提示 */}
          {fromDashboard && result && (
            <div className="mt-4 flex items-center justify-between bg-blue-500/10 border border-blue-500/30 rounded-lg px-3 py-2">
              <div className="flex items-center gap-2 text-xs text-blue-400">
                <Sparkles className="w-4 h-4" />
                <span>来自 Dashboard 的分析结果</span>
              </div>
              <Button
                onClick={() => {
                  localStorage.removeItem('ic_meeting_shared_data')
                  setResult(null)
                  setFromDashboard(false)
                }}
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-blue-300 hover:text-blue-200 hover:bg-blue-500/20"
              >
                清除
              </Button>
            </div>
          )}

          {error && (
            <div className="mt-4 text-red-400 text-sm">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ========================================
          Loading State (Dynamic Progress)
          ======================================== */}
      {isLoading && (
        <Card className="bg-gradient-to-r from-slate-900/80 to-slate-800/80 border-slate-700 backdrop-blur-sm">
          <CardContent className="p-8">
            <div className="flex flex-col items-center gap-6">
              {/* Animated Loader */}
              <div className="relative">
                <Loader2 className="w-16 h-16 animate-spin text-amber-400" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Gavel className="w-6 h-6 text-amber-600" />
                </div>
              </div>

              {/* Dynamic Stage Indicator */}
              <div className="text-center space-y-3">
                <div className="flex items-center justify-center gap-3 text-slate-200">
                  {LOADING_STAGES[currentStage].icon}
                  <span className="text-lg font-medium">{LOADING_STAGES[currentStage].text}</span>
                </div>

                {/* Progress Dots */}
                <div className="flex items-center justify-center gap-2">
                  {LOADING_STAGES.map((_, idx) => (
                    <div
                      key={idx}
                      className={`h-2 rounded-full transition-all duration-300 ${
                        idx === currentStage
                          ? "w-8 bg-amber-400"
                          : idx < currentStage
                          ? "w-2 bg-emerald-400"
                          : "w-2 bg-slate-700"
                      }`}
                    />
                  ))}
                </div>

                <p className="text-sm text-slate-500">
                  预计等待时间 20-40 秒，请耐心等待...
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ========================================
          Error State (Connection Lost)
          ======================================== */}
      {error && !isLoading && (
        <Card className="bg-red-950/30 border-red-800/50 backdrop-blur-sm">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-full bg-red-900/50">
                <Sparkles className="w-6 h-6 text-red-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-300 mb-2">
                  Connection Lost: 会议中断
                </h3>
                <p className="text-sm text-red-400/80 mb-4">{error}</p>
                <Button
                  onClick={() => {
                    setError(null)
                    handleConductMeeting()
                  }}
                  variant="outline"
                  className="border-red-700 text-red-300 hover:bg-red-900/30"
                >
                  重试
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ========================================
          Results Display
          ======================================== */}
      {result && !isLoading && (
        <div className="space-y-6">
          {/* Final Verdict Card */}
          <Card className="bg-gradient-to-r from-slate-900/80 to-slate-800/80 border-slate-700 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-slate-100 flex items-center gap-2">
                <Scale className="w-6 h-6 text-amber-400" />
                最终判决 - {result.stock_name} ({result.symbol})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Verdict Badge */}
              <div className="flex items-center gap-4">
                <Badge className={`text-lg px-6 py-2 ${getVerdictBadgeColor(result.verdict_chinese)}`}>
                  {result.verdict_chinese} {result.conviction_stars}
                </Badge>
                <div className="text-slate-400">
                  当前价格: <span className="text-slate-200 font-semibold">¥{result.current_price.toFixed(2)}</span>
                </div>
              </div>

              {/* Key Considerations */}
              <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                <h4 className="text-sm font-medium text-slate-300 mb-3">关键考虑因素</h4>
                <ul className="space-y-2">
                  {result.final_verdict.key_considerations.map((item, idx) => (
                    <li key={idx} className="text-sm text-slate-400 flex items-start gap-2">
                      <span className="text-amber-400 mt-0.5">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Invert Risks */}
              {result.final_verdict.invert_risks.length > 0 && (
                <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                  <h4 className="text-sm font-medium text-red-300 mb-3">反向思考风险</h4>
                  <ul className="space-y-2">
                    {result.final_verdict.invert_risks.map((item, idx) => (
                      <li key={idx} className="text-sm text-red-400/80 flex items-start gap-2">
                        <span className="text-red-400 mt-0.5">!</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Munger Wisdom & Synthesis */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-amber-950/20 rounded-lg p-4 border border-amber-900/30">
                  <h4 className="text-sm font-medium text-amber-300 mb-2">芒格格言</h4>
                  <p className="text-sm text-amber-200/80 italic">"{result.final_verdict.munger_wisdom}"</p>
                </div>
                <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                  <h4 className="text-sm font-medium text-slate-300 mb-2">综合逻辑</h4>
                  <p className="text-sm text-slate-400">{result.final_verdict.synthesis}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Analyst Cards */}
          <div className="grid grid-cols-1 gap-6">
            {/* Cathie Wood */}
            <Card className={`border ${getAnalystColor("cathie_wood")}`}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                  {getAnalystIcon("cathie_wood")}
                  {getAnalystName("cathie_wood")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-400 whitespace-pre-wrap">{result.cathie_wood}</p>
              </CardContent>
            </Card>

            {/* Nancy Pelosi */}
            <Card className={`border ${getAnalystColor("nancy_pelosi")}`}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                  {getAnalystIcon("nancy_pelosi")}
                  {getAnalystName("nancy_pelosi")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-400 whitespace-pre-wrap">{result.nancy_pelosi}</p>
              </CardContent>
            </Card>

            {/* Warren Buffett */}
            <Card className={`border ${getAnalystColor("warren_buffett")}`}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                  {getAnalystIcon("warren_buffett")}
                  {getAnalystName("warren_buffett")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-400 whitespace-pre-wrap">{result.warren_buffett}</p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* ========================================
          Empty State (Initial)
          ======================================== */}
      {!result && !error && !isLoading && (
        <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
          <CardContent className="py-16 text-center">
            <Gavel className="w-16 h-16 mx-auto mb-4 text-slate-600" />
            <p className="text-slate-400">输入股票代码，召开AI投委会会议</p>
            <p className="text-sm text-slate-600 mt-2">
              四大投资名人将为您多视角分析该股票
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
