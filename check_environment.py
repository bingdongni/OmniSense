#!/usr/bin/env python
"""
OmniSense Web Application Environment Checker
Verifies system requirements before launching the application
"""

import sys
import subprocess
from pathlib import Path


def print_header():
    """Print header"""
    print("=" * 60)
    print("  OmniSense Web Application - Environment Checker")
    print("  全域数据智能洞察平台 - 环境检查")
    print("=" * 60)
    print()


def check_python_version():
    """Check Python version"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major >= 3 and version.minor >= 10:
        print(f"✅ Python {version_str} (OK)")
        return True
    else:
        print(f"❌ Python {version_str} (Requires 3.10+)")
        return False


def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name

    try:
        __import__(import_name)
        print(f"✅ {package_name} (Installed)")
        return True
    except ImportError:
        print(f"❌ {package_name} (Not installed)")
        return False


def check_required_packages():
    """Check required packages"""
    print("\n🔍 Checking required packages...")

    packages = {
        "streamlit": "streamlit",
        "plotly": "plotly",
        "pandas": "pandas",
        "omnisense": "omnisense",
    }

    all_installed = True
    for package_name, import_name in packages.items():
        if not check_package(package_name, import_name):
            all_installed = False

    return all_installed


def check_optional_packages():
    """Check optional packages"""
    print("\n🔍 Checking optional packages...")

    packages = {
        "aiohttp": "aiohttp",
        "playwright": "playwright",
        "chromadb": "chromadb",
        "langchain": "langchain",
    }

    for package_name, import_name in packages.items():
        check_package(package_name, import_name)


def check_files():
    """Check required files"""
    print("\n🔍 Checking required files...")

    files = [
        "app.py",
        "omnisense/__init__.py",
        "omnisense/core.py",
    ]

    all_exist = True
    base_path = Path(__file__).parent

    for file in files:
        file_path = base_path / file
        if file_path.exists():
            print(f"✅ {file} (Found)")
        else:
            print(f"❌ {file} (Not found)")
            all_exist = False

    return all_exist


def check_directories():
    """Check required directories"""
    print("\n🔍 Checking required directories...")

    directories = [
        "data",
        "logs",
        "cache",
        "reports",
    ]

    base_path = Path(__file__).parent

    for directory in directories:
        dir_path = base_path / directory
        if not dir_path.exists():
            print(f"⚠️  {directory} (Creating...)")
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ {directory} (Created)")
            except Exception as e:
                print(f"❌ {directory} (Failed: {e})")
        else:
            print(f"✅ {directory} (Exists)")


def check_port():
    """Check if port 8501 is available"""
    print("\n🔍 Checking port availability...")

    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8501))
        sock.close()

        if result != 0:
            print("✅ Port 8501 (Available)")
            return True
        else:
            print("⚠️  Port 8501 (In use - will use next available port)")
            return True
    except Exception as e:
        print(f"⚠️  Port check failed: {e}")
        return True


def check_llm_services():
    """Check if LLM services are running"""
    print("\n🔍 Checking LLM services (optional)...")

    # Check Ollama
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama (Running)")
        else:
            print("⚠️  Ollama (Not responding)")
    except Exception:
        print("⚠️  Ollama (Not running - required for local LLM analysis)")

    print("   Note: You can also use OpenAI or Anthropic APIs")


def install_missing_packages(packages):
    """Install missing packages"""
    print("\n📦 Installing missing packages...")

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages,
            check=True
        )
        print("✅ Installation completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False


def main():
    """Main function"""
    print_header()

    # Track results
    results = {
        "python": False,
        "packages": False,
        "files": False,
    }

    # Check Python version
    results["python"] = check_python_version()

    if not results["python"]:
        print("\n" + "=" * 60)
        print("❌ FAILED: Python 3.10+ is required")
        print("   Please upgrade Python: https://www.python.org/downloads/")
        print("=" * 60)
        return False

    # Check required packages
    results["packages"] = check_required_packages()

    # Check optional packages
    check_optional_packages()

    # Check files
    results["files"] = check_files()

    # Check directories
    check_directories()

    # Check port
    check_port()

    # Check LLM services
    check_llm_services()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Environment Check Summary")
    print("=" * 60)

    all_passed = all(results.values())

    if all_passed:
        print("✅ All checks passed!")
        print("\n🚀 You can now start the application:")
        print("   - Windows: start_webapp.bat")
        print("   - Linux/macOS: ./start_webapp.sh")
        print("   - Command: python run_webapp.py")
        print("   - Direct: streamlit run app.py")
    else:
        print("⚠️  Some checks failed:")

        if not results["packages"]:
            print("\n📦 To install missing packages:")
            print("   pip install streamlit plotly pandas")
            print("   pip install -e .")

        if not results["files"]:
            print("\n📂 Missing files detected. Please ensure:")
            print("   - app.py exists in the current directory")
            print("   - omnisense package is properly installed")

        print("\n❓ Need help?")
        print("   - See WEBAPP_README.md for detailed instructions")
        print("   - See STREAMLIT_GUIDE.md for usage guide")
        print("   - Check documentation at docs.omnisense.com")

    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
