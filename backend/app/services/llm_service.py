# -*- coding: utf-8 -*-
"""
LLM Service - AI-Powered Report Summarization & Chat
使用阿里云通义千问 (Qwen) 生成研报摘要和对话功能
"""

import json
import os
from typing import Dict, List, Optional

import dashscope
from supabase import Client

from app.core.config import settings
from app.core.db import get_db_client


# 本地分类映射（当 AI 失败时使用）
_SECTOR_INDUSTRY_MAPPING = {
    # A 股分类
    "消费品": {"白酒": "消费品", "家电": "消费品", "食品": "消费品", "纺织": "消费品"},
    "金融": {"银行": "金融", "保险": "金融", "证券": "金融", "信托": "金融"},
    "科技": {"安防": "科技", "软件": "科技", "互联网": "科技", "半导体": "科技", "通信": "科技"},
    "新能源": {"锂电池": "新能源", "新能源汽车": "新能源", "光伏": "新能源", "风电": "新能源"},
    "医疗健康": {"化学制药": "医疗健康", "生物制药": "医疗健康", "医疗器械": "医疗健康", "中药": "医疗健康"},
    "公用事业": {"电力": "公用事业", "水务": "公用事业", "燃气": "公用事业"},

    # 美股分类
    "科技": {"Technology": "科技", "Software": "科技", "Semiconductor": "科技", "Internet": "科技",
             "Social Media": "科技", "Streaming": "科技", "Automotive": "科技"},
    "金融": {"Banking": "金融", "Payment": "金融", "Insurance": "金融"},
    "消费品": {"E-Commerce": "消费品", "Retail": "消费品", "Entertainment": "消费品"},
    "医疗健康": {"Pharma": "医疗健康", "Biotech": "医疗健康", "Healthcare": "医疗健康"},
}


def _get_local_classification(sector_en: str, industry_en: str) -> dict:
    """从本地映射获取分类"""
    sector_en_lower = sector_en.lower() if sector_en else ""
    industry_en_lower = industry_en.lower() if industry_en else ""

    # 直接匹配行业
    for sector_cn, industries in _SECTOR_INDUSTRY_MAPPING.items():
        for industry_en_key, industry_cn in industries.items():
            if industry_en_key.lower() in industry_en_lower or industry_en_key.lower() in sector_en_lower:
                return {"sector_cn": sector_cn, "industry_cn": industry_cn}

    # 模糊匹配板块
    for sector_cn, industries in _SECTOR_INDUSTRY_MAPPING.items():
        if sector_cn.lower() in sector_en_lower or sector_cn.lower() in industry_en_lower:
            # 找该板块下的第一个行业
            return {"sector_cn": sector_cn, "industry_cn": list(industries.values())[0]}

    return {"sector_cn": "其他", "industry_cn": "其他"}


def generate_summary(report_id: str) -> str | None:
    """为报告生成 AI 摘要"""
    db: Client = get_db_client()

    try:
        # 获取报告文本块
        chunks_result = (
            db.table("report_chunks")
            .select("content")
            .eq("report_id", report_id)
            .order("page_number")
            .execute()
        )

        if not chunks_result.data:
            print(f"[ERROR] No chunks found for report {report_id}")
            return None

        # 拼接文本，限制在 6000 字符以内
        full_text = "\n\n".join([chunk["content"] for chunk in chunks_result.data])
        text_to_analyze = full_text[:6000]

        print(f"[OK] Analyzing {len(text_to_analyze)} characters from {len(chunks_result.data)} chunks")

        # 调用通义千问 API
        api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            print("[ERROR] DASHSCOPE_API_KEY not found")
            return None

        messages = [
            {
                "role": "system",
                "content": "你是一位资深的金融分析师，擅长分析研报并提取核心观点。请用简洁的语言总结报告的主要内容，包括：1) 核心观点 2) 关键数据 3) 投资建议。输出控制在200字以内。"
            },
            {
                "role": "user",
                "content": f"请分析以下研报内容：\n\n{text_to_analyze}"
            },
        ]

        response = dashscope.Generation.call(
            model="qwen-plus",
            messages=messages,
            api_key=api_key,
        )

        if response.status_code != 200:
            print(f"[ERROR] Qwen API Error: {response.code} - {response.message}")
            return None

        summary = response.output.text
        print(f"[OK] Generated summary: {summary[:50]}...")

        # 更新数据库
        db.table("reports").update({"summary": summary}).eq("id", report_id).execute()
        print(f"[OK] Summary saved to report {report_id}")
        return summary

    except Exception as e:
        print(f"[ERROR] Error generating summary: {e}")
        return None


def create_embedding(text: str) -> List[float] | None:
    """使用阿里云 text-embedding-v1 模型生成文本向量嵌入"""
    api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        print("[ERROR] DASHSCOPE_API_KEY not found")
        return None

    try:
        response = dashscope.TextEmbedding.call(
            model="text-embedding-v1",
            input=text,
            api_key=api_key,
        )

        if response.status_code != 200:
            print(f"[ERROR] Embedding API Error: {response.code} - {response.message}")
            return None

        # 提取 embedding
        output = response.output
        embedding = None

        if isinstance(output, dict):
            embeddings = output.get('embeddings', [])
            if embeddings and len(embeddings) > 0:
                first = embeddings[0]
                if isinstance(first, dict):
                    embedding = first.get('embedding')
                else:
                    embedding = first
        elif hasattr(output, 'embeddings'):
            embeddings_list = output.embeddings
            if embeddings_list and len(embeddings_list) > 0:
                embedding = embeddings_list[0].embedding
        elif hasattr(output, 'embedding'):
            embedding = output.embedding

        if embedding:
            print(f"[OK] Generated embedding for {len(text)} characters, dim: {len(embedding)}")
            return embedding

        print(f"[ERROR] Failed to extract embedding from response")
        return None

    except Exception as e:
        print(f"[ERROR] Error creating embedding: {e}")
        return None


def generate_chat_response(
    report_id: str,
    query: str,
    match_threshold: float = 0.1,
    match_count: int = 5
) -> str | None:
    """
    使用 RAG (Retrieval Augmented Generation) 生成回答

    流程:
    1. 将用户问题转换为向量
    2. 在数据库中搜索相似的文本块
    3. 将找到的文本块作为上下文
    4. 使用 Qwen 生成回答
    """
    db: Client = get_db_client()

    try:
        # 为用户问题生成向量
        query_embedding = create_embedding(query)
        if not query_embedding:
            return None

        # 向量搜索获取相关上下文
        print(f"[DEBUG] Calling match_documents with threshold={match_threshold}, count={match_count}")
        match_result = db.rpc(
            "match_documents",
            params={
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count,
                "filter_report_id": report_id,
            }
        ).execute()

        if not match_result.data:
            context = "未找到与问题相关的内容。"
        else:
            context_parts = []
            for chunk in match_result.data:
                context_parts.append(f"[Page {chunk['page_number']}] {chunk['content']}")
            context = "\n\n".join(context_parts)
            print(f"[OK] Retrieved {len(match_result.data)} relevant chunks")

        # 使用 Qwen 生成回答
        api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            print("[ERROR] DASHSCOPE_API_KEY not found")
            return None

        messages = [
            {
                "role": "system",
                "content": "你是一位资深的金融分析师助手。请基于提供的研报内容回答用户的问题。如果提供的上下文中没有相关信息，请明确告知。回答要准确、专业、简洁。"
            },
            {
                "role": "user",
                "content": f"基于以下研报内容，请回答问题：\n\n【研报内容】\n{context}\n\n【问题】\n{query}"
            }
        ]

        response = dashscope.Generation.call(
            model="qwen-plus",
            messages=messages,
            api_key=api_key,
        )

        if response.status_code != 200:
            print(f"[ERROR] Qwen API Error: {response.code} - {response.message}")
            return None

        answer = response.output.text
        print(f"[OK] Generated chat response: {answer[:50]}...")
        return answer

    except Exception as e:
        print(f"[ERROR] Error generating chat response: {e}")
        import traceback
        traceback.print_exc()
        return None


def classify_stock(symbol: str, name: str, sector_en: str, industry_en: str) -> dict:
    """
    使用 AI 將股票分類為中文板块和行业

    Returns:
        {"sector_cn": "板块名稱", "industry_cn": "行业名稱"}
    """
    print(f"[DEBUG] classify_stock called: symbol={symbol}, sector_en={sector_en}, industry_en={industry_en}")

    api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")

    # 1. 先尝试本地映射（快速且可靠）
    local_result = _get_local_classification(sector_en, industry_en)
    print(f"[DEBUG] Local classification result: {local_result}")
    if local_result["sector_cn"] != "其他":
        print(f"[OK] Local classification for {symbol}: {local_result['sector_cn']} / {local_result['industry_cn']}")
        return local_result

    # 2. 本地映射失败，尝试 AI 分类
    if not api_key:
        print("[WARN] DASHSCOPE_API_KEY not found, using local fallback")
        return local_result

    try:
        messages = [
            {
                "role": "system",
                "content": """你是一位資深的金融分析師，擅長將股票分類到中文的板块和行业。
請根據公司的英文名稱、sector 和 industry，將其分類到最合適的中文板块和行业。

常見的中文板块包括：半導體、新能源、醫療健康、消費品、金融、科技、工業、房地產、公用事業、能源、通信、材料、其他

請以 JSON 格式返回：{"sector_cn": "板块名稱", "industry_cn": "行业名稱"}"""
            },
            {
                "role": "user",
                "content": f"""請將以下股票分類到中文的板块和行业：

股票代碼：{symbol}
公司名稱：{name}
英文 Sector：{sector_en}
英文 Industry：{industry_en}

請返回 JSON 格式：{{"sector_cn": "...", "industry_cn": "..."}}"""
            }
        ]

        response = dashscope.Generation.call(
            model="qwen-plus",
            messages=messages,
            api_key=api_key,
            result_format="message",
        )

        if response.status_code != 200:
            print(f"[WARN] Qwen API Error: {response.code} - {response.message}, using local fallback")
            return local_result

        # 解析 JSON 響應
        if response.output is None or response.output.text is None:
            print(f"[WARN] Qwen API returned None output, using local fallback")
            return local_result

        result_text = response.output.text.strip()

        # 嘗試提取 JSON（處理可能的 markdown 代碼塊）
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)
        sector_cn = result.get("sector_cn", "其他")
        industry_cn = result.get("industry_cn", "其他")

        print(f"[OK] AI Classified {symbol}: {sector_cn} / {industry_cn}")
        return {"sector_cn": sector_cn, "industry_cn": industry_cn}

    except Exception as e:
        print(f"[WARN] Error classifying stock {symbol}: {e}, using local fallback")
        import traceback
        traceback.print_exc()
        return local_result


def generate_portfolio_review(
    symbol: str,
    name: str,
    sector: str,
    start_price: float,
    end_price: float,
    price_change_pct: float,
    period_days: int = 7,
    technical_data: Optional[Dict] = None
) -> Dict:
    """
    生成股票週度復盤分析（返回结构化JSON数据）

    Args:
        technical_data: 技术分析数据，包含 ma20_status, volume_status, health_score 等

    Returns:
        {
            "health_score": 0-100,
            "action_signal": "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL",
            "analysis": "分析文本",
            "quote": "投资名言"
        }
    """
    api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")

    direction = "上漲" if price_change_pct > 0 else "下跌"

    # 计算基础健康分
    base_health_score = 50

    # 价格趋势影响 (+/- 30)
    if price_change_pct > 5:
        base_health_score += 30
    elif price_change_pct > 0:
        base_health_score += 15
    elif price_change_pct < -5:
        base_health_score -= 30
    else:
        base_health_score -= 15

    # 整合技术面数据
    if technical_data:
        # MA20状态 (+/- 20)
        if technical_data.get("ma20_status") == "站上均线":
            base_health_score += 20
        elif technical_data.get("ma20_status") == "跌破均线":
            base_health_score -= 20

        # 量能状态 (+/- 10)
        if technical_data.get("volume_status") == "放量":
            base_health_score += 10
        elif technical_data.get("volume_status") == "缩量":
            base_health_score -= 10

        # 使用技术面计算的health_score
        base_health_score = (base_health_score + technical_data.get("health_score", 50)) / 2

    # 限制在 0-100
    health_score = max(0, min(100, int(base_health_score)))

    # 确定信号
    if health_score >= 80:
        action_signal = "STRONG_BUY"
    elif health_score >= 60:
        action_signal = "BUY"
    elif health_score >= 40:
        action_signal = "HOLD"
    elif health_score >= 20:
        action_signal = "SELL"
    else:
        action_signal = "STRONG_SELL"


    # 生成AI分析（如果API可用）
    ai_analysis = None
    if not api_key:
        print("[WARN] DASHSCOPE_API_KEY not found, using template")

        # 使用模板生成分析
        ma_status = technical_data.get("ma20_status", "中性") if technical_data else "中性"
        vol_status = technical_data.get("volume_status", "持平") if technical_data else "持平"

        templates = {
            "STRONG_BUY": f"{name}週度{direction}{'强势' if price_change_pct > 0 else ''}，{ma_status}且{vol_status}，技術面健康。建議積極配置。",
            "BUY": f"{name}週度{direction}，{ma_status}，整體走勢良好。可適度加倉。",
            "HOLD": f"{name}週度小幅震盪，{vol_status}，觀望為主。",
            "SELL": f"{name}週度{direction}，{ma_status}，量能不濟。建議減倉。",
            "STRONG_SELL": f"{name}週度{'大幅' if abs(price_change_pct) > 5 else ''}{direction}，技術面轉弱。建議止損。"
        }

        ai_analysis = templates.get(action_signal, f"{name}({symbol}) 過去 {period_days} 天{direction} {abs(price_change_pct):.2f}%。")

    else:
        try:
            # 构建技术面上下文
            tech_context = ""
            if technical_data:
                tech_context = f"""
技术指标：
- MA20状态：{technical_data.get('ma20_status', 'N/A')}
- MA5状态：{technical_data.get('ma5_status', 'N/A')}
- 量能状态：{technical_data.get('volume_status', 'N/A')}
- 健康评分：{technical_data.get('health_score', 'N/A')}/100
- Alpha收益：{technical_data.get('alpha', 0):.2f}%
- K线形态：{technical_data.get('k_line_pattern', 'N/A')}
- 形态信号：{technical_data.get('pattern_signal', 'N/A')}
"""

            messages = [
                {
                    "role": "system",
                    "content": """你是一个严格的量化基金经理。请重点分析K线形态的含义。

K线形态解读指南：
- 金针探底：下影线长，底部支撑强劲，可能反转向上
- 冲高回落：上影线长，顶部压力明显，注意回调风险
- 变盘十字星：实体极小，方向不明，密切关注后续走势
- 光头大阳线：强势上涨，多方力量充足
- 光脚大阴线：强势下跌，空方力量主导
- 普通震荡：无明显形态，常规波动

请根据以下信息，输出纯 JSON 格式：
1. 股票基本信息（代码、名称、板块、价格变化）
2. K线形态分析（重点解读当前形态的含义）
3. 给出 0-100 的健康分
4. 给出交易信号（STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL）
5. 用一句话总结分析（不超过50字，必须包含K线形态解读）

输出格式（纯 JSON）：
{
  "health_score": 85,
  "action_signal": "BUY",
  "analysis": "出现金针探底，底部支撑强劲，建议关注反弹机会。"
}
"""
                },
                {
                    "role": "user",
                    "content": f"""请分析以下股票：

股票代码：{symbol}
公司名称：{name}
所属板块：{sector}
期初价格：{start_price:.2f}
期末价格：{end_price:.2f}
涨跌幅：{price_change_pct:.2f}%（{direction}）
统计周期：{period_days} 天
{tech_context}

请返回纯 JSON 格式。"""
                }
            ]

            response = dashscope.Generation.call(
                model="qwen-plus",
                messages=messages,
                api_key=api_key,
            )

            if response.status_code != 200:
                print(f"[WARN] Qwen API Error: {response.code} - {response.message}, using fallback")
                ai_analysis = None
            else:
                result_text = response.output.text.strip()

                # 提取JSON
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                import json as json_module
                try:
                    ai_result = json_module.loads(result_text)

                    # 更新健康分和信号
                    if "health_score" in ai_result:
                        health_score = ai_result["health_score"]

                    if "action_signal" in ai_result:
                        valid_signals = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
                        if ai_result["action_signal"] in valid_signals:
                            action_signal = ai_result["action_signal"]

                    ai_analysis = ai_result.get("analysis", "")
                    print(f"[OK] AI Analysis for {symbol}: {action_signal}, Score={health_score}")

                except json_module.JSONDecodeError:
                    print(f"[WARN] Failed to parse AI response, using template")
                    ai_analysis = None

        except Exception as e:
            print(f"[WARN] AI analysis failed: {e}, using template")
            ai_analysis = None

    # 如果没有AI分析，使用模板
    if not ai_analysis:
        ma_status = technical_data.get("ma20_status", "中性") if technical_data else "中性"
        vol_status = technical_data.get("volume_status", "持平") if technical_data else "持平"
        k_pattern = technical_data.get("k_line_pattern", "普通震荡") if technical_data else "普通震荡"

        # K线形态解读
        pattern_meanings = {
            "金针探底": "底部支撑强劲，关注反弹",
            "冲高回落": "顶部压力明显，注意回调",
            "变盘十字星": "方向不明，密切关注",
            "光头大阳线": "强势上涨，多方充足",
            "光脚大阴线": "强势下跌，空方主导",
            "普通震荡": "常规波动，持续观察"
        }
        pattern_desc = pattern_meanings.get(k_pattern, "常规波动")

        templates = {
            "STRONG_BUY": f"{name}週度{direction}{'强势' if price_change_pct > 0 else ''}，出现{k_pattern}（{pattern_desc}），{ma_status}且{vol_status}。强烈买入。",
            "BUY": f"{name}週度{direction}，{k_pattern}（{pattern_desc}），{ma_status}，整體走勢良好。适量买入。",
            "HOLD": f"{name}週度震盪整理，{k_pattern}（{pattern_desc}），{vol_status}。建議持有觀望。",
            "SELL": f"{name}週度{direction}，{k_pattern}（{pattern_desc}），{ma_status}，量能偏弱。建議減倉。",
            "STRONG_SELL": f"{name}週度{'大幅' if abs(price_change_pct) > 5 else ''}{direction}，{k_pattern}（{pattern_desc}），技術面轉弱。建議止損賣出。"
        }

        ai_analysis = templates.get(action_signal, f"{name}({symbol}) 過去 {period_days} 天{direction} {abs(price_change_pct):.2f}%，{k_pattern}。")

    return {
        "health_score": health_score,
        "action_signal": action_signal,
        "analysis": ai_analysis
    }
