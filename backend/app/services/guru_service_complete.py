"""
Guru Watcher - Complete Service Implementation

完整的大V信号监控服务：RSS抓取 → AI提取 → 数据库保存
"""

import asyncio
import logging
import feedparser
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session

from app.config.guru_sources import GURU_RSS_SOURCES, get_active_gurus
from app.models.guru import GuruSignalDB, get_guru_signal_db, GURU_LIST
from app.core.llm_factory import LLMFactory
from app.models.guru_signal import GuruSignalSchema, schema_to_orm

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
# 主服务类
# ============================================

class GuruService:
    """大V信号监控服务（完整实现版）"""

    def __init__(self):
        self.db_client = get_guru_signal_db()
        self.rss_client = httpx.AsyncClient(timeout=30)

    async def _ai_extract(
        self,
        guru_name: str,
        platform: str,
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 从文本中提取交易信号

        Args:
            guru_name: 大V名字
            platform: 平台名称
            content: 帖子内容

        Returns:
            提取的结果字典，失败返回 None
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

            return extraction_result

        except Exception as e:
            logger.error(f"[GURU] Error in AI extraction: {e}")
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

        logger.error(f"[GURU] Failed to parse JSON from: {response[:300]}")
        return None

    async def fetch_and_save_all(
        self,
        guru_names: Optional[List[str]] = None,
        limit_per_guru: int = 3
    ) -> Dict[str, Any]:
        """
        遍历所有大V，抓取RSS、提取信号、保存到数据库

        Args:
            guru_names: 大V名字列表，None 则使用全部
            limit_per_guru: 每个大V获取的数量限制

        Returns:
            采集统计信息
        """
        if guru_names is None:
            active_gurus = get_active_gurus()
            guru_names = [g.name for g in active_gurus]

        logger.info(f"[GURU] Scanning {len(guru_names)} gurus")

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
                    logger.warning(f"[GURU] Guru not found in config: {guru_name}")
                    continue

                # 1. 抓取 RSS
                feed = await self._fetch_rss(guru_config.rss_url)
                if not feed or not feed.entries:
                    logger.warning(f"[GURU] No entries found for {guru_name}")
                    continue

                stats["feeds_fetched"] += len(feed.entries[:limit_per_guru])

                # 2. 处理每个条目
                for entry in feed.entries[:limit_per_guru]:
                    try:
                        link = entry.get('link', '')
                        if not link:
                            continue

                        # 3. 去重检查
                        existing = self.db_client.table("guru_signals").select("id").eq("source_link", link).execute()
                        if existing.data:
                            logger.debug(f"[GURU] Duplicate link skipped: {link}")
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

                        # 添加交易观点
                        trading_idea = ai_result.get("trading_idea")
                        if trading_idea:
                            signal_data.update({
                                "entry_point": trading_idea.get("entry_point"),
                                "stop_loss": trading_idea.get("stop_loss"),
                                "target_price": trading_idea.get("target_price"),
                                "time_horizon": trading_idea.get("time_horizon"),
                                "position_size": trading_idea.get("position_size"),
                                "reasoning": trading_idea.get("reasoning"),
                            })

                        # 保存（使用 upsert 避免重复）
                        result = self.db_client.table("guru_signals").upsert(
                            signal_data,
                            on_conflict="source_link"
                        ).execute()

                        if result.data:
                            stats["signals_saved"] += 1
                            stats["saved_summaries"].append(ai_result.get("summary", ""))
                            logger.info(f"[GURU] ✅ Saved: {guru_name} -> {ai_result.get('summary', '')}")

                    except Exception as e:
                        logger.error(f"[GURU] Error processing entry for {guru_name}: {e}")

                stats["successful_gurus"] += 1

            except Exception as e:
                logger.error(f"[GURU] Error fetching {guru_name}: {e}")
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

            feed = feedparser.parse(response.content)
            return feed

        except Exception as e:
            logger.error(f"[GURU] RSS fetch error: {e}")
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """解析日期"""
        if not date_str:
            return None

        try:
            if isinstance(date_str, datetime):
                return date_str.isoformat()

            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str).isoformat()
        except Exception:
            return None

    async def close(self):
        """关闭客户端"""
        await self.rss_client.aclose()


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
# 主入口和测试
# ============================================

async def main():
    """测试入口"""
    print("=" * 60)
    print("Guru Watcher - Complete Service Test")
    print("=" * 60)

    service = get_guru_service()

    # 测试完整采集周期
    print("\n[TEST] Running collection cycle...")
    stats = await service.fetch_and_save_all(
        guru_names=["但斌", "逸修", "卢桂凤"],  # 测试前3位大V
        limit_per_guru=2
    )

    print(f"\n[TEST] Collection Results:")
    print(f"  Total gurus: {stats['total_gurus']}")
    print(f"  Successful: {stats['successful_gurus']}")
    print(f"  Feeds fetched: {stats['feeds_fetched']}")
    print(f"  Signals extracted: {stats['signals_extracted']}")
    print(f"  Signals saved: {stats['signals_saved']}")

    if stats['errors']:
        print(f"\n[TEST] Errors:")
        for error in stats['errors']:
            print(f"  - {error}")

    await service.close()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
