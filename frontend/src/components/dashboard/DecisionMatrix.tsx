"use client"

import React from "react"

interface DecisionMatrixProps {
  technical: number | null
  fundamental: number | null
}

export function DecisionMatrix({ technical, fundamental }: DecisionMatrixProps) {
  // 处理 null/undefined 情况
  const safeTechnical = technical ?? 50
  const safeFundamental = fundamental ?? 50
  const isAnalyzing = technical === null || fundamental === null

  // 计算象限
  const getQuadrant = () => {
    if (safeTechnical > 50 && safeFundamental > 50) return {
      label: "强烈买入区",
      emoji: "🌟",
      description: "AI投委会一致看好",
      advice: "成长与价值共振，可长期持有",
      bgColor: "bg-emerald-50/50",
      textColor: "text-emerald-700"
    }
    if (safeTechnical < 50 && safeFundamental > 50) return {
      label: "左侧埋伏区",
      emoji: "👁️",
      description: "价值面优秀，等待成长",
      advice: "价值投资者可分批建仓",
      bgColor: "bg-blue-50/50",
      textColor: "text-blue-700"
    }
    if (safeTechnical > 50 && safeFundamental < 50) return {
      label: "趋势投机区",
      emoji: "🔥",
      description: "成长强势，价值疲弱",
      advice: "仅适合短线，严格止损",
      bgColor: "bg-amber-50/50",
      textColor: "text-amber-700"
    }
    return {
      label: "建议观望区",
      emoji: "❄️",
      description: "AI投委会整体悲观",
      advice: "成长与价值双弱，等待时机",
      bgColor: "bg-slate-100/50",
      textColor: "text-slate-500"
    }
  }

  const quadrant = getQuadrant()

  return (
    <div className="w-full max-w-md mx-auto space-y-3">
      {/* 标题 */}
      <div className="text-center space-y-1">
        <h3 className="text-sm font-semibold text-slate-300">AI投委会决策矩阵</h3>
        <p className="text-xs text-slate-500">趋势/成长（纵轴）vs 价值/基本面（横轴）</p>
        <p className="text-[10px] text-slate-600">基于4位AI专家加权计算</p>
      </div>

      {/* 矩阵说明 */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1 text-slate-400">
          <div className="w-2 h-2 rounded-full bg-amber-400"></div>
          <span>左上：成长强势，价值疲弱</span>
        </div>
        <div className="flex items-center gap-1 text-slate-400">
          <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
          <span>右上：成长与价值共振</span>
        </div>
        <div className="flex items-center gap-1 text-slate-400">
          <div className="w-2 h-2 rounded-full bg-slate-400"></div>
          <span>左下：双弱，建议观望</span>
        </div>
        <div className="flex items-center gap-1 text-slate-400">
          <div className="w-2 h-2 rounded-full bg-blue-400"></div>
          <span>右下：价值优秀，左侧埋伏</span>
        </div>
      </div>

      {/* 决策矩阵 */}
      <div className="relative aspect-square w-full bg-slate-900/50 border border-slate-700 rounded-lg overflow-hidden">
        {/* 象限标签 - 增强对比度 */}
        <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 pointer-events-none">
          {/* 左上 - 趋势投机区 */}
          <div className="bg-amber-500/10 border-t border-l border-amber-400/30 flex flex-col items-center justify-center p-2 gap-1">
            <span className="text-sm font-bold text-amber-400 text-center drop-shadow-lg">🔥 趋势投机区</span>
            <span className="text-[10px] text-amber-300/70 text-center">短线波段</span>
          </div>

          {/* 右上 - 强烈买入区 */}
          <div className="bg-emerald-500/10 border-t border-r border-emerald-400/30 flex flex-col items-center justify-center p-2 gap-1">
            <span className="text-sm font-bold text-emerald-400 text-center drop-shadow-lg">🌟 强烈买入区</span>
            <span className="text-[10px] text-emerald-300/70 text-center">长线持有</span>
          </div>

          {/* 左下 - 建议观望区 */}
          <div className="bg-slate-500/10 border-b border-l border-slate-400/30 flex flex-col items-center justify-center p-2 gap-1">
            <span className="text-sm font-bold text-slate-400 text-center drop-shadow-lg">❄️ 建议观望区</span>
            <span className="text-[10px] text-slate-300/70 text-center">等待时机</span>
          </div>

          {/* 右下 - 左侧埋伏区 */}
          <div className="bg-blue-500/10 border-b border-r border-blue-400/30 flex flex-col items-center justify-center p-2 gap-1">
            <span className="text-sm font-bold text-blue-400 text-center drop-shadow-lg">👁️ 左侧埋伏区</span>
            <span className="text-[10px] text-blue-300/70 text-center">分批建仓</span>
          </div>
        </div>

        {/* 轴标签 - 更清晰 */}
        <div className="absolute top-1 left-1/2 -translate-x-1/2 text-xs font-semibold text-slate-300 bg-slate-800/90 px-2 rounded border border-slate-600">
          价值/基本面 弱 → 强
        </div>
        <div className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-xs font-semibold text-slate-300 bg-slate-800/90 px-2 rounded border border-slate-600 whitespace-nowrap">
          趋势/成长 弱 → 强
        </div>

        {/* 中线 */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-full h-px bg-slate-500/50"></div>
          <div className="absolute w-full h-px bg-slate-500/50 rotate-90"></div>
        </div>

        {/* 脉冲点 */}
        <div
          className="absolute w-4 h-4 rounded-full bg-indigo-600 shadow-lg shadow-indigo-500/50 transition-transform hover:scale-125"
          style={{
            bottom: `${safeTechnical}%`,
            left: `${safeFundamental}%`,
            transform: "translate(-50%, 50%)"
          }}
        >
          {/* 呼吸动画 */}
          <span className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping">
            <span className="absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75 animate-ping"></span>
          </span>
        </div>

        {/* Tooltip */}
        {isAnalyzing ? (
          <div className="absolute bottom-2 left-2 bg-slate-800/90 text-slate-300 text-xs px-2 py-1 rounded">
            AI投委会分析中...
          </div>
        ) : (
          <div
            className="absolute bottom-2 left-2 bg-slate-800/90 text-slate-300 text-xs px-2 py-1 rounded opacity-0 hover:opacity-100 transition-opacity pointer-events-auto"
          >
            趋势/成长: {safeTechnical} | 价值/基本面: {safeFundamental}
          </div>
        )}
      </div>

      {/* 当前状态标签和建议 */}
      <div className="space-y-2">
        <div className="flex items-center justify-center gap-2">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${quadrant.bgColor} ${quadrant.textColor}`}>
            {quadrant.emoji} {quadrant.label}
          </span>
          <span className="text-xs text-slate-500">{quadrant.description}</span>
        </div>

        {/* 投资建议卡片 */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <span className="text-lg">💡</span>
            <div className="flex-1">
              <div className="text-xs font-semibold text-slate-300 mb-1">投资建议</div>
              <div className="text-sm text-slate-400">{quadrant.advice}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
