# 腾讯云轻量服务器 - 快速部署指南

## 📋 服务器配置
- **CPU**: 2核
- **内存**: 4GB
- **系统**: Docker CE
- **存储**: 60GB SSD
- **流量**: 1536GB/月

**✅ 这个配置完全够用！**

---

## 🚀 一键部署（推荐）

### 步骤1: SSH连接服务器

```bash
# Windows用户使用PowerShell或Git Bash
ssh root@your-server-ip

# 输入密码或密钥
```

### 步骤2: 下载并运行部署脚本

```bash
# 克隆代码
git clone https://github.com/lizz0504/ashare-sentinel-pro.git
cd ashare-sentinel-pro

# 赋予执行权限
chmod +x deploy-tencent.sh

# 运行部署脚本
./deploy-tencent.sh
```

### 步骤3: 配置环境变量

脚本会自动创建 `.env` 文件，编辑它：

```bash
nano .env
```

填入你的API密钥：
```env
SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
SUPABASE_SERVICE_KEY=your-key-here
DEEPSEEK_API_KEY=sk-your-key
TUSHARE_TOKEN=your-token
TAVILY_API_KEY=tvly-your-key
```

### 步骤4: 访问应用

部署完成后，访问：
- **前端**: `http://your-server-ip:3000`
- **后端API**: `http://your-server-ip:8000`
- **API文档**: `http://your-server-ip:8000/docs`

---

## 🛠️ 手动部署（可选）

如果自动脚本失败，可以手动执行：

### 1. 安装依赖

```bash
# 更新系统
apt update && apt upgrade -y

# 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

### 3. 修改docker-compose.yml

编辑 `docker-compose.prod.yml`，替换以下内容：
- `your-server-ip` → 你的服务器公网IP
- `your-domain.com` → 你的域名（如果有的话）

```bash
nano docker-compose.prod.yml
```

### 4. 构建并启动

```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d
```

### 5. 查看状态

```bash
# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
```

---

## 🔧 常用管理命令

### 查看日志
```bash
# 所有日志
docker-compose -f docker-compose.prod.yml logs -f

# 后端日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 前端日志
docker-compose -f docker-compose.prod.yml logs -f frontend
```

### 重启服务
```bash
# 重启所有
docker-compose -f docker-compose.prod.yml restart

# 重启单个服务
docker-compose -f docker-compose.prod.yml restart backend
docker-compose -f docker-compose.prod.yml restart frontend
```

### 停止服务
```bash
docker-compose -f docker-compose.prod.yml down
```

### 更新代码
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建并启动
docker-compose -f docker-compose.prod.yml up -d --build

# 3. 清理旧镜像
docker image prune -a
```

### 查看资源占用
```bash
# 容器资源占用
docker stats

# 磁盘占用
df -h

# 内存占用
free -h
```

---

## 🌐 配置域名（可选）

### 1. 配置DNS解析

在腾讯云控制台：
- 进入 **域名解析** → 添加记录
- 添加A记录指向服务器IP

```
类型: A
主机记录: @
记录值: your-server-ip
```

### 2. 配置Nginx反向代理（可选）

如果需要域名访问：

```bash
# 安装Nginx
apt install nginx -y

# 创建配置文件
cat > /etc/nginx/sites-available/ashare-sentinel << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 后端API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# 启用配置
ln -s /etc/nginx/sites-available/ashare-sentinel /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 3. 配置HTTPS（免费SSL证书）

```bash
# 安装Certbot
apt install certbot python3-certbot-nginx -y

# 获取证书
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```

---

## 🔍 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs backend

# 进入容器检查
docker exec -it ashare-backend bash
```

### 端口被占用

```bash
# 查看端口占用
netstat -tlnp | grep :3000
netstat -tlnp | grep :8000

# 停止占用端口的进程
kill -9 <PID>
```

### 内存不足

```bash
# 查看内存使用
free -h

# 清理Docker缓存
docker system prune -a

# 重启Docker
systemctl restart docker
```

### 更换API密钥

```bash
# 1. 编辑.env文件
nano .env

# 2. 重启后端服务
docker-compose -f docker-compose.prod.yml restart backend
```

---

## 📊 性能优化

### 1. 限制容器资源（可选）

编辑 `docker-compose.prod.yml`：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
  frontend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### 2. 开启日志轮转

```bash
# 配置日志轮转防止磁盘占满
cat > /etc/logrotate.d/docker << 'EOF'
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    missingok
    delaycompress
    copytruncate
}
EOF
```

### 3. 设置自动重启

Docker Compose已配置 `restart: unless-stopped`，服务器重启后会自动启动服务。

---

## 💰 成本估算

**轻量服务器**（已购买）：
- 月费: ~¥50-100（2核4G配置）

**Supabase**：
- 免费版: 500MB数据库（已够用）
- Pro版: $25/月（可选）

**总成本**: **¥50-100/月**

---

## 🎯 部署检查清单

部署前：
- [ ] 已购买腾讯云轻量服务器
- [ ] 已获取服务器公网IP
- [ ] 准备好所有API密钥
- [ ] 已安装SSH客户端

部署后：
- [ ] 后端健康检查通过 (curl http://ip:8000/health)
- [ ] 前端可正常访问 (http://ip:3000)
- [ ] IC投委会分析功能正常
- [ ] 数据保存到Supabase
- [ ] 雷达图正常显示

---

## 📞 技术支持

遇到问题？
1. 查看日志: `docker-compose -f docker-compose.prod.yml logs -f`
2. 检查配置: `cat .env`
3. 重启服务: `docker-compose -f docker-compose.prod.yml restart`

需要帮助？
- GitHub Issues: https://github.com/lizz0504/ashare-sentinel-pro/issues
- 查看文档: [DEPLOY_TENCENT.md](./DEPLOY_TENCENT.md)
