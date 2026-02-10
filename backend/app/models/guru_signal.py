"""
Guru Watcher - Database Model

大V交易信号数据库模型（适配 Supabase PostgreSQL）
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ARRAY, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# ============================================
# 枚举类型
# ============================================

class SentimentType(str, Enum):
    """情绪类型"""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class ActionType(str, Enum):
    """操作类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    COMMENT = "COMMENT"


class PlatformType(str, Enum):
    """平台类型"""
    XUEQIU = "Xueqiu"
    TWITTER = "Twitter"
    WEIBO = "Weibo"
    EASTMONEY = "Eastmoney"


# ============================================
# SQLAlchemy 模型
# ============================================

class GuruSignalDB(Base):
    """
    大V交易信号数据库模型

    对应 Supabase guru_signals 表
    """
    __tablename__ = "guru_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guru_name = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), nullable=False, default="Xueqiu")
    source_link = Column(Text, unique=True, nullable=True)
    source_id = Column(String(255), unique=True, nullable=True, index=True)

    # 原始内容
    raw_text = Column(Text, nullable=False)
    publish_time = Column(DateTime, nullable=True)

    # AI 提取的数据
    mentioned_symbols = Column(ARRAY(String), nullable=True)  # PostgreSQL 数组类型
    sentiment = Column(String(20), nullable=True, index=True)
    action = Column(String(20), nullable=True)
    summary = Column(Text, nullable=True)

    # 交易观点
    entry_point = Column(Text, nullable=True)
    stop_loss = Column(Text, nullable=True)
    target_price = Column(Text, nullable=True)
    time_horizon = Column(String(20), nullable=True)
    position_size = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)

    # 相关信息
    related_themes = Column(ARRAY(String), nullable=True)
    key_factors = Column(ARRAY(String), nullable=True)
    confidence_score = Column(Float, default=0.8)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_guru_signals_publish_time', 'publish_time'),
        Index('idx_guru_signals_created_at', 'created_at'),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "guru_name": self.guru_name,
            "platform": self.platform,
            "source_link": self.source_link,
            "source_id": self.source_id,
            "raw_text": self.raw_text,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "mentioned_symbols": self.mentioned_symbols or [],
            "sentiment": self.sentiment,
            "action": self.action,
            "summary": self.summary,
            "entry_point": self.entry_point,
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "time_horizon": self.time_horizon,
            "position_size": self.position_size,
            "reasoning": self.reasoning,
            "related_themes": self.related_themes or [],
            "key_factors": self.key_factors or [],
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GuruProfileDB(Base):
    """
    大V基本信息数据库模型

    对应 Supabase guru_profiles 表
    """
    __tablename__ = "guru_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    platform = Column(String(50), nullable=False, default="Xueqiu")
    platform_id = Column(String(100), unique=True, nullable=True)  # 雪球 UID
    description = Column(Text, nullable=True)
    followers_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "platform_id": self.platform_id,
            "description": self.description,
            "followers_count": self.followers_count,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================
# Pydantic 模型（用于 API 和数据传输）
# ============================================

from pydantic import BaseModel, Field


class MentionedStockSchema(BaseModel):
    """提到的股票"""
    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")


class TradingIdeaSchema(BaseModel):
    """交易观点"""
    entry_point: Optional[str] = Field(None, description="入场点")
    stop_loss: Optional[str] = Field(None, description="止损位")
    target_price: Optional[str] = Field(None, description="目标价")
    time_horizon: Optional[str] = Field(None, description="时间周期")
    position_size: Optional[str] = Field(None, description="仓位")
    reasoning: Optional[str] = Field(None, description="投资逻辑")


class GuruSignalSchema(BaseModel):
    """大V交易信号（API 请求/响应模型）"""
    guru_name: str = Field(..., description="大V名字")
    platform: str = Field("Xueqiu", description="平台")
    source_link: Optional[str] = Field(None, description="源链接")
    source_id: Optional[str] = Field(None, description="源ID（去重）")

    raw_text: str = Field(..., description="原始内容")
    publish_time: Optional[datetime] = Field(None, description="发布时间")

    mentioned_symbols: List[str] = Field(default_factory=list, description="提到的股票代码")
    sentiment: str = Field("Neutral", description="情绪")
    action: str = Field("COMMENT", description="操作")
    summary: str = Field("", description="摘要")

    entry_point: Optional[str] = Field(None, description="入场点")
    stop_loss: Optional[str] = Field(None, description="止损位")
    target_price: Optional[str] = Field(None, description="目标价")
    time_horizon: Optional[str] = Field(None, description="时间周期")
    position_size: Optional[str] = Field(None, description="仓位")
    reasoning: Optional[str] = Field(None, description="投资逻辑")

    related_themes: List[str] = Field(default_factory=list, description="相关主题")
    key_factors: List[str] = Field(default_factory=list, description="关键因素")
    confidence_score: float = Field(0.8, description="置信度")

    id: Optional[int] = Field(None, description="数据库ID（仅返回时）")
    created_at: Optional[datetime] = Field(None, description="创建时间（仅返回时）")
    updated_at: Optional[datetime] = Field(None, description="更新时间（仅返回时）")


class GuruProfileSchema(BaseModel):
    """大V基本信息（API 请求/响应模型）"""
    name: str = Field(..., description="大V名字")
    platform: str = Field("Xueqiu", description="平台")
    platform_id: Optional[str] = Field(None, description="平台ID")
    description: Optional[str] = Field(None, description="描述")
    followers_count: int = Field(0, description="粉丝数")
    is_active: bool = Field(True, description="是否活跃")

    id: Optional[int] = Field(None, description="数据库ID（仅返回时）")
    created_at: Optional[datetime] = Field(None, description="创建时间（仅返回时）")
    updated_at: Optional[datetime] = Field(None, description="更新时间（仅返回时）")


# ============================================
# 11位大V配置
# ============================================

GURU_CONFIG = [
    {
        "name": "但斌",
        "platform_id": "danbin",
        "description": "深圳东方港湾投资董事长，价值投资代表",
        "followers_count": 1500000,
    },
    {
        "name": "梁宏",
        "platform_id": "lianghong",
        "description": "希瓦资产创始人，半导体专家",
        "followers_count": 800000,
    },
    {
        "name": "耐力投资",
        "platform_id": "naili",
        "description": "长期价值投资者",
        "followers_count": 500000,
    },
    {
        "name": "管我财",
        "platform_id": "guanwo",
        "description": "量化交易专家",
        "followers_count": 600000,
    },
    {
        "name": "省心省力",
        "platform_id": "shengxin",
        "description": "波段交易高手",
        "followers_count": 400000,
    },
    {
        "name": "处镜如初",
        "platform_id": "chujing",
        "description": "趋势投资者",
        "followers_count": 300000,
    },
    {
        "name": "徐翔",
        "platform_id": "xuxiang",
        "description": "曾经的私募一哥",
        "followers_count": 2000000,
    },
    {
        "name": "林园",
        "platform_id": "linyuan",
        "description": "林园投资董事长",
        "followers_count": 1800000,
    },
    {
        "name": "冯柳",
        "platform_id": "fengliu",
        "description": "高毅资产基金经理",
        "followers_count": 1200000,
    },
    {
        "name": "张坤",
        "platform_id": "zhangkun",
        "description": "易方达基金经理",
        "followers_count": 2500000,
    },
    {
        "name": "刘彦春",
        "platform_id": "liuyanchun",
        "description": "景顺长城基金经理",
        "followers_count": 1000000,
    },
]


# ============================================
# 数据转换工具
# ============================================

def schema_to_orm(schema: GuruSignalSchema) -> GuruSignalDB:
    """将 Pydantic Schema 转换为 SQLAlchemy ORM 对象"""
    return GuruSignalDB(
        guru_name=schema.guru_name,
        platform=schema.platform,
        source_link=schema.source_link,
        source_id=schema.source_id,
        raw_text=schema.raw_text,
        publish_time=schema.publish_time,
        mentioned_symbols=schema.mentioned_symbols,
        sentiment=schema.sentiment,
        action=schema.action,
        summary=schema.summary,
        entry_point=schema.entry_point,
        stop_loss=schema.stop_loss,
        target_price=schema.target_price,
        time_horizon=schema.time_horizon,
        position_size=schema.position_size,
        reasoning=schema.reasoning,
        related_themes=schema.related_themes,
        key_factors=schema.key_factors,
        confidence_score=schema.confidence_score,
    )


def orm_to_schema(orm: GuruSignalDB) -> GuruSignalSchema:
    """将 SQLAlchemy ORM 对象转换为 Pydantic Schema"""
    return GuruSignalSchema(
        id=orm.id,
        guru_name=orm.guru_name,
        platform=orm.platform,
        source_link=orm.source_link,
        source_id=orm.source_id,
        raw_text=orm.raw_text,
        publish_time=orm.publish_time,
        mentioned_symbols=orm.mentioned_symbols or [],
        sentiment=orm.sentiment or "Neutral",
        action=orm.action or "COMMENT",
        summary=orm.summary or "",
        entry_point=orm.entry_point,
        stop_loss=orm.stop_loss,
        target_price=orm.target_price,
        time_horizon=orm.time_horizon,
        position_size=orm.position_size,
        reasoning=orm.reasoning,
        related_themes=orm.related_themes or [],
        key_factors=orm.key_factors or [],
        confidence_score=orm.confidence_score,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
