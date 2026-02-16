"""
技术面与基本面融合分析服务

解决技术面和基本面之间的背离，给出统一的操作策略
"""

import json
import logging
import re
import textwrap
from typing import Dict, Any, Optional
from app.core.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class SynthesisService:
    """技术面与基本面融合分析服务"""

    @staticmethod
    async def synthesize_strategy(
        symbol: str,
        tech_view: Dict[str, Any],
        fund_view: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        融合技术面和基本面分析，解决冲突给出最终策略

        Args:
            symbol: 股票代码
            tech_view: 技术面分析视图
            fund_view: 基本面分析视图
            context: 额外的市场数据上下文

        Returns:
            包含策略类型的字典
        """

        # 构建上下文：把矛盾摆在台面上
        context_text = f"""
【标的】{symbol}

【矛盾的根源】

1. 技术面信号 (短期视角):
   - 决策: {tech_view.get('decision', 'N/A')}
   - 评分: {tech_view.get('score', 0)}/100
   - 分析: {tech_view.get('analysis_summary', 'N/A')}
   - 关键信号: {json.dumps(tech_view.get('key_signals', {}), ensure_ascii=False)}

2. 基本面信号 (长期视角):
   - 决策: {fund_view.get('decision', 'N/A')}
   - 评分: {fund_view.get('score', 0)}/100
   - 分析: {fund_view.get('analysis_summary', 'N/A')}
   - 关键信号: {json.dumps(fund_view.get('key_signals', {}), ensure_ascii=False)}

【当前市场数据】
{json.dumps(context or {}, ensure_ascii=False, indent=2)}
"""

        # 核心 Prompt：策略路由逻辑
        system_prompt = textwrap.dedent("""
            你是【首席投资策略官】。你的工作不是选股，而是【配置策略】。
            你需要解决"技术面"和"基本面"可能存在的冲突。

            【四大策略场景】

            1. 情形 A：垃圾股的反弹 (技术BUY + 基本面SELL)
               - 判定：刀口舔血 / 投机性反弹
               - 建议：轻仓(10-20%)，严格止损，快进快出。不要格局。
               - 警告：这是价值陷阱，反弹即是卖点。
               - strategy_type: "SPECULATIVE_REBOUND"

            2. 情形 B：好公司的错杀 (技术SELL + 基本面BUY)
               - 判定：左侧磨底 / 价值定投
               - 建议：分批建仓，越跌越买，耐心持有。
               - 警告：短期可能继续浮亏，需要时间换空间。
               - strategy_type: "VALUE_ACCUMULATION"

            3. 情形 C：共振主升浪 (技术BUY + 基本面BUY)
               - 判定：戴维斯双击 / 积极做多
               - 建议：重仓跟随，只设止盈，不设止损。
               - strategy_type: "RESONANCE_LONG"

            4. 情形 D：崩盘回避 (技术SELL + 基本面SELL)
               - 判定：君子不立危墙 / 观望
               - 建议：空仓，耐心等待。
               - strategy_type: "AVOID"

            【输出要求】
            1. 必须是纯JSON格式，不要有任何markdown标记
            2. strategy_type必须是以下四个之一:
               SPECULATIVE_REBOUND, VALUE_ACCUMULATION, RESONANCE_LONG, AVOID
            3. 标题要一针见血，用中文表达策略本质
            4. action_guide要具体可执行
            5. conviction是置信度，1-5星

            输出JSON格式:
            {
                "strategy_type": "SPECULATIVE_REBOUND",
                "title": "刀口舔血",
                "position_suggest": "轻仓10-20%",
                "action_guide": "具体操作指导，3句话以内",
                "risk_warning": "最大风险点，一句话",
                "time_frame": "短线(1-2周)" | "中长期(3-12月)" | "无限制",
                "conviction": 3,
                "rationale": "策略推理逻辑，100字以内"
            }
        """).strip()

        user_prompt = (
            f"请分析以下技术面与基本面的背离情况，"
            f"给出融合策略：\n{context_text}"
        )

        try:
            # 使用DeepSeek进行深度逻辑整合
            raw_response = await LLMFactory.fast_reply(
                "deepseek", system_prompt, user_prompt, timeout=30
            )

            logger.info(f"[Synthesis] Raw response: {raw_response[:200]}...")

            # 清洗JSON
            cleaned = SynthesisService._clean_json(raw_response)
            result = json.loads(cleaned)

            # 验证必填字段
            if "strategy_type" not in result:
                raise ValueError("Missing strategy_type in response")

            # 添加原始分析
            result["raw_analysis"] = (
                raw_response[:500] if len(raw_response) > 500 else raw_response
            )

            return result
        except Exception as e:
            logger.error(f"[Synthesis] Error: {e}")
            # 降级到规则引擎
            return SynthesisService._fallback_strategy(tech_view, fund_view)

    @staticmethod
    def _clean_json(raw: str) -> str:
        """清洗LLM输出的JSON"""
        # 移除markdown标记
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r'```(?:json)?\n?', '', text)
            text = re.sub(r'\n?```', '', text)

        # 提取JSON对象
        start = text.find('{')
        end = text.rfind('}')

        if start != -1 and end != -1:
            return text[start:end + 1]

        return text

    @staticmethod
    def _fallback_strategy(tech_view: Dict, fund_view: Dict) -> Dict[str, Any]:
        """降级策略：基于规则引擎"""
        tech_score = tech_view.get('score', 50)
        fund_score = fund_view.get('score', 50)

        # 规则引擎
        if tech_score >= 60 and fund_score < 40:
            return {
                "strategy_type": "SPECULATIVE_REBOUND",
                "title": "刀口舔血",
                "position_suggest": "轻仓10-20%",
                "action_guide": "技术面强势但基本面疲弱，可能是短期反弹。控制仓位，严格止损，不贪心。",
                "risk_warning": "价值陷阱，反弹可能是出货机会",
                "time_frame": "短线(1-2周)",
                "conviction": 2,
                "rationale": "技术面优于基本面，适合短线投机"
            }

        elif tech_score < 40 and fund_score >= 70:
            return {
                "strategy_type": "VALUE_ACCUMULATION",
                "title": "左侧埋伏",
                "position_suggest": "分批建仓30-60%",
                "action_guide": "基本面优秀但技术面疲弱，是左侧布局良机。分批买入，耐心持有。",
                "risk_warning": "短期可能继续浮亏，需要耐心",
                "time_frame": "中长期(3-12月)",
                "conviction": 4,
                "rationale": "基本面支撑长期价值，技术面提供买点"
            }

        elif tech_score >= 70 and fund_score >= 70:
            return {
                "strategy_type": "RESONANCE_LONG",
                "title": "戴维斯双击",
                "position_suggest": "重仓60-80%",
                "action_guide": "技术面和基本面共振向上，重仓跟随。只设止盈，不设止损。",
                "risk_warning": "注意市场整体情绪变化",
                "time_frame": "中长期持有",
                "conviction": 5,
                "rationale": "双强共振，最佳做多时机"
            }

        else:
            return {
                "strategy_type": "AVOID",
                "title": "观望等待",
                "position_suggest": "空仓",
                "action_guide": "方向不明，耐心等待明确信号。",
                "risk_warning": "震荡市场，盲目操作易亏损",
                "time_frame": "短期观察",
                "conviction": 3,
                "rationale": "缺乏明确信号，保持谨慎"
            }


# 便捷函数
async def synthesize_strategy(
    symbol: str,
    tech_view: Dict[str, Any],
    fund_view: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """便捷函数：融合技术面和基本面策略"""
    return await SynthesisService.synthesize_strategy(
        symbol, tech_view, fund_view, context
    )
