@echo off
REM 用于在 Windows 下一键启动 docker-compose 项目
cd /d %~dp0

echo [iCinema] 正在启动 docker-compose 服务...
docker-compose up --build
