"""
Guru Service - Enhanced Database-Integrated Service

集成数据库的完整大V信号监控服务
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.models.guru import (
    GuruSignal,
    MentionedStock,
    TradingIdea,
    GuruSignalDB,
    get_guru_signal_db,
    GURU_LIST,
)
from app.core.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


# ============================================
# LLM 提取提示词
# ============================================

EXTRACTION_PROMPT = """你是一位专业的金融舆情分析师，擅长从投资大V的帖子中提取结构化交易信号。

请分析以下帖子内容，提取关键信息并以JSON格式返回：

**帖子内容**：
作者：{guru_name}
平台：{platform}
内容：{content}

**提取要求**：

1. **mentioned_symbols**: 提取所有提到的股票代码
   - A股代码格式：6位数字（如 600519）
   - 美股代码：大写字母（如 NVDA）
   - 港股代码：5位数字（如 00700）
   - 股票别名映射：茅台→600519, 五粮液→000858, 宁德时代→300750, 比亚迪→002594
   - 返回格式：["600519", "NVDA"]

2. **sentiment**: 判断整体情绪倾向
   - "Bullish" - 明显看多，使用"加仓"、"买入"、"看好"、"机会"等词汇
   - "Bearish" - 明显看空，使用"减仓"、"卖出"、"回避"、"风险"等词汇
   - "Neutral" - 中性观点或单纯分析

3. **action**: 操作建议
   - "BUY" - 明确建议买入/加仓
   - "SELL" - 明确建议卖出/减仓
   - "HOLD" - 建议持有
   - "COMMENT" - 纯评论，无明确操作建议

4. **summary**: 一句话总结（不超过50字）

5. **trading_idea** (可选): 交易细节
   - "entry_point": 入场点建议
   - "stop_loss": 止损位
   - "target_price": 目标价
   - "time_horizon": 时间周期（短线/中线/长线）
   - "position_size": 仓位建议
   - "reasoning": 投资逻辑

6. **related_themes**: 相关主题/板块（如 ["白酒", "消费"]）

7. **key_factors**: 关键因素（如 ["估值修复", "业绩超预期"]）

**输出格式（纯JSON，不要包含markdown格式）**：
```json
{{
  "mentioned_symbols": ["股票代码列表"],
  "sentiment": "Bullish/Bearish/Neutral",
  "action": "BUY/SELL/HOLD/COMMENT",
  "summary": "一句话总结",
  "trading_idea": {{
    "entry_point": "入场点（如有）",
    "stop_loss": "止损位（如有）",
    "target_price": "目标价（如有）",
    "time_horizon": "时间周期（如有）",
    "position_size": "仓位（如有）",
    "reasoning": "投资逻辑（如有）"
  }},
  "related_themes": ["主题1", "主题2"],
  "key_factors": ["因素1", "因素2"]
}}
```

请严格按照上述JSON格式输出，不要添加任何其他文字说明。
"""


# ============================================
# 数据抓取模拟器（可替换为真实RSS/API）
# ============================================

class XueqiuScraper:
    """雪球网数据抓取器"""

    # 模拟数据源（实际应替换为真实API）
    MOCK_FEEDS = [
        {
            "id": "xq_001",
            "author": "但斌",
            "content": "今天加仓了贵州茅台(600519)，长期看好白酒板块，当前位置安全边际较高。",
            "publish_time": "2025-02-09T10:30:00",
            "likes": 328,
            "comments": 45,
        },
        {
            "id": "xq_002",
            "author": "梁宏",
            "content": "半导体板块机会来了！重点关注中芯国际(688981)和北方华创(002371)，国产替代加速。",
            "publish_time": "2025-02-09T11:20:00",
            "likes": 456,
            "comments": 67,
        },
        {
            "id": "xq_003",
            "author": "省心省力",
            "content": "减仓宁德时代(300750)，短期涨幅过大，建议获利了结，等回调再接回。",
            "publish_time": "2025-02-09T13:45:00",
            "likes": 234,
            "comments": 34,
        },
        {
            "id": "xq_004",
            "author": "林园",
            "content": "医药板块经过长期调整，估值已经回到合理区间，可以开始布局了。看好恒瑞医药(600276)。",
            "publish_time": "2025-02-09T14:30:00",
            "likes": 567,
            "comments": 89,
        },
        {
            "id": "xq_005",
            "author": "冯柳",
            "content": "当前市场处于底部区域，不需要过度悲观。关注优质公司的长期价值。",
            "publish_time": "2025-02-09T15:10:00",
            "likes": 892,
            "comments": 123,
        },
    ]

    @classmethod
    def fetch_feeds(cls, guru_list: List[str], limit: int = 20) -> List[Dict]:
        """
        抓取指定大V的最新动态

        Args:
            guru_list: 大V名字列表
            limit: 每个大V获取的数量

        Returns:
            帖子列表
        """
        feeds = []

        for guru in guru_list:
            # 筛选该大V的帖子
            guru_feeds = [f for f in cls.MOCK_FEEDS if f["author"] == guru]
            feeds.extend(guru_feeds[:limit])

        return feeds


# ============================================
# 主服务类
# ============================================

class GuruService:
    """大V信号监控服务（数据库集成版）"""

    def __init__(self):
        self.db = get_guru_signal_db()
        self.scraper = XueqiuScraper()

    async def extract_signal_from_text(
        self,
        guru_name: str,
        platform: str,
        content: str,
        publish_time: Optional[datetime] = None,
        source_id: Optional[str] = None
    ) -> Optional[GuruSignal]:
        """
        从文本中提取交易信号

        Args:
            guru_name: 大V名字
            platform: 平台名称
            content: 帖子内容
            publish_time: 发布时间
            source_id: 源ID（用于去重）

        Returns:
            提取的信号，失败返回 None
        """
        try:
            # 构建提示词
            prompt = EXTRACTION_PROMPT.format(
                guru_name=guru_name,
                platform=platform,
                content=content
            )

            # 调用 LLM 提取
            result = await LLMFactory.fast_reply(
                model="deepseek",
                system="你是一位专业的金融文本分析专家。请严格按照JSON格式返回结果，不要包含任何其他文字。",
                user=prompt,
                timeout=15
            )

            if not result or result.startswith("[错误]"):
                logger.warning(f"[GURU] LLM extraction failed for {guru_name}")
                return None

            # 解析 JSON
            extraction_result = self._parse_llm_json_response(result)
            if not extraction_result:
                logger.warning(f"[GURU] Failed to parse JSON from LLM response")
                return None

            # 构建信号对象
            mentioned_stocks = []
            for symbol in extraction_result.get("mentioned_symbols", []):
                mentioned_stocks.append(MentionedStock(symbol=symbol))

            # 处理交易观点
            trading_idea = None
            idea_data = extraction_result.get("trading_idea")
            if idea_data and any(idea_data.values()):
                trading_idea = TradingIdea(
                    entry_point=idea_data.get("entry_point"),
                    stop_loss=idea_data.get("stop_loss"),
                    target_price=idea_data.get("target_price"),
                    time_horizon=idea_data.get("time_horizon"),
                    position_size=idea_data.get("position_size"),
                    reasoning=idea_data.get("reasoning"),
                )

            signal = GuruSignal(
                guru_name=guru_name,
                platform=platform,
                source_id=source_id,
                raw_text=content,
                publish_time=publish_time,
                mentioned_symbols=mentioned_stocks,
                sentiment=extraction_result.get("sentiment", "Neutral"),
                action=extraction_result.get("action", "COMMENT"),
                summary=extraction_result.get("summary", ""),
                trading_idea=trading_idea,
                related_themes=extraction_result.get("related_themes", []),
                key_factors=extraction_result.get("key_factors", []),
            )

            logger.info(f"[GURU] Successfully extracted signal from {guru_name}: {signal.summary}")
            return signal

        except Exception as e:
            logger.error(f"[GURU] Error extracting signal: {e}")
            return None

    def _parse_llm_json_response(self, response: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON"""
        import re
        import json

        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取花括号内容
        first_brace = response.find('{')
        last_brace = response.rfind('}')
        if first_brace != -1 and last_brace != -1:
            try:
                json_text = response[first_brace:last_brace + 1]
                json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        logger.error(f"[PARSE] Failed to parse JSON from: {response[:300]}")
        return None

    async def run_collection_cycle(self, guru_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        运行一次完整的抓取周期

        Args:
            guru_names: 要抓取的大V列表，None 则抓取全部

        Returns:
            采集统计信息
        """
        if guru_names is None:
            guru_names = [g.name for g in GURU_LIST]

        logger.info(f"[GURU] Starting collection cycle for {len(guru_names)} gurus")

        # 抓取数据
        feeds = self.scraper.fetch_feeds(guru_names, limit=5)
        logger.info(f"[GURU] Fetched {len(feeds)} feeds")

        # 提取信号
        signals = []
        for feed in feeds:
            signal = await self.extract_signal_from_text(
                guru_name=feed["author"],
                platform="Xueqiu",
                content=feed["content"],
                publish_time=datetime.fromisoformat(feed["publish_time"]) if feed.get("publish_time") else None,
                source_id=feed["id"]
            )
            if signal:
                signals.append(signal)

        # 保存到数据库
        saved_count = 0
        for signal in signals:
            if self.db.save_signal(signal):
                saved_count += 1

        # 返回统计
        stats = {
            "guru_count": len(guru_names),
            "feeds_fetched": len(feeds),
            "signals_extracted": len(signals),
            "signals_saved": saved_count,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"[GURU] Collection cycle complete: {stats}")
        return stats

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
            guru_name: 筛选大V
            symbol: 筛选股票

        Returns:
            信号列表
        """
        return self.db.get_recent_signals(limit, guru_name, symbol)

    def get_aggregated_sentiment(self, symbol: str) -> Dict[str, Any]:
        """获取某股票的聚合情绪分析"""
        return self.db.get_aggregated_sentiment(symbol)

    def get_trending_symbols(self, limit: int = 10) -> List[Dict]:
        """获取热门提及股票"""
        return self.db.get_trending_symbols(limit)

    def get_top_gurus(self, limit: int = 10) -> List[Dict]:
        """获取最活跃的大V"""
        return self.db.get_top_gurus(limit)


# ============================================
# 单例实例
# ============================================

_guru_service_instance: Optional[GuruService] = None


def get_guru_service() -> GuruService:
    """获取 GuruService 单例"""
    global _guru_service_instance
    if _guru_service_instance is None:
        _guru_service_instance = GuruService()
    return _guru_service_instance


# ============================================
# FastAPI 路由
# ============================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v2/guru", tags=["Guru Watcher"])


class CollectionRequest(BaseModel):
    """数据采集请求"""
    guru_names: List[str] = []
    limit: int = 10


class CollectionResponse(BaseModel):
    """数据采集响应"""
    guru_count: int
    feeds_fetched: int
    signals_extracted: int
    signals_saved: int
    timestamp: str


@router.post("/collect", response_model=CollectionResponse)
async def collect_signals(request: CollectionRequest):
    """
    触发数据采集

    从配置的大V列表中抓取最新动态，提取交易信号并保存到数据库
    """
    try:
        service = get_guru_service()
        guru_names = request.guru_names if request.guru_names else None

        stats = await service.run_collection_cycle(guru_names)

        return CollectionResponse(**stats)

    except Exception as e:
        logger.error(f"[API] Collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def trigger_guru_refresh():
    """
    快速刷新大V数据

    从所有配置的大V抓取最新数据（使用默认配置）
    """
    try:
        service = get_guru_service()
        result = await service.run_collection_cycle()
        return {
            "status": "success",
            "message": "数据刷新完成",
            "data": result
        }
    except Exception as e:
        logger.error(f"[API] Refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_signals(
    limit: int = 50,
    guru: str = None,
    symbol: str = None
):
    """获取信号列表"""
    try:
        service = get_guru_service()
        signals = service.get_recent_signals(limit, guru, symbol)
        return {"total": len(signals), "signals": signals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def get_trending(limit: int = 10):
    """获取热门股票"""
    try:
        service = get_guru_service()
        trending = service.get_trending_symbols(limit)
        return {"trending": trending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/{symbol}")
async def get_sentiment(symbol: str):
    """获取聚合情绪分析"""
    try:
        service = get_guru_service()
        sentiment = service.get_aggregated_sentiment(symbol)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gurus")
async def get_gurus(limit: int = 10):
    """获取活跃大V列表"""
    try:
        service = get_guru_service()
        gurus = service.get_top_gurus(limit)
        return {"gurus": gurus}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 主入口
# ============================================

async def main():
    """测试入口"""
    service = get_guru_service()

    # 运行采集周期
    stats = await service.run_collection_cycle()
    print(f"\n=== Collection Stats ===")
    print(f"大V数量: {stats['guru_count']}")
    print(f"抓取动态: {stats['feeds_fetched']}")
    print(f"提取信号: {stats['signals_extracted']}")
    print(f"保存信号: {stats['signals_saved']}")

    # 获取热门股票
    trending = service.get_trending_symbols(5)
    print(f"\n=== Trending Symbols ===")
    for item in trending:
        print(f"{item['symbol']}: {item['mention_count']} 次提及")

    # 获取聚合情绪
    for item in trending[:3]:
        sentiment = service.get_aggregated_sentiment(item["symbol"])
        print(f"\n=== {item['symbol']} Sentiment ===")
        print(f"总信号: {sentiment['total_signals']}")
        print(f"整体情绪: {sentiment['avg_sentiment']}")


if __name__ == "__main__":
    asyncio.run(main())
