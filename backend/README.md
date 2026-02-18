# Backend - AShare Sentinel Pro API服务

## 🚀 快速启动

```bash
# 1. 进入后端目录
cd backend

# 2. 激活虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入Supabase配置

# 5. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📦 关键依赖

- FastAPI - Web框架
- Supabase Python Client - 数据库
- DeepSeek SDK - AI分析
- Tushare/Baostock - 数据源

## 🔧 配置文件

### `.env` 必需配置
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret
DEEPSEEK_API_KEY=your-deepseek-key
TUSHARE_TOKEN=your-tushare-token
TAVILY_API_KEY=your-tavily-key
```

### CORS配置
```
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## 🧪 测试

```bash
# 健康检查
curl http://localhost:8000/health

# IC投委会分析
curl -X POST http://localhost:8000/api/v1/ic/meeting \
  -H "Content-Type: application/json" \
  -d '{"symbol":"688019"}'
```

## 🐛 常见问题

### 1. Python缓存导致代码不更新
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 2. Supabase连接失败
- 检查 `.env` 中的 `SUPABASE_URL` 和 `SUPABASE_SERVICE_KEY`
- 确认Supabase项目已启动

### 3. 端口被占用
```bash
# 查找占用8000端口的进程
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# 杀死进程
kill -9 <PID>  # Linux/Mac
taskkill /F /PID <PID>  # Windows
```

## 📊 数据库

- **类型**: Supabase (PostgreSQL)
- **Schema**: `backend/supabase_schema.sql`
- **Repository**: `backend/app/repositories/supabase_repository.py`

## 🔄 代码结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI主入口
│   ├── core/
│   │   ├── config.py           # 配置管理
│   │   └── db_supabase.py      # Supabase连接
│   ├── repositories/
│   │   └── supabase_repository.py  # 数据访问层
│   ├── services/
│   │   ├── ic_service.py       # IC投委会核心逻辑
│   │   └── data_fetcher.py     # 数据获取
│   └── models/                 # Pydantic模型
├── tests/                      # 测试代码
├── .env                        # 环境变量（不提交）
├── requirements.txt            # Python依赖
└── supabase_schema.sql         # 数据库Schema
```

## ⚠️ 重要规则

1. **永远使用Supabase，不要使用MySQL**
2. **处理百分比数据时使用 `safe_float_convert()`**
3. **修改代码后必须清理缓存并重启**
4. **返回数据必须包含 `advanced_metrics` 字段**

## 🔍 日志

后端日志会输出到控制台，关键信息：
- `[ARCHIVE]` - 数据保存日志
- `[ERROR]` - 错误日志
- `[SUCCESS]` - 成功日志
