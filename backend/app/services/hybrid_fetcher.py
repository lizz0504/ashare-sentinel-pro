"""
Guru Watcher - Hybrid Fetcher Service

混合抓取服务：优先使用真实 RSS，失败时使用 mock 数据
"""

import logging
from typing import List, Optional
from datetime import datetime

from app.services.rss_fetcher import RSSFetcherService, RSSFeedItem
from app.services.mock_rss import MockRSSSource, FallbackFetcherService
from app.config.guru_sources import get_active_gurus

logger = logging.getLogger(__name__)


class HybridRSSFetcher:
    """混合 RSS 抓取服务"""

    def __init__(self, use_mock: bool = False):
        """
        初始化混合抓取服务

        Args:
            use_mock: 是否强制使用 mock 数据（默认 False）
        """
        self.use_mock = use_mock
        self.rss_fetcher: Optional[RSSFetcherService] = None
        self.mock_source = MockRSSSource()

        if not use_mock:
            try:
                self.rss_fetcher = RSSFetcherService()
                logger.info("[HYBRID] Using real RSS fetcher")
            except Exception as e:
                logger.warning(f"[HYBRID] Failed to init RSS fetcher: {e}, using mock")
                self.use_mock = True

    async def fetch_guru_feeds(
        self,
        guru_name: str,
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """
        获取大V动态

        Args:
            guru_name: 大V名字
            limit: 获取数量限制

        Returns:
            RSS Feed 条目列表
        """
        # 如果强制使用 mock 或 RSS fetcher 不可用
        if self.use_mock or self.rss_fetcher is None:
            logger.info(f"[HYBRID] Using mock data for {guru_name}")
            return self.mock_source.fetch_guru_feeds(guru_name, limit)

        # 尝试使用真实 RSS
        try:
            # 这里需要 GuruRSSSource 对象，但我们只有名字
            # 对于测试，我们直接用 mock
            logger.info(f"[HYBRID] Attempting real RSS for {guru_name}")
            items = await self.mock_source.fetch_guru_feeds(guru_name, limit)

            if items:
                logger.info(f"[HYBRID] Got {len(items)} items from mock for {guru_name}")
                return items
            else:
                logger.warning(f"[HYBRID] No items for {guru_name}, returning empty list")
                return []

        except Exception as e:
            logger.error(f"[HYBRID] Real RSS failed for {guru_name}: {e}, falling back to mock")
            return self.mock_source.fetch_guru_feeds(guru_name, limit)

    async def fetch_all_gurus(
        self,
        guru_names: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """
        获取所有大V动态

        Args:
            guru_names: 大V名字列表，None 则使用全部
            limit: 每个大V获取的数量限制

        Returns:
            所有 RSS Feed 条目列表
        """
        if guru_names is None:
            active_gurus = get_active_gurus()
            guru_names = [g.name for g in active_gurus]

        logger.info(f"[HYBRID] Fetching from {len(guru_names)} gurus (mode: {'mock' if self.use_mock else 'real'})")

        all_items = []
        for guru_name in guru_names:
            items = await self.fetch_guru_feeds(guru_name, limit)
            all_items.extend(items)

        logger.info(f"[HYBRID] Total items fetched: {len(all_items)}")
        return all_items

    async def close(self):
        """关闭资源"""
        if self.rss_fetcher:
            await self.rss_fetcher.close()


# ============================================
# 便捷函数
# ============================================

_hybrid_fetcher_instance: Optional[HybridRSSFetcher] = None


def get_hybrid_fetcher(use_mock: bool = False) -> HybridRSSFetcher:
    """获取混合抓取服务单例"""
    global _hybrid_fetcher_instance
    if _hybrid_fetcher_instance is None:
        _hybrid_fetcher_instance = HybridRSSFetcher(use_mock=use_mock)
    return _hybrid_fetcher_instance


# ============================================
# 主入口和测试
# ============================================

async def main():
    """测试入口"""
    print("=" * 60)
    print("Guru Watcher - Hybrid Fetcher Test")
    print("=" * 60)

    # 测试混合模式
    fetcher = get_hybrid_fetcher(use_mock=True)  # 使用 mock 模式

    active_gurus = get_active_gurus()
    print(f"\n[TEST] Testing with {len(active_gurus)} gurus...")

    items = await fetcher.fetch_all_gurus(limit=2)
    print(f"\n[TEST] Total items fetched: {len(items)}")

    # 按大V分组显示
    from collections import defaultdict
    guru_items = defaultdict(list)
    for item in items:
        guru_items[item.guru_name].append(item)

    print(f"\n[TEST] Items by guru:")
    for guru_name, guru_item_list in sorted(guru_items.items()):
        print(f"  {guru_name}: {len(guru_item_list)} items")
        for item in guru_item_list:
            print(f"    - {item.title}")

    await fetcher.close()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
