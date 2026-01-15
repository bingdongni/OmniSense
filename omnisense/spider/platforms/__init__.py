"""
Platform-specific spiders for OmniSense

This package contains specialized spider implementations for each supported platform.
Each spider follows the 4-layer architecture:
1. Spider Layer: Data collection
2. Anti-Crawl Layer: Anti-detection measures
3. Matcher Layer: Content matching and filtering
4. Interaction Layer: User interaction handling

Available platforms:
- douyin: Douyin (抖音) short video platform
"""

from omnisense.spider.platforms.douyin import (
    DouyinSpider,
    DouyinAntiCrawl,
    DouyinMatcher,
    DouyinInteraction,
    search_douyin_videos,
    get_douyin_user_videos,
)

__all__ = [
    # Douyin
    "DouyinSpider",
    "DouyinAntiCrawl",
    "DouyinMatcher",
    "DouyinInteraction",
    "search_douyin_videos",
    "get_douyin_user_videos",
]

# Platform registry for dynamic loading
PLATFORM_SPIDERS = {
    "douyin": DouyinSpider,
    # Add more platforms here as they are implemented
    # "xiaohongshu": XiaohongshuSpider,
    # "weibo": WeiboSpider,
    # etc.
}


def get_spider(platform: str, **kwargs):
    """
    Get spider instance for a platform

    Args:
        platform: Platform name
        **kwargs: Spider initialization parameters

    Returns:
        Spider instance

    Raises:
        ValueError: If platform is not supported
    """
    if platform not in PLATFORM_SPIDERS:
        raise ValueError(
            f"Platform '{platform}' not supported. "
            f"Available platforms: {', '.join(PLATFORM_SPIDERS.keys())}"
        )

    spider_class = PLATFORM_SPIDERS[platform]
    return spider_class(**kwargs)


def list_platforms() -> list:
    """
    List all available platforms

    Returns:
        List of platform names
    """
    return list(PLATFORM_SPIDERS.keys())
