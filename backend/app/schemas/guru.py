"""
Guru Watcher - 大V交易信号提取模块

Schema定义：标准化从大V帖子中提取的交易信号数据
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SentimentType(str, Enum):
    """情绪类型"""
    BULLISH = "Bullish"    # 看多
    BEARISH = "Bearish"    # 看空
    NEUTRAL = "Neutral"    # 中性


class ActionType(str, Enum):
    """操作类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    COMMENT = "COMMENT"


class PlatformType(str, Enum):
    """平台类型"""
    XUEQIU = "Xueqiu"           # 雪球
    EASTMONEY = "Eastmoney"     # 东方财富
    GUBA = "Guba"               # 股吧
    WEIBO = "Weibo"             # 微博
    OTHER = "Other"


class MentionedStock(BaseModel):
    """提到的股票信息"""
    symbol: str = Field(..., description="股票代码，如 600519 或 NVDA")
    name: Optional[str] = Field(None, description="股票名称，如 贵州茅台")
    market: Optional[str] = Field(None, description="市场，如 A股/美股/港股")


class TradingIdea(BaseModel):
    """交易观点"""
    entry_point: Optional[str] = Field(None, description="入场点建议")
    stop_loss: Optional[str] = Field(None, description="止损位")
    target_price: Optional[str] = Field(None, description="目标价")
    time_horizon: Optional[str] = Field(None, description="时间周期，如 短线/中线/长线")
    position_size: Optional[str] = Field(None, description="仓位建议")
    reasoning: Optional[str] = Field(None, description="投资逻辑")


class GuruSignal(BaseModel):
    """
    大V交易信号模型

    从大V的帖子中提取的结构化交易信号
    """
    # --- 基本信息 ---
    id: str = Field(..., description="唯一标识")
    guru_name: str = Field(..., description="大V名字，如 省心省力")
    platform: PlatformType = Field(..., description="来源平台")
    raw_text: str = Field(..., description="原始帖子内容")

    # --- 时间信息 ---
    publish_time: Optional[datetime] = Field(None, description="发布时间")
    fetch_time: datetime = Field(default_factory=datetime.now, description="抓取时间")

    # --- AI 提取数据 ---
    mentioned_symbols: List[MentionedStock] = Field(
        default_factory=list,
        description="提取出的股票代码列表"
    )
    sentiment: SentimentType = Field(
        default=SentimentType.NEUTRAL,
        description="情绪倾向: 看多/看空/中性"
    )
    action: ActionType = Field(
        default=ActionType.COMMENT,
        description="操作建议: 买入/卖出/持有/评论"
    )
    summary: str = Field(..., description="一句话总结核心观点")

    # --- 交易细节 ---
    trading_idea: Optional[TradingIdea] = Field(None, description="详细交易观点")

    # --- 元数据 ---
    confidence_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="AI提取置信度 0-1"
    )
    processing_notes: Optional[str] = Field(None, description="处理备注")

    # --- 关联分析 ---
    related_themes: List[str] = Field(
        default_factory=list,
        description="相关主题/板块，如 [芯片, 新能源]"
    )
    key_factors: List[str] = Field(
        default_factory=list,
        description="关键因素，如 [业绩超预期, 政策利好]"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "xueqiu_20250115_001",
                "guru_name": "省心省力",
                "platform": "Xueqiu",
                "raw_text": "今天加仓了贵州茅台，看好白酒板块的修复行情...",
                "publish_time": "2025-01-15T10:30:00",
                "mentioned_symbols": [
                    {
                        "symbol": "600519",
                        "name": "贵州茅台",
                        "market": "A股"
                    }
                ],
                "sentiment": "Bullish",
                "action": "BUY",
                "summary": "看好白酒板块修复，加仓贵州茅台",
                "trading_idea": {
                    "entry_point": "当前价位附近",
                    "time_horizon": "中线",
                    "reasoning": "板块估值修复，龙头受益"
                },
                "confidence_score": 0.85,
                "related_themes": ["白酒", "消费"],
                "key_factors": ["估值修复", "龙头效应"]
            }
        }


class GuruFeedItem(BaseModel):
    """
    原始订阅源数据

    从RSS或API获取的原始帖子数据
    """
    id: str
    author: str
    platform: PlatformType
    content: str
    publish_time: Optional[datetime] = None
    url: Optional[str] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMExtractionRequest(BaseModel):
    """
    LLM提取请求

    发送给LLM进行结构化提取的请求
    """
    guru_name: str
    platform: str
    content: str
    extraction_rules: Optional[str] = None


class LLMExtractionResponse(BaseModel):
    """
    LLM提取响应

    LLM返回的结构化数据
    """
    mentioned_symbols: List[str]
    sentiment: str
    action: str
    summary: str
    trading_idea: Optional[Dict[str, Any]] = None
    related_themes: List[str] = []
    key_factors: List[str] = []


class GuruWatchConfig(BaseModel):
    """
    Guru Watcher 配置

    配置要追踪的大V和平台
    """
    enabled_gurus: List[str] = Field(
        default_factory=list,
        description="启用追踪的大V列表"
    )
    platforms: List[PlatformType] = Field(
        default_factory=lambda: [PlatformType.XUEQIU],
        description="启用的平台列表"
    )
    min_confidence_score: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="最低置信度阈值"
    )
    auto_fetch_enabled: bool = Field(
        default=False,
        description="是否启用自动抓取"
    )
    fetch_interval_minutes: int = Field(
        default=30,
        ge=5,
        description="抓取间隔（分钟）"
    )
