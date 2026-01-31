# -*- coding: utf-8 -*-
"""
Committee Service - 全脑协同投资决策系统

基于各模型原生特长的任务分配：
- Qwen (右脑): 情绪与题材叙事
- DeepSeek (左脑): 估值与逻辑风控
- Zhipu (皮层): 综合决策
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict

from app.core.llm_factory import LLMFactory
from app.services.market_service import get_market_snapshot, get_stock_technical_analysis, get_news_titles


# ============================================
# 模型任务提示词 (基于原生特长设计)
# ============================================

# Qwen: 感性脑 - 市场情绪与题材叙事分析
# 利用其对中文语境、热门概念、行业赛道的敏锐感知
QWEN_SENTIMENT_PROMPT = """
你负责【市场情绪与题材叙事分析】。
你的优势在于对中文语境、热门概念、行业赛道的敏锐感知。

【分析维度】
1. **题材含金量**：新闻里的概念（如AI、出海、重组、国产替代）是当前市场的风口吗？
2. **情绪溢价**：Sentinel分数和量能是否反映出资金的兴奋度？
3. **想象空间**：脱离枯燥的财报，这家公司的未来愿景是否有吸引力？

【输出要求】
- 就像一个嗅觉灵敏的游资在分析"风口"。
- 给出【情绪评分 (0-100)】。
- 150字以内，直接输出分析文本。
"""

# DeepSeek: 理性脑 - 基本面审计与逻辑风控
# 利用其严密的逻辑推理和对数据的客观判断
DEEPSEEK_LOGIC_PROMPT = """
你负责【基本面审计与逻辑风控】。
你的优势在于严密的逻辑推理和对数据的客观判断。

【分析维度】
1. **估值安全边际**：当前的 ROE 能否支撑目前的 PE？价格是否严重透支？
2. **逻辑验证**：市场看到的热点题材，在财务报表上有体现吗？还是纯粹的空气？
3. **技术背离**：价格上涨时，量能和技术指标是否健康？有无诱多嫌疑？

【输出要求】
- 就像一个严谨的审计师在进行"压力测试"。
- 给出【安全评分 (0-100)】。
- 150字以内，直接输出分析文本。
"""

# Zhipu: 皮层 - 综合决策中枢
# 对比"理想"与"现实"，计算预期差
ZHIPU_DECISION_PROMPT = """
你是【首席投资官 CIO】。
你面前有两份报告：一份是关于"未来愿景"的(Qwen)，一份是关于"现实风险"的(DeepSeek)。

【决策模型：预期差理论】
1. **高胜率机会**：Qwen认为题材极好(情绪分高) + DeepSeek认为估值安全(安全分高) -> **重仓 (STRONG_BUY)**。
2. **投机机会**：Qwen认为题材极好 + DeepSeek认为估值太贵 -> **轻仓参与泡沫 (BUY/HOLD)**。
3. **价值陷阱**：Qwen认为没故事 + DeepSeek认为很便宜 -> **观望 (HOLD)**。
4. **垃圾时间**：Qwen认为没故事 + DeepSeek认为太贵 -> **清仓 (SELL)**。

【输出格式】
纯JSON（无```标记）：
{
    "sentiment_summary": "概括Qwen的观点",
    "risk_summary": "概括DeepSeek的观点",
    "final_decision": "STRONG_BUY / BUY / HOLD / SELL",
    "suggested_position": "0-100%",
    "reasoning": "一句话总结预期差"
}
"""


# ============================================
# 服务类
# ============================================

class CommitteeService:
    """全脑协同投资决策服务"""

    def __init__(self):
        self.llm = LLMFactory

    async def run_meeting(self, symbol: str) -> Dict:
        """
        运行全脑协同决策会议

        Returns: dict with symbol, timestamp, fundamentals, analysis, conclusion
        """
        print(f"[全脑协同] 正在调用不同模型的原生特长分析: {symbol}")

        # 1. 加载市场数据
        data = await self._load_data(symbol)
        if not data:
            return self._error(symbol, "无法获取市场数据")

        # 2. 构建通用上下文
        context = self._build_context(symbol, data)
        print(f"[市场数据] PE:{data['pe_ttm']} PB:{data['pb']} ROE:{data['roe']}% 健康:{data['health_score']}/100")

        # 3. 左右脑并行执行
        print("[左右脑并行] 千问看题材，DeepSeek算估值...")
        qwen_res, deepseek_res = await asyncio.gather(
            self.llm.fast_reply("qwen", QWEN_SENTIMENT_PROMPT, f"分析对象数据：\n{context}"),
            self.llm.fast_reply("deepseek", DEEPSEEK_LOGIC_PROMPT, f"审计对象数据：\n{context}")
        )
        print(f"[感性脑-Qwen] {qwen_res[:80]}...")
        print(f"[理性脑-DeepSeek] {deepseek_res[:80]}...")

        # 4. 皮层综合决策
        print("[最终整合] 智谱正在计算预期差...")
        zhipu_input = f"""
【市场数据】{context}
---
【感性脑 (Qwen)】{qwen_res}
【理性脑 (DeepSeek)】{deepseek_res}
"""
        judge_raw = await self.llm.fast_reply("zhipu", ZHIPU_DECISION_PROMPT, zhipu_input)
        conclusion = self._parse_judge(judge_raw)

        print(f"[最终决策] {conclusion['final_decision']} ({conclusion['reasoning']})")

        return {
            "symbol": symbol,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "fundamentals": {k: data[k] for k in [
                "pe_ttm", "pb", "total_mv", "turnover", "roe", "volume_ratio",
                "health_score", "action_signal"
            ]},
            "analysis": {
                "narrative_agent": {"model": "Qwen", "role": "感性脑", "content": qwen_res},
                "logic_agent": {"model": "DeepSeek", "role": "理性脑", "content": deepseek_res}
            },
            "conclusion": conclusion
        }

    async def _load_data(self, symbol: str) -> Dict:
        """加载市场数据"""
        snapshot = get_market_snapshot(symbol)
        if not snapshot:
            return None

        technical = get_stock_technical_analysis(symbol)
        fund = snapshot.get('fundamentals', {})

        # 获取新闻标题（舆情数据）
        news = get_news_titles(symbol, limit=5)

        return {
            "pe_ttm": fund.get('pe_ttm'),
            "pb": fund.get('pb'),
            "total_mv": fund.get('total_mv'),
            "turnover": fund.get('turnover'),
            "roe": fund.get('roe'),
            "volume_ratio": fund.get('volume_ratio'),
            "health_score": technical.get('health_score') if technical else None,
            "action_signal": technical.get('action_signal') if technical else None,
            "ma20_status": technical.get('ma20_status') if technical else None,
            "volume_status": technical.get('volume_status') if technical else None,
            "rsi_14": technical.get('rsi_14') if technical else None,
            "bollinger_upper": technical.get('bollinger_upper') if technical else None,
            "bollinger_lower": technical.get('bollinger_lower') if technical else None,
            "bandwidth": technical.get('bandwidth') if technical else None,
            "vwap_20": technical.get('vwap_20') if technical else None,
            "current_price": snapshot.get('current_price'),
            "price_change_pct": snapshot.get('price_change_pct', 0),
            "news": news
        }

    def _build_context(self, symbol: str, data: Dict) -> str:
        """构建通用上下文"""
        news_str = " | ".join(data.get('news', [])[:5])  # 最多5条新闻

        return f"""【标的】{symbol}
【现价】¥{data['current_price']} ({data['price_change_pct']:.2f}%)

=== 估值 ===
PE-TTM: {data['pe_ttm'] or 'N/A'}
PB: {data['pb'] or 'N/A'}
ROE: {data['roe'] or 'N/A'}%
市值: {data['total_mv'] or 'N/A'}亿

=== 流动性 ===
换手: {data['turnover'] or 'N/A'}%
量比: {data['volume_ratio'] or 'N/A'}

=== 技术 ===
健康分: {data['health_score'] or 'N/A'}/100
信号: {data['action_signal'] or 'N/A'}
MA20: {data['ma20_status'] or 'N/A'}
量价: {data['volume_status'] or 'N/A'}
RSI: {data['rsi_14'] or 'N/A'}
布林: {data['bollinger_upper'] or 'N/A'} / {data['bollinger_lower'] or 'N/A'}
VWAP: {data['vwap_20'] or 'N/A'}

=== 舆情 ===
{news_str or '暂无相关新闻'}"""

    def _parse_judge(self, raw: str) -> Dict:
        """解析裁判响应"""
        default = {
            "sentiment_summary": "",
            "risk_summary": "",
            "final_decision": "HOLD",
            "suggested_position": "观望",
            "reasoning": "解析异常，建议观望"
        }

        if not raw:
            return default

        try:
            clean = re.sub(r'```json|```', '', raw).strip()
            first, last = clean.find('{'), clean.rfind('}')
            if first != -1 and last != -1:
                parsed = json.loads(clean[first:last + 1])
                return {
                    "sentiment_summary": parsed.get('sentiment_summary', ''),
                    "risk_summary": parsed.get('risk_summary', ''),
                    "final_decision": parsed.get('final_decision', 'HOLD'),
                    "suggested_position": parsed.get('suggested_position', '观望'),
                    "reasoning": parsed.get('reasoning', default['reasoning'])
                }
        except Exception as e:
            print(f"[ERROR] Parse judge error: {e}")

        return default

    def _error(self, symbol: str, msg: str) -> Dict:
        """错误响应"""
        return {
            "symbol": symbol,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "fundamentals": {},
            "analysis": {
                "narrative_agent": {"model": "Qwen", "role": "感性脑", "content": f"[失败] {msg}"},
                "logic_agent": {"model": "DeepSeek", "role": "理性脑", "content": f"[失败] {msg}"}
            },
            "conclusion": {
                "sentiment_summary": "",
                "risk_summary": "",
                "final_decision": "HOLD",
                "suggested_position": "空仓",
                "reasoning": msg
            }
        }

    @staticmethod
    def format_decision(decision: str) -> str:
        """格式化决策中文"""
        return {
            "STRONG_BUY": "强烈买入", "BUY": "买入", "HOLD": "持有",
            "SELL": "卖出", "STRONG_SELL": "强烈卖出"
        }.get(decision, decision)

    @staticmethod
    def get_stars(decision: str) -> str:
        """获取信心星级"""
        return {
            "STRONG_BUY": "⭐⭐⭐⭐⭐", "BUY": "⭐⭐⭐⭐",
            "HOLD": "⭐⭐⭐", "SELL": "⭐⭐", "STRONG_SELL": "⭐"
        }.get(decision, "⭐⭐⭐")
