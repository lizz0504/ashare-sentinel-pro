-- ============================================
-- Guru Watcher - Supabase Database Setup
-- ============================================
-- 在 Supabase SQL Editor 中运行此脚本以创建必要的表和索引

-- 1. 创建 guru_signals 表 (存储大V交易信号)
CREATE TABLE IF NOT EXISTS guru_signals (
    id BIGSERIAL PRIMARY KEY,
    guru_name VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'Xueqiu',
    source_link TEXT UNIQUE,
    source_id VARCHAR(255) UNIQUE,

    -- 原始内容
    raw_text TEXT NOT NULL,
    publish_time TIMESTAMP WITH TIME ZONE,

    -- AI 提取的数据
    mentioned_symbols TEXT[],  -- PostgreSQL 数组类型，存储股票代码
    sentiment VARCHAR(20),
    action VARCHAR(20),
    summary TEXT,

    -- 交易观点
    entry_point TEXT,
    stop_loss TEXT,
    target_price TEXT,
    time_horizon VARCHAR(20),
    position_size TEXT,
    reasoning TEXT,

    -- 相关信息
    related_themes TEXT[],
    key_factors TEXT[],
    confidence_score FLOAT DEFAULT 0.8,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_guru_signals_guru_name ON guru_signals(guru_name);
CREATE INDEX IF NOT EXISTS idx_guru_signals_symbol ON guru_signals USING GIN(mentioned_symbols);
CREATE INDEX IF NOT EXISTS idx_guru_signals_sentiment ON guru_signals(sentiment);
CREATE INDEX IF NOT EXISTS idx_guru_signals_publish_time ON guru_signals(publish_time DESC);
CREATE INDEX IF NOT EXISTS idx_guru_signals_created_at ON guru_signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_guru_signals_source_id ON guru_signals(source_id);

-- 3. 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_guru_signals_updated_at
    BEFORE UPDATE ON guru_signals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 4. 创建 guru_profiles 表 (大V基本信息)
CREATE TABLE IF NOT EXISTS guru_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'Xueqiu',
    platform_id VARCHAR(100) UNIQUE,  -- 雪球 UID
    description TEXT,
    followers_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. 创建触发器
CREATE TRIGGER update_guru_profiles_updated_at
    BEFORE UPDATE ON guru_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 6. 插入预定义的11位大V
INSERT INTO guru_profiles (name, platform, platform_id, description) VALUES
    ('但斌', 'Xueqiu', 'danbin', '深圳东方港湾投资董事长，价值投资代表'),
    ('梁宏', 'Xueqiu', 'lianghong', '希瓦资产创始人，半导体专家'),
    ('耐力投资', 'Xueqiu', 'naili', '长期价值投资者'),
    ('管我财', 'Xueqiu', 'guanwo', '量化交易专家'),
    ('省心省力', 'Xueqiu', 'shengxin', '波段交易高手'),
    ('处镜如初', 'Xueqiu', 'chujing', '趋势投资者'),
    ('徐翔', 'Xueqiu', 'xuxiang', '曾经的私募一哥'),
    ('林园', 'Xueqiu', 'linyuan', '林园投资董事长'),
    ('冯柳', 'Xueqiu', 'fengliu', '高毅资产基金经理'),
    ('张坤', 'Xueqiu', 'zhangkun', '易方达基金经理'),
    ('刘彦春', 'Xueqiu', 'liuyanchun', '景顺长城基金经理')
ON CONFLICT (name) DO NOTHING;

-- 7. 启用 Row Level Security (RLS) - 可选
-- ALTER TABLE guru_signals ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE guru_profiles ENABLE ROW LEVEL SECURITY;

-- 8. 创建查询视图
CREATE OR REPLACE VIEW v_guru_signals_summary AS
SELECT
    id,
    guru_name,
    platform,
    mentioned_symbols,
    sentiment,
    action,
    summary,
    publish_time,
    created_at
FROM guru_signals
ORDER BY publish_time DESC;

-- 9. 创建聚合统计视图
CREATE OR REPLACE VIEW v_guru_stats AS
SELECT
    guru_name,
    COUNT(*) as total_signals,
    COUNT(DISTINCT unnest(mentioned_symbols)) as unique_symbols_mentioned,
    MAX(publish_time) as last_signal_time,
    COUNT(*) FILTER (WHERE sentiment = 'Bullish') as bullish_count,
    COUNT(*) FILTER (WHERE sentiment = 'Bearish') as bearish_count,
    COUNT(*) FILTER (WHERE sentiment = 'Neutral') as neutral_count
FROM guru_signals
GROUP BY guru_name;

-- 10. 创建热门股票视图
CREATE OR REPLACE VIEW v_trending_symbols AS
SELECT
    unnest(mentioned_symbols) as symbol,
    COUNT(*) as mention_count,
    COUNT(DISTINCT guru_name) as unique_guru_count,
    MAX(publish_time) as last_mention_time
FROM guru_signals
WHERE mentioned_symbols IS NOT NULL
GROUP BY unnest(mentioned_symbols)
ORDER BY mention_count DESC;
