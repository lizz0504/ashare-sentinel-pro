"""
Guru Watcher - Complete Supabase-Integrated Service

完整的大V信号监控服务：RSS抓取 → AI提取 → Supabase保存
"""

import asyncio
import logging
import feedparser
import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from supabase import create_client

from app.core.config import settings
from app.core.llm_factory import LLMFactory
from app.config.guru_sources import GURU_RSS_SOURCES, get_active_gurus

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
   - 股票别名映射：茅台→600519, 五粮液→000858, 宁德时代→300750
   - 返回格式：["600519", "NVDA"]

2. **sentiment**: 判断整体情绪倾向
   - "Bullish" - 明显看多
   - "Bearish" - 明显看空
   - "Neutral" - 中性

3. **action**: 操作建议
   - "BUY" - 买入
   - "SELL" - 卖出
   - "HOLD" - 持有
   - "COMMENT" - 评论

4. **summary**: 一句话总结（不超过50字）

**输出格式（纯JSON）**：
```json
{{
  "mentioned_symbols": ["股票代码"],
  "sentiment": "Bullish/Bearish/Neutral",
  "action": "BUY/SELL/HOLD/COMMENT",
  "summary": "一句话总结"
}}
```

请严格按照JSON格式输出，不要添加任何其他文字。
"""


# ============================================
# 主服务类
# ============================================

class GuruWatcherService:
    """大V信号监控服务（Supabase集成版）"""

    def __init__(self):
        self.client: Client = None
        self.rss_client = httpx.AsyncClient(timeout=30)
        self._init_client()

    def _init_client(self):
        """初始化 Supabase 客户端"""
        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            logger.info("[GURU] Supabase client initialized")
        except Exception as e:
            logger.error(f"[GURU] Failed to init Supabase client: {e}")

    async def _ai_extract(
        self,
        guru_name: str,
        platform: str,
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 从文本中提取交易信号
        """
        try:
            prompt = EXTRACTION_PROMPT.format(
                guru_name=guru_name,
                platform=platform,
                content=content
            )

            logger.debug(f"[GURU] Calling LLM for {guru_name}...")
            result = await LLMFactory.fast_reply(
                model="deepseek",
                system="你是一位专业的金融文本分析专家。请严格按照JSON格式返回结果。",
                user=prompt,
                timeout=15
            )

            logger.debug(f"[GURU] LLM response for {guru_name}: {result[:200]}...")

            if not result or result.startswith("[错误]"):
                logger.warning(f"[GURU] LLM returned error or empty for {guru_name}")
                return None

            # 解析 JSON
            parsed = self._parse_json(result)
            if parsed:
                logger.info(f"[GURU] Successfully extracted signal from {guru_name}")
            else:
                logger.warning(f"[GURU] Failed to parse JSON from LLM response for {guru_name}")
            return parsed

        except Exception as e:
            logger.error(f"[GURU] AI extraction error for {guru_name}: {e}")
            import traceback
            logger.error(f"[GURU] Traceback: {traceback.format_exc()}")
            return None

    def _parse_json(self, response: str) -> Optional[Dict]:
        """解析 JSON 响应"""
        import re

        logger.debug(f"[GURU] LLM Response: {response[:500]}")

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 提取 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if json_match:
            try:
                json_str = json_match.group(1)
                logger.debug(f"[GURU] Extracted JSON from code block: {json_str[:200]}")
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.debug(f"[GURU] Failed to parse JSON from code block: {e}")
                pass

        # 提取花括号内容
        first_brace = response.find('{')
        last_brace = response.rfind('}')
        if first_brace != -1 and last_brace != -1:
            try:
                json_text = response[first_brace:last_brace + 1]
                json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                logger.debug(f"[GURU] Extracted JSON from braces: {json_text[:200]}")
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.debug(f"[GURU] Failed to parse JSON from braces: {e}")
                pass

        logger.error(f"[GURU] Failed to parse JSON from response: {response[:300]}")
        return None

    async def fetch_and_save_all(
        self,
        guru_names: Optional[List[str]] = None,
        limit_per_guru: int = 3
    ) -> Dict[str, Any]:
        """
        遍历所有大V，抓取RSS、提取信号、保存到数据库

        Args:
            guru_names: 大V名字列表
            limit_per_guru: 每个大V获取的数量限制

        Returns:
            采集统计信息
        """
        if guru_names is None:
            active_gurus = get_active_gurus()
            guru_names = [g.name for g in active_gurus]

        logger.info(f"[GURU] 🦅 Scanning {len(guru_names)} gurus")

        stats = {
            "total_gurus": len(guru_names),
            "successful_gurus": 0,
            "feeds_fetched": 0,
            "signals_extracted": 0,
            "signals_saved": 0,
            "errors": [],
            "saved_summaries": []
        }

        for guru_name in guru_names:
            try:
                # 获取大V配置
                guru_config = None
                for g in GURU_RSS_SOURCES:
                    if g.name == guru_name:
                        guru_config = g
                        break

                if not guru_config:
                    logger.warning(f"[GURU] Guru not found: {guru_name}")
                    continue

                # 1. 抓取 RSS
                feed = await self._fetch_rss(guru_config.rss_url)
                if not feed or not feed.entries:
                    logger.warning(f"[GURU] No entries for {guru_name}")
                    continue

                stats["feeds_fetched"] += len(feed.entries[:limit_per_guru])

                # 2. 处理条目
                for entry in feed.entries[:limit_per_guru]:
                    try:
                        link = entry.get('link', '')
                        if not link:
                            continue

                        # 3. 去重
                        existing = self.client.table("guru_signals").select("id").eq("source_link", link).execute()
                        if existing.data:
                            continue

                        # 4. 提取内容
                        title = entry.get('title', '')
                        description = entry.get('description', '')
                        content = f"{title}\n{description}"

                        # 5. AI 提取
                        ai_result = await self._ai_extract(
                            guru_name=guru_name,
                            platform=guru_config.platform,
                            content=content
                        )

                        if not ai_result:
                            continue

                        stats["signals_extracted"] += 1

                        # 6. 保存到数据库
                        signal_data = {
                            "guru_name": guru_name,
                            "platform": guru_config.platform,
                            "source_link": link,
                            "source_id": f"{guru_config.uid}_{hash(link)}",
                            "raw_text": content,
                            "publish_time": self._parse_date(entry.get('published')),
                            "mentioned_symbols": ai_result.get("mentioned_symbols", []),
                            "sentiment": ai_result.get("sentiment", "Neutral"),
                            "action": ai_result.get("action", "COMMENT"),
                            "summary": ai_result.get("summary", ""),
                            "related_themes": ai_result.get("related_themes", []),
                            "key_factors": ai_result.get("key_factors", []),
                            "confidence_score": 0.8,
                        }

                        result = self.client.table("guru_signals").upsert(
                            signal_data,
                            on_conflict="source_link"
                        ).execute()

                        if result.data:
                            stats["signals_saved"] += 1
                            summary = ai_result.get("summary", "")
                            stats["saved_summaries"].append(f"{guru_name}: {summary}")
                            logger.info(f"[GURU] ✅ {guru_name} -> {summary}")

                    except Exception as e:
                        logger.error(f"[GURU] Error processing entry: {e}")

                stats["successful_gurus"] += 1

            except Exception as e:
                logger.error(f"[GURU] Error processing {guru_name}: {e}")
                stats["errors"].append(f"{guru_name}: {str(e)}")

        logger.info(f"[GURU] Collection complete: {stats}")
        return stats

    async def _fetch_rss(self, rss_url: str) -> Optional[feedparser.FeedParserDict]:
        """抓取 RSS feed"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }

            response = await self.rss_client.get(rss_url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            return feedparser.parse(response.content)

        except Exception as e:
            logger.error(f"[GURU] RSS fetch error: {e}")
            return None

    def _parse_date(self, date_obj) -> Optional[str]:
        """解析日期"""
        if not date_obj:
            return None

        try:
            if hasattr(date_obj, 'isoformat'):
                return date_obj.isoformat()
            return str(date_obj)
        except Exception:
            return None

    async def get_recent_signals(self, limit: int = 20) -> List[Dict]:
        """获取最近的信号"""
        try:
            result = self.client.table("guru_signals").select("*").order("created_at", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"[GURU] Error getting signals: {e}")
            return []

    async def get_aggregated_sentiment(self, symbol: str) -> Dict[str, Any]:
        """获取股票聚合情绪"""
        try:
            result = self.client.table("guru_signals").select("*").contains("mentioned_symbols", [symbol]).execute()

            if not result.data:
                return {"symbol": symbol, "total_signals": 0, "avg_sentiment": "Neutral"}

            signals = result.data
            bullish = sum(1 for s in signals if s.get("sentiment") == "Bullish")
            bearish = sum(1 for s in signals if s.get("sentiment") == "Bearish")
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
                "neutral_count": total - bullish - bearish,
                "avg_sentiment": avg_sentiment
            }
        except Exception as e:
            logger.error(f"[GURU] Error getting sentiment: {e}")
            return {"symbol": symbol, "error": str(e)}

    async def close(self):
        """关闭资源"""
        await self.rss_client.aclose()


# ============================================
# 单例实例
# ============================================

_guru_watcher_instance: Optional[GuruWatcherService] = None


def get_guru_watcher_service() -> GuruWatcherService:
    """获取 GuruWatcher 单例"""
    global _guru_watcher_instance
    if _guru_watcher_instance is None:
        _guru_watcher_instance = GuruWatcherService()
    return _guru_watcher_instance


# ============================================
# 主入口和测试
# ============================================

async def main():
    """测试入口"""
    print("=" * 60)
    print("Guru Watcher - Complete Service Test")
    print("=" * 60)

    service = get_guru_watcher_service()

    # 测试完整采集周期
    print("\n[TEST] Running collection cycle...")
    stats = await service.fetch_and_save_all(
        guru_names=["但斌", "逸修", "卢桂凤"],
        limit_per_guru=2
    )

    print(f"\n[TEST] Results:")
    print(f"  Total gurus: {stats['total_gurus']}")
    print(f"  Successful: {stats['successful_gurus']}")
    print(f"  Feeds fetched: {stats['feeds_fetched']}")
    print(f"  Signals extracted: {stats['signals_extracted']}")
    print(f"  Signals saved: {stats['signals_saved']}")

    if stats['saved_summaries']:
        print(f"\n[TEST] Saved signals:")
        for summary in stats['saved_summaries']:
            print(f"  - {summary}")

    # 测试获取信号
    print(f"\n[TEST] Fetching recent signals...")
    signals = await service.get_recent_signals(limit=5)
    print(f"  Retrieved {len(signals)} signals")

    # 测试聚合情绪
    print(f"\n[TEST] Aggregated sentiment for 600519...")
    sentiment = await service.get_aggregated_sentiment("600519")
    print(f"  Total: {sentiment['total_signals']}")
    print(f"  Avg sentiment: {sentiment['avg_sentiment']}")

    await service.close()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
