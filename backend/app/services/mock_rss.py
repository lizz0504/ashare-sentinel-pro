"""
Guru Watcher - Local Mock RSS Source

当 RSSHub 不可用时使用的本地模拟数据源
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

from app.services.rss_fetcher import RSSFeedItem


class MockRSSSource:
    """本地模拟 RSS 源"""

    # 模拟大V动态数据
    MOCK_DATA = {
        "但斌": [
            {
                "title": "加仓贵州茅台，长期价值投资",
                "content": "今天加仓了贵州茅台(600519)，当前位置安全边际较高，长期看好白酒板块。消费升级是长期趋势，优质股权是核心资产。",
                "link": "https://xueqiu.com/1102105103/123456",
                "published": datetime.now() - timedelta(hours=2),
            },
            {
                "title": "腾讯控股值得长期持有",
                "content": "腾讯控股(00700)依然是核心资产，互联网龙头地位稳固，护城河深。当前位置适合分批建仓。",
                "link": "https://xueqiu.com/1102105103/123457",
                "published": datetime.now() - timedelta(days=1),
            },
        ],
        "逸修": [
            {
                "title": "互联网板块见底信号",
                "content": "互联网公司经过大幅调整，估值已经回到合理区间。关注头部平台公司的投资机会。",
                "link": "https://xueqiu.com/1936609590/234567",
                "published": datetime.now() - timedelta(hours=4),
            },
            {
                "title": "港股通配置建议",
                "content": "通过港股通配置优质互联网龙头，是当前市场环境下的较好选择。",
                "link": "https://xueqiu.com/1936609590/234568",
                "published": datetime.now() - timedelta(hours=12),
            },
        ],
        "卢桂凤": [
            {
                "title": "医药行业长期逻辑不变",
                "content": "医药行业长期增长逻辑没有改变，人口老龄化趋势下，创新药和医疗器械是重点方向。",
                "link": "https://xueqiu.com/7161883713/345678",
                "published": datetime.now() - timedelta(hours=6),
            },
        ],
        "郭荆璞": [
            {
                "title": "周期股投资机会",
                "content": "当前周期股处于底部区域，关注化工、有色等行业的投资机会。供给端收缩是核心逻辑。",
                "link": "https://xueqiu.com/7625126831/456789",
                "published": datetime.now() - timedelta(hours=3),
            },
        ],
        "阿狸 (期货踩坑)": [
            {
                "title": "期货交易风险提示",
                "content": "最近又踩了一个坑，提醒大家期货交易风险巨大。严格止损是生存法则。",
                "link": "https://xueqiu.com/9905072371/567890",
                "published": datetime.now() - timedelta(hours=1),
            },
        ],
        "阿狸 (消费观察)": [
            {
                "title": "白酒渠道库存去化良好",
                "content": "调研发现白酒渠道库存去化良好，春节动销符合预期。高端白酒确定性更强。",
                "link": "https://xueqiu.com/5691911217/678901",
                "published": datetime.now() - timedelta(hours=8),
            },
        ],
        "庶人哑士": [
            {
                "title": "市场情绪过度悲观",
                "content": "当前市场情绪过于悲观，往往是布局的好时机。逆向投资需要耐心和勇气。",
                "link": "https://xueqiu.com/4925760634/789012",
                "published": datetime.now() - timedelta(hours=5),
            },
        ],
        "滇南王": [
            {
                "title": "低估值蓝筹机会",
                "content": "市场低迷时正是寻找低估值蓝筹的好时机。关注分红率高、现金流稳定的公司。",
                "link": "https://xueqiu.com/2496980475/890123",
                "published": datetime.now() - timedelta(hours=10),
            },
        ],
        "巍巍昆仑侠": [
            {
                "title": "红利策略长期有效",
                "content": "红利策略在震荡市中表现优异。高股息率公司提供稳定现金流，降低组合波动。",
                "link": "https://xueqiu.com/7815672011/901234",
                "published": datetime.now() - timedelta(hours=7),
            },
        ],
        "边城浪子1986": [
            {
                "title": "低估+风口双击",
                "content": "当前市场存在低估+风口的潜在双击机会。关注政策和行业景气度共振的标的。",
                "link": "https://xueqiu.com/8254848373/012345",
                "published": datetime.now() - timedelta(hours=9),
            },
        ],
        "三体人在地球": [
            {
                "title": "认知博弈在股市",
                "content": "股市本质上是认知的博弈。当市场形成一致预期时，往往意味着反转即将到来。",
                "link": "https://xueqiu.com/7280306436/123456",
                "published": datetime.now() - timedelta(hours=11),
            },
        ],
        "静待花开十八载": [
            {
                "title": "制造业周期启动",
                "content": "制造业周期有望启动，关注高端装备、工业机器人等细分领域的投资机会。",
                "link": "https://xueqiu.com/8032421430/234567",
                "published": datetime.now() - timedelta(hours=15),
            },
        ],
    }

    @classmethod
    def fetch_guru_feeds(
        cls,
        guru_name: str,
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """
        获取大V的模拟数据

        Args:
            guru_name: 大V名字
            limit: 获取数量限制

        Returns:
            RSS Feed 条目列表
        """
        items = cls.MOCK_DATA.get(guru_name, [])

        # 转换为 RSSFeedItem
        feed_items = []
        for i, item in enumerate(items[:limit]):
            feed_item = RSSFeedItem(
                id=f"mock_{guru_name}_{i}",
                guru_name=guru_name,
                platform="Xueqiu",
                title=item["title"],
                content=item["content"],
                link=item["link"],
                published=item["published"],
                author=guru_name,
                tags=[],
            )
            feed_items.append(feed_item)

        return feed_items

    @classmethod
    def fetch_all_feeds(
        cls,
        guru_names: List[str],
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """
        获取所有大V的模拟数据

        Args:
            guru_names: 大V名字列表
            limit: 每个大V获取的数量限制

        Returns:
            所有 RSS Feed 条目列表
        """
        all_items = []
        for guru_name in guru_names:
            items = cls.fetch_guru_feeds(guru_name, limit)
            all_items.extend(items)
        return all_items


# ============================================
# 备用抓取服务（当 RSSHub 不可用时）
# ============================================

class FallbackFetcherService:
    """备用抓取服务（使用 mock 数据）"""

    def __init__(self):
        self.mock_source = MockRSSSource()

    async def fetch_guru_feeds(
        self,
        guru_name: str,
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """获取大V动态（备用）"""
        return self.mock_source.fetch_guru_feeds(guru_name, limit)

    async def fetch_all_gurus(
        self,
        guru_names: List[str],
        limit: int = 20
    ) -> List[RSSFeedItem]:
        """获取所有大V动态（备用）"""
        return self.mock_source.fetch_all_feeds(guru_names, limit)

    async def close(self):
        """关闭（mock 不需要）"""
        pass


def get_fallback_fetcher() -> FallbackFetcherService:
    """获取备用抓取服务"""
    return FallbackFetcherService()
