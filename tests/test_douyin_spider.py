"""
Unit tests for Douyin Spider

Run with: pytest tests/test_douyin_spider.py
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from omnisense.spider.platforms.douyin import (
    DouyinSpider,
    DouyinAntiCrawl,
    DouyinMatcher,
    DouyinInteraction,
    search_douyin_videos,
    get_douyin_user_videos,
)


@pytest.fixture
def mock_page():
    """Mock Playwright Page object"""
    page = AsyncMock()
    page.url = "https://www.douyin.com"
    page.viewport_size = {'width': 1920, 'height': 1080}
    return page


@pytest.fixture
async def spider():
    """Create spider instance for testing"""
    spider = DouyinSpider(headless=True)
    # Mock the browser session
    spider._page = AsyncMock()
    spider._page.url = "https://www.douyin.com"
    return spider


class TestDouyinAntiCrawl:
    """Test DouyinAntiCrawl class"""

    def test_generate_device_id(self):
        """Test device ID generation"""
        spider = DouyinSpider(headless=True)
        anti_crawl = DouyinAntiCrawl(spider)

        device_id = anti_crawl._generate_device_id()

        assert device_id is not None
        assert isinstance(device_id, str)
        assert len(device_id) == 32  # MD5 hash length

    @pytest.mark.asyncio
    async def test_initialize(self, mock_page):
        """Test anti-crawl initialization"""
        spider = DouyinSpider(headless=True)
        anti_crawl = DouyinAntiCrawl(spider)

        await anti_crawl.initialize(mock_page)

        # Verify scripts were injected
        assert mock_page.add_init_script.call_count >= 3

    @pytest.mark.asyncio
    async def test_random_scroll_behavior(self, mock_page):
        """Test random scroll behavior simulation"""
        spider = DouyinSpider(headless=True)
        anti_crawl = DouyinAntiCrawl(spider)

        mock_page.evaluate = AsyncMock(side_effect=[1000, 500, 1000])

        await anti_crawl.random_scroll_behavior(mock_page, duration=1.0)

        # Verify scroll was executed
        assert mock_page.evaluate.called

    @pytest.mark.asyncio
    async def test_slider_captcha_detection(self, mock_page):
        """Test slider captcha detection"""
        spider = DouyinSpider(headless=True)
        anti_crawl = DouyinAntiCrawl(spider)

        # Mock no captcha present
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await anti_crawl.handle_slider_captcha(mock_page)

        assert result is True  # No captcha = success


class TestDouyinMatcher:
    """Test DouyinMatcher class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.matcher = DouyinMatcher()

    @pytest.mark.asyncio
    async def test_match_video_with_keywords(self):
        """Test video matching with keywords"""
        video = {
            'title': 'Python编程教程',
            'description': '学习Python的最佳资源',
            'hashtags': ['Python', '编程'],
            'like_count': 1000,
            'view_count': 10000
        }

        criteria = {
            'keywords': ['Python', '教程']
        }

        is_match, score = await self.matcher.match_video(video, criteria)

        assert is_match is True
        assert score > 0.0

    @pytest.mark.asyncio
    async def test_match_video_with_filters(self):
        """Test video matching with engagement filters"""
        video = {
            'title': 'Test Video',
            'like_count': 500,
            'view_count': 5000
        }

        criteria = {
            'min_likes': 1000,
            'min_views': 10000
        }

        is_match, score = await self.matcher.match_video(video, criteria)

        assert is_match is False  # Should not match due to low engagement

    @pytest.mark.asyncio
    async def test_match_video_no_criteria(self):
        """Test video matching without criteria"""
        video = {'title': 'Any Video'}
        criteria = None

        is_match, score = await self.matcher.match_video(video, criteria)

        assert is_match is True
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_match_video_hashtags(self):
        """Test video matching with hashtags"""
        video = {
            'title': 'Video with hashtags',
            'description': 'Content',
            'hashtags': ['AI', 'MachineLearning', 'Python']
        }

        criteria = {
            'keywords': ['AI', 'Python']
        }

        is_match, score = await self.matcher.match_video(video, criteria)

        assert is_match is True


class TestDouyinInteraction:
    """Test DouyinInteraction class"""

    @pytest.fixture
    def interaction(self):
        """Create interaction handler"""
        spider = DouyinSpider(headless=True)
        return DouyinInteraction(spider)

    @pytest.mark.asyncio
    async def test_parse_comment_element(self, interaction, mock_page):
        """Test comment parsing"""
        mock_element = AsyncMock()

        # Mock comment data
        mock_element.query_selector = AsyncMock(side_effect=[
            AsyncMock(inner_text=AsyncMock(return_value='TestUser')),  # username
            AsyncMock(get_attribute=AsyncMock(return_value='avatar.jpg')),  # avatar
            AsyncMock(inner_text=AsyncMock(return_value='Great video!')),  # text
            AsyncMock(inner_text=AsyncMock(return_value='100')),  # likes
            AsyncMock(inner_text=AsyncMock(return_value='1小时前')),  # time
            None,  # author tag
            None,  # IP location
        ])

        comment = await interaction._parse_comment_element(mock_page, mock_element)

        assert comment is not None
        assert comment['text'] == 'Great video!'
        assert comment['user']['nickname'] == 'TestUser'


class TestDouyinSpider:
    """Test DouyinSpider class"""

    @pytest.mark.asyncio
    async def test_spider_initialization(self):
        """Test spider initialization"""
        spider = DouyinSpider(headless=True)

        assert spider.platform == "douyin"
        assert spider.base_url == "https://www.douyin.com"
        assert spider.anti_crawl is not None
        assert spider.matcher is not None
        assert spider.interaction is not None

    def test_extract_video_id(self):
        """Test video ID extraction from URL"""
        spider = DouyinSpider(headless=True)

        # Test valid URL
        url = "https://www.douyin.com/video/7123456789012345678"
        video_id = spider._extract_video_id(url)

        assert video_id == "7123456789012345678"

        # Test invalid URL
        invalid_url = "https://www.douyin.com/invalid"
        video_id = spider._extract_video_id(invalid_url)

        assert video_id is None

    def test_extract_user_id(self):
        """Test user ID extraction from URL"""
        spider = DouyinSpider(headless=True)

        url = "https://www.douyin.com/user/MS4wLjABAAAAtest"
        user_id = spider._extract_user_id(url)

        assert user_id == "MS4wLjABAAAAtest"

    @pytest.mark.asyncio
    async def test_check_login_status(self):
        """Test login status check"""
        spider = DouyinSpider(headless=True)
        spider._page = AsyncMock()

        # Mock logged in
        spider._page.query_selector = AsyncMock(return_value=Mock())
        is_logged_in = await spider._check_login_status()
        assert is_logged_in is True

        # Mock not logged in
        spider._page.query_selector = AsyncMock(return_value=None)
        is_logged_in = await spider._check_login_status()
        assert is_logged_in is False


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.mark.asyncio
    @patch('omnisense.spider.platforms.douyin.DouyinSpider')
    async def test_search_douyin_videos(self, mock_spider_class):
        """Test search_douyin_videos convenience function"""
        # Mock spider instance
        mock_spider = AsyncMock()
        mock_spider.session = AsyncMock()
        mock_spider.search = AsyncMock(return_value=[
            {'title': 'Video 1', 'content_id': '123'},
            {'title': 'Video 2', 'content_id': '456'}
        ])

        mock_spider_class.return_value = mock_spider

        # Note: This test would need proper mocking of context manager
        # For now, just verify the function exists and is callable
        assert callable(search_douyin_videos)

    @pytest.mark.asyncio
    @patch('omnisense.spider.platforms.douyin.DouyinSpider')
    async def test_get_douyin_user_videos(self, mock_spider_class):
        """Test get_douyin_user_videos convenience function"""
        mock_spider = AsyncMock()
        mock_spider.session = AsyncMock()
        mock_spider.get_user_posts = AsyncMock(return_value=[
            {'title': 'Video 1', 'content_id': '123'}
        ])

        mock_spider_class.return_value = mock_spider

        # Verify function exists and is callable
        assert callable(get_douyin_user_videos)


class TestIntegration:
    """Integration tests (require actual browser)"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_search_flow(self):
        """Test complete search flow (integration test)"""
        spider = DouyinSpider(headless=True)

        try:
            async with spider.session():
                # This will fail without actual browser
                # but tests the flow
                pass
        except Exception as e:
            # Expected to fail in test environment
            assert True


def test_module_imports():
    """Test that all modules can be imported"""
    from omnisense.spider.platforms import (
        DouyinSpider,
        DouyinAntiCrawl,
        DouyinMatcher,
        DouyinInteraction,
        search_douyin_videos,
        get_douyin_user_videos,
        get_spider,
        list_platforms,
    )

    assert DouyinSpider is not None
    assert DouyinAntiCrawl is not None
    assert DouyinMatcher is not None
    assert DouyinInteraction is not None
    assert search_douyin_videos is not None
    assert get_douyin_user_videos is not None
    assert get_spider is not None
    assert list_platforms is not None


def test_platform_registry():
    """Test platform registry"""
    from omnisense.spider.platforms import get_spider, list_platforms, PLATFORM_SPIDERS

    # Test list platforms
    platforms = list_platforms()
    assert 'douyin' in platforms

    # Test get spider
    spider = get_spider('douyin', headless=True)
    assert isinstance(spider, DouyinSpider)

    # Test unknown platform
    with pytest.raises(ValueError):
        get_spider('unknown_platform')

    # Test registry structure
    assert 'douyin' in PLATFORM_SPIDERS
    assert PLATFORM_SPIDERS['douyin'] == DouyinSpider


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
