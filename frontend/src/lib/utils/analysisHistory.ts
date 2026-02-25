/**
 * 分析历史记录管理
 * 用于在 Dashboard、IC 投委会和复盘页面之间共享数据
 */

export interface AnalysisRecord {
  id: string
  type: 'dashboard' | 'ic_meeting'
  symbol: string
  stock_name: string
  current_price: number
  technical_score: number | null
  fundamental_score: number | null
  verdict_chinese: string
  conviction_stars: string
  timestamp: number
  // IC meeting 特有字段
  full_report?: string
  attendees?: string[]
  // 合并记录时保存的原始ID列表
  originalIds?: string[]
  // 综合判决相关字段（仅当有多个来源时）
  merged_verdict?: {
    dashboard_verdict: string
    ic_verdict: string
    final_verdict: string
    final_conviction: string
  }
}

const ANALYSIS_HISTORY_KEY = 'analysis_history'

/**
 * 判决权重映射
 * 用于综合多个来源的分析结果
 */
const VERDICT_WEIGHTS: Record<string, number> = {
  '强烈卖出': 0,
  '卖出': 1,
  '持有': 2,
  '买入': 3,
  '强烈买入': 4
}

const VERDICT_ORDER = ['强烈卖出', '卖出', '持有', '买入', '强烈买入']

/**
 * 计算综合判决
 * 当有多个来源时，综合计算最终判决
 */
function calculateMergedVerdict(records: AnalysisRecord[]): {
  dashboard_verdict: string
  ic_verdict: string
  final_verdict: string
  final_conviction: string
} {
  const dashboardRecord = records.find(r => r.type === 'dashboard')
  const icRecord = records.find(r => r.type === 'ic_meeting')

  const dashboardVerdict = dashboardRecord?.verdict_chinese || 'N/A'
  const icVerdict = icRecord?.verdict_chinese || 'N/A'

  // 如果只有一个来源，直接返回
  if (!dashboardRecord || !icRecord) {
    return {
      dashboard_verdict: dashboardVerdict,
      ic_verdict: icVerdict,
      final_verdict: dashboardVerdict !== 'N/A' ? dashboardVerdict : icVerdict,
      final_conviction: (dashboardRecord || icRecord)?.conviction_stars || '⭐⭐⭐'
    }
  }

  // 两个来源都有，综合计算
  const weight1 = VERDICT_WEIGHTS[dashboardVerdict] ?? 2
  const weight2 = VERDICT_WEIGHTS[icVerdict] ?? 2

  // 取平均权重（保守策略）
  const avgWeight = Math.round((weight1 + weight2) / 2)
  const finalVerdict = VERDICT_ORDER[avgWeight] || '持有'

  // 计算平均信心等级
  const conviction1 = (dashboardRecord?.conviction_stars.match(/⭐/g) || []).length
  const conviction2 = (icRecord?.conviction_stars.match(/⭐/g) || []).length
  const avgConviction = Math.round((conviction1 + conviction2) / 2)
  const finalConviction = '⭐'.repeat(avgConviction)

  return {
    dashboard_verdict: dashboardVerdict,
    ic_verdict: icVerdict,
    final_verdict: finalVerdict,
    final_conviction: finalConviction
  }
}

/**
 * 获取所有分析记录
 */
export function getAnalysisHistory(): AnalysisRecord[] {
  try {
    const cached = localStorage.getItem(ANALYSIS_HISTORY_KEY)
    if (!cached) return []
    return JSON.parse(cached)
  } catch {
    return []
  }
}

/**
 * 添加一条分析记录
 */
export function addAnalysisRecord(record: Omit<AnalysisRecord, 'id' | 'timestamp'>): void {
  const history = getAnalysisHistory()

  // 检查是否已存在相同股票的记录（24小时内）
  const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000
  const existingIndex = history.findIndex(
    r => r.symbol === record.symbol && r.timestamp > oneDayAgo
  )

  const newRecord: AnalysisRecord = {
    ...record,
    id: `${record.type}_${record.symbol}_${Date.now()}`,
    timestamp: Date.now()
  }

  if (existingIndex >= 0) {
    // 更新现有记录
    history[existingIndex] = newRecord
  } else {
    // 添加新记录到开头
    history.unshift(newRecord)
  }

  // 只保留最近 50 条记录
  const trimmedHistory = history.slice(0, 50)

  localStorage.setItem(ANALYSIS_HISTORY_KEY, JSON.stringify(trimmedHistory))
}

/**
 * 删除指定记录
 */
export function deleteAnalysisRecord(id: string): void {
  const history = getAnalysisHistory()
  const filtered = history.filter(r => r.id !== id)
  localStorage.setItem(ANALYSIS_HISTORY_KEY, JSON.stringify(filtered))
}

/**
 * 清空所有记录
 */
export function clearAnalysisHistory(): void {
  localStorage.removeItem(ANALYSIS_HISTORY_KEY)
}

/**
 * 获取所有分析记录（每只股票只保留最新1条，用于Portfolio列表显示）
 */
export function getMergedAnalysisHistory(): AnalysisRecord[] {
  const history = getAnalysisHistory()

  // 按股票代码分组
  const stockGroups = new Map<string, AnalysisRecord[]>()

  for (const record of history) {
    const symbol = record.symbol
    if (!stockGroups.has(symbol)) {
      stockGroups.set(symbol, [])
    }
    stockGroups.get(symbol)!.push(record)
  }

  // 每只股票只保留最新的1条记录
  const latestRecords: AnalysisRecord[] = []

  for (const [symbol, records] of stockGroups) {
    // 按时间倒序排序，取第1条（最新的）
    const sortedRecords = records.sort((a, b) => b.timestamp - a.timestamp)
    latestRecords.push(sortedRecords[0])
  }

  // 按时间戳排序（最新的在前）
  return latestRecords.sort((a, b) => b.timestamp - a.timestamp)
}

/**
 * 获取指定股票的所有历史记录（用于抽屉显示）
 */
export function getStockHistory(symbol: string): AnalysisRecord[] {
  const history = getAnalysisHistory()

  // 过滤出该股票的所有记录
  const stockRecords = history.filter(r => r.symbol === symbol)

  // 按时间倒序排序（最新的在前）
  return stockRecords.sort((a, b) => b.timestamp - a.timestamp)
}

/**
 * 获取股票的来源类型
 * 返回股票是从哪些来源添加的
 */
export function getStockSourceTypes(symbol: string): {
  hasDashboard: boolean
  hasIC: boolean
} {
  const history = getAnalysisHistory()
  const records = history.filter(r => r.symbol === symbol)

  return {
    hasDashboard: records.some(r => r.type === 'dashboard'),
    hasIC: records.some(r => r.type === 'ic_meeting')
  }
}

/**
 * 删除指定股票的所有记录
 */
export function deleteStockAllRecords(symbol: string): void {
  const history = getAnalysisHistory()
  const filtered = history.filter(r => r.symbol !== symbol)
  localStorage.setItem(ANALYSIS_HISTORY_KEY, JSON.stringify(filtered))
}
