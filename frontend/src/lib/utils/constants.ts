/**
 * Frontend Constants and Configuration
 * 集中管理前端常量、API路径等
 */

// API Endpoints
const API_ENDPOINTS = {
  PORTFOLIO: {
    BASE: '/api/v1/portfolio',
    ADD: '/api/v1/portfolio',
    DELETE: (id: string) => `/api/v1/portfolio/${id}`,
    ANALYZE: (id: string) => `/api/v1/portfolio/${id}/analyze`,
    TECHNICAL: (symbol: string) => `/api/v1/market/technical/${symbol}`,
  },
  IC_MEETING: {
    BASE: '/api/v1/ic/meeting',
    FORMAT_SHARED_DATA: '/api/v1/ic/meeting/format-shared-data',
  },
  MARKET: {
    TECHNICAL: '/api/v1/market/technical',
    TECHNICAL_BY_SYMBOL: (symbol: string) => `/api/v1/market/technical/${symbol}`,
    SEARCH: '/api/v1/market/search',
  },
  REPORTS: {
    BASE: '/api/v1/reports',
  },
  WEEKLY_REVIEWS: {
    BASE: '/api/v1/weekly-reviews',
  },
} as const;

// Local Storage Keys
const LOCAL_STORAGE_KEYS = {
  ANALYSIS_HISTORY: 'ic_analysis_history',
  PORTFOLIO_ITEMS: 'portfolio_items',
  USER_PREFERENCES: 'user_preferences',
  IC_MEETING_SHARED_DATA: 'ic_meeting_shared_data',
} as const;

// Default Values
const DEFAULT_VALUES = {
  PAGE_SIZE: 20,
  LOADING_DELAY_MS: 300, // 延迟显示加载指示器，避免闪烁
  RETRY_ATTEMPTS: 3,
  CACHE_DURATION_MS: 5 * 60 * 1000, // 5分钟
} as const;

// UI Constants
const UI_CONSTANTS = {
  STAR_RATING: {
    MAX_STARS: 5,
    FILLED_STAR: '★',
    EMPTY_STAR: '☆',
  },
  ACTION_COLORS: {
    STRONG_BUY: 'bg-green-500',
    BUY: 'bg-green-400',
    HOLD: 'bg-yellow-500',
    SELL: 'bg-red-400',
    STRONG_SELL: 'bg-red-500',
  },
  ACTION_LABELS: {
    STRONG_BUY: '强烈买入',
    BUY: '买入',
    HOLD: '持有',
    SELL: '卖出',
    STRONG_SELL: '强烈卖出',
  }
} as const;

export {
  API_ENDPOINTS,
  LOCAL_STORAGE_KEYS,
  DEFAULT_VALUES,
  UI_CONSTANTS,
};