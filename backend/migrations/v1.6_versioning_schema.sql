-- ============================================================================
-- V1.6: 版本化管理数据模型迁移
-- 支持 IC 投委会报告多版本存档和股票去重
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. 创建 stocks 表 (主表) - 存储股票基本信息和最新状态
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stocks (
    -- 主键: 股票代码
    code VARCHAR(10) PRIMARY KEY COMMENT '股票代码 (如: 002050, 600519)',

    -- 基本信息
    name VARCHAR(50) NOT NULL COMMENT '股票名称',
    market VARCHAR(10) DEFAULT 'A' COMMENT '市场类型: A/H/US',
    industry VARCHAR(50) COMMENT '所属行业',
    sector VARCHAR(50) COMMENT '所属板块',

    -- 最新行情 (冗余存储，用于快速展示)
    current_price DECIMAL(10, 2) DEFAULT NULL COMMENT '当前价格',
    change_percent DECIMAL(10, 2) DEFAULT NULL COMMENT '涨跌幅 (%)',
    turnover_rate DECIMAL(10, 2) DEFAULT NULL COMMENT '换手率 (%)',

    -- 最新报告分值 (冗余存储，用于 Dashboard 快速查询)
    latest_score_growth INT DEFAULT NULL COMMENT '最新成长得分 (Cathie)',
    latest_score_value INT DEFAULT NULL COMMENT '最新价值得分 (Warren)',
    latest_score_technical INT DEFAULT NULL COMMENT '最新技术得分 (Nancy)',

    -- 最新建议
    latest_suggestion VARCHAR(20) DEFAULT NULL COMMENT '最新建议: BUY/HOLD/SELL',
    latest_conviction VARCHAR(10) DEFAULT NULL COMMENT '信心程度: */***/*****/*****',

    -- 时间戳
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    -- 索引
    INDEX idx_market (market),
    INDEX idx_industry (industry),
    INDEX idx_updated (updated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票主表 - 存储基本信息和最新状态';


-- ----------------------------------------------------------------------------
-- 2. 创建 analysis_reports 表 (从表) - 存储历史分析报告
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_reports (
    -- 主键
    id UUID PRIMARY KEY DEFAULT (UUID()) COMMENT '报告唯一ID',

    -- 关联股票
    stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
    version_id VARCHAR(50) NOT NULL COMMENT '版本号: vYYYYMMDD_HHMM',

    -- 报告内容 (Markdown 格式)
    content TEXT COMMENT '专家辩论全文 (Markdown 格式)',

    -- 专家分析内容
    cathie_wood_analysis TEXT COMMENT 'Cathie Wood (成长投资) 观点',
    nancy_pelosi_analysis TEXT COMMENT 'Nancy Pelosi (技术面) 观点',
    warren_buffett_analysis TEXT COMMENT 'Warren Buffett (价值投资) 观点',
    charlie_munger_analysis TEXT COMMENT 'Charlie Munger (最终裁决) 观点',

    -- 分值数据
    score_growth INT DEFAULT NULL COMMENT '成长得分 (0-100)',
    score_value INT DEFAULT NULL COMMENT '价值得分 (0-100)',
    score_technical INT DEFAULT NULL COMMENT '技术得分 (0-100)',
    composite_score INT DEFAULT NULL COMMENT '综合得分',

    -- 评级和建议
    verdict VARCHAR(20) DEFAULT NULL COMMENT '最终评级: BUY/HOLD/SELL',
    conviction_level INT DEFAULT NULL COMMENT '信心等级 (1-5)',
    conviction_stars VARCHAR(10) DEFAULT NULL COMMENT '信心星级: */***/*****/*****',

    -- 财务指标快照 (用于历史对比)
    financial_data JSON COMMENT '财务指标快照 (PE/PB/ROE/营收增长率等)',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '报告创建时间',

    -- 外键约束
    FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE,

    -- 唯一约束: 每个股票的每个版本号唯一
    UNIQUE KEY uk_stock_version (stock_code, version_id),

    -- 索引: 优化历史时间轴查询
    INDEX idx_stock_created (stock_code, created_at DESC),
    INDEX idx_created (created_at DESC),
    INDEX idx_verdict (verdict),
    INDEX idx_score_growth (score_growth),
    INDEX idx_score_value (score_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析报告表 - 存储历史分析报告';


-- ----------------------------------------------------------------------------
-- 3. 创建触发器 - 更新 stocks 表的最新状态
-- ----------------------------------------------------------------------------
DELIMITER $$

CREATE TRIGGER trg_update_latest_report
AFTER INSERT ON analysis_reports
FOR EACH ROW
BEGIN
    -- 当插入新报告时，自动更新 stocks 表的最新状态
    UPDATE stocks
    SET
        latest_score_growth = NEW.score_growth,
        latest_score_value = NEW.score_value,
        latest_score_technical = NEW.score_technical,
        latest_suggestion = NEW.verdict,
        latest_conviction = NEW.conviction_stars,
        updated_at = CURRENT_TIMESTAMP
    WHERE code = NEW.stock_code;
END$$

DELIMITER ;


-- ----------------------------------------------------------------------------
-- 4. 创建视图 - 报告历史列表查询
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_report_history AS
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
    -- 计算与当前价格的变化
    s.current_price,
    s.change_percent
FROM analysis_reports r
JOIN stocks s ON r.stock_code = s.code
ORDER BY r.stock_code, r.created_at DESC;


-- ----------------------------------------------------------------------------
-- 5. 创建视图 - Dashboard 股票列表
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_dashboard_stocks AS
SELECT
    code,
    name,
    market,
    industry,
    current_price,
    change_percent,
    turnover_rate,
    latest_score_growth,
    latest_score_value,
    latest_score_technical,
    latest_suggestion,
    latest_conviction,
    -- 计算综合得分
    (IFNULL(latest_score_growth, 50) + IFNULL(latest_score_value, 50)) / 2 AS composite_score,
    -- 最新报告时间
    (SELECT MAX(created_at) FROM analysis_reports WHERE stock_code = stocks.code) AS latest_report_time,
    -- 报告数量
    (SELECT COUNT(*) FROM analysis_reports WHERE stock_code = stocks.code) AS report_count,
    updated_at
FROM stocks
WHERE latest_suggestion IS NOT NULL
ORDER BY updated_at DESC;


-- ----------------------------------------------------------------------------
-- 6. 初始化示例数据 (可选)
-- ----------------------------------------------------------------------------
-- 插入测试股票
INSERT INTO stocks (code, name, market, industry, current_price, change_percent)
VALUES
    ('002050', '三花智控', 'A', '制冷设备', 53.48, -1.25),
    ('600519', '贵州茅台', 'A', '白酒', 1530.00, 0.85)
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- ============================================================================
-- 迁移完成
-- ============================================================================
