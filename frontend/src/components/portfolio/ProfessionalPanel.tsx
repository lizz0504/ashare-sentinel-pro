"use client"

import React, { useMemo } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  TrendingUp,
  TrendingDown,
  Activity
} from "lucide-react"
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer
} from "recharts"

interface AdvancedMetrics {
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

interface StockData {
  symbol: string
  stock_name: string
  current_price?: number
  change?: number
  verdict_chinese: string
  conviction_stars: string
  technical_score: number | null
  fundamental_score: number | null
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
  industry?: string
  [key: string]: any
}

interface ProfessionalPanelProps {
  stock: StockData
}

export function ProfessionalPanel({ stock }: ProfessionalPanelProps) {
  // 调试日志
  if (typeof window !== 'undefined') {
    console.log('[ProfessionalPanel] Rendering with stock:', stock.symbol, stock.stock_name)
    console.log('[ProfessionalPanel] Stock keys:', Object.keys(stock))
    console.log('[ProfessionalPanel] turnover_rate:', stock.turnover_rate)
    console.log('[ProfessionalPanel] Has advanced_metrics:', !!stock.advanced_metrics)
  }

  // 根据建议确定信号卡片颜色
  const signalConfig = useMemo(() => {
    const verdict = stock.verdict_chinese
    if (verdict.includes("买入")) {
      return {
        bgColor: "bg-emerald-500/10",
        borderColor: "border-emerald-500",
        textColor: "text-emerald-400",
        icon: <TrendingUp className="w-5 h-5" />,
        label: "买入信号"
      }
    } else if (verdict.includes("卖出")) {
      return {
        bgColor: "bg-red-500/10",
        borderColor: "border-red-500",
        textColor: "text-red-400",
        icon: <TrendingDown className="w-5 h-5" />,
        label: "卖出信号"
      }
    } else {
      return {
        bgColor: "bg-yellow-500/10",
        borderColor: "border-yellow-500",
        textColor: "text-yellow-400",
        icon: <Activity className="w-5 h-5" />,
        label: "持有观察"
      }
    }
  }, [stock.verdict_chinese])

  // 核心指标数据（只取前4个最重要的）
  const metrics = useMemo(() => {
    const adv = stock.advanced_metrics
    return [
      {
        title: "技术评分",
        value: stock.technical_score ?? "N/A",
        trend: stock.technical_score && stock.technical_score >= 70 ? "up" : "down"
      },
      {
        title: "基本面评分",
        value: stock.fundamental_score ?? "N/A",
        trend: stock.fundamental_score && stock.fundamental_score >= 70 ? "up" : "down"
      },
      {
        title: "换手率",
        value: stock.turnover_rate || "N/A",
        trend: "neutral"
      },
      {
        title: "建议强度",
        value: stock.conviction_stars || "N/A",
        trend: "neutral"
      }
    ]
  }, [stock.advanced_metrics, stock.technical_score, stock.fundamental_score, stock.turnover_rate, stock.conviction_stars])

  // 雷达图数据
  const radarData = useMemo(() => {
    const adv = stock.advanced_metrics?.radar
    return [
      { subject: "估值", fullMark: 100, value: adv?.value_score || 50 },
      { subject: "成长", fullMark: 100, value: adv?.growth_score || 50 },
      { subject: "安全", fullMark: 100, value: adv?.safety_score || 50 },
      { subject: "股息", fullMark: 100, value: adv?.dividend_score || 50 },
      { subject: "趋势", fullMark: 100, value: adv?.trend_score || 50 }
    ]
  }, [stock.advanced_metrics])

  return (
    <div className="h-full bg-[#0D0D0D] p-5 overflow-hidden">
      {/* Header - 优化布局 */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-2xl font-semibold text-white mb-1">{stock.stock_name}</h2>
          <p className="text-sm text-slate-400 font-mono">{stock.symbol}</p>
        </div>
        <Badge variant="outline" className="text-xs border-slate-600 text-slate-300 px-2.5 py-1 h-6">
          {stock.industry || "科技"}
        </Badge>
      </div>

      {/* Signal Card - 优化设计 */}
      <div className={`rounded-xl border ${signalConfig.borderColor} transition-all mb-4 shadow-lg bg-gradient-to-r ${signalConfig.bgColor.replace('bg-', 'from-').replace('/20', '/10')} to-transparent`}>
        <div className="p-5">
          <div className="flex items-center gap-4">
            <div className={`p-2.5 rounded-lg ${signalConfig.bgColor}`}>
              {signalConfig.icon}
            </div>
            <div className="flex-1">
              <h3 className={`text-xl font-bold ${signalConfig.textColor} mb-1`}>
                {signalConfig.label}
              </h3>
              <p className="text-sm text-slate-300">
                {stock.verdict_chinese} {stock.conviction_stars}
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-white mb-1">
                ¥{stock.current_price?.toFixed(2) || "--"}
              </div>
              <div className={`text-sm font-medium ${stock.change && stock.change > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {stock.change ? `${stock.change > 0 ? '+' : ''}${stock.change.toFixed(2)}%` : '--'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 核心指标和雷达图 - 优化布局 */}
      <div className="grid grid-cols-3 gap-5 flex-1 h-full">
        {/* 核心指标 (4个) - 左侧 1/3 */}
        <div className="grid grid-cols-2 gap-4">
          {metrics.map((metric, idx) => (
            <Card key={idx} className="bg-slate-800/60 border-slate-700 hover:bg-slate-800/80 transition-colors">
              <CardContent className="p-4">
                <div className="text-xs text-slate-400 mb-2 font-medium">{metric.title}</div>
                <div className="flex items-center justify-between">
                  <div className="text-xl font-bold text-white">{metric.value}</div>
                  {metric.trend === "up" && <TrendingUp className="w-5 h-5 text-emerald-400" />}
                  {metric.trend === "down" && <TrendingDown className="w-5 h-5 text-red-400" />}
                  {metric.trend === "neutral" && <Activity className="w-5 h-5 text-blue-400" />}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* 雷达图 - 右侧 2/3，占据全部可用空间 */}
        <Card className="bg-slate-800/40 border-slate-600 col-span-2 h-full flex flex-col shadow-lg backdrop-blur-sm">
          <CardContent className="p-4 flex-1 flex flex-col">
            <div className="text-base font-semibold text-slate-200 mb-3 ml-2">五维评分</div>
            <div className="flex-1 min-h-0 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart
                  data={radarData}
                  margin={{ top: 5, right: 5, bottom: 5, left: 5 }}
                >
                  <PolarGrid stroke="#334155" strokeDasharray="3 3" radialLines={true} />
                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{
                      fill: "#f8fafc",
                      fontSize: 12,
                      fontWeight: 500
                    }}
                    tickLine={{ stroke: "#64748b", strokeWidth: 1 }}
                    axisLine={{ stroke: "#64748b", strokeWidth: 1 }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 100]}
                    tick={false}
                    tickCount={5}
                    axisLine={{ stroke: "transparent" }}
                    tickLine={{ stroke: "#475569", strokeWidth: 1 }}
                  />
                  <Radar
                    name="评分"
                    dataKey="value"
                    stroke="#ec4899"
                    fill="#ec4899"
                    fillOpacity={0.1}
                    strokeWidth={2}
                    dot={{ r: 4, fill: '#ec4899', strokeWidth: 2, stroke: '#ffffff' }}
                    activeDot={{ r: 6, fill: '#ffffff', stroke: '#ec4899', strokeWidth: 2 }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
