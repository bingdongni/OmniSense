#!/bin/bash
# OmniSense Web Application Launcher for Unix/Linux/macOS

echo "========================================"
echo "  OmniSense Web Application"
echo "  全域数据智能洞察平台"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.10+ from https://www.python.org/"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Check if Streamlit is installed
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "⚠️  Streamlit not found, installing..."
    pip3 install streamlit plotly pandas
    echo ""
fi

echo "🚀 Starting OmniSense Web Application..."
echo "🌐 URL: http://localhost:8501"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""
echo "========================================"
echo ""

# Start the application
python3 -m streamlit run app.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.gatherUsageStats false
