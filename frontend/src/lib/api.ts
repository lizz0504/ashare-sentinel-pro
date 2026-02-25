/**
 * API 配置统一管理
 * 避免在多个文件中重复定义 API_BASE
 */

export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  TIMEOUT: {
    DEFAULT: 10000,      // 10s
    IC_MEETING: 180000,  // 3 minutes - IC meeting needs more time
    UPLOAD: 60000,       // 1 minute for file upload
  },
  ENDPOINTS: {
    IC_MEETING: '/api/v1/ic/meeting',
    ANALYZE: '/api/v1/analyze/upload',
    CHAT: '/api/v1/chat',
    STOCK_SEARCH: '/api/v1/stock/search',
  },
}

export function buildUrl(endpoint: string): string {
  return `${API_CONFIG.BASE_URL}${endpoint}`
}

export function getApiBase(): string {
  return API_CONFIG.BASE_URL
}
