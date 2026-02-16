"""
Constants and Configuration
集中管理API路径、常量等
"""

# API Endpoints
API_PREFIX = "/api/v1"

# Database Table Names
TABLE_PORTFOLIO = "portfolio"
TABLE_REPORTS = "reports"
TABLE_WEEKLY_REVIEWS = "weekly_reviews"
TABLE_REPORT_CHUNKS = "report_chunks"

# Cache Keys
CACHE_STOCK_INFO = "stock_info_{symbol}"
CACHE_TECHNICAL_DATA = "tech_data_{symbol}"

# Response Messages
MSG_STOCK_ADDED = "[OK] Stock added: {symbol}"
MSG_SUMMARY_SAVED = "[OK] Summary saved to report {id}"
MSG_ANALYSIS_COMPLETE = "[OK] Analysis complete for {symbol}"

# Error Messages
ERR_FAILED_SAVE_STOCK = "Failed to save stock"
ERR_FAILED_GET_STOCK = "Failed to get stock data"
ERR_FAILED_API_CALL = "API call failed: {error_msg}"

# Valid Action Signals
VALID_ACTION_SIGNALS = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]

# IC Meeting Verdicts
IC_VERDICT_OPTIONS = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]

# Technical Analysis Constants
TECHNICAL_FIELDS = [
    "tech_ma20_status",
    "tech_ma5_status",
    "tech_volume_status",
    "tech_volume_change_pct",
    "tech_alpha",
    "tech_k_line_pattern",
    "tech_pattern_signal",
    "tech_action_signal",
    "tech_analysis_date"
]

# Default Values
DEFAULT_HEALTH_SCORE = 50
DEFAULT_CONFIDENCE_LEVEL = 3