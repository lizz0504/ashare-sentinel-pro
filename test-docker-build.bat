@echo off
REM Docker构建测试脚本 - Windows版本

echo ========================================
echo Docker Build Test - Windows
echo ========================================
echo.

REM 检查Docker是否运行
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not running!
    echo.
    echo Please start Docker Desktop first:
    echo 1. Open Docker Desktop from Start Menu
    echo 2. Wait for the Docker icon to show in system tray
    echo 3. Run this script again
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM 创建测试环境变量
if not exist .env (
    echo Creating test .env file...
    (
        echo # Test environment variables
        echo SUPABASE_URL=https://jxitxkubtehxwjlnxdsw.supabase.co
        echo SUPABASE_SERVICE_KEY=test-key
        echo SUPABASE_JWT_SECRET=test-secret
        echo SUPABASE_ANON_KEY=test-anon-key
        echo DEEPSEEK_API_KEY=test-key
        echo TUSHARE_TOKEN=test-token
        echo TAVILY_API_KEY=test-key
        echo SERVER_IP=localhost
    ) > .env
    echo [OK] Test .env file created
)

echo.
echo ========================================
echo Building Backend Image...
echo ========================================
echo This may take 5-10 minutes...
echo.

cd backend
docker build -t ashare-backend:test .
if %errorlevel% neq 0 (
    echo [ERROR] Backend build failed!
    pause
    exit /b 1
)

echo [OK] Backend image built successfully
cd ..

echo.
echo ========================================
echo Building Frontend Image...
echo ========================================
echo This may take 5-10 minutes...
echo.

cd frontend
docker build -t ashare-frontend:test .
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)

echo [OK] Frontend image built successfully
cd ..

echo.
echo ========================================
echo Build Summary
echo ========================================
echo.
docker images | findstr ashare
echo.
echo ========================================
echo.
echo To clean up test images:
echo   docker rmi ashare-backend:test ashare-frontend:test
echo.
echo To deploy to Tencent Cloud:
echo   1. SSH to your server
echo   2. Run: ./deploy-tencent.sh
echo.
echo ========================================

pause
