@echo off
REM ============================================
REM Windows快速部署脚本
REM 将代码和配置上传到腾讯云服务器
REM ============================================

echo ========================================
echo AShare Sentinel Pro - 快速部署到腾讯云
echo ========================================
echo.

set /p SERVER_IP="请输入服务器IP: "
set /p SSH_USER="请输入SSH用户名 (默认root): "
if "%SSH_USER%"=="" set SSH_USER=root

echo.
echo [1/5] 检查本地文件...
if not exist "docker-compose.prod.yml" (
    echo 错误: 找不到 docker-compose.prod.yml
    pause
    exit /b 1
)
if not exist ".env.docker.example" (
    echo 错误: 找不到 .env.docker.example
    pause
    exit /b 1
)
echo ✓ 本地文件检查完成
echo.

echo [2/5] 上传代码到服务器...
echo 正在上传，请稍候...
tar -czf ashare-upload.tar.gz --exclude=node_modules --exclude=.next --exclude=.git --exclude=ashare-upload.tar.gz .

scp ashare-upload.tar.gz %SSH_USER%@%SERVER_IP%:/tmp/
del ashare-upload.tar.gz
echo ✓ 代码上传完成
echo.

echo [3/5] 配置服务器环境...
ssh %SSH_USER%@%SERVER_IP% "bash -s" << 'ENDSSH'
# 安装Docker
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
fi

# 安装Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "安装Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 解压代码
cd /root
mkdir -p ashare-sentinel-pro
tar -xzf /tmp/ashare-upload.tar.gz -C ashare-sentinel-pro
rm /tmp/ashare-upload.tar.gz

cd ashare-sentinel-pro

# 创建.env文件（如果不存在）
if [ ! -f .env ]; then
    cp .env.docker.example .env
    echo "警告: 请编辑 .env 文件填入正确的API密钥"
    echo "nano /root/ashare-sentinel-pro/.env"
fi

echo "✓ 服务器环境配置完成"
ENDSSH

echo.
echo [4/5] 部署应用...
ssh %SSH_USER%@%SERVER_IP% "cd /root/ashare-sentinel-pro && docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml build && docker-compose -f docker-compose.prod.yml up -d"
echo ✓ 应用部署完成
echo.

echo [5/5] 验证部署...
ssh %SSH_USER%@%SERVER_IP% "cd /root/ashare-sentinel-pro && docker-compose -f docker-compose.prod.yml ps"
echo.

echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 访问地址:
echo   前端:  http://%SERVER_IP%:3000
echo   后端:  http://%SERVER_IP%:8000
echo   API文档: http://%SERVER_IP%:8000/docs
echo.
echo 下一步:
echo   1. SSH登录服务器: ssh %SSH_USER%@%SERVER_IP%
echo   2. 编辑环境变量: nano /root/ashare-sentinel-pro/.env
echo   3. 重启服务: cd /root/ashare-sentinel-pro && docker-compose -f docker-compose.prod.yml restart
echo.
pause
