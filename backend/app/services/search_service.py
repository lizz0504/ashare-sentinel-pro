# -*- coding: utf-8 -*-
"""
Search Service - 增强版网络检索服务
使用 Tavily Search API 获取最新新闻、研报和市场情报，解决 AI 幻觉问题

优化需求：
1. Query Pre-processing：将原始查询用站点参数包装
2. 强制高级搜索：search_depth="advanced"
3. 严格时间窗过滤：保留 days=7 但添加 include_raw_content=True
4. 内容去噪：剔除包含"行情"、"实时行情"、"个股概况"、"资金流向"的结果
5. 结果分层：如果少于3条结果，明确标注"非实时信息"
6. 日期格式规范化：匹配正文中日期格式（如"2026年2月"、"2026-02"）
"""

import os
import asyncio
import re
from typing import Dict, Optional
from datetime import datetime, timedelta
from tavily import TavilyClient

_tavily_client = None

# ============================================
# 全局配置
# ============================================

# 支持的搜索站点配置
SITE_CONFIG = {
    "eastmoney.com": {"name": "东方财富", "query_prefix": "site:eastmoney.com "},
    "xueqiu.com": {"name": "雪球", "query_prefix": "site:xueqiu.com "},
    "sina.com.cn": {"name": "新浪财经", "query_prefix": "site:sina.com.cn "},
    "10jqka.com.cn": {"name": "同花顺", "query_prefix": "site:10jqka.com.cn "},
    "cs.com.cn": {"name": "中证网", "query_prefix": "site:cs.com.cn "},
    "stock.stcn.com": {"name": "巨潮资讯", "query_prefix": "site:stock.stcn.com "},
    "sse.com.cn": {"name": "上交所", "query_prefix": "site:sse.com.cn "},
    "szse.cn": {"name": "深交所", "query_prefix": "site:szse.cn "},
    "cninfo.com.cn": {"name": "中证网", "query_prefix": "site:cninfo.com.cn "},
}

# 来源优先级配置 (0-1, 越高越优先)
SOURCE_PRIORITIES = {
    "cninfo.com.cn": 1.0,     # 巨潮资讯 (官方公告)
    "sse.com.cn": 1.0,          # 上交所 (官方)
    "szse.cn": 1.0,           # 深交所 (官方)
    "stock.stcn.com": 0.95,     # 巨潮资讯 (公告)
    "cs.com.cn": 0.8,           # 中证网 (权威)
    "eastmoney.com": 0.7,       # 东方财富
    "10jqka.com.cn": 0.6,      # 同花顺
    "sina.com.cn": 0.7,         # 新浪财经
    "xueqiu.com": 0.4,          # 雪球 (用户生成内容)
}

# 噪声关键词（用于内容去噪）
NOISE_KEYWORDS = [
    "行情", "实时行情", "个股概况", "资金流向",
    "机构评级", "晨会早报", "午间公告",
    "龙虎榜", "概念板块", "热点追踪",
    "大宗交易", "融资融券", "股指期货",
    "港股通", "北向资金", "债市", "基"
]

# ============================================
# Tavily 客户端初始化
# ============================================


def _get_tavily_client():
    """获取或创建 Tavily 客户端"""
    global _tavily_client
    if _tavily_client is None:
        try:
            # 确保加载.env文件
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("TAVILY_API_KEY")

            if not api_key:
                print(
                    "[SEARCH] ERROR: TAVILY_API_KEY not found "
                    "in environment"
                )
                return None

            # 验证API key格式
            if not api_key.startswith('tvly-'):
                print(
                    "[SEARCH] WARNING: API key format may be invalid "
                    "(should start with 'tvly-')"
                )
                return None

            # 初始化客户端
            print(
                f"[SEARCH] Tavily API Key found (length: {len(api_key)}, "
                f"prefix: {api_key[:10]}...)"
            )
            _tavily_client = TavilyClient(api_key=api_key)
            print("[SEARCH] Tavily Search client initialized successfully")

        except ImportError:
            print(
                "[SEARCH] ERROR: tavily-python not installed. "
                "Run: pip install tavily-python"
            )
            return None
        except Exception as e:
            print(f"[SEARCH] ERROR: Failed to init Tavily client: {e}")
            _tavily_client = None

    return _tavily_client


# ============================================
# 查询预处理
# ============================================


def _preprocess_query(
    symbol: str,
    stock_name: str,
    query_type: str = "news"
) -> str:
    """
    预处理查询字符串，添加站点参数和高级搜索选项

    Args:
        symbol: 股票代码
        stock_name: 股票名称
        query_type: 查询类型 (news/company)

    Returns:
        增强后的查询字符串
    """
    # 确定查询类型
    if query_type not in ["news", "company"]:
        query_type = "news"

    # 获取时间窗（最近7天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    date_range = (
        f"{start_date.strftime('%Y-%m-%d')} TO "
        f"{end_date.strftime('%Y-%m-%d')}"
    )

    # 构建基础查询
    base_query = (
        f"{stock_name} {symbol} {stock_name} "
        "最新 研报 业绩 利好 利空"
    )

    # 根据查询类型使用不同策略
    if query_type == "news":
        # 新闻搜索：要求深度搜索，包含原始内容
        sites = "eastmoney.com OR xueqiu.com OR sina.com.cn "
        sites += "OR 10jqka.com.cn OR cs.com.cn"
        return f'({base_query} ({date_range}) {{site: {sites}}})'
    elif query_type == "company":
        # 公司信息：基础搜索即可
        return f'"{stock_name} {symbol} 主营业务 行业 简介 公司资料"'


# ============================================
# 内容质量评分（用于去噪）
# ============================================

def _calculate_content_quality_score(title: str, content: str) -> float:
    """
    计算内容质量分数 (0-1)，分数越高越可能是有价值的新闻

    评分规则：
    - 标题包含核心关键词 (+0.3)
    - 内容长度适中 (+0.2)
    - 标题格式规范 (+0.1)
    - 来源可信度 (+0.2)
    - 时效性 (+0.2，7天内内容 +0.3
    """
    score = 0.0

    # 标题质量 (0.3)
    if title and len(title) >= 5 and len(title) <= 30:
        score += 0.3

    # 内容长度 (0.2) - 适中长度更有价值
    if content and 200 <= len(content) <= 1000:
        score += 0.2
    elif len(content) > 1000:
        score += 0.1

    # 标题格式 (0.1) - 包含股票代码或数字
    if any(char.isdigit() for char in title):
        score += 0.1

    # 来源可信度 (0.2) - 来自主流财经网站
    credible_sources = [
        "eastmoney.com",
        "xueqiu.com",
        "sina.com.cn",
        "10jqka.com.cn"
    ]
    if any(source in content for source in credible_sources):
        score += 0.2

    # 时效性 (0.3) - 7天内内容
    # 提取发布日期判断
    try:
        pub_date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', content)
        if pub_date_match:
            pub_date = datetime.strptime(pub_date_match.group(0), '%Y-%m-%d')
            days_diff = (datetime.now() - pub_date).days
            if days_diff <= 7:
                score += 0.3
    except Exception:
        pass

    return min(score, 1.0)


# ============================================
# 噪声检测
# ============================================

def _is_noise_content(title: str, content: str) -> bool:
    """
    检测内容是否为噪音（包含行情关键词）

    Returns:
        True if 是噪音，False if 不是噪音
    """
    # 检查是否包含噪音关键词
    noise_keywords = NOISE_KEYWORDS

    # 标题检测
    title_lower = title.lower()
    for keyword in noise_keywords:
        if keyword in title_lower:
            return True

    # 内容检测（更严格）
    content_lower = content.lower()
    for keyword in noise_keywords:
        if keyword in content_lower:
            return True

    # 特殊情况：如果是"个股行情"这类明确噪音，即使标题不含关键词也要过滤
    if any(kw in title_lower for kw in ["个股", "行情", "资金流"]):
        return True

    return False


# ============================================
# 日期格式规范化
# ============================================

def _extract_and_normalize_date(content: str) -> Optional[str]:
    """
    从文章内容中提取并规范化日期格式

    支持的格式：
    - "2026年2月"  ->  2026-02
    - "2026-02"     -> 2026-02

    Returns:
        规范化的日期字符串，如果未找到则返回 None
    """
    # 优先尝试匹配常见中文日期格式
    date_patterns = [
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日', 3),  # 2024年02月15日
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', 3),      # 2024-02-15
        (r'(\d{4})/(\d{1,2})/(\d{1,2})', 3),      # 2024/02/15
        (r'(\d{4})年(\d{1,2})月', 2),              # 2024年02月
    ]

    for pattern, group_count in date_patterns:
        match = re.search(pattern, content)
        if match:
            try:
                year = match.group(1)
                month = match.group(2).lstrip('0') or '1'
                if group_count >= 3:
                    day = match.group(3).lstrip('0') or '1'
                    normalized_date = (
                        f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    )
                else:
                    normalized_date = f"{year}-{month.zfill(2)}"
                return normalized_date
            except Exception:
                continue

    return None


# ============================================
# 财经新闻搜索 (增强版 - 多策略召回)
# ============================================


async def _execute_single_search(
    client,
    query: str,
    max_results: int,
    days: int = 7
) -> list:
    """执行单次搜索并返回结果"""
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            days=days,
            include_domains=list(SITE_CONFIG.keys()),
            include_raw_content=False,
            include_answer=False
        )
        return response.get("results", [])
    except Exception as e:
        print(f"[SEARCH] Query failed: {query[:50]}... - {e}")
        return []


def _group_results_by_topic(results: list) -> dict:
    """按主题分组：业绩、公告、研报、重大事项、其他"""
    groups = {
        "业绩预告": [],
        "公司公告": [],
        "研报评级": [],
        "重大事项": [],
        "其他": []
    }

    for result in results:
        title = result.get("title", "").lower()

        # 按标题关键词分类
        if any(kw in title for kw in
               ["业绩", "预告", "快报", "财报", "中报", "年报"]):
            groups["业绩预告"].append(result)
        elif any(kw in title for kw in
                 ["公告", "通知", "股东大会", "董事会"]):
            groups["公司公告"].append(result)
        elif any(kw in title for kw in
                 ["研报", "评级", "目标价", "买入", "卖出", "中性"]):
            groups["研报评级"].append(result)
        elif any(kw in title for kw in
                 ["重组", "并购", "分红", "定增", "回购", "合作", "签约"]):
            groups["重大事项"].append(result)
        else:
            groups["其他"].append(result)

    # 移除空分组
    return {k: v for k, v in groups.items() if v}


def _apply_source_priority_boost(results: list) -> list:
    """根据来源优先级调整质量分数"""
    for result in results:
        url = result.get("url", "")
        base_score = result.get("score", 0.5)

        # 从URL提取域名
        for domain, priority in SOURCE_PRIORITIES.items():
            if domain in url:
                # 应用优先级加成 (0.5~1.5倍)
                boosted_score = min(1.0, base_score * (0.8 + priority))
                result["score"] = boosted_score
                result["priority_boost"] = priority
                break

    return results


async def search_financial_news(
    symbol: str,
    stock_name: str,
    max_results: int = 10
) -> Dict:
    """
    搜索最新的财经新闻、研报和市场情报 (增强版 - 多策略召回)

    改进点:
    1. 多次搜索策略: "最新消息"、"研报评级"、"业绩预告" 3个查询
    2. 质量过滤: 排除纯索引页面、过短内容
    3. 内容验证: 必须包含股票名称或代码
    4. 时效性提示: 标注"最近7天"警告

    Args:
        symbol: 股票代码 (如 "688008")
        stock_name: 股票名称 (如 "澜起科技")
        max_results: 最大返回结果数

    Returns:
        {
            "symbol": str,
            "stock_name": str,
            "query": str,
            "results": List[Dict],
            "summary": str,
            "search_time": str,
            "search_queries_used": list  # 使用的查询列表
        }
    """
    client = _get_tavily_client()
    if not client:
        return {
            "symbol": symbol,
            "stock_name": stock_name,
            "error": "Tavily not configured",
            "results": [],
            "summary": "【网络搜索未启用】请设置 TAVILY_API_KEY 环境变量",
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "search_queries_used": []
        }

    # ====================================================================
    # 策略1: 多查询并行召回 (提高召回率) - 5路查询
    # ====================================================================
    search_queries = [
        # 查询1: 最新消息
        f'({stock_name} {symbol}) (最新 消息 动态 公告)',
        # 查询2: 研报评级
        f'({stock_name} {symbol}) (研报 评级 目标价 买入 卖出)',
        # 查询3: 业绩预告
        f'({stock_name} {symbol}) (业绩 预告 财报 中报 年报)',
        # 查询4: 重大事项 (新增)
        f'({stock_name} {symbol}) (重组 并购 分红 定增 回购)',
        # 查询5: 公司公告 (新增)
        f'({stock_name}) 投资者关系 活动 路演 调研'
    ]

    print(f"[SEARCH] Multi-strategy search for {symbol} - {stock_name}")
    print("[SEARCH] Query 1: 最新消息")
    print("[SEARCH] Query 2: 研报评级")
    print("[SEARCH] Query 3: 业绩预告")
    print("[SEARCH] Query 4: 重大事项")
    print("[SEARCH] Query 5: 公司公告")

    all_results = []
    seen_urls = set()  # URL去重
    seen_titles = set()  # 标题去重
    quality_threshold = 0.4  # 初始质量阈值
    days_window = 7  # 初始时间窗

    try:
        # 第一轮：执行5个查询
        results_per_query = await asyncio.gather(
            _execute_single_search(
                client, search_queries[0], max_results, days_window
            ),
            _execute_single_search(
                client, search_queries[1], max_results, days_window
            ),
            _execute_single_search(
                client, search_queries[2], max_results, days_window
            ),
            _execute_single_search(
                client, search_queries[3], max_results, days_window
            ),
            _execute_single_search(
                client, search_queries[4], max_results, days_window
            )
        )

        # 合并并去重结果
        for query_idx, query_results in enumerate(results_per_query):
            query_name = [
                "最新消息", "研报评级", "业绩预告",
                "重大事项", "公司公告"
            ][query_idx]
            print(
                f"[SEARCH] {query_name} query returned "
                f"{len(query_results)} results"
            )

            for result in query_results:
                url = result.get("url", "")
                title = result.get("title", "")
                content = result.get("content", "")

                # URL去重
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # 标题去重（去除完全相同的标题）
                title_normalized = title.strip().lower()
                if title_normalized in seen_titles:
                    continue
                seen_titles.add(title_normalized)

                # ====================================================================
                # 策略2: 严格质量过滤
                # ====================================================================

                # 2.1 排除纯索引页面（包含特征关键词）
                index_page_keywords = [
                    "数据中心",
                    "数据统计",
                    "行情中心",
                    "f10数据",
                    "个股资料",
                    "股票列表",
                    "全部股票",
                    "数据查询",
                    "行情软件",
                    "level1行情",
                    "盈亏预测",
                    "业绩预告明细",
                    "业绩预告汇总表"
                ]
                is_index_page = any(kw in title for kw in index_page_keywords)
                if is_index_page:
                    print(f"[SEARCH] Filtered index page: {title[:40]}...")
                    continue

                # 2.2 内容长度检查（过短内容排除）
                if len(content) < 50:
                    print(f"[SEARCH] Filtered too short: {title[:40]}...")
                    continue

                # ====================================================================
                # 策略3: 内容相关性验证 (必须包含股票名称或代码)
                # ====================================================================
                # 标题和内容中必须出现股票名称或代码
                title_content = f"{title} {content}".lower()
                stock_name_lower = stock_name.lower()
                symbol_lower = symbol.lower()
                if (stock_name_lower not in title_content and
                        symbol_lower not in title_content):
                    print(f"[SEARCH] Filtered irrelevant: {title[:40]}...")
                    continue

                # ====================================================================
                # 质量评分
                # ====================================================================
                quality_score = _calculate_content_quality_score(
                    title, content
                )

                # 噪声检测
                is_noise = _is_noise_content(title, content)
                if is_noise:
                    print(f"[SEARCH] Filtered noise: {title[:40]}...")
                    continue

                # 应用质量阈值
                if quality_score >= quality_threshold:
                    all_results.append({
                        "title": title,
                        "url": url,
                        "content": content,
                        "score": quality_score,
                        "published_date": result.get("published_date", ""),
                        "is_realtime": False,
                        "query_source": query_name  # 标记来源查询
                    })
                else:
                    print(
                        f"[SEARCH] Low quality filtered: {title[:40]} "
                        f"(score: {quality_score:.2f})"
                    )

        # ====================================================================
        # 策略5: 智能降级机制
        # ====================================================================
        # 如果结果不足3条，启动降级策略
        if len(all_results) < 3:
            print(
                f"[SEARCH] [!] Results below threshold "
                f"({len(all_results)} < 3), activating fallback..."
            )

            # 降级1: 扩展时间窗
            if days_window == 7:
                print("[SEARCH] Fallback 1: Expanding time window to 14 days")
                days_window = 14
                # 重新执行所有查询
                fallback_results = await asyncio.gather(
                    _execute_single_search(
                        client, search_queries[0], max_results, days_window
                    ),
                    _execute_single_search(
                        client, search_queries[1], max_results, days_window
                    ),
                    _execute_single_search(
                        client, search_queries[2], max_results, days_window
                    ),
                    _execute_single_search(
                        client, search_queries[3], max_results, days_window
                    ),
                    _execute_single_search(
                        client, search_queries[4], max_results, days_window
                    )
                )

                # 合并降级结果
                for query_idx, query_results in enumerate(fallback_results):
                    query_name = [
                        "最新消息", "研报评级", "业绩预告",
                        "重大事项", "公司公告"
                    ][query_idx]
                    for result in query_results:
                        url = result.get("url", "")
                        title = result.get("title", "")
                        content = result.get("content", "")

                        if url not in seen_urls:
                            seen_urls.add(url)
                            title_normalized = title.strip().lower()
                            if title_normalized not in seen_titles:
                                seen_titles.add(title_normalized)

                                # 重复质量检查
                                quality_score = (
                                    _calculate_content_quality_score(
                                        title, content
                                    )
                                )
                                if not _is_noise_content(
                                    title, content
                                ) and len(content) >= 50:
                                    title_content = (
                                        f"{title} {content}".lower()
                                    )
                                    condition = (
                                        stock_name_lower in title_content or
                                        symbol_lower in title_content
                                    )
                                    if condition:
                                        all_results.append({
                                            "title": title,
                                            "url": url,
                                            "content": content,
                                            "score": quality_score,
                                            "published_date": result.get(
                                                "published_date", ""
                                            ),
                                            "is_realtime": False,
                                            "query_source": (
                                                f"{query_name}(14天)"
                                            )
                                        })

                print(f"[SEARCH] After fallback 1: {len(all_results)} results")

            # 降级2: 降低质量阈值 (如果仍然不足)
            if len(all_results) < 3:
                print(
                    "[SEARCH] Fallback 2: Lowering quality threshold "
                    "to 0.3"
                )
                # 添加被低分过滤的结果
                for result in list(all_results):
                    if result.get("score", 0) < 0.4:
                        result["score"] += 0.15  # 提升分数
                        result["priority_boost"] = (
                            result.get("priority_boost", 0) + 0.1
                        )

        # ====================================================================
        # 应用来源优先级加成
        # ====================================================================
        all_results = _apply_source_priority_boost(all_results)

        # 按质量分数排序（高质量优先）
        sorted_results = sorted(
            all_results, key=lambda x: x.get("score", 0), reverse=True
        )

        # 限制最终结果数量
        final_results = sorted_results[:max_results]

        # ====================================================================
        # 结果分组统计
        # ====================================================================
        topic_groups = _group_results_by_topic(final_results)

        # 提取日期并规范化
        has_published_date = False
        for result in final_results:
            content = result.get("content", "")
            extracted_date = _extract_and_normalize_date(content)
            if extracted_date:
                result["published_date"] = extracted_date
                has_published_date = True
            else:
                # 使用Tavily返回的日期
                tavily_date = result.get("published_date", "")
                if tavily_date:
                    result["published_date"] = tavily_date
                    has_published_date = True

        # ====================================================================
        # 策略4: 时效性提示标注 + 分组展示
        # ====================================================================
        result_count = len(final_results)
        topic_info = "无分组"
        summary = ""
        if result_count == 0:
            summary = (
                f"[网络情报 - {stock_name}]\\n[!] 未找到相关新闻。"
                "可能原因：1) Tavily数据库覆盖不足 2) 搜索时间窗过窄 "
                "3) 该股票近期无重大事件"
            )
        elif result_count < 3:
            summary = (
                f"[网络情报 - {stock_name} (最近{days_window}天)]\\n[!] "
                f"仅找到 {result_count} 条结果，Tavily数据覆盖有限。"
                "已启用智能降级(扩展时间窗)，建议查阅公司官网或交易所"
                "公告获取最新信息。"
            )
        elif not has_published_date:
            summary = (
                f"[网络情报 - {stock_name} (最近{days_window}天)]\\n"
                f"找到 {result_count} 条相关结果。\\n[!] 警告: "
                "Tavily未返回发布日期，时效性需人工验证。"
            )
        else:
            # 显示结果来源分布
            source_counts = {}
            for r in final_results:
                qs = r.get("query_source", "unknown")
                source_counts[qs] = source_counts.get(qs, 0) + 1
            source_info = ", ".join(
                [f"{k}:{v}" for k, v in source_counts.items()]
            )

            # 显示主题分组
            topic_summary = []
            for topic, items in topic_groups.items():
                if items:
                    topic_summary.append(f'{topic}({len(items)})')
            topic_info = " | ".join(topic_summary) if topic_summary else "无分组"

            summary = (
                f"【网络情报 - {stock_name} (最近{days_window}天)】\n"
                f"找到 {result_count} 条相关结果 ({source_info})，"
                f"主题分布: {topic_info}，已展示质量最高的 "
                f"{min(5, result_count)} 条。"
            )

        print(
            f"[SEARCH] Final results: {result_count} "
            f"(from {len(all_results)} total)"
        )
        if result_count > 0:
            print(f"[SEARCH] Topic breakdown: {topic_info}")

        return {
            "symbol": symbol,
            "stock_name": stock_name,
            "query": " + ".join(search_queries),
            "results": final_results,
            "summary": summary,
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "search_queries_used": ["最新消息", "研报评级", "业绩预告", "重大事项", "公司公告"],
            "total_fetched": len(all_results),
            "has_published_date": has_published_date,
            "topic_groups": topic_groups,
            "days_window_used": days_window,
            "quality_threshold_used": quality_threshold
        }

    except Exception as e:
        print(f"[SEARCH] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "symbol": symbol,
            "stock_name": stock_name,
            "error": str(e),
            "results": [],
            "summary": f"【网络搜索异常】{str(e)}",
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "search_queries_used": ["最新消息", "研报评级", "业绩预告", "重大事项", "公司公告"],
            "total_fetched": 0,
            "has_published_date": False,
            "topic_groups": {},
            "days_window_used": 7,
            "quality_threshold_used": 0.4
        }


# ============================================
# 公司信息搜索
# ============================================

async def search_company_info(symbol: str, stock_name: str) -> Dict:
    """
    搜索公司基本信息、业务描述（作为 Tushare 的补充）

    Args:
        symbol: 股票代码
        stock_name: 股票名称

    Returns:
        {
            "company_info": str,
            "main_business": str,
            "industry_info": str
        }
    """
    client = _get_tavily_client()
    if not client:
        return {
            "company_info": "【网络搜索未启用】请设置 TAVILY_API_KEY 环境变量",
            "main_business": "",
            "industry_info": ""
        }

    # 预处理查询
    processed_query = _preprocess_query(symbol, stock_name, "company")

    print(f"[SEARCH] Tavily searching company: {processed_query}")

    try:
        response = client.search(
            query=processed_query,
            search_depth="basic",  # 公司信息用基础搜索即可
            max_results=3,
            days=30  # 公司信息相对稳定，可以查更长时间窗
        )

        if not response or "results" not in response:
            print(
                "[SEARCH] WARNING: Tavily returned invalid company "
                "info response"
            )
            return {
                "company_info": "【网络搜索异常】Tavily返回了无效响应",
                "main_business": "",
                "industry_info": ""
            }

        # 解析结果
        main_business_parts = []
        industry_info_parts = []

        for result in response.get("results", []):
            title = result.get("title", "")
            content = result.get("content", "")

            # 分类提取
            if any(kw in title for kw in ["主营", "业务", "产品"]):
                main_business_parts.append(f"{title}: {content}")
            elif any(kw in title for kw in ["行业", "板块", "所属"]):
                industry_info_parts.append(f"{title}: {content}")

        # 构建返回结果
        if main_business_parts or industry_info_parts:
            company_info = (
                "\n".join(main_business_parts) if main_business_parts
                else "未找到公司主营业务信息"
            )
            industry_info = (
                "\n".join(industry_info_parts) if industry_info_parts
                else "未找到行业信息"
            )
        else:
            company_info = "未找到公司主营业务信息"
            industry_info = "未找到行业信息"

        results_count = len(response.get('results', []))
        print(f"[SEARCH] Tavily found {results_count} company info results")

        return {
            "company_info": f"{company_info}\n{industry_info}",
            "main_business": company_info,
            "industry_info": industry_info
        }

    except Exception as e:
        print(f"[SEARCH] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "company_info": f"【网络搜索异常】{str(e)}",
            "main_business": "",
            "industry_info": ""
        }


# ============================================
# 格式化搜索结果为 LLM 上下文
# ============================================

def format_search_context_for_llm(search_result: Dict, stock_name: str) -> str:
    """
    将搜索结果格式化为 LLM 可读的上下文 (增强版 - 支持主题分组)

    Args:
        search_result: search_financial_news 的返回值
        stock_name: 股票名称

    Returns:
        格式化的文本上下文
    """
    if not search_result or search_result.get("error"):
        return "\n【网络情报】网络搜索不可用，依赖已有数据。\n"

    results = search_result.get("results", [])
    if not results:
        default_msg = f'未找到 {stock_name} 的最新新闻。'
        summary = search_result.get('summary', default_msg)
        return f"\n【网络情报】{summary}\n"

    # 按质量分数排序
    sorted_results = sorted(
        results,
        key=lambda x: x.get("score", 0),
        reverse=True
    )

    # 构建上下文（按质量降序）
    context = f"\n【网络情报 - {stock_name} 最新动态】\n"
    context += f"搜索时间: {search_result.get('search_time', '')}\n"

    # 显示查询策略统计
    queries_used = search_result.get("search_queries_used", [])
    if queries_used:
        context += f"查询策略: {', '.join(queries_used)} (5路并行)\n"
    total_fetched = search_result.get("total_fetched", len(results))
    context += f"召回统计: 共检索 {total_fetched} 条，去重后保留 {len(results)} 条\n"

    # 显示智能降级信息
    days_window = search_result.get("days_window_used", 7)
    if days_window > 7:
        context += f"[!] 智能降级: 时间窗扩展至 {days_window} 天\\n"
    quality_threshold = search_result.get("quality_threshold_used", 0.4)
    context += f"质量阈值: {quality_threshold}\n"

    has_date = search_result.get("has_published_date", True)
    if not has_date:
        context += "[!] 警告: Tavily未返回发布日期，时效性需人工验证\\n"

    context += "=" * 50 + "\n"

    # 按主题分组展示
    topic_groups = search_result.get("topic_groups", {})
    if topic_groups and any(topic_groups.values()):
        context += "【主题分组】\n"
        for topic, items in topic_groups.items():
            if items:
                context += f"  [Topic] {topic}: {len(items)} 条\\n"
                # 每个主题最多显示2条
                for item in items[:2]:
                    context += f"     • {item.get('title', '')[:50]}\n"
        context += "\n"

    # 逐条展示新闻（只显示前5条高质量结果）
    context += "\n【详细结果】\n"
    for i, result in enumerate(sorted_results[:5], 1):
        title = result.get("title", "")
        score = result.get("score", 0)
        date_str = result.get("published_date", "")
        query_source = result.get("query_source", "")
        priority_boost = result.get("priority_boost", 0)
        is_realtime = not result.get("is_realtime", True)

        # 标记非实时信息
        realtime_label = "" if is_realtime else " [历史]"

        # 来源标签和优先级标记
        source_label = f"[{query_source}]" if query_source else ""
        if priority_boost and priority_boost >= 0.8:
            priority_label = "🔼"
        elif priority_boost and priority_boost >= 0.6:
            priority_label = "📊"
        else:
            priority_label = ""

        context += f"{i}. 【{title}】{source_label}{realtime_label}\n"
        context += f"   来源: {result.get('url', '')}\n"
        context += f"   发布时间: {date_str if date_str else '未知'}\n"
        context += f"   内容质量: {score:.2f}/1.0 {priority_label}\n"
        context += "-" * 40 + "\n"

        # 如果有更多结果，添加提示
        if i == 4 and len(sorted_results) > 5:
            context += (
                f"   (还有 {len(sorted_results) - 5} 条结果已过滤，"
                "可通过扩大时间窗查看)"
            )

        context += (
            "=[!] 风险提示[!]\\n以上信息来自网络搜索，"
            "请结合公司官方披露信息综合判断。"
            "部分内容可能存在时效性滞后或准确性问题，"
            "建议查阅公司最新公告。\\n"
        )

    # 返回结构化数据（JSON 格式）供 IC 投委会处理
    structured_data = {
        "tavily_data": {
            "results": results,
            "total_fetched": search_result.get(
                "total_fetched", len(results)
            ),
            "search_time": search_result.get("search_time", ""),
            "quality_threshold": search_result.get(
                "quality_threshold_used", 0.4
            ),
            "summary": search_result.get("summary", "")
        }
    }
    import json
    return json.dumps(structured_data, ensure_ascii=False)


# ============================================
# 主函数 - 同步版本
# ============================================


async def search_financial_news_sync(
    symbol: str,
    stock_name: str,
    max_results: int = 5
) -> Dict:
    """同步版本的财经新闻搜索"""
    return await asyncio.run(
        search_financial_news(symbol, stock_name, max_results)
    )


async def search_company_info_sync(symbol: str, stock_name: str) -> Dict:
    """同步版本的公司信息搜索"""
    return await asyncio.run(search_company_info(symbol, stock_name))


# ============================================
# 主函数 - 用于非异步环境
# ============================================

if __name__ == "__main__":
    # 测试代码
    # result = asyncio.run(search_financial_news("688008", "澜起科技", 5))
    # print(format_search_context_for_llm(result, "澜起科技"))
    # 测试公司搜索
    # result = asyncio.run(search_company_info("688008", "澜起科技"))

    print("[SEARCH] Search service starting...")
    print("[SEARCH] Current configuration:")
    print(f"[SEARCH]   - Max results per query: {5}")
    print("[SEARCH]   - Time window: 7 days")
    print("[SEARCH]   - Content de-noising: ENABLED")
    print("[SEARCH]   - Advanced search: ENABLED")
    print("[SEARCH]   - Raw content: DISABLED")
    print("[SEARCH]   - Result layering: ENABLED")
    print("[SEARCH]   - Date normalization: ENABLED")
