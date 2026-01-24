"use client"

import React, { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Plus, Trash2, Loader2, Sparkles, Building2, Activity, Zap, Play, RefreshCw } from "lucide-react"
import { Badge } from "@/components/ui/badge"

// 导入新的工具函数
import { isMarketOpen, isCacheValid } from "@/lib/utils/marketTime"
import {
  getTechnicalCache,
  setTechnicalCache,
  getSentimentCache,
  setSentimentCache,
  clearTechnicalCache,
  clearSentimentCache,
  getPortfolioCache,
  setPortfolioCache,
  type TechnicalCache,
  type SentimentCache
} from "@/lib/utils/cache"

// ============================================
// Mock Data (用于开发测试)
// ============================================
const MOCK_SENTIMENT = {
  score: 82,
  label: "极度贪婪",
  rsi: 75.5,
  date: "2026-01-23"
}

const MOCK_TECHNICAL: Record<string, any> = {
  "600519": {
    symbol: "600519",
    current_price: 1343.69,
    ma5: 1356.87,
    ma20: 1394.67,
    ma20_status: "跌破均线",
    ma5_status: "跌破MA5",
    volume_status: "缩量",
    volume_change_pct: -15.2,
    alpha: -2.5,
    health_score: 25,
    k_line_pattern: "光脚大阴线",
    pattern_signal: "bearish",
    date: "2026-01-23",
    action_signal: "SELL",
    analysis: "跌破MA20均线，Alpha显著为负，量能萎缩。短期技术面转弱，建议减仓防守。",
    quote: "在别人贪婪时恐惧。(巴菲特)"
  },
  "002594": {
    symbol: "002594",
    current_price: 245.80,
    ma5: 238.50,
    ma20: 228.30,
    ma20_status: "站上均线",
    ma5_status: "站上MA5",
    volume_status: "放量",
    volume_change_pct: 35.8,
    alpha: 8.5,
    health_score: 85,
    k_line_pattern: "光头大阳线",
    pattern_signal: "bullish",
    date: "2026-01-23",
    action_signal: "STRONG_BUY",
    analysis: "强势突破MA20，量价配合完美，大幅跑赢大盘。新能源板块景气上行，建议积极配置。",
    quote: "趋势是你的朋友。(杰西·利弗莫尔)"
  },
  "002050": {
    symbol: "002050",
    current_price: 28.50,
    ma5: 27.20,
    ma20: 26.80,
    ma20_status: "站上均线",
    ma5_status: "站上MA5",
    volume_status: "持平",
    volume_change_pct: 2.1,
    alpha: 3.2,
    health_score: 72,
    k_line_pattern: "普通震荡",
    pattern_signal: "neutral",
    date: "2026-01-23",
    action_signal: "BUY",
    analysis: "站上MA5和MA20，整体趋势向上。量能持平说明观望情绪浓厚，建议持有等待。",
    quote: "时间是优秀企业的朋友。(巴菲特)"
  }
}

// ============================================
// Interfaces
// ============================================
interface PortfolioItem {
  id: string
  symbol: string
  name: string | null
  sector: string | null
  industry: string | null
  cost_basis: number | null
  shares: number
  notes: string | null
  created_at: string
  updated_at: string
  // 持久化字段（从数据库的缓存数据）
  last_price?: number | null
  last_health_score?: number | null
  last_updated_at?: string | null
  // 技术分析详细字段（用于完整显示）
  tech_ma20_status?: string | null
  tech_ma5_status?: string | null
  tech_volume_status?: string | null
  tech_volume_change_pct?: number | null
  tech_alpha?: number | null
  tech_k_line_pattern?: string | null
  tech_pattern_signal?: string | null
  tech_action_signal?: string | null
  tech_analysis_date?: string | null
}

interface WeeklyReview {
  id: string
  portfolio_id: string
  review_date: string
  start_price: number
  end_price: number
  price_change_pct: number
  ai_analysis: string
}

interface PortfolioResponse {
  items: PortfolioItem[]
  grouped: Record<string, PortfolioItem[]>
}

interface MarketSentiment {
  score: number
  label: string
  rsi: number
  date: string
}

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

export default function PortfolioPage() {
  const [symbol, setSymbol] = useState("")
  const [costBasis, setCostBasis] = useState("")
  const [shares, setShares] = useState("1")
  const [notes, setNotes] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isGeneratingReview, setIsGeneratingReview] = useState<string | null>(null)
  const [isGlobalReviewing, setIsGlobalReviewing] = useState(false)
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null)
  const [reviews, setReviews] = useState<Record<string, WeeklyReview[]>>({})
  const [isLoadingPortfolio, setIsLoadingPortfolio] = useState(true)
  const [selectedStockForReview, setSelectedStockForReview] = useState<string | null>(null)
  const [marketSentiment, setMarketSentiment] = useState<MarketSentiment | null>(null)
  const [technicalData, setTechnicalData] = useState<Record<string, TechnicalAnalysis>>({})
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [refreshingStocks, setRefreshingStocks] = useState<Set<string>>(new Set())
  const [reportText, setReportText] = useState<string | null>(null)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)
  // 新增：强制刷新状态（绕过缓存）
  const [forceRefresh, setForceRefresh] = useState(false)
  // 新增：市场状态提示
  const [marketStatus, setMarketStatus] = useState<{ isOpen: boolean; message: string }>({
    isOpen: false,
    message: ""
  })

  // 使用环境变量或默认值
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  // Debug: 打印 API_BASE 值
  console.log("[DEBUG] API_BASE =", API_BASE, "(env:", process.env.NEXT_PUBLIC_API_URL || "not set", ")")

  // ============================================
  // Data Loading Functions (with Cache Support)
  // ============================================

  /**
   * 加载市场情绪数据（带缓存）
   * - 如果在收盘后且有缓存，直接使用缓存
   * - 如果在开盘期间，缓存有效期为5分钟
   */
  const loadMarketSentiment = async (force: boolean = false) => {
    const startTime = performance.now()
    // 如果不是强制刷新，先检查缓存
    if (!force) {
      const cached = getSentimentCache()
      if (cached) {
        setMarketSentiment(cached)
        console.log("[Cache] Using cached sentiment data")
        return
      }
    }

    try {
      const fetchStart = performance.now()
      const response = await fetch(`${API_BASE}/api/v1/market/sentiment`)
      const fetchTime = performance.now() - fetchStart
      console.log(`[⏱️ SENTIMENT FETCH] took: ${fetchTime.toFixed(0)}ms`)

      if (response.ok) {
        const jsonStart = performance.now()
        const data = await response.json()
        const jsonTime = performance.now() - jsonStart
        console.log(`[⏱️ SENTIMENT JSON] took: ${jsonTime.toFixed(0)}ms`)

        setMarketSentiment(data)
        // 保存到缓存
        setSentimentCache(data)
      } else {
        // Use mock data if API fails
        console.log("Using mock sentiment data")
        setMarketSentiment(MOCK_SENTIMENT)
      }
    } catch (error) {
      console.log("Using mock sentiment data due to error:", error)
      setMarketSentiment(MOCK_SENTIMENT)
    } finally {
      const totalTime = performance.now() - startTime
      console.log(`[⏱️ SENTIMENT TOTAL] took: ${totalTime.toFixed(0)}ms`)
    }
  }

  /**
   * 加载技术分析数据（带缓存）
   * - 如果在收盘后且有缓存，直接使用缓存
   * - 如果在开盘期间，缓存有效期为2分钟
   * - 支持强制刷新（绕过缓存）
   */
  const loadTechnicalAnalysis = async (symbol: string, force: boolean = false) => {
    // 如果不是强制刷新，先检查缓存
    if (!force) {
      const cached = getTechnicalCache(symbol)
      if (cached) {
        setTechnicalData(prev => ({ ...prev, [symbol]: cached }))
        console.log(`[Cache] Using cached technical data for ${symbol}`)
        return cached
      }
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/market/technical/${symbol}`)
      if (response.ok) {
        const data = await response.json()
        setTechnicalData(prev => ({ ...prev, [symbol]: data }))
        // 保存到缓存
        setTechnicalCache(symbol, data)
        return data
      } else {
        console.warn(`API returned ${response.status} for ${symbol}`)
        // Fallback to mock data only on API error
        if (MOCK_TECHNICAL[symbol]) {
          console.log(`Using mock data for ${symbol}`)
          setTechnicalData(prev => ({ ...prev, [symbol]: MOCK_TECHNICAL[symbol] }))
          return MOCK_TECHNICAL[symbol]
        }
      }
    } catch (error) {
      console.error("Error loading technical analysis:", error)
      // Fallback to mock data on network error
      if (MOCK_TECHNICAL[symbol]) {
        console.log(`Using mock data for ${symbol} due to error`)
        setTechnicalData(prev => ({ ...prev, [symbol]: MOCK_TECHNICAL[symbol] }))
        return MOCK_TECHNICAL[symbol]
      }
    }
    return null
  }

  /**
   * 加载投资组合数据（Phase 1 - 秒开）
   * - 立即返回数据库中的数据（包含持久化的 last_price 等字段）
   * - 不等待技术分析 API 请求
   */
  const loadPortfolio = async () => {
    const startTime = performance.now()
    try {
      console.log(`[API] Fetching portfolio from ${API_BASE}/api/v1/portfolio`)

      const fetchStart = performance.now()
      const response = await fetch(`${API_BASE}/api/v1/portfolio`)
      const fetchTime = performance.now() - fetchStart
      console.log(`[⏱️ FETCH] fetch() call took: ${fetchTime.toFixed(0)}ms`)
      console.log(`[API] Response status: ${response.status}, ok: ${response.ok}`)

      if (!response.ok) {
        const errorText = await response.text()
        console.error(`[API] Error response:`, errorText)
        throw new Error(`Failed to load portfolio (HTTP ${response.status}): ${errorText}`)
      }

      const jsonStart = performance.now()

      const data = await response.json()
      const jsonTime = performance.now() - jsonStart
      console.log(`[⏱️ JSON] response.json() took: ${jsonTime.toFixed(0)}ms`)
      console.log(`[API] Portfolio data loaded: ${data.items.length} items, ${Object.keys(data.grouped || {}).length} sectors`)
      // 不要打印完整数据，避免浏览器卡顿
      // console.log(`[API] Portfolio data loaded:`, data)

      const setStateStart = performance.now()
      setPortfolio(data)
      const setStateTime = performance.now() - setStateStart
      console.log(`[⏱️ STATE] setPortfolio() took: ${setStateTime.toFixed(0)}ms`)

      // 保存到缓存（用于快速加载）
      setPortfolioCache(data)
    } catch (error) {
      console.error("Error loading portfolio:", error)
      // 如果 API 失败，尝试使用缓存
      const cached = getPortfolioCache()
      if (cached) {
        setPortfolio(cached)
        console.log("[Cache] Using cached portfolio data")
      } else {
        console.error("[Cache] No cached data available")
      }
    } finally {
      setIsLoadingPortfolio(false)
      const totalTime = performance.now() - startTime
      console.log(`[⏱️ TOTAL] loadPortfolio() took: ${totalTime.toFixed(0)}ms`)
    }
  }

  useEffect(() => {
    const loadData = async () => {
      const pageLoadStart = performance.now()
      console.log(`[⏱️ PERFORMANCE] Page load started at ${new Date().toLocaleTimeString()}`)

      // Phase 1: 立即加载 portfolio 和 sentiment（并行）
      // 使用缓存数据实现秒开
      const phase1Start = performance.now()
      await Promise.all([
        loadPortfolio(),
        loadMarketSentiment(forceRefresh)
      ])
      const phase1Time = performance.now() - phase1Start
      console.log(`[⏱️ PERFORMANCE] Phase 1 completed: ${phase1Time.toFixed(0)}ms`)

      // 更新市场状态提示
      const isOpen = isMarketOpen()
      setMarketStatus({
        isOpen,
        message: isOpen ? "🟢 市场开盘中" : "🔴 市场收盘（使用缓存数据）"
      })

      // 重置强制刷新标志
      if (forceRefresh) {
        setForceRefresh(false)
      }

      const totalTime = performance.now() - pageLoadStart
      console.log(`[⏱️ PERFORMANCE] Total page load time: ${totalTime.toFixed(0)}ms`)
    }
    loadData()
  }, [forceRefresh])

  // Phase 1.5: 当 portfolio 数据加载完成后，使用持久化数据初始化 technicalData
  useEffect(() => {
    if (portfolio?.items) {
      const phase15Start = performance.now()
      console.log(`[Phase 1.5] 🚀 Starting Phase 1.5 with ${portfolio.items.length} items`)

      const initialTechnicalData: Record<string, TechnicalAnalysis> = {}
      const cacheStart = performance.now()

      portfolio.items.forEach(item => {
        // 如果数据库中有完整的技术分析数据，直接使用
        if (item.last_price !== null && item.tech_action_signal !== null) {
          const techData: TechnicalAnalysis = {
            symbol: item.symbol,
            current_price: item.last_price!,
            ma5: 0,
            ma20: 0,
            ma20_status: item.tech_ma20_status || "未知",
            ma5_status: item.tech_ma5_status || "未知",
            volume_status: item.tech_volume_status || "未知",
            volume_change_pct: item.tech_volume_change_pct || 0,
            alpha: item.tech_alpha || 0,
            health_score: item.last_health_score!,
            k_line_pattern: item.tech_k_line_pattern || "未知",
            pattern_signal: item.tech_pattern_signal || "neutral",
            date: item.tech_analysis_date || new Date().toLocaleDateString('zh-CN'),
            action_signal: item.tech_action_signal || "HOLD",
            analysis: `数据更新于 ${item.tech_analysis_date || (item.last_updated_at ? new Date(item.last_updated_at).toLocaleDateString('zh-CN') : new Date().toLocaleDateString('zh-CN'))}`,
          }
          initialTechnicalData[item.symbol] = techData

          // 同时写入 LocalStorage 缓存，确保 Phase 2 能立即读取
          setTechnicalCache(item.symbol, techData)

          console.log(`[Phase 1.5] ✅ Loaded from DB & cached: ${item.symbol} (${item.tech_action_signal})`)
        }
      })

      const cacheTime = performance.now() - cacheStart
      console.log(`[Phase 1.5] 📦 Cache write took: ${cacheTime.toFixed(0)}ms`)

      // 如果有持久化数据，立即更新状态
      if (Object.keys(initialTechnicalData).length > 0) {
        const setStateStart = performance.now()
        setTechnicalData(prev => ({ ...prev, ...initialTechnicalData }))
        const setStateTime = performance.now() - setStateStart
        console.log(`[Phase 1.5] ⚡ setTechnicalData took: ${setStateTime.toFixed(0)}ms for ${Object.keys(initialTechnicalData).length} stocks`)
      }

      const totalPhase15Time = performance.now() - phase15Start
      console.log(`[Phase 1.5] ✅ Total Phase 1.5 took: ${totalPhase15Time.toFixed(0)}ms`)
    }
  }, [portfolio])

  // Phase 2: 后台静默更新技术分析数据（不阻塞 UI）
  useEffect(() => {
    if (portfolio?.items && portfolio.items.length > 0) {
      // 批量加载技术分析数据，避免并发过多
      const aShareItems = portfolio.items.filter(item => /^\d{6}$/.test(item.symbol))

      // 检查缓存数据的完整性（优先检查 LocalStorage，然后是 technicalData 状态）
      const hasCompleteCache = (symbol: string) => {
        // 首先检查 LocalStorage 缓存（快速检查，不依赖状态更新顺序）
        const cached = getTechnicalCache(symbol)
        if (cached && cached.ma20_status !== "数据加载中..." &&
                   cached.ma5_status !== "数据加载中..." &&
                   cached.k_line_pattern !== "数据加载中...") {
          return true
        }

        // 然后检查 Phase 1.5 已经加载到状态中的数据（从数据库）
        const stateData = technicalData[symbol]
        if (stateData && stateData.ma20_status !== "未知" && stateData.k_line_pattern !== "未知") {
          return true
        }

        return false
      }

      // 使用批量加载，每次最多 2 个并发
      const loadInBatches = async (items: typeof aShareItems, batchSize = 2) => {
        console.log(`[Phase 2] 🚀 Loading ${items.length} stocks in batches...`)
        for (let i = 0; i < items.length; i += batchSize) {
          const batch = items.slice(i, i + batchSize)
          console.log(`[Phase 2] 📦 Batch ${Math.floor(i/batchSize) + 1}:`, batch.map(i => i.symbol))
          await Promise.all(batch.map(item =>
            loadTechnicalAnalysis(item.symbol, forceRefresh)
          ))
        }
      }

      // 如果市场未开盘且所有股票都有完整缓存，跳过 API 请求
      if (!isMarketOpen()) {
        const cacheStatus = aShareItems.map(item => ({
          symbol: item.symbol,
          hasCache: hasCompleteCache(item.symbol)
        }))
        console.log("[Phase 2] 📊 Cache status:", cacheStatus)

        const allCached = aShareItems.every(item => hasCompleteCache(item.symbol))
        const uncachedSymbols = aShareItems.filter(item => !hasCompleteCache(item.symbol)).map(i => i.symbol)

        if (allCached) {
          console.log("[Phase 2] ✅ Market closed, using complete cached data for all stocks")
          return
        }

        // 即使市场收盘，也要为没有缓存的股票加载数据
        console.log("[Phase 2] 🔄 Market closed but loading uncached stocks:", uncachedSymbols)
        const itemsToLoad = aShareItems.filter(item => !hasCompleteCache(item.symbol))
        loadInBatches(itemsToLoad)
        return
      }

      loadInBatches(aShareItems)
    }
  }, [portfolio])

  // ============================================
  // Action Handlers
  // ============================================
  const handleAddStock = async () => {
    if (!symbol.trim()) {
      alert("请输入股票代码")
      return
    }

    // 验证 A 股代码格式（必须是 6 位数字）
    const trimmedSymbol = symbol.trim().toUpperCase()
    if (!/^\d{6}$/.test(trimmedSymbol)) {
      alert("无效的 A 股代码格式\n\nA 股代码必须是 6 位数字\n例如：600519（贵州茅台）、000001（平安银行）")
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/api/v1/portfolio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol.toUpperCase().trim(),
          cost_basis: costBasis ? parseFloat(costBasis) : null,
          shares: parseInt(shares) || 1,
          notes: notes || null,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "添加失败")
      }

      setSymbol("")
      setCostBasis("")
      setShares("1")
      setNotes("")
      await loadPortfolio()
    } catch (error) {
      console.error("Error adding stock:", error)
      alert(`添加失败: ${error instanceof Error ? error.message : "未知错误"}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteStock = async (id: string) => {
    if (!confirm("确定要删除这只股票吗？")) return

    try {
      const response = await fetch(`${API_BASE}/api/v1/portfolio/${id}`, {
        method: "DELETE",
      })

      if (!response.ok) throw new Error("删除失败")
      await loadPortfolio()
    } catch (error) {
      console.error("Error deleting stock:", error)
      alert(`删除失败: ${error instanceof Error ? error.message : "未知错误"}`)
    }
  }

  const handleGenerateReview = async (portfolioId: string, stockSymbol: string) => {
    setIsGeneratingReview(portfolioId)

    try {
      const response = await fetch(`${API_BASE}/api/v1/portfolio/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          portfolio_id: portfolioId,
          days: 7,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "生成复盘失败")
      }

      const review = await response.json()
      setReviews((prev) => ({
        ...prev,
        [portfolioId]: [review, ...(prev[portfolioId] || [])],
      }))

      alert(`复盘生成成功！${stockSymbol} 过去7天 ${review.price_change_pct >= 0 ? "上涨" : "下跌"} ${Math.abs(review.price_change_pct).toFixed(2)}%`)
    } catch (error) {
      console.error("Error generating review:", error)
      alert(`生成失败: ${error instanceof Error ? error.message : "未知错误"}`)
    } finally {
      setIsGeneratingReview(null)
    }
  }

  const handleGlobalReview = async () => {
    setIsGlobalReviewing(true)
    try {
      // Refresh market sentiment
      await loadMarketSentiment()

      // Generate reviews for all stocks
      if (portfolio?.items) {
        for (const item of portfolio.items) {
          await handleGenerateReview(item.id, item.symbol)
        }
      }
    } finally {
      setIsGlobalReviewing(false)
    }
  }

  const toggleRowExpansion = (id: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedRows(newExpanded)
  }

  const handleRefreshStock = async (stockSymbol: string) => {
    console.log(`[🔄 REFRESH] Starting refresh for ${stockSymbol}`)
    setRefreshingStocks(prev => new Set(prev).add(stockSymbol))

    try {
      const apiUrl = `${API_BASE}/api/v1/market/technical/${stockSymbol}`
      console.log(`[🔄 REFRESH] Fetching from: ${apiUrl}`)

      // 使用强制刷新（绕过缓存）
      const fetchStart = performance.now()
      const response = await fetch(apiUrl)
      const fetchTime = performance.now() - fetchStart
      console.log(`[🔄 REFRESH] Fetch took: ${fetchTime.toFixed(0)}ms, status: ${response.status}`)

      if (response.ok) {
        const jsonStart = performance.now()
        const data = await response.json()
        const jsonTime = performance.now() - jsonStart
        console.log(`[🔄 REFRESH] JSON parse took: ${jsonTime.toFixed(0)}ms`)
        console.log(`[🔄 REFRESH] Received data:`, data)

        setTechnicalData(prev => ({ ...prev, [stockSymbol]: data }))
        // 更新缓存
        setTechnicalCache(stockSymbol, data)
        console.log(`[🔄 REFRESH] ✅ Success: ${stockSymbol} - ${data.action_signal}, price: ${data.current_price}`)
      } else {
        const errorText = await response.text()
        console.error(`[🔄 REFRESH] ❌ Failed: HTTP ${response.status}, body:`, errorText)
        alert(`刷新失败 (${response.status}): ${errorText}`)
      }
    } catch (error) {
      console.error(`[🔄 REFRESH] ❌ Error refreshing ${stockSymbol}:`, error)
      alert(`刷新失败: ${error instanceof Error ? error.message : '未知错误'}`)
    } finally {
      setRefreshingStocks(prev => {
        const newSet = new Set(prev)
        newSet.delete(stockSymbol)
        return newSet
      })
      console.log(`[🔄 REFRESH] Finished refresh for ${stockSymbol}`)
    }
  }

  /**
   * 强制刷新所有数据（绕过缓存）
   */
  const handleForceRefreshAll = () => {
    // 清除所有缓存
    clearSentimentCache()
    clearTechnicalCache()

    // 设置强制刷新标志
    setForceRefresh(true)

    console.log("[Force Refresh] All caches cleared, reloading data...")
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    try {
      const response = await fetch(`${API_BASE}/api/v1/report/generate`)
      if (response.ok) {
        const data = await response.json()
        setReportText(data.report)
        setShowReportModal(true)
      } else {
        console.error("Failed to generate report")
      }
    } catch (error) {
      console.error("Error generating report:", error)
    } finally {
      setIsGeneratingReport(false)
    }
  }

  const handleCopyReport = () => {
    if (reportText) {
      navigator.clipboard.writeText(reportText)
      alert("报告已复制到剪贴板")
    }
  }

  const handleDownloadReport = () => {
    if (reportText) {
      const blob = new Blob([reportText], { type: "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `投资组合复盘报告_${new Date().toISOString().slice(0, 10)}.txt`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  // ============================================
  // UI Helper Functions
  // ============================================
  const getSentimentColor = (score: number) => {
    if (score >= 80) return { bar: "bg-red-500", text: "text-red-400", bg: "bg-red-500/20" }
    if (score >= 60) return { bar: "bg-orange-500", text: "text-orange-400", bg: "bg-orange-500/20" }
    if (score >= 40) return { bar: "bg-yellow-500", text: "text-yellow-400", bg: "bg-yellow-500/20" }
    if (score >= 20) return { bar: "bg-blue-500", text: "text-blue-400", bg: "bg-blue-500/20" }
    return { bar: "bg-emerald-500", text: "text-emerald-400", bg: "bg-emerald-500/20" }
  }

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

  const getPatternBadgeColor = (signal: string) => {
    if (signal === "bullish") return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
    if (signal === "bearish") return "bg-red-500/20 text-red-400 border-red-500/30"
    if (signal === "warning") return "bg-amber-500/20 text-amber-400 border-amber-500/30"
    return "bg-slate-500/20 text-slate-400 border-slate-500/30"
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

  // A股配色：红涨绿跌
  const getPriceChangeColor = (change: number) => {
    return change >= 0 ? "text-red-400" : "text-emerald-400"
  }

  const getVolumeBadgeColor = (status: string) => {
    if (status === "放量") return "bg-red-500/20 text-red-400 border-red-500/30"
    if (status === "缩量") return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
    return "bg-slate-500/20 text-slate-400 border-slate-500/30"
  }

  // ============================================
  // Render
  // ============================================
  return (
    <div className="space-y-6">
      {/* ========================================
          Header with Action Buttons
          ======================================== */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <Zap className="w-8 h-8 text-amber-400" />
            智能复盘中心
          </h1>
          <div className="mt-2 flex items-center gap-3">
            <p className="text-slate-400">Smart Review Center - AI驱动的投资组合分析</p>
            {marketStatus.message && (
              <Badge variant="outline" className={marketStatus.isOpen ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" : "bg-slate-500/20 text-slate-400 border-slate-500/30"}>
                {marketStatus.message}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={handleForceRefreshAll}
            disabled={refreshingStocks.size > 0}
            variant="outline"
            className="border-blue-600 text-blue-300 hover:bg-blue-900 hover:text-white"
            title="清除缓存并强制刷新所有数据"
          >
            {refreshingStocks.size > 0 ? (
              <React.Fragment>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                刷新中...
              </React.Fragment>
            ) : (
              <React.Fragment>
                <RefreshCw className="w-4 h-4 mr-2" />
                刷新全部
              </React.Fragment>
            )}
          </Button>
          <Button
            onClick={handleGenerateReport}
            disabled={isGeneratingReport}
            variant="outline"
            className="border-emerald-600 text-emerald-300 hover:bg-emerald-900 hover:text-white"
          >
            {isGeneratingReport ? (
              <React.Fragment>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                生成中...
              </React.Fragment>
            ) : (
              <React.Fragment>
                <Sparkles className="w-4 h-4 mr-2" />
                导出报告
              </React.Fragment>
            )}
          </Button>
          <Button
            onClick={handleGlobalReview}
            disabled={isGlobalReviewing}
            className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-medium px-6"
          >
            {isGlobalReviewing ? (
              <React.Fragment>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                AI 分析中...
              </React.Fragment>
            ) : (
              <React.Fragment>
                <Play className="w-4 h-4 mr-2" />
                立即复盘
              </React.Fragment>
            )}
          </Button>
        </div>
      </div>

      {/* ========================================
          Module 1: Macro Sentiment Bar
          ======================================== */}
      {marketSentiment && (
        <Card className="bg-gradient-to-r from-slate-900/80 to-slate-800/80 border-slate-700 backdrop-blur-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-full ${getSentimentColor(marketSentiment.score).bg}`}>
                  <Activity className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-slate-200">市场贪婪指数</div>
                  <div className="text-sm text-slate-500">Market Greed Index (RSI: {marketSentiment.rsi.toFixed(1)})</div>
                </div>
              </div>

              <div className="flex items-center gap-6">
                {/* Score Display */}
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getSentimentColor(marketSentiment.score).text}`}>
                    {marketSentiment.score.toFixed(0)}
                  </div>
                  <div className={`text-sm font-medium mt-1 ${getSentimentColor(marketSentiment.score).text}`}>
                    {marketSentiment.label}
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-64">
                  <div className="relative h-3 w-full overflow-hidden rounded-full bg-slate-700">
                    <div
                      className={`h-full transition-all ${getSentimentColor(marketSentiment.score).bar}`}
                      style={{ width: `${marketSentiment.score}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-xs text-slate-500">
                    <span>恐慌</span>
                    <span>中性</span>
                    <span>贪婪</span>
                  </div>
                </div>

                {/* Risk/Opportunity Indicator */}
                <div className={`px-4 py-2 rounded-lg ${
                  marketSentiment.score >= 80 ? "bg-red-500/20 border border-red-500/30" :
                  marketSentiment.score <= 20 ? "bg-emerald-500/20 border border-emerald-500/30" :
                  "bg-slate-700/30 border border-slate-600/30"
                }`}>
                  <div className="text-sm font-medium text-slate-200">
                    {marketSentiment.score >= 80 && "⚠️ 风险积聚，建议防守"}
                    {marketSentiment.score <= 20 && "💎 恐慌触底，建议关注"}
                    {marketSentiment.score > 20 && marketSentiment.score < 80 && "⚖️ 市场中性，均衡配置"}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ========================================
          Add Stock Card (Simplified)
          ======================================== */}
      <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100 text-lg">
            <Plus className="w-5 h-5 text-blue-400" />
            添加股票
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="股票代码 (如: 600519, AAPL)"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={isLoading}
              className="bg-slate-950/50 border-slate-700 text-slate-100 max-w-xs"
              onKeyDown={(e) => e.key === "Enter" && handleAddStock()}
            />
            <Input
              type="number"
              step="0.01"
              placeholder="成本价"
              value={costBasis}
              onChange={(e) => setCostBasis(e.target.value)}
              disabled={isLoading}
              className="bg-slate-950/50 border-slate-700 text-slate-100 max-w-xs"
            />
            <Button
              onClick={handleAddStock}
              disabled={!symbol.trim() || isLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              添加
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ========================================
          Module 2: Portfolio Table
          ======================================== */}
      {isLoadingPortfolio ? (
        <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
          <CardContent className="py-16">
            <div className="flex flex-col items-center justify-center space-y-4">
              <Loader2 className="w-12 h-12 animate-spin text-blue-400" />
              <div className="text-center">
                <p className="text-lg font-medium text-slate-200">正在加载投资组合...</p>
                <p className="text-sm text-slate-500 mt-1">从云端获取数据</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : portfolio && portfolio.items.length > 0 ? (
        <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-400" />
              持仓透视表
              <span className="text-sm font-normal text-slate-500">
                ({portfolio.items.length} 只股票)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-slate-400 w-32">标的</TableHead>
                  <TableHead className="text-slate-400 w-32">现价/涨跌</TableHead>
                  <TableHead className="text-slate-400 w-40">技术信号</TableHead>
                  <TableHead className="text-slate-400 w-32">均线状态</TableHead>
                  <TableHead className="text-slate-400 w-28">健康分</TableHead>
                  <TableHead className="text-slate-400 w-32">操作建议</TableHead>
                  <TableHead className="text-slate-400 w-24">K线形态</TableHead>
                  <TableHead className="text-slate-400 text-right w-24">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {portfolio.items.map((item) => {
                  const tech = technicalData[item.symbol]
                  const isExpanded = expandedRows.has(item.id)
                  const actionBadge = getActionSignalBadge(tech?.action_signal)

                  return (
                    <React.Fragment key={item.id}>
                      <TableRow
                        className="hover:bg-slate-800/50 cursor-pointer"
                        onClick={() => toggleRowExpansion(item.id)}
                      >
                        {/* 标的 */}
                        <TableCell>
                          <div>
                            <div className="font-bold text-blue-400">{item.symbol}</div>
                            <div className="text-xs text-slate-500">{item.name}</div>
                            {item.sector && (
                              <Badge variant="outline" className="mt-1 text-xs bg-slate-800 border-slate-700 text-slate-400">
                                {item.sector}
                              </Badge>
                            )}
                          </div>
                        </TableCell>

                        {/* 现价/涨跌 - A股红涨绿跌 */}
                        <TableCell>
                          {tech ? (
                            <div>
                              <div className="text-lg font-semibold text-slate-200">
                                ¥{tech.current_price.toFixed(2)}
                              </div>
                              <div className={`text-sm font-medium ${getPriceChangeColor(tech.alpha)}`}>
                                {tech.alpha >= 0 ? "+" : ""}{tech.alpha.toFixed(2)}%
                                <span className="text-xs text-slate-500 ml-1">Alpha</span>
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </TableCell>

                        {/* 技术信号 */}
                        <TableCell>
                          {tech ? (
                            <div className="flex flex-wrap gap-1">
                              <Badge className={getVolumeBadgeColor(tech.volume_status)}>
                                {tech.volume_status}
                              </Badge>
                              {tech.volume_change_pct !== 0 && (
                                <span className={`text-xs ${tech.volume_change_pct > 0 ? "text-red-400" : "text-emerald-400"}`}>
                                  {tech.volume_change_pct > 0 ? "+" : ""}{tech.volume_change_pct.toFixed(0)}%
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </TableCell>

                        {/* 均线状态 */}
                        <TableCell>
                          {tech ? (
                            <div className="text-xs space-y-1">
                              <div className={`flex items-center gap-1.5 ${tech.ma20_status === "站上均线" ? "text-red-400" : "text-emerald-400"}`}>
                                <div className={`w-2 h-2 rounded-full ${tech.ma20_status === "站上均线" ? "bg-red-400" : "bg-emerald-400"}`} />
                                MA20: {tech.ma20_status}
                              </div>
                              <div className={`flex items-center gap-1.5 ${tech.ma5_status === "站上MA5" ? "text-red-400" : "text-emerald-400"}`}>
                                <div className={`w-2 h-2 rounded-full ${tech.ma5_status === "站上MA5" ? "bg-red-400" : "bg-emerald-400"}`} />
                                MA5: {tech.ma5_status}
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </TableCell>

                        {/* 健康评分 */}
                        <TableCell>
                          {tech ? (
                            <div className="flex items-center gap-2">
                              <div className={`relative w-12 h-12`}>
                                <svg className="w-full h-full transform -rotate-90">
                                  <circle
                                    cx="24"
                                    cy="24"
                                    r="20"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                    className="text-slate-700"
                                  />
                                  <circle
                                    cx="24"
                                    cy="24"
                                    r="20"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                    strokeDasharray={`${tech.health_score * 1.256} 125.6`}
                                    className={getHealthScoreColor(tech.health_score)}
                                    strokeLinecap="round"
                                  />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                  <span className={`text-sm font-bold ${getHealthScoreColor(tech.health_score)}`}>
                                    {tech.health_score.toFixed(0)}
                                  </span>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </TableCell>

                        {/* 操作建议 */}
                        <TableCell>
                          <Badge className={actionBadge.color}>
                            {actionBadge.label}
                          </Badge>
                        </TableCell>

                        {/* K线形态 */}
                        <TableCell>
                          {tech ? (
                            <Badge className={getPatternBadgeColor(tech.pattern_signal)}>
                              {tech.k_line_pattern}
                            </Badge>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </TableCell>

                        {/* 操作 */}
                        <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleRefreshStock(item.symbol)
                              }}
                              disabled={refreshingStocks.has(item.symbol)}
                              className="text-blue-400 hover:text-blue-300 hover:bg-blue-900/20"
                              title="刷新实时数据"
                            >
                              {refreshingStocks.has(item.symbol) ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <RefreshCw className="w-4 h-4" />
                              )}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleGenerateReview(item.id, item.symbol)
                              }}
                              disabled={isGeneratingReview === item.id}
                              className="text-amber-400 hover:text-amber-300 hover:bg-amber-900/20"
                            >
                              {isGeneratingReview === item.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Sparkles className="w-4 h-4" />
                              )}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDeleteStock(item.id)
                              }}
                              className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>

                      {/* Expandable Details Row */}
                      {isExpanded && tech && (
                        <TableRow>
                          <TableCell colSpan={8} className="bg-slate-950/50">
                            <div className="py-4 px-2 space-y-4">
                              {/* AI Analysis Card */}
                              <Card className="bg-slate-900/80 border-slate-700">
                                <CardHeader className="pb-3">
                                  <CardTitle className="text-sm text-slate-300 flex items-center gap-2">
                                    <Sparkles className="w-4 h-4 text-amber-400" />
                                    AI 深度分析
                                  </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                  <p className="text-sm text-slate-300 leading-relaxed">
                                    {tech.analysis || "暂无分析数据"}
                                  </p>
                                </CardContent>
                              </Card>

                              {/* Technical Details */}
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800">
                                  <div className="text-xs text-slate-500">MA5</div>
                                  <div className="text-sm font-semibold text-slate-200">¥{tech.ma5.toFixed(2)}</div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800">
                                  <div className="text-xs text-slate-500">MA20</div>
                                  <div className="text-sm font-semibold text-slate-200">¥{tech.ma20.toFixed(2)}</div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800">
                                  <div className="text-xs text-slate-500">量能变化</div>
                                  <div className={`text-sm font-semibold ${tech.volume_change_pct > 0 ? "text-red-400" : "text-emerald-400"}`}>
                                    {tech.volume_change_pct > 0 ? "+" : ""}{tech.volume_change_pct.toFixed(1)}%
                                  </div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800">
                                  <div className="text-xs text-slate-500">更新日期</div>
                                  <div className="text-sm font-semibold text-slate-200">{tech.date}</div>
                                </div>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-slate-900/50 border-slate-800 backdrop-blur-sm">
          <CardContent className="py-12 text-center text-slate-400">
            <Building2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>暂无持仓股票，请添加第一只股票开始分析</p>
          </CardContent>
        </Card>
      )}

      {/* ========================================
          Footer Legend
          ======================================== */}
      <Card className="bg-slate-900/30 border-slate-800">
        <CardContent className="py-4">
          <div className="flex items-center justify-center gap-6 text-xs text-slate-500">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-red-400" />
              <span>A股红涨</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>A股绿跌</span>
            </div>
            <div className="flex items-center gap-1">
              <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">强烈买入</Badge>
            </div>
            <div className="flex items-center gap-1">
              <Badge className="bg-red-500/20 text-red-400 text-xs">强烈卖出</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ========================================
          Report Modal
          ======================================== */}
      {showReportModal && reportText && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <h2 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                投资组合复盘报告
              </h2>
              <button
                onClick={() => setShowReportModal(false)}
                className="text-slate-400 hover:text-slate-200 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-4">
              <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                {reportText}
              </pre>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-700">
              <Button
                onClick={handleCopyReport}
                variant="outline"
                className="border-slate-600 text-slate-300 hover:bg-slate-800"
              >
                复制到剪贴板
              </Button>
              <Button
                onClick={handleDownloadReport}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                下载报告
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
