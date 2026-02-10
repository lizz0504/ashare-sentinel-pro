"""
Guru Watcher - Database Models and Service

使用 Supabase 存储大V交易信号

数据表结构 (需要在 Supabase SQL Editor 中执行):
```sql
-- 创建 guru_signals 表
CREATE TABLE IF NOT EXISTS guru_signals (
    id BIGSERIAL PRIMARY KEY,
    guru_name VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'Xueqiu',
    source_link TEXT UNIQUE,
    source_id VARCHAR(255) UNIQUE,

    -- 原始内容
    raw_text TEXT NOT NULL,
    publish_time TIMESTAMP WITH TIME ZONE,

    -- AI 提取的数据
    mentioned_symbols TEXT[],  -- PostgreSQL 数组类型
    sentiment VARCHAR(20),
    action VARCHAR(20),
    summary TEXT,

    -- 交易观点
    entry_point TEXT,
    stop_loss TEXT,
    target_price TEXT,
    time_horizon VARCHAR(20),
    position_size TEXT,
    reasoning TEXT,

    -- 相关信息
    related_themes TEXT[],
    key_factors TEXT[],
    confidence_score FLOAT DEFAULT 0.8,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_guru_signals_guru_name ON guru_signals(guru_name);
CREATE INDEX IF NOT EXISTS idx_guru_signals_symbol ON guru_signals(mentioned_symbols);
CREATE INDEX IF NOT EXISTS idx_guru_signals_sentiment ON guru_signals(sentiment);
CREATE INDEX IF NOT EXISTS idx_guru_signals_publish_time ON guru_signals(publish_time DESC);
CREATE INDEX IF NOT EXISTS idx_guru_signals_created_at ON guru_signals(created_at DESC);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_guru_signals_updated_at
    BEFORE UPDATE ON guru_signals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 创建 guru_profiles 表 (大V基本信息)
CREATE TABLE IF NOT EXISTS guru_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'Xueqiu',
    platform_id VARCHAR(100) UNIQUE,  -- 雪球 UID
    description TEXT,
    followers_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 预定义的11位大V
INSERT INTO guru_profiles (name, platform, platform_id, description) VALUES
    ('但斌', 'Xueqiu', 'danbin', '深圳东方港湾投资董事长，价值投资代表'),
    ('梁宏', 'Xueqiu', 'lianghong', '希瓦资产创始人，半导体专家'),
    ('耐力投资', 'Xueqiu', 'naili', '长期价值投资者'),
    ('管我财', 'Xueqiu', 'guanwo', '量化交易专家'),
    ('省心省力', 'Xueqiu', 'shengxin', '波段交易高手'),
    ('处镜如初', 'Xueqiu', 'chujing', '趋势投资者'),
    ('徐翔', 'Xueqiu', 'xuxiang', '曾经的私募一哥'),
    ('林园', 'Xueqiu', 'linyuan', '林园投资董事长'),
    ('冯柳', 'Xueqiu', 'fengliu', '高毅资产基金经理'),
    ('张坤', 'Xueqiu', 'zhangkun', '易方达基金经理'),
    ('刘彦春', 'Xueqiu', 'liuyanchun', '景顺长城基金经理')
ON CONFLICT (name) DO NOTHING;
```
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from ..core.db import get_db_client


# ============================================
# 数据模型 (Pydantic/数据类)
# ============================================

@dataclass
class MentionedStock:
    """提到的股票"""
    symbol: str
    name: Optional[str] = None


@dataclass
class TradingIdea:
    """交易观点"""
    entry_point: Optional[str] = None
    stop_loss: Optional[str] = None
    target_price: Optional[str] = None
    time_horizon: Optional[str] = None
    position_size: Optional[str] = None
    reasoning: Optional[str] = None


@dataclass
class GuruSignal:
    """大V交易信号"""
    guru_name: str
    platform: str = "Xueqiu"
    source_link: Optional[str] = None
    source_id: Optional[str] = None

    raw_text: str = ""
    publish_time: Optional[datetime] = None

    mentioned_symbols: List[MentionedStock] = field(default_factory=list)
    sentiment: str = "Neutral"  # Bullish, Bearish, Neutral
    action: str = "COMMENT"    # BUY, SELL, HOLD, COMMENT
    summary: str = ""

    trading_idea: Optional[TradingIdea] = None
    related_themes: List[str] = field(default_factory=list)
    key_factors: List[str] = field(default_factory=list)
    confidence_score: float = 0.8


@dataclass
class GuruProfile:
    """大V基本信息"""
    name: str
    platform: str = "Xueqiu"
    platform_id: Optional[str] = None
    description: Optional[str] = None
    followers_count: int = 0
    is_active: bool = True


# ============================================
# 11位大V 配置
# ============================================

GURU_LIST = [
    GuruProfile(
        name="但斌",
        platform_id="danbin",
        description="深圳东方港湾投资董事长，价值投资代表"
    ),
    GuruProfile(
        name="梁宏",
        platform_id="lianghong",
        description="希瓦资产创始人，半导体专家"
    ),
    GuruProfile(
        name="耐力投资",
        platform_id="naili",
        description="长期价值投资者"
    ),
    GuruProfile(
        name="管我财",
        platform_id="guanwo",
        description="量化交易专家"
    ),
    GuruProfile(
        name="省心省力",
        platform_id="shengxin",
        description="波段交易高手"
    ),
    GuruProfile(
        name="处镜如初",
        platform_id="chujing",
        description="趋势投资者"
    ),
    GuruProfile(
        name="徐翔",
        platform_id="xuxiang",
        description="曾经的私募一哥"
    ),
    GuruProfile(
        name="林园",
        platform_id="linyuan",
        description="林园投资董事长"
    ),
    GuruProfile(
        name="冯柳",
        platform_id="fengliu",
        description="高毅资产基金经理"
    ),
    GuruProfile(
        name="张坤",
        platform_id="zhangkun",
        description="易方达基金经理"
    ),
    GuruProfile(
        name="刘彦春",
        platform_id="liuyanchun",
        description="景顺长城基金经理"
    ),
]


# ============================================
# 数据库服务
# ============================================

class GuruSignalDB:
    """大V信号数据库服务"""

    def __init__(self):
        self.client = get_db_client()
        self.table = self.client.table("guru_signals")

    def save_signal(self, signal: GuruSignal) -> Optional[Dict]:
        """
        保存信号到数据库

        Args:
            signal: 大V信号对象

        Returns:
            保存后的记录，如果重复则返回 None
        """
        try:
            data = {
                "guru_name": signal.guru_name,
                "platform": signal.platform,
                "source_link": signal.source_link,
                "source_id": signal.source_id,
                "raw_text": signal.raw_text,
                "publish_time": signal.publish_time.isoformat() if signal.publish_time else None,
                "mentioned_symbols": [ms.symbol for ms in signal.mentioned_symbols],
                "sentiment": signal.sentiment,
                "action": signal.action,
                "summary": signal.summary,
                "related_themes": signal.related_themes,
                "key_factors": signal.key_factors,
                "confidence_score": signal.confidence_score,
            }

            # 添加交易观点
            if signal.trading_idea:
                data.update({
                    "entry_point": signal.trading_idea.entry_point,
                    "stop_loss": signal.trading_idea.stop_loss,
                    "target_price": signal.trading_idea.target_price,
                    "time_horizon": signal.trading_idea.time_horizon,
                    "position_size": signal.trading_idea.position_size,
                    "reasoning": signal.trading_idea.reasoning,
                })

            # 使用 upsert 避免重复
            result = self.table.upsert(data, on_conflict="source_link").execute()

            if result.data:
                return result.data[0]

            return None

        except Exception as e:
            print(f"[DB] Error saving signal: {e}")
            return None

    def get_recent_signals(
        self,
        limit: int = 50,
        guru_name: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict]:
        """
        获取最近的信号

        Args:
            limit: 返回数量
            guru_name: 筛选大V名字
            symbol: 筛选股票代码

        Returns:
            信号列表
        """
        try:
            query = self.table.select("*").order("publish_time", desc=True).limit(limit)

            if guru_name:
                query = query.eq("guru_name", guru_name)

            if symbol:
                query = query.contains("mentioned_symbols", [symbol])

            result = query.execute()
            return result.data if result.data else []

        except Exception as e:
            print(f"[DB] Error fetching signals: {e}")
            return []

    def get_aggregated_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        获取某股票的聚合情绪分析

        Args:
            symbol: 股票代码

        Returns:
            聚合分析结果
        """
        try:
            # 获取该股票的所有信号
            result = self.table.select("*").contains("mentioned_symbols", [symbol]).execute()

            if not result.data:
                return {
                    "symbol": symbol,
                    "total_signals": 0,
                    "bullish_count": 0,
                    "bearish_count": 0,
                    "neutral_count": 0,
                    "avg_sentiment": "Neutral"
                }

            signals = result.data
            bullish = sum(1 for s in signals if s.get("sentiment") == "Bullish")
            bearish = sum(1 for s in signals if s.get("sentiment") == "Bearish")
            neutral = sum(1 for s in signals if s.get("sentiment") == "Neutral")

            # 计算整体情绪
            total = len(signals)
            if total == 0:
                avg_sentiment = "Neutral"
            elif bullish / total > 0.6:
                avg_sentiment = "Strongly Bullish"
            elif bullish / total > 0.4:
                avg_sentiment = "Bullish"
            elif bearish / total > 0.4:
                avg_sentiment = "Bearish"
            else:
                avg_sentiment = "Neutral"

            return {
                "symbol": symbol,
                "total_signals": total,
                "bullish_count": bullish,
                "bearish_count": bearish,
                "neutral_count": neutral,
                "avg_sentiment": avg_sentiment
            }

        except Exception as e:
            print(f"[DB] Error aggregating sentiment: {e}")
            return {
                "symbol": symbol,
                "error": str(e)
            }

    def get_top_gurus(self, limit: int = 10) -> List[Dict]:
        """
        获取最活跃的大V (按信号数量排序)

        Args:
            limit: 返回数量

        Returns:
            大V列表
        """
        try:
            # 使用 RPC 或原始 SQL (需要 Supabase 配置)
            # 这里简化处理，使用 Python 聚合
            result = self.table.select("guru_name").execute()

            if not result.data:
                return []

            # 统计每个大V的信号数量
            from collections import Counter
            guru_counts = Counter(s["guru_name"] for s in result.data)

            top_gurus = [
                {
                    "guru_name": guru,
                    "signal_count": count
                }
                for guru, count in guru_counts.most_common(limit)
            ]

            return top_gurus

        except Exception as e:
            print(f"[DB] Error fetching top gurus: {e}")
            return []

    def get_trending_symbols(self, limit: int = 10) -> List[Dict]:
        """
        获取热门提及股票 (按提及次数排序)

        Args:
            limit: 返回数量

        Returns:
            股票列表
        """
        try:
            result = self.table.select("mentioned_symbols").execute()

            if not result.data:
                return []

            # 统计每个股票的提及次数
            from collections import Counter
            symbol_counts = Counter()

            for record in result.data:
                symbols = record.get("mentioned_symbols", [])
                if isinstance(symbols, list):
                    symbol_counts.update(symbols)

            trending = [
                {
                    "symbol": symbol,
                    "mention_count": count
                }
                for symbol, count in symbol_counts.most_common(limit)
            ]

            return trending

        except Exception as e:
            print(f"[DB] Error fetching trending symbols: {e}")
            return []


# ============================================
# 便捷函数
# ============================================

def get_guru_signal_db() -> GuruSignalDB:
    """获取数据库服务单例"""
    return GuruSignalDB()


def save_signal_batch(signals: List[GuruSignal]) -> int:
    """
    批量保存信号

    Args:
        signals: 信号列表

    Returns:
        成功保存的数量
    """
    db = get_guru_signal_db()
    count = 0

    for signal in signals:
        if db.save_signal(signal):
            count += 1

    return count
