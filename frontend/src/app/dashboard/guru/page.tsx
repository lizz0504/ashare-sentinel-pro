"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, RefreshCw, TrendingUp, TrendingDown, Minus, Zap } from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004"

// ============================================
// 数据类型定义
// ============================================
interface GuruSignal {
  id: string
  guru_name: string
  platform: string
  sentiment: string
  action: string
  summary: string
  mentioned_symbols: Array<{ symbol: string; name: string | null }>
  trading_idea: {
    entry_point: string | null
    stop_loss: string | null
    target_price: string | null
    time_horizon: string | null
    position_size: string | null
    reasoning: string | null
  } | null
  related_themes: string[]
  key_factors: string[]
  confidence_score: number
  publish_time: string | null
}

interface AggregatedSentiment {
  symbol: string
  total_signals: number
  bullish_count: number
  bearish_count: number
  neutral_count: number
  avg_sentiment: string
  recent_summary: Array<{
    guru: string
    action: string
    summary: string
    time: string | null
  }>
}

// ============================================
// 组件
// ============================================
export default function GuruWatcherPage() {
  const [signals, setSignals] = useState<GuruSignal[]>([])
  const [aggregatedData, setAggregatedData] = useState<Record<string, AggregatedSentiment>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [selectedSymbol, setSelectedSymbol] = useState<string>("")
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    loadSignals()
  }, [])

  // ============================================
  // 数据加载函数
  // ============================================
  const loadSignals = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/api/v1/guru/signals`)
      if (response.ok) {
        const data = await response.json()
        setSignals(data.signals || [])
      }
    } catch (error) {
      console.error("Failed to load signals:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const processFeeds = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/api/v1/guru/process-feeds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: "xueqiu", limit: 10 })
      })
      if (response.ok) {
        const data = await response.json()
        setSignals(data.signals || [])
      }
    } catch (error) {
      console.error("Failed to process feeds:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadAggregatedSentiment = async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/guru/signal/${symbol}`)
      if (response.ok) {
        const data = await response.json()
        setAggregatedData(prev => ({ ...prev, [symbol]: data }))
      }
    } catch (error) {
      console.error(`Failed to load sentiment for ${symbol}:`, error)
    }
  }

  // ============================================
  // 渲染辅助函数
  // ============================================
  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case "bullish": return <TrendingUp className="w-4 h-4 text-green-500" />
      case "bearish": return <TrendingDown className="w-4 h-4 text-red-500" />
      default: return <Minus className="w-4 h-4 text-gray-500" />
    }
  }

  const getActionBadge = (action: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      "BUY": "default",
      "STRONG_BUY": "default",
      "SELL": "destructive",
      "STRONG_SELL": "destructive",
      "HOLD": "secondary",
      "COMMENT": "outline"
    }
    const labels: Record<string, string> = {
      "BUY": "买入",
      "STRONG_BUY": "强买",
      "SELL": "卖出",
      "STRONG_SELL": "强卖",
      "HOLD": "持有",
      "COMMENT": "评论"
    }
    return (
      <Badge variant={variants[action] || "outline"}>
        {labels[action] || action}
      </Badge>
    )
  }

  const getAggregatedSentimentColor = (sentiment: string) => {
    if (sentiment.includes("Bullish")) return "text-green-600"
    if (sentiment.includes("Bearish")) return "text-red-600"
    return "text-gray-600"
  }

  // 提取所有提到的股票代码
  const getAllMentionedSymbols = () => {
    const symbolMap = new Map<string, { count: number; signals: GuruSignal[] }>()
    signals.forEach(signal => {
      signal.mentioned_symbols.forEach(ms => {
        const existing = symbolMap.get(ms.symbol) || { count: 0, signals: [] }
        symbolMap.set(ms.symbol, {
          count: existing.count + 1,
          signals: [...existing.signals, signal]
        })
      })
    })
    return Array.from(symbolMap.entries()).sort((a, b) => b[1].count - a[1].count)
  }

  const mentionedSymbols = getAllMentionedSymbols()

  // ============================================
  // 渲染
  // ============================================
  if (!mounted) return null

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* 页面标题 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Zap className="w-8 h-8 text-yellow-500" />
              Guru Watcher
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              大V交易信号监控 · AI智能提取
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={loadSignals}
              variant="outline"
              disabled={isLoading}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
              刷新
            </Button>
            <Button
              onClick={processFeeds}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Zap className="w-4 h-4 mr-2" />
              )}
              处理订阅源
            </Button>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">{signals.length}</div>
              <div className="text-sm text-slate-600 dark:text-slate-400">总信号数</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-green-600">
                {signals.filter(s => s.sentiment === "Bullish").length}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">看多信号</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-red-600">
                {signals.filter(s => s.sentiment === "Bearish").length}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">看空信号</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold">
                {mentionedSymbols.length}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">涉及股票</div>
            </CardContent>
          </Card>
        </div>

        {/* 热门股票 */}
        {mentionedSymbols.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>🔥 热门提及股票</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {mentionedSymbols.map(([symbol, data]) => (
                  <Button
                    key={symbol}
                    variant={selectedSymbol === symbol ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                      setSelectedSymbol(symbol)
                      loadAggregatedSentiment(symbol)
                    }}
                  >
                    {symbol} ({data.count})
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 聚合情绪分析 */}
        {selectedSymbol && aggregatedData[selectedSymbol] && (
          <Card>
            <CardHeader>
              <CardTitle>
                📊 {selectedSymbol} 聚合情绪分析
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="text-3xl font-bold text-green-600">
                    {aggregatedData[selectedSymbol].bullish_count}
                  </div>
                  <div className="text-sm text-green-700 dark:text-green-400">看多</div>
                </div>
                <div className="text-center p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <div className="text-3xl font-bold text-red-600">
                    {aggregatedData[selectedSymbol].bearish_count}
                  </div>
                  <div className="text-sm text-red-700 dark:text-red-400">看空</div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-3xl font-bold text-gray-600">
                    {aggregatedData[selectedSymbol].neutral_count}
                  </div>
                  <div className="text-sm text-gray-700 dark:text-gray-400">中性</div>
                </div>
              </div>
              <div className="mt-4 text-center">
                <div className={`text-lg font-semibold ${getAggregatedSentimentColor(aggregatedData[selectedSymbol].avg_sentiment)}`}>
                  整体情绪: {aggregatedData[selectedSymbol].avg_sentiment}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 信号列表 */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
            最新信号
          </h2>
          {signals.length === 0 ? (
            <Card>
              <CardContent className="pt-6 text-center text-slate-500">
                暂无信号，点击"处理订阅源"开始抓取
              </CardContent>
            </Card>
          ) : (
            signals.map(signal => (
              <Card key={signal.id} className="hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold">
                        {signal.guru_name.charAt(0)}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {signal.guru_name}
                        </div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                          {signal.platform} · {signal.publish_time ? new Date(signal.publish_time).toLocaleDateString() : "未知时间"}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getSentimentIcon(signal.sentiment)}
                      {getActionBadge(signal.action)}
                    </div>
                  </div>

                  <p className="text-slate-700 dark:text-slate-300 mb-3">
                    {signal.summary}
                  </p>

                  {signal.mentioned_symbols.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {signal.mentioned_symbols.map(ms => (
                        <Badge key={ms.symbol} variant="outline" className="cursor-pointer hover:bg-slate-100">
                          {ms.symbol}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {signal.related_themes.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {signal.related_themes.map(theme => (
                        <Badge key={theme} variant="secondary" className="text-xs">
                          {theme}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {signal.trading_idea && signal.trading_idea.reasoning && (
                    <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm">
                      <div className="font-medium text-slate-700 dark:text-slate-300 mb-1">
                        💡 投资逻辑:
                      </div>
                      <div className="text-slate-600 dark:text-slate-400">
                        {signal.trading_idea.reasoning}
                      </div>
                    </div>
                  )}

                  {signal.key_factors.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {signal.key_factors.map(factor => (
                        <span key={factor} className="text-xs px-2 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded">
                          {factor}
                        </span>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
