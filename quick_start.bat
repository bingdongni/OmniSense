@echo off
REM OmniSense 快速启动脚本 (Windows)
REM 用于快速体验项目功能

echo ============================================================
echo  OmniSense 快速启动
echo ============================================================
echo.

echo [1/5] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: Python未安装或不在PATH中
    pause
    exit /b 1
)
echo.

echo [2/5] 检查项目结构...
if not exist "omnisense\" (
    echo 错误: omnisense目录不存在，请确认在项目根目录运行
    pause
    exit /b 1
)
echo 项目结构正确
echo.

echo [3/5] 验证安装...
python verify_installation.py
if %errorlevel% neq 0 (
    echo.
    echo 提示: 验证未完全通过，但可以继续测试基础功能
    echo.
)
echo.

echo [4/5] 运行功能演示...
echo.
echo ============================================================
echo  CLI 命令演示
echo ============================================================
echo.

echo --- 查看所有平台 ---
python cli.py platforms
echo.

echo --- 查看系统状态 ---
python cli.py status
echo.

echo --- 查看帮助信息 ---
python cli.py --help
echo.

echo [5/5] 完成!
echo.
echo ============================================================
echo  快速开始完成
echo ============================================================
echo.
echo 接下来可以尝试:
echo.
echo 1. 数据采集:
echo    python cli.py collect weibo --query "科技" --limit 5
echo.
echo 2. 查看平台详情:
echo    python cli.py platforms --detail
echo.
echo 3. 启动Web UI (需要先安装依赖):
echo    pip install streamlit
echo    streamlit run app.py
echo.
echo 4. 查看完整使用指南:
echo    type LOCAL_RUN_GUIDE.md
echo.

pause
