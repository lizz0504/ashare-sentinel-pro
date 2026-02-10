# Guru Watcher - 大V交易信号监控模块

## 模块概述

Guru Watcher 是一个完整的投资大V交易信号监控系统，能够：
1. 从雪球等平台抓取大V动态
2. 使用 AI 自动提取交易信号
3. 存储到 Supabase 数据库
4. 提供聚合分析和情绪监控

## 文件结构

```
backend/app/
├── config/
│   ├── __init__.py
│   └── guru_sources.py       # 11位大V RSS 源配置
├── models/
│   ├── __init__.py
│   └── guru.py              # 数据模型（已存在）
│   └── guru_signal.py       # SQLAlchemy 模型
├── services/
│   ├── rss_fetcher.py       # RSS 抓取服务
│   ├── mock_rss.py          # Mock 数据源
│   ├── hybrid_fetcher.py    # 混合抓取服务
│   ├── guru_service.py      # 主服务（已存在）
│   └── guru_watcher.py      # 原有服务
└── supabase_guru_setup.sql  # 数据库创建脚本
```

## 预定义的 11 位大V

| 分类 | 大V | 特点 |
|------|-----|------|
| 顶级多头 | 但斌 | 主线极度坚定派 |
| 行业专家 | 逸修 | 互联网/港股 |
| 行业专家 | 卢桂凤 | 医药方向 |
| 行业专家 | 郭荆璞 | 周期/卖方视角 |
| 市场情绪 | 阿狸 (期货踩坑) | 期货踩坑实盘 |
| 市场情绪 | 阿狸 (消费观察) | 消费赛道观察 |
| 市场情绪 | 庶人哑士 | 消费+情绪分析 |
| 深度价投 | 滇南王 | 深度价值投资 |
| 深度价投 | 巍巍昆仑侠 | 低估值/红利策略 |
| 深度价投 | 边城浪子1986 | 低估+风口捕捉 |
| 认知周期 | 三体人在地球 | 认知演习与博弈 |
| 认知周期 | 静待花开十八载 | 制造周期研究 |

## 数据库配置

### 1. 在 Supabase SQL Editor 中运行以下脚本

```sql
-- 创建 guru_signals 表
CREATE TABLE IF NOT EXISTS guru_signals (
    id BIGSERIAL PRIMARY KEY,
    guru_name VARCHAR(100) NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'Xueqiu',
    source_link TEXT UNIQUE,
    source_id VARCHAR(255) UNIQUE,
    raw_text TEXT NOT NULL,
    publish_time TIMESTAMP WITH TIME ZONE,
    mentioned_symbols TEXT[],
    sentiment VARCHAR(20),
    action VARCHAR(20),
    summary TEXT,
    entry_point TEXT,
    stop_loss TEXT,
    target_price TEXT,
    time_horizon VARCHAR(20),
    position_size TEXT,
    reasoning TEXT,
    related_themes TEXT[],
    key_factors TEXT[],
    confidence_score FLOAT DEFAULT 0.8,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_guru_signals_guru_name ON guru_signals(guru_name);
CREATE INDEX IF NOT EXISTS idx_guru_signals_symbol ON guru_signals USING GIN(mentioned_symbols);
CREATE INDEX IF NOT EXISTS idx_guru_signals_sentiment ON guru_signals(sentiment);
CREATE INDEX IF NOT EXISTS idx_guru_signals_publish_time ON guru_signals(publish_time DESC);

-- 创建更新时间触发器
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
```

## API 端点

### V1 API（原有）
- `GET /api/v1/guru/test` - 测试接口
- `POST /api/v1/guru/process-feeds` - 处理订阅源
- `GET /api/v1/guru/signals` - 获取所有信号
- `GET /api/v1/guru/signal/{symbol}` - 获取股票聚合情绪
- `GET /api/v1/guru/guru/{guru_name}` - 获取大V信号

### V2 API（新增，数据库集成）
- `POST /api/v2/guru/collect` - 触发数据采集
- `GET /api/v2/guru/signals` - 获取信号列表（支持筛选）
- `GET /api/v2/guru/trending` - 获取热门股票
- `GET /api/v2/guru/sentiment/{symbol}` - 获取聚合情绪
- `GET /api/v2/guru/gurus` - 获取活跃大V

## 测试

### 运行测试脚本

```bash
# 测试混合抓取服务
python backend/app/services/hybrid_fetcher.py

# 测试数据库集成
python backend/test_guru_db.py

# 打印大V列表
python backend/app/config/guru_sources.py
```

## 前端页面

访问 http://localhost:3001/dashboard/guru 查看 Guru Watcher 前端界面。

## RSSHub 注意事项

公共 RSSHub 实例可能限制访问，解决方法：

1. **自建 RSSHub 实例**（推荐）
   ```bash
   docker run -d --name rsshub -p 1200:1200 diygod/rsshub
   ```
   然后修改 RSS URL 为 `http://localhost:1200/xueqiu/user/{UID}`

2. **使用 Mock 数据**
   当前已实现自动降级，RSS 失败时使用模拟数据。

## 下一步

1. 在 Supabase 中创建数据库表
2. 运行测试脚本验证功能
3. 部署后端服务
4. 在前端页面中测试完整流程
