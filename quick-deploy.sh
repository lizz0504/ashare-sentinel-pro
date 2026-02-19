#!/bin/bash
# ============================================
# 一键部署脚本 - 直接复制粘贴到服务器执行
# ============================================

set -e

echo "🚀 AShare Sentinel Pro - 一键部署脚本"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================
# 步骤1：安装Docker
# ============================================
echo -e "${YELLOW}[1/7] 安装Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}✅ Docker安装完成${NC}"
else
    echo -e "${GREEN}✅ Docker已安装${NC}"
fi
docker --version
echo ""

# ============================================
# 步骤2：安装Docker Compose
# ============================================
echo -e "${YELLOW}[2/7] 安装Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✅ Docker Compose安装完成${NC}"
else
    echo -e "${GREEN}✅ Docker Compose已安装${NC}"
fi
docker-compose --version
echo ""

# ============================================
# 步骤3：克隆代码
# ============================================
echo -e "${YELLOW}[3/7] 克隆代码仓库...${NC}"
if [ -d "/root/ashare-sentinel-pro" ]; then
    cd /root/ashare-sentinel-pro
    git pull
    echo -e "${GREEN}✅ 代码已更新${NC}"
else
    cd /root
    git clone https://github.com/lizz0504/ashare-sentinel-pro.git
    cd ashare-sentinel-pro
    echo -e "${GREEN}✅ 代码已克隆${NC}"
fi
echo ""

# ============================================
# 步骤4：配置环境变量
# ============================================
echo -e "${YELLOW}[4/7] 配置环境变量...${NC}"
if [ ! -f .env ]; then
    cp .env.docker.example .env
    echo -e "${YELLOW}⚠️  请先编辑 .env 文件，填入你的API密钥${NC}"
    echo ""
    echo "nano .env"
    echo ""
    echo "必须配置的密钥："
    echo "  - SUPABASE_SERVICE_KEY"
    echo "  - SUPABASE_ANON_KEY"
    echo "  - SUPABASE_JWT_SECRET"
    echo "  - DEEPSEEK_API_KEY"
    echo "  - TUSHARE_TOKEN"
    echo "  - TAVILY_API_KEY"
    echo ""
    read -p "配置完成后按Enter继续..."
else
    echo -e "${GREEN}✅ 环境变量文件已存在${NC}"
fi
echo ""

# ============================================
# 步骤5：替换服务器IP
# ============================================
echo -e "${YELLOW}[5/7] 配置服务器IP...${NC}"
SERVER_IP=$(curl -s ifconfig.me)
echo "检测到服务器IP: $SERVER_IP"
echo ""

# 询问是否自动替换
read -p "是否自动替换docker-compose.yml中的IP? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sed -i "s/your-server-ip/$SERVER_IP/g" docker-compose.prod.yml
    echo -e "${GREEN}✅ 已替换为实际IP: $SERVER_IP${NC}"
else
    echo -e "${YELLOW}⚠️  请手动编辑 docker-compose.prod.yml 替换IP${NC}"
fi
echo ""

# ============================================
# 步骤6：构建并启动
# ============================================
echo -e "${YELLOW}[6/7] 构建Docker镜像（预计10-15分钟）...${NC}"
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
docker-compose -f docker-compose.prod.yml build
echo -e "${GREEN}✅ 镜像构建完成${NC}"
echo ""

echo -e "${YELLOW}[7/7] 启动服务...${NC}"
docker-compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✅ 服务已启动${NC}"
echo ""

# ============================================
# 验证部署
# ============================================
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 15

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
echo "📊 常用命令:"
echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
echo "  查看状态: docker-compose -f docker-compose.prod.yml ps"
echo ""
echo "========================================"
