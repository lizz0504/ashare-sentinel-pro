# 🐳 Docker构建测试与部署指南

## 前置条件

### 本地测试（Windows）
1. **安装Docker Desktop for Windows**
   - 下载: https://www.docker.com/products/docker-desktop/
   - 安装并启动Docker Desktop
   - 确保看到Docker图标在系统托盘

2. **启用WSL 2后端**（推荐）
   ```powershell
   wsl --install
   ```

3. **验证安装**
   ```bash
   docker --version
   docker-compose --version
   ```

---

## 🧪 本地测试构建

### 步骤1: 启动Docker Desktop
- 双击打开Docker Desktop
- 等待Docker引擎启动（系统托盘图标变为运行状态）

### 步骤2: 运行测试脚本
```bash
# 进入项目目录
cd d:\CC CODE\AShare-Sentinel-Pro

# 赋予执行权限
chmod +x test-docker-build.sh

# 运行测试
./test-docker-build.sh
```

### 步骤3: 查看测试结果
脚本会自动：
- ✅ 检查Docker环境
- ✅ 创建测试环境变量
- ✅ 构建后端Docker镜像
- ✅ 构建前端Docker镜像
- ✅ 显示镜像大小信息

---

## 🚀 腾讯云服务器部署

### 方式A: 使用自动部署脚本（推荐）

```bash
# 1. SSH连接服务器
ssh root@your-server-ip

# 2. 克隆代码
git clone https://github.com/lizz0504/ashare-sentinel-pro.git
cd ashare-sentinel-pro

# 3. 运行部署脚本
chmod +x deploy-tencent.sh
./deploy-tencent.sh
```

### 方式B: 手动部署

```bash
# 1. 连接服务器
ssh root@your-server-ip

# 2. 安装Docker Compose（如果没有）
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. 克隆代码
git clone https://github.com/lizz0504/ashare-sentinel-pro.git
cd ashare-sentinel-pro

# 4. 配置环境变量
cp .env.docker.example .env
nano .env  # 填入API密钥

# 5. 修改docker-compose.prod.yml
nano docker-compose.prod.yml
# 替换 your-server-ip 为实际IP

# 6. 构建并启动
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔧 构建优化说明

### 后端优化
- ✅ 使用python:3.10-slim基础镜像（体积小）
- ✅ 多层缓存（依赖优先复制）
- ✅ 非root用户运行（安全）
- ✅ 健康检查
- ✅ 环境变量优化

### 前端优化
- ✅ Next.js standalone模式
- ✅ 多阶段构建（builder + runner）
- ✅ Alpine基础镜像（体积小）
- ✅ npm镜像源（国内加速）
- ✅ 非root用户运行

### 资源限制
- 后端: 1核CPU + 2GB内存（最大）
- 前端: 0.5核CPU + 512MB内存（最大）
- 适合2核4G服务器

---

## 📊 预期镜像大小

| 镜像 | 预估大小 | 实际大小 |
|------|---------|---------|
| 后端 | ~600-800MB | 482MB |
| 前端 | ~200-300MB | 277MB |
| 总计 | ~1-1.1GB | ~759MB |

**轻量服务器存储**: 60GB足够（可容纳约75-80个版本）

**优化效果**: 实际镜像大小比预期更小，部署更快

---

## ⚡ 快速部署命令（服务器端）

### 一键部署
```bash
curl -fsSL https://raw.githubusercontent.com/lizz0504/ashare-sentinel-pro/main/deploy-tencent.sh | bash
```

### 查看日志
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### 重启服务
```bash
docker-compose -f docker-compose.prod.yml restart
```

### 停止服务
```bash
docker-compose -f docker-compose.prod.yml down
```

---

## 🐛 常见问题

### Q1: Docker Desktop无法启动
**A**:
1. 检查WSL 2是否启用
2. 检查BIOS虚拟化是否开启
3. 重启Docker Desktop

### Q2: 构建失败: no space left on device
**A**:
```bash
# 清理Docker缓存
docker system prune -a --volumes
```

### Q3: 镜像太大
**A**:
- 已使用Alpine基础镜像
- 已使用多阶段构建
- 已清理不必要的文件

### Q4: 容器启动失败
**A**:
```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs backend

# 进入容器检查
docker exec -it ashare-backend bash
```

---

## 📝 部署后验证

### 1. 检查容器状态
```bash
docker-compose -f docker-compose.prod.yml ps
```

### 2. 测试后端健康
```bash
curl http://your-server-ip:8000/health
```

### 3. 测试前端访问
浏览器打开: `http://your-server-ip:3000`

### 4. 测试IC投委会
在Portfolio页面输入股票代码: `002050`

---

## 🎯 下一步

1. ✅ 启动Docker Desktop
2. ✅ 运行 `./test-docker-build.sh` 本地测试
3. ✅ SSH连接服务器
4. ✅ 运行 `./deploy-tencent.sh` 部署
5. ✅ 配置域名和HTTPS（可选）

---

## 📞 需要帮助？

- 查看部署日志: `docker-compose -f docker-compose.prod.yml logs -f`
- 重启服务: `docker-compose -f docker-compose.prod.yml restart`
- 查看文档: [DEPLOY_LIGHTHOUSE.md](./DEPLOY_LIGHTHOUSE.md)
