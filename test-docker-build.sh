#!/bin/bash
# Docker构建测试脚本

set -e

echo "🐳 开始测试Docker构建..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================
# 1. 检查Docker环境
# ============================================
echo -e "${YELLOW}[1/4] 检查Docker环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装${NC}"
    echo "请先安装Docker Desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  docker-compose未安装${NC}"
    echo "将使用docker compose插件"
fi

echo -e "${GREEN}✅ Docker环境正常${NC}"
docker --version
echo ""

# ============================================
# 2. 创建测试环境变量
# ============================================
echo -e "${YELLOW}[2/4] 创建测试环境变量...${NC}"
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# 测试环境变量
SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
SUPABASE_SERVICE_KEY=test-key
SUPABASE_JWT_SECRET=test-secret
SUPABASE_ANON_KEY=test-anon-key
DEEPSEEK_API_KEY=test-key
TUSHARE_TOKEN=test-token
TAVILY_API_KEY=test-key
SERVER_IP=localhost
EOF
    echo -e "${GREEN}✅ 测试环境变量已创建${NC}"
else
    echo -e "${GREEN}✅ 环境变量文件已存在${NC}"
fi
echo ""

# ============================================
# 3. 测试后端构建
# ============================================
echo -e "${YELLOW}[3/4] 测试后端Docker构建...${NC}"
echo "这可能需要5-10分钟，请耐心等待..."
echo ""

cd backend
if docker build -t ashare-backend:test . ; then
    echo -e "${GREEN}✅ 后端镜像构建成功${NC}"

    # 显示镜像大小
    IMAGE_SIZE=$(docker images ashare-backend:test --format "{{.Size}}")
    echo "镜像大小: $IMAGE_SIZE"
else
    echo -e "${RED}❌ 后端镜像构建失败${NC}"
    exit 1
fi

cd ..
echo ""

# ============================================
# 4. 测试前端构建
# ============================================
echo -e "${YELLOW}[4/4] 测试前端Docker构建...${NC}"
echo "这可能需要5-10分钟，请耐心等待..."
echo ""

cd frontend
if docker build \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=test-anon-key \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  -t ashare-frontend:test . ; then
    echo -e "${GREEN}✅ 前端镜像构建成功${NC}"

    # 显示镜像大小
    IMAGE_SIZE=$(docker images ashare-frontend:test --format "{{.Size}}")
    echo "镜像大小: $IMAGE_SIZE"
else
    echo -e "${RED}❌ 前端镜像构建失败${NC}"
    exit 1
fi

cd ..
echo ""

# ============================================
# 5. 构建总结
# ============================================
echo "========================================"
echo -e "${GREEN}🎉 所有构建测试通过！${NC}"
echo "========================================"
echo ""
echo "📊 镜像信息:"
docker images | grep ashare
echo ""
echo "💾 清理测试镜像:"
echo "  docker rmi ashare-backend:test ashare-frontend:test"
echo ""
echo "🚀 准备部署到腾讯云:"
echo "  1. SSH连接服务器"
echo "  2. 运行 ./deploy-tencent.sh"
echo ""
echo "========================================"
