# Frontend - AShare Sentinel Pro Web界面

## 🚀 快速启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install
# 或
yarn install

# 3. 配置环境变量
cp .env.example .env.local
# 编辑 .env.local，填入Supabase和后端配置

# 4. 启动开发服务器
npm run dev
# 或
yarn dev

# 5. 访问浏览器
open http://localhost:3000
```

## 📦 关键依赖

- **Next.js 14** - React框架（App Router）
- **Supabase SSR** - 客户端Supabase
- **Recharts** - 图表库（雷达图）
- **TailwindCSS** - 样式框架
- **shadcn/ui** - UI组件库

## 🔧 配置文件

### `.env.local` 必需配置
```bash
# Supabase配置
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# 后端API配置
NEXT_PUBLIC_API_URL=http://localhost:8000
```

⚠️ **注意**: `NEXT_PUBLIC_API_URL` 必须是 `http://localhost:8000`，不能是 `8001`！

## 🎨 页面结构

```
frontend/
├── app/
│   ├── page.tsx                # 首页（重定向到登录）
│   ├── login/
│   │   └── page.tsx            # 登录页
│   └── dashboard/
│       ├── page.tsx            # Dashboard主页
│       └── portfolio/
│           └── page.tsx        # Portfolio页面（含雷达图）
├── src/
│   └── components/
│       ├── dashboard/          # Dashboard组件
│       │   └── DecisionMatrix.tsx
│       └── portfolio/          # Portfolio组件
│           └── ProfessionalPanel.tsx  # 雷达图组件
├── lib/
│   └── utils/
│       └── analysisHistory.ts  # 本地存储管理
└── .env.local                  # 环境变量（不提交）
```

## 🧪 测试

```bash
# 开发模式（带热重载）
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run start

# 类型检查
npx tsc --noEmit

# 代码格式化
npm run lint
```

## 🐛 常见问题

### 1. API连接失败 (Failed to fetch)
**原因**: 前端配置的端口与后端不一致

**解决**:
```bash
# 检查 .env.local
cat .env.local | grep API_URL
# 应该输出: NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. 雷达图显示都一样
**原因**: 后端没有返回 `advanced_metrics`

**解决**:
1. 硬刷新浏览器: `Ctrl + Shift + R` (Windows) 或 `Cmd + Shift + R` (Mac)
2. 清除浏览器缓存
3. 检查后端日志确认返回了 `advanced_metrics`

### 3. 环境变量不生效
**原因**: Next.js需要重启才能读取新的环境变量

**解决**:
```bash
# 停止开发服务器 (Ctrl+C)
# 重新启动
npm run dev
```

### 4. TypeScript类型错误
```bash
# 删除TypeScript缓存
rm -rf node_modules/.cache
rm tsconfig.tsbuildinfo
npm run dev
```

## 📊 数据流

```
用户输入股票代码
    ↓
前端调用 /api/v1/ic/meeting
    ↓
后端IC投委会分析
    ↓
返回结果 (含 advanced_metrics)
    ↓
前端ProfessionalPanel渲染雷达图
    ↓
保存到本地 localStorage
```

## 🎨 雷达图数据结构

```typescript
interface AdvancedMetrics {
  radar: {
    value_score: number;      // 价值评分 (Warren Buffett)
    growth_score: number;     // 成长评分 (Cathie Wood)
    safety_score: number;     // 安全评分 (ROE+负债率)
    dividend_score: number;   // 股息评分 (PB)
    trend_score: number;      // 趋势评分 (Nancy Pelosi)
  }
  technical: {...}
  capital: {...}
  fundamental: {...}
}
```

## 🔍 浏览器DevTools调试

### 查看API请求
1. 打开DevTools (F12)
2. 切换到 Network 标签
3. 输入股票代码并分析
4. 查找 `ic/meeting` 请求
5. 检查Response中是否有 `advanced_metrics`

### 查看Console日志
```javascript
// ProfessionalPanel会输出调试信息
console.log('[ProfessionalPanel] Rendering with stock:', stock.symbol)
console.log('[ProfessionalPanel] Has advanced_metrics:', !!stock.advanced_metrics)
```

### 查看本地存储
```javascript
// Console中执行
localStorage.getItem('dashboard_analysis_cache')
```

## ⚠️ 重要规则

1. **修改 `.env.local` 后必须重启开发服务器**
2. **API端口必须是 8000，不能是 8001**
3. **修改代码后硬刷新浏览器** (`Ctrl + Shift + R`)
4. **永远不要提交 `.env.local` 到Git**
5. **雷达图必须显示不同的形状，如果都一样说明数据有问题**

## 🚀 部署

```bash
# 1. 构建生产版本
npm run build

# 2. 部署到Vercel
vercel --prod

# 或部署到其他平台
# 将 .next/ 和 public/ 目录上传到服务器
```
