"""
Pydantic 数据模型 - V1.6 版本化管理

支持 IC 投委会报告多版本存档和股票去重
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


# ============================================================================
# 枚举类型
# ============================================================================

class SuggestionEnum(str, Enum):
    """投资建议枚举"""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class MarketEnum(str, Enum):
    """市场类型枚举"""
    A_SHARE = "A"
    HK = "HK"
    US = "US"


# ============================================================================
# Stock 模型 - 股票基本信息
# ============================================================================

class StockBase(BaseModel):
    """股票基础信息"""
    code: str = Field(..., description="股票代码", min_length=6, max_length=10)
    name: str = Field(..., description="股票名称", min_length=1, max_length=50)
    market: MarketEnum = Field(default=MarketEnum.A_SHARE, description="市场类型")
    industry: Optional[str] = Field(None, description="所属行业")
    sector: Optional[str] = Field(None, description="所属板块")


class StockMarketData(BaseModel):
    """股票行情数据"""
    current_price: Optional[float] = Field(None, description="当前价格")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    turnover_rate: Optional[float] = Field(None, description="换手率 (%)")

    @validator('change_percent')
    def validate_change_percent(cls, v):
        if v is not None and not -100 <= v <= 100:
            raise ValueError('涨跌幅必须在 -100 到 100 之间')
        return v


class StockLatestScores(BaseModel):
    """最新报告分值"""
    score_growth: Optional[int] = Field(None, ge=0, le=100, description="成长得分 (0-100)")
    score_value: Optional[int] = Field(None, ge=0, le=100, description="价值得分 (0-100)")
    score_technical: Optional[int] = Field(None, ge=0, le=100, description="技术得分 (0-100)")


class StockCreate(StockBase, StockMarketData):
    """创建股票请求"""
    pass


class StockUpdate(BaseModel):
    """更新股票请求"""
    name: Optional[str] = None
    current_price: Optional[float] = None
    change_percent: Optional[float] = None
    turnover_rate: Optional[float] = None


class StockResponse(StockBase, StockMarketData, StockLatestScores):
    """股票响应"""
    latest_suggestion: Optional[SuggestionEnum] = Field(None, description="最新建议")
    latest_conviction: Optional[str] = Field(None, description="信心程度 (*/***/*****/*****)")
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # 计算字段
    composite_score: Optional[int] = Field(None, description="综合得分")
    latest_report_time: Optional[datetime] = Field(None, description="最新报告时间")
    report_count: int = Field(default=0, description="报告数量")

    class Config:
        from_attributes = True


# ============================================================================
# AnalysisReport 模型 - 分析报告
# ============================================================================

class ExpertAnalysis(BaseModel):
    """专家分析内容"""
    cathie_wood: Optional[str] = Field(None, description="Cathie Wood (成长投资) 观点")
    nancy_pelosi: Optional[str] = Field(None, description="Nancy Pelosi (技术面) 观点")
    warren_buffett: Optional[str] = Field(None, description="Warren Buffett (价值投资) 观点")
    charlie_munger: Optional[str] = Field(None, description="Charlie Munger (最终裁决) 观点")


class ReportScores(BaseModel):
    """报告分值"""
    score_growth: Optional[int] = Field(None, ge=0, le=100, description="成长得分 (0-100)")
    score_value: Optional[int] = Field(None, ge=0, le=100, description="价值得分 (0-100)")
    score_technical: Optional[int] = Field(None, ge=0, le=100, description="技术得分 (0-100)")
    composite_score: Optional[int] = Field(None, ge=0, le=100, description="综合得分 (0-100)")


class ReportVerdict(BaseModel):
    """报告评级"""
    verdict: SuggestionEnum = Field(..., description="最终评级: BUY/HOLD/SELL")
    conviction_level: Optional[int] = Field(None, ge=1, le=5, description="信心等级 (1-5)")
    conviction_stars: Optional[str] = Field(None, description="信心星级")


class FinancialSnapshot(BaseModel):
    """财务指标快照"""
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    revenue_growth_cagr: Optional[float] = None
    peg_ratio: Optional[float] = None
    rd_intensity: Optional[float] = None
    rsi_14: Optional[float] = None
    beta: Optional[float] = None
    fcf_yield: Optional[float] = None
    dividend_yield: Optional[float] = None
    turnover_rate: Optional[float] = None


class ReportCreate(BaseModel):
    """创建报告请求"""
    stock_code: str = Field(..., min_length=6, max_length=10, description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    content: Optional[str] = Field(None, description="专家辩论全文 (Markdown)")
    cathie_wood_analysis: Optional[str] = None
    nancy_pelosi_analysis: Optional[str] = None
    warren_buffett_analysis: Optional[str] = None
    charlie_munger_analysis: Optional[str] = None
    score_growth: Optional[int] = Field(None, ge=0, le=100)
    score_value: Optional[int] = Field(None, ge=0, le=100)
    score_technical: Optional[int] = Field(None, ge=0, le=100)
    verdict: SuggestionEnum
    conviction_level: Optional[int] = Field(None, ge=1, le=5)
    conviction_stars: Optional[str] = None
    financial_data: Optional[Dict[str, Any]] = None


class ReportResponse(ExpertAnalysis, ReportScores, ReportVerdict):
    """报告响应"""
    id: str
    stock_code: str
    stock_name: Optional[str] = None
    version_id: str
    content: Optional[str] = None
    financial_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    # 关联股票信息
    current_price: Optional[float] = None
    change_percent: Optional[float] = None

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    """报告列表项"""
    id: str
    stock_code: str
    stock_name: str
    version_id: str
    verdict: SuggestionEnum
    conviction_stars: Optional[str] = None
    score_growth: Optional[int] = None
    score_value: Optional[int] = None
    score_technical: Optional[int] = None
    composite_score: Optional[int] = None
    created_at: datetime
    current_price: Optional[float] = None
    change_percent: Optional[float] = None


# ============================================================================
# Dashboard 模型
# ============================================================================

class DashboardStockItem(BaseModel):
    """Dashboard 股票列表项"""
    code: str
    name: str
    market: MarketEnum
    industry: Optional[str] = None
    current_price: Optional[float] = None
    change_percent: Optional[float] = None
    turnover_rate: Optional[float] = None
    latest_score_growth: Optional[int] = None
    latest_score_value: Optional[int] = None
    latest_score_technical: Optional[int] = None
    latest_suggestion: Optional[SuggestionEnum] = None
    latest_conviction: Optional[str] = None
    composite_score: Optional[int] = None
    latest_report_time: Optional[datetime] = None
    report_count: int = 0
    updated_at: Optional[datetime] = None


class DashboardStats(BaseModel):
    """Dashboard 统计数据"""
    total_stocks: int = 0
    total_reports: int = 0
    buy_count: int = 0
    hold_count: int = 0
    sell_count: int = 0
    avg_growth_score: Optional[float] = None
    avg_value_score: Optional[float] = None


# ============================================================================
# 请求/响应模型
# ============================================================================

class ICMeetingRequestV2(BaseModel):
    """IC 投委会会议请求 V2 (带版本保存)"""
    symbol: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    save_to_db: bool = Field(default=False, description="是否保存到数据库")


class ICMeetingResponseV2(BaseModel):
    """IC 投委会会议响应 V2 (带版本信息)"""
    # 基本字段
    symbol: str
    stock_name: str
    current_price: float
    verdict_chinese: str
    conviction_stars: str

    # 版本信息 (新增)
    report_id: Optional[str] = None
    version_id: Optional[str] = None
    saved_to_db: bool = False

    # 分析内容
    cathie_wood: str
    nancy_pelosi: str
    warren_buffett: str
    final_verdict: Dict[str, Any]

    # 分数
    technical_score: int
    fundamental_score: int
    agent_scores: Dict[str, Any]
    dashboard_position: Dict[str, int]


# ============================================================================
# 历史查询请求
# ============================================================================

class ReportHistoryRequest(BaseModel):
    """报告历史查询请求"""
    stock_code: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    verdict: Optional[SuggestionEnum] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ReportHistoryResponse(BaseModel):
    """报告历史响应"""
    total: int
    reports: List[ReportListItem]
    has_more: bool
