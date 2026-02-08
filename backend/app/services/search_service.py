# -*- coding: utf-8 -*-
"""
Search Service - 实时网络检索服务
使用 Tavily Search API 获取最新新闻、研报和市场情报，解决 AI 幻觉问题
"""
import os
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta

_tavily_client = None


def _get_tavily_client():
    """获取或创建 Tavily 客户端"""
    global _tavily_client
    if _tavily_client is None:
        try:
            from tavily import TavilyClient

            # 确保加载.env文件
            from dotenv import load_dotenv
            load_dotenv()

            api_key = os.getenv("TAVILY_API_KEY")

            # 详细日志
            if not api_key:
                print("[SEARCH] ERROR: TAVILY_API_KEY not found in environment")
                return None

            print(f"[SEARCH] Tavily API Key found (length: {len(api_key)}, prefix: {api_key[:10]}...)")

            # 验证API key格式
            if not api_key.startswith('tvly-'):
                print(f"[SEARCH] WARNING: API key format may be invalid (should start with 'tvly-')")

            _tavily_client = TavilyClient(api_key=api_key)
            print("[SEARCH] Tavily Search client initialized successfully")

        except ImportError:
            print("[SEARCH] ERROR: tavily-python not installed. Run: pip install tavily-python")
        except Exception as e:
            print(f"[SEARCH] ERROR: Failed to init Tavily client: {e}")
            _tavily_client = None

    return _tavily_client


async def search_financial_news(symbol: str, stock_name: str, max_results: int = 5) -> Dict:
    """
    搜索最新的财经新闻、研报和市场情报

    Args:
        symbol: 股票代码 (如 "688008")
        stock_name: 股票名称 (如 "澜起科技")
        max_results: 最大返回结果数

    Returns:
        {
            "symbol": str,
            "stock_name": str,
            "query": str,
            "results": [
                {
                    "title": str,
                    "url": str,
                    "content": str,
                    "score": float,
                    "published_date": str
                }
            ],
            "summary": str,  # LLM 可读的摘要
            "search_time": str
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
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    try:
        # 构造高信噪比的搜索词
        # 搜索策略：搜最新的研报观点、业绩预告、突发利空
        query = f"{stock_name} {symbol} 股票 最新 研报 业绩 利好 利空"

        print(f"[SEARCH] Tavily searching: {query}")

        # 执行搜索
        response = client.search(
            query=query,
            search_depth="advanced",  # 深度搜索
            max_results=max_results,
            include_domains=[
                "eastmoney.com",  # 东方财富
                "xueqiu.com",       # 雪球
                "sina.com.cn",      # 新浪财经
                "jiemian.com",      # 界面新闻
                "10jqka.com.cn",    # 同花顺
                "cs.com.cn"         # 中证网
            ],
            days=7,  # 只搜索最近7天的内容
            include_answer=False,
            include_raw_content=False
        )

        # 检查响应是否有效
        if not response or "results" not in response:
            print("[SEARCH] WARNING: Tavily returned invalid response")
            return {
                "symbol": symbol,
                "stock_name": stock_name,
                "error": "Invalid Tavily response",
                "results": [],
                "summary": "【网络搜索异常】Tavily返回了无效响应",
                "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # 解析结果
        results = []
        context_parts = []

        for result in response.get("results", []):
            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")
            score = result.get("score", 0)

            # 截取内容（省 token）
            if content and len(content) > 500:
                content = content[:500] + "..."

            results.append({
                "title": title,
                "url": url,
                "content": content,
                "score": score,
                "published_date": ""  # Tavily 可能不返回日期
            })

            # 构建上下文
            if title and content:
                context_parts.append(f"• 【{title}】\n  {content}\n  来源: {url}")

        # 生成摘要
        summary = "\n\n".join(context_parts) if context_parts else "未找到相关新闻"

        print(f"[OK] Tavily found {len(results)} results")

        return {
            "symbol": symbol,
            "stock_name": stock_name,
            "query": query,
            "results": results,
            "summary": summary,
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        print(f"[ERROR] Tavily search failed: {e}")
        return {
            "symbol": symbol,
            "stock_name": stock_name,
            "error": str(e),
            "results": [],
            "summary": f"【网络搜索失败】{str(e)}"
        }


async def search_company_info(symbol: str, stock_name: str) -> Dict:
    """
    搜索公司基本信息、业务描述（作为 Tushare 的补充）

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
            "company_info": "【网络搜索未启用】",
            "main_business": "",
            "industry_info": ""
        }

    try:
        query = f"{stock_name} {symbol} 主营业务 行业 简介 公司资料"

        print(f"[SEARCH] Tavily searching company info: {query}")

        response = client.search(
            query=query,
            search_depth="basic",  # 基础搜索即可
            max_results=3,
            days=30  # 公司信息相对稳定，可以查久一点的
        )

        company_info_parts = []
        main_business_parts = []
        industry_info_parts = []

        for result in response.get("results", []):
            title = result.get("title", "")
            content = result.get("content", "")

            if content:
                if len(content) > 300:
                    content = content[:300] + "..."

                company_info_parts.append(f"【{title}】{content}")

                # 简单分类
                if any(kw in title for kw in ["主营", "业务", "产品"]):
                    main_business_parts.append(f"{title}: {content}")
                if any(kw in title for kw in ["行业", "板块", "所属"]):
                    industry_info_parts.append(f"{title}: {content}")

        return {
            "company_info": "\n\n".join(company_info_parts) if company_info_parts else "未找到公司信息",
            "main_business": "\n\n".join(main_business_parts) if main_business_parts else "",
            "industry_info": "\n\n".join(industry_info_parts) if industry_info_parts else ""
        }

    except Exception as e:
        print(f"[ERROR] Tavily company search failed: {e}")
        return {
            "company_info": f"【搜索失败】{str(e)}",
            "main_business": "",
            "industry_info": ""
        }


def format_search_context_for_llm(search_result: Dict, stock_name: str) -> str:
    """
    将搜索结果格式化为 LLM 可读的上下文

    Args:
        search_result: search_financial_news 的返回值
        stock_name: 股票名称

    Returns:
        格式化的文本上下文
    """
    if not search_result or search_result.get("error"):
        return f"\n【网络情报】网络搜索不可用，依赖已有数据。\n"

    results = search_result.get("results", [])
    if not results:
        return f"\n【网络情报】未找到 {stock_name} 的最新新闻。\n"

    context = f"\n【网络情报 - {stock_name} 最新动态】\n"
    context += f"搜索时间: {search_result.get('search_time', '')}\n"

    # 按相关性排序并展示
    sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    for i, result in enumerate(sorted_results[:5], 1):
        title = result.get("title", "")
        content = result.get("content", "")
        url = result.get("url", "")

        context += f"\n{i}. 【{title}】\n"
        context += f"   摘要: {content}\n"
        context += f"   来源: {url}\n"

    context += "\n【风险提示】以上信息来自网络搜索，请结合官方披露信息综合判断。\n"

    return context


# 同步版本（用于非异步环境）
def search_financial_news_sync(symbol: str, stock_name: str, max_results: int = 5) -> Dict:
    """同步版本的搜索函数"""
    return asyncio.run(search_financial_news(symbol, stock_name, max_results))


def search_company_info_sync(symbol: str, stock_name: str) -> Dict:
    """同步版本的公司信息搜索"""
    return asyncio.run(search_company_info(symbol, stock_name))


if __name__ == "__main__":
    # 测试代码
    import os
    if not os.getenv("TAVILY_API_KEY"):
        print("请设置 TAVILY_API_KEY 环境变量")
    else:
        result = asyncio.run(search_financial_news("688008", "澜起科技"))
        print(format_search_context_for_llm(result, "澜起科技"))
