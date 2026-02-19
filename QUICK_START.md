# ============================================
# 腾讯云轻量服务器自动部署指南
# ============================================

## 前提条件

- ✅ 已购买腾讯云轻量服务器（2核4G）
- ✅ 已安装 Docker CE
- ✅ 已有 GitHub 仓库访问权限
- ✅ 已准备好 Supabase 和 API 密钥

---

## 🚀 自动部署步骤（复制粘贴即可）

### 第1步：连接到服务器

```bash
# 替换为你的服务器公网IP
ssh root@your-server-ip
```

### 第2步：安装 Docker 和 Docker Compose（如果未安装）

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动 Docker
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 第3步：克隆代码仓库

```bash
# 克隆代码（替换为你的仓库地址）
cd /root
git clone https://github.com/lizz0504/ashare-sentinel-pro.git
cd ashare-sentinel-pro
```

### 第4步：配置环境变量

```bash
# 复制环境变量模板
cp .env.docker.example .env

# 编辑环境变量
nano .env
```

**需要填写的密钥**：

```bash
# 从 Supabase Dashboard → Settings → API 获取
SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
SUPABASE_SERVICE_KEY=eyJhb...（你的service_role密钥）
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_ANON_KEY=eyJhb...（你的anon密钥）

# AI API密钥
DEEPSEEK_API_KEY=sk-xxx
TAVILY_API_KEY=tvly-xxx

# 数据源
TUSHARE_TOKEN=xxx

# 服务器IP（重要！替换为实际IP）
SERVER_IP=你的服务器公网IP
```

保存：`Ctrl + O` → `Enter` → `Ctrl + X`

### 第5步：修改 docker-compose.yml 中的服务器IP

```bash
nano docker-compose.prod.yml
```

**替换所有** `your-server-ip` **为实际IP**（如 `123.45.67.89`）：

```yaml
frontend:
  environment:
    - NEXT_PUBLIC_API_URL=http://123.45.67.89:8000  # 修改这里
```

### 第6步：一键启动服务

```bash
# 赋予执行权限
chmod +x deploy-tencent.sh

# 执行部署脚本
./deploy-tencent.sh
```

**部署脚本会自动**：
1. 停止旧容器
2. 拉取最新代码
3. 构建新镜像
4. 启动所有服务
5. 显示容器状态

---

## ✅ 验证部署

### 1. 检查容器状态

```bash
docker-compose -f docker-compose.prod.yml ps
```

应该看到：
```
NAME                STATUS              PORTS
ashare-backend      Up (healthy)        0.0.0.0:8000->8000/tcp
ashare-frontend     Up (healthy)        0.0.0.0:3000->3000/tcp
```

### 2. 测试后端API

```bash
curl http://localhost:8000/health
```

应该返回：
```json
{"status":"healthy","service":"AShare Sentinel Pro Backend"}
```

### 3. 测试前端（浏览器访问）

```
http://your-server-ip:3000
```

### 4. 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 只看后端日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 只看前端日志
docker-compose -f docker-compose.prod.yml logs -f frontend
```

---

## 🔧 常用维护命令

### 停止服务

```bash
docker-compose -f docker-compose.prod.yml down
```

### 重启服务

```bash
docker-compose -f docker-compose.prod.yml restart
```

### 更新代码并重新部署

```bash
git pull
./deploy-tencent.sh
```

### 清理旧镜像释放空间

```bash
docker image prune -a
```

---

## 🔒 安全配置（可选但推荐）

### 配置防火墙

```bash
# 只开放必要端口
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw allow 3000  # 前端（可选，建议用nginx反向代理）
ufw allow 8000  # 后端API（可选，建议用nginx反向代理）
ufw enable
```

### 配置 Nginx 反向代理（生产环境推荐）

```bash
# 安装 Nginx
apt install nginx -y

# 创建前端配置
nano /etc/nginx/sites-available/ashare-frontend
```

Nginx配置内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # 后端API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用配置：
```bash
ln -s /etc/nginx/sites-available/ashare-frontend /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

## 📊 监控服务器资源

```bash
# 实时监控
htop

# Docker资源使用
docker stats

# 磁盘使用
df -h

# 内存使用
free -h
```

---

## ❗ 故障排查

### 问题1：容器无法启动

```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend
```

### 问题2：端口被占用

```bash
# 查看端口占用
netstat -tunlp | grep 3000
netstat -tunlp | grep 8000

# 杀死占用进程
kill -9 <PID>
```

### 问题3：构建失败

```bash
# 清理缓存重新构建
docker-compose -f docker-compose.prod.yml build --no-cache
```

### 问题4：内存不足

2核4G服务器足够运行此应用，如果遇到OOM（内存溢出）：
1. 减少docker-compose中的资源限制
2. 增加swap空间：
```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 📞 需要帮助？

查看完整文档：
- [DOCKER_GUIDE.md](DOCKER_GUIDE.md) - Docker详细说明
- [DEPLOY_LIGHTHOUSE.md](DEPLOY_LIGHTHOUSE.md) - 腾讯云部署说明

---

## ✨ 部署检查清单

- [ ] Docker 已安装
- [ ] Docker Compose 已安装
- [ ] 代码已克隆
- [ ] .env 文件已配置
- [ ] docker-compose.yml IP已替换
- [ ] 容器已启动
- [ ] 后端健康检查通过
- [ ] 前端可以访问
- [ ] 防火墙已配置（可选）

**部署成功后访问**：`http://your-server-ip:3000`
