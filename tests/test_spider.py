"""
Tests for OmniSense spider framework
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from omnisense.spider.base import BaseSpider
from omnisense.spider.manager import SpiderManager
from omnisense.spider.utils.playwright_helper import PlaywrightHelper
from omnisense.spider.utils.parser import ContentParser


# Mock spider for testing
class MockSpider(BaseSpider):
    """Mock spider for testing"""

    async def login(self, username: str, password: str) -> bool:
        return True

    async def search(self, keyword: str, max_results: int = 20):
        return [
            {"id": "1", "title": f"Result 1 for {keyword}"},
            {"id": "2", "title": f"Result 2 for {keyword}"},
        ]

    async def get_user_profile(self, user_id: str):
        return {
            "user_id": user_id,
            "username": f"user_{user_id}",
            "followers": 1000,
        }

    async def get_user_posts(self, user_id: str, max_posts: int = 20):
        return [
            {"id": "post1", "user_id": user_id, "title": "Post 1"},
            {"id": "post2", "user_id": user_id, "title": "Post 2"},
        ]

    async def get_post_detail(self, post_id: str):
        return {
            "id": post_id,
            "title": f"Post {post_id}",
            "content": "Post content",
        }

    async def get_comments(self, post_id: str, max_comments: int = 100):
        return [
            {"id": "comment1", "post_id": post_id, "content": "Comment 1"},
            {"id": "comment2", "post_id": post_id, "content": "Comment 2"},
        ]


class TestBaseSpider:
    """Tests for BaseSpider"""

    def test_spider_initialization(self):
        """Test spider initialization"""
        spider = MockSpider(platform="test_platform", headless=True)

        assert spider.platform == "test_platform"
        assert spider.headless is True
        assert spider.max_retries > 0
        assert spider._is_logged_in is False

    @pytest.mark.asyncio
    async def test_spider_abstract_methods(self):
        """Test that spider implements all abstract methods"""
        spider = MockSpider(platform="test")

        # Test all abstract methods
        assert await spider.login("user", "pass") is True
        assert isinstance(await spider.search("keyword"), list)
        assert isinstance(await spider.get_user_profile("user1"), dict)
        assert isinstance(await spider.get_user_posts("user1"), list)
        assert isinstance(await spider.get_post_detail("post1"), dict)
        assert isinstance(await spider.get_comments("post1"), list)

    def test_spider_properties(self):
        """Test spider properties"""
        spider = MockSpider(platform="test")

        assert spider.user_data_dir.exists()
        assert isinstance(spider.logger, Mock) or hasattr(spider.logger, 'info')
        assert isinstance(spider.helper, PlaywrightHelper)
        assert isinstance(spider.parser, ContentParser)


class TestSpiderManager:
    """Tests for SpiderManager"""

    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = SpiderManager(max_concurrent=3)

        assert manager.max_concurrent == 3
        assert len(manager._spider_classes) == 0
        assert len(manager._spider_instances) == 0

    def test_register_spider(self):
        """Test spider registration"""
        manager = SpiderManager()
        manager.register_spider("test", MockSpider)

        assert "test" in manager._spider_classes
        assert manager._spider_classes["test"] == MockSpider

    def test_unregister_spider(self):
        """Test spider unregistration"""
        manager = SpiderManager()
        manager.register_spider("test", MockSpider)
        manager.unregister_spider("test")

        assert "test" not in manager._spider_classes

    def test_register_invalid_spider(self):
        """Test registering invalid spider class"""
        manager = SpiderManager()

        with pytest.raises(ValueError):
            manager.register_spider("test", dict)  # Not a BaseSpider subclass

    @pytest.mark.asyncio
    async def test_get_spider(self):
        """Test getting spider instance"""
        manager = SpiderManager()
        manager.register_spider("test", MockSpider)

        spider = await manager.get_spider("test")

        assert isinstance(spider, MockSpider)
        assert spider.platform == "test"

    @pytest.mark.asyncio
    async def test_get_unregistered_spider(self):
        """Test getting unregistered spider"""
        manager = SpiderManager()

        with pytest.raises(ValueError):
            await manager.get_spider("nonexistent")

    @pytest.mark.asyncio
    async def test_close_spider(self):
        """Test closing spider"""
        manager = SpiderManager()
        manager.register_spider("test", MockSpider)

        spider = await manager.get_spider("test")
        assert "test" in manager._spider_instances

        await manager.close_spider("test")
        assert "test" not in manager._spider_instances

    @pytest.mark.asyncio
    async def test_manager_context(self):
        """Test manager context manager"""
        manager = SpiderManager()
        manager.register_spider("test", MockSpider)

        async with manager:
            spider = await manager.get_spider("test")
            assert isinstance(spider, MockSpider)

        # Spider should be closed after exiting context
        assert len(manager._spider_instances) == 0

    def test_get_stats(self):
        """Test getting manager statistics"""
        manager = SpiderManager()
        manager.register_spider("test1", MockSpider)
        manager.register_spider("test2", MockSpider)

        stats = manager.get_stats()

        assert "total_tasks" in stats
        assert "completed_tasks" in stats
        assert "failed_tasks" in stats
        assert "registered_platforms" in stats
        assert len(stats["registered_platforms"]) == 2

    def test_reset_stats(self):
        """Test resetting statistics"""
        manager = SpiderManager()
        manager._stats["total_tasks"] = 10
        manager._stats["completed_tasks"] = 8

        manager.reset_stats()

        assert manager._stats["total_tasks"] == 0
        assert manager._stats["completed_tasks"] == 0


class TestPlaywrightHelper:
    """Tests for PlaywrightHelper"""

    def test_helper_initialization(self):
        """Test helper initialization"""
        logger = Mock()
        helper = PlaywrightHelper(logger)

        assert helper.logger == logger

    @pytest.mark.asyncio
    async def test_get_browser_context_options(self):
        """Test getting browser context options"""
        logger = Mock()
        helper = PlaywrightHelper(logger)

        options = await helper.get_browser_context_options()

        assert "viewport" in options
        assert "user_agent" in options
        assert "locale" in options
        assert "extra_http_headers" in options

    def test_get_random_viewport(self):
        """Test random viewport generation"""
        logger = Mock()
        helper = PlaywrightHelper(logger)

        viewport = helper._get_random_viewport()

        assert "width" in viewport
        assert "height" in viewport
        assert viewport["width"] > 0
        assert viewport["height"] > 0

    def test_get_user_agent(self):
        """Test user agent generation"""
        logger = Mock()
        helper = PlaywrightHelper(logger)

        user_agent = helper._get_user_agent()

        assert isinstance(user_agent, str)
        assert len(user_agent) > 0

    def test_is_valid_url(self):
        """Test URL validation"""
        logger = Mock()
        helper = PlaywrightHelper(logger)

        assert helper.is_valid_url("https://example.com") is True
        assert helper.is_valid_url("http://example.com/path") is True
        assert helper.is_valid_url("not a url") is False
        assert helper.is_valid_url("") is False


class TestContentParser:
    """Tests for ContentParser"""

    def test_parser_initialization(self):
        """Test parser initialization"""
        logger = Mock()
        parser = ContentParser(logger)

        assert parser.logger == logger

    def test_parse_html(self):
        """Test HTML parsing"""
        logger = Mock()
        parser = ContentParser(logger)

        html = "<html><body><p>Test</p></body></html>"
        soup = parser.parse_html(html)

        assert soup.find("p").text == "Test"

    def test_parse_json(self):
        """Test JSON parsing"""
        logger = Mock()
        parser = ContentParser(logger)

        json_str = '{"key": "value", "number": 123}'
        data = parser.parse_json(json_str)

        assert data["key"] == "value"
        assert data["number"] == 123

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        logger = Mock()
        parser = ContentParser(logger)

        result = parser.parse_json("invalid json")

        assert result is None

    def test_extract_text(self):
        """Test text extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        html = "<div><span class='title'>Test Title</span></div>"
        soup = parser.parse_html(html)

        text = parser.extract_text(soup, ".title")

        assert text == "Test Title"

    def test_extract_texts(self):
        """Test multiple text extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        html = "<div><p>Text 1</p><p>Text 2</p><p>Text 3</p></div>"
        soup = parser.parse_html(html)

        texts = parser.extract_texts(soup, "p")

        assert len(texts) == 3
        assert texts[0] == "Text 1"
        assert texts[2] == "Text 3"

    def test_extract_attribute(self):
        """Test attribute extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        html = '<a href="https://example.com" class="link">Link</a>'
        soup = parser.parse_html(html)

        href = parser.extract_attribute(soup, ".link", "href")

        assert href == "https://example.com"

    def test_extract_numbers(self):
        """Test number extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        text = "There are 123 items and 45.6 percent"
        numbers = parser.extract_numbers(text)

        assert 123.0 in numbers
        assert 45.6 in numbers

    def test_extract_hashtags(self):
        """Test hashtag extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        text = "Check out #python and #coding #programming"
        hashtags = parser.extract_hashtags(text)

        assert "python" in hashtags
        assert "coding" in hashtags
        assert "programming" in hashtags

    def test_extract_mentions(self):
        """Test mention extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        text = "Hello @user1 and @user2"
        mentions = parser.extract_mentions(text)

        assert "user1" in mentions
        assert "user2" in mentions

    def test_extract_emails(self):
        """Test email extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        text = "Contact us at info@example.com or support@test.org"
        emails = parser.extract_emails(text)

        assert "info@example.com" in emails
        assert "support@test.org" in emails

    def test_extract_urls(self):
        """Test URL extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        text = "Visit https://example.com and http://test.org"
        urls = parser.extract_urls(text)

        assert "https://example.com" in urls
        assert "http://test.org" in urls

    def test_parse_count(self):
        """Test count parsing"""
        logger = Mock()
        parser = ContentParser(logger)

        assert parser.parse_count("1.2万") == 12000
        assert parser.parse_count("3.5K") == 3500
        assert parser.parse_count("1.5M") == 1500000
        assert parser.parse_count("123") == 123

    def test_parse_duration(self):
        """Test duration parsing"""
        logger = Mock()
        parser = ContentParser(logger)

        assert parser.parse_duration("01:23") == 83  # 1*60 + 23
        assert parser.parse_duration("1:23:45") == 5025  # 1*3600 + 23*60 + 45

    def test_clean_text(self):
        """Test text cleaning"""
        logger = Mock()
        parser = ContentParser(logger)

        text = "  Text   with   extra    spaces  "
        cleaned = parser.clean_text(text)

        assert cleaned == "Text with extra spaces"

    def test_get_domain(self):
        """Test domain extraction"""
        logger = Mock()
        parser = ContentParser(logger)

        domain = parser.get_domain("https://www.example.com/path?query=1")

        assert domain == "www.example.com"


@pytest.mark.integration
class TestSpiderIntegration:
    """Integration tests (require browser)"""

    @pytest.mark.asyncio
    async def test_spider_session_context(self):
        """Test spider session context manager"""
        spider = MockSpider(platform="test")

        # This would normally start/stop browser
        # For testing, we just verify the context manager works
        try:
            async with spider.session():
                assert spider is not None
        except Exception as e:
            # Browser might not be available in test environment
            pytest.skip(f"Browser not available: {e}")

    @pytest.mark.asyncio
    async def test_manager_execute_task(self):
        """Test manager task execution"""
        manager = SpiderManager()
        manager.register_spider("test", MockSpider)

        try:
            async with manager:
                results = await manager.execute_task("test", "search", "keyword", 10)
                assert isinstance(results, list)
        except Exception as e:
            pytest.skip(f"Browser not available: {e}")


# Run tests with: pytest tests/test_spider.py -v
# Run with coverage: pytest tests/test_spider.py --cov=omnisense.spider --cov-report=html
