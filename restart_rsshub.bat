@echo off
echo 正在停止并删除旧容器...
docker stop rsshub rsshub-browserless 2>nul
docker rm rsshub rsshub-browserless 2>nul

echo 正在启动新容器...
docker-compose -f rsshub-docker-compose.yml up -d

echo.
echo 等待服务启动...
timeout /t 5 /nobreak > nul

echo.
echo 容器状态：
docker ps

echo.
echo 浏览器日志：
docker logs rsshub-browserless --tail 10

echo.
echo RSSHub 日志：
docker logs rsshub --tail 10
