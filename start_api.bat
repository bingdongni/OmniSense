@echo off
REM Startup script for OmniSense API on Windows

echo =========================================
echo Starting OmniSense API Services
echo =========================================

REM Check if .env file exists
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please edit .env with your configuration
)

REM Create required directories
echo Creating required directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist cache mkdir cache

REM Start services
echo Starting Docker services...
docker-compose -f docker-compose.api.yml up -d

REM Wait for services
echo Waiting for services to start...
timeout /t 10 /nobreak > nul

REM Check service health
echo Checking service health...

echo.
echo =========================================
echo OmniSense API Services Started
echo =========================================
echo.
echo Access points:
echo   - API Documentation: http://localhost:8000/docs
echo   - Alternative Docs:  http://localhost:8000/redoc
echo   - Health Check:      http://localhost:8000/health
echo   - Flower (Celery):   http://localhost:5555
echo   - Prometheus:        http://localhost:9090
echo   - Grafana:           http://localhost:3000 (admin/admin)
echo.
echo View logs:
echo   docker-compose -f docker-compose.api.yml logs -f
echo.
echo Stop services:
echo   docker-compose -f docker-compose.api.yml down
echo.
