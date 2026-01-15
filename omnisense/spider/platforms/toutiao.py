"""
Toutiao (今日头条) Spider Implementation
新闻资讯平台爬虫实现
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import random

from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class ToutiaoSpider(BaseSpider):
    """
    Toutiao (今日头条) Spider

    Platform: Chinese news and information content platform
    Base URL: https://www.toutiao.com
    Features: Personalized news feed, articles, videos
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="toutiao", headless=headless, proxy=proxy)
        self.base_url = "https://www.toutiao.com"
        self.search_url = f"{self.base_url}/search"

    async def login(self, username: str, password: str) -> bool:
        """Login to Toutiao (usually not required for reading)"""
        try:
            self.logger.info(f"Logging in to {self.platform} as {username}...")

            login_url = f"{self.base_url}/login"
            if not await self.navigate(login_url):
                return False

            await asyncio.sleep(2)

            # Check if already logged in
            if await self._page.query_selector(".user-info, [class*='user']"):
                self._is_logged_in = True
                return True

            # Try cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self._page.reload()
                await asyncio.sleep(2)

                if await self._page.query_selector(".user-info, [class*='user']"):
                    self._is_logged_in = True
                    return True

            self.logger.warning("Manual login may be required")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search for articles by keyword"""
        try:
            self.logger.info(f"Searching for '{keyword}' on {self.platform}")

            search_url = f"{self.search_url}/?keyword={keyword}"
            if not await self.navigate(search_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            results = []
            items = soup.select(".article-item, [class*='article'], [class*='feed']")[:max_results]

            for item in items:
                try:
                    result = {
                        "id": self.parser.extract_attribute(item, "[data-item-id]", "data-item-id"),
                        "title": self.parser.extract_text(item, ".title, [class*='title']"),
                        "abstract": self.parser.extract_text(item, ".abstract, [class*='abstract']"),
                        "author": self.parser.extract_text(item, ".source, [class*='source']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "thumbnail": self.parser.extract_attribute(item, "img", "src"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".time, [class*='time']")
                        ),
                        "comments": self.parser.parse_count(
                            self.parser.extract_text(item, ".comment-count, [class*='comment']")
                        ),
                        "category": self.parser.extract_text(item, ".category, [class*='category']"),
                        "platform": self.platform,
                    }
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to parse result: {e}")
                    continue

            self.logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            profile_url = f"{self.base_url}/c/user/{user_id}"
            if not await self.navigate(profile_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            profile = {
                "user_id": user_id,
                "name": self.parser.extract_text(soup, ".name, [class*='name']"),
                "avatar": self.parser.extract_attribute(soup, ".avatar img", "src"),
                "description": self.parser.extract_text(soup, ".description, [class*='desc']"),
                "followers": self.parser.parse_count(
                    self.parser.extract_text(soup, ".followers, [class*='follower']")
                ),
                "articles": self.parser.parse_count(
                    self.parser.extract_text(soup, ".article-count, [class*='article']")
                ),
                "platform": self.platform,
            }
            return profile

        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get articles from a user"""
        try:
            profile_url = f"{self.base_url}/c/user/{user_id}"
            if not await self.navigate(profile_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=5)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            posts = []
            items = soup.select(".article-item, [class*='article']")[:max_posts]

            for item in items:
                try:
                    post = {
                        "id": self.parser.extract_attribute(item, "[data-item-id]", "data-item-id"),
                        "user_id": user_id,
                        "title": self.parser.extract_text(item, ".title, [class*='title']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".time, [class*='time']")
                        ),
                        "views": self.parser.parse_count(
                            self.parser.extract_text(item, ".view-count, [class*='view']")
                        ),
                        "comments": self.parser.parse_count(
                            self.parser.extract_text(item, ".comment-count, [class*='comment']")
                        ),
                        "platform": self.platform,
                    }
                    posts.append(post)
                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {e}")
                    continue

            return posts

        except Exception as e:
            self.logger.error(f"Failed to get user posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed article information"""
        try:
            post_url = f"{self.base_url}/group/{post_id}/"
            if not await self.navigate(post_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post = {
                "id": post_id,
                "title": self.parser.extract_text(soup, ".article-title, h1"),
                "content": self.parser.extract_text(soup, ".article-content, [class*='content']"),
                "author_name": self.parser.extract_text(soup, ".author-name, [class*='author']"),
                "url": post_url,
                "created_at": self.parser.parse_date(
                    self.parser.extract_text(soup, ".publish-time, [class*='time']")
                ),
                "views": self.parser.parse_count(
                    self.parser.extract_text(soup, ".read-count, [class*='read']")
                ),
                "comments": self.parser.parse_count(
                    self.parser.extract_text(soup, ".comment-count, [class*='comment']")
                ),
                "images": self.parser.extract_images(soup, base_url=self.base_url),
                "platform": self.platform,
            }
            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments for an article"""
        try:
            post_url = f"{self.base_url}/group/{post_id}/"
            if not await self.navigate(post_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            comments = []
            items = soup.select(".comment-item, [class*='comment']")[:max_comments]

            for item in items:
                try:
                    comment = {
                        "id": self.parser.extract_attribute(item, "[data-comment-id]", "data-comment-id"),
                        "post_id": post_id,
                        "username": self.parser.extract_text(item, ".username, [class*='author']"),
                        "content": self.parser.extract_text(item, ".comment-content, [class*='content']"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".comment-time, [class*='time']")
                        ),
                        "likes": self.parser.parse_count(
                            self.parser.extract_text(item, ".like-count, [class*='like']")
                        ),
                        "platform": self.platform,
                    }
                    comments.append(comment)
                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []
