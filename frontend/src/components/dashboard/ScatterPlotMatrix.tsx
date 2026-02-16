"use client"

import React, { useState, useEffect } from "react"
import Link from "next/link"
import { ChevronDown, TrendingUp, TrendingDown, Minus, X } from "lucide-react"
import { cn } from "@/lib/utils"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// 单个股票数据
interface StockPoint {
  code: string
  name: string
  current_price: number | null
  latest_score_growth: number | null
  latest_score_value: number | null
  latest_score_technical: number | null
  latest_suggestion: "BUY" | "HOLD" | "SELL" | null
  latest_conviction: string | null
  report_count: number
}

// 迷你卡片 Props
interface MiniCardProps {
  stock: StockPoint
  onClose: () => void
}

function MiniCard({ stock, onClose }: MiniCardProps) {
  const getSuggestionColor = (suggestion: string | null) => {
    switch (suggestion) {
      case "BUY": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
      case "HOLD": return "text-amber-400 bg-amber-500/10 border-amber-500/30"
      case "SELL": return "text-rose-400 bg-rose-500/10 border-rose-500/30"
      default: return "text-slate-400 bg-slate-500/10 border-slate-500/30"
    }
  }

  const getSuggestionIcon = (suggestion: string | null) => {
    switch (suggestion) {
      case "BUY": return <TrendingUp className="w-4 h-4" />
      case "SELL": return <TrendingDown className="w-4 h-4" />
      default: return <Minus className="w-4 h-4" />
    }
  }

  const getSuggestionText = (suggestion: string | null) => {
    switch (suggestion) {
      case "BUY": return "强烈买入"
      case "HOLD": return "持有观望"
      case "SELL": return "建议卖出"
      default: return "未分析"
    }
  }

  return (
    <div className="fixed z-50 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-4 w-72 animate-in fade-in zoom-in duration-200">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-slate-100">{stock.name}</h3>
          <p className="text-sm text-slate-400">{stock.code}</p>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Price */}
      <div className="mb-3">
        <div className="text-sm text-slate-500">当前价格</div>
        <div className="text-2xl font-bold text-slate-100">
          ¥{stock.current_price?.toFixed(2) ?? "--"}
        </div>
      </div>

      {/* Suggestion Badge */}
      <div className="mb-3">
        <div className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium",
          getSuggestionColor(stock.latest_suggestion)
        )}>
          {getSuggestionIcon(stock.latest_suggestion)}
          <span>{getSuggestionText(stock.latest_suggestion)}</span>
          {stock.latest_conviction && (
            <span className="ml-1 text-xs opacity-70">{stock.latest_conviction}</span>
          )}
        </div>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-slate-800/50 rounded-lg p-2 text-center">
          <div className="text-[10px] text-slate-500">成长性</div>
          <div className="text-sm font-bold text-slate-100">
            {stock.latest_score_growth ?? "--"}
          </div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-2 text-center">
          <div className="text-[10px] text-slate-500">价值度</div>
          <div className="text-sm font-bold text-slate-100">
            {stock.latest_score_value ?? "--"}
          </div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-2 text-center">
          <div className="text-[10px] text-slate-500">技术面</div>
          <div className="text-sm font-bold text-slate-100">
            {stock.latest_score_technical ?? "--"}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-2">
        <Link
          href={`/ic?code=${stock.code}`}
          className="block w-full py-2 px-4 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white text-sm font-medium rounded-lg text-center transition-colors"
        >
          深度分析
        </Link>
        <Link
          href={`/portfolio?code=${stock.code}&expand=true`}
          className="block w-full py-2 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg text-center transition-colors border border-slate-700"
        >
          查看历史
        </Link>
      </div>
    </div>
  )
}

// 获取象限颜色
const getQuadrantColor = (x: number, y: number): string => {
  if (y > 50 && x > 50) return "bg-emerald-500" // 右上：强烈买入
  if (y < 50 && x > 50) return "bg-blue-500"    // 右下：左侧埋伏
  if (y > 50 && x < 50) return "bg-amber-500"   // 左上：趋势投机
  return "bg-slate-500"                          // 左下：建议观望
}

interface ScatterPlotMatrixProps {
  className?: string
}

export function ScatterPlotMatrix({ className }: ScatterPlotMatrixProps) {
  const [stocks, setStocks] = useState<StockPoint[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedStock, setSelectedStock] = useState<StockPoint | null>(null)
  const [hoveredStock, setHoveredStock] = useState<StockPoint | null>(null)
  const [stats, setStats] = useState({
    total: 0,
    buy: 0,
    hold: 0,
    sell: 0
  })
  const [useMockData, setUseMockData] = useState(false)

  // 模拟数据（用于测试 UI）
  const mockStocks: StockPoint[] = [
    { code: "002353", name: "三花智控", current_price: 28.50, latest_score_growth: 75, latest_score_value: 65, latest_score_technical: 70, latest_suggestion: "BUY", latest_conviction: "⭐⭐⭐⭐", report_count: 2 },
    { code: "300750", name: "宁德时代", current_price: 180.20, latest_score_growth: 85, latest_score_value: 80, latest_score_technical: 75, latest_suggestion: "BUY", latest_conviction: "⭐⭐⭐⭐⭐", report_count: 3 },
    { code: "600519", name: "贵州茅台", current_price: 1680.00, latest_score_growth: 45, latest_score_value: 90, latest_score_technical: 50, latest_suggestion: "HOLD", latest_conviction: "⭐⭐⭐", report_count: 5 },
    { code: "000858", name: "五粮液", current_price: 145.30, latest_score_growth: 40, latest_score_value: 75, latest_score_technical: 45, latest_suggestion: "HOLD", latest_conviction: "⭐⭐⭐", report_count: 2 },
    { code: "002475", name: "立讯精密", current_price: 32.80, latest_score_growth: 70, latest_score_value: 55, latest_score_technical: 65, latest_suggestion: "BUY", latest_conviction: "⭐⭐⭐⭐", report_count: 1 },
    { code: "600036", name: "招商银行", current_price: 32.50, latest_score_growth: 30, latest_score_value: 85, latest_score_technical: 40, latest_suggestion: "HOLD", latest_conviction: "⭐⭐⭐", report_count: 4 },
    { code: "000001", name: "平安银行", current_price: 11.20, latest_score_growth: 35, latest_score_value: 60, latest_score_technical: 45, latest_suggestion: "HOLD", latest_conviction: "⭐⭐", report_count: 2 },
    { code: "300059", name: "东方财富", current_price: 15.80, latest_score_growth: 60, latest_score_value: 40, latest_score_technical: 55, latest_suggestion: "HOLD", latest_conviction: "⭐⭐⭐", report_count: 1 },
    { code: "002050", name: "天奇股份", current_price: 12.30, latest_score_growth: 25, latest_score_value: 30, latest_score_technical: 35, latest_suggestion: "SELL", latest_conviction: "⭐⭐", report_count: 1 },
    { code: "600276", name: "恒瑞医药", current_price: 45.60, latest_score_growth: 55, latest_score_value: 70, latest_score_technical: 50, latest_suggestion: "BUY", latest_conviction: "⭐⭐⭐", report_count: 3 },
  ]

  // 获取股票数据
  useEffect(() => {
    const fetchStocks = async () => {
      console.log("[ScatterPlot] 开始获取股票数据...")
      try {
        const response = await fetch(`${API_BASE}/api/v1/stocks?limit=100`)
        console.log("[ScatterPlot] API响应状态:", response.status)

        if (!response.ok) {
          console.log("[ScatterPlot] API请求失败，使用模拟数据")
          throw new Error("Failed to fetch stocks")
        }

        const data = await response.json()
        console.log("[ScatterPlot] API返回数据:", data)

        const stocks = data.stocks || []

        // 如果返回空数据，也使用模拟数据
        if (stocks.length === 0) {
          console.log("[ScatterPlot] API返回空数据，使用模拟数据")
          throw new Error("Empty data")
        }

        setStocks(stocks)

        // 计算统计
        setStats({
          total: stocks.length,
          buy: stocks.filter((s: StockPoint) => s.latest_suggestion === "BUY").length,
          hold: stocks.filter((s: StockPoint) => s.latest_suggestion === "HOLD").length,
          sell: stocks.filter((s: StockPoint) => s.latest_suggestion === "SELL").length
        })
      } catch (error) {
        console.error("[ScatterPlot] 获取股票失败:", error)
        // 使用模拟数据
        console.log("[ScatterPlot] 使用模拟数据进行 UI 测试")
        console.log("[ScatterPlot] 模拟股票数量:", mockStocks.length)
        setStocks(mockStocks)
        setStats({
          total: mockStocks.length,
          buy: mockStocks.filter(s => s.latest_suggestion === "BUY").length,
          hold: mockStocks.filter(s => s.latest_suggestion === "HOLD").length,
          sell: mockStocks.filter(s => s.latest_suggestion === "SELL").length
        })
        setUseMockData(true)
      } finally {
        setIsLoading(false)
      }
    }

    fetchStocks()
  }, [])

  // 点击背景关闭 Mini Card
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (selectedStock && !(e.target as HTMLElement).closest(".fixed.z-50")) {
        setSelectedStock(null)
      }
    }

    if (selectedStock) {
      document.addEventListener("click", handleClick)
      return () => document.removeEventListener("click", handleClick)
    }
  }, [selectedStock])

  // 过滤有坐标数据的股票
  const plotStocks = stocks.filter(
    s => s.latest_score_value !== null && s.latest_score_growth !== null
  )

  return (
    <div className={cn("w-full space-y-4", className)}>
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">投资矩阵全景图</h3>
          <p className="text-sm text-slate-400">X轴：价值度 | Y轴：成长性</p>
        </div>

        {/* 统计卡片 */}
        <div className="flex gap-3">
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-center">
            <div className="text-xs text-slate-500">总计</div>
            <div className="text-lg font-bold text-slate-100">{stats.total}</div>
          </div>
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2 text-center">
            <div className="text-xs text-emerald-400">买入</div>
            <div className="text-lg font-bold text-emerald-400">{stats.buy}</div>
          </div>
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2 text-center">
            <div className="text-xs text-amber-400">持有</div>
            <div className="text-lg font-bold text-amber-400">{stats.hold}</div>
          </div>
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2 text-center">
            <div className="text-xs text-rose-400">卖出</div>
            <div className="text-lg font-bold text-rose-400">{stats.sell}</div>
          </div>
        </div>
      </div>

      {/* 散点图矩阵 */}
      <div className="relative bg-slate-900/50 border border-slate-700 rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-32">
            <div className="text-slate-400">加载中...</div>
          </div>
        ) : plotStocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32">
            <div className="text-slate-400">暂无数据</div>
            <div className="text-sm text-slate-600 mt-2">请先在 IC 投委会分析股票</div>
          </div>
        ) : (
          <>
            {/* 模拟数据提示 */}
            {useMockData && (
              <div className="absolute top-2 right-2 bg-amber-500/20 border border-amber-500/50 text-amber-400 text-xs px-2 py-1 rounded z-10">
                模拟数据演示
              </div>
            )}

            {/* 象限背景 */}
            <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 pointer-events-none">
              {/* 左上 - 趋势投机区 */}
              <div className="bg-amber-500/5 border-t border-l border-amber-400/20" />
              {/* 右上 - 强烈买入区 */}
              <div className="bg-emerald-500/5 border-t border-r border-emerald-400/20" />
              {/* 左下 - 建议观望区 */}
              <div className="bg-slate-500/5 border-b border-l border-slate-400/20" />
              {/* 右下 - 左侧埋伏区 */}
              <div className="bg-blue-500/5 border-b border-r border-blue-400/20" />
            </div>

            {/* 轴标签 */}
            <div className="absolute top-2 left-1/2 -translate-x-1/2 text-xs font-medium text-slate-400 bg-slate-900/80 px-2 rounded">
              价值/基本面
            </div>
            <div className="absolute left-2 top-1/2 -translate-y-1/2 -rotate-90 text-xs font-medium text-slate-400 bg-slate-900/80 px-2 rounded whitespace-nowrap">
              趋势/成长性
            </div>

            {/* 中线 */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-full h-px bg-slate-600/30 border-t border-dashed border-slate-500/50" />
              <div className="absolute w-full h-px bg-slate-600/30 border-t border-dashed border-slate-500/50 rotate-90" />
            </div>

            {/* 散点 */}
            <div className="relative" style={{ paddingBottom: "100%" }}>
              {plotStocks.map((stock) => {
                const x = stock.latest_score_value ?? 50
                const y = stock.latest_score_growth ?? 50
                const isSelected = selectedStock?.code === stock.code
                const isHovered = hoveredStock?.code === stock.code

                return (
                  <button
                    key={stock.code}
                    onClick={() => setSelectedStock(stock)}
                    onMouseEnter={() => setHoveredStock(stock)}
                    onMouseLeave={() => setHoveredStock(null)}
                    className="absolute transform -translate-x-1/2 translate-y-1/2 transition-transform hover:scale-125 focus:outline-none"
                    style={{
                      left: `${x}%`,
                      bottom: `${y}%`,
                      zIndex: isSelected ? 10 : isHovered ? 5 : 1
                    }}
                  >
                    <div
                      className={cn(
                        "w-4 h-4 rounded-full border-2 shadow-lg transition-all",
                        getQuadrantColor(x, y),
                        isSelected ? "w-6 h-6 border-white shadow-xl scale-125" : "border-white/50",
                        isHovered && "scale-110"
                      )}
                    />
                    {/* 选中/Hover 时的股票代码 */}
                    {(isSelected || isHovered) && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 bg-slate-800 text-slate-200 text-xs px-2 py-0.5 rounded whitespace-nowrap">
                        {stock.code}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>

            {/* 图例 */}
            <div className="absolute bottom-2 left-2 flex gap-3 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                <span className="text-slate-400">强烈买入区</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-slate-400">左侧埋伏区</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                <span className="text-slate-400">趋势投机区</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-slate-500"></div>
                <span className="text-slate-400">建议观望区</span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Mini Card */}
      {selectedStock && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40" />
      )}
      {selectedStock && (
        <div className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none">
          <div className="pointer-events-auto" style={{ marginLeft: "200px" }}>
            <MiniCard stock={selectedStock} onClose={() => setSelectedStock(null)} />
          </div>
        </div>
      )}
    </div>
  )
}
