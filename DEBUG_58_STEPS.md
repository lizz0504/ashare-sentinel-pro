# A股Sentinel Pro - 58步骤性能问题

## 问题描述

**症状**：前端调用后端 `/api/v1/ic/meeting` API 分析股票时，出现 `0/58` 到 `58/58` 的进度条，每步耗时 10-30 秒，总共需要 10-20 分钟。

**日志输出**：
```
[stderr]   0%|          | 0/58 [00:00<?, ?it/s]
[stderr]   2%|          | 1/58 [00:09<09:23,  9.88s/it]
[stderr]   3%|          | 2/58 [00:15<06:57,  7.45s/it]
...
```

**出现时机**：在 Tushare 数据获取完成后，LLM 调用阶段出现

```
[OK] Tushare complete data, skipping other sources
[stderr]   0%|          | 0/58 [00:00<?, ?it/s]  <-- 这里开始
```

---

## 关键代码文件

### 1. IC 投委会服务入口

**文件**: `backend/app/services/ic_service.py`

**关键函数**: `conduct_meeting()` (第 413-896 行)

**执行流程**:
```python
async def conduct_meeting(
    symbol: str,
    stock_name: str,
    current_price: float,
    context: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    # 准备数据
    # ...

    # Round 1: 并行执行 Cathie Wood + Nancy Pelosi (2个LLM调用)
    cathie_task = call_llm_async(...)
    nancy_task = call_llm_async(...)
    cathie_response, nancy_response = await asyncio.gather(
        cathie_task, nancy_task
    )

    # Round 2: Warren Buffett (1个LLM调用)
    warren_response = await call_llm_async(...)

    # Round 3: Charlie Munger (1个LLM调用)
    charlie_response = await call_llm_async(...)

    # 总共应该是 4 次 LLM 调用，而不是 58 次！
```

**可能的问题点**：
- 第 554 行：`news_result = await search_financial_news(symbol, stock_name, max_results=5)`

---

### 2. LLM 调用工厂

**文件**: `backend/app/core/llm_factory.py`

**关键代码**:
```python
class LLMFactory:
    APIS = {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    }

    @classmethod
    async def fast_reply(
        cls,
        model: str,
        system: str,
        user: str,
        timeout: int = 30
    ) -> str:
        caller = {
            "deepseek": cls._call_deepseek,
            "zhipu": cls._call_zhipu
        }.get(model)

        return await caller(system, user, timeout)

    @classmethod
    async def _call_zhipu(cls, system: str, user: str, timeout: int) -> str:
        api_key = getattr(settings, 'ZHIPU_API_KEY', None)

        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        payload = {
            "model": "glm-4",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": 8000,  # <-- 注意这个设置
            "temperature": 0.6
        }

        async with AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
```

**可能的问题点**：
- `max_tokens=8000` 可能导致进度条显示 8000/某个数值？
- `AsyncClient` 可能有内置的进度显示？

---

### 3. Tavily 搜索服务

**文件**: `backend/app/services/search_service.py`

**关键函数**: `search_financial_news()` (第 375-783 行)

**执行流程**:
```python
async def search_financial_news(
    symbol: str,
    stock_name: str,
    max_results: int = 10
) -> Dict:
    # 定义 5 个查询
    search_queries = [
        f'({stock_name} {symbol}) (最新 消息 动态 公告)',
        f'({stock_name} {symbol}) (研报 评级 目标价 买入 卖出)',
        f'({stock_name} {symbol}) (业绩 预告 快报 中报 年报)',
        f'({stock_name} {symbol}) (重组 并购 分红 定增 回购)',
        f'({stock_name}) 投资者关系 活动 路演 调研'
    ]

    # 并行执行 5 个查询
    results_per_query = await asyncio.gather(
        _execute_single_search(client, search_queries[0], max_results, days_window),
        _execute_single_search(client, search_queries[1], max_results, days_window),
        _execute_single_search(client, search_queries[2], max_results, days_window),
        _execute_single_search(client, search_queries[3], max_results, days_window),
        _execute_single_search(client, search_queries[4], max_results, days_window)
    )

    # 每个查询可能返回多条结果，然后遍历处理
    for query_idx, query_results in enumerate(results_per_query):
        for result in query_results:
            # 处理每条结果...
            # 5 个查询 * max_results (5-10条) = 25-50 次迭代？
```

**可能的问题点**：
- 5 个查询，每个返回多条结果
- 内部循环处理可能导致 58 次迭代？
- `search_financial_news` 在 `ic_service.py:554` 被调用

---

### 4. 主程序配置

**文件**: `backend/app/main.py` (第 8-17 行)

**已尝试的修复**:
```python
# 禁用 tqdm 和进度条（解决 58 步骤问题）
import os
os.environ['TQDM_DISABLE'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['DASHSCOPE_DISABLE_PROGRESS_BAR'] = '1'
os.environ['DASHSCOPE_SHOW_PROGRESS_BAR'] = 'False'

# 加载 .env 文件 (必须在其他导入之前)
from dotenv import load_dotenv
load_dotenv()
```

**效果**: ❌ 进度条仍然出现

---

## 调试建议

### 需要检查的关键点

1. **进度条的确切来源**
   - 在 `ic_service.py` 的每个关键步骤添加日志，确定 58 步骤出现在哪个阶段
   - 检查是否是 Tavily SDK、httpx 或某个 LLM SDK 的内置进度条

2. **Tavily 搜索结果处理**
   - `search_service.py:466-563` 有嵌套循环处理搜索结果
   - 可能是 5 个查询 × 约 10 条结果/查询 = 约 50 次处理

3. **LLM API 响应格式**
   - DeepSeek/Zhipu API 是否使用流式响应？
   - `max_tokens=8000` 可能导致 8000/某数值 的进度显示？

4. **httpx 库配置**
   - `AsyncClient` 是否有进度显示功能？
   - 尝试添加 `disable_progress_bar=True` 参数（如果有）

### 建议的调试步骤

**步骤 1**: 在 `ic_service.py` 添加更详细的日志

```python
# 在 conduct_meeting() 函数中添加：
logger.info("[DEBUG] Before Tavily search")
news_result = await search_financial_news(symbol, stock_name, max_results=5)
logger.info("[DEBUG] After Tavily search")

logger.info("[DEBUG] Before Round 1 LLM calls")
cathie_task = call_llm_async(...)
# ... 其他 LLM 调用
logger.info("[DEBUG] After Round 1 LLM calls")
```

**步骤 2**: 检查是否是 Tavily SDK 的问题

```python
# 在 search_service.py 的 search_financial_news() 中添加：
print(f"[SEARCH DEBUG] About to execute {len(search_queries)} queries")
print(f"[SEARCH DEBUG] Before asyncio.gather")
results_per_query = await asyncio.gather(...)
print(f"[SEARCH DEBUG] After asyncio.gather, got {len(results_per_query)} results")
```

**步骤 3**: 检查 LLM API 调用

```python
# 在 llm_factory.py 的 _call_zhipu() 中添加：
print(f"[LLM DEBUG] Before API call to {url}")
print(f"[LLM DEBUG] Payload length: {len(str(payload))}")
r = await client.post(url, headers=headers, json=payload)
print(f"[LLM DEBUG] After API call, status: {r.status_code}")
```

---

## 环境信息

- **Python 版本**: 3.x
- **后端**: FastAPI + Uvicorn
- **前端**: Next.js 15
- **主要依赖**:
  - httpx (HTTP 客户端)
  - tavily-python (搜索)
  - tushare (数据)
  - 自定义 LLM Factory (DeepSeek/Zhipu)

---

## 期望行为

**正常流程应该是**:
1. Tushare 数据获取: ~5 秒
2. Tavily 新闻搜索: ~10 秒 (5 个并行查询)
3. Round 1 LLM (Cathie + Nancy): ~30 秒 (并行)
4. Round 2 LLM (Warren): ~20 秒
5. Round 3 LLM (Charlie): ~20 秒

**总时间**: 约 85 秒 (1.5 分钟)

**实际时间**: 10-20 分钟 (58 步骤 × 10-30 秒/步)

---

## 下一步

请根据以上信息：

1. **定位进度条来源** - 在哪个函数的哪一行开始显示 `0/58`
2. **检查第三方库** - Tavily、httpx、Zhipu SDK 是否有内置进度条
3. **验证循环逻辑** - 确认是否有意外的循环或重复调用

如果需要更多信息，请查看：
- 后端完整日志: `C:\Users\lohas\AppData\Local\Temp\claude\d--CC-CODE-AShare-Sentinel-Pro\tasks\b45bef6.output`
- 前端配置: `frontend/.env.local` (API_URL: http://localhost:8000)
- 后端配置: `backend/.env` (API keys 和 CORS 设置)
