"""
数据库访问层 - V1.6 版本化管理

支持 IC 投委会报告多版本存档和股票去重的 CRUD 操作
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import json

from app.models.versioning import (
    StockCreate, StockUpdate, StockResponse,
    ReportCreate, ReportResponse, ReportListItem,
    DashboardStockItem, DashboardStats,
    ReportHistoryRequest, ReportHistoryResponse,
    SuggestionEnum, MarketEnum
)


class StockRepository:
    """股票数据仓库"""

    def __init__(self, db_conn):
        """初始化数据库连接"""
        self.db_conn = db_conn

    async def create(self, stock: StockCreate) -> StockResponse:
        """创建新股票"""
        cursor = self.db_conn.cursor()

        sql = """
            INSERT INTO stocks (code, name, market, industry, sector, current_price, change_percent, turnover_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                market = VALUES(market),
                industry = VALUES(industry),
                sector = VALUES(sector),
                current_price = VALUES(current_price),
                change_percent = VALUES(change_percent),
                turnover_rate = VALUES(turnover_rate)
        """

        cursor.execute(sql, (
            stock.code, stock.name, stock.market.value,
            stock.industry, stock.sector,
            stock.current_price, stock.change_percent, stock.turnover_rate
        ))
        self.db_conn.commit()

        return await self.get_by_code(stock.code)

    async def get_by_code(self, code: str) -> Optional[StockResponse]:
        """根据代码获取股票"""
        cursor = self.db_conn.cursor()

        sql = """
            SELECT
                s.*,
                (IFNULL(s.latest_score_growth, 50) + IFNULL(s.latest_score_value, 50)) / 2 AS composite_score,
                (SELECT MAX(created_at) FROM reports WHERE stock_code = s.code) AS latest_report_time,
                (SELECT COUNT(*) FROM reports WHERE stock_code = s.code) AS report_count
            FROM stocks s
            WHERE s.code = %s
        """

        cursor.execute(sql, (code,))
        row = cursor.fetchone()

        if row:
            return self._row_to_stock_response(row)
        return None

    async def get_all(
        self,
        market: Optional[MarketEnum] = None,
        industry: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockResponse]:
        """获取股票列表"""
        cursor = self.db_conn.cursor()

        conditions = []
        params = []

        if market:
            conditions.append("market = %s")
            params.append(market.value)

        if industry:
            conditions.append("industry = %s")
            params.append(industry)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT
                s.*,
                (IFNULL(s.latest_score_growth, 50) + IFNULL(s.latest_score_value, 50)) / 2 AS composite_score,
                (SELECT MAX(created_at) FROM reports WHERE stock_code = s.code) AS latest_report_time,
                (SELECT COUNT(*) FROM reports WHERE stock_code = s.code) AS report_count
            FROM stocks s
            WHERE {where_clause}
            ORDER BY s.updated_at DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])
        cursor.execute(sql, tuple(params))

        return [self._row_to_stock_response(row) for row in cursor.fetchall()]

    async def update(self, code: str, update: StockUpdate) -> Optional[StockResponse]:
        """更新股票信息"""
        cursor = self.db_conn.cursor()

        # 构建动态更新语句
        updates = []
        params = []

        if update.name is not None:
            updates.append("name = %s")
            params.append(update.name)

        if update.current_price is not None:
            updates.append("current_price = %s")
            params.append(update.current_price)

        if update.change_percent is not None:
            updates.append("change_percent = %s")
            params.append(update.change_percent)

        if update.turnover_rate is not None:
            updates.append("turnover_rate = %s")
            params.append(update.turnover_rate)

        if not updates:
            return await self.get_by_code(code)

        params.append(code)
        sql = f"UPDATE stocks SET {', '.join(updates)} WHERE code = %s"

        cursor.execute(sql, tuple(params))
        self.db_conn.commit()

        return await self.get_by_code(code)

    async def update_latest_scores(
        self,
        code: str,
        score_growth: Optional[int] = None,
        score_value: Optional[int] = None,
        score_technical: Optional[int] = None,
        suggestion: Optional[SuggestionEnum] = None,
        conviction: Optional[str] = None
    ) -> Optional[StockResponse]:
        """更新最新报告分值"""
        cursor = self.db_conn.cursor()

        updates = []
        params = []

        if score_growth is not None:
            updates.append("latest_score_growth = %s")
            params.append(score_growth)

        if score_value is not None:
            updates.append("latest_score_value = %s")
            params.append(score_value)

        if score_technical is not None:
            updates.append("latest_score_technical = %s")
            params.append(score_technical)

        if suggestion is not None:
            updates.append("latest_suggestion = %s")
            params.append(suggestion.value)

        if conviction is not None:
            updates.append("latest_conviction = %s")
            params.append(conviction)

        if not updates:
            return await self.get_by_code(code)

        params.append(code)
        sql = f"UPDATE stocks SET {', '.join(updates)} WHERE code = %s"

        cursor.execute(sql, tuple(params))
        self.db_conn.commit()

        return await self.get_by_code(code)

    async def delete(self, code: str) -> bool:
        """删除股票（级联删除相关报告）"""
        cursor = self.db_conn.cursor()

        sql = "DELETE FROM stocks WHERE code = %s"
        cursor.execute(sql, (code,))
        self.db_conn.commit()

        return cursor.rowcount > 0

    def _row_to_stock_response(self, row: Dict[str, Any]) -> StockResponse:
        """将数据库行转换为 StockResponse"""
        return StockResponse(
            code=row.get('code'),
            name=row.get('name'),
            market=MarketEnum(row.get('market', 'A')),
            industry=row.get('industry'),
            sector=row.get('sector'),
            current_price=row.get('current_price'),
            change_percent=row.get('change_percent'),
            turnover_rate=row.get('turnover_rate'),
            latest_score_growth=row.get('latest_score_growth'),
            latest_score_value=row.get('latest_score_value'),
            latest_score_technical=row.get('latest_score_technical'),
            latest_suggestion=SuggestionEnum(row['latest_suggestion']) if row.get('latest_suggestion') else None,
            latest_conviction=row.get('latest_conviction'),
            composite_score=int(row.get('composite_score', 0)) if row.get('composite_score') else None,
            latest_report_time=row.get('latest_report_time'),
            report_count=row.get('report_count', 0),
            updated_at=row.get('updated_at'),
            created_at=row.get('created_at')
        )


class ReportRepository:
    """分析报告数据仓库"""

    def __init__(self, db_conn):
        """初始化数据库连接"""
        self.db_conn = db_conn

    async def create(self, report: ReportCreate) -> ReportResponse:
        """创建新报告"""
        cursor = self.db_conn.cursor()

        # 生成版本号
        version_id = datetime.now().strftime("v%Y%m%d_%H%M")

        # 计算综合得分
        scores = [report.score_growth, report.score_value, report.score_technical]
        valid_scores = [s for s in scores if s is not None]
        composite_score = sum(valid_scores) // len(valid_scores) if valid_scores else None

        sql = """
            INSERT INTO reports
            (id, stock_code, stock_name, version_id, content,
             cathie_wood_analysis, nancy_pelosi_analysis, warren_buffett_analysis, charlie_munger_analysis,
             score_growth, score_value, score_technical, composite_score,
             verdict, conviction_level, conviction_stars, financial_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        report_id = str(uuid4())
        financial_json = json.dumps(report.financial_data) if report.financial_data else None

        cursor.execute(sql, (
            report_id, report.stock_code, report.stock_name, version_id, report.content,
            report.cathie_wood_analysis, report.nancy_pelosi_analysis,
            report.warren_buffett_analysis, report.charlie_munger_analysis,
            report.score_growth, report.score_value, report.score_technical, composite_score,
            report.verdict.value, report.conviction_level, report.conviction_stars,
            financial_json
        ))
        self.db_conn.commit()

        return await self.get_by_id(report_id)

    async def get_by_id(self, report_id: str) -> Optional[ReportResponse]:
        """根据 ID 获取报告"""
        cursor = self.db_conn.cursor()

        sql = """
            SELECT
                r.*,
                s.name AS stock_name,
                s.current_price,
                s.change_percent
            FROM reports r
            JOIN stocks s ON r.stock_code = s.code
            WHERE r.id = %s
        """

        cursor.execute(sql, (report_id,))
        row = cursor.fetchone()

        if row:
            return self._row_to_report_response(row)
        return None

    async def get_by_stock_code(
        self,
        stock_code: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[ReportListItem]:
        """获取股票的报告历史"""
        cursor = self.db_conn.cursor()

        sql = """
            SELECT
                r.id,
                r.stock_code,
                s.name AS stock_name,
                r.version_id,
                r.verdict,
                r.conviction_stars,
                r.score_growth,
                r.score_value,
                r.score_technical,
                r.composite_score,
                r.created_at,
                s.current_price,
                s.change_percent
            FROM reports r
            JOIN stocks s ON r.stock_code = s.code
            WHERE r.stock_code = %s
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(sql, (stock_code, limit, offset))

        return [self._row_to_report_list_item(row) for row in cursor.fetchall()]

    async def get_history(self, request: ReportHistoryRequest) -> ReportHistoryResponse:
        """获取报告历史（带筛选）"""
        cursor = self.db_conn.cursor()

        # 构建查询条件
        conditions = []
        params = []

        if request.stock_code:
            conditions.append("r.stock_code = %s")
            params.append(request.stock_code)

        if request.start_date:
            conditions.append("r.created_at >= %s")
            params.append(request.start_date)

        if request.end_date:
            conditions.append("r.created_at <= %s")
            params.append(request.end_date)

        if request.verdict:
            conditions.append("r.verdict = %s")
            params.append(request.verdict.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询总数
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM reports r
            WHERE {where_clause}
        """
        cursor.execute(count_sql, tuple(params))
        total_row = cursor.fetchone()
        total = total_row['total'] if total_row else 0

        # 查询数据
        params.extend([request.limit, request.offset])
        data_sql = f"""
            SELECT
                r.id,
                r.stock_code,
                s.name AS stock_name,
                r.version_id,
                r.verdict,
                r.conviction_stars,
                r.score_growth,
                r.score_value,
                r.score_technical,
                r.composite_score,
                r.created_at,
                s.current_price,
                s.change_percent
            FROM reports r
            JOIN stocks s ON r.stock_code = s.code
            WHERE {where_clause}
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(data_sql, tuple(params))
        reports = [self._row_to_report_list_item(row) for row in cursor.fetchall()]

        has_more = (request.offset + request.limit) < total

        return ReportHistoryResponse(
            total=total,
            reports=reports,
            has_more=has_more
        )

    async def get_latest_by_stock(self, stock_code: str) -> Optional[ReportResponse]:
        """获取股票的最新报告"""
        cursor = self.db_conn.cursor()

        sql = """
            SELECT
                r.*,
                s.name AS stock_name,
                s.current_price,
                s.change_percent
            FROM reports r
            JOIN stocks s ON r.stock_code = s.code
            WHERE r.stock_code = %s
            ORDER BY r.created_at DESC
            LIMIT 1
        """

        cursor.execute(sql, (stock_code,))
        row = cursor.fetchone()

        if row:
            return self._row_to_report_response(row)
        return None

    async def delete(self, report_id: str) -> bool:
        """删除报告"""
        cursor = self.db_conn.cursor()

        sql = "DELETE FROM reports WHERE id = %s"
        cursor.execute(sql, (report_id,))
        self.db_conn.commit()

        return cursor.rowcount > 0

    def _row_to_report_response(self, row: Dict[str, Any]) -> ReportResponse:
        """将数据库行转换为 ReportResponse"""
        # 解析财务数据 JSON
        financial_data = None
        if row.get('financial_data'):
            try:
                financial_data = json.loads(row['financial_data'])
            except:
                pass

        return ReportResponse(
            id=str(row.get('id')),
            stock_code=row.get('stock_code'),
            stock_name=row.get('stock_name'),
            version_id=row.get('version_id'),
            content=row.get('content'),
            cathie_wood_analysis=row.get('cathie_wood_analysis'),
            nancy_pelosi_analysis=row.get('nancy_pelosi_analysis'),
            warren_buffett_analysis=row.get('warren_buffett_analysis'),
            charlie_munger_analysis=row.get('charlie_munger_analysis'),
            score_growth=row.get('score_growth'),
            score_value=row.get('score_value'),
            score_technical=row.get('score_technical'),
            composite_score=row.get('composite_score'),
            verdict=SuggestionEnum(row.get('verdict')),
            conviction_level=row.get('conviction_level'),
            conviction_stars=row.get('conviction_stars'),
            financial_data=financial_data,
            created_at=row.get('created_at'),
            current_price=row.get('current_price'),
            change_percent=row.get('change_percent')
        )

    def _row_to_report_list_item(self, row: Dict[str, Any]) -> ReportListItem:
        """将数据库行转换为 ReportListItem"""
        return ReportListItem(
            id=str(row.get('id')),
            stock_code=row.get('stock_code'),
            stock_name=row.get('stock_name'),
            version_id=row.get('version_id'),
            verdict=SuggestionEnum(row.get('verdict')),
            conviction_stars=row.get('conviction_stars'),
            score_growth=row.get('score_growth'),
            score_value=row.get('score_value'),
            score_technical=row.get('score_technical'),
            composite_score=row.get('composite_score'),
            created_at=row.get('created_at'),
            current_price=row.get('current_price'),
            change_percent=row.get('change_percent')
        )


class DashboardRepository:
    """Dashboard 数据仓库"""

    def __init__(self, db_conn):
        """初始化数据库连接"""
        self.db_conn = db_conn

    async def get_stocks(
        self,
        limit: int = 50,
        offset: int = 0,
        suggestion: Optional[SuggestionEnum] = None
    ) -> List[DashboardStockItem]:
        """获取 Dashboard 股票列表"""
        cursor = self.db_conn.cursor()

        where_clause = ""
        params = []

        if suggestion:
            where_clause = "WHERE latest_suggestion = %s"
            params.append(suggestion.value)

        sql = f"""
            SELECT * FROM v_dashboard_stocks
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])
        cursor.execute(sql, tuple(params))

        return [self._row_to_dashboard_item(row) for row in cursor.fetchall()]

    async def get_stats(self) -> DashboardStats:
        """获取 Dashboard 统计数据"""
        cursor = self.db_conn.cursor()

        sql = """
            SELECT
                COUNT(DISTINCT code) as total_stocks,
                SUM(report_count) as total_reports,
                SUM(CASE WHEN latest_suggestion = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN latest_suggestion = 'HOLD' THEN 1 ELSE 0 END) as hold_count,
                SUM(CASE WHEN latest_suggestion = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                AVG(latest_score_growth) as avg_growth_score,
                AVG(latest_score_value) as avg_value_score
            FROM v_dashboard_stocks
        """

        cursor.execute(sql)
        row = cursor.fetchone()

        return DashboardStats(
            total_stocks=int(row.get('total_stocks', 0)),
            total_reports=int(row.get('total_reports', 0)),
            buy_count=int(row.get('buy_count', 0)),
            hold_count=int(row.get('hold_count', 0)),
            sell_count=int(row.get('sell_count', 0)),
            avg_growth_score=float(row.get('avg_growth_score')) if row.get('avg_growth_score') else None,
            avg_value_score=float(row.get('avg_value_score')) if row.get('avg_value_score') else None
        )

    def _row_to_dashboard_item(self, row: Dict[str, Any]) -> DashboardStockItem:
        """将数据库行转换为 DashboardStockItem"""
        return DashboardStockItem(
            code=row.get('code'),
            name=row.get('name'),
            market=MarketEnum(row.get('market', 'A')),
            industry=row.get('industry'),
            current_price=row.get('current_price'),
            change_percent=row.get('change_percent'),
            turnover_rate=row.get('turnover_rate'),
            latest_score_growth=row.get('latest_score_growth'),
            latest_score_value=row.get('latest_score_value'),
            latest_score_technical=row.get('latest_score_technical'),
            latest_suggestion=SuggestionEnum(row['latest_suggestion']) if row.get('latest_suggestion') else None,
            latest_conviction=row.get('latest_conviction'),
            composite_score=int(row.get('composite_score', 0)) if row.get('composite_score') else None,
            latest_report_time=row.get('latest_report_time'),
            report_count=int(row.get('report_count', 0)),
            updated_at=row.get('updated_at')
        )
