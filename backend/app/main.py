"""
Fintech Platform - Backend API
FastAPI Application Entry Point
"""

# 加载 .env 文件 (必须在其他导入之前)
from dotenv import load_dotenv
load_dotenv()

import uuid
from typing import Literal

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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


# ============================================
# Application Configuration
# ============================================
app = FastAPI(
    title="Fintech Platform API",
    description="Investment Research & Intelligence Platform",
    version="1.0.0",
)


# 全局 OPTIONS 处理器（在所有路由之前）
@app.middleware("http")
async def add_options_handler(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
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
    db = get_db_client()
    try:
        result = db.table("portfolio").insert({
            "symbol": stock_info["symbol"],
            "name": stock_info["name"],
            "sector": classification["sector_cn"],
            "industry": classification["industry_cn"],
            "cost_basis": request.cost_basis,
            "shares": request.shares,
            "notes": request.notes,
        }).execute()

        if result.data:
            item = result.data[0]
            print(f"[OK] Stock added: {item['symbol']}")
            return PortfolioItem(**item)
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Failed to save stock")

    except Exception as e:
        print(f"[ERROR] Failed to add stock: {e}")
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


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
        query_start = time.time()
        result = db.table("portfolio").select("*").order("created_at", desc=True).execute()
        query_time = time.time() - query_start
        print(f"[INFO] Database query took: {query_time:.3f}s, returned {len(result.data)} rows")

        items = []
        for item_data in result.data:
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
                        db.table("portfolio").update(update_data).eq("id", item.id).execute()

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

    db = get_db_client()
    try:
        result = db.table("portfolio").delete().eq("id", portfolio_id).execute()

        if result.data:
            print(f"[OK] Stock deleted: {portfolio_id}")
            return DeleteStockResponse(success=True, message="Stock deleted successfully")
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Stock not found")

    except Exception as e:
        print(f"[ERROR] Failed to delete stock: {e}")
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


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
        portfolio_result = db.table("portfolio").select("*").eq("id", request.portfolio_id).execute()

        if not portfolio_result.data:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Stock not found")

        stock = portfolio_result.data[0]
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
        result = db.table("weekly_reviews").select("*").eq("portfolio_id", portfolio_id).order("review_date", desc=True).execute()

        reviews = [WeeklyReviewResponse(**item) for item in result.data]
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
        db = get_db_client()
        result = db.table("portfolio").select("id").eq("symbol", symbol).execute()

        if result.data:
            portfolio_id = result.data[0]["id"]
            from datetime import datetime

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

            db.table("portfolio").update(update_data).eq("id", portfolio_id).execute()
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
        db = get_db_client()
        result = db.table("portfolio").select("*").order("created_at", desc=True).execute()

        items = [PortfolioItem(**item) for item in result.data]
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


@app.post("/api/v1/ic/meeting", response_model=ICMeetingResponse)
async def conduct_ic_meeting(request: ICMeetingRequest):
    """
    召开AI投委会会议

    四位著名投资者（Cathie Wood、Nancy Pelosi、Warren Buffett、Charlie Munger）
    将对指定股票进行多视角分析，并给出最终投资建议。

    流程：
    1. 并行执行：Cathie Wood + Nancy Pelosi 独立分析
    2. 顺序执行：Warren Buffett 审阅前两者观点
    3. 最终裁决：Charlie Munger 综合所有观点并给出JSON判决
    """
    import os
    from datetime import datetime

    print(f"[INFO] Conducting IC meeting for: {request.symbol}")

    try:
        # 如果没有提供股票名称或价格，从Baostock获取
        stock_name = request.stock_name
        current_price = request.current_price if request.current_price is not None else None

        if not stock_name:
            stock_info = get_stock_info(request.symbol, fetch_price=False)
            if stock_info:
                stock_name = stock_info.get("name", request.symbol)

        if current_price is None:
            # 先尝试从Baostock获取价格
            baostock_data = get_financials_baostock(request.symbol)
            if baostock_data and baostock_data.get('metrics'):
                current_price = baostock_data['metrics'].get('current_price')

        # 如果Baostock没有价格，尝试从AkShare获取
        if current_price is None or current_price == 0:
            technical = get_stock_technical_analysis(request.symbol)
            if technical:
                current_price = technical.get("current_price", 0.0)

        if current_price is None:
            current_price = 0.0

        # 获取完整的财务指标数据
        # 优先使用Baostock（免费、稳定），如果失败则使用AkShare
        baostock_data = get_financials_baostock(request.symbol)
        if baostock_data and baostock_data.get('metrics'):
            print(f"[OK] Using Baostock data source")
            metrics_data = baostock_data['metrics']
            data_source = 'baostock'
        else:
            print(f"[WARN] Baostock failed, trying AkShare...")
            financial_metrics = calculate_financial_metrics(request.symbol)
            metrics_data = financial_metrics.get("metrics", {})
            data_source = 'akshare'

        # 获取市场快照数据（实时行情 + 核心财务指标）
        from app.services.market_service import get_market_snapshot
        market_snapshot = get_market_snapshot(request.symbol)
        if market_snapshot and market_snapshot.get('fundamentals'):
            print(f"[OK] Market snapshot available for IC analysis")
            snapshot_fundamentals = market_snapshot.get('fundamentals', {})
            # 如果之前的数据源没有某些指标，使用快照数据补充
            if not metrics_data.get('pe_ratio') and snapshot_fundamentals.get('pe_ttm'):
                metrics_data['pe_ratio'] = snapshot_fundamentals.get('pe_ttm')
            if not metrics_data.get('pb_ratio') and snapshot_fundamentals.get('pb'):
                metrics_data['pb_ratio'] = snapshot_fundamentals.get('pb')
            if not metrics_data.get('roe') and snapshot_fundamentals.get('roe'):
                metrics_data['roe'] = snapshot_fundamentals.get('roe')
            # 更新实时价格和换手率
            if market_snapshot.get('current_price'):
                current_price = market_snapshot.get('current_price')
            if snapshot_fundamentals.get('turnover'):
                metrics_data['turnover_realtime'] = snapshot_fundamentals.get('turnover')
            if snapshot_fundamentals.get('total_mv'):
                metrics_data['market_cap_realtime'] = snapshot_fundamentals.get('total_mv')
        else:
            print(f"[WARN] Market snapshot not available, using existing data")

        # 获取技术分析数据（用于智能资金流向、RSI等）
        technical_data = get_stock_technical_analysis(request.symbol)
        if technical_data:
            print(f"[OK] Technical data available for IC analysis")

        # 格式化函数：将数字转换为易读格式
        def format_metric(value, unit='', decimals=2):
            if value is None or value == 'N/A':
                return 'N/A'
            try:
                if isinstance(value, str):
                    value = float(value)
                # 如果是百分比形式的小数（如0.26表示26%），转换为百分比
                if unit == '%' and abs(value) < 1:
                    return f"{value * 100:.{decimals}f}%"
                return f"{value:.{decimals}f}{unit}"
            except:
                return str(value)

        # 计算PEG比率（如果有PE和营收增长）
        # PEG = PE Ratio / Revenue Growth Rate (%)
        pe_ratio = metrics_data.get('pe_ratio')
        revenue_growth = metrics_data.get('revenue_growth_cagr')
        calculated_peg = None
        if pe_ratio and revenue_growth:
            try:
                pe_float = float(pe_ratio)
                growth_float = float(revenue_growth)
                # revenue_growth_cagr 是小数形式（如0.15表示15%），需要转换为百分比
                growth_percentage = growth_float * 100 if abs(growth_float) < 1 else growth_float
                if growth_percentage > 0:
                    calculated_peg = pe_float / growth_percentage
            except:
                pass

        # 准备上下文（使用实际财务数据 + 技术分析数据 + 市场快照）
        # 优先使用实时市场快照数据，如果没有则使用其他数据源
        turnover_value = (
            format_metric(metrics_data.get('turnover_realtime')) if metrics_data.get('turnover_realtime') else
            format_metric(technical_data.get('turnover')) if technical_data and technical_data.get('turnover') else
            'N/A'
        )
        market_cap_value = (
            f"{metrics_data.get('market_cap_realtime'):.0f}亿" if metrics_data.get('market_cap_realtime') else
            request.market_cap or
            "N/A"
        )

        context = {
            "industry": request.industry or (stock_info.get('industry_en') if stock_info else 'N/A'),
            "market_cap": market_cap_value,
            # 格式化财务指标
            "pe_ratio": request.pe_ratio or format_metric(metrics_data.get('pe_ratio')),
            "revenue_growth": request.revenue_growth or format_metric(metrics_data.get('revenue_growth_cagr'), '%'),
            "roe": format_metric(metrics_data.get('roe'), '%'),
            "debt_to_equity": format_metric(metrics_data.get('debt_to_equity'), '%'),
            "pb_ratio": format_metric(metrics_data.get('pb_ratio')),
            "peg_ratio": request.peg_ratio or format_metric(calculated_peg if calculated_peg else metrics_data.get('peg_ratio')),
            "rd_intensity": format_metric(metrics_data.get('rd_intensity'), '%'),
            "beta": format_metric(metrics_data.get('beta')),
            "rsi_14": format_metric(metrics_data.get('rsi_14')),
            "fcf_yield": format_metric(metrics_data.get('fcf_yield'), '%'),
            # 技术分析指标（来自 get_stock_technical_analysis）
            "volume_status": technical_data.get('volume_status', 'N/A') if technical_data else 'N/A',
            "volume_change_pct": technical_data.get('volume_change_pct', 0) if technical_data else 0,
            "turnover": turnover_value,
            "ma20_status": technical_data.get('ma20_status', 'N/A') if technical_data else 'N/A',
            "health_score": technical_data.get('health_score', 50) if technical_data else 50,
            "action_signal": technical_data.get('action_signal', 'HOLD') if technical_data else 'HOLD',
            # 布林带数据
            "bollinger_upper": technical_data.get('bollinger_upper', 'N/A') if technical_data else 'N/A',
            "bollinger_lower": technical_data.get('bollinger_lower', 'N/A') if technical_data else 'N/A',
            "bandwidth": technical_data.get('bandwidth', 'N/A') if technical_data else 'N/A',
            # VWAP 筹码成本
            "vwap_20": technical_data.get('vwap_20', 'N/A') if technical_data else 'N/A',
            "timestamp": datetime.now().isoformat()
        }

        print(f"[DEBUG] IC Context: {data_source} source")
        print(f"[DEBUG] PE: {context['pe_ratio']}, ROE: {context['roe']}, Growth: {context['revenue_growth']}")

        # 获取API密钥
        api_key = os.environ.get("DASHSCOPE_API_KEY", "")

        # 执行IC会议（异步）
        meeting_result = await conduct_meeting(
            symbol=request.symbol,
            stock_name=stock_name or request.symbol,
            current_price=current_price,
            context=context,
            api_key=api_key
        )

        # 生成摘要
        summary = get_ic_recommendation_summary(meeting_result)

        print(f"[OK] IC meeting completed: {meeting_result['verdict_chinese']}")

        return ICMeetingResponse(
            symbol=meeting_result["symbol"],
            stock_name=meeting_result["stock_name"],
            current_price=meeting_result["current_price"],
            verdict_chinese=meeting_result["verdict_chinese"],
            conviction_stars=meeting_result["conviction_stars"],
            cathie_wood=meeting_result["cathie_wood"],
            nancy_pelosi=meeting_result["nancy_pelosi"],
            warren_buffett=meeting_result["warren_buffett"],
            final_verdict=meeting_result["final_verdict"],
            summary=summary,
            technical_score=meeting_result.get("technical_score"),
            fundamental_score=meeting_result.get("fundamental_score")
        )

    except Exception as e:
        print(f"[ERROR] IC meeting failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/committee/meeting", response_model=CommitteeResponse)
async def conduct_committee_meeting(request: CommitteeRequest):
    """
    召开三方博弈会议

    使用三个不同的AI模型进行多空对决：
    - 多头 (Qwen): A股顶级游资大佬
    - 空头 (DeepSeek): 量化做空机构
    - 裁判 (Zhipu): 首席投资官CIO

    流程：
    1. 加载市场快照数据
    2. 多空并行辩论
    3. 裁判长给出最终投资建议
    """
    try:
        print(f"[INFO] Committee meeting for: {request.symbol}")

        committee_service = CommitteeService()
        result = await committee_service.run_meeting(request.symbol)

        return CommitteeResponse(**result)

    except Exception as e:
        print(f"[ERROR] Committee meeting failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    uvicorn.run(app, host=host, port=port, reload=True)
