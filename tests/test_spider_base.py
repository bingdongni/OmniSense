"""
Tests for base spider functionality
Tests BaseSpider class, browser automation, and utility methods
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Mock playwright before importing spider
import sys
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()


@pytest.fixture
def mock_spider_class():
    """Create a concrete implementation of BaseSpider for testing"""
    from omnisense.spider.base import BaseSpider

    class TestSpider(BaseSpider):
        async def login(self, username: str, password: str) -> bool:
            return True

        async def search(self, keyword: str, max_results: int = 20):
            return []

        async def get_user_profile(self, user_id: str):
            return {"user_id": user_id}

        async def get_user_posts(self, user_id: str, max_posts: int = 20):
            return []

        async def get_post_detail(self, post_id: str):
            return {"post_id": post_id}

        async def get_comments(self, post_id: str, max_comments: int = 100):
            return []

    return TestSpider


class TestSpiderInitialization:
    """Test spider initialization"""

    def test_spider_creation(self, mock_spider_class, temp_dir):
        """Test creating spider instance"""
        spider = mock_spider_class(
            platform="test_platform",
            headless=True,
            user_data_dir=temp_dir,
        )

        assert spider.platform == "test_platform"
        assert spider.headless is True
        assert spider.user_data_dir == temp_dir

    def test_default_parameters(self, mock_spider_class):
        """Test spider with default parameters"""
        spider = mock_spider_class(platform="test_platform")

        assert spider.platform == "test_platform"
        assert spider.headless is True
        assert spider.proxy is None

    def test_with_proxy(self, mock_spider_class):
        """Test spider with proxy"""
        spider = mock_spider_class(
            platform="test_platform",
            proxy="http://proxy.example.com:8080",
        )

        assert spider.proxy == "http://proxy.example.com:8080"


class TestBrowserManagement:
    """Test browser start/stop operations"""

    @pytest.mark.asyncio
    async def test_start_browser(self, mock_spider_class, mock_playwright):
        """Test starting browser"""
        spider = mock_spider_class(platform="test_platform")

        with patch('omnisense.spider.base.async_playwright') as mock_pw:
            mock_pw.return_value.__aenter__.return_value = mock_playwright

            await spider.start()

            assert spider._playwright is not None
            assert spider._browser is not None

    @pytest.mark.asyncio
    async def test_stop_browser(self, mock_spider_class):
        """Test stopping browser"""
        spider = mock_spider_class(platform="test_platform")

        spider._page = AsyncMock()
        spider._context = AsyncMock()
        spider._browser = AsyncMock()
        spider._playwright = AsyncMock()

        await spider.stop()

        spider._page.close.assert_called_once()
        spider._context.close.assert_called_once()
        spider._browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_context_manager(self, mock_spider_class, mock_playwright):
        """Test session context manager"""
        spider = mock_spider_class(platform="test_platform")

        with patch('omnisense.spider.base.async_playwright') as mock_pw:
            mock_pw.return_value.__aenter__.return_value = mock_playwright
            spider._page = AsyncMock()
            spider._context = AsyncMock()
            spider._browser = AsyncMock()
            spider._playwright = AsyncMock()

            async with spider.session():
                assert spider._page is not None


class TestNavigationMethods:
    """Test navigation and interaction methods"""

    @pytest.mark.asyncio
    async def test_navigate(self, mock_spider_class):
        """Test page navigation"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()

        result = await spider.navigate("https://example.com")

        assert result is True
        spider._page.goto.assert_called()

    @pytest.mark.asyncio
    async def test_wait_for_selector(self, mock_spider_class):
        """Test waiting for selector"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()

        result = await spider.wait_for_selector(".test-selector")

        assert result is True
        spider._page.wait_for_selector.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_element(self, mock_spider_class):
        """Test clicking element"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()

        result = await spider.click_element(".button")

        assert result is True
        spider._page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_type_text(self, mock_spider_class):
        """Test typing text"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()

        result = await spider.type_text("#input", "test text")

        assert result is True
        spider._page.fill.assert_called()
        spider._page.type.assert_called()


class TestDataExtraction:
    """Test data extraction methods"""

    @pytest.mark.asyncio
    async def test_get_element_text(self, mock_spider_class):
        """Test getting element text"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()
        spider._page.text_content = AsyncMock(return_value="Test content")

        text = await spider.get_element_text(".element")

        assert text == "Test content"

    @pytest.mark.asyncio
    async def test_get_element_attribute(self, mock_spider_class):
        """Test getting element attribute"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()
        spider._page.get_attribute = AsyncMock(return_value="test-value")

        attr = await spider.get_element_attribute(".element", "href")

        assert attr == "test-value"

    @pytest.mark.asyncio
    async def test_execute_script(self, mock_spider_class):
        """Test executing JavaScript"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()
        spider._page.evaluate = AsyncMock(return_value=42)

        result = await spider.execute_script("return 42;")

        assert result == 42


class TestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_spider_class):
        """Test request rate limiting"""
        from omnisense.config import config

        original_min = config.anti_crawl.request_delay_min
        original_max = config.anti_crawl.request_delay_max

        config.anti_crawl.request_delay_min = 0.1
        config.anti_crawl.request_delay_max = 0.2

        spider = mock_spider_class(platform="test_platform")

        import time
        start = time.time()
        await spider._wait_for_rate_limit()
        await spider._wait_for_rate_limit()
        elapsed = time.time() - start

        # Should have some delay
        assert elapsed >= 0.1

        config.anti_crawl.request_delay_min = original_min
        config.anti_crawl.request_delay_max = original_max


class TestRetryLogic:
    """Test retry mechanism"""

    @pytest.mark.asyncio
    async def test_retry_on_error(self, mock_spider_class):
        """Test retry on error"""
        spider = mock_spider_class(platform="test_platform")

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Test error")
            return "success"

        result = await spider._retry_on_error(failing_func)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_spider_class):
        """Test max retries exceeded"""
        spider = mock_spider_class(platform="test_platform")
        spider.max_retries = 2

        async def always_failing_func():
            raise Exception("Always fails")

        with pytest.raises(Exception):
            await spider._retry_on_error(always_failing_func)


class TestMediaDownload:
    """Test media download functionality"""

    @pytest.mark.asyncio
    async def test_download_media(self, mock_spider_class, temp_dir):
        """Test downloading media"""
        from omnisense.config import config

        original_download = config.spider.download_media
        config.spider.download_media = True

        spider = mock_spider_class(platform="test_platform")
        spider._download_dir = temp_dir
        spider._page = AsyncMock()
        spider.helper = Mock()
        spider.helper.download_file = AsyncMock(return_value=True)

        result = await spider.download_media(
            "https://example.com/video.mp4",
            filename="test.mp4"
        )

        assert result is not None
        assert result.name == "test.mp4"

        config.spider.download_media = original_download

    @pytest.mark.asyncio
    async def test_skip_duplicate_download(self, mock_spider_class, temp_dir):
        """Test skipping duplicate downloads"""
        spider = mock_spider_class(platform="test_platform")
        spider._download_dir = temp_dir

        # First download
        url = "https://example.com/video.mp4"
        spider._page = AsyncMock()
        spider.helper = Mock()
        spider.helper.download_file = AsyncMock(return_value=True)

        result1 = await spider.download_media(url)

        # Second download of same URL
        result2 = await spider.download_media(url)

        # Should skip second download
        assert result2 is None


class TestCookieManagement:
    """Test cookie management"""

    @pytest.mark.asyncio
    async def test_load_cookies(self, mock_spider_class, temp_dir):
        """Test loading cookies"""
        spider = mock_spider_class(platform="test_platform")
        spider._context = AsyncMock()

        # Create cookies file
        cookies_file = temp_dir / "cookies.json"
        import json
        cookies = [{"name": "test", "value": "value"}]
        with open(cookies_file, "w") as f:
            json.dump(cookies, f)

        spider._cookies_file = cookies_file
        await spider._load_cookies()

        spider._context.add_cookies.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_cookies(self, mock_spider_class, temp_dir):
        """Test saving cookies"""
        spider = mock_spider_class(platform="test_platform")
        spider._context = AsyncMock()
        spider._context.cookies = AsyncMock(return_value=[
            {"name": "test", "value": "value"}
        ])

        spider._cookies_file = temp_dir / "cookies.json"
        await spider._save_cookies()

        assert spider._cookies_file.exists()


class TestScrolling:
    """Test scrolling functionality"""

    @pytest.mark.asyncio
    async def test_scroll_to_bottom(self, mock_spider_class):
        """Test scrolling to bottom"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()

        # Mock scroll height - first different, then same (reached bottom)
        spider._page.evaluate = AsyncMock(side_effect=[1000, 2000, 2000])

        await spider.scroll_to_bottom(wait_time=0.1, max_scrolls=3)

        # Should stop when height doesn't change
        assert spider._page.evaluate.call_count >= 2


class TestScreenshot:
    """Test screenshot functionality"""

    @pytest.mark.asyncio
    async def test_take_screenshot(self, mock_spider_class, temp_dir):
        """Test taking screenshot"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()
        spider._download_dir = temp_dir

        result = await spider.screenshot("test.png")

        assert result is not None
        spider._page.screenshot.assert_called_once()


class TestAbstractMethods:
    """Test that abstract methods must be implemented"""

    def test_abstract_methods_required(self):
        """Test that abstract methods must be implemented"""
        from omnisense.spider.base import BaseSpider

        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            BaseSpider(platform="test")


class TestSpiderPerformance:
    """Test spider performance"""

    @pytest.mark.asyncio
    async def test_navigation_performance(self, mock_spider_class, performance_tracker):
        """Test navigation performance"""
        spider = mock_spider_class(platform="test_platform")
        spider._page = AsyncMock()

        performance_tracker.start()
        for _ in range(10):
            await spider.navigate("https://example.com")
        elapsed = performance_tracker.stop()

        assert elapsed < 1.0, f"10 navigations took {elapsed}s"
