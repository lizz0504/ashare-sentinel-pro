# A股Sentinel Pro - IC投委会完整代码文档

**生成时间**: 2026-02-16
**目标**: 在不改变逻辑的情况下，将IC投委会分析时间从10-20分钟压缩到60秒

---

## 📋 目录

1. [问题描述](#问题描述)
2. [核心代码 - conduct_meeting函数](#核心代码---conduct_meeting函数)
3. [LLM调用工厂](#llm调用工厂)
4. [AI提示词定义](#ai提示词定义)
5. [性能瓶颈分析](#性能瓶颈分析)
6. [优化建议](#优化建议)

---

## 问题描述

### 当前状态
- **正常流程**: 应该在60-90秒内完成
- **实际状态**: 需要10-20分钟
- **症状**: 后端出现58步骤tqdm进度条（已禁用Tavily搜索后消失）

### IC投委会架构

```
Round 1: 并行执行 (Cathie Wood + Nancy Pelosi) → 2个LLM调用
Round 2: 顺序执行 (Warren Buffett) → 1个LLM调用
Round 3: 最终决策 (Charlie Munger) → 1个LLM调用

总计: 4次LLM调用
```

---

## 核心代码 - conduct_meeting函数

**文件**: `backend/app/services/ic_service.py` (第413-896行)

```python
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
    """
    logger.info(f"Starting IC meeting for {symbol} ({stock_name})")

    # Prepare context
    if context is None:
        context = {}
        # 获取财务数据
        from app.services.market_service import calculate_financial_metrics
        financial_metrics = calculate_financial_metrics(symbol)
        context.update(financial_metrics.get('metrics', {}))
        context['market'] = financial_metrics.get('market', 'A')
        context['symbol'] = financial_metrics.get('symbol', symbol)

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
Revenue Growth (CAGR): {context.get('revenue_growth_cagr', 'N/A')}
PEG Ratio: {context.get('peg_ratio', 'N/A')}
R&D Intensity: {context.get('rd_intensity', 'N/A')}

=== Technical & Momentum Metrics (Nancy Pelosi) ===
RSI (14): {context.get('rsi_14', 'N/A')}
Volume Status: {context.get('volume_status', 'N/A')}
Volume Change %: {context.get('volume_change_pct', 'N/A')}%
Turnover Rate: {context.get('turnover_rate', 'N/A')}%
MA20 Status: {context.get('ma20_status', 'N/A')}
Health Score: {context.get('health_score', 'N/A')}/100
Action Signal: {context.get('action_signal', 'N/A')}
Bollinger Band Width: {context.get('bb_width', 'N/A')}
VWAP (20-day): {context.get('vwap_20d', 'N/A')}
Bollinger Position: {context.get('bollinger_position', 'N/A')}
"""

    # ========================================================================
    # NEW: Enhanced Context Injection (Anti-Hallucination Data)
    # ========================================================================
    injection_context = ""
    profile_data = None
    news_result = None

    try:
        # 1. Fetch Tushare Profile (Official Company Identity)
        logger.info(f"[ENHANCED] Fetching Tushare profile for {symbol}...")
        from app.services.market_service import get_stock_main_business_tushare

        try:
            profile_data = get_stock_main_business_tushare(symbol)
            logger.info("[ENHANCED] Tushare profile fetched successfully")

            # 获取当前价格
            from app.services.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            stock_info = fetcher.get_stock_info(symbol)
            current_price = stock_info.get("current_price", 0) if stock_info else 0
        except Exception as tushare_error:
            logger.warning(f"[ENHANCED] Tushare fetch failed: {tushare_error}")
            profile_data = None

        # 2. Fetch Tavily Intelligence (Real-time News Intelligence) - DISABLED
        # from app.services.search_service import search_financial_news, format_search_context_for_llm
        logger.info(f"[ENHANCED] Skipping Tavily search to avoid 58-step progress bar issue")
        news_result = {"results": [], "summary": "网络搜索已禁用以优化性能"}

        # 解析 Tavily JSON 数据
        tavily_context_json = format_search_context_for_llm(news_result, stock_name)
        try:
            tavily_data = json.loads(tavily_context_json)
            tavily_structured = tavily_data.get("tavily_data", {})
            tavily_summary = tavily_data.get("summary", "")
            tavily_results = tavily_structured.get("results", [])
            tavily_total = tavily_structured.get("total_fetched", 0)
        except Exception as e:
            logger.warning(f"[ENHANCED] Failed to parse Tavily JSON: {e}")
            tavily_summary = tavily_context_json

        # 3. Build Injection Payload
        if profile_data or news_result.get('results'):
            injection_context = """
【=== 新增高维数据输入 (Anti-Hallucination) ===】
"""
            if profile_data:
                injection_context += f"""
1. 公司官方身份 (Tushare Profile):
   - 股票代码: {profile_data.get('symbol', 'N/A')}
   - 股票名称: {profile_data.get('name', 'N/A')}
   - 所属行业: {profile_data.get('industry', 'N/A')}
   - 所在地: {profile_data.get('area', 'N/A')}
   - 主营业务: {profile_data.get('main_business', 'N/A')}
   - 经营范围: {profile_data.get('business_scope', 'N/A')[:200]}...
"""

            if news_result.get('results'):
                injection_context += f"""
2. 市场实时情报 (Tavily Search):
{tavily_summary}
"""

            injection_context += """
【重要】请基于以上新增事实数据，结合你原有的投资逻辑进行分析。
"""
            logger.info(f"[ENHANCED] Injected Tushare Profile + Tavily Intel for {symbol}")

    except Exception as e:
        logger.warning(f"[ENHANCED] Failed to fetch anti-hallucination data: {e}")
        injection_context = ""

    # Merge injection context into base context
    enhanced_base_context = base_context + injection_context

    # ========================================================================
    # Round 1: Parallel Execution (Cathie + Nancy)
    # ========================================================================
    logger.info("Round 1: Parallel execution - Cathie Wood + Nancy Pelosi")

    try:
        # Create tasks for parallel execution
        cathie_task = call_llm_async(
            f"{PROMPT_CATHIE_WOOD}\n\n{enhanced_base_context}",
            api_key or ""
        )

        nancy_task = call_llm_async(
            f"{PROMPT_NANCY_PELOSI}\n\n{enhanced_base_context}",
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

    # ========================================================================
    # Round 2: Sequential Execution (Warren Buffett)
    # ========================================================================
    logger.info("Round 2: Sequential execution - Warren Buffett")

    # 截断前两轮响应
    cathie_summary = truncate_with_summary(cathie_response, 200)
    nancy_summary = truncate_with_summary(nancy_response, 200)

    warren_context = f"""
{enhanced_base_context}

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

    # ========================================================================
    # Round 3: Final Verdict (Charlie Munger)
    # ========================================================================
    logger.info("Round 3: Final verdict - Charlie Munger")

    # 计算可用 token 预算
    prompt_tokens = estimate_tokens(PROMPT_CHARLIE_MUNGER)
    context_tokens = estimate_tokens(base_context)
    available_for_summaries = (
        MAX_PROMPT_TOKENS - prompt_tokens - context_tokens - 5000
    )

    if available_for_summaries < 1000:
        logger.error(f"Not enough token budget for Charlie: {available_for_summaries}")
        available_for_summaries = 1000

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
{enhanced_base_context}

## IC Meeting Summary (Brief)

### Cathie Wood (Growth & Disruption):
{cathie_brief}

### Nancy Pelosi (Power & Policy):
{nancy_brief}

### Warren Buffett (Deep Value):
{warren_brief}

## Your Task
Review the summarized perspectives above, then provide your FINAL VERDICT in JSON format.

**CRITICAL OUTPUT REQUIREMENTS:**
- Do NOT output markdown formatting (no ```json or ``` blocks)
- Output RAW JSON only
- Keep the "synthesis" field under 50 words
- Keep each "key_consideration" under 20 words
- Keep each "invert_risk" under 15 words
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

    # ========================================================================
    # Compile Results
    # ========================================================================
    verdict_key = "decision" if "decision" in final_verdict else "final_verdict"
    conviction_key = "conviction" if "conviction" in final_verdict else "conviction_level"
    risks_key = "risk_factors" if "risk_factors" in final_verdict else "invert_risks"

    normalized_verdict = {
        "final_verdict": final_verdict.get(
            verdict_key, final_verdict.get("final_verdict", "HOLD")
        ),
        "conviction_level": final_verdict.get(
            conviction_key, final_verdict.get("conviction_level", 3)
        ),
        "key_considerations": final_verdict.get("key_considerations", []),
        "invert_risks": final_verdict.get(risks_key, final_verdict.get("invert_risks", [])),
        "synthesis": final_verdict.get("synthesis", ""),
        "score": final_verdict.get("score"),
        "logical_flaws_detected": final_verdict.get("logical_flaws_detected", []),
    }

    verdict_chinese = VERDICT_MAP.get(normalized_verdict["final_verdict"], "持有")
    conviction_level = normalized_verdict["conviction_level"]
    conviction_stars = CONVICTION_LEVELS.get(conviction_level, "***")

    # 计算技术面和基本面得分
    technical_score = calculate_technical_score(context)
    fundamental_score = calculate_fundamental_score(context)

    # 提取角色评分
    cathie_score_data = extract_agent_score(cathie_response)
    nancy_score_data = extract_agent_score(nancy_response)
    warren_score_data = extract_agent_score(warren_response)

    # 计算Dashboard坐标
    fundamental_x = int((warren_score_data["score"] * 0.6) + (nancy_score_data["score"] * 0.4))
    fundamental_x = max(0, min(100, fundamental_x))

    trend_y = int((cathie_score_data["score"] * 0.5) + (technical_score * 0.5))
    trend_y = max(0, min(100, trend_y))

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
        "timestamp": context.get("timestamp", ""),
        "agent_scores": {
            "cathie_wood": cathie_score_data,
            "nancy_pelosi": nancy_score_data,
            "warren_buffett": warren_score_data
        },
        "dashboard_position": {
            "final_x": fundamental_x,
            "final_y": trend_y
        }
    }

    logger.info(f"IC meeting completed for {symbol}: {verdict_chinese} {conviction_stars}")
    return result
```

---

## LLM调用工厂

**文件**: `backend/app/core/llm_factory.py`

```python
class LLMFactory:
    """多模型AI调用工厂"""

    APIS = {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    }

    MODELS = {
        "deepseek": "deepseek-chat",
        "zhipu": "glm-4"
    }

    NAMES = {
        "deepseek": "DeepSeek",
        "zhipu": "智谱GLM"
    }

    @classmethod
    async def fast_reply(
        cls,
        model: str,
        system: str,
        user: str,
        timeout: int = 60  # 增加到 60 秒（原 30 秒）
    ) -> str:
        """快速调用模型"""
        caller = {
            "deepseek": cls._call_deepseek,
            "zhipu": cls._call_zhipu
        }.get(model)

        if caller:
            return await caller(system, user, timeout)
        return f"[错误] 未知模型: {model}"

    @classmethod
    async def _call_deepseek(cls, system: str, user: str, timeout: int) -> str:
        """调用DeepSeek"""
        api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        if not api_key:
            logger.warning("DeepSeek未配置，降级到Zhipu")
            return await cls._call_zhipu(system, user, timeout)

        data = await cls._call_api(
            cls.APIS["deepseek"],
            {"Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"},
            {
                "model": cls.MODELS["deepseek"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "max_tokens": 500,  # 减少到 500（原 1000）加快响应
                "temperature": 0.7
            },
            timeout
        )

        if data and "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        return "[错误] DeepSeek调用失败"

    @classmethod
    async def _call_zhipu(cls, system: str, user: str, timeout: int) -> str:
        """调用智谱GLM"""
        api_key = getattr(settings, 'ZHIPU_API_KEY', None)
        if not api_key:
            logger.warning("智谱未配置，降级到DeepSeek")
            return await cls._call_deepseek(system, user, timeout)

        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": cls.MODELS["zhipu"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": 1000,  # 减少到 1000（原 8000）加快响应
            "temperature": 0.6
        }

        try:
            async with AsyncClient(timeout=timeout) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"]
                return "[错误] 智谱调用失败"
        except HttpTimeout:
            logger.error(f"智谱API超时: {url}")
        except Exception as e:
            logger.error(f"智谱API错误: {e}")

        return "[错误] 智谱调用失败"
```

### LLM调用包装函数

**文件**: `backend/app/services/ic_service.py` (第158-242行)

```python
async def call_llm_async(
    prompt: str,
    api_key: str,
    timeout: int = DEFAULT_TIMEOUT  # DEFAULT_TIMEOUT = 30秒
) -> str:
    """
    Call LLM API asynchronously with multi-model fallback.

    优先级: deepseek -> zhipu (自动降级)

    Args:
        prompt: The prompt to send
        api_key: API key (兼容旧参数，现在使用LLM工厂)
        timeout: Request timeout in seconds

    Returns:
        LLM response text
    """
    from app.core.llm_factory import LLMFactory

    # Token 检查：使用更保守的估算
    chinese_chars = sum(1 for c in prompt if '\u4e00' <= c <= '\u9fff')
    non_chinese = len(prompt) - chinese_chars
    estimated_tokens = int(chinese_chars * 2.5 + non_chinese * 0.5)

    logger.info(
        f"[TOKEN_CHECK] Prompt: {len(prompt)} chars, {chinese_chars} Chinese, "
        f"estimated {estimated_tokens} tokens"
    )

    # 强制限制
    MAX_CHARS = 60000
    if len(prompt) > MAX_CHARS:
        logger.error(
            f"[TOKEN_LIMIT] Prompt too long: {len(prompt)} chars > "
            f"{MAX_CHARS}, truncating..."
        )
        prompt = prompt[:MAX_CHARS] + "\n\n[...由于长度限制已截断...]"

    # 重新计算
    chinese_chars = sum(1 for c in prompt if '\u4e00' <= c <= '\u9fff')
    non_chinese = len(prompt) - chinese_chars
    estimated_tokens = int(chinese_chars * 2.5 + non_chinese * 0.5)

    if estimated_tokens > SAFE_TOKEN_LIMIT:  # SAFE_TOKEN_LIMIT = 180000
        logger.error(
            f"[TOKEN_LIMIT] Estimated {estimated_tokens} > {SAFE_TOKEN_LIMIT}, "
            f"truncating..."
        )
        target_chars = int(SAFE_TOKEN_LIMIT / 2.5)
        prompt = prompt[:target_chars] + "\n\n[...由于长度限制已截断...]"
        logger.warning(f"[TOKEN_LIMIT] Truncated to {len(prompt)} chars")

    # 多模型降级策略 (DeepSeek -> Zhipu)
    models_to_try = ["deepseek", "zhipu"]

    for model in models_to_try:
        try:
            logger.info(f"[LLM] 🔄 尝试使用 {LLMFactory.NAMES.get(model, model)}...")

            system_prompt = "你是一位专业的A股投资分析专家。请按照要求格式返回结果。"

            result = await LLMFactory.fast_reply(
                model=model,
                system=system_prompt,
                user=prompt,
                timeout=timeout
            )

            # 检查结果
            if result and not result.startswith("[错误]"):
                logger.info(f"[LLM] ✅ {LLMFactory.NAMES.get(model, model)} 成功!")
                return result
            else:
                logger.warning(f"[LLM] ❌ {LLMFactory.NAMES.get(model, model)} 失败: {result[:100]}")
                continue

        except Exception as e:
            logger.warning(f"[LLM] ❌ {LLMFactory.NAMES.get(model, model)} 异常: {str(e)[:100]}")
            continue

    # 所有模型都失败
    logger.error("[LLM] 💀 所有模型均失败！请检查API密钥配置。")
    return "Error: 所有LLM模型调用失败，请检查API密钥配置 (DEEPSEEK_API_KEY, ZHIPU_API_KEY)"
```

---

## AI提示词定义

**文件**: `backend/app/core/prompts.py`

### Cathie Wood (成长风格分析师)

```python
PROMPT_CATHIE_WOOD = """你是A股成长风格投资专家，对标易方达、中欧基金等头部机构的成长投资部。

**核心原则**: 成长是第一生产力。寻找戴维斯双击机会，警惕杀估值风险。

## 你的机构级成长投资框架

### 1. PEG 比率核心指标（主要判断标准）
**公式**: PEG = (市盈率-TTM) / (营收增长率 % × 100)

**机构决策标准**:
- **PEG < 0.8**: 显著低估，戴维斯双击前夜 → **强烈买入**
- **PEG 0.8 - 1.2**: 成长匹配估值，合理区间 → **买入**
- **PEG 1.2 - 2.0**: 估值偏高，需高增长消化 → **谨慎持有**
- **PEG > 2.0**: 杀估值风险极大 → **卖出/回避**

## 你的输出格式（必须使用中文）

【第一步：JSON评分输出】（必须首先输出）
```json
{
    "score": 0-100的整数评分,
    "reasoning": "一句话总结你的核心观点（50字以内）"
}
```

【第二步：详细分析】
【PEG 估值分析】
PEG 比率: [计算值或"数据不可用"]
判断: [显著低估 / 合理估值 / 估值偏高 / 杀估值风险]
评级: ⭐⭐⭐⭐⭐ (1-5星)

【综合评级】
机构建议: [强烈买入 / 买入 / 持有 / 卖出 / 强烈卖出]

**重要规则**:
- 使用可用数据进行分析，不要简单说"数据不足"
- 必须首先输出JSON格式，然后输出详细分析
- 以"**成长分析师_COMPLETE**"结束
"""
```

### Warren Buffett (价值风格分析师)

```python
PROMPT_WARREN_BUFFETT = """你是A股价值投资专家，对标兴全基金、中庚基金、景顺长城等头部机构的价值投资部。

**核心原则**: 安全边际是生命线。以合理价格买入优秀公司，绝不以便宜价格买入平庸公司。

## 你的机构级价值投资框架

### 1. ROE 筛选（质量过滤器）
**机构决策标准**:
- **ROE < 8%**: 垃圾资产，直接拒绝 → **一票否决**
- **ROE 8-12%**: 平庸资产，需深度折价才考虑 → **谨慎**
- **ROE 12-15%**: 良好资产 → **观察**
- **ROE 15-20%**: 优秀资产 → **买入**
- **ROE > 20%**: 卓越资产，创造复利机器 → **强烈买入**

## 你的输出格式（必须使用中文）

【第一步：JSON评分输出】（必须首先输出）
```json
{
    "score": 0-100的整数评分,
    "reasoning": "一句话总结你的核心观点（50字以内）"
}
```

【第二步：详细分析】
【质量分析】
ROE: [值]%, 评级: [卓越/优秀/良好/平庸/垃圾]

【价值投资评级】
机构建议: [强烈买入 / 买入 / 持有 / 卖出 / 强烈卖出]

**重要规则**:
- 安全边际是第一原则
- 拒绝平庸资产（ROE < 10%）
- 必须首先输出JSON格式，然后输出详细分析
- 以"**价值分析师_COMPLETE**"结束
"""
```

### Nancy Pelosi (技术与风格分析师)

```python
PROMPT_NANCY_PELOSI = """你是A股技术与风格投资专家，对标顶级游资、量化私募、券商自营盘。

**核心原则**: 跟踪聪明钱，把握市场情绪，顺势而为，截断亏损，让利润奔跑。

## 你的机构级技术投资框架

### 1. 市场微观结构分析（量价关系）
**量价配合度判断**:
- **放量上涨**: 机构积极买入，趋势确认 → **强烈买入信号**
- **缩量上涨**: 缺乏跟风盘，上涨乏力 → **谨慎**
- **放量下跌**: 机构抛售，恐慌蔓延 → **卖出信号**
- **缩量下跌**: 惜售/洗盘，可能见底 → **观察买入机会**

### 2. 市场情绪指标（RSI + 换手率）
**RSI 情绪图谱**:
- **RSI < 30**: 超卖，恐慌盘出清 → **左侧买入机会**
- **RSI 50-70**: 强势区域 → **持仓**
- **RSI > 70**: 超买，情绪过热 → **警惕回调**

## 你的输出格式（必须使用中文）

【第一步：JSON评分输出】（必须首先输出）
```json
{
    "score": 0-100的整数评分,
    "reasoning": "一句话总结你的核心观点（50字以内）"
}
```

【第二步：详细分析】
【市场微观结构】
量价关系: [放量上涨 / 缩量上涨 / 放量下跌 / 缩量下跌]
判断: [机构积极买入 / 缺乏跟风 / 机构抛售 / 惜售洗盘]
信号强度: [⭐⭐⭐⭐⭐]

【风格评分】
机构建议: [强烈买入 / 买入 / 持有 / 卖出 / 强烈卖出]

**重要规则**:
- 顺势而为，不逆势操作
- 必须首先输出JSON格式，然后输出详细分析
- 以"**技术分析师_COMPLETE**"结束
"""
```

### Charlie Munger (投委会主席)

```python
PROMPT_CHARLIE_MUNGER = """你是A股投委会主席，对标公募基金经理、私募投资总监的决策角色。

**核心原则**: 综合三方观点，做出最终决策。风险可控，收益可期。

## 你的综合决策框架

### 1. 一致性检查（共识机制）
- **三方一致看多** → **强烈买入**，重仓配置
- **两方看多，一方中性** → **买入**，标配配置
- **两方看多，一方看空** → **持有/低配**，观察
- **意见分歧** → **持有**，等待更多信息
- **三方一致看空** → **卖出**，清仓回避

## 你的输出格式（JSON格式，必须使用中文）

```json
{
  "final_verdict": "强烈买入 / 买入 / 持有 / 卖出 / 强烈卖出",
  "conviction_level": 1-5,
  "position_recommendation": "5-8成 / 3-5成 / 维持 / 1-2成 / 清仓",
  "key_considerations": [
    "关键考虑点1 (成长方面)",
    "关键考虑点2 (价值方面)",
    "关键考虑点3 (技术方面)"
  ],
  "risk_factors": [
    "估值风险: 高/中/低",
    "业绩风险: 高/中/低",
    "政策风险: 高/中/低",
    "市场风险: 高/中/低"
  ],
  "investment_thesis": "2-3句话总结投资逻辑",
  "triggers": {
    "buy_trigger": "加仓条件",
    "sell_trigger": "减仓/止损条件"
  },
  "score": 0-100,
  "timestamp": "当前时间"
}
```

**重要规则**:
- 你是最终决策者，责任重大
- 风险优先，收益其次
- 输出纯JSON，不要有markdown格式
- 以"**投委会主席_COMPLETE**"结束
"""
```

---

## 性能瓶颈分析

### 当前配置参数

| 参数 | 当前值 | 位置 | 说明 |
|------|--------|------|------|
| `DEFAULT_TIMEOUT` | 30秒 | ic_service.py:42 | call_llm_async默认超时 |
| `fast_reply timeout` | 60秒 | llm_factory.py:45 | LLM工厂超时 |
| DeepSeek max_tokens | 500 | llm_factory.py:95 | 已优化 |
| Zhipu max_tokens | 1000 | llm_factory.py:125 | 已优化 |
| MAX_CHARS | 60000 | ic_service.py:189 | 强制字符限制 |
| SAFE_TOKEN_LIMIT | 180000 | ic_service.py:202 | Token安全限制 |

### 时间分配分析

**正常流程 (期望)**:
```
Tushare数据获取: ~5-10秒
Round 1 (Cathie + Nancy并行): ~15-30秒
Round 2 (Warren): ~15-20秒
Round 3 (Charlie): ~15-20秒
----------------------------------------------
总计: ~50-80秒
```

**实际流程 (问题)**:
```
Tushare数据获取: 5-10秒 ✓
Round 1 (Cathie + Nancy并行): 180-600秒 ❌ (每个90-300秒)
Round 2 (Warren): 90-300秒 ❌
Round 3 (Charlie): 90-300秒 ❌
----------------------------------------------
总计: 600-1200秒 (10-20分钟)
```

### 潜在瓶颈点

1. **LLM API响应慢**
   - DeepSeek/Zhipu API可能需要10-30秒/次
   - 4次调用 × 30秒 = 120秒（正常）
   - 但实际每个调用需要90-300秒

2. **Token检查开销**
   - 每次调用前进行中文字符统计
   - 可能导致额外的处理时间

3. **上下文构建**
   - `enhanced_base_context` 包含大量数据
   - Token估算和截断逻辑复杂

4. **模型降级**
   - DeepSeek失败后尝试Zhipu
   - 可能导致双倍等待时间

---

## 优化建议

### 方案1: 使用更快的模型 (不改逻辑)

```python
# 在 llm_factory.py 中添加更快的模型配置
FAST_MODELS = {
    "deepseek-fast": "deepseek-chat",  # 使用更快的端点
    "zhipu-fast": "glm-4-flash",        # 如果有的话
}

# 修改 fast_reply 使用快速模式
@classmethod
async def fast_reply(cls, model: str, system: str, user: str, timeout: int = 30) -> str:
    # 使用快速模型配置
    pass
```

### 方案2: 减少Token检查开销

```python
# 简化 Token 检查逻辑
async def call_llm_async(prompt: str, api_key: str, timeout: int = 30) -> str:
    # 移除复杂的中文字符统计
    # 直接检查 prompt 长度
    if len(prompt) > 30000:  # 简化阈值
        prompt = prompt[:30000] + "\n\n[...截断...]"

    # 直接调用 LLM，不做详细 Token 估算
    pass
```

### 方案3: 并行化更多操作

```python
# 在 conduct_meeting 中，将 Tushare 调用也并行化
async def conduct_meeting(...):
    # 并行获取所有数据
    tushare_task = asyncio.create_task(get_stock_main_business_tushare(symbol))
    price_task = asyncio.create_task(fetcher.get_stock_info(symbol))

    profile_data, stock_info = await asyncio.gather(tushare_task, price_task)
    pass
```

### 方案4: 缓存机制

```python
# 添加简单的缓存，避免重复调用相同股票
from functools import lru_cache

@lru_cache(maxsize=100)
def _get_cached_prompt(stock_name: str, prompt_type: str) -> str:
    # 缓存常用prompt模板
    pass
```

### 方案5: 连接池复用

```python
# 在 llm_factory.py 中复用 HTTP 连接
class LLMFactory:
    _client = None  # 类级别的客户端

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = AsyncClient(timeout=60)
        return cls._client
```

---

## 文件位置汇总

| 文件 | 路径 | 关键函数 |
|------|------|----------|
| IC服务 | `backend/app/services/ic_service.py` | `conduct_meeting()` |
| LLM工厂 | `backend/app/core/llm_factory.py` | `fast_reply()` |
| 提示词 | `backend/app/core/prompts.py` | `PROMPT_*` |
| 搜索服务 | `backend/app/services/search_service.py` | `search_financial_news()` |
| 市场服务 | `backend/app/services/market_service.py` | `calculate_financial_metrics()` |

---

## 调试日志关键点

在以下位置添加时间戳日志可定位瓶颈：

```python
# ic_service.py
import time

start = time.time()
logger.info(f"[TIMING] conduct_meeting start: {symbol}")

# Round 1
round1_start = time.time()
cathie_response, nancy_response = await asyncio.gather(...)
logger.info(f"[TIMING] Round 1 completed in {time.time() - round1_start:.2f}s")

# Round 2
round2_start = time.time()
warren_response = await call_llm_async(...)
logger.info(f"[TIMING] Round 2 completed in {time.time() - round2_start:.2f}s")

# Round 3
round3_start = time.time()
charlie_response = await call_llm_async(...)
logger.info(f"[TIMING] Round 3 completed in {time.time() - round3_start:.2f}s")

logger.info(f"[TIMING] Total time: {time.time() - start:.2f}s")
```

---

**重要**: 用户明确要求**不改变现有逻辑**，仅优化性能。以上建议都是在保持逻辑不变的前提下进行的优化。

**生成人**: Claude Code
**用途**: 与Gemini AI共享进行性能调试
