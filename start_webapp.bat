@echo off
REM OmniSense Web Application Launcher for Windows
REM Double-click this file to start the web application

echo ========================================
echo   OmniSense Web Application
echo   全域数据智能洞察平台
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [*] Python found
echo.

REM Check if Streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [!] Streamlit not found, installing...
    pip install streamlit plotly pandas
    echo.
)

echo [*] Starting OmniSense Web Application...
echo [*] URL: http://localhost:8501
echo [*] Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

REM Start the application
python -m streamlit run app.py --server.port 8501 --server.address localhost --browser.gatherUsageStats false

pause
