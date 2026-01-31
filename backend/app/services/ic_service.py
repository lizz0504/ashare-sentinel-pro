"""
AI Investment Committee (IC Meeting) Service

 Implements a multi-perspective investment analysis system using four famous investor personas:
 - Cathie Wood (Growth & Disruption)
 - Nancy Pelosi (Power & Policy)
 - Warren Buffett (Deep Value)
 - Charlie Munger (Inversion & Synthesis)

Architecture:
 1. Parallel execution for Cathie + Nancy (independent analyses)
 2. Sequential execution for Warren (reviews Cathie + Nancy)
 3. Final synthesis by Charlie (reviews all three, produces JSON verdict)
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional
from httpx import AsyncClient, TimeoutException

# Import prompts
from app.core.prompts import (
    PROMPT_CATHIE_WOOD,
    PROMPT_NANCY_PELOSI,
    PROMPT_WARREN_BUFFETT,
    PROMPT_CHARLIE_MUNGER,
    INVESTOR_PERSONAS,
    VERDICT_MAP,
    CONVICTION_LEVELS
)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# =============================================================================
# Configuration
# =============================================================================

DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3

# Model context limits (保守估计，留出安全边界)
MAX_MODEL_TOKENS = 200000  # qwen-max 的实际限制是 202750，我们使用 200000 作为安全值
SAFE_TOKEN_LIMIT = 180000  # 安全限制，留出 20% 的余量
MAX_PROMPT_TOKENS = 150000  # 单次请求的最大 prompt token 数

# Token 估算系数（粗略估计）
CHINESE_TOKEN_RATIO = 1.5  # 中文字符 ≈ 1.5 tokens/字符
ENGLISH_TOKEN_RATIO = 0.25  # 英文单词 ≈ 4 tokens/单词
MIXED_TOKEN_RATIO = 1.0    # 混合内容的平均值


# =============================================================================
# Token Management Helpers
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量。

    使用简单的启发式方法：
    - 中文字符约占 1.5 tokens/字符
    - 英文单词约占 0.25 tokens/单词（即 4 tokens/单词）
    - 混合内容取平均值

    Args:
        text: 要估算的文本

    Returns:
        估算的 token 数量
    """
    if not text:
        return 0

    # 统计中文字符和非中文字符
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text)

    if total_chars == 0:
        return 0

    # 如果主要是中文，使用中文比例
    if chinese_chars / total_chars > 0.5:
        return int(total_chars * CHINESE_TOKEN_RATIO)
    else:
        # 估算英文单词数（按空格分词）
        words = len(text.split())
        return int(words * 4)  # 英文约 4 tokens/单词


def truncate_text_by_tokens(text: str, max_tokens: int) -> str:
    """
    根据 token 限制截断文本。

    Args:
        text: 要截断的文本
        max_tokens: 最大 token 数量

    Returns:
        截断后的文本
    """
    if not text:
        return text

    current_tokens = estimate_tokens(text)

    if current_tokens <= max_tokens:
        return text

    # 需要截断的比例
    ratio = max_tokens / current_tokens
    target_length = int(len(text) * ratio * 0.9)  # 再留 10% 安全余量

    # 尝试在句子边界处截断
    truncated = text[:target_length]

    # 查找最后一个句号、问号或感叹号
    for delimiter in ['。', '！', '？', '.', '!', '?', '\n\n']:
        last_pos = truncated.rfind(delimiter)
        if last_pos > target_length * 0.7:  # 如果截断点在 70% 以后
            truncated = truncated[:last_pos + len(delimiter)]
            break

    return truncated + "\n\n[...内容已截断以符合模型限制...]"


def truncate_with_summary(text: str, max_chars: int = 300) -> str:
    """
    将长文本截断为摘要，保留关键信息。

    Args:
        text: 原始文本
        max_chars: 最大字符数

    Returns:
        截断后的摘要文本
    """
    if len(text) <= max_chars:
        return text

    # 尝试在句子边界截断
    truncated = text[:max_chars]
    for delimiter in ['。', '！', '？', '.', '!', '?', '\n']:
        last_pos = truncated.rfind(delimiter)
        if last_pos > max_chars * 0.7:
            return truncated[:last_pos + len(delimiter)] + "..."

    return truncated + "..."


# =============================================================================
# LLM Client
# =============================================================================

async def call_llm_async(
    prompt: str,
    api_key: str,
    timeout: int = DEFAULT_TIMEOUT
) -> str:
    """
    Call DashScope LLM API asynchronously.

    Args:
        prompt: The prompt to send
        api_key: DashScope API key
        timeout: Request timeout in seconds

    Returns:
        LLM response text
    """
    # Token 检查：使用更保守的估算
    # 中文字符通常需要 2-3 tokens，我们使用 2.5 作为安全值
    chinese_chars = sum(1 for c in prompt if '\u4e00' <= c <= '\u9fff')
    non_chinese = len(prompt) - chinese_chars
    # 更保守的估算：中文 2.5 tokens/字符，非中文 0.5 tokens/字符
    estimated_tokens = int(chinese_chars * 2.5 + non_chinese * 0.5)

    # 记录详细信息用于调试
    logger.info(f"[TOKEN_CHECK] Prompt: {len(prompt)} chars, {chinese_chars} Chinese, estimated {estimated_tokens} tokens")

    # 强制限制：无论估算如何，如果 prompt 超过 60000 字符，直接截断
    MAX_CHARS = 60000  # 约等于 150k tokens（保守估计）
    if len(prompt) > MAX_CHARS:
        logger.error(f"[TOKEN_LIMIT] Prompt too long: {len(prompt)} chars > {MAX_CHARS}, truncating...")
        prompt = prompt[:MAX_CHARS] + "\n\n[...由于长度限制已截断...]"

    # 重新计算截断后的 token
    chinese_chars = sum(1 for c in prompt if '\u4e00' <= c <= '\u9fff')
    non_chinese = len(prompt) - chinese_chars
    estimated_tokens = int(chinese_chars * 2.5 + non_chinese * 0.5)

    if estimated_tokens > SAFE_TOKEN_LIMIT:
        logger.error(f"[TOKEN_LIMIT] Estimated {estimated_tokens} > {SAFE_TOKEN_LIMIT}, truncating...")
        # 按字符数截断到安全值（约 120k tokens = 48000 字符）
        target_chars = int(SAFE_TOKEN_LIMIT / 2.5)
        prompt = prompt[:target_chars] + "\n\n[...由于长度限制已截断...]"
        logger.warning(f"[TOKEN_LIMIT] Truncated to {len(prompt)} chars")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen-max",
        "input": {
            "messages": [
                {"role": "system", "content": "You are an expert investment analyst."},
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "max_tokens": 2000,
            "temperature": 0.7
        }
    }

    async with AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(DASHSCOPE_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract the generated text
            if "output" in data and "text" in data["output"]:
                return data["output"]["text"]
            else:
                logger.error(f"Unexpected API response structure: {data}")
                return "Error: Unexpected API response"

        except TimeoutException:
            logger.error(f"LLM API timeout after {timeout}s")
            return "Error: API request timed out"
        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            return f"Error: {str(e)}"


# =============================================================================
# JSON Parsing Helper
# =============================================================================

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Robust JSON parsing with cleanup for LLM responses.

    Handles:
    - Markdown code blocks (```json ... ```)
    - Leading/trailing whitespace
    - Common JSON formatting issues
    - Fallback to default JSON if parsing fails

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dictionary, or default JSON if parsing fails
    """
    default_json = {
        "final_verdict": "HOLD",
        "conviction_level": 3,
        "key_considerations": ["无法解析AI响应，建议人工复核"],
        "invert_risks": ["AI分析失败风险"],
        "synthesis": "由于技术原因，无法生成综合分析。"
    }

    if not text:
        logger.warning("Empty text provided to clean_and_parse_json")
        return default_json

    try:
        # Step 1: Remove markdown code blocks
        # Pattern 1: ```json ... ```
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1)
            logger.info("Extracted JSON from ```json block")

        # Pattern 2: ``` ... ``` (no language specified)
        if not match:
            code_pattern = r'```\s*(.*?)\s*```'
            match = re.search(code_pattern, text, re.DOTALL)
            if match:
                text = match.group(1)
                logger.info("Extracted JSON from ``` block")

        # Step 2: Try to find JSON object boundaries
        # Look for first { and last }
        first_brace = text.find('{')
        last_brace = text.rfind('}')

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace:last_brace + 1]
            logger.info("Extracted JSON using brace boundaries")

        # Step 3: Clean common issues
        # Remove trailing commas before closing brackets/braces
        text = re.sub(r',(\s*[}\]])', r'\1', text)

        # Step 4: Parse JSON
        parsed = json.loads(text)
        logger.info("Successfully parsed JSON response")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        logger.error(f"Text that failed to parse: {text[:500]}...")
        return default_json
    except Exception as e:
        logger.error(f"Unexpected error in clean_and_parse_json: {str(e)}")
        return default_json


# =============================================================================
# IC Meeting Service
# =============================================================================

async def conduct_meeting(
    symbol: str,
    stock_name: str,
    current_price: float,
    context: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Conduct an AI Investment Committee meeting for a given stock.

    Meeting Flow:
    1. Parallel: Cathie Wood + Nancy Pelosi analyze independently
    2. Sequential: Warren Buffett reviews Cathie + Nancy's views
    3. Final: Charlie Munger synthesizes all views into JSON verdict

    Args:
        symbol: Stock symbol (e.g., "600519")
        stock_name: Stock name (e.g., "贵州茅台")
        current_price: Current stock price
        context: Additional context (industry, market cap, etc.)
        api_key: DashScope API key (optional, reads from env if not provided)

    Returns:
        Dictionary containing:
        - symbol: Stock symbol
        - cathie_wood: Analysis from Cathie Wood
        - nancy_pelosi: Analysis from Nancy Pelosi
        - warren_buffett: Analysis from Warren Buffett
        - final_verdict: Parsed JSON verdict from Charlie Munger
        - verdict_chinese: Chinese translation of verdict
        - conviction_stars: Star rating for conviction
        - error: Error message if any step failed
    """
    logger.info(f"Starting IC meeting for {symbol} ({stock_name})")

    # Prepare context
    if context is None:
        context = {}

    base_context = f"""
Stock: {symbol} - {stock_name}
Current Price: {current_price}
Industry: {context.get('industry', 'N/A')}
Market Cap: {context.get('market_cap', 'N/A')}

=== Value Metrics (Warren Buffett) ===
PE Ratio: {context.get('pe_ratio', 'N/A')}
PB Ratio: {context.get('pb_ratio', 'N/A')}
ROE: {context.get('roe', 'N/A')}
Debt-to-Equity: {context.get('debt_to_equity', 'N/A')}
FCF Yield: {context.get('fcf_yield', 'N/A')}

=== Growth Metrics (Cathie Wood) ===
Revenue Growth (CAGR): {context.get('revenue_growth', 'N/A')}
PEG Ratio: {context.get('peg_ratio', 'N/A')}
R&D Intensity: {context.get('rd_intensity', 'N/A')}

=== Technical & Momentum Metrics (Nancy Pelosi) ===
RSI (14): {context.get('rsi_14', 'N/A')}
Volume Status: {context.get('volume_status', 'N/A')}
Volume Change %: {context.get('volume_change_pct', 'N/A')}%
Turnover Rate: {context.get('turnover', 'N/A')}%
MA20 Status: {context.get('ma20_status', 'N/A')}
Health Score: {context.get('health_score', 'N/A')}/100
Action Signal: {context.get('action_signal', 'N/A')}
Bollinger Band Width: {context.get('bandwidth', 'N/A')}
VWAP (20-day): {context.get('vwap_20', 'N/A')}
"""

    # 检查并截断 base_context（预留足够空间给 prompt）
    base_context_tokens = estimate_tokens(base_context)
    if base_context_tokens > 5000:
        logger.warning(f"Base context too large: {base_context_tokens} tokens, truncating...")
        base_context = truncate_text_by_tokens(base_context, 3000)
        base_context_tokens = estimate_tokens(base_context)

    # Debug: Print the context to see what data is being sent to AI
    print(f"[DEBUG] IC Meeting Context for {symbol}:")
    print(base_context)
    print(f"[DEBUG] Context keys: {list(context.keys())}")

    # =============================================================================
    # Round 1: Parallel Execution (Cathie + Nancy)
    # =============================================================================

    logger.info("Round 1: Parallel execution - Cathie Wood + Nancy Pelosi")

    try:
        # Create tasks for parallel execution
        cathie_task = call_llm_async(
            f"{PROMPT_CATHIE_WOOD}\n\n{base_context}",
            api_key or ""
        )

        nancy_task = call_llm_async(
            f"{PROMPT_NANCY_PELOSI}\n\n{base_context}",
            api_key or ""
        )

        # Execute in parallel
        cathie_response, nancy_response = await asyncio.gather(
            cathie_task,
            nancy_task
        )

        logger.info("Round 1 completed: Received responses from Cathie and Nancy")

    except Exception as e:
        logger.error(f"Round 1 failed: {str(e)}")
        cathie_response = f"Error: Cathie Wood analysis failed - {str(e)}"
        nancy_response = f"Error: Nancy Pelosi analysis failed - {str(e)}"

    # =============================================================================
    # Round 2: Sequential Execution (Warren Buffett)
    # =============================================================================

    logger.info("Round 2: Sequential execution - Warren Buffett")

    # 更激进地截断前两轮响应，减少 token 使用
    cathie_summary = truncate_with_summary(cathie_response, 200)
    nancy_summary = truncate_with_summary(nancy_response, 200)

    # 计算 Warren 的 prompt 预估 token 数
    warren_prompt_est = estimate_tokens(PROMPT_WARREN_BUFFETT) + estimate_tokens(base_context) + 2000  # 预留 2000 for summaries

    if warren_prompt_est > MAX_PROMPT_TOKENS:
        logger.warning(f"Warren's prompt too large: {warren_prompt_est} tokens, further truncating...")
        cathie_summary = truncate_with_summary(cathie_response, 100)
        nancy_summary = truncate_with_summary(nancy_response, 100)

    warren_context = f"""
{base_context}

## Previous Analysts' Views (Summarized)

### Cathie Wood (Growth Perspective):
{cathie_summary}

### Nancy Pelosi (Policy Perspective):
{nancy_summary}

## Your Task
Review the summarized perspectives above, then provide your value investing analysis.
**Please be concise** - limit your response to 300 words maximum.
"""

    try:
        warren_response = await call_llm_async(
            f"{PROMPT_WARREN_BUFFETT}\n\n{warren_context}",
            api_key or ""
        )
        logger.info("Round 2 completed: Received response from Warren Buffett")

    except Exception as e:
        logger.error(f"Round 2 failed: {str(e)}")
        warren_response = f"Error: Warren Buffett analysis failed - {str(e)}"

    # =============================================================================
    # Round 3: Final Verdict (Charlie Munger)
    # =============================================================================

    logger.info("Round 3: Final verdict - Charlie Munger")

    # 计算可用 token 预算
    prompt_tokens = estimate_tokens(PROMPT_CHARLIE_MUNGER)
    context_tokens = estimate_tokens(base_context)
    available_for_summaries = MAX_PROMPT_TOKENS - prompt_tokens - context_tokens - 5000  # 留出 5000 安全余量

    if available_for_summaries < 1000:
        logger.error(f"Not enough token budget for Charlie: {available_for_summaries}")
        available_for_summaries = 1000  # 最少保留 1000

    # 每个摘要分配 1/3 的可用空间
    summary_limit = available_for_summaries // 3

    # 使用 token 感知的截断
    cathie_brief = truncate_text_by_tokens(cathie_response, summary_limit)
    nancy_brief = truncate_text_by_tokens(nancy_response, summary_limit)
    warren_brief = truncate_text_by_tokens(warren_response, summary_limit)

    # 进一步压缩为极简摘要
    cathie_brief = truncate_with_summary(cathie_brief, 150)
    nancy_brief = truncate_with_summary(nancy_brief, 150)
    warren_brief = truncate_with_summary(warren_brief, 150)

    charlie_context = f"""
{base_context}

## IC Meeting Summary (Brief)

### Cathie Wood (Growth & Disruption):
{cathie_brief}

### Nancy Pelosi (Power & Policy):
{nancy_brief}

### Warren Buffett (Deep Value):
{warren_brief}

## Your Task
Review the summarized perspectives above, then provide your FINAL VERDICT in JSON format as specified in your instructions.

**CRITICAL OUTPUT REQUIREMENTS:**
- Do NOT output markdown formatting (no ```json or ``` blocks)
- Output RAW JSON only
- Keep the "synthesis" field under 50 words
- Keep each "key_consideration" under 20 words
- Keep each "invert_risk" under 15 words
"""

    # 最终检查 Charlie 的 prompt 是否超过限制
    final_charlie_prompt = f"{PROMPT_CHARLIE_MUNGER}\n\n{charlie_context}"
    final_token_count = estimate_tokens(final_charlie_prompt)

    if final_token_count > SAFE_TOKEN_LIMIT:
        logger.error(f"Charlie's prompt exceeds safe limit: {final_token_count} > {SAFE_TOKEN_LIMIT}")
        # 紧急截断：只保留最核心的上下文
        charlie_context = f"""
Stock: {symbol} - {stock_name}
Current Price: {current_price}

## Key Metrics:
PE: {context.get('pe_ratio', 'N/A')}, ROE: {context.get('roe', 'N/A')}, Growth: {context.get('revenue_growth', 'N/A')}

## Analysts' Key Decisions:
- Cathie Wood: {truncate_with_summary(cathie_response, 50)}
- Nancy Pelosi: {truncate_with_summary(nancy_response, 50)}
- Warren Buffett: {truncate_with_summary(warren_response, 50)}

Provide your FINAL VERDICT in JSON format. Be concise.
"""

    try:
        charlie_response = await call_llm_async(
            f"{PROMPT_CHARLIE_MUNGER}\n\n{charlie_context}",
            api_key or ""
        )
        logger.info("Round 3 completed: Received response from Charlie Munger")

        # Parse Charlie's JSON response
        final_verdict = clean_and_parse_json(charlie_response)

    except Exception as e:
        logger.error(f"Round 3 failed: {str(e)}")
        final_verdict = {
            "final_verdict": "HOLD",
            "conviction_level": 3,
            "key_considerations": [f"AI分析失败: {str(e)}"],
            "invert_risks": ["技术故障风险"],
            "synthesis": "由于技术原因，无法完成投委会会议。"
        }

    # =============================================================================
    # Compile Results
    # =============================================================================

    # Handle both old and new JSON format from Charlie Munger
    # New format: "decision", "conviction", "risk_factors"
    # Old format: "final_verdict", "conviction_level", "invert_risks"
    verdict_key = "decision" if "decision" in final_verdict else "final_verdict"
    conviction_key = "conviction" if "conviction" in final_verdict else "conviction_level"
    risks_key = "risk_factors" if "risk_factors" in final_verdict else "invert_risks"

    # Normalize to old format for backward compatibility
    normalized_verdict = {
        "final_verdict": final_verdict.get(verdict_key, final_verdict.get("final_verdict", "HOLD")),
        "conviction_level": final_verdict.get(conviction_key, final_verdict.get("conviction_level", 3)),
        "key_considerations": final_verdict.get("key_considerations", []),
        "invert_risks": final_verdict.get(risks_key, final_verdict.get("invert_risks", [])),
        "synthesis": final_verdict.get("synthesis", ""),
        # New fields (if present)
        "score": final_verdict.get("score"),
        "logical_flaws_detected": final_verdict.get("logical_flaws_detected", []),
    }

    verdict_chinese = VERDICT_MAP.get(normalized_verdict["final_verdict"], "持有")
    conviction_level = normalized_verdict["conviction_level"]
    conviction_stars = CONVICTION_LEVELS.get(conviction_level, "⭐⭐⭐")

    # 计算技术面和基本面得分
    technical_score = calculate_technical_score(context)
    fundamental_score = calculate_fundamental_score(context)

    result = {
        "symbol": symbol,
        "stock_name": stock_name,
        "current_price": current_price,
        "cathie_wood": cathie_response,
        "nancy_pelosi": nancy_response,
        "warren_buffett": warren_response,
        "charlie_munger_raw": charlie_response if 'charlie_response' in locals() else "Error",
        "final_verdict": normalized_verdict,
        "verdict_chinese": verdict_chinese,
        "conviction_level": conviction_level,
        "conviction_stars": conviction_stars,
        "technical_score": technical_score,
        "fundamental_score": fundamental_score,
        "timestamp": context.get("timestamp", "")
    }

    logger.info(f"IC meeting completed for {symbol}: {verdict_chinese} {conviction_stars}")

    return result


# =============================================================================
# Helper Functions
# =============================================================================

def format_ic_meeting_summary(meeting_result: Dict[str, Any]) -> str:
    """
    Format IC meeting results into a readable text summary.

    Args:
        meeting_result: Result from conduct_meeting()

    Returns:
        Formatted text summary
    """
    lines = [
        f"# AI投委会会议纪要",
        f"",
        f"**股票代码**: {meeting_result['symbol']}",
        f"**股票名称**: {meeting_result['stock_name']}",
        f"**当前价格**: {meeting_result['current_price']}",
        f"**最终判决**: {meeting_result['verdict_chinese']} {meeting_result['conviction_stars']}",
        f"",
        f"---",
        f"",
        f"## 1. Cathie Wood (成长与颠覆)",
        f"",
        f"{meeting_result['cathie_wood']}",
        f"",
        f"---",
        f"",
        f"## 2. Nancy Pelosi (权力与政策)",
        f"",
        f"{meeting_result['nancy_pelosi']}",
        f"",
        f"---",
        f"",
        f"## 3. Warren Buffett (深度价值)",
        f"",
        f"{meeting_result['warren_buffett']}",
        f"",
        f"---",
        f"",
        f"## 4. Charlie Munger (最终判决)",
        f"",
        f"**最终观点**: {meeting_result['verdict_chinese']}",
        f"**信心等级**: {meeting_result['conviction_stars']} ({meeting_result['conviction_level']}/5)",
        f"",
        f"**关键考虑因素**:",
    ]

    for consideration in meeting_result['final_verdict'].get('key_considerations', []):
        lines.append(f"- {consideration}")

    lines.append("")
    lines.append("**反向思考风险**:")

    for risk in meeting_result['final_verdict'].get('invert_risks', []):
        lines.append(f"- {risk}")

    lines.append("")
    lines.append(f"**综合逻辑**: {meeting_result['final_verdict'].get('synthesis', 'N/A')}")

    return "\n".join(lines)


def get_ic_recommendation_summary(meeting_result: Dict[str, Any]) -> str:
    """
    Get a one-line summary of the IC recommendation.

    Args:
        meeting_result: Result from conduct_meeting()

    Returns:
        One-line summary string
    """
    return (
        f"{meeting_result['stock_name']} ({meeting_result['symbol']}): "
        f"{meeting_result['verdict_chinese']} {meeting_result['conviction_stars']} - "
        f"{meeting_result['final_verdict'].get('synthesis', '')[:50]}..."
    )


def _to_float(value: Any) -> float | None:
    """Helper function to convert various types to float, handling percentages and 'N/A'"""
    if value is None or value == 'N/A' or value == '':
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove % sign and whitespace
        cleaned = value.replace('%', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def calculate_technical_score(context: Dict[str, Any]) -> int:
    """
    根据技术指标计算技术面得分（0-100）

    Args:
        context: 包含技术指标的字典

    Returns:
        技术面得分 (0-100)
    """
    score = 50  # 基础分

    try:
        # Health Score (0-100) - 权重 30%
        health_score = _to_float(context.get('health_score'))
        if health_score is not None:
            score += (health_score - 50) * 0.3

        # RSI (14) - 权重 20%
        # RSI > 70 超买（减分），RSI < 30 超卖（加分），30-70 理想
        rsi = _to_float(context.get('rsi_14'))
        if rsi is not None:
            if 30 <= rsi <= 70:
                score += 10
            elif rsi < 30:
                score += 5  # 超卖可能反弹
            else:  # rsi > 70
                score -= 15  # 超买风险

        # MA20 Status - 权重 15%
        ma20_status = context.get('ma20_status', '')
        if isinstance(ma20_status, str):
            if '价格位于均线上方' in ma20_status or 'above' in ma20_status.lower():
                score += 15
            elif '价格位于均线附近' in ma20_status or 'near' in ma20_status.lower():
                score += 5
            else:
                score -= 10

        # Volume Change % - 权重 15%
        volume_change = _to_float(context.get('volume_change_pct'))
        if volume_change is not None:
            if volume_change > 50:
                score += 10
            elif volume_change > 20:
                score += 5
            elif volume_change < -20:
                score -= 10

        # Bollinger Band Width - 权重 10%
        # 宽度过窄可能预示突破，宽度过宽可能回调
        bandwidth = _to_float(context.get('bandwidth'))
        if bandwidth is not None:
            if bandwidth < 0.05:
                score += 8  # 可能突破
            elif bandwidth > 0.2:
                score -= 5  # 可能回调

        # VWAP vs Price - 权重 10%
        vwap = _to_float(context.get('vwap_20'))
        current_price = _to_float(context.get('current_price'))
        if vwap is not None and current_price is not None:
            if current_price > vwap:
                score += 10
            elif current_price < vwap * 0.95:
                score -= 10

    except Exception as e:
        logger.warning(f"Error calculating technical score: {e}")

    return max(0, min(100, int(score)))


def calculate_fundamental_score(context: Dict[str, Any]) -> int:
    """
    根据基本面指标计算基本面得分（0-100）

    Args:
        context: 包含基本面指标的字典

    Returns:
        基本面得分 (0-100)
    """
    score = 50  # 基础分

    try:
        # ROE - 权重 25%
        roe = _to_float(context.get('roe'))
        if roe is not None:
            if roe >= 20:
                score += 20
            elif roe >= 15:
                score += 15
            elif roe >= 10:
                score += 10
            elif roe < 5:
                score -= 15

        # PE Ratio - 权重 20%
        pe = _to_float(context.get('pe_ratio'))
        if pe is not None:
            if pe < 15:
                score += 20
            elif pe < 25:
                score += 15
            elif pe < 35:
                score += 5
            elif pe > 50:
                score -= 20

        # Revenue Growth (CAGR) - 权重 25%
        growth = _to_float(context.get('revenue_growth'))
        if growth is not None:
            growth_pct = growth * 100 if growth < 1 else growth
            if growth_pct >= 20:
                score += 25
            elif growth_pct >= 15:
                score += 20
            elif growth_pct >= 10:
                score += 15
            elif growth_pct >= 5:
                score += 10
            elif growth_pct < 0:
                score -= 20

        # Debt-to-Equity - 权重 15%
        debt_to_equity = _to_float(context.get('debt_to_equity'))
        if debt_to_equity is not None:
            if debt_to_equity < 30:
                score += 15
            elif debt_to_equity < 50:
                score += 10
            elif debt_to_equity < 80:
                score += 5
            else:  # >= 80
                score -= 15

        # PB Ratio - 权重 10%
        pb = _to_float(context.get('pb_ratio'))
        if pb is not None:
            if pb < 2:
                score += 10
            elif pb < 3:
                score += 5
            elif pb > 8:
                score -= 10

        # PEG Ratio - 权重 5%
        peg = _to_float(context.get('peg_ratio'))
        if peg is not None:
            if peg < 1:
                score += 5
            elif peg > 2:
                score -= 5

    except Exception as e:
        logger.warning(f"Error calculating fundamental score: {e}")

    return max(0, min(100, int(score)))
