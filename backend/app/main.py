"""
Fintech Platform - Backend API
FastAPI Application Entry Point
"""
# flake8: noqa: E501


# ============================================================================
# 全局禁用 tqdm 和所有进度条（解决 Tushare SDK 的 58 步骤问题）
# ============================================================================
import os
import sys
import io

# 设置环境变量
os.environ['TQDM_DISABLE'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 强制设置标准输出为 UTF-8 (解决 Windows GBK 编码问题)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 创建一个完全静默的 tqdm 模块
class _SilentTqdm:
    """完全静默的 tqdm 替代品"""
    def __init__(self, iterable=None, *args, **kwargs):
        self.iterable = iterable
        self.n = 0

    def __iter__(self):
        if self.iterable is not None:
            return iter(self.iterable)
        return iter([])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, n=1):
        self.n += n

    def close(self):
        pass

    def set_description(self, desc=None):
        pass

    def refresh(self):
        pass

    def write(self, s, file=sys.stdout, end='\n'):
        pass

    @property
    def format_dict(self):
        return {}

# 在任何导入之前替换 tqdm
sys.modules['tqdm'] = type('Module', (), {
    'tqdm': _SilentTqdm,
    'trange': lambda *a, **k: _SilentTqdm(),
    'tqdm_gui': _SilentTqdm,
    'tqdm_notebook': _SilentTqdm,
    'autonotebook': lambda *a, **k: None,
    '__version__': '0.0.0'
})()
sys.modules['tqdm.gui'] = type('Module', (), {'tqdm': _SilentTqdm})()
sys.modules['tqdm.auto'] = type('Module', (), {'tqdm': _SilentTqdm})()
sys.modules['tqdm.notebook'] = type('Module', (), {'tqdm': _SilentTqdm})()

# 加载 .env 文件 (必须在其他导入之前)
from dotenv import load_dotenv
load_dotenv()

# 标准库导入
import uuid # noqa: F401
import asyncio # noqa: F401
import logging
from typing import Literal, Optional

# 第三方库导入
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 应用导入
from app.core.config import settings
from app.deps import get_current_user, get_current_user_optional
from app.services.ocr_service import process_pdf
from app.services.llm_service import generate_chat_response, classify_stock, generate_portfolio_review
from app.services.market_service import (
    get_stock_info,
    get_weekly_performance,
    validate_symbol,
    get_market_sentiment,
    get_stock_technical_analysis,
    calculate_financial_metrics
)
from app.services.market_service_baostock import get_financials_baostock
from app.services.ic_service import conduct_meeting, format_ic_meeting_summary, get_ic_recommendation_summary
from app.services.committee_service import CommitteeService
from app.core.db import get_db_client

# 配置日志根logger
# 确保日志文件使用 UTF-8 编码
_file_handler = logging.FileHandler(settings.LOG_FILE_PATH, encoding='utf-8')
_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, "INFO"),
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[_file_handler]
)

logger = logging.getLogger(__name__)

# ============================================
# Application Configuration
# ============================================
app = FastAPI(
    title="Fintech Platform API",
    description="Investment Research & Intelligence Platform",
    version="1.0.0",
)

# CORS 中间件 - 从配置读取
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    """记录所有请求"""
    import sys
    import time
    import traceback

    start_time = time.time()

    # 写入文件以确保输出
    try:
        # 确保日志目录存在
        import os
        log_dir = os.path.dirname(settings.LOG_FILE_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        with open(settings.LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(f"[{time.time()}] {request.method} {request.url}\n")
            f.flush()
    except Exception as e:
        print(f"[ERROR] Failed to write to log: {e}", flush=True)

    print(f"[REQUEST] {request.method} {request.url}", flush=True)
    sys.stdout.flush()

    try:
        response = await call_next(request)
    except Exception as e:
        print(f"[ERROR] Request failed: {e}", flush=True)
        traceback.print_exc()
        # Return error response
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "detail": traceback.format_exc()}
        )

    process_time = (time.time() - start_time) * 1000
    print(f"[RESPONSE] {request.method} {request.url} - {response.status_code} ({process_time:.0f}ms)", flush=True)

    try:
        with open(settings.LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(f"[{time.time()}] {request.method} {request.url} - {response.status_code} ({process_time:.0f}ms)\n")
            f.flush()
    except Exception as e:
        print(f"[ERROR] Failed to write to log: {e}", flush=True)

    return response


# ============================================
# Response Models
# ============================================
class UploadResponse(BaseModel):
    """文件上传响应模型"""
    status: Literal["queued", "processing", "completed", "failed"]
    task_id: str
    filename: str
    size: int
    message: str | None = None


class ChatRequest(BaseModel):
    """聊天请求模型"""
    report_id: str
    query: str
    match_threshold: float = 0.1  # 降低阈值以便更容易匹配
    match_count: int = 5


class ChatResponse(BaseModel):
    """聊天响应模型"""
    answer: str
    report_id: str
    query: str


# ============================================
# Portfolio Management Models
# ============================================
class AddStockRequest(BaseModel):
    """添加股票请求模型"""
    symbol: str
    cost_basis: float | None = None
    shares: int = 1
    notes: str | None = None


class PortfolioItem(BaseModel):
    """投资组合项目模型"""
    id: str
    symbol: str
    name: str | None
    sector: str | None
    industry: str | None
    cost_basis: float | None
    shares: int
    notes: str | None
    created_at: str
    updated_at: str
    # 持久化字段（缓存最后一次技术分析数据）
    last_price: float | None = None
    last_health_score: int | None = None
    last_updated_at: str | None = None
    # 技术分析详细字段（用于完整显示，避免 Phase 2 重复请求）
    tech_ma20_status: str | None = None
    tech_ma5_status: str | None = None
    tech_volume_status: str | None = None
    tech_volume_change_pct: float | None = None
    tech_alpha: float | None = None
    tech_k_line_pattern: str | None = None
    tech_pattern_signal: str | None = None
    tech_action_signal: str | None = None
    tech_analysis_date: str | None = None


class PortfolioResponse(BaseModel):
    """投资组合响应模型"""
    items: list[PortfolioItem]
    grouped: dict[str, list[PortfolioItem]]  # 按板块分组


class DeleteStockResponse(BaseModel):
    """删除股票响应模型"""
    success: bool
    message: str


class GenerateReviewRequest(BaseModel):
    """生成复盤请求模型"""
    portfolio_id: str
    days: int = 7


class WeeklyReviewResponse(BaseModel):
    """週度复盤响应模型"""
    id: str
    portfolio_id: str
    review_date: str
    start_price: float
    end_price: float
    price_change_pct: float
    ai_analysis: str


class ICMeetingRequest(BaseModel):
    """AI投委会会议请求模型"""
    symbol: str
    stock_name: str | None = None
    current_price: float | None = None
    industry: str | None = None
    market_cap: str | None = None
    pe_ratio: str | None = None
    pb_ratio: str | None = None
    roe: str | None = None
    revenue_growth: str | None = None
    peg_ratio: str | None = None
    debt_to_equity: str | None = None
    rd_intensity: str | None = None
    beta: str | None = None
    rsi_14: str | None = None
    fcf_yield: str | None = None
    save_to_db: bool = False  # 是否保存到数据库（自动归档）


class ICMeetingResponse(BaseModel):
    """AI投委会会议响应模型"""
    symbol: str
    stock_name: str
    current_price: float
    verdict_chinese: str
    conviction_stars: str
    cathie_wood: str
    nancy_pelosi: str
    warren_buffett: str
    final_verdict: dict
    summary: str
    technical_score: int | None = None
    fundamental_score: int | None = None
    # NEW: 添加角色评分和Dashboard坐标
    agent_scores: dict | None = None
    dashboard_position: dict | None = None


# ============================================
# Committee Service Models (三方博弈)
# ============================================
class CommitteeRequest(BaseModel):
    """三方博弈请求模型"""
    symbol: str


class CommitteeResponse(BaseModel):
    """三方博弈响应模型"""
    symbol: str
    timestamp: str
    fundamentals: dict
    debate: dict
    conclusion: dict



# ============================================
# API Endpoints
# ============================================
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "Fintech Platform API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


@app.post("/api/v1/analyze/upload", response_model=UploadResponse)
async def upload_research_report(file: UploadFile = File(...)):
    """
    上传研报文件进行分析

    Args:
        file: 上传的文件（PDF）

    Returns:
        UploadResponse: 包含任务 ID 和状态的响应
    """
    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)

    # 生成任务 ID
    task_id = str(uuid.uuid4())

    # 直接同步处理（临时方案，确保能工作）
    print(f"[DEBUG] Processing file: {file.filename}, size: {file_size}")
    try:
        report_id = process_pdf(file_content, file.filename or "unknown.pdf")
        print(f"[DEBUG] Processing completed, report_id: {report_id}")
    except Exception as e:
        print(f"[DEBUG] Processing failed: {e}")
        import traceback
        traceback.print_exc()

    return UploadResponse(
        status="processing",
        task_id=task_id,
        filename=file.filename,
        size=file_size,
        message="File uploaded successfully. Processing started.",
    )


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_with_report(request: ChatRequest):
    """
    与研报进行对话（RAG 功能）

    Args:
        request: 包含 report_id、query 和可选参数的请求体

    Returns:
        ChatResponse: 包含 AI 生成的回答
    """
    print(f"[INFO] Chat request for report {request.report_id}: {request.query[:50]}...")

    answer = generate_chat_response(
        report_id=request.report_id,
        query=request.query,
        match_threshold=request.match_threshold,
        match_count=request.match_count,
    )

    if not answer:
        return ChatResponse(
            answer="抱歉，生成回答时出现错误，请稍后重试。",
            report_id=request.report_id,
            query=request.query,
        )

    return ChatResponse(
        answer=answer,
        report_id=request.report_id,
        query=request.query,
    )


# ============================================
# Portfolio Management Endpoints
# ============================================

@app.post("/api/v1/portfolio", response_model=PortfolioItem)
async def add_stock(request: AddStockRequest):
    """
    添加股票到投资组合

    流程：
    1. 使用 AkShare 获取股票信息
    2. 使用 AI 分类为中文板块和行业
    3. 保存到数据库
    """
    print(f"[INFO] Adding stock to portfolio: {request.symbol}")

    # 获取股票信息（如果 AkShare 失败，使用默认值）
    stock_info = get_stock_info(request.symbol)
    if not stock_info:
        print(f"[WARN] Failed to fetch stock info for {request.symbol}, using defaults")
        # 使用默认值，允许用户继续
        stock_info = {
            "symbol": request.symbol.upper(),
            "name": request.symbol.upper(),
            "sector_en": "Unknown",
            "industry_en": "Unknown",
            "current_price": None,
            "currency": "USD",
            "market_cap": None,
            "description": "",
        }

    # AI 分类（如果 sector/industry 是 Unknown，仍然尝试分类）
    classification = classify_stock(
        symbol=stock_info["symbol"],
        name=stock_info["name"],
        sector_en=stock_info["sector_en"],
        industry_en=stock_info["industry_en"]
    )

    # 保存到数据库
    from utils.db_helper import safe_insert
    from utils.constants import MSG_STOCK_ADDED, ERR_FAILED_SAVE_STOCK

    portfolio_data = {
        "symbol": stock_info["symbol"],
        "name": stock_info["name"],
        "sector": classification["sector_cn"],
        "industry": classification["industry_cn"],
        "cost_basis": request.cost_basis,
        "shares": request.shares,
        "notes": request.notes,
    }

    result_data = safe_insert("portfolio", portfolio_data)

    if result_data:
        item = result_data[0]
        print(MSG_STOCK_ADDED.format(symbol=item['symbol']))
        return PortfolioItem(**item)
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=ERR_FAILED_SAVE_STOCK)


@app.get("/api/v1/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """
    获取投资组合列表（按板块分组）

    Returns:
        所有股票及其按板块分组的视图
    """
    import time
    start_time = time.time()
    print(f"[INFO] ===== Portfolio GET request received at {time.strftime('%H:%M:%S.%f')[:-3]} =====")

    db = get_db_client()
    try:
        # 获取所有股票
        from utils.db_helper import safe_select
        query_start = time.time()
        result_data = safe_select("portfolio", order_by="created_at", desc=True)
        if result_data is None:
            result_data = []
        query_time = time.time() - query_start
        print(f"[INFO] Database query took: {query_time:.3f}s, returned {len(result_data)} rows")

        items = []
        for item_data in result_data:
            item = PortfolioItem(**item_data)

            # 如果股票缺少名称或行业为"其他"，尝试从AkShare更新
            # 注意：暂时禁用自动更新，避免外部服务连接问题导致接口失败
            if False and (not item.name or item.sector in [None, "其他", "未分类"]):
                try:
                    from app.services.market_service import get_stock_info
                    print(f"[INFO] Updating stock info for {item.symbol}...")

                    stock_info = get_stock_info(item.symbol, fetch_price=False)
                    if stock_info:
                        # 更新数据库
                        update_data = {
                            "name": stock_info.get("name", item.name),
                            "sector": stock_info.get("sector_en", item.sector),
                            "industry": stock_info.get("industry_en", item.industry)
                        }
                        # 更新数据库
                        from utils.db_helper import safe_update
                        update_success = safe_update("portfolio", update_data, {"id": item.id})
                        if update_success:
                            # 更新当前对象
                            item.name = update_data["name"]
                            item.sector = update_data["sector"]
                            item.industry = update_data["industry"]

                            print(f"[OK] Updated {item.symbol}: {item.name}")
                except Exception as e:
                    print(f"[WARN] Failed to update {item.symbol}: {e}")

            items.append(item)

        # 按板块分组
        grouped = {}
        for item in items:
            sector = item.sector or "未分类"
            if sector not in grouped:
                grouped[sector] = []
            grouped[sector].append(item)

        print(f"[OK] Retrieved {len(items)} stocks in {len(grouped)} sectors")

        return PortfolioResponse(items=items, grouped=grouped)

    except Exception as e:
        print(f"[ERROR] Failed to fetch portfolio: {e}")
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/portfolio/{portfolio_id}", response_model=DeleteStockResponse)
async def delete_stock(portfolio_id: str):
    """
    从投资组合中删除股票
    """
    print(f"[INFO] Deleting stock: {portfolio_id}")

    from utils.db_helper import safe_delete
    from utils.constants import ERR_FAILED_SAVE_STOCK

    delete_success = safe_delete("portfolio", {"id": portfolio_id})

    if delete_success:
        print(f"[OK] Stock deleted: {portfolio_id}")
        return DeleteStockResponse(success=True, message="Stock deleted successfully")
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Stock not found")


@app.post("/api/v1/portfolio/review", response_model=WeeklyReviewResponse)
async def generate_weekly_review(request: GenerateReviewRequest):
    """
    生成週度复盤

    流程：
    1. 获取股票信息
    2. 使用 AkShare 获取週度价格变化
    3. 使用 AI 生成复盤分析
    4. 保存到数据库
    """
    print(f"[INFO] Generating review for portfolio: {request.portfolio_id}")

    db = get_db_client()
    try:
        # 获取股票
        from utils.db_helper import safe_select
        portfolio_result_data = safe_select("portfolio", {"id": request.portfolio_id}, order_by=None)

        if not portfolio_result_data:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Stock not found")

        stock = portfolio_result_data[0]
        symbol = stock["symbol"]
        name = stock["name"]
        sector = stock["sector"]

        # 获取週度表現
        performance = get_weekly_performance(symbol, days=request.days)
        if not performance:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Failed to fetch stock performance")

        # 获取技术分析数据（仅 A 股支持）
        technical_data = None
        try:
            from app.services.market_service import get_stock_technical_analysis
            technical_data = get_stock_technical_analysis(symbol)
            print(f"[INFO] Technical analysis for {symbol}: health_score={technical_data.get('health_score') if technical_data else 'N/A'}")
        except Exception as e:
            print(f"[WARN] Failed to get technical analysis: {e}")

        # AI 生成复盤（返回结构化数据）
        review_data = generate_portfolio_review(
            symbol=symbol,
            name=name,
            sector=sector,
            start_price=performance["start_price"],
            end_price=performance["end_price"],
            price_change_pct=performance["price_change_pct"],
            period_days=request.days,
            technical_data=technical_data
        )

        # 将结构化数据转换为文本保存
        analysis_text = f"""{review_data.get('analysis', '')}

健康评分: {review_data.get('health_score', 'N/A')}/100
操作信号: {review_data.get('action_signal', 'N/A')}
"""

        # 保存到数据库
        from datetime import datetime, date
        review_date = date.today()

        review_result = db.table("weekly_reviews").insert({
            "portfolio_id": request.portfolio_id,
            "review_date": review_date.isoformat(),
            "start_price": performance["start_price"],
            "end_price": performance["end_price"],
            "price_change_pct": performance["price_change_pct"],
            "ai_analysis": analysis_text,
        }).execute()

        if review_result.data:
            review = review_result.data[0]
            print(f"[OK] Review generated: {review['id']}")
            return WeeklyReviewResponse(**review)
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Failed to save review")

    except Exception as e:
        print(f"[ERROR] Failed to generate review: {e}")
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/portfolio/{portfolio_id}/reviews", response_model=list[WeeklyReviewResponse])
async def get_stock_reviews(portfolio_id: str):
    """
    获取股票的所有週度复盤
    """
    print(f"[INFO] Fetching reviews for: {portfolio_id}")

    db = get_db_client()
    try:
        from utils.db_helper import safe_select
        result_data = safe_select("weekly_reviews", {"portfolio_id": portfolio_id}, order_by="review_date", desc=True)
        if result_data is None:
            result_data = []

        reviews = [WeeklyReviewResponse(**item) for item in result_data]
        print(f"[OK] Retrieved {len(reviews)} reviews")

        return reviews

    except Exception as e:
        print(f"[ERROR] Failed to fetch reviews: {e}")
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Market Analysis Endpoints
# ============================================

@app.get("/api/v1/market/sentiment")
async def get_market_sentiment_endpoint():
    """
    获取市场贪婪指数（基于沪深300 RSI）
    """
    print(f"[INFO] Fetching market sentiment")

    try:
        sentiment = get_market_sentiment()
        if not sentiment:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Market sentiment data unavailable")

        print(f"[OK] Market sentiment: {sentiment['label']}")
        return sentiment

    except Exception as e:
        print(f"[ERROR] Failed to fetch market sentiment: {e}")
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


def update_portfolio_persistent_data(symbol: str, technical_data: dict) -> bool:
    """
    异步更新投资组合的持久化数据（不阻塞主流程）

    当技术分析接口请求成功后，将完整的技术分析数据持久化到 Supabase
    """
    try:
        from utils.db_helper import safe_select, safe_update
        from datetime import datetime

        result_data = safe_select("portfolio", {"symbol": symbol}, order_by=None)

        if result_data:
            portfolio_id = result_data[0]["id"]

            # 将 health_score 转换为整数（数据库字段是 integer 类型）
            health_score = technical_data.get("health_score", 0)
            if health_score is not None:
                health_score = int(health_score)

            # 准备完整的更新数据
            update_data = {
                # 基础字段
                "last_price": technical_data.get("current_price"),
                "last_health_score": health_score,
                "last_updated_at": datetime.now().isoformat(),
                # 技术分析详细字段
                "tech_ma20_status": technical_data.get("ma20_status"),
                "tech_ma5_status": technical_data.get("ma5_status"),
                "tech_volume_status": technical_data.get("volume_status"),
                "tech_volume_change_pct": technical_data.get("volume_change_pct"),
                "tech_alpha": technical_data.get("alpha"),
                "tech_k_line_pattern": technical_data.get("k_line_pattern"),
                "tech_pattern_signal": technical_data.get("pattern_signal"),
                "tech_action_signal": technical_data.get("action_signal"),
                "tech_analysis_date": str(datetime.now().date()),
            }

            update_success = safe_update("portfolio", update_data, {"id": portfolio_id})
            if update_success:
                action_signal = technical_data.get("action_signal", "N/A")
                current_price = technical_data.get("current_price", 0)
                print(f"[DB UPDATE] ✅ Saved to database: {symbol} | 信号: {action_signal} | 价格: ¥{current_price}")
                return True
    except Exception as e:
        print(f"[DB UPDATE] ❌ Failed to update {symbol}: {e}")
    return False


@app.get("/api/v1/market/technical/{symbol}")
async def get_stock_technical_analysis_endpoint(symbol: str, update_persistent: bool = True):
    """
    获取个股技术分析（包含K线形态识别）

    Args:
        symbol: 股票代码
        update_persistent: 是否更新持久化数据（默认True）
    """
    print(f"\n[API] Technical analysis request for {symbol}")

    try:
        # 验证股票代码格式
        if not validate_symbol(symbol):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Invalid stock symbol format")

        technical = get_stock_technical_analysis(symbol)
        if not technical:
            # 返回默认数据而不是404错误
            print(f"[WARN] Technical analysis unavailable for {symbol}, returning default data")
            from datetime import datetime
            return {
                "symbol": symbol,
                "current_price": 0,
                "ma20": 0,
                "ma5": 0,
                "ma20_status": "未知",
                "ma5_status": "未知",
                "volume_status": "未知",
                "volume_change_pct": 0,
                "alpha": 0,
                "health_score": 50,
                "k_line_pattern": "数据不可用",
                "pattern_signal": "neutral",
                "action_signal": "HOLD",
                "analysis": "当前无法获取技术分析数据，请稍后重试。",
                "quote": "投资有风险，入市需谨慎。",
                "date": datetime.now().strftime('%Y-%m-%d')
            }

        # 异步更新持久化数据（不阻塞响应）
        if update_persistent:
            # 使用后台线程更新数据库，避免阻塞主响应
            import threading
            print(f"[API] Spawning background thread to update database for {symbol}...")
            try:
                thread = threading.Thread(
                    target=update_portfolio_persistent_data,
                    args=(symbol, technical),
                    daemon=True
                )
                thread.start()
            except Exception as thread_error:
                print(f"[WARN] Failed to start background thread: {thread_error}")

        health_score = technical.get('health_score', 'N/A')
        print(f"[API] Analysis complete: Score={health_score}")
        return technical

    except Exception as e:
        print(f"[ERROR] Failed to fetch technical analysis: {e}")
        import traceback
        traceback.print_exc()
        # 返回默认数据而不是500错误
        from datetime import datetime
        return {
            "symbol": symbol,
            "current_price": 0,
            "ma20": 0,
            "ma5": 0,
            "ma20_status": "未知",
            "ma5_status": "未知",
            "volume_status": "未知",
            "volume_change_pct": 0,
            "alpha": 0,
            "health_score": 50,
            "k_line_pattern": "网络错误",
            "pattern_signal": "neutral",
            "action_signal": "HOLD",
            "analysis": f"网络连接错误，无法获取{symbol}的技术分析数据。请检查网络连接后重试。",
            "quote": "投资有风险，入市需谨慎。",
            "date": datetime.now().strftime('%Y-%m-%d')
        }


@app.get("/api/v1/market/financial/{symbol}")
async def get_stock_financial_metrics(symbol: str):
    """
    获取个股财务指标（硬核量化分析）

    返回价值、成长、动量三大类指标，为 AI 投委会提供数据支撑
    """
    print(f"[INFO] Fetching financial metrics for: {symbol}")

    try:
        # 验证股票代码格式
        if not validate_symbol(symbol):
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Invalid stock symbol format")

        financial = calculate_financial_metrics(symbol)
        if not financial:
            # 返回默认数据而不是404错误
            print(f"[WARN] Financial metrics unavailable for {symbol}, returning default data")
            return {
                "symbol": symbol,
                "metrics": {},
                "context": "Financial data temporarily unavailable. Please try again later."
            }

        print(f"[OK] Financial metrics retrieved for {symbol}")
        return financial

    except Exception as e:
        print(f"[ERROR] Failed to fetch financial metrics: {e}")
        import traceback
        traceback.print_exc()
        # 返回默认数据而不是500错误
        return {
            "symbol": symbol,
            "metrics": {},
            "context": f"Error retrieving financial data: {str(e)}"
        }


@app.get("/api/v1/report/generate")
async def generate_portfolio_report():
    """
    生成投资组合复盘报告（文字版）
    """
    try:
        from datetime import datetime
        from fastapi import HTTPException

        # 1. 获取投资组合数据
        from utils.db_helper import safe_select
        result_data = safe_select("portfolio", order_by="created_at", desc=True)
        if result_data is None:
            result_data = []

        items = [PortfolioItem(**item) for item in result_data]
        # A股代码是6位数字
        a_share_items = [item for item in items if item.symbol and item.symbol.isdigit() and len(item.symbol) == 6]

        if not a_share_items:
            raise HTTPException(status_code=404, detail="No A-share stocks found in portfolio")

        # 2. 获取市场情绪
        sentiment = get_market_sentiment()

        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("     AShare Sentinel Pro - 投资组合复盘报告")
        report_lines.append("=" * 60)
        report_lines.append(f"\n📅 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"📊 持仓数量: {len(a_share_items)} 只A股")

        # 市场情绪部分
        if sentiment:
            sentiment_label = sentiment.get("label", "未知")
            rsi = sentiment.get("rsi", 0)
            report_lines.append(f"\n🌡️  市场情绪: {sentiment_label}")
            report_lines.append(f"   市场RSI: {rsi:.1f}")

            if sentiment.get("score", 50) > 60:
                market_outlook = "市场情绪偏热，注意追高风险。"
            elif sentiment.get("score", 50) < 40:
                market_outlook = "市场情绪偏冷，可关注超跌机会。"
            else:
                market_outlook = "市场情绪中性，保持谨慎乐观。"
            report_lines.append(f"   市场解读: {market_outlook}")

        # 个股分析部分
        report_lines.append("\n" + "-" * 60)
        report_lines.append("📈 个股详细分析")
        report_lines.append("-" * 60)

        for item in a_share_items:
            symbol = item.symbol
            name = item.name or "未知"
            sector = item.sector or "其他"

            # 获取技术分析
            technical = get_stock_technical_analysis(symbol)
            if technical:
                # 信号对应的中文描述
                action_signal = technical.get("action_signal", "HOLD")
                signal_map = {
                    "STRONG_BUY": "强烈买入 ⭐⭐⭐⭐⭐",
                    "BUY": "买入 ⭐⭐⭐⭐",
                    "HOLD": "持有 ⭐⭐⭐",
                    "SELL": "卖出 ⭐⭐",
                    "STRONG_SELL": "强烈卖出 ⭐"
                }
                signal_cn = signal_map.get(action_signal, "观望")

                report_lines.append(f"\n🔸 {name} ({symbol})")
                report_lines.append(f"   所属板块: {sector}")
                report_lines.append(f"   当前价格: ¥{technical.get('current_price', 0):.2f}")
                report_lines.append(f"   MA20均线: ¥{technical.get('ma20', 0):.2f} ({technical.get('ma20_status', 'N/A')})")
                report_lines.append(f"   MA5均线: ¥{technical.get('ma5', 0):.2f} ({technical.get('ma5_status', 'N/A')})")
                report_lines.append(f"   量能状态: {technical.get('volume_status', 'N/A')}")
                report_lines.append(f"   超额收益(Alpha): {technical.get('alpha', 0):.2f}%")
                report_lines.append(f"   健康评分: {technical.get('health_score', 0)}/100")
                report_lines.append(f"   K线形态: {technical.get('k_line_pattern', 'N/A')}")
                report_lines.append(f"   操作建议: {signal_cn}")

                analysis = technical.get('analysis', '')
                if analysis:
                    report_lines.append(f"   AI分析: {analysis}")

                quote = technical.get('quote', '')
                if quote:
                    report_lines.append(f"   💬 {quote}")

            else:
                report_lines.append(f"\n🔸 {name} ({symbol})")
                report_lines.append(f"   ⚠️ 技术数据暂时无法获取")

        # 总结部分
        report_lines.append("\n" + "-" * 60)
        report_lines.append("📋 复盘总结")
        report_lines.append("-" * 60)

        # 统计信号
        buy_signals = 0
        hold_signals = 0
        sell_signals = 0

        for item in a_share_items:
            technical = get_stock_technical_analysis(item.symbol)
            if technical:
                signal = technical.get("action_signal", "")
                if signal in ["BUY", "STRONG_BUY"]:
                    buy_signals += 1
                elif signal == "HOLD":
                    hold_signals += 1
                elif signal in ["SELL", "STRONG_SELL"]:
                    sell_signals += 1

        report_lines.append(f"• 建议买入: {buy_signals} 只")
        report_lines.append(f"• 建议持有: {hold_signals} 只")
        report_lines.append(f"• 建议卖出: {sell_signals} 只")

        # 投资建议
        if buy_signals > sell_signals:
            final_advice = "整体偏向积极，可考虑适当加仓优质标的。"
        elif sell_signals > buy_signals:
            final_advice = "整体偏弱，建议控制仓位，防范风险。"
        else:
            final_advice = "多空平衡，建议维持现有仓位，关注市场变化。"

        report_lines.append(f"\n💡 投资建议: {final_advice}")

        # 免责声明
        report_lines.append("\n" + "=" * 60)
        report_lines.append("⚠️  免责声明")
        report_lines.append("=" * 60)
        report_lines.append("本报告由AI生成，仅供参考，不构成投资建议。")
        report_lines.append("投资有风险，入市需谨慎。")
        report_lines.append("=" * 60)

        report_text = "\n".join(report_lines)

        return {
            "report": report_text,
            "generated_at": datetime.now().isoformat(),
            "total_stocks": len(a_share_items),
            "buy_signals": buy_signals,
            "hold_signals": hold_signals,
            "sell_signals": sell_signals
        }

    except Exception as e:
        print(f"[ERROR] Failed to generate report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ic/meeting")
async def conduct_ic_meeting(request: ICMeetingRequest):
    """
    召开AI投委会会议 - 完整实现（带自动归档）

    新增功能：
    - save_to_db: 分析完成后自动保存到数据库，实现版本化管理
    """
    import sys
    import os
    import re

    def extract_json_content(text: str) -> str:
        """提取分析内容，移除 JSON 代码块和标题标记"""
        if not text:
            return text
        # 查找 ```json ... ``` 代码块
        json_match = re.search(r'```json\s*\n?\s*\{.*?\}\s*\n?```', text, re.DOTALL)
        if json_match:
            # 提取 JSON 后面的内容
            content = text[json_match.end():]
            # 移除【第二步：详细分析】等标题标记
            content = re.sub(r'【.*?】.*?\n', '', content)
            return content.strip()
        # 如果没有找到代码块，尝试移除标题标记
        content = re.sub(r'【.*?】.*?\n', '', text)
        return content.strip()

    # 数据库连接（用于归档）
    db_conn = None
    report_id = None
    version_id = None
    saved_to_db = False

    try:
        # 1. 获取基本股票信息 (包含当前价格)
        stock_info = get_stock_info(request.symbol, fetch_price=True)
        stock_name = stock_info.get("name", request.symbol) if stock_info else request.symbol
        industry = stock_info.get("industry_en", "未知行业") if stock_info else "未知行业"

        # 2. 获取财务数据（优先级：Tushare → Baostock → AkShare）
        from app.services.market_service import calculate_financial_metrics, get_stock_technical_analysis

        # 尝试获取完整财务指标
        financial_result = calculate_financial_metrics(request.symbol)
        metrics_data = financial_result.get('metrics', {}) if financial_result else {}

        # 导入数据增强服务
        from app.services.data_enhancement_service import enhance_financial_metrics

        # 增强财务数据（智能填充缺失字段）
        metrics_data = enhance_financial_metrics(metrics_data, industry)

        # 总是获取技术分析数据（包含 RSI、换手率、MA20 等独立指标）
        technical_data = get_stock_technical_analysis(request.symbol)
        print(f"[DEBUG] Technical data received: {list(technical_data.keys()) if technical_data else 'None'}")
        if technical_data:
            # 先合并所有原始数据
            for key, value in technical_data.items():
                metrics_data[key] = value

            # 计算布林带位置
            if technical_data.get('bollinger_lower') and technical_data.get('bollinger_upper'):
                bb_range = technical_data['bollinger_upper'] - technical_data['bollinger_lower']
                if bb_range > 0:
                    bb_position = (technical_data['current_price'] - technical_data['bollinger_lower']) / bb_range
                    metrics_data['bollinger_position'] = f"{bb_position:.1%}"
                else:
                    metrics_data['bollinger_position'] = "N/A"
            else:
                metrics_data['bollinger_position'] = "N/A"

            # 标准化字段名称（必须在合并后立即执行）
            if 'rsi_14' in technical_data and technical_data['rsi_14'] is not None:
                metrics_data['rsi'] = technical_data['rsi_14']
                print(f"[DEBUG] Set rsi={technical_data['rsi_14']}")
            if 'bandwidth' in technical_data and technical_data['bandwidth'] is not None:
                metrics_data['bb_width'] = technical_data['bandwidth']
                print(f"[DEBUG] Set bb_width={technical_data['bandwidth']}")
            if 'vwap_20' in technical_data and technical_data['vwap_20'] is not None:
                metrics_data['vwap_20d'] = technical_data['vwap_20']
                print(f"[DEBUG] Set vwap_20d={technical_data['vwap_20']}")
            # 换手率数据源优先级：Tushare > AkShare（遵循项目数据源优先级）
            # 只有当 Tushare 没有返回 turnover_rate 时，才使用 AkShare 的 turnover
            if 'turnover' in technical_data and technical_data['turnover'] is not None:
                if not metrics_data.get('turnover_rate'):
                    metrics_data['turnover_rate'] = technical_data['turnover']
                    print(f"[DEBUG] Set turnover_rate from AkShare (fallback): {technical_data['turnover']}")
                else:
                    print(f"[DEBUG] Using Tushare turnover_rate={metrics_data.get('turnover_rate')}, AkShare ignored")

            # 优先使用 technical_data 的价格，其次使用 stock_info 的价格，最后使用默认值
            current_price = technical_data.get('current_price') or stock_info.get('current_price') or metrics_data.get('current_price', 100.0)
            print(f"[DEBUG] Final metrics_data keys: {list(metrics_data.keys())}")
            print(f"[DEBUG] turnover_rate value: {metrics_data.get('turnover_rate')}, type: {type(metrics_data.get('turnover_rate'))}")
            print(f"[DEBUG] current_price source: technical={technical_data.get('current_price')}, stock_info={stock_info.get('current_price')}, final={current_price}")
        else:
            current_price = stock_info.get('current_price') or metrics_data.get('current_price', 100.0)
            print(f"[DEBUG] current_price (no technical data): stock_info={stock_info.get('current_price')}, final={current_price}")

        # 3. 构建上下文（使用真实财务数据 + 技术分析数据）
        # 构建带估算说明的上下文
        context = {
            # 基本信息和估值指标
            "industry": industry,
            "market_cap": f"{metrics_data.get('market_cap', 0) / 100000000:.1f}亿" if metrics_data.get('market_cap') else "N/A",
            "pe_ratio": f"{metrics_data.get('pe_ratio', 0):.1f}" if metrics_data.get('pe_ratio') else "N/A",
            "pb_ratio": f"{metrics_data.get('pb_ratio', 0):.1f}" if metrics_data.get('pb_ratio') else "N/A",

            # PEG比率 - 显示是否为计算值
            "peg_ratio": f"{metrics_data.get('peg_ratio', 0):.1f}" if metrics_data.get('peg_ratio') else "N/A",

            # 盈利能力和财务健康
            "roe": f"{metrics_data.get('roe', 0):.1f}%" if metrics_data.get('roe') else "N/A",
            "debt_to_equity": f"{metrics_data.get('debt_to_equity', 0):.1f}%" if metrics_data.get('debt_to_equity') else "N/A",
            "fcf_yield": f"{metrics_data.get('fcf_yield', 0):.1f}%" if metrics_data.get('fcf_yield') else "N/A",
            "dividend_yield": f"{metrics_data.get('dividend_yield', 0):.1f}%" if metrics_data.get('dividend_yield') else "N/A",  # 股息率

            # 成长指标 - 显示是否为估算值
            "revenue_growth_cagr": f"{metrics_data.get('revenue_growth_cagr', 0):.1f}%" if metrics_data.get('revenue_growth_cagr') else "N/A",
            "rd_intensity": f"{metrics_data.get('rd_intensity', 0):.1f}" if metrics_data.get('rd_intensity') else "N/A",

            # 技术指标 - 使用更安全的格式化逻辑
            "rsi_14": f"{metrics_data.get('rsi_14', 0):.1f}" if metrics_data.get('rsi_14') is not None else "N/A",
            "volume_status": metrics_data.get('volume_status', "N/A") or "N/A",
            "volume_change_pct": f"{metrics_data.get('volume_change_pct', 0):.1f}%" if metrics_data.get('volume_change_pct') is not None else "N/A",
            "turnover_rate": f"{metrics_data.get('turnover_rate', 0):.2f}%" if metrics_data.get('turnover_rate') is not None and metrics_data.get('turnover_rate') > 0 else "N/A",
            "ma20_status": metrics_data.get('ma20_status', "N/A") or "N/A",
            "bollinger_position": metrics_data.get('bollinger_position', "N/A") or "N/A",
            "bb_width": f"{metrics_data.get('bb_width', 0):.3f}" if metrics_data.get('bb_width') is not None else "N/A",
            "vwap_20d": f"{metrics_data.get('vwap_20d', 0):.2f}" if metrics_data.get('vwap_20d') is not None else "N/A",

            # 综合评分
            "health_score": metrics_data.get('health_score', 50),
            "action_signal": metrics_data.get('action_signal', "HOLD") or "HOLD"
        }

        # 添加数据质量说明给AI
        data_quality_notes = []
        if metrics_data.get('revenue_growth_estimated'):
            data_quality_notes.append(f"营收增长率({context['revenue_growth_cagr']})为基于ROE或行业平均值的估算")
        if metrics_data.get('rd_intensity_estimated'):
            data_quality_notes.append(f"研发费率({context['rd_intensity']})为基于行业平均值的估算")
        if metrics_data.get('peg_ratio_calculated'):
            data_quality_notes.append(f"PEG比率({context['peg_ratio']})为基于PE和营收增长率计算得出")

        if data_quality_notes:
            context['data_quality_notes'] = "; ".join(data_quality_notes)

        # 调试：打印context数据
        print(f"[DEBUG] Context for AI: rsi_14={context.get('rsi_14')}, bb_width={context.get('bb_width')}, vwap_20d={context.get('vwap_20d')}, ma20_status={context.get('ma20_status')}")

        # 4. 执行IC meeting
        meeting_result = await conduct_meeting(
            symbol=request.symbol,
            stock_name=stock_name,
            current_price=current_price,
            context=context,
            api_key=""
        )

        # 5. 自动归档逻辑（使用 Supabase）
        if request.save_to_db:
            try:
                from app.core.db_supabase import get_supabase_client
                from app.repositories.supabase_repository import StockRepository, ReportRepository

                # 获取 Supabase 客户端
                supabase = get_supabase_client()
                stock_repo = StockRepository(supabase)
                report_repo = ReportRepository(supabase)

                # 5.1 创建或更新股票记录
                await stock_repo.create(
                    code=request.symbol,
                    name=stock_name,
                    current_price=current_price,
                    change_percent=metrics_data.get('change_percent'),
                    turnover_rate=metrics_data.get('turnover_rate')
                )

                # 5.2 解析专家评分
                agent_scores = meeting_result.get('agent_scores', {})
                score_growth = agent_scores.get('cathie_wood', {}).get('score')
                score_value = agent_scores.get('warren_buffett', {}).get('score')
                score_technical = meeting_result.get('technical_score')

                # 解析评级
                verdict_chinese = meeting_result.get('verdict_chinese', '')
                conviction_stars = meeting_result.get('conviction_stars', '')

                # 映射中文评级到英文
                verdict_map = {
                    '买入': 'BUY',
                    '持有': 'HOLD',
                    '卖出': 'SELL'
                }
                verdict = verdict_map.get(verdict_chinese, 'HOLD')

                # 5.3 创建报告记录
                # 构建 Markdown 内容
                content_md = f"""# {stock_name} ({request.symbol}) - IC投委会分析报告

## 基本信息
- 当前价格: {current_price}
- 行业: {industry}
- PE: {context.get('pe_ratio')}
- PB: {context.get('pb_ratio')}
- ROE: {context.get('roe')}

## Cathie Wood (成长投资)
{extract_json_content(meeting_result.get('cathie_wood', ''))}

## Nancy Pelosi (技术面)
{extract_json_content(meeting_result.get('nancy_pelosi', ''))}

## Warren Buffett (价值投资)
{extract_json_content(meeting_result.get('warren_buffett', ''))}

## 最终裁决
- 评级: {verdict_chinese}
- 信心程度: {conviction_stars}
"""

                # 创建报告
                saved_report = await report_repo.create(
                    stock_code=request.symbol,
                    content=content_md,
                    cathie_wood_analysis=meeting_result.get('cathie_wood', ''),
                    nancy_pelosi_analysis=meeting_result.get('nancy_pelosi', ''),
                    warren_buffett_analysis=meeting_result.get('warren_buffett', ''),
                    charlie_munger_analysis=str(meeting_result.get('final_verdict', {})),
                    score_growth=score_growth,
                    score_value=score_value,
                    score_technical=score_technical,
                    verdict=verdict,
                    conviction_level=len(conviction_stars) if conviction_stars else None,
                    conviction_stars=conviction_stars,
                    financial_data=metrics_data
                )

                report_id = saved_report.id
                version_id = getattr(saved_report, 'version_id', None)
                saved_to_db = True

                # 5.4 更新股票表的最新状态
                await stock_repo.update_latest_scores(
                    code=request.symbol,
                    score_growth=score_growth,
                    score_value=score_value,
                    score_technical=score_technical,
                    suggestion=verdict,
                    conviction=conviction_stars
                )

                print(f"[ARCHIVE] Report saved to Supabase: {version_id}, stock updated: {request.symbol}")

            except Exception as archive_error:
                print(f"[WARN] Failed to save to Supabase: {archive_error}")
                import traceback
                traceback.print_exc()

        # 6. 计算雷达图数据（基于IC投委会评分）
        agent_scores = meeting_result.get("agent_scores", {})
        cathie_score = agent_scores.get("cathie_wood", {}).get("score", 50)
        nancy_score = agent_scores.get("nancy_pelosi", {}).get("score", 50)
        warren_score = agent_scores.get("warren_buffett", {}).get("score", 50)

        # Helper function to safely convert values to float
        def safe_float_convert(value, default=0):
            if value is None or value == 'N/A':
                return default
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Remove % sign and whitespace
                cleaned = value.replace('%', '').strip()
                try:
                    return float(cleaned)
                except ValueError:
                    return default
            return default

        # 计算安全评分（基于ROE和负债率）
        roe = safe_float_convert(context.get("roe"), 0)
        debt_to_equity = safe_float_convert(context.get("debt_to_equity"), 50)
        safety_score = min(100, max(0, (roe * 10) + (100 - debt_to_equity) / 2))

        # 计算股息评分（基于PE/PB）
        pb = safe_float_convert(context.get("pb_ratio"), 100)
        dividend_score = min(100, max(0, 100 - pb * 2))  # PB越低，股息潜力越高

        advanced_metrics = {
            "radar": {
                "value_score": int(warren_score),  # 价值评分 = Warren Buffett评分
                "growth_score": int(cathie_score),  # 成长评分 = Cathie Wood评分
                "safety_score": int(safety_score),  # 安全评分 = 基于ROE和负债率
                "dividend_score": int(dividend_score),  # 股息评分 = 基于PB
                "trend_score": int(nancy_score)  # 趋势评分 = Nancy Pelosi评分
            },
            "technical": {
                "rps": int(meeting_result.get("technical_score", 50)),
                "deviation": 0,
                "ma200_deviation": 0
            },
            "capital": {
                "purity": 80,
                "control_duration": 5,
                "accumulation_strength": 60
            },
            "fundamental": {
                "peg": None,
                "growth_rate": int(cathie_score),
                "beta": 1.0
            }
        }

        # 7. 构建响应（提取分析内容，移除 markdown 代码块）
        result = {
            "symbol": meeting_result["symbol"],
            "stock_name": meeting_result["stock_name"],
            "current_price": meeting_result["current_price"],
            "turnover_rate": context.get("turnover_rate", "N/A"),
            "verdict_chinese": meeting_result["verdict_chinese"],
            "conviction_stars": meeting_result["conviction_stars"],
            "cathie_wood": extract_json_content(meeting_result.get("cathie_wood", "")),
            "nancy_pelosi": extract_json_content(meeting_result.get("nancy_pelosi", "")),
            "warren_buffett": extract_json_content(meeting_result.get("warren_buffett", "")),
            "final_verdict": meeting_result["final_verdict"],
            "summary": get_ic_recommendation_summary(meeting_result),
            "technical_score": meeting_result.get("technical_score", 50),
            "fundamental_score": meeting_result.get("fundamental_score", 50),
            "agent_scores": meeting_result.get("agent_scores"),
            "dashboard_position": meeting_result.get("dashboard_position"),
            "advanced_metrics": advanced_metrics,  # 新增：雷达图数据
            # V1.6 新增：版本信息
            "report_id": report_id,
            "version_id": version_id,
            "saved_to_db": saved_to_db
        }

        # Log response size for debugging
        import json
        result_json = json.dumps(result, ensure_ascii=False)
        response_size_kb = len(result_json.encode('utf-8')) / 1024
        print(f"[SUCCESS] IC meeting completed for {request.symbol}: {meeting_result['verdict_chinese']}", flush=True)
        print(f"[DEBUG] Response size: {response_size_kb:.1f} KB, returning to client...", flush=True)
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()

        # 返回错误响应而不是抛出异常
        return {
            "symbol": request.symbol,
            "error": str(e)[:500],
            "stock_name": request.symbol,
            "verdict_chinese": "分析失败",
            "conviction_stars": "*",
            "cathie_wood": f"分析失败: {str(e)[:200]}",
            "nancy_pelosi": "",
            "warren_buffett": "",
            "final_verdict": {"final_verdict": "HOLD"},
            "summary": f"分析失败: {str(e)}",
            "technical_score": 50,
            "fundamental_score": 50,
            "saved_to_db": False
        }
    finally:
        # 确保数据库连接被关闭
        if db_conn:
            try:
                db_conn.close()
            except:
                pass
    """
    召开AI投委会会议 - 完整实现
    """
    import sys
    import os
    import re

    def extract_json_content(text: str) -> str:
        """提取分析内容，移除 JSON 代码块和标题标记"""
        if not text:
            return text
        # 查找 ```json ... ``` 代码块
        json_match = re.search(r'```json\s*\n?\s*\{.*?\}\s*\n?```', text, re.DOTALL)
        if json_match:
            # 提取 JSON 后面的内容
            content = text[json_match.end():]
            # 移除【第二步：详细分析】等标题标记
            content = re.sub(r'【.*?】.*?\n', '', content)
            return content.strip()
        # 如果没有找到代码块，尝试移除标题标记
        content = re.sub(r'【.*?】.*?\n', '', text)
        return content.strip()

    try:
        # 1. 获取基本股票信息 (包含当前价格)
        stock_info = get_stock_info(request.symbol, fetch_price=True)
        stock_name = stock_info.get("name", request.symbol) if stock_info else request.symbol

        # 2. 获取财务数据（优先级：Tushare → Baostock → AkShare）
        from app.services.market_service import calculate_financial_metrics, get_stock_technical_analysis

        # 尝试获取完整财务指标
        financial_result = calculate_financial_metrics(request.symbol)
        metrics_data = financial_result.get('metrics', {}) if financial_result else {}

        # 导入数据增强服务
        from app.services.data_enhancement_service import enhance_financial_metrics

        # 获取行业信息用于估算
        industry = stock_info.get("industry_en", "未知行业") if stock_info else "未知行业"

        # 增强财务数据（智能填充缺失字段）
        metrics_data = enhance_financial_metrics(metrics_data, industry)

        # 总是获取技术分析数据（包含 RSI、换手率、MA20 等独立指标）
        technical_data = get_stock_technical_analysis(request.symbol)
        print(f"[DEBUG] Technical data received: {list(technical_data.keys()) if technical_data else 'None'}")
        if technical_data:
            # 先合并所有原始数据
            for key, value in technical_data.items():
                metrics_data[key] = value

            # 计算布林带位置
            if technical_data.get('bollinger_lower') and technical_data.get('bollinger_upper'):
                bb_range = technical_data['bollinger_upper'] - technical_data['bollinger_lower']
                if bb_range > 0:
                    bb_position = (technical_data['current_price'] - technical_data['bollinger_lower']) / bb_range
                    metrics_data['bollinger_position'] = f"{bb_position:.1%}"
                else:
                    metrics_data['bollinger_position'] = "N/A"
            else:
                metrics_data['bollinger_position'] = "N/A"

            # 标准化字段名称（必须在合并后立即执行）
            if 'rsi_14' in technical_data and technical_data['rsi_14'] is not None:
                metrics_data['rsi'] = technical_data['rsi_14']
                print(f"[DEBUG] Set rsi={technical_data['rsi_14']}")
            if 'bandwidth' in technical_data and technical_data['bandwidth'] is not None:
                metrics_data['bb_width'] = technical_data['bandwidth']
                print(f"[DEBUG] Set bb_width={technical_data['bandwidth']}")
            if 'vwap_20' in technical_data and technical_data['vwap_20'] is not None:
                metrics_data['vwap_20d'] = technical_data['vwap_20']
                print(f"[DEBUG] Set vwap_20d={technical_data['vwap_20']}")
            # 换手率数据源优先级：Tushare > AkShare（遵循项目数据源优先级）
            # 只有当 Tushare 没有返回 turnover_rate 时，才使用 AkShare 的 turnover
            if 'turnover' in technical_data and technical_data['turnover'] is not None:
                if not metrics_data.get('turnover_rate'):
                    metrics_data['turnover_rate'] = technical_data['turnover']
                    print(f"[DEBUG] Set turnover_rate from AkShare (fallback): {technical_data['turnover']}")
                else:
                    print(f"[DEBUG] Using Tushare turnover_rate={metrics_data.get('turnover_rate')}, AkShare ignored")

            # 优先使用 technical_data 的价格，其次使用 stock_info 的价格，最后使用默认值
            current_price = technical_data.get('current_price') or stock_info.get('current_price') or metrics_data.get('current_price', 100.0)
            print(f"[DEBUG] Final metrics_data keys: {list(metrics_data.keys())}")
            print(f"[DEBUG] turnover_rate value: {metrics_data.get('turnover_rate')}, type: {type(metrics_data.get('turnover_rate'))}")
            print(f"[DEBUG] current_price source: technical={technical_data.get('current_price')}, stock_info={stock_info.get('current_price')}, final={current_price}")
        else:
            current_price = stock_info.get('current_price') or metrics_data.get('current_price', 100.0)
            print(f"[DEBUG] current_price (no technical data): stock_info={stock_info.get('current_price')}, final={current_price}")

        # 3. 构建上下文（使用真实财务数据 + 技术分析数据）
        # 构建带估算说明的上下文
        context = {
            # 基本信息和估值指标
            "industry": stock_info.get("industry_en", "未知行业") if stock_info else "未知行业",
            "market_cap": f"{metrics_data.get('market_cap', 0) / 100000000:.1f}亿" if metrics_data.get('market_cap') else "N/A",
            "pe_ratio": f"{metrics_data.get('pe_ratio', 0):.1f}" if metrics_data.get('pe_ratio') else "N/A",
            "pb_ratio": f"{metrics_data.get('pb_ratio', 0):.1f}" if metrics_data.get('pb_ratio') else "N/A",

            # PEG比率 - 显示是否为计算值
            "peg_ratio": f"{metrics_data.get('peg_ratio', 0):.1f}" if metrics_data.get('peg_ratio') else "N/A",

            # 盈利能力和财务健康
            "roe": f"{metrics_data.get('roe', 0):.1f}%" if metrics_data.get('roe') else "N/A",
            "debt_to_equity": f"{metrics_data.get('debt_to_equity', 0):.1f}%" if metrics_data.get('debt_to_equity') else "N/A",
            "fcf_yield": f"{metrics_data.get('fcf_yield', 0):.1f}%" if metrics_data.get('fcf_yield') else "N/A",
            "dividend_yield": f"{metrics_data.get('dividend_yield', 0):.1f}%" if metrics_data.get('dividend_yield') else "N/A",  # 股息率

            # 成长指标 - 显示是否为估算值
            "revenue_growth_cagr": f"{metrics_data.get('revenue_growth_cagr', 0):.1f}%" if metrics_data.get('revenue_growth_cagr') else "N/A",
            "rd_intensity": f"{metrics_data.get('rd_intensity', 0):.1f}" if metrics_data.get('rd_intensity') else "N/A",

            # 技术指标 - 使用更安全的格式化逻辑
            "rsi_14": f"{metrics_data.get('rsi_14', 0):.1f}" if metrics_data.get('rsi_14') is not None else "N/A",
            "volume_status": metrics_data.get('volume_status', "N/A") or "N/A",
            "volume_change_pct": f"{metrics_data.get('volume_change_pct', 0):.1f}%" if metrics_data.get('volume_change_pct') is not None else "N/A",
            "turnover_rate": f"{metrics_data.get('turnover_rate', 0):.2f}%" if metrics_data.get('turnover_rate') is not None and metrics_data.get('turnover_rate') > 0 else "N/A",
            "ma20_status": metrics_data.get('ma20_status', "N/A") or "N/A",
            "bollinger_position": metrics_data.get('bollinger_position', "N/A") or "N/A",
            "bb_width": f"{metrics_data.get('bb_width', 0):.3f}" if metrics_data.get('bb_width') is not None else "N/A",
            "vwap_20d": f"{metrics_data.get('vwap_20d', 0):.2f}" if metrics_data.get('vwap_20d') is not None else "N/A",

            # 综合评分
            "health_score": metrics_data.get('health_score', 50),
            "action_signal": metrics_data.get('action_signal', "HOLD") or "HOLD"
        }

        # 添加数据质量说明给AI
        data_quality_notes = []
        if metrics_data.get('revenue_growth_estimated'):
            data_quality_notes.append(f"营收增长率({context['revenue_growth_cagr']})为基于ROE或行业平均值的估算")
        if metrics_data.get('rd_intensity_estimated'):
            data_quality_notes.append(f"研发费率({context['rd_intensity']})为基于行业平均值的估算")
        if metrics_data.get('peg_ratio_calculated'):
            data_quality_notes.append(f"PEG比率({context['peg_ratio']})为基于PE和营收增长率计算得出")

        if data_quality_notes:
            context['data_quality_notes'] = "; ".join(data_quality_notes)

        # 调试：打印context数据
        print(f"[DEBUG] Context for AI: rsi_14={context.get('rsi_14')}, bb_width={context.get('bb_width')}, vwap_20d={context.get('vwap_20d')}, ma20_status={context.get('ma20_status')}")

        # 4. 执行IC meeting
        meeting_result = await conduct_meeting(
            symbol=request.symbol,
            stock_name=stock_name,
            current_price=current_price,
            context=context,
            api_key=""
        )

        # 5. 构建响应（提取分析内容，移除 markdown 代码块）
        result = {
            "symbol": meeting_result["symbol"],
            "stock_name": meeting_result["stock_name"],
            "current_price": meeting_result["current_price"],
            "turnover_rate": context.get("turnover_rate", "N/A"),
            "verdict_chinese": meeting_result["verdict_chinese"],
            "conviction_stars": meeting_result["conviction_stars"],
            "cathie_wood": extract_json_content(meeting_result.get("cathie_wood", "")),
            "nancy_pelosi": extract_json_content(meeting_result.get("nancy_pelosi", "")),
            "warren_buffett": extract_json_content(meeting_result.get("warren_buffett", "")),
            "final_verdict": meeting_result["final_verdict"],
            "summary": get_ic_recommendation_summary(meeting_result),
            "technical_score": meeting_result.get("technical_score", 50),
            "fundamental_score": meeting_result.get("fundamental_score", 50),
            "agent_scores": meeting_result.get("agent_scores"),
            "dashboard_position": meeting_result.get("dashboard_position")
        }

        # Log response size for debugging
        import json
        result_json = json.dumps(result, ensure_ascii=False)
        response_size_kb = len(result_json.encode('utf-8')) / 1024
        print(f"[SUCCESS] IC meeting completed for {request.symbol}: {meeting_result['verdict_chinese']}", flush=True)
        print(f"[DEBUG] Response size: {response_size_kb:.1f} KB, returning to client...", flush=True)
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()

        # 返回错误响应而不是抛出异常
        return {
            "symbol": request.symbol,
            "error": str(e)[:500],
            "stock_name": request.symbol,
            "verdict_chinese": "分析失败",
            "conviction_stars": "*",
            "cathie_wood": f"分析失败: {str(e)[:200]}",
            "nancy_pelosi": "",
            "warren_buffett": "",
            "final_verdict": {"final_verdict": "HOLD"},
            "summary": f"分析失败: {str(e)}",
            "technical_score": 50,
            "fundamental_score": 50
        }


# ============================================
# V1.6 版本化管理 API - 历史报告查询
# ============================================

@app.get("/api/v1/reports")
async def get_reports(
    stock_code: Optional[str] = None,
    verdict: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取历史报告列表（带分页和筛选）

    Query Parameters:
        - stock_code: 股票代码（可选）
        - verdict: 评级筛选 (BUY/HOLD/SELL，可选)
        - limit: 每页数量 (默认 50)
        - offset: 偏移量 (默认 0)

    Returns:
        {
            "total": 总数,
            "reports": 报告列表,
            "has_more": 是否有更多
        }
    """
    try:
        from app.models.versioning import ReportHistoryRequest, SuggestionEnum
        from app.repositories.versioning_repository import ReportRepository

        # 构建查询请求
        request_filters = ReportHistoryRequest(
            stock_code=stock_code,
            verdict=SuggestionEnum(verdict) if verdict else None,
            limit=min(limit, 100),  # 最大 100
            offset=offset
        )

        # 获取数据库连接
        if not test_mysql_connection():
            return {
                "total": 0,
                "reports": [],
                "has_more": False,
                "error": "数据库连接失败"
            }

        with get_mysql_connection() as db_conn:
            report_repo = ReportRepository(db_conn)
            result = await report_repo.get_history(request_filters)

            # 转换为字典格式
            reports_data = [
                {
                    "id": r.id,
                    "stock_code": r.stock_code,
                    "stock_name": r.stock_name,
                    "version_id": r.version_id,
                    "verdict": r.verdict.value,
                    "conviction_stars": r.conviction_stars,
                    "score_growth": r.score_growth,
                    "score_value": r.score_value,
                    "score_technical": r.score_technical,
                    "composite_score": r.composite_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "current_price": r.current_price,
                    "change_percent": r.change_percent
                }
                for r in result.reports
            ]

            return {
                "total": result.total,
                "reports": reports_data,
                "has_more": result.has_more
            }
    except Exception as e:
        print(f"[ERROR] Failed to get reports: {e}")
        import traceback
        traceback.print_exc()
        return {
            "total": 0,
            "reports": [],
            "has_more": False,
            "error": str(e)[:500]
        }

# ============================================
# 认证测试接口
# ============================================

@app.get("/api/me")
async def get_me(user_id: str = Depends(get_current_user)):
    """
    获取当前用户信息（需要认证）

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        {
            "user_id": "<uuid>",
            "status": "authenticated"
        }
    """
    return {
        "user_id": user_id,
        "status": "authenticated"
    }


@app.get("/api/v1/me")
async def get_me_v1(user_id: str = Depends(get_current_user)):
    """
    获取当前用户信息 v1（需要认证）

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        {
            "user_id": "<uuid>",
            "status": "authenticated"
        }
    """
    return {
        "user_id": user_id,
        "status": "authenticated"
    }


# End of file
