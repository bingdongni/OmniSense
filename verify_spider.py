"""
Verification script for OmniSense spider framework
Run this to verify the spider framework is properly installed and working
"""

import sys
from pathlib import Path


def check_imports():
    """Check if all modules can be imported"""
    print("Checking imports...")

    try:
        from omnisense.spider import BaseSpider, SpiderManager
        print("  ✓ omnisense.spider imports successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import omnisense.spider: {e}")
        return False

    try:
        from omnisense.spider.utils import PlaywrightHelper, ContentParser
        print("  ✓ omnisense.spider.utils imports successfully")
    except ImportError as e:
        print(f"  ✗ Failed to import omnisense.spider.utils: {e}")
        return False

    try:
        from playwright.async_api import async_playwright
        print("  ✓ Playwright is installed")
    except ImportError:
        print("  ✗ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    try:
        from bs4 import BeautifulSoup
        print("  ✓ BeautifulSoup4 is installed")
    except ImportError:
        print("  ✗ BeautifulSoup4 not installed. Run: pip install beautifulsoup4")
        return False

    try:
        from lxml import etree
        print("  ✓ lxml is installed")
    except ImportError:
        print("  ✗ lxml not installed. Run: pip install lxml")
        return False

    try:
        from fake_useragent import UserAgent
        print("  ✓ fake-useragent is installed")
    except ImportError:
        print("  ✗ fake-useragent not installed. Run: pip install fake-useragent")
        return False

    return True


def check_files():
    """Check if all required files exist"""
    print("\nChecking files...")

    base_path = Path(__file__).parent

    required_files = [
        "omnisense/spider/__init__.py",
        "omnisense/spider/base.py",
        "omnisense/spider/manager.py",
        "omnisense/spider/utils/__init__.py",
        "omnisense/spider/utils/playwright_helper.py",
        "omnisense/spider/utils/parser.py",
        "examples/spider_example.py",
        "tests/test_spider.py",
        "docs/spider_framework.md",
        "SPIDER_QUICKSTART.md",
    ]

    all_exist = True
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path} ({size:,} bytes)")
        else:
            print(f"  ✗ {file_path} not found")
            all_exist = False

    return all_exist


def check_class_structure():
    """Check if classes are properly structured"""
    print("\nChecking class structure...")

    try:
        from omnisense.spider.base import BaseSpider
        from omnisense.spider.manager import SpiderManager
        from omnisense.spider.utils import PlaywrightHelper, ContentParser

        # Check BaseSpider has required methods
        required_methods = [
            'login', 'search', 'get_user_profile', 'get_user_posts',
            'get_post_detail', 'get_comments', 'start', 'stop',
            'navigate', 'download_media', 'session'
        ]

        for method in required_methods:
            if hasattr(BaseSpider, method):
                print(f"  ✓ BaseSpider.{method} exists")
            else:
                print(f"  ✗ BaseSpider.{method} missing")
                return False

        # Check SpiderManager has required methods
        manager_methods = [
            'register_spider', 'get_spider', 'execute_task',
            'search_all_platforms', 'health_check'
        ]

        for method in manager_methods:
            if hasattr(SpiderManager, method):
                print(f"  ✓ SpiderManager.{method} exists")
            else:
                print(f"  ✗ SpiderManager.{method} missing")
                return False

        print("  ✓ All required methods exist")
        return True

    except Exception as e:
        print(f"  ✗ Error checking class structure: {e}")
        return False


def check_config():
    """Check if configuration is accessible"""
    print("\nChecking configuration...")

    try:
        from omnisense.config import config

        # Check spider config
        spider_config = config.spider
        print(f"  ✓ Spider concurrent_tasks: {spider_config.concurrent_tasks}")
        print(f"  ✓ Spider timeout: {spider_config.timeout}s")
        print(f"  ✓ Download media: {spider_config.download_media}")

        # Check anti-crawl config
        anti_crawl_config = config.anti_crawl
        print(f"  ✓ User agent rotation: {anti_crawl_config.user_agent_rotation}")
        print(f"  ✓ Request delay: {anti_crawl_config.request_delay_min}-{anti_crawl_config.request_delay_max}s")

        return True

    except Exception as e:
        print(f"  ✗ Error checking config: {e}")
        return False


def run_basic_test():
    """Run a basic functional test"""
    print("\nRunning basic functional test...")

    try:
        from omnisense.spider.base import BaseSpider
        from omnisense.spider.manager import SpiderManager
        from typing import Any, Dict, List

        # Create a test spider
        class TestSpider(BaseSpider):
            async def login(self, username: str, password: str) -> bool:
                return True

            async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
                return [{"id": "1", "title": "Test"}]

            async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
                return {"user_id": user_id, "username": "test"}

            async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
                return []

            async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
                return {"id": post_id}

            async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
                return []

        # Create spider instance
        spider = TestSpider(platform="test", headless=True)
        print(f"  ✓ Created spider: {spider}")

        # Create manager
        manager = SpiderManager(max_concurrent=3)
        manager.register_spider("test", TestSpider)
        print(f"  ✓ Created manager: {manager}")

        # Test parser
        from omnisense.spider.utils import ContentParser
        from omnisense.utils.logger import get_logger

        parser = ContentParser(get_logger("test"))
        html = "<div><p class='test'>Hello World</p></div>"
        soup = parser.parse_html(html)
        text = parser.extract_text(soup, ".test")
        assert text == "Hello World", "Parser test failed"
        print("  ✓ Parser working correctly")

        print("  ✓ All basic tests passed")
        return True

    except Exception as e:
        print(f"  ✗ Basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("OmniSense Spider Framework Verification")
    print("=" * 60)

    results = []

    results.append(("Imports", check_imports()))
    results.append(("Files", check_files()))
    results.append(("Class Structure", check_class_structure()))
    results.append(("Configuration", check_config()))
    results.append(("Basic Tests", run_basic_test()))

    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name:20s}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All checks passed! Spider framework is ready to use.")
        print("\nNext steps:")
        print("1. Read SPIDER_QUICKSTART.md for usage guide")
        print("2. Check examples/spider_example.py for examples")
        print("3. Read docs/spider_framework.md for full documentation")
        print("4. Implement platform-specific spiders in omnisense/spider/platforms/")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
