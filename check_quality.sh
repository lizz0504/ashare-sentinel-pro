#!/bin/bash
# AShare Sentinel Pro - 项目质量检查脚本
# 用法：每次修改代码后运行 ./check_quality.sh

echo "🔍 开始项目质量检查..."
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# ============================================
# 1. 后端 Python 代码检查
# ============================================
echo "📦 检查后端代码..."

cd backend

# 检查语法错误
echo "  - Python语法检查..."
python -m py_compile app/main.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Python语法错误${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "${GREEN}✅ Python语法正确${NC}"
fi

# 检查关键配置是否存在
echo "  - 检查后端配置..."
if [ -f ".env" ]; then
    if grep -q "SUPABASE_URL" .env && grep -q "SUPABASE_SERVICE_KEY" .env; then
        echo -e "${GREEN}✅ 后端配置完整${NC}"
    else
        echo -e "${RED}❌ 后端缺少Supabase配置${NC}"
        ERRORS=$((ERRORS+1))
    fi
else
    echo -e "${RED}❌ 后端.env文件不存在${NC}"
    ERRORS=$((ERRORS+1))
fi

# 检查是否有MySQL残留代码
echo "  - 检查MySQL残留..."
if grep -r "mysql" app/main.py | grep -q "import"; then
    echo -e "${YELLOW}⚠️  警告: 代码中仍有MySQL引用${NC}"
    ERRORS=$((ERRORS+1))
else
    echo -e "${GREEN}✅ 无MySQL残留${NC}"
fi

cd ..

# ============================================
# 2. 前端代码检查
# ============================================
echo ""
echo "🎨 检查前端代码..."

cd frontend

# 检查环境配置
echo "  - 检查前端配置..."
if [ -f ".env.local" ]; then
    API_URL=$(grep "NEXT_PUBLIC_API_URL" .env.local | cut -d'=' -f2)
    if [ "$API_URL" = "http://localhost:8000" ]; then
        echo -e "${GREEN}✅ 前端API端口正确 (8000)${NC}"
    else
        echo -e "${RED}❌ 前端API端口错误: $API_URL (应为8000)${NC}"
        ERRORS=$((ERRORS+1))
    fi

    if grep -q "SUPABASE_URL" .env.local; then
        echo -e "${GREEN}✅ 前端Supabase配置存在${NC}"
    else
        echo -e "${RED}❌ 前端缺少Supabase配置${NC}"
        ERRORS=$((ERRORS+1))
    fi
else
    echo -e "${RED}❌ 前端.env.local文件不存在${NC}"
    ERRORS=$((ERRORS+1))
fi

# TypeScript类型检查（如果安装了）
if command -v npx &> /dev/null; then
    echo "  - TypeScript类型检查..."
    npx tsc --noEmit --skipLibCheck 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ TypeScript类型正确${NC}"
    else
        echo -e "${YELLOW}⚠️  TypeScript有类型警告（非致命）${NC}"
    fi
fi

cd ..

# ============================================
# 3. 拼写检查
# ============================================
echo ""
echo "🔤 检查代码拼写..."

if command -v codespell &> /dev/null; then
    codespell --ignore-words-list=hist,recuse,nd,hso backend/ frontend/ 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 无拼写错误${NC}"
    else
        echo -e "${YELLOW}⚠️  发现拼写问题${NC}"
        ERRORS=$((ERRORS+1))
    fi
else
    echo -e "${YELLOW}⚠️  codespell未安装，跳过拼写检查${NC}"
fi

# ============================================
# 4. Git状态检查
# ============================================
echo ""
echo "📝 检查Git状态..."

# 检查是否有未提交的修改
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  有未提交的修改${NC}"
    echo "  修改的文件:"
    git status --short | head -5
    echo ""
    echo "  💡 建议执行: git add . && git commit -m 'fix: 修复问题'"
else
    echo -e "${GREEN}✅ 工作区干净${NC}"
fi

# ============================================
# 5. 缓存检查
# ============================================
echo ""
echo "🗑️  检查Python缓存..."

CACHE_COUNT=$(find backend/ -type d -name "__pycache__" 2>/dev/null | wc -l)
if [ $CACHE_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $CACHE_COUNT 个Python缓存目录${NC}"
    echo "  💡 建议执行: cd backend && find . -type d -name '__pycache__' -exec rm -rf {} +"
else
    echo -e "${GREEN}✅ 无Python缓存${NC}"
fi

# ============================================
# 6. 后端健康检查
# ============================================
echo ""
echo "💓 检查后端健康状态..."

HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✅ 后端运行正常${NC}"
else
    echo -e "${RED}❌ 后端未运行或不健康${NC}"
    echo "  💡 建议执行: cd backend && uvicorn app.main:app --reload"
    ERRORS=$((ERRORS+1))
fi

# ============================================
# 最终结果
# ============================================
echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！${NC}"
    exit 0
else
    echo -e "${RED}❌ 发现 $ERRORS 个问题${NC}"
    echo "请修复上述问题后再提交代码"
    exit 1
fi
