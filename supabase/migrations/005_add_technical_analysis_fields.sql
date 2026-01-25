-- Add comprehensive technical analysis fields to portfolio table
-- This allows Phase 1.5 to display complete technical data immediately without waiting for Phase 2

-- Add technical analysis fields to portfolio table
ALTER TABLE portfolio
ADD COLUMN IF NOT EXISTS tech_ma20_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS tech_ma5_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS tech_volume_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS tech_volume_change_pct DECIMAL(8, 4),
ADD COLUMN IF NOT EXISTS tech_alpha DECIMAL(8, 4),
ADD COLUMN IF NOT EXISTS tech_k_line_pattern VARCHAR(50),
ADD COLUMN IF NOT EXISTS tech_pattern_signal VARCHAR(20),
ADD COLUMN IF NOT EXISTS tech_action_signal VARCHAR(20),
ADD COLUMN IF NOT EXISTS tech_analysis_date DATE;

-- Add comment for documentation
COMMENT ON COLUMN portfolio.tech_ma20_status IS 'MA20均线状态（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_ma5_status IS 'MA5均线状态（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_volume_status IS '量能状态（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_volume_change_pct IS '量能变化百分比（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_alpha IS '超额收益（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_k_line_pattern IS 'K线形态（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_pattern_signal IS '形态信号（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_action_signal IS '操作建议（技术分析缓存）';
COMMENT ON COLUMN portfolio.tech_analysis_date IS '技术分析日期';
