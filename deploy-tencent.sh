# 腾讯云轻量服务器部署脚本
# 使用方法: bash deploy-tencent.sh

set -e

echo "🚀 开始部署 AShare Sentinel Pro 到腾讯云轻量服务器..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================
# 1. 检查Docker环境
# ============================================
echo -e "${YELLOW}[1/6] 检查Docker环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  docker-compose未安装，正在安装...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo -e "${GREEN}✅ Docker环境正常${NC}"
docker --version
docker-compose --version
echo ""

# ============================================
# 2. 创建环境变量文件
# ============================================
echo -e "${YELLOW}[2/6] 配置环境变量...${NC}"
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# Supabase配置
SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here
SUPABASE_ANON_KEY=your-anon-key-here

# AI API配置
DEEPSEEK_API_KEY=sk-your-deepseek-key
OPENAI_API_KEY=sk-your-openai-key

# 数据源配置
TUSHARE_TOKEN=your-tushare-token
TAVILY_API_KEY=tvly-your-tavily-key

# 服务器IP（替换为你的实际IP）
EOF
    echo -e "${YELLOW}⚠️  请编辑 .env 文件，填入正确的API密钥${NC}"
    echo "nano .env"
    echo ""
    read -p "按Enter继续..."
fi

echo -e "${GREEN}✅ 环境变量文件已创建${NC}"
echo ""

# ============================================
# 3. 拉取代码
# ============================================
echo -e "${YELLOW}[3/6] 拉取最新代码...${NC}"
if [ -d "ashare-sentinel-pro" ]; then
    cd ashare-sentinel-pro
    git pull origin main
else
    git clone https://github.com/lizz0504/ashare-sentinel-pro.git
    cd ashare-sentinel-pro
fi

echo -e "${GREEN}✅ 代码已更新${NC}"
echo ""

# ============================================
# 4. 构建Docker镜像
# ============================================
echo -e "${YELLOW}[4/6] 构建Docker镜像（这可能需要10-15分钟）...${NC}"

# 停止旧容器
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# 构建新镜像
docker-compose -f docker-compose.prod.yml build --no-cache

echo -e "${GREEN}✅ 镜像构建完成${NC}"
echo ""

# ============================================
# 5. 启动服务
# ============================================
echo -e "${YELLOW}[5/6] 启动服务...${NC}"
docker-compose -f docker-compose.prod.yml up -d

echo -e "${GREEN}✅ 服务已启动${NC}"
echo ""

# ============================================
# 6. 验证部署
# ============================================
echo -e "${YELLOW}[6/6] 验证部署...${NC}"
sleep 10

# 检查容器状态
echo "容器状态:"
docker-compose -f docker-compose.prod.yml ps

# 测试后端健康检查
echo ""
echo "后端健康检查:"
if curl -f http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✅ 后端服务正常${NC}"
else
    echo -e "${RED}❌ 后端服务异常${NC}"
fi

# 测试前端
echo ""
echo "前端访问测试:"
if curl -f http://localhost:3000 &> /dev/null; then
    echo -e "${GREEN}✅ 前端服务正常${NC}"
else
    echo -e "${YELLOW}⚠️  前端可能还在启动中...${NC}"
fi

# ============================================
# 7. 访问信息
# ============================================
echo ""
echo "========================================"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "========================================"
echo ""
echo "📍 访问地址:"
echo "  - 前端: http://$(curl -s ifconfig.me):3000"
echo "  - 后端: http://$(curl -s ifconfig.me):8000"
echo "  - API文档: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "📊 查看日志:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🔄 重启服务:"
echo "  docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "⏹️  停止服务:"
echo "  docker-compose -f docker-compose.prod.yml down"
echo ""
echo "========================================"

# 显示实时日志
echo ""
read -p "是否查看实时日志? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose -f docker-compose.prod.yml logs -f
fi
