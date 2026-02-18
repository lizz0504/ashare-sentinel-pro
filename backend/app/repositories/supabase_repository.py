"""
Supabase 版本化 Repository

使用 Supabase 替代 MySQL 存储和分析历史记录
"""

import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import Client

from app.models.versioning import (
    StockCreate, StockUpdate, StockResponse,
    ReportCreate, ReportResponse,
    SuggestionEnum
)


class StockRepository:
    """股票仓库（Supabase 版本）"""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client

    async def create(self, stock: StockCreate) -> StockResponse:
        """创建或更新股票记录"""
        # 检查是否已存在
        existing = await self.get_by_code(stock.code)

        stock_data = {
            "code": stock.code,
            "name": stock.name,
            "current_price": stock.current_price,
            "change_percent": stock.change_percent,
            "turnover_rate": stock.turnover_rate,
            "updated_at": datetime.utcnow().isoformat()
        }

        if existing:
            # 更新
            response = self.client.table('stocks').update(stock_data).eq('code', stock.code).execute()
            return self._to_stock_response(response.data[0])
        else:
            # 创建
            response = self.client.table('stocks').insert(stock_data).execute()
            return self._to_stock_response(response.data[0])

    async def get_by_code(self, code: str) -> Optional[StockResponse]:
        """根据股票代码查询"""
        response = self.client.table('stocks').select("*").eq('code', code).execute()

        if response.data:
            return self._to_stock_response(response.data[0])
        return None

    async def update_latest_scores(
        self,
        code: str,
        score_growth: Optional[int] = None,
        score_value: Optional[int] = None,
        score_technical: Optional[int] = None,
        suggestion: Optional[SuggestionEnum] = None,
        conviction: Optional[str] = None
    ):
        """更新最新评分和建议"""
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }

        if score_growth is not None:
            update_data['score_growth'] = score_growth
        if score_value is not None:
            update_data['score_value'] = score_value
        if score_technical is not None:
            update_data['score_technical'] = score_technical
        if suggestion is not None:
            update_data['latest_suggestion'] = suggestion.value
        if conviction is not None:
            update_data['latest_conviction'] = conviction

        self.client.table('stocks').update(update_data).eq('code', code).execute()

    def _to_stock_response(self, data: Dict) -> StockResponse:
        """转换为 StockResponse 模型"""
        return StockResponse(
            id=data.get('id'),
            code=data.get('code'),
            name=data.get('name'),
            industry=data.get('industry'),
            sector=data.get('sector'),
            current_price=float(data['current_price']) if data.get('current_price') else None,
            change_percent=float(data['change_percent']) if data.get('change_percent') else None,
            turnover_rate=float(data['turnover_rate']) if data.get('turnover_rate') else None,
            score_growth=data.get('score_growth'),
            score_value=data.get('score_value'),
            score_technical=data.get('score_technical'),
            latest_suggestion=data.get('latest_suggestion'),
            latest_conviction=data.get('latest_conviction'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


class ReportRepository:
    """报告仓库（Supabase 版本）"""

    def __init__(self, supabase_client: Client):
        self.client = supabase_client

    async def create(self, report: ReportCreate) -> ReportResponse:
        """创建新报告"""
        # 生成版本ID（使用时间戳 + UUID）
        version_id = f"v1_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        report_data = {
            "id": str(uuid.uuid4()),
            "stock_code": report.stock_code,
            "stock_name": report.stock_name or "",
            "version_id": version_id,
            "content": report.content,
            "cathie_wood_analysis": report.cathie_wood_analysis,
            "nancy_pelosi_analysis": report.nancy_pelosi_analysis,
            "warren_buffett_analysis": report.warren_buffett_analysis,
            "charlie_munger_analysis": report.charlie_munger_analysis,
            "score_growth": report.score_growth,
            "score_value": report.score_value,
            "score_technical": report.score_technical,
            "composite_score": (report.score_growth + report.score_value + report.score_technical) // 3
                                if all([report.score_growth, report.score_value, report.score_technical])
                                else None,
            "verdict": report.verdict.value if isinstance(report.verdict, SuggestionEnum) else report.verdict,
            "conviction_level": report.conviction_level,
            "conviction_stars": report.conviction_stars,
            "financial_data": report.financial_data,
            "created_at": datetime.utcnow().isoformat()
        }

        response = self.client.table('reports').insert(report_data).execute()

        print(f"[ARCHIVE] Report saved to Supabase: {version_id}, stock: {report.stock_code}")

        return self._to_report_response(response.data[0])

    async def get_by_id(self, report_id: str) -> Optional[ReportResponse]:
        """根据ID查询报告"""
        response = self.client.table('reports').select("*").eq('id', report_id).execute()

        if response.data:
            return self._to_report_response(response.data[0])
        return None

    async def get_by_stock_code(
        self,
        stock_code: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[ReportResponse]:
        """查询某股票的所有报告（按时间倒序）"""
        response = self.client.table('reports') \
            .select("*") \
            .eq('stock_code', stock_code) \
            .order('created_at', desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return [self._to_report_response(item) for item in response.data]

    async def get_latest_by_stock(self, stock_code: str) -> Optional[ReportResponse]:
        """获取某股票的最新报告"""
        response = self.client.table('reports') \
            .select("*") \
            .eq('stock_code', stock_code) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()

        if response.data:
            return self._to_report_response(response.data[0])
        return None

    def _to_report_response(self, data: Dict) -> ReportResponse:
        """转换为 ReportResponse 模型"""
        return ReportResponse(
            id=data.get('id'),
            stock_code=data.get('stock_code'),
            stock_name=data.get('stock_name'),
            version_id=data.get('version_id'),
            content=data.get('content'),
            cathie_wood_analysis=data.get('cathie_wood_analysis'),
            nancy_pelosi_analysis=data.get('nancy_pelosi_analysis'),
            warren_buffett_analysis=data.get('warren_buffett_analysis'),
            charlie_munger_analysis=data.get('charlie_munger_analysis'),
            score_growth=data.get('score_growth'),
            score_value=data.get('score_value'),
            score_technical=data.get('score_technical'),
            verdict=data.get('verdict'),
            conviction_level=data.get('conviction_level'),
            conviction_stars=data.get('conviction_stars'),
            financial_data=data.get('financial_data'),
            created_at=data.get('created_at')
        )
