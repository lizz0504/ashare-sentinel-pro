#!/bin/bash
# ============================================
# 腾讯云一键部署脚本（代码清理后版本）
# ============================================

set -e

echo "========================================"
echo "  AShare Sentinel Pro - 代码清理后部署"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================
# 1. 设置2G虚拟内存
# ============================================
echo -e "${YELLOW}[1/7] 设置2G虚拟内存...${NC}"
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo -e "${GREEN}✅ Swap已创建${NC}"
else
  echo -e "${GREEN}✅ Swap已存在${NC}"
fi
echo ""

# ============================================
# 2. 拉取最新代码
# ============================================
echo -e "${YELLOW}[2/7] 拉取最新代码...${NC}"
if [ -d "/root/ashare-sentinel-pro" ]; then
  cd /root/ashare-sentinel-pro
  echo "拉取最新更新..."
  git fetch origin
  git reset --hard origin/main
  git clean -fd
else
  cd /root
  git clone https://github.com/lizz0504/ashare-sentinel-pro.git
  cd ashare-sentinel-pro
fi
echo -e "${GREEN}✅ 代码已更新（MySQL已清理）${NC}"
echo ""

# ============================================
# 3. 配置环境变量
# ============================================
echo -e "${YELLOW}[3/7] 配置环境变量...${NC}"
if [ ! -f .env ]; then
  echo "⚠️  未找到.env文件，运行配置向导..."
  bash setup-env.sh
else
  echo -e "${GREEN}✅ .env已存在${NC}"
fi
echo ""

# ============================================
# 4. 检查Docker
# ============================================
echo -e "${YELLOW}[4/7] 检查Docker环境...${NC}"
if ! command -v docker &> /dev/null; then
  echo "安装Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl start docker
  systemctl enable docker
fi
echo -e "${GREEN}✅ Docker环境正常${NC}"
docker --version
echo ""

# ============================================
# 5. 停止旧容器
# ============================================
echo -e "${YELLOW}[5/7] 停止旧容器...${NC}"
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
echo -e "${GREEN}✅ 旧容器已停止${NC}"
echo ""

# ============================================
# 6. 设置Node内存限制并构建
# ============================================
echo -e "${YELLOW}[6/7] 构建Docker镜像（预计10-15分钟）...${NC}"

# 从.env读取环境变量
export SUPABASE_URL=$(grep SUPABASE_URL .env | cut -d '=' -f2)
export SUPABASE_ANON_KEY=$(grep SUPABASE_ANON_KEY .env | cut -d '=' -f2)
export SUPABASE_SERVICE_KEY=$(grep SUPABASE_SERVICE_KEY .env | cut -d '=' -f2)
export DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY .env | cut -d '=' -f2)
export TAVILY_API_KEY=$(grep TAVILY_API_KEY .env | cut -d '=' -f2)
export TUSHARE_TOKEN=$(grep TUSHARE_TOKEN .env | cut -d '=' -f2)
export SUPABASE_JWT_SECRET=$(grep SUPABASE_JWT_SECRET .env | cut -d '=' -f2)

# 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me)

# 设置Node内存限制
export NODE_OPTIONS="--max-old-space-size=3072"

echo "构建参数："
echo "  SUPABASE_URL: $SUPABASE_URL"
echo "  服务器IP: $SERVER_IP"
echo "  NODE_OPTIONS: $NODE_OPTIONS"
echo ""

# 构建并传递环境变量
docker-compose -f docker-compose.prod.yml build \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY \
  --build-arg NEXT_PUBLIC_API_URL=http://$SERVER_IP:8000

echo -e "${GREEN}✅ 镜像构建完成${NC}"
echo ""

# ============================================
# 7. 启动服务
# ============================================
echo -e "${YELLOW}[7/7] 启动服务...${NC}"
docker-compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✅ 服务已启动${NC}"
echo ""

# ============================================
# 等待服务启动
# ============================================
echo "等待服务启动..."
sleep 15

# ============================================
# 验证部署
# ============================================
echo ""
echo "========================================"
echo "容器状态:"
docker-compose -f docker-compose.prod.yml ps
echo ""

echo "后端健康检查:"
if curl -f http://localhost:8000/health &> /dev/null; then
  echo -e "${GREEN}✅ 后端服务正常${NC}"
else
  echo -e "${YELLOW}⚠️  后端可能还在启动中...${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "========================================"
echo ""
echo "📍 访问地址:"
echo "  前端:  http://$SERVER_IP:3000"
echo "  后端:  http://$SERVER_IP:8000"
echo "  API文档: http://$SERVER_IP:8000/docs"
echo ""
echo "📊 本次更新内容:"
echo "  ✅ 完全移除MySQL遗留代码"
echo "  ✅ 统一使用Supabase数据库"
echo "  ✅ 清理重复导入（-859行代码）"
echo "  ✅ 修复前端构建缺失文件"
echo ""
echo "📊 常用命令:"
echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
echo ""
echo "========================================"
