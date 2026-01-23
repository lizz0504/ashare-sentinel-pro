-- Portfolio Management Tables Migration
-- This migration creates tables for smart portfolio management

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Portfolio table: Stores user's stock holdings
CREATE TABLE IF NOT EXISTS portfolio (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  symbol VARCHAR(20) NOT NULL,              -- Stock symbol (e.g., "AAPL", "TSLA")
  name VARCHAR(200),                        -- Company name (fetched from yfinance)
  sector VARCHAR(100),                      -- Chinese sector (e.g., "半导体", "新能源")
  industry VARCHAR(100),                    -- Chinese industry (e.g., "半导体设备", "锂电池")
  cost_basis DECIMAL(12, 4),                -- Cost basis per share
  shares INTEGER DEFAULT 1,                 -- Number of shares
  notes TEXT,                               -- User notes
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on symbol for faster lookups
CREATE INDEX IF NOT EXISTS idx_portfolio_symbol ON portfolio(symbol);

-- Create index on sector for grouping
CREATE INDEX IF NOT EXISTS idx_portfolio_sector ON portfolio(sector);

-- Weekly reviews table: Stores AI-generated weekly performance reviews
CREATE TABLE IF NOT EXISTS weekly_reviews (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  portfolio_id UUID REFERENCES portfolio(id) ON DELETE CASCADE,
  review_date DATE NOT NULL,                -- Date of the review
  start_price DECIMAL(12, 4),               -- Price at start of week
  end_price DECIMAL(12, 4),                 -- Price at end of week
  price_change_pct DECIMAL(8, 4),           -- Percentage change
  ai_analysis TEXT,                         -- AI-generated review (100 words)
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on review_date for querying by week
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_date ON weekly_reviews(review_date DESC);

-- Create index on portfolio_id for faster joins
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_portfolio_id ON weekly_reviews(portfolio_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER update_portfolio_updated_at
  BEFORE UPDATE ON portfolio
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE portfolio ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reviews ENABLE ROW LEVEL SECURITY;

-- For now, allow all operations (in production, implement proper user auth)
CREATE POLICY "Enable all access for portfolio" ON portfolio
  FOR ALL USING (true);

CREATE POLICY "Enable all access for weekly_reviews" ON weekly_reviews
  FOR ALL USING (true);
