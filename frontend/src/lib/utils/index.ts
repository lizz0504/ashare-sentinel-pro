/**
 * 工具函数统一导出
 */

// 市场时间相关
export { isMarketOpen, isCacheValid, getMarketTimeStatus } from './marketTime'

// 缓存相关
export {
  getTechnicalCache,
  setTechnicalCache,
  clearTechnicalCache,
  getSentimentCache,
  setSentimentCache,
  clearSentimentCache,
  getPortfolioCache,
  setPortfolioCache,
  clearAllCache,
  type TechnicalCache,
  type SentimentCache,
  type PortfolioCache
} from './cache'

// 分析历史记录相关
export {
  getAnalysisHistory,
  addAnalysisRecord,
  deleteAnalysisRecord,
  clearAnalysisHistory,
  type AnalysisRecord
} from './analysisHistory'
