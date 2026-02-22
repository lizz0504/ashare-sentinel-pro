#!/bin/bash
# ============================================
# 环境变量配置向导
# 在服务器上运行此脚本，交互式填写密钥
# ============================================

echo "========================================"
echo "  AShare Sentinel Pro - 环境变量配置向导"
echo "========================================"
echo ""

# 检查是否已存在.env文件
if [ -f .env ]; then
    echo "⚠️  检测到已存在 .env 文件"
    read -p "是否覆盖？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消配置"
        exit 0
    fi
    rm .env
fi

echo "请按照提示输入配置信息（留空保持默认值）"
echo "========================================"
echo ""

# 获取Supabase URL
read -p "SUPABASE_URL [https://jxitxkubtehxwjlnxdsw.supabase.co]: " supabase_url
supabase_url=${supabase_url:-https://jxitxkubtehxwjlnxdsw.supabase.co}

# 获取Service Key
read -p "SUPABASE_SERVICE_KEY: " supabase_service_key
while [ -z "$supabase_service_key" ]; do
    echo "❌ Service Key 不能为空"
    read -p "SUPABASE_SERVICE_KEY: " supabase_service_key
done

# 获取JWT Secret
read -p "SUPABASE_JWT_SECRET: " supabase_jwt
while [ -z "$supabase_jwt" ]; do
    echo "❌ JWT Secret 不能为空"
    read -p "SUPABASE_JWT_SECRET: " supabase_jwt
done

# 获取Anon Key
read -p "SUPABASE_ANON_KEY: " supabase_anon
while [ -z "$supabase_anon" ]; do
    echo "❌ Anon Key 不能为空"
    read -p "SUPABASE_ANON_KEY: " supabase_anon
done

echo ""
echo "----------------------------------------"

# 获取DeepSeek Key
read -p "DEEPSEEK_API_KEY: " deepseek_key
while [ -z "$deepseek_key" ]; do
    echo "❌ DeepSeek API Key 不能为空"
    read -p "DEEPSEEK_API_KEY: " deepseek_key
done

# 获取Tavily Key
read -p "TAVILY_API_KEY: " tavily_key
while [ -z "$tavily_key" ]; do
    echo "❌ Tavily API Key 不能为空"
    read -p "TAVILY_API_KEY: " tavily_key
done

# 获取Tushare Token
read -p "TUSHARE_TOKEN: " tushare_token
while [ -z "$tushare_token" ]; do
    echo "❌ Tushare Token 不能为空"
    read -p "TUSHARE_TOKEN: " tushare_token
done

echo ""
echo "----------------------------------------"

# 获取服务器IP（自动检测）
SERVER_IP=$(curl -s ifconfig.me)
read -p "服务器IP [自动检测: $SERVER_IP]: " server_ip
server_ip=${server_ip:-$SERVER_IP}

# 创建.env文件
cat > .env << EOF
# ============================================
# AShare Sentinel Pro - 环境变量配置
# 自动生成时间: $(date)
# ============================================

# Supabase配置
SUPABASE_URL=$supabase_url
SUPABASE_SERVICE_KEY=$supabase_service_key
SUPABASE_JWT_SECRET=$supabase_jwt
SUPABASE_ANON_KEY=$supabase_anon

# AI API配置
DEEPSEEK_API_KEY=$deepseek_key
TAVILY_API_KEY=$tavily_key

# 数据源配置
TUSHARE_TOKEN=$tushare_token

# 服务器配置
SERVER_IP=$server_ip
EOF

# 设置权限
chmod 600 .env

echo ""
echo "========================================"
echo "✅ .env 文件创建成功！"
echo "========================================"
echo ""
echo "文件位置: $(pwd)/.env"
echo "权限设置: 600 (仅所有者可读写)"
echo ""
echo "配置摘要："
echo "  Supabase URL: $supabase_url"
echo "  服务器IP: $server_ip"
echo ""
echo "下一步："
echo "  1. 验证配置: cat .env"
echo "  2. 启动服务: docker-compose -f docker-compose.prod.yml up -d"
echo ""
