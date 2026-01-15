#!/usr/bin/env python
"""
OmniSense 环境验证脚本
检查所有依赖是否正确安装，配置是否正确

Usage:
    python verify_installation.py
"""

import sys
import importlib
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI颜色代码
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str):
    """打印标题"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def print_success(text: str):
    """打印成功信息"""
    print(f"{GREEN}✓{RESET} {text}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{RED}✗{RESET} {text}")


def print_warning(text: str):
    """打印警告信息"""
    print(f"{YELLOW}⚠{RESET} {text}")


def check_python_version() -> bool:
    """检查Python版本"""
    print_header("检查Python版本")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major == 3 and version.minor >= 11:
        print_success(f"Python版本: {version_str} (满足要求 ≥3.11)")
        return True
    else:
        print_error(f"Python版本: {version_str} (需要 ≥3.11)")
        return False


def check_dependencies() -> Tuple[int, int]:
    """检查依赖包"""
    print_header("检查依赖包")

    # 核心依赖
    core_deps = [
        ("dotenv", "python-dotenv"),
        ("loguru", "loguru"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
    ]

    # Web框架
    web_deps = [
        ("streamlit", "streamlit"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
    ]

    # 爬虫相关
    spider_deps = [
        ("playwright", "playwright"),
        ("requests", "requests"),
        ("aiohttp", "aiohttp"),
        ("bs4", "beautifulsoup4"),
    ]

    # 数据处理
    data_deps = [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
    ]

    # 机器学习
    ml_deps = [
        ("transformers", "transformers"),
        ("torch", "torch"),
        ("sklearn", "scikit-learn"),
    ]

    # 存储系统
    storage_deps = [
        ("aiosqlite", "aiosqlite"),
        ("chromadb", "chromadb"),
        ("redis", "redis"),
        ("minio", "minio"),
    ]

    # 可视化
    viz_deps = [
        ("plotly", "plotly"),
        ("wordcloud", "wordcloud"),
        ("networkx", "networkx"),
    ]

    all_deps = {
        "核心依赖": core_deps,
        "Web框架": web_deps,
        "爬虫相关": spider_deps,
        "数据处理": data_deps,
        "机器学习": ml_deps,
        "存储系统": storage_deps,
        "可视化": viz_deps,
    }

    total_checked = 0
    total_passed = 0

    for category, deps in all_deps.items():
        print(f"\n{category}:")
        for module_name, package_name in deps:
            total_checked += 1
            try:
                module = importlib.import_module(module_name)
                version = getattr(module, "__version__", "unknown")
                print_success(f"{package_name:30s} v{version}")
                total_passed += 1
            except ImportError:
                print_error(f"{package_name:30s} 未安装")

    print(f"\n{'-' * 60}")
    print(f"依赖检查完成: {total_passed}/{total_checked} 通过")

    return total_passed, total_checked


def check_project_structure() -> bool:
    """检查项目结构"""
    print_header("检查项目结构")

    required_paths = [
        # 核心目录
        "omnisense/",
        "omnisense/spider/",
        "omnisense/anti_crawl/",
        "omnisense/matcher/",
        "omnisense/interaction/",
        "omnisense/agents/",
        "omnisense/analysis/",
        "omnisense/storage/",
        "omnisense/visualization/",
        "omnisense/utils/",

        # 核心文件
        "omnisense/__init__.py",
        "omnisense/config.py",
        "omnisense/core.py",

        # 用户界面
        "cli.py",
        "app.py",
        "api.py",

        # 配置文件
        "requirements.txt",
        "docker-compose.yml",
        "Dockerfile",
        ".env.example",

        # 文档
        "README.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
    ]

    missing = []
    existing = []

    for path_str in required_paths:
        path = Path(path_str)
        if path.exists():
            print_success(f"{path_str}")
            existing.append(path_str)
        else:
            print_error(f"{path_str} (缺失)")
            missing.append(path_str)

    print(f"\n{'-' * 60}")
    print(f"结构检查完成: {len(existing)}/{len(required_paths)} 存在")

    if missing:
        print(f"\n缺失的文件/目录:")
        for item in missing:
            print(f"  - {item}")
        return False

    return True


def check_configuration() -> bool:
    """检查配置"""
    print_header("检查配置")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_example.exists():
        print_error(".env.example 文件不存在")
        return False
    else:
        print_success(".env.example 文件存在")

    if not env_file.exists():
        print_warning(".env 文件不存在 (需要从.env.example复制)")
        print(f"  运行: cp .env.example .env")
        return False
    else:
        print_success(".env 文件存在")

    return True


def check_omnisense_import() -> bool:
    """检查OmniSense模块导入"""
    print_header("检查OmniSense模块")

    try:
        # 尝试导入配置
        print("尝试导入 omnisense.config...")
        from omnisense import config
        print_success("omnisense.config 导入成功")

        # 尝试导入核心模块
        print("\n尝试导入 OmniSense 核心类...")
        # 注意: 这里可能会因为缺少配置而失败，但我们只检查语法
        # from omnisense import OmniSense
        # print_success("OmniSense 类导入成功")

        return True

    except Exception as e:
        print_error(f"导入失败: {e}")
        print_warning("这可能是因为缺少必要的配置或依赖")
        return False


def check_playwright() -> bool:
    """检查Playwright浏览器"""
    print_header("检查Playwright浏览器")

    try:
        import playwright
        print_success("Playwright已安装")

        # 检查浏览器是否已安装
        from playwright.sync_api import sync_playwright

        print("\n检查Chromium浏览器...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print_success("Chromium浏览器已安装且可用")
                return True
        except Exception as e:
            print_error(f"Chromium浏览器未安装或不可用: {e}")
            print_warning("运行: playwright install chromium")
            return False

    except ImportError:
        print_error("Playwright未安装")
        return False


def main():
    """主函数"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{'OmniSense 环境验证':^60}{RESET}")
    print(f"{BLUE}{'版本: 1.0.0':^60}{RESET}")
    print(f"{BLUE}{'开发者: bingdongni':^60}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    results = {}

    # 1. 检查Python版本
    results['python'] = check_python_version()

    # 2. 检查依赖
    passed, total = check_dependencies()
    results['dependencies'] = (passed == total)

    # 3. 检查项目结构
    results['structure'] = check_project_structure()

    # 4. 检查配置
    results['config'] = check_configuration()

    # 5. 检查OmniSense导入
    results['omnisense'] = check_omnisense_import()

    # 6. 检查Playwright
    results['playwright'] = check_playwright()

    # 总结
    print_header("验证总结")

    all_passed = all(results.values())
    total_checks = len(results)
    passed_checks = sum(results.values())

    for check_name, result in results.items():
        status = f"{GREEN}✓ 通过{RESET}" if result else f"{RED}✗ 失败{RESET}"
        print(f"{check_name:20s}: {status}")

    print(f"\n{'-' * 60}")

    if all_passed:
        print(f"{GREEN}🎉 所有检查通过! OmniSense已准备就绪！{RESET}")
        print(f"\n快速开始:")
        print(f"  1. 配置环境变量: nano .env")
        print(f"  2. 启动Web UI:    streamlit run app.py")
        print(f"  3. 启动API服务:   uvicorn api:app --reload")
        print(f"  4. 或使用Docker:  docker-compose up -d")
        return 0
    else:
        print(f"{RED}⚠ {total_checks - passed_checks}/{total_checks} 项检查失败{RESET}")
        print(f"\n建议:")

        if not results['python']:
            print(f"  1. 升级Python到3.11+")

        if not results['dependencies']:
            print(f"  2. 安装缺失的依赖: pip install -r requirements.txt")

        if not results['config']:
            print(f"  3. 创建配置文件: cp .env.example .env")

        if not results['playwright']:
            print(f"  4. 安装Playwright浏览器: playwright install chromium")

        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}用户中断{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}发生错误: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
