"""
Guru Watcher - RSS Fetcher Service

从 RSSHub 抓取雪球大V动态的服务
"""

import feedparser
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import httpx

from app.config.guru_sources import GuruRSSSource, get_active_gurus

logger = logging.getLogger(__name__)


# ============================================
# RSS Feed 数据模型
# ============================================

@dataclass
class RSSFeedItem:
    """RSS Feed 条目"""
    id: str  # 唯一ID
    guru_name: str  # 大V名字
    platform: str  # 平台
    title: str  # 标题
    content: str  # 内容
    link: str  # 原始链接
    published: Optional[datetime]  # 发布时间
    author: Optional[str]  # 作者
    tags: List[str]  # 标签

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "guru_name": self.guru_name,
            "platform": self.platform,
            "title": self.title,
            "content": self.content,
            "link": self.link,
            "published": self.published.isoformat() if self.published else None,
            "author": self.author,
            "tags": self.tags,
        }


# ============================================
# RSS Fetcher Service
# ============================================

class RSSFetcherService:
    """RSS 抓取服务"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def fetch_from_rsshub(
        self,
        rss_url: str,
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """
        从 RSSHub 抓取数据

        Args:
            rss_url: RSSHub URL
            limit: 获取数量限制

        Returns:
            RSS Feed 条目列表
        """
        try:
            logger.info(f"[RSS] Fetching from {rss_url}")

            # 添加 User-Agent 头部避免被阻止
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }

            # 使用 httpx 抓取 RSS
            response = await self.client.get(rss_url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            # 解析 RSS
            feed = feedparser.parse(response.content)

            items = []
            for entry in feed.entries[:limit]:
                # 提取内容
                content = self._extract_content(entry)

                # 生成唯一ID
                item_id = self._generate_id(entry)

                # 解析发布时间
                published = self._parse_date(entry.get('published'))

                item = RSSFeedItem(
                    id=item_id,
                    guru_name="",  # 将在外部设置
                    platform="Xueqiu",
                    title=entry.get('title', ''),
                    content=content,
                    link=entry.get('link', ''),
                    published=published,
                    author=entry.get('author', ''),
                    tags=[tag.term for tag in entry.get('tags', [])],
                )
                items.append(item)

            logger.info(f"[RSS] Fetched {len(items)} items from {rss_url}")
            return items

        except httpx.HTTPError as e:
            logger.error(f"[RSS] HTTP error fetching {rss_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"[RSS] Error fetching {rss_url}: {e}")
            return []

    async def fetch_guru_feeds(
        self,
        guru: GuruRSSSource,
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """
        抓取单个大V的动态

        Args:
            guru: 大V配置
            limit: 获取数量限制

        Returns:
            RSS Feed 条目列表
        """
        items = await self.fetch_from_rsshub(guru.rss_url, limit)

        # 设置大V名字
        for item in items:
            item.guru_name = guru.name

        return items

    async def fetch_all_gurus(
        self,
        gurus: Optional[List[GuruRSSSource]] = None,
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """
        抓取所有大V的动态

        Args:
            gurus: 大V列表，None 则使用全部
            limit: 每个大V获取的数量限制

        Returns:
            所有 RSS Feed 条目列表
        """
        if gurus is None:
            gurus = get_active_gurus()

        logger.info(f"[RSS] Fetching feeds from {len(gurus)} gurus")

        # 并发抓取
        tasks = [self.fetch_guru_feeds(guru, limit) for guru in gurus]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_items = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[RSS] Error in parallel fetch: {result}")
            elif isinstance(result, list):
                all_items.extend(result)

        logger.info(f"[RSS] Total items fetched: {len(all_items)}")
        return all_items

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    def _extract_content(self, entry: Dict[str, Any]) -> str:
        """提取内容"""
        # 优先使用 content
        if hasattr(entry, 'content') and entry.content:
            if isinstance(entry.content, list) and len(entry.content) > 0:
                return entry.content[0].value
            return str(entry.content)

        # 其次使用 description
        if hasattr(entry, 'description') and entry.description:
            return entry.description

        # 最后使用 summary
        if hasattr(entry, 'summary') and entry.summary:
            return entry.summary

        return ""

    def _generate_id(self, entry: Dict[str, Any]) -> str:
        """生成唯一ID"""
        # 使用 link 或 id 作为唯一标识
        link = entry.get('link', '')
        entry_id = entry.get('id', '')

        if link:
            # 从 URL 中提取 ID
            import hashlib
            return hashlib.md5(link.encode()).hexdigest()

        if entry_id:
            return str(entry_id)

        # 使用时间戳和标题生成
        import hashlib
        title = entry.get('title', '')
        published = entry.get('published', '')
        unique_str = f"{title}:{published}"
        return hashlib.md5(unique_str.encode()).hexdigest()

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期"""
        if not date_str:
            return None

        try:
            # feedparser 已经解析了日期
            if isinstance(date_str, datetime):
                return date_str.replace(tzinfo=timezone.utc)

            # 尝试解析字符串
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"[RSS] Failed to parse date '{date_str}': {e}")
            return None


# ============================================
# 单例实例
# ============================================

_rss_fetcher_instance: Optional[RSSFetcherService] = None


def get_rss_fetcher() -> RSSFetcherService:
    """获取 RSS Fetcher 单例"""
    global _rss_fetcher_instance
    if _rss_fetcher_instance is None:
        _rss_fetcher_instance = RSSFetcherService()
    return _rss_fetcher_instance


# ============================================
# 主入口和测试
# ============================================

async def main():
    """测试入口"""
    print("=" * 60)
    print("Guru Watcher - RSS Fetcher Test")
    print("=" * 60)

    fetcher = get_rss_fetcher()

    # 打印大V列表
    from app.config.guru_sources import print_guru_list
    print_guru_list()

    # 获取活跃的大V
    active_gurus = get_active_gurus()
    print(f"\n[TEST] Fetching from {len(active_gurus)} active gurus...")

    # 测试单个大V
    test_guru = active_gurus[0]
    print(f"\n[TEST] Testing with {test_guru.name}...")

    items = await fetcher.fetch_guru_feeds(test_guru, limit=3)

    print(f"\n[TEST] Fetched {len(items)} items:")
    for item in items:
        print(f"\n  [{item.published}] {item.title}")
        print(f"  Content: {item.content[:100]}...")
        print(f"  Link: {item.link}")

    # 关闭客户端
    await fetcher.close()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
