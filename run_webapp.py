#!/usr/bin/env python
"""
OmniSense Web Application Launcher
Quick start script for the Streamlit web interface
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Launch the OmniSense Streamlit application"""

    # Get the app.py path
    app_path = Path(__file__).parent / "app.py"

    if not app_path.exists():
        print("❌ Error: app.py not found!")
        print(f"Expected location: {app_path}")
        sys.exit(1)

    print("🚀 Launching OmniSense Web Application...")
    print("=" * 60)
    print("📍 Application: OmniSense - 全域数据智能洞察平台")
    print(f"📂 Location: {app_path}")
    print("🌐 Default URL: http://localhost:8501")
    print("=" * 60)
    print()
    print("💡 Tips:")
    print("  - Use Ctrl+C to stop the server")
    print("  - Access the app at http://localhost:8501")
    print("  - The app will auto-reload on code changes")
    print()
    print("🔧 Custom port: streamlit run app.py --server.port 8502")
    print("=" * 60)
    print()

    try:
        # Launch Streamlit
        subprocess.run([
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n\n✅ OmniSense Web Application stopped")
    except Exception as e:
        print(f"\n❌ Error launching application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
