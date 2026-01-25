-- ============================================
-- AShare Sentinel Pro - 数据库初始化脚本
-- 在 Supabase SQL Editor 中运行此脚本
-- ============================================

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Portfolio Table (投资组合表)
-- ============================================
CREATE TABLE IF NOT EXISTS portfolio (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  symbol VARCHAR(20) NOT NULL,
  name VARCHAR(200),
  sector VARCHAR(100),
  industry VARCHAR(100),
  cost_basis DECIMAL(12, 4),
  shares INTEGER DEFAULT 1,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_portfolio_symbol ON portfolio(symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_sector ON portfolio(sector);

-- ============================================
-- Weekly Reviews Table (周度复盘表)
-- ============================================
CREATE TABLE IF NOT EXISTS weekly_reviews (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  portfolio_id UUID REFERENCES portfolio(id) ON DELETE CASCADE,
  review_date DATE NOT NULL,
  start_price DECIMAL(12, 4),
  end_price DECIMAL(12, 4),
  price_change_pct DECIMAL(8, 4),
  ai_analysis TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_date ON weekly_reviews(review_date DESC);
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_portfolio_id ON weekly_reviews(portfolio_id);

-- ============================================
-- Reports Table (研报主表)
-- ============================================
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    file_size INTEGER,
    summary TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID,

    CONSTRAINT status_check CHECK (status IN ('processing', 'completed', 'failed'))
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_uploaded_at ON reports(uploaded_at DESC);

-- ============================================
-- Report Chunks Table (研报分块)
-- ============================================
CREATE TABLE IF NOT EXISTS report_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT report_page_unique UNIQUE (report_id, page_number)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_report_chunks_report_id ON report_chunks(report_id);

-- ============================================
-- Trigger Function (自动更新 updated_at)
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为 portfolio 表创建触发器
CREATE TRIGGER update_portfolio_updated_at
    BEFORE UPDATE ON portfolio
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为 reports 表创建触发器
CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- RLS (Row Level Security) - 开发环境允许所有访问
-- ============================================
-- Portfolio 表
ALTER TABLE portfolio ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable all access for portfolio" ON portfolio
  FOR ALL USING (true);

-- Weekly Reviews 表
ALTER TABLE weekly_reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable all access for weekly_reviews" ON weekly_reviews
  FOR ALL USING (true);

-- Reports 表
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable all access for reports" ON reports
  FOR ALL USING (true);

-- Report Chunks 表
ALTER TABLE report_chunks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable all access for report_chunks" ON report_chunks
  FOR ALL USING (true);

-- ============================================
-- 完成
-- ============================================
-- 数据库表创建完成！
