-- ============================================
-- AShare Sentinel Pro - Supabase 表结构
-- ============================================
-- 在 Supabase Dashboard -> SQL Editor 中执行此脚本
-- ============================================

-- 1. 创建 stocks 表（股票基本信息）
CREATE TABLE IF NOT EXISTS stocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    industry VARCHAR(100),
    sector VARCHAR(100),

    -- 价格信息
    current_price DECIMAL(10, 2),
    change_percent DECIMAL(10, 2),
    turnover_rate DECIMAL(10, 2),

    -- 评分
    score_growth INTEGER,
    score_value INTEGER,
    score_technical INTEGER,

    -- 最新建议
    latest_suggestion VARCHAR(20),
    latest_conviction VARCHAR(20),

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 全文搜索（可选）
    search_text TEXT GENERATED ALWAYS AS (
        code || ' ' || name || ' ' || COALESCE(industry, '')
    ) STORED
);

-- 2. 创建 reports 表（IC分析报告）
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,

    -- 版本控制
    version_id VARCHAR(50) UNIQUE NOT NULL,

    -- 分析内容
    content TEXT,

    -- 专家分析
    cathie_wood_analysis TEXT,
    nancy_pelosi_analysis TEXT,
    warren_buffett_analysis TEXT,
    charlie_munger_analysis TEXT,

    -- 评分
    score_growth INTEGER,
    score_value INTEGER,
    score_technical INTEGER,
    composite_score INTEGER,

    -- 最终建议
    verdict VARCHAR(20) NOT NULL,  -- BUY, HOLD, SELL
    conviction_level INTEGER,
    conviction_stars VARCHAR(20),

    -- 财务数据快照（JSON）
    financial_data JSONB,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 外键关联（可选）
    FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE
);

-- 3. 创建索引（提升查询性能）
CREATE INDEX IF NOT EXISTS idx_stocks_code ON stocks(code);
CREATE INDEX IF NOT EXISTS idx_stocks_name ON stocks(name);
CREATE INDEX IF NOT EXISTS idx_stocks_industry ON stocks(industry);

CREATE INDEX IF NOT EXISTS idx_reports_stock_code ON reports(stock_code);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_verdict ON reports(verdict);
CREATE INDEX IF NOT EXISTS idx_reports_compound_score ON reports(composite_score);

-- 4. 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_stocks_search ON stocks USING GIN(to_tsvector('english', search_text));

-- 5. 启用 Row Level Security (RLS) - 可选
ALTER TABLE stocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- 允许所有读取（公开访问）
CREATE POLICY "Allow public read access on stocks"
ON stocks FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow public read access on reports"
ON reports FOR SELECT
TO anon
USING (true);

-- 允许 service_role 进行所有操作
CREATE POLICY "Allow service_role all access on stocks"
ON stocks FOR ALL
TO service_role
USING (true);

CREATE POLICY "Allow service_role all access on reports"
ON reports FOR ALL
TO service_role
USING (true);

-- 6. 创建更新时间戳触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_stocks_updated_at
    BEFORE UPDATE ON stocks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 7. 添加注释
COMMENT ON TABLE stocks IS '股票基本信息表';
COMMENT ON TABLE reports IS 'IC投委会分析报告历史记录表';

COMMENT ON COLUMN reports.verdict IS '建议评级: BUY(买入), HOLD(持有), SELL(卖出)';
COMMENT ON COLUMN reports.conviction_stars IS '信心程度: *, **, ***, ****, *****';
