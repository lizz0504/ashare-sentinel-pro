"use client"

import React, { useState, useEffect, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Eye, X, TrendingUp, Trash2, ChevronRight, FileText, RefreshCw, Loader2, Sparkles } from "lucide-react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getMergedAnalysisHistory, deleteStockAllRecords, type AnalysisRecord } from "@/lib/utils/analysisHistory"
import { ProfessionalPanel } from "@/components/portfolio/ProfessionalPanel"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// ============================================
// Types
// ============================================

interface StockWithPrice extends Omit<AnalysisRecord, 'current_price'> {
  current_price?: number
  change?: number
  turnover_rate?: string
  advanced_metrics?: {
    technical: {
      rps: number
      deviation: number
      ma200_deviation: number
    }
    capital: {
      purity: number
      control_duration: number
      accumulation_strength: number
    }
    fundamental: {
      peg: number | null
      growth_rate: number
      beta: number
    }
    radar: {
      value_score: number
      growth_score: number
      safety_score: number
      dividend_score: number
      trend_score: number
    }
  }
}

// ============================================
// Components
// ============================================

function SuggestionBadge({ verdict, conviction }: { verdict: string; conviction: string }) {
  if (verdict.includes("买入")) {
    return (
      <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50 hover:bg-emerald-500/30">
        {verdict} {conviction}
      </Badge>
    )
  }
  if (verdict.includes("卖出")) {
    return (
      <Badge className="bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/30">
        {verdict} {conviction}
      </Badge>
    )
  }
  return (
    <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/50 hover:bg-blue-500/30">
      {verdict} {conviction}
    </Badge>
  )
}

function StockRow({
  stock,
  isExpanded,
  is_selected,
  onToggle,
  onViewReport,
  onDelete,
  isLoading,
  onSelectStock
}: {
  stock: StockWithPrice
  isExpanded: boolean
  is_selected: boolean
  onToggle: () => void
  onViewReport: () => void
  onDelete: () => void
  isLoading: boolean
  onSelectStock: () => void
}) {
  return (
    <Card className={`bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-colors overflow-hidden ${is_selected ? 'ring-2 ring-blue-500' : ''}`}>
      <CardContent className="p-0">
        <div className="flex items-center gap-3 p-3 hover:bg-slate-800/50 transition-colors cursor-pointer" onClick={() => { onSelectStock(); onToggle(); }}>
          <ChevronRight className={`w-4 h-4 text-slate-500 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`} />

          <div className="flex-1 grid grid-cols-12 gap-3 items-center">
            <div className="col-span-3">
              <div className="font-mono font-bold text-blue-400 text-sm">{stock.symbol}</div>
              <div className="text-xs text-slate-400 truncate">{stock.stock_name}</div>
            </div>

            <div className="col-span-2 text-right">
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-slate-500 mx-auto" />
              ) : (
                <>
                  <div className={`text-base font-bold ${stock.change && stock.change >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                    ¥{stock.current_price ? stock.current_price.toFixed(2) : "--"}
                  </div>
                  {stock.change !== undefined && (
                    <div className={`text-xs ${stock.change >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="col-span-4 flex gap-2 text-xs">
              {stock.technical_score !== null && (
                <>
                  <div className="flex flex-col items-center">
                    <span className="text-slate-500 text-xs">技</span>
                    <span className={`font-semibold ${stock.technical_score >= 70 ? 'text-red-400' : 'text-slate-400'}`}>
                      {stock.technical_score}
                    </span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="text-slate-500 text-xs">基</span>
                    <span className={`font-semibold ${stock.fundamental_score && stock.fundamental_score >= 70 ? 'text-red-400' : 'text-slate-400'}`}>
                      {stock.fundamental_score ?? "--"}
                    </span>
                  </div>
                </>
              )}
            </div>

            <div className="col-span-2">
              <SuggestionBadge
                verdict={stock.verdict_chinese}
                conviction={stock.conviction_stars}
              />
            </div>

            <div className="col-span-1 flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); onDelete(); }}
                className="text-slate-500 hover:text-red-400 hover:bg-red-500/10 h-8 w-8 p-0"
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>

        {isExpanded && (
          <div className="border-t border-slate-800 bg-slate-950/50">
            <div className="p-4">
              <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                分析报告
              </h4>
              <Card className="bg-slate-900 border-slate-800">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs border-blue-500/50 text-blue-400">
                        {stock.type === 'dashboard' ? '📈 Dashboard' : '👥 IC投委会'}
                      </Badge>
                      <span className="text-sm text-slate-500">
                        {new Date(stock.timestamp).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    <SuggestionBadge
                      verdict={stock.verdict_chinese}
                      conviction={stock.conviction_stars}
                    />
                  </div>
                  <p className="text-sm text-slate-400 mb-3">{stock.verdict_chinese}</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onViewReport}
                    className="text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 h-8"
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    查看完整报告
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ReportDrawer({
  isOpen,
  onClose,
  stock
}: {
  isOpen: boolean
  onClose: () => void
  stock: StockWithPrice | null
}) {
  const [isFetching, setIsFetching] = useState(false)
  const [fetchedReport, setFetchedReport] = useState<any>(null)
  const [stockHistory, setStockHistory] = useState<AnalysisRecord[]>([])
  const [dbReports, setDbReports] = useState<any[]>([]) // 新增：数据库中的历史报告
  const [loadingDbReports, setLoadingDbReports] = useState(false) // 新增：加载状态

  // 当打开 drawer 时，加载该股票的所有历史记录（本地 + 数据库）
  useEffect(() => {
    if (isOpen && stock) {
      // 加载本地历史记录
      const { getStockHistory } = require('@/lib/utils/analysisHistory')
      const localHistory = getStockHistory(stock.symbol)
      setStockHistory(localHistory)

      // 加载数据库中的历史报告
      const fetchDbReports = async () => {
        setLoadingDbReports(true)
        try {
          const response = await fetch(`${API_BASE}/api/v1/reports/stock/${stock.symbol}?limit=50`)
          if (response.ok) {
            const data = await response.json()
            setDbReports(data.reports || [])
          } else {
            console.error('[ReportDrawer] Failed to fetch DB reports:', response.status)
            setDbReports([])
          }
        } catch (error) {
          console.error('[ReportDrawer] Error fetching DB reports:', error)
          setDbReports([])
        } finally {
          setLoadingDbReports(false)
        }
      }

      fetchDbReports()
    }
  }, [isOpen, stock])

  // 合并本地和数据库的历史记录
  const allHistoricalRecords = useMemo(() => {
    const combined: AnalysisRecord[] = []

    // 添加本地历史记录
    combined.push(...stockHistory)

    // 添加数据库中的报告，转换成 AnalysisRecord 格式
    dbReports.forEach((dbReport) => {
      // 检查是否已存在相同的记录（通过时间戳和类型）
      const exists = combined.some(
        record => record.timestamp === new Date(dbReport.created_at).getTime()
      )

      if (!exists) {
        combined.push({
          id: dbReport.id,
          type: 'ic_meeting',
          symbol: dbReport.stock_code,
          stock_name: dbReport.stock_name,
          current_price: dbReport.current_price || stock?.current_price || 0,
          technical_score: dbReport.score_technical,
          fundamental_score: dbReport.score_value,
          verdict_chinese: dbReport.verdict,
          conviction_stars: dbReport.conviction_stars,
          timestamp: new Date(dbReport.created_at).getTime(),
          full_report: JSON.stringify(dbReport, null, 2) // 存储完整的数据库报告
        })
      }
    })

    // 按时间戳排序（最新的在前）
    return combined.sort((a, b) => b.timestamp - a.timestamp)
  }, [stockHistory, dbReports, stock])

  // 当打开 drawer 且没有 full_report 时，自动获取 IC 投委会报告
  useEffect(() => {
    if (isOpen && stock && !stock.full_report && !isFetching && !fetchedReport) {
      const fetchICReport = async () => {
        setIsFetching(true)
        console.log('[ReportDrawer] Fetching IC report for', stock.symbol)

        try {
          const response = await fetch(`${API_BASE}/api/v1/ic/meeting`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: stock.symbol, save_to_db: false })
          })

          if (response.ok) {
            const data = await response.json()
            console.log('[ReportDrawer] IC report fetched successfully')
            setFetchedReport(data)

            // 自动保存到 localStorage
            const { addAnalysisRecord } = await import('@/lib/utils/analysisHistory')
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
          } else {
            console.error('[ReportDrawer] Failed to fetch IC report')
          }
        } catch (error) {
          console.error('[ReportDrawer] Error fetching IC report:', error)
        } finally {
          setIsFetching(false)
        }
      }

      fetchICReport()
    }
  }, [isOpen, stock, isFetching, fetchedReport])

  if (!isOpen || !stock) return null

  // 如果正在获取，显示加载状态
  if (isFetching && !stock.full_report) {
    return (
      <>
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={onClose} />
        <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl z-50">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900">
            <div>
              <h3 className="text-lg font-bold text-slate-100">{stock.stock_name}</h3>
              <p className="text-sm text-slate-500 font-mono">{stock.symbol}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-400 hover:text-slate-100">
              <X className="w-6 h-6" />
            </Button>
          </div>
          <div className="h-[calc(100vh-72px)] flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
              <p className="text-slate-400">正在获取 IC 投委会完整报告...</p>
              <p className="text-sm text-slate-500 mt-2">预计需要 40-60 秒</p>
            </div>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-4xl bg-slate-950 border-l border-slate-800 shadow-2xl z-50 flex">
        {/* 左侧：历史记录列表 */}
        <div className="w-80 border-r border-slate-800 flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-900">
            <h3 className="text-lg font-bold text-slate-100">{stock.stock_name}</h3>
            <p className="text-sm text-slate-500 font-mono">{stock.symbol}</p>
            <p className="text-xs text-slate-600 mt-1">
              共 {allHistoricalRecords.length} 条分析记录
              {loadingDbReports && <span className="ml-2 text-blue-400">加载中...</span>}
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {allHistoricalRecords.map((record, index) => (
              <Card
                key={`${record.id}-${record.timestamp}`}
                className={`bg-slate-900/50 border-slate-800 hover:border-slate-700 cursor-pointer transition-colors ${index === 0 ? 'ring-2 ring-blue-500' : ''}`}
              >
                <CardContent className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="outline" className="text-xs border-blue-500/50 text-blue-400">
                      {record.type === 'dashboard' ? '📈 Dashboard' : '👥 IC投委会'}
                    </Badge>
                    <span className="text-xs text-slate-500">
                      {new Date(record.timestamp).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-slate-100 mb-1">
                    {record.verdict_chinese} {record.conviction_stars}
                  </div>
                  <div className="text-xs text-slate-500 flex justify-between">
                    <span>技: {record.technical_score ?? 'N/A'}</span>
                    <span>基: {record.fundamental_score ?? 'N/A'}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
            {allHistoricalRecords.length === 0 && !loadingDbReports && (
              <div className="p-8 text-center text-slate-500 text-sm">
                暂无历史分析记录
              </div>
            )}
          </div>
        </div>

        {/* 右侧：当前选中的报告详情 */}
        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900">
            <div className="text-sm text-slate-400">
              最新分析 · {new Date(stock.timestamp).toLocaleString('zh-CN')}
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-400 hover:text-slate-100">
              <X className="w-6 h-6" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5 prose prose-invert prose-headings:text-slate-100 prose-p:text-slate-300 prose-strong:text-slate-100 max-w-none">
            <ReportContent stock={stock} fetchedReport={fetchedReport} />
          </div>
        </div>
      </div>
    </>
  )
}

// 抽离报告内容渲染逻辑
function ReportContent({ stock, fetchedReport }: { stock: StockWithPrice; fetchedReport: any }) {
  let reportContent = ""

  // 调试日志
  if (typeof window !== 'undefined') {
    console.log('[ReportContent] Stock:', stock.symbol, stock.stock_name)
    console.log('[ReportContent] Has full_report:', !!stock.full_report)
    console.log('[ReportContent] Has fetchedReport:', !!fetchedReport)
  }

  try {
    // 优先使用 fetchedReport，其次使用 full_report，最后使用 stock 数据
    const reportData = fetchedReport || (stock.full_report ? JSON.parse(stock.full_report) : stock)
    reportContent = formatReportAsMarkdown(reportData, stock)
  } catch (error) {
    console.error("[ReportContent] Failed to parse report:", error)
    reportContent = formatReportAsMarkdown(stock, stock)
  }

  // 如果报告内容为空，生成默认报告
  if (!reportContent || reportContent.trim().length === 0) {
    reportContent = `# ${stock.stock_name} (${stock.symbol})

**判决**: ${stock.verdict_chinese} ${stock.conviction_stars}

**技术评分**: ${stock.technical_score ?? "N/A"}/100
**基本面评分**: ${stock.fundamental_score ?? "N/A"}/100

**分析时间**: ${new Date(stock.timestamp).toLocaleString('zh-CN')}

**类型**: ${stock.type === 'dashboard' ? '📈 Dashboard 分析' : '👥 IC 投委会会议'}

---

*报告数据不完整，请重新分析以获取完整报告。*`
  }

  return <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportContent}</ReactMarkdown>
}

function formatReportAsMarkdown(data: any, stock: StockWithPrice): string {
  // 调试日志
  if (typeof window !== 'undefined') {
    console.log('[formatReportAsMarkdown] Input data keys:', Object.keys(data))
    console.log('[formatReportAsMarkdown] Has cathie_wood:', !!data.cathie_wood, data.cathie_wood?.length)
    console.log('[formatReportAsMarkdown] Has final_verdict:', !!data.final_verdict)
    if (data.final_verdict) {
      console.log('[formatReportAsMarkdown] final_verdict keys:', Object.keys(data.final_verdict))
      console.log('[formatReportAsMarkdown] synthesis value:', data.final_verdict.synthesis)
    }
  }

  // 判断是否为 IC 投委会报告（更宽松的条件）
  const hasICReport = data.cathie_wood || data.nancy_pelosi || data.warren_buffett || data.final_verdict

  if (hasICReport) {
    // 处理 final_verdict 中的空字符串
    const fv = data.final_verdict || {}
    const keyConsiderations = fv.key_considerations || fv.considerations || []
    const invertRisks = fv.invert_risks || fv.risk_factors || []
    const synthesis = fv.synthesis?.trim() || '暂无综合观点'

    return `# AI投委会会议纪要

**股票代码**: ${data.symbol}
**股票名称**: ${data.stock_name}
**当前价格**: ¥${data.current_price}
${data.turnover_rate ? `**换手率**: ${data.turnover_rate}` : ""}
**分析时间**: ${new Date(stock.timestamp).toLocaleString('zh-CN')}

---

## 最终判决

**${data.verdict_chinese}** ${data.conviction_stars}

### 关键考虑因素
${keyConsiderations.length > 0 ? keyConsiderations.map((item: string) => `- ${item}`).join('\n') : '暂无'}

### 反向风险
${invertRisks.length > 0 ? invertRisks.map((item: string) => `- ${item}`).join('\n') : '暂无'}

### 综合观点
${synthesis}

---

## 分析师观点

### 1. Cathie Wood (成长与颠覆)

${data.cathie_wood?.trim() || '暂无分析'}

---

### 2. Nancy Pelosi (权力与政策)

${data.nancy_pelosi?.trim() || '暂无分析'}

---

### 3. Warren Buffett (深度价值)

${data.warren_buffett?.trim() || '暂无分析'}

---

*本报告由 AI 投委会自动生成，仅供参考，不构成投资建议。*`
  }

  return `# Dashboard 分析报告

**股票代码**: ${data.symbol}
**股票名称**: ${data.stock_name}
**当前价格**: ¥${data.current_price}
**分析时间**: ${new Date(stock.timestamp).toLocaleString('zh-CN')}

---

## 分析结果

**判决**: ${data.verdict_chinese} ${data.conviction_stars}

**技术评分**: ${data.technical_score ?? "N/A"}/100
**基本面评分**: ${data.fundamental_score ?? "N/A"}/100

---

*本报告由 Dashboard 分析自动生成，仅供参考，不构成投资建议。*`
}

// ============================================
// Main Page
// ============================================

export default function PortfolioPage() {
  const [stocks, setStocks] = useState<StockWithPrice[]>([])
  const [expandedStocks, setExpandedStocks] = useState<Set<string>>(new Set())
  const [drawerStock, setDrawerStock] = useState<StockWithPrice | null>(null)
  const [selectedStock, setSelectedStock] = useState<StockWithPrice | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingPrices, setIsLoadingPrices] = useState(false)

  const loadStocks = async () => {
    setIsLoading(true)
    try {
      const mergedHistory = getMergedAnalysisHistory()

      if (mergedHistory.length === 0) {
        setStocks([])
        setIsLoading(false)
        return
      }

      const stocksWithPrices = await Promise.all(
        mergedHistory.map(async (stock) => {
          let updatedStock: StockWithPrice = {
            ...stock,
            current_price: stock.current_price,
            change: undefined,
            turnover_rate: undefined
          }

          // 从 full_report 中提取 turnover_rate
          if (stock.full_report) {
            console.log('[Portfolio] === Checking full_report for', stock.symbol, '===')
            console.log('[Portfolio] full_report length:', stock.full_report.length)
            console.log('[Portfolio] full_report preview:', stock.full_report.substring(0, 300))

            try {
              const reportData = JSON.parse(stock.full_report)
              console.log('[Portfolio] Parsed successfully. Keys:', Object.keys(reportData))
              console.log('[Portfolio] Has turnover_rate:', 'turnover_rate' in reportData, reportData.turnover_rate)
              console.log('[Portfolio] Has advanced_metrics:', 'advanced_metrics' in reportData)

              // Log all available fields for inspection
              Object.keys(reportData).forEach(key => {
                const value = reportData[key]
                if (typeof value === 'object' && value !== null) {
                  console.log('[Portfolio]', key, ':', Object.keys(value))
                } else if (typeof value !== 'object') {
                  console.log('[Portfolio]', key, ':', value)
                }
              })

              if (reportData.turnover_rate) {
                console.log('[Portfolio] ✓ Found turnover_rate:', reportData.turnover_rate)
                updatedStock.turnover_rate = reportData.turnover_rate
              } else {
                console.warn('[Portfolio] ✗ turnover_rate NOT found in full_report')
              }

              if (reportData.advanced_metrics) {
                console.log('[Portfolio] ✓ Found advanced_metrics')
                updatedStock.advanced_metrics = reportData.advanced_metrics
              }
            } catch (e) {
              console.error('[Portfolio] ✗ Failed to parse full_report:', e)
            }
          } else {
            console.log('[Portfolio] No full_report for', stock.symbol)
          }

          // 从 technical API 获取实时价格
          try {
            const response = await fetch(`${API_BASE}/api/v1/market/technical/${stock.symbol}`)
            if (response.ok) {
              const data = await response.json()
              updatedStock.current_price = data.current_price
              updatedStock.change = data.alpha
            }
          } catch (e) {
            console.warn("Failed to fetch technical data:", e)
          }

          return updatedStock
        })
      )

      setStocks(stocksWithPrices)
    } catch {
      setStocks([])
    } finally {
      setIsLoading(false)
    }
  }

  const fetchRealtimePrices = async () => {
    setIsLoadingPrices(true)
    try {
      const updatedStocks = await Promise.all(
        stocks.map(async (stock) => {
          try {
            const response = await fetch(`${API_BASE}/api/v1/market/technical/${stock.symbol}`)
            if (response.ok) {
              const data = await response.json()
              return {
                ...stock,
                current_price: data.current_price,
                change: data.alpha
              }
            }
            return stock
          } catch {
            return stock
          }
        })
      )
      setStocks(updatedStocks)
    } finally {
      setIsLoadingPrices(false)
    }
  }

  useEffect(() => {
    loadStocks()
  }, [])

  const handleSelectStock = (stock: StockWithPrice) => {
    console.log('[Portfolio] Selected stock:', stock.symbol, stock.stock_name)
    console.log('[Portfolio] Stock data:', stock)
    console.log('[Portfolio] Has advanced_metrics:', !!stock.advanced_metrics)
    console.log('[Portfolio] turnover_rate:', stock.turnover_rate)
    if (stock.advanced_metrics) {
      console.log('[Portfolio] advanced_metrics:', stock.advanced_metrics)
    }
    setSelectedStock(stock)
  }

  const handleToggle = (symbol: string) => {
    setExpandedStocks(prev => {
      const newSet = new Set(prev)
      if (newSet.has(symbol)) {
        newSet.delete(symbol)
      } else {
        newSet.add(symbol)
      }
      return newSet
    })
  }

  const handleDelete = (symbol: string) => {
    if (confirm(`确定要删除 ${symbol} 吗？`)) {
      deleteStockAllRecords(symbol)
      loadStocks()
    }
  }

  const handleViewReport = (stock: StockWithPrice) => {
    setSelectedStock(stock)
  }

  const buyCount = stocks.filter(s => s.verdict_chinese.includes("买入")).length
  const holdCount = stocks.filter(s => s.verdict_chinese.includes("持有")).length
  const sellCount = stocks.filter(s => s.verdict_chinese.includes("卖出")).length
  const dashboardCount = stocks.filter(s => s.type === 'dashboard').length
  const icCount = stocks.filter(s => s.type === 'ic_meeting').length

  return (
    <div className="h-full flex flex-col">
      {/* 上方 60%：深度分析面板 */}
      <div className="h-[60%] border-b border-slate-800">
        {selectedStock ? (
          <ProfessionalPanel stock={selectedStock} />
        ) : (
          <div className="h-full bg-[#0D0D0D] flex items-center justify-center">
            <div className="text-center text-slate-500">
              <FileText className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p className="text-slate-400">点击下方股票</p>
              <p className="text-sm text-slate-600">查看深度分析面板</p>
            </div>
          </div>
        )}
      </div>

      {/* 下方 40%：智能股票池列表 */}
      <div className="h-[40%] flex flex-col overflow-hidden">
        {/* 统计卡片和刷新按钮 */}
        <div className="px-6 pt-3 pb-2 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              <div>
                <h1 className="text-lg font-bold text-slate-100">智能股票池</h1>
                <p className="text-xs text-slate-500">版本化管理 · 投研级复盘</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchRealtimePrices}
              disabled={isLoadingPrices}
              className="border-slate-700 text-slate-300 hover:bg-slate-800 h-8"
            >
              <RefreshCw className={`w-3 h-3 mr-1 ${isLoadingPrices ? 'animate-spin' : ''}`} />
              价格
            </Button>
          </div>

          <div className="grid grid-cols-4 gap-2">
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="p-2">
                <div className="text-lg font-bold text-slate-100">{stocks.length}</div>
                <div className="text-xs text-slate-500">总计</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="p-2">
                <div className="text-lg font-bold text-blue-400">{dashboardCount}</div>
                <div className="text-xs text-slate-500">Dashboard</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="p-2">
                <div className="text-lg font-bold text-purple-400">{icCount}</div>
                <div className="text-xs text-slate-500">IC投委会</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="p-2">
                <div className="text-lg font-bold text-emerald-400">{buyCount}</div>
                <div className="text-xs text-slate-500">买入</div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* 股票列表（可滚动） */}
        <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-3">
          {isLoading ? (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="flex items-center justify-center py-20">
                <div className="text-center text-slate-500">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
                  <p>加载股票数据...</p>
                </div>
              </CardContent>
            </Card>
          ) : stocks.length === 0 ? (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardContent className="flex items-center justify-center py-20">
                <div className="text-center text-slate-500">
                  <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="text-slate-400 mb-2">智能股票池为空</p>
                  <p className="text-sm text-slate-600">
                    在 <span className="text-blue-400">Dashboard</span> 分析股票，<br />
                    或在 <span className="text-purple-400">IC投委会</span> 开会，<br />
                    推荐股票会自动添加到这里
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            stocks.map((stock) => (
              <StockRow
                key={stock.symbol + stock.timestamp}
                stock={stock}
                isExpanded={expandedStocks.has(stock.symbol)}
                is_selected={selectedStock?.symbol === stock.symbol}
                onToggle={() => handleToggle(stock.symbol)}
                onViewReport={() => setDrawerStock(stock)}
                onDelete={() => handleDelete(stock.symbol)}
                isLoading={isLoadingPrices}
                onSelectStock={() => handleSelectStock(stock)}
              />
            ))
          )}
        </div>
      </div>

      <ReportDrawer
        isOpen={drawerStock !== null}
        onClose={() => setDrawerStock(null)}
        stock={drawerStock}
      />
    </div>
  )
}
