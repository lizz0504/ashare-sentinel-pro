"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Trash2, Loader2, RefreshCw, Sparkles, Zap } from "lucide-react"

// 导入分析历史工具
import {
  getMergedAnalysisHistory,
  getAnalysisHistory,
  deleteStockAllRecords,
  clearAnalysisHistory,
  getStockSourceTypes,
  type AnalysisRecord
} from "@/lib/utils/analysisHistory"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// ============================================
// 技术分析数据类型
// ============================================
interface TechnicalAnalysis {
  symbol: string
  current_price: number
  ma5: number
  ma20: number
  ma20_status: string
  ma5_status: string
  volume_status: string
  volume_change_pct: number
  alpha: number
  health_score: number
  k_line_pattern: string
  pattern_signal: string
  date: string
  action_signal?: string
  analysis?: string
  quote?: string
}

export default function SmartPoolPage() {
  const [smartPool, setSmartPool] = useState<AnalysisRecord[]>([])
  const [technicalData, setTechnicalData] = useState<Record<string, TechnicalAnalysis>>({})
  const [failedTechnicalLoads, setFailedTechnicalLoads] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [mounted, setMounted] = useState(false)

  // 确保只在客户端挂载后渲染
  useEffect(() => {
    setMounted(true)
  }, [])

  // ============================================
  // 数据加载函数
  // ============================================

  /**
   * 加载技术分析数据
   */
  const loadTechnicalAnalysis = async (symbol: string, force: boolean = false): Promise<TechnicalAnalysis | null> => {
    try {
      // 添加缓存破坏参数，确保获取最新数据
      const cacheBuster = Date.now()
      const url = `${API_BASE}/api/v1/market/technical/${symbol}?_t=${cacheBuster}${force ? '&force=true' : ''}`
      const response = await fetch(url, {
        cache: 'no-store'
      })
      if (response.ok) {
        const data = await response.json()
        setTechnicalData(prev => ({ ...prev, [symbol]: data }))
        return data
      }
      return null
    } catch (error) {
      console.error(`[SmartPool] Error loading technical analysis for ${symbol}:`, error)
      return null
    }
  }

  /**
   * 加载智能股票池数据
   */
  const loadSmartPool = async (force: boolean = false) => {
    setIsLoading(true)
    // 使用合并后的历史记录，自动合并同一只股票
    const mergedHistory = getMergedAnalysisHistory()

    setSmartPool(mergedHistory)
    setFailedTechnicalLoads(new Set())

    // 检查是否有有效的股票需要加载
    if (!mergedHistory || mergedHistory.length === 0) {
      console.log("[SmartPool] No stocks to load")
      setIsLoading(false)
      return
    }

    // 为智能股票池的股票加载技术分析
    const symbolsToLoad = mergedHistory
      .filter(stock => stock.symbol && /^\d{6}$/.test(stock.symbol))
      .map(stock => stock.symbol)

    if (symbolsToLoad.length === 0) {
      setIsLoading(false)
      return
    }

    console.log(`[SmartPool] Loading technical analysis for ${symbolsToLoad.length} stocks`)

    const newFailedLoads = new Set<string>()

    // 批量加载（每次最多3个并发）
    for (let i = 0; i < symbolsToLoad.length; i += 3) {
      const batch = symbolsToLoad.slice(i, i + 3)
      await Promise.all(batch.map(async (symbol) => {
        try {
          const result = await loadTechnicalAnalysis(symbol, force)
          if (!result) {
            newFailedLoads.add(symbol)
          }
        } catch (error) {
          console.error(`[SmartPool] Error loading ${symbol}:`, error)
          newFailedLoads.add(symbol)
        }
      }))
    }

    setFailedTechnicalLoads(newFailedLoads)
    setIsLoading(false)
  }

  // 页面加载时初始化
  useEffect(() => {
    loadSmartPool()

    // 页面焦点时刷新数据
    const handleFocus = () => {
      loadSmartPool()
    }

    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [])

  // ============================================
  // UI Helper Functions
  // ============================================

  const getActionSignalBadge = (signal?: string) => {
    const badges: Record<string, { color: string; label: string }> = {
      "STRONG_BUY": { color: "bg-emerald-500 text-white border-emerald-600", label: "强烈买入" },
      "BUY": { color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50", label: "买入" },
      "HOLD": { color: "bg-blue-500/20 text-blue-400 border-blue-500/50", label: "持有" },
      "SELL": { color: "bg-red-500/20 text-red-400 border-red-500/50", label: "卖出" },
      "STRONG_SELL": { color: "bg-red-500 text-white border-red-600", label: "强烈卖出" },
    }
    return badges[signal || ""] || { color: "bg-slate-500/20 text-slate-400", label: "-" }
  }

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-400"
    if (score >= 60) return "text-lime-400"
    if (score >= 40) return "text-yellow-400"
    if (score >= 20) return "text-orange-400"
    return "text-red-400"
  }

  const getHealthScoreBg = (score: number) => {
    if (score >= 80) return "bg-emerald-500"
    if (score >= 60) return "bg-lime-500"
    if (score >= 40) return "bg-yellow-500"
    if (score >= 20) return "bg-orange-500"
    return "bg-red-500"
  }

  const getVolumeBadgeColor = (status: string) => {
    if (status === "放量") return "bg-red-500/20 text-red-400 border-red-500/30"
    if (status === "缩量") return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
    return "bg-slate-500/20 text-slate-400 border-slate-500/30"
  }

  const getVerdictBadgeClass = (verdict: string) => {
    if (verdict.includes('买入')) return 'bg-emerald-500/20 text-emerald-400'
    if (verdict.includes('卖出')) return 'bg-red-500/20 text-red-400'
    return 'bg-blue-500/20 text-blue-400'
  }

  // ============================================
  // Actions
  // ============================================

  const handleRefresh = async () => {
    // 强制重新加载，清除旧的技术数据和后端缓存
    setTechnicalData({})
    setFailedTechnicalLoads(new Set())
    await loadSmartPool(true)  // force=true 强制刷新
  }

  const handleClearAll = () => {
    if (confirm('确定要清空智能股票池吗？')) {
      clearAnalysisHistory()
      setSmartPool([])
      setTechnicalData({})
      setFailedTechnicalLoads(new Set())
    }
  }

  const handleDeleteStock = (symbol: string) => {
    deleteStockAllRecords(symbol)
    loadSmartPool(false)  // 不强制刷新
  }

  const handleRetryTechnical = async (symbol: string) => {
    await loadTechnicalAnalysis(symbol)
    // 重新加载以更新失败状态
    const history = getAnalysisHistory()
    setFailedTechnicalLoads(prev => {
      const newSet = new Set(prev)
      newSet.delete(symbol)
      return newSet
    })
  }

  // ============================================
  // Render
  // ============================================

  // 基于原始历史记录计算统计数据
  const originalHistory = getAnalysisHistory()
  const dashboardCount = originalHistory.filter(s => s.type === 'dashboard').length
  const icCount = originalHistory.filter(s => s.type === 'ic_meeting').length
  const buyCount = smartPool.filter(s => s.verdict_chinese.includes('买入')).length
  const sellCount = smartPool.filter(s => s.verdict_chinese.includes('卖出')).length

  // 服务端渲染时显示加载状态，避免水合错误
  if (!mounted) {
    return (
      <div className="space-y-6 p-8">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-8">
      {/* ========================================
          Header
          ======================================== */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <Zap className="w-8 h-8 text-amber-400" />
            智能股票池
          </h1>
          <div className="mt-2 flex items-center gap-3">
            <p className="text-slate-400">来自 Dashboard 和 IC 投委会的 AI 推荐股票</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={handleRefresh}
            disabled={isLoading}
            variant="outline"
            className="border-blue-600 text-blue-300 hover:bg-blue-900 hover:text-white"
          >
            {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            刷新
          </Button>
          <Button
            onClick={handleClearAll}
            disabled={smartPool.length === 0}
            variant="outline"
            className="border-red-600 text-red-300 hover:bg-red-900 hover:text-white"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            清空
          </Button>
        </div>
      </div>

      {/* ========================================
          Statistics Cards
          ======================================== */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-slate-100">{smartPool.length}</div>
            <div className="text-sm text-slate-400">总推荐</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-400">{dashboardCount}</div>
            <div className="text-sm text-slate-400">Dashboard</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-purple-400">{icCount}</div>
            <div className="text-sm text-slate-400">IC 投委会</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-emerald-400">{buyCount}</div>
            <div className="text-sm text-slate-400">买入信号</div>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-red-400">{sellCount}</div>
            <div className="text-sm text-slate-400">卖出信号</div>
          </CardContent>
        </Card>
      </div>

      {/* ========================================
          Smart Pool List
          ======================================== */}
      {isLoading ? (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="py-16">
            <div className="flex flex-col items-center justify-center space-y-4">
              <Loader2 className="w-12 h-12 animate-spin text-blue-400" />
              <p className="text-slate-400">正在加载智能股票池...</p>
            </div>
          </CardContent>
        </Card>
      ) : smartPool.length === 0 ? (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardContent className="py-16">
            <div className="flex flex-col items-center justify-center space-y-4">
              <Sparkles className="w-16 h-16 text-slate-600" />
              <div className="text-center">
                <p className="text-lg font-medium text-slate-200">智能股票池为空</p>
                <p className="text-sm text-slate-500 mt-2">
                  在 <span className="text-blue-400">Dashboard</span> 分析股票，<br />
                  或在 <span className="text-purple-400">IC投委会</span> 开会，<br />
                  推荐股票会自动添加到这里
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {smartPool.map((stock) => {
            // 获取股票的实际来源类型
            const sourceTypes = getStockSourceTypes(stock.symbol)
            const hasBothSources = sourceTypes.hasDashboard && sourceTypes.hasIC

            const tech = technicalData[stock.symbol]
            const hasFailed = failedTechnicalLoads.has(stock.symbol)
            const actionBadge = getActionSignalBadge(tech?.action_signal)
            const healthScore = tech?.health_score ?? 0
            const healthColor = getHealthScoreColor(healthScore)

            return (
              <Card
                key={stock.id}
                className="bg-gradient-to-r from-slate-900/80 to-slate-800/80 border-slate-700 hover:border-slate-600 transition-all"
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-6">
                    <div className="flex-1">
                      {/* Stock Header */}
                      <div className="flex items-center gap-3 mb-4">
                        {hasBothSources ? (
                          // 显示合并的来源标签
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-1 rounded-lg text-sm font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                              📈 Dashboard
                            </span>
                            <span className="text-slate-500">+</span>
                            <span className="px-2 py-1 rounded-lg text-sm font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">
                              👥 IC投委会
                            </span>
                          </div>
                        ) : (
                          // 显示单个来源标签
                          <span className={`px-3 py-1 rounded-lg text-sm font-semibold ${
                            stock.type === 'dashboard'
                              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                          }`}>
                            {stock.type === 'dashboard' ? '📈 Dashboard' : '👥 IC投委会'}
                          </span>
                        )}
                        <h3 className="text-xl font-bold text-slate-100">{stock.stock_name}</h3>
                        <span className="text-slate-400 font-mono">({stock.symbol})</span>
                      </div>

                      {/* Price & Verdict */}
                      <div className="flex items-center gap-4 mb-4 flex-wrap">
                        <span className="text-2xl font-semibold text-slate-100">
                          ¥{stock.current_price.toFixed(2)}
                        </span>

                        {/* 当有多个来源时，显示综合判决详情 */}
                        {hasBothSources && stock.merged_verdict ? (
                          <div className="flex items-center gap-3 flex-wrap">
                            {/* Dashboard 原始判决 */}
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-slate-500">Dashboard:</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${
                                stock.merged_verdict.dashboard_verdict !== 'N/A' && stock.merged_verdict.dashboard_verdict?.includes('买入')
                                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                  : stock.merged_verdict.dashboard_verdict !== 'N/A' && stock.merged_verdict.dashboard_verdict?.includes('卖出')
                                  ? 'bg-red-500/20 text-red-400 border-red-500/30'
                                  : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                              }`}>
                                {stock.merged_verdict.dashboard_verdict}
                              </span>
                            </div>

                            {/* IC 原始判决 */}
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-slate-500">IC投委会:</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${
                                stock.merged_verdict.ic_verdict !== 'N/A' && stock.merged_verdict.ic_verdict?.includes('买入')
                                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                  : stock.merged_verdict.ic_verdict !== 'N/A' && stock.merged_verdict.ic_verdict?.includes('卖出')
                                  ? 'bg-red-500/20 text-red-400 border-red-500/30'
                                  : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                              }`}>
                                {stock.merged_verdict.ic_verdict}
                              </span>
                            </div>

                            {/* 分隔符 */}
                            <span className="text-slate-600">→</span>

                            {/* 综合终审判决 */}
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-amber-400 font-medium">终审:</span>
                              <span className={`px-3 py-1 rounded-lg text-sm font-semibold ${getVerdictBadgeClass(stock.verdict_chinese)}`}>
                                {stock.verdict_chinese} {stock.conviction_stars}
                              </span>
                            </div>
                          </div>
                        ) : (
                          // 单来源，直接显示判决
                          <span className={`px-3 py-1 rounded-lg text-sm font-semibold ${getVerdictBadgeClass(stock.verdict_chinese)}`}>
                            {stock.verdict_chinese} {stock.conviction_stars}
                          </span>
                        )}

                        <span className="text-sm text-slate-500">
                          技:{stock.technical_score ?? '-'} 基:{stock.fundamental_score ?? '-'}
                        </span>
                      </div>

                      {/* Technical Analysis Details */}
                      {tech ? (
                        <div className="space-y-3">
                          {/* Health Score */}
                          <div className="flex items-center gap-3">
                            <span className="text-sm text-slate-500 w-20">健康分:</span>
                            <div className="flex items-center gap-2 flex-1">
                              <span className={`text-lg font-bold ${healthColor}`}>
                                {healthScore}
                              </span>
                              <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden max-w-[200px]">
                                <div
                                  className={`h-full ${getHealthScoreBg(healthScore)} transition-all`}
                                  style={{ width: `${healthScore}%` }}
                                />
                              </div>
                            </div>
                          </div>

                          {/* Technical Indicators */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            <div className="flex items-center gap-2">
                              <span className="text-slate-500">MA20:</span>
                              <span className={`font-medium ${tech.ma20_status?.includes('站上') ? 'text-emerald-400' : 'text-red-400'}`}>
                                {tech.ma20_status}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-slate-500">成交量:</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getVolumeBadgeColor(tech.volume_status)}`}>
                                {tech.volume_status}
                              </span>
                              <span className="text-xs text-slate-500">
                                ({tech.volume_change_pct?.toFixed(1) ?? 0}%)
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-slate-500">Alpha:</span>
                              <span className={`font-medium ${tech.alpha >= 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                                {tech.alpha >= 0 ? '+' : ''}{tech.alpha.toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-slate-500">操作:</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${actionBadge.color}`}>
                                {actionBadge.label}
                              </span>
                            </div>
                          </div>

                          {/* Analysis Quote */}
                          {tech.analysis && (
                            <div className="mt-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                              <p className="text-sm text-slate-300 leading-relaxed">
                                {tech.analysis}
                              </p>
                              {tech.quote && (
                                <p className="text-xs text-slate-500 mt-2 italic">
                                  "{tech.quote}"
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      ) : hasFailed ? (
                        <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                          <span className="text-amber-500">⚠️ 技术分析数据暂不可用</span>
                          <button
                            onClick={() => handleRetryTechnical(stock.symbol)}
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            重试
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 p-3 bg-slate-800/50 rounded-lg">
                          <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
                          <span className="text-slate-500 text-sm">正在加载技术分析...</span>
                        </div>
                      )}
                    </div>

                    {/* Delete Button */}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                      onClick={() => handleDeleteStock(stock.symbol)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>

                  {/* Footer */}
                  <div className="mt-4 pt-4 border-t border-slate-700 flex items-center justify-between text-xs text-slate-500">
                    <span>
                      {new Date(stock.timestamp).toLocaleString('zh-CN')}
                    </span>
                    {tech && (
                      <span>数据更新于: {tech.date}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* ========================================
          Footer Legend
          ======================================== */}
      <Card className="bg-slate-900/30 border-slate-800">
        <CardContent className="py-4">
          <div className="flex items-center justify-center gap-6 text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-blue-500/20 border border-blue-500/30"></div>
              <span>Dashboard 分析</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-purple-500/20 border border-purple-500/30"></div>
              <span>IC 投委会</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-emerald-500/20 border border-emerald-500/30"></div>
              <span>买入信号</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-red-500/20 border border-red-500/30"></div>
              <span>卖出信号</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
