/**
 * 缓存管理工具
 */

// ============================================
// 技术面缓存
// ============================================

export interface TechnicalCache {
  score: number
  healthScore: number
  actionSignal: string
  timestamp: number
}

const TECHNICAL_CACHE_KEY = 'technical_cache'

export function getTechnicalCache(symbol: string): TechnicalCache | null {
  const key = `${TECHNICAL_CACHE_KEY}_${symbol}`
  const cached = localStorage.getItem(key)
  if (!cached) return null

  try {
    return JSON.parse(cached)
  } catch {
    return null
  }
}

export function setTechnicalCache(symbol: string, data: Omit<TechnicalCache, 'timestamp'>): void {
  const key = `${TECHNICAL_CACHE_KEY}_${symbol}`
  const cache: TechnicalCache = {
    ...data,
    timestamp: Date.now()
  }
  localStorage.setItem(key, JSON.stringify(cache))
}

export function clearTechnicalCache(symbol?: string): void {
  if (symbol) {
    localStorage.removeItem(`${TECHNICAL_CACHE_KEY}_${symbol}`)
  } else {
    // 清除所有技术面缓存
    Object.keys(localStorage)
      .filter(key => key.startsWith(TECHNICAL_CACHE_KEY))
      .forEach(key => localStorage.removeItem(key))
  }
}

// ============================================
// 情绪分析缓存
// ============================================

export interface SentimentCache {
  score: number
  sentiment: string
  timestamp: number
}

const SENTIMENT_CACHE_KEY = 'sentiment_cache'

export function getSentimentCache(symbol: string): SentimentCache | null {
  const key = `${SENTIMENT_CACHE_KEY}_${symbol}`
  const cached = localStorage.getItem(key)
  if (!cached) return null

  try {
    return JSON.parse(cached)
  } catch {
    return null
  }
}

export function setSentimentCache(symbol: string, data: Omit<SentimentCache, 'timestamp'>): void {
  const key = `${SENTIMENT_CACHE_KEY}_${symbol}`
  const cache: SentimentCache = {
    ...data,
    timestamp: Date.now()
  }
  localStorage.setItem(key, JSON.stringify(cache))
}

export function clearSentimentCache(symbol?: string): void {
  if (symbol) {
    localStorage.removeItem(`${SENTIMENT_CACHE_KEY}_${symbol}`)
  } else {
    // 清除所有情绪缓存
    Object.keys(localStorage)
      .filter(key => key.startsWith(SENTIMENT_CACHE_KEY))
      .forEach(key => localStorage.removeItem(key))
  }
}

// ============================================
// 投资组合缓存
// ============================================

export interface PortfolioCache {
  stocks: string[]
  timestamp: number
}

const PORTFOLIO_CACHE_KEY = 'portfolio_cache'

export function getPortfolioCache(): PortfolioCache | null {
  const cached = localStorage.getItem(PORTFOLIO_CACHE_KEY)
  if (!cached) return null

  try {
    return JSON.parse(cached)
  } catch {
    return null
  }
}

export function setPortfolioCache(stocks: string[]): void {
  const cache: PortfolioCache = {
    stocks,
    timestamp: Date.now()
  }
  localStorage.setItem(PORTFOLIO_CACHE_KEY, JSON.stringify(cache))
}

// ============================================
// 通用缓存清理
// ============================================

export function clearAllCache(): void {
  clearTechnicalCache()
  clearSentimentCache()
  localStorage.removeItem(PORTFOLIO_CACHE_KEY)
}
