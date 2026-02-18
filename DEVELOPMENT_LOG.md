# AShare Sentinel Pro - 开发日志

**目的**: 记录项目关键配置和已修复问题，防止功能回滚和Bug复现

**最后更新**: 2026-02-18

---

## 🔴 终极状态定义 (修改代码前必须遵守)

### 1. 前端配置
- **API端口**: `NEXT_PUBLIC_API_URL=http://localhost:8000` (不是8001!)
- **Supabase**: 使用 `frontend/.env.local` 中的配置
- **硬刷新**: 修改前端代码后，必须使用 `Ctrl + Shift + R` 清除缓存

### 2. 后端配置
- **数据库**: Supabase (不是MySQL!)
- **连接模块**: `backend/app/core/db_supabase.py`
- **Repository**: `backend/app/repositories/supabase_repository.py`
- **环境变量**: `backend/.env` 必须包含:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY`
  - `SUPABASE_JWT_SECRET`

### 3. IC投委会返回数据结构
`/api/v1/ic/meeting` 必须包含:
```json
{
  "symbol": "string",
  "stock_name": "string",
  "current_price": number,
  "verdict_chinese": "string",
  "conviction_stars": "string",
  "technical_score": number,
  "fundamental_score": number,
  "advanced_metrics": {
    "radar": {
      "value_score": number,
      "growth_score": number,
      "safety_score": number,
      "dividend_score": number,
      "trend_score": number
    }
  },
  "saved_to_db": true
}
```

### 4. 数据转换安全规则
**永远使用安全函数处理百分比和字符串**:
```python
def safe_float_convert(value, default=0):
    if value is None or value == 'N/A':
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace('%', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default
```

### 5. Python缓存管理
**遇到奇怪的代码问题时，执行**:
```bash
cd backend
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
uvicorn app.main:app --reload
```

---

## 🟢 已修复问题记录

### 问题1: 雷达图所有股票显示一样
- **日期**: 2026-02-18
- **原因**: 后端没有返回 `advanced_metrics` 字段
- **修复**: 在 `main.py` line 1377-1415 添加雷达图数据计算
- **文件**: `backend/app/main.py`
- **状态**: ✅ 已修复

### 问题2: 前端API连接失败 (Failed to fetch)
- **日期**: 2026-02-18
- **原因**: `.env.local` 配置了8001端口，但后端在8000
- **修复**: 修改 `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **文件**: `frontend/.env.local`
- **状态**: ✅ 已修复

### 问题3: IC投委会数据类型转换错误
- **日期**: 2026-02-18
- **原因**: `float()` 无法处理 "4.6%" 这样的百分比字符串
- **修复**: 使用 `safe_float_convert()` 函数
- **文件**: `backend/app/main.py`
- **状态**: ✅ 已修复

### 问题4: MySQL到Supabase迁移
- **日期**: 2026-02-17
- **原因**: 初始设计使用MySQL，应该统一为Supabase
- **修复**: 删除MySQL相关代码，改用Supabase
- **状态**: ✅ 已完成

---

## ⚠️ 代码修改检查清单

修改代码前:
- [ ] 阅读 `DEVELOPMENT_LOG.md` 确认不违反规则
- [ ] 使用 `Read` 工具完整读取文件，不要基于记忆修改
- [ ] 确认修改会影响哪些模块

修改代码后:
- [ ] 运行语法检查
- [ ] 清理Python缓存
- [ ] 重启后端验证
- [ ] 硬刷新浏览器 (`Ctrl + Shift + R`)
- [ ] 测试实际功能

---

## 🚀 快速命令

### 清理并重启后端
```bash
cd backend
find . -type d -name "__pycache__" -exec rm -rf {} +
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 测试后端健康
```bash
curl http://localhost:8000/health
```

### 硬刷新前端
- Windows/Linux: `Ctrl + Shift + R`
- Mac: `Cmd + Shift + R`

---

**重要**: 如果这个文档中的规则和代码不一致，以**代码实际运行结果**为准，并更新此文档！
