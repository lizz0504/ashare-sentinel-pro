"""
Guru Watcher Service - 大V交易信号监控服务

功能：
1. 模拟RSS订阅源获取（可扩展为真实RSS/API）
2. 使用LLM从非结构化文本中提取结构化交易信号
3. 信号聚合与分析
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from app.schemas.guru import (
    GuruSignal,
    GuruFeedItem,
    LLMExtractionRequest,
    LLMExtractionResponse,
    SentimentType,
    ActionType,
    PlatformType,
    MentionedStock,
    TradingIdea,
)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# =============================================================================
# 模拟RSS数据源（可替换为真实RSS/API）
# =============================================================================

MOCK_XUEQIU_FEEDS = [
    {
        "id": "xq_001",
        "author": "省心省力",
        "content": "今天加仓了贵州茅台(600519)，看好白酒板块的估值修复行情。当前位置安全边际较高，中线持有。",
        "publish_time": "2025-01-15T10:30:00",
        "likes": 328,
        "comments": 45,
    },
    {
        "id": "xq_002",
        "author": "价值发现者",
        "content": "减仓宁德时代(300750)，短期涨幅过大，建议获利了结。等回调到200以下再考虑接回。",
        "publish_time": "2025-01-15T11:20:00",
        "likes": 156,
        "comments": 23,
    },
    {
        "id": "xq_003",
        "author": "趋势猎手",
        "content": "半导体板块机会来了！重点关注中芯国际(688981)和北方华创(002371)，国产替代加速，业绩有预期。",
        "publish_time": "2025-01-15T13:45:00",
        "likes": 512,
        "comments": 89,
    },
    {
        "id": "xq_004",
        "author": "量化交易员",
        "content": "市场情绪转暖，科技成长股有望继续走强。关注芯片、AI应用方向。当前位置适合做多。",
        "publish_time": "2025-01-15T14:30:00",
        "likes": 234,
        "comments": 34,
    },
    {
        "id": "xq_005",
        "author": "保守投资者",
        "content": "当前市场不确定性较大，建议控制仓位。高分红股票如工商银行(601398)可以作为防御配置。",
        "publish_time": "2025-01-15T15:10:00",
        "likes": 189,
        "comments": 56,
    },
    {
        "id": "xq_006",
        "author": "省心省力",
        "content": "继续看好AI算力方向，英伟达(NVDA)财报季可能超预期，国内相关标的也会有表现。",
        "publish_time": "2025-01-16T09:15:00",
        "likes": 445,
        "comments": 67,
    },
    {
        "id": "xq_007",
        "author": "技术派大师",
        "content": "指数在关键位置获得支撑，短线可以博弈反弹。推荐券商板块，如中信证券(600030)。",
        "publish_time": "2025-01-16T10:00:00",
        "likes": 278,
        "comments": 41,
    },
    {
        "id": "xq_008",
        "author": "行业研究员",
        "content": "光伏产业链价格企稳，龙头企业迎来布局良机。推荐隆基绿能(601012)、通威股份(600438)。",
        "publish_time": "2025-01-16T11:30:00",
        "likes": 367,
        "comments": 52,
    },
]


# =============================================================================
# LLM 提取提示词
# =============================================================================

EXTRACTION_PROMPT = """你是一位专业的金融文本分析专家，擅长从投资大V的帖子中提取结构化交易信号。

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


# =============================================================================
# LLM 客户端（复用现有LLM工厂）
# =============================================================================

async def call_llm_for_extraction(prompt: str) -> Optional[Dict[str, Any]]:
    """
    调用LLM进行文本提取

    Args:
        prompt: 完整的提示词

    Returns:
        解析后的JSON数据，失败返回None
    """
    try:
        from app.core.llm_factory import LLMFactory

        system_prompt = "你是一位专业的金融文本分析专家。请严格按照JSON格式返回结果，不要包含任何其他文字。"

        result = await LLMFactory.fast_reply(
            model="deepseek",  # 使用DeepSeek进行快速提取
            system=system_prompt,
            user=prompt,
            timeout=15
        )

        if result and not result.startswith("[错误]"):
            # 解析JSON
            parsed = _parse_llm_json_response(result)
            if parsed:
                logger.info(f"[LLM] Successfully extracted trading signal")
                return parsed
            else:
                logger.warning(f"[LLM] Failed to parse JSON from response: {result[:200]}")
        else:
            logger.warning(f"[LLM] Extraction failed: {result[:100] if result else 'No result'}")

    except Exception as e:
        logger.error(f"[LLM] Extraction error: {str(e)}")

    return None


def _parse_llm_json_response(response: str) -> Optional[Dict[str, Any]]:
    """
    解析LLM返回的JSON（处理可能的格式问题）

    Args:
        response: LLM原始响应

    Returns:
        解析后的字典，失败返回None
    """
    import re
    import json

    try:
        # 尝试直接解析
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 尝试提取JSON代码块
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
            # 清理常见问题
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    logger.error(f"[PARSE] Failed to parse JSON from: {response[:300]}")
    return None


# =============================================================================
# Guru Watcher Service
# =============================================================================

class GuruWatcherService:
    """
    大V交易信号监控服务

    功能：
    1. 获取大V的帖子（RSS/API/模拟数据）
    2. 使用LLM提取结构化交易信号
    3. 聚合和分析信号
    """

    def __init__(self):
        self.signals_cache: List[GuruSignal] = []
        self.feed_items: List[GuruFeedItem] = []

    async def fetch_feeds(
        self,
        platform: PlatformType = PlatformType.XUEQIU,
        limit: int = 20
    ) -> List[GuruFeedItem]:
        """
        获取订阅源数据

        Args:
            platform: 平台类型
            limit: 获取数量限制

        Returns:
            原始帖子列表
        """
        logger.info(f"[GURU] Fetching feeds from {platform.value}, limit={limit}")

        # 模拟数据（实际可替换为真实RSS/API调用）
        if platform == PlatformType.XUEQIU:
            mock_data = MOCK_XUEQIU_FEEDS[:limit]
        else:
            mock_data = []

        # 转换为GuruFeedItem
        feed_items = []
        for item in mock_data:
            feed_items.append(GuruFeedItem(
                id=item["id"],
                author=item["author"],
                platform=platform,
                content=item["content"],
                publish_time=datetime.fromisoformat(item["publish_time"]) if item.get("publish_time") else None,
                likes=item.get("likes"),
                comments=item.get("comments"),
            ))

        self.feed_items = feed_items
        logger.info(f"[GURU] Fetched {len(feed_items)} feed items")
        return feed_items

    async def extract_signal(self, feed_item: GuruFeedItem) -> Optional[GuruSignal]:
        """
        从单个帖子中提取交易信号

        Args:
            feed_item: 原始帖子

        Returns:
            提取的交易信号，失败返回None
        """
        logger.info(f"[GURU] Extracting signal from {feed_item.id} by {feed_item.author}")

        # 构建提示词
        prompt = EXTRACTION_PROMPT.format(
            guru_name=feed_item.author,
            platform=feed_item.platform.value,
            content=feed_item.content
        )

        # 调用LLM提取
        extraction_result = await call_llm_for_extraction(prompt)

        if not extraction_result:
            logger.warning(f"[GURU] Failed to extract signal from {feed_item.id}")
            return None

        try:
            # 构建GuruSignal
            signal_id = f"{feed_item.platform.value}_{feed_item.id}"

            # 处理提到的股票
            mentioned_stocks = []
            for symbol in extraction_result.get("mentioned_symbols", []):
                mentioned_stocks.append(MentionedStock(symbol=symbol))

            # 处理交易观点
            trading_idea = None
            if extraction_result.get("trading_idea"):
                idea_data = extraction_result["trading_idea"]
                # 只在有实际内容时创建TradingIdea
                if any(idea_data.values()):
                    trading_idea = TradingIdea(**{k: v for k, v in idea_data.items() if v})

            # 创建信号
            signal = GuruSignal(
                id=signal_id,
                guru_name=feed_item.author,
                platform=feed_item.platform,
                raw_text=feed_item.content,
                publish_time=feed_item.publish_time,
                mentioned_symbols=mentioned_stocks,
                sentiment=SentimentType(extraction_result.get("sentiment", "Neutral")),
                action=ActionType(extraction_result.get("action", "COMMENT")),
                summary=extraction_result.get("summary", ""),
                trading_idea=trading_idea,
                confidence_score=0.8,  # 可以根据提取质量动态调整
                related_themes=extraction_result.get("related_themes", []),
                key_factors=extraction_result.get("key_factors", []),
            )

            logger.info(f"[GURU] Successfully extracted signal: {signal.summary}")
            return signal

        except Exception as e:
            logger.error(f"[GURU] Error building signal: {str(e)}")
            return None

    async def process_feeds(
        self,
        platform: PlatformType = PlatformType.XUEQIU,
        limit: int = 20
    ) -> List[GuruSignal]:
        """
        批量处理订阅源并提取信号

        Args:
            platform: 平台类型
            limit: 处理数量限制

        Returns:
            提取的交易信号列表
        """
        logger.info(f"[GURU] Processing feeds from {platform.value}")

        # 获取订阅源
        feed_items = await self.fetch_feeds(platform, limit)

        # 并发提取信号
        tasks = [self.extract_signal(item) for item in feed_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤成功的结果
        signals = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[GURU] Error processing feed: {str(result)}")
            elif isinstance(result, GuruSignal):
                signals.append(result)

        self.signals_cache = signals
        logger.info(f"[GURU] Processed {len(signals)} signals successfully")

        return signals

    def get_signals_by_symbol(self, symbol: str) -> List[GuruSignal]:
        """
        按股票代码筛选信号

        Args:
            symbol: 股票代码

        Returns:
            该股票的相关信号列表
        """
        return [
            s for s in self.signals_cache
            if any(ms.symbol == symbol for ms in s.mentioned_symbols)
        ]

    def get_signals_by_guru(self, guru_name: str) -> List[GuruSignal]:
        """
        按大V筛选信号

        Args:
            guru_name: 大V名字

        Returns:
            该大V的信号列表
        """
        return [s for s in self.signals_cache if s.guru_name == guru_name]

    def get_aggregated_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        获取某股票的聚合情绪分析

        Args:
            symbol: 股票代码

        Returns:
            聚合分析结果
        """
        signals = self.get_signals_by_symbol(symbol)

        if not signals:
            return {
                "symbol": symbol,
                "total_signals": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "avg_sentiment": "Neutral",
                "recent_summary": []
            }

        bullish = sum(1 for s in signals if s.sentiment == SentimentType.BULLISH)
        bearish = sum(1 for s in signals if s.sentiment == SentimentType.BEARISH)
        neutral = sum(1 for s in signals if s.sentiment == SentimentType.NEUTRAL)

        # 确定整体情绪
        total = len(signals)
        if bullish / total > 0.6:
            avg_sentiment = "Strongly Bullish"
        elif bullish / total > 0.4:
            avg_sentiment = "Bullish"
        elif bearish / total > 0.4:
            avg_sentiment = "Bearish"
        else:
            avg_sentiment = "Neutral"

        # 最近的观点摘要
        recent_summary = [
            {
                "guru": s.guru_name,
                "action": s.action.value,
                "summary": s.summary,
                "time": s.publish_time.isoformat() if s.publish_time else None
            }
            for s in signals[:5]
        ]

        return {
            "symbol": symbol,
            "total_signals": total,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "avg_sentiment": avg_sentiment,
            "recent_summary": recent_summary
        }


# =============================================================================
# 单例实例
# =============================================================================

_guru_watcher_instance: Optional[GuruWatcherService] = None


def get_guru_watcher() -> GuruWatcherService:
    """获取GuruWatcher单例"""
    global _guru_watcher_instance
    if _guru_watcher_instance is None:
        _guru_watcher_instance = GuruWatcherService()
    return _guru_watcher_instance


# =============================================================================
# 主入口
# =============================================================================

async def main():
    """测试入口"""
    service = get_guru_watcher()

    # 处理订阅源
    signals = await service.process_feeds(platform=PlatformType.XUEQIU, limit=5)

    # 打印结果
    print(f"\n=== Guru Watcher 测试结果 ===\n")
    print(f"成功提取 {len(signals)} 个信号\n")

    for signal in signals:
        print(f"[{signal.guru_name}] ({signal.platform.value})")
        print(f"   情绪: {signal.sentiment.value} | 操作: {signal.action.value}")
        print(f"   股票: {[ms.symbol for ms in signal.mentioned_symbols]}")
        print(f"   摘要: {signal.summary}")
        if signal.trading_idea:
            print(f"   观点: {signal.trading_idea.reasoning}")
        print(f"   主题: {signal.related_themes}")
        print()

    # 测试聚合分析
    if signals:
        test_symbol = signals[0].mentioned_symbols[0].symbol if signals[0].mentioned_symbols else "600519"
        aggregated = service.get_aggregated_sentiment(test_symbol)
        print(f"\n=== {test_symbol} 聚合分析 ===")
        print(json.dumps(aggregated, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
