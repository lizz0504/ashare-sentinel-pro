# AShare Sentinel Pro - 腾讯云部署指南

## 前端部署（腾讯云静态网站托管）

### 1. 构建Next.js静态导出

```bash
cd frontend

# 安装依赖
npm install

# 配置静态导出
cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true
  },
  basePath: '',
  assetPrefix: '',
}
module.exports = nextConfig
EOF

# 构建静态文件
npm run build

# 构建产物在 out/ 目录
```

### 2. 上传到腾讯云

#### 方法A：使用腾讯云控制台（推荐）

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入 **静态网站托管** 服务
3. 创建新的静态网站托管
4. 上传 `frontend/out/` 目录内容
5. 配置自定义域名（可选）

#### 方法B：使用COS+CDN

1. 创建 **对象存储COS** 存储桶
2. 开启 **静态网站** 托管
3. 上传 `frontend/out/` 内容
4. 配置CDN加速

### 3. 环境变量配置

在部署前修改 `frontend/.env.production`:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://your-backend-api.tencentcloudapi.com
```

---

## 后端部署（两种方案）

### 方案A：腾讯云云服务器CVM（推荐新手）

#### 1. 购买并配置CVM

```bash
# 系统选择: Ubuntu 20.04/22.04
# 配置: 2核4G起步
# 带宽: 按量计费

# SSH连接服务器
ssh root@your-server-ip

# 更新系统
apt update && apt upgrade -y

# 安装Python 3.10
apt install python3.10 python3-pip python3-venv -y

# 安装Supabase客户端
pip3 install supabase

# 安装uvicorn
pip3 install uvicorn[standard] fastapi python-multipart
```

#### 2. 部署后端代码

```bash
# 在服务器上
mkdir -p /var/www/ashare-sentinel-pro
cd /var/www/ashare-sentinel-pro

# 上传代码（使用git或scp）
git clone https://github.com/lizz0504/ashare-sentinel-pro.git
cd ashare-sentinel-pro/backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 填入API密钥

# 测试启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 3. 使用Systemd管理服务

```bash
# 创建服务文件
cat > /etc/systemd/system/ashare-backend.service << 'EOF'
[Unit]
Description=AShare Sentinel Pro Backend
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/ashare-sentinel-pro/backend
Environment="PATH=/var/www/ashare-sentinel-pro/backend/venv/bin"
ExecStart=/var/www/ashare-sentinel-pro/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl enable ashare-backend
systemctl start ashare-backend
systemctl status ashare-backend
```

#### 4. 配置Nginx反向代理

```bash
# 安装Nginx
apt install nginx -y

# 配置Nginx
cat > /etc/nginx/sites-available/ashare-sentinel << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 启用配置
ln -s /etc/nginx/sites-available/ashare-sentinel /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

#### 5. 配置HTTPS（Let's Encrypt）

```bash
# 安装Certbot
apt install certbot python3-certbot-nginx -y

# 获取SSL证书
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```

---

### 方案B：腾讯云函数SCF（无服务器）

#### 1. 安装Serverless Framework

```bash
npm install -g serverless
```

#### 2. 创建serverless配置

```yaml
# serverless.yml (在backend目录)
service: ashare-sentinel-backend

provider:
  name: tencent
  runtime: Python3.10
  region: ap-guangzhou
  credentials: ~/..tencentcloud/credentials

functions:
  ic-meeting:
    handler: handler.main
    events:
      - apigw:
          path: /api/v1/ic/meeting
          method: POST
          cors: true

plugins:
  - serverless-tencent-scf

custom:
  serverless-tencent-scf:
    functionName: ashare-ic-meeting
    codeUri: ./
    description: IC投委会分析API
    handler: handler.main
    memorySize: 512
    timeout: 120
    environment:
      variables:
        SUPABASE_URL: ${env:SUPABASE_URL}
        SUPABASE_KEY: ${env:SUPABASE_KEY}
```

#### 3. 创建云函数入口

```python
# backend/handler.py
from app.main import app
from mangum import Mangum

# ASGI适配器
asgi_handler = Mangum(app)

def main(event, context):
    """云函数入口"""
    return asgi_handler(event, context)
```

#### 4. 部署

```bash
# 安装依赖
pip install mangum

# 部署到腾讯云
serverless deploy --region ap-guangzhou
```

---

## 数据库配置

Supabase已经在云端，无需额外配置。只需确保后端环境变量正确：

```bash
# backend/.env
SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

---

## 域名配置

### 前端域名
- 类型: A记录
- 记录值: 腾讯云静态网站托管IP

### 后端域名
- 类型: A记录
- 记录值: CVM公网IP
- API路径: https://api.your-domain.com

---

## 监控和日志

### 前端
- 腾讯云控制台 → 静态网站托管 → 监控
- 查看访问量、流量、错误日志

### 后端
```bash
# CVM方式
journalctl -u ashare-backend -f  # 查看后端日志
systemctl status ashare-backend  # 查看服务状态

# SCF方式
# 腾讯云控制台 → 云函数 → 日志查询
```

---

## 成本估算

### 前端（静态网站托管）
- **免费额度**: 10GB存储/月
- **超出**: ¥0.004/GB/月
- **流量**: ¥0.21/GB（中国大陆）

### 后端（CVM 2核4G）
- **按量计费**: ~¥200-300/月
- **包年包月**: 更便宜

### 后端（云函数SCF）
- **免费额度**: 100万次调用/月
- **超出**: ¥0.0000167/次
- **预估**: 低流量下几乎免费

### Supabase
- **免费版**: 500MB数据库 + 1GB文件存储
- **Pro版**: $25/月

**总成本**: 低流量场景 ¥50-100/月，中等流量 ¥300-500/月

---

## 常见问题

### Q1: 前端部署后API连接失败
**A**: 检查 `NEXT_PUBLIC_API_URL` 是否配置为后端的公网域名

### Q2: 后端CORS错误
**A**: 在FastAPI中添加前端域名到CORS配置

### Q3: 云函数超时
**A**: 增加timeout配置（最大120秒）

### Q4: 数据库连接失败
**A**: 确认Supabase项目已暂停或网络问题

---

## 安全建议

1. **环境变量**: 不要在代码中硬编码API密钥
2. **HTTPS**: 强制使用HTTPS加密通信
3. **防火墙**: CVM只开放80、443、22端口
4. **备份**: 定期备份Supabase数据
5. **监控**: 配置告警通知

---

## 下一步

1. 选择部署方案（CVM 或 SCF）
2. 购买腾讯云资源
3. 按照上述步骤部署
4. 配置域名和SSL证书
5. 测试完整流程

需要我协助具体哪个步骤？
