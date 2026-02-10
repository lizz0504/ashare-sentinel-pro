"""
Guru Watcher - RSS Sources Configuration

大V监控名单 - 通过 RSSHub 抓取雪球动态

RSSHub URL 格式: {RSSHUB_URL}/xueqiu/user/{UID}
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

from app.core.config import settings


class GuruCategory(str, Enum):
    """大V分类"""
    TOP_BULLISH = "top_bullish"  # 顶级多头/主线派
    INDUSTRY_EXPERT = "industry_expert"  # 行业专家/深度研究
    MARKET_SENTIMENT = "market_sentiment"  # 市场情绪/避坑指南
    DEEP_VALUE = "deep_value"  # 深度价投/策略派
    COGNITION_CYCLE = "cognition_cycle"  # 认知/博弈/周期


@dataclass
class GuruRSSSource:
    """大V RSS 源配置"""
    name: str  # 大V名字
    platform: str  # 平台（Xueqiu）
    rss_url: str  # RSSHub URL
    uid: Optional[str] = None  # 雪球 UID
    category: GuruCategory = GuruCategory.INDUSTRY_EXPERT
    description: Optional[str] = None  # 描述
    followers_count: int = 0  # 粉丝数
    is_active: bool = True  # 是否启用监控

    def __post_init__(self):
        """从 RSS URL 提取 UID"""
        if self.uid is None and self.rss_url:
            # 从 URL 中提取 UID
            if "/xueqiu/user/" in self.rss_url:
                uid_start = self.rss_url.rfind("/") + 1
                # 移除可能的 URL 参数
                uid_end = self.rss_url.find("?", uid_start)
                if uid_end == -1:
                    uid_end = len(self.rss_url)
                self.uid = self.rss_url[uid_start:uid_end]


def get_rsshub_base_url() -> str:
    """获取 RSSHub 基础 URL"""
    if settings.RSSHUB_USE_PUBLIC:
        return "https://rsshub.app"
    return settings.RSSHUB_URL


def get_rss_url(uid: str) -> str:
    """根据 UID 生成 RSS URL"""
    return f"{get_rsshub_base_url()}/xueqiu/user/{uid}"


# ============================================
# 大V UID 配置（不包含完整 URL）
# ============================================

_GURU_UID_CONFIG: List[dict] = [
    # --- 1. 顶级多头/主线派 ---
    {
        "name": "但斌",
        "uid": "1102105103",
        "category": "top_bullish",
        "description": "主线极度坚定派",
        "followers_count": 1500000,
    },
    # --- 2. 行业专家/深度研究 ---
    {
        "name": "逸修",
        "uid": "1936609590",
        "category": "industry_expert",
        "description": "互联网/港股专家",
        "followers_count": 500000,
    },
    {
        "name": "卢桂凤",
        "uid": "7161883713",
        "category": "industry_expert",
        "description": "医药方向研究",
        "followers_count": 300000,
    },
    {
        "name": "郭荆璞",
        "uid": "7625126831",
        "category": "industry_expert",
        "description": "周期/卖方视角",
        "followers_count": 400000,
    },
    # --- 3. 市场情绪/避坑指南 ---
    {
        "name": "阿狸 (期货踩坑)",
        "uid": "9905072371",
        "category": "market_sentiment",
        "description": "期货踩坑实盘记录",
        "followers_count": 200000,
    },
    {
        "name": "阿狸 (消费观察)",
        "uid": "5691911217",
        "category": "market_sentiment",
        "description": "消费赛道观察",
        "followers_count": 200000,
    },
    {
        "name": "庶人哑士",
        "uid": "4925760634",
        "category": "market_sentiment",
        "description": "消费+情绪分析",
        "followers_count": 350000,
    },
    # --- 4. 深度价投/策略派 ---
    {
        "name": "滇南王",
        "uid": "2496980475",
        "category": "deep_value",
        "description": "深度价值投资",
        "followers_count": 600000,
    },
    {
        "name": "巍巍昆仑侠",
        "uid": "7815672011",
        "category": "deep_value",
        "description": "低估值/红利策略",
        "followers_count": 450000,
    },
    {
        "name": "边城浪子1986",
        "uid": "8254848373",
        "category": "deep_value",
        "description": "低估+风口捕捉",
        "followers_count": 550000,
    },
    # --- 5. 认知/博弈/周期 ---
    {
        "name": "三体人在地球",
        "uid": "7280306436",
        "category": "cognition_cycle",
        "description": "认知演习与博弈",
        "followers_count": 700000,
    },
    {
        "name": "静待花开十八载",
        "uid": "8032421430",
        "category": "cognition_cycle",
        "description": "制造周期研究",
        "followers_count": 380000,
    },
]


def build_guru_sources() -> List[GuruRSSSource]:
    """根据配置动态构建大V RSS 源列表"""
    sources = []
    for config in _GURU_UID_CONFIG:
        rss_url = get_rss_url(config["uid"])
        # 将字符串转换为 GuruCategory 枚举
        category_str = config["category"]
        category = GuruCategory(category_str) if isinstance(category_str, str) else category_str

        sources.append(
            GuruRSSSource(
                name=config["name"],
                platform="Xueqiu",
                rss_url=rss_url,
                uid=config["uid"],
                category=category,
                description=config["description"],
                followers_count=config["followers_count"],
                is_active=True,
            )
        )
    return sources


# 动态构建大V列表
GURU_RSS_SOURCES = build_guru_sources()


def refresh_guru_sources():
    """刷新大V源配置（当 RSSHub URL 变更时调用）"""
    global GURU_RSS_SOURCES
    GURU_RSS_SOURCES = build_guru_sources()
    return GURU_RSS_SOURCES


# ============================================
# 核心大V监控名单（动态构建）
# ============================================

# GURU_RSS_SOURCES 由 build_guru_sources() 动态构建
# 根据 settings.RSSHUB_URL 自动生成 RSS URL
GURU_RSS_SOURCES = build_guru_sources()


# ============================================
# 按分类分组
# ============================================

def get_gurus_by_category(category: GuruCategory) -> List[GuruRSSSource]:
    """按分类获取大V列表"""
    return [g for g in GURU_RSS_SOURCES if g.category == category]


def get_active_gurus() -> List[GuruRSSSource]:
    """获取所有启用的大V"""
    return [g for g in GURU_RSS_SOURCES if g.is_active]


def get_guru_by_name(name: str) -> Optional[GuruRSSSource]:
    """按名字获取大V配置"""
    for guru in GURU_RSS_SOURCES:
        if guru.name == name:
            return guru
    return None


# ============================================
# 辅助函数
# ============================================

def get_category_name(category: GuruCategory) -> str:
    """获取分类名称"""
    names = {
        GuruCategory.TOP_BULLISH: "顶级多头",
        GuruCategory.INDUSTRY_EXPERT: "行业专家",
        "market_sentiment": "市场情绪",
        "deep_value": "深度价投",
        "cognition_cycle": "认知周期",
    }
    return names.get(category, "其他")


def print_guru_list():
    """打印大V列表"""
    print("=" * 80)
    print("Guru Watcher - 大V监控名单")
    print("=" * 80)

    for category in GuruCategory:
        gurus = get_gurus_by_category(category)
        if not gurus:
            continue

        print(f"\n【{get_category_name(category)}】")
        for guru in gurus:
            status = "✓" if guru.is_active else "✗"
            print(f"  {status} {guru.name} (UID: {guru.uid})")
            print(f"     描述: {guru.description}")
            print(f"     RSS: {guru.rss_url}")

    print(f"\n总计: {len(GURU_RSS_SOURCES)} 位大V")


if __name__ == "__main__":
    print_guru_list()
