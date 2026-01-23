# AShare Sentinel Pro

> 智能A股投资复盘系统 - V1.0

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-15-black.svg)](https://nextjs.org/)

## 功能特性

### 📊 智能复盘
- **持仓管理** - 添加/删除A股持仓，实时追踪
- **技术分析** - MA5/MA20均线、Alpha超额收益、K线形态识别
- **健康评分** - 0-100分综合评分系统
- **市场情绪** - 基于沪深300的贪婪/恐慌指数

### 🤖 AI分析
- 自动生成周度复盘报告
- K线形态智能解读（金针探底、冲高回落等）
- 个性化投资建议（强烈买入/买入/持有/卖出/强烈卖出）
- 投资名言引用

### 📈 实时数据
- 集成AkShare获取实时股价
- 自动从AkShare获取股票名称和行业信息
- 支持个股刷新和批量刷新
- 生成可导出的文字报告

## 技术栈

### 前端
- **框架**: Next.js 15 + React 18
- **语言**: TypeScript
- **样式**: TailwindCSS
- **组件**: shadcn/ui

### 后端
- **框架**: FastAPI
- **语言**: Python 3.10+
- **数据**: AkShare + Supabase

## 快速开始

### 前置要求
- Python 3.10+
- Node.js 18+
- Supabase账号

### 安装

1. 克隆项目
```bash
git clone https://github.com/YOUR_USERNAME/ashare-sentinel-pro.git
cd ashare-sentinel-pro
```

2. 安装依赖
```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

3. 配置环境变量
```bash
# backend/.env
DATABASE_URL=your_supabase_database_url
DASHSCOPE_API_KEY=your_dashscope_api_key  # 可选

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8003
```

4. 启动服务
```bash
# 后端
cd backend
python -m uvicorn app.main:app --reload

# 前端
cd frontend
npm run dev
```

5. 访问应用
- 前端: http://localhost:3000
- 后端API: http://localhost:8003
- API文档: http://localhost:8003/docs

## 使用说明

### 1. 添加股票
- 输入6位A股代码（如：600519）
- 系统自动获取股票名称和行业信息
- 设置成本价和持股数量

### 2. 查看技术分析
- 展开股票行查看详细分析
- 包括均线状态、量能、Alpha、K线形态
- 查看健康评分和操作建议

### 3. 生成复盘报告
- 点击"导出报告"按钮
- 系统生成包含所有股票的详细报告
- 支持复制到剪贴板或下载为.txt文件

## 健康评分说明

### 评分维度（0-100分）
1. **基础分**：50分
2. **MA20状态**：站上+30分，跌破-30分
3. **量能状态**：放量+20分，缩量-20分
4. **Alpha**：相对沪深300的超额收益（±30分）
5. **K线形态**：金针探底+15分，冲高回落-15分等

### 操作建议
- **80-100分**：强烈买入 ⭐⭐⭐⭐⭐
- **60-79分**：买入 ⭐⭐⭐⭐
- **40-59分**：持有 ⭐⭐⭐
- **20-39分**：卖出 ⭐⭐
- **0-19分**：强烈卖出 ⭐

## API文档

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/portfolio` | POST/GET | 添加/获取持仓 |
| `/api/v1/portfolio/{id}` | DELETE | 删除持仓 |
| `/api/v1/market/technical/{symbol}` | GET | 技术分析 |
| `/api/v1/market/sentiment` | GET | 市场情绪 |
| `/api/v1/report/generate` | GET | 生成报告 |

完整API文档：http://localhost:8003/docs

## 数据来源

- **股票数据**: AkShare (akshare.xyz)
- **市场指数**: 沪深300
- **AI分析**: 通义千问（可选）

## 常见问题

### Q: AkShare连接失败怎么办？
A: 系统已配置容错机制，会返回默认数据。可以稍后重试刷新按钮。

### Q: 支持哪些股票？
A: 目前支持6位数字代码的A股。

### Q: 如何获取股票名称？
A: 系统会自动从AkShare获取股票名称和行业信息。

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### V1.0.0 (2025-01-23)
- ✅ 初始版本发布
- ✅ 持仓管理功能
- ✅ 技术分析系统
- ✅ 健康评分算法
- ✅ K线形态识别
- ✅ 复盘报告生成
- ✅ 实时数据刷新

---

**免责声明**：本系统提供的所有信息和数据仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。
