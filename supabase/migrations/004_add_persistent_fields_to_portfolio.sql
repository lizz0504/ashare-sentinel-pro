-- Add persistent technical analysis fields to portfolio table
-- This migration adds fields to cache the last known price and health score
-- for instant page loading (Phase 1), with background updates (Phase 2)

-- Add last_price field to store the most recent price
ALTER TABLE portfolio
ADD COLUMN IF NOT EXISTS last_price DECIMAL(12, 4);

-- Add last_health_score field to store the most recent health score
ALTER TABLE portfolio
ADD COLUMN IF NOT EXISTS last_health_score INTEGER;

-- Add last_updated_at field to track when the technical data was last updated
ALTER TABLE portfolio
ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMPTZ;

-- Add index on last_updated_at for querying stale data
CREATE INDEX IF NOT EXISTS idx_portfolio_last_updated ON portfolio(last_updated_at DESC);

-- Add comment for documentation
COMMENT ON COLUMN portfolio.last_price IS '最后一次更新的股价（用于缓存）';
COMMENT ON COLUMN portfolio.last_health_score IS '最后一次更新的健康评分（用于缓存）';
COMMENT ON COLUMN portfolio.last_updated_at IS '技术数据最后更新时间';
