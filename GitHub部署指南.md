# GitHub 部署指南 - AShare Sentinel Pro V1

## 准备工作

### 1. 确认Git已初始化

```bash
cd "d:\CC CODE\AShare-Sentinel-Pro"
git log --oneline
```

应该显示：
```
c24c890 Initial commit - AShare Sentinel Pro V1
```

---

## 方法1：通过GitHub网页创建（推荐）

### 步骤1：登录GitHub
访问：https://github.com

### 步骤2：创建新仓库
1. 点击右上角 **+** → **New repository**
2. 填写仓库信息：
   - **Repository name**: `ashare-sentinel-pro`
   - **Description**: `AShare Sentinel Pro - 智能投资复盘系统 V1`
   - 选择 **Public** 或 **Private**
   - **不要**勾选 "Add a README file"
   - **不要**勾选 "Add .gitignore"

### 步骤3：推送代码
创建仓库后，GitHub会显示推送命令。在项目目录执行：

```bash
cd "d:\CC CODE\AShare-Sentinel-Pro"

# 添加远程仓库（替换 YOUR_USERNAME 为你的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/ashare-sentinel-pro.git

# 推送代码
git branch -M main
git push -u origin main
```

---

## 方法2：使用GitHub CLI（如果已安装）

```bash
cd "d:\CC CODE\AShare-Sentinel-Pro"

# 登录GitHub
gh auth login

# 创建仓库
gh repo create ashare-sentinel-pro --public --source=. --description "AShare Sentinel Pro - 智能投资复盘系统 V1"
```

---

## 验证部署

部署成功后，检查：

```bash
# 查看远程仓库
git remote -v

# 查看提交历史
git log --oneline --all
```

---

## V1 版本包含的功能

### 核心功能
- ✅ 持仓管理（添加、删除股票）
- ✅ 实时股价获取（AkShare集成）
- ✅ 技术分析（MA5/MA20/Alpha/K线形态）
- ✅ 健康评分系统（0-100分）
- ✅ 市场情绪分析
- ✅ K线形态识别
- ✅ 自动生成复盘报告
- ✅ 报告导出（复制/下载）

### 技术栈
- **前端**：Next.js 15 + React + TypeScript + TailwindCSS
- **后端**：FastAPI + Python + AkShare
- **数据库**：Supabase PostgreSQL

### 文件结构
```
AShare-Sentinel-Pro/
├── backend/              # 后端服务
│   ├── app/
│   │   ├── core/        # 核心配置
│   │   ├── data/        # 数据文件
│   │   ├── services/    # 业务逻辑
│   │   └── main.py      # API入口
│   ├── scripts/         # 工具脚本
│   └── pyproject.toml
├── frontend/            # 前端服务
│   ├── src/
│   │   ├── app/        # 页面
│   │   ├── components/ # 组件
│   │   └── types/      # 类型定义
│   ├── package.json
│   └── tailwind.config.ts
├── supabase/           # 数据库配置
├── docker-compose.yml  # Docker配置
└── README.md           # 项目说明
```

---

## 后续开发建议

### V2 功能规划
- [ ] 用户认证系统
- [ ] 多账户支持
- [ ] 策略回测功能
- [ ] 模拟交易
- [ ] 移动端适配

### 部署建议
- [ ] 配置生产环境变量
- [ ] 使用Docker部署
- [ ] 配置HTTPS
- [ ] 设置CI/CD
