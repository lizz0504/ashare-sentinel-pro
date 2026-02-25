"""
应用常量定义

集中管理硬编码的值，提高代码可维护性
"""

# ============================================
# 日志前缀
# ============================================
LOG_PREFIX_ERROR = "[ERROR]"
LOG_PREFIX_WARN = "[WARN]"
LOG_PREFIX_INFO = "[INFO]"
LOG_PREFIX_DEBUG = "[DEBUG]"
LOG_PREFIX_ARCHIVE = "[ARCHIVE]"
LOG_PREFIX_REQUEST = "[REQUEST]"
LOG_PREFIX_RESPONSE = "[RESPONSE]"

# ============================================
# AI提示模板
# ============================================
AI_PROMPT_TEMPLATES = {
    "cathie_wood": {
        "role": "激进成长投资者",
        "focus": "创新技术、成长性、行业趋势",
        "keywords": ["创新", "成长", "技术", "颠覆性"]
    },
    "warren_buffett": {
        "role": "价值投资者",
        "focus": "估值安全、护城河、现金流",
        "keywords": ["估值", "安全", "护城河", "现金流"]
    },
    "nancy_pelosi": {
        "role": "技术分析师",
        "focus": "价格趋势、量能、技术形态",
        "keywords": ["趋势", "量能", "形态", "阻力位"]
    },
    "charlie_munger": {
        "role": "CFO/裁判",
        "focus": "综合评估、风险控制",
        "keywords": ["风险", "逆向思维", "避免愚蠢"]
    }
}

# ============================================
# 评级映射
# ============================================
VERDICT_MAP = {
    '买入': 'BUY',
    '持有': 'HOLD',
    '卖出': 'SELL'
}

# ============================================
# API端点
# ============================================
API_ENDPOINTS = {
    "TUSHARE": "http://api.tushare.pro",
    "AKSHARE": "https://faweke.ssapi.cn"
}

# ============================================
# 评分阈值
# ============================================
SCORE_THRESHOLDS = {
    "EXCELLENT": 80,
    "GOOD": 60,
    "AVERAGE": 40,
    "POOR": 20
}

# ============================================
# 技术指标阈值
# ============================================
TECHNICAL_THRESHOLDS = {
    "RSI_OVERBOUGHT": 70,
    "RSI_OVERSOLD": 30,
    "MA_SHORT": 5,
    "MA_LONG": 20,
    "VOLUME_HIGH": 1.5,  # 放量倍数
    "VOLUME_LOW": 0.7
}
