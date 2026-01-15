"""
Hupu (虎扑) Spider Implementation
体育社区爬虫实现
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import random

from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class HupuSpider(BaseSpider):
    """
    Hupu (虎扑) Spider

    Platform: Chinese sports-focused social networking service
    Base URL: https://www.hupu.com
    Features: Sports news, forum discussions, NBA/CBA content
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="hupu", headless=headless, proxy=proxy)
        self.base_url = "https://www.hupu.com"
        self.bbs_url = "https://bbs.hupu.com"

    async def login(self, username: str, password: str) -> bool:
        """
        Login to Hupu

        Args:
            username: Username or phone
            password: Password

        Returns:
            True if login successful
        """
        try:
            self.logger.info(f"Logging in to {self.platform} as {username}...")

            login_url = f"{self.base_url}/login"
            if not await self.navigate(login_url):
                return False

            await asyncio.sleep(2)

            # Check if already logged in
            if await self._page.query_selector(".user-info, [class*='user']"):
                self._is_logged_in = True
                self.logger.info("Already logged in")
                return True

            # Try loading cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self._page.reload()
                await asyncio.sleep(2)

                if await self._page.query_selector(".user-info, [class*='user']"):
                    self._is_logged_in = True
                    self.logger.info("Logged in with cookies")
                    return True

            # Fill in credentials
            if not await self.wait_for_selector("input[name='username'], input[type='text']"):
                self.logger.error("Login form not found")
                return False

            await self.type_text("input[name='username'], input[type='text']", username)
            await asyncio.sleep(random.uniform(0.5, 1))
            await self.type_text("input[name='password'], input[type='password']", password)

            # Click login
            await self.click_element("button[type='submit'], .login-btn")
            await asyncio.sleep(3)

            if await self._page.query_selector(".user-info, [class*='user']"):
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True
            else:
                self.logger.error("Login failed")
                return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for posts by keyword

        Args:
            keyword: Search keyword
            max_results: Maximum number of results

        Returns:
            List of post dictionaries
        """
        try:
            self.logger.info(f"Searching for '{keyword}' on {self.platform}")

            search_url = f"{self.bbs_url}/search?q={keyword}"
            if not await self.navigate(search_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            results = []
            items = soup.select(".search-result, .thread-item, [class*='item']")[:max_results]

            for item in items:
                try:
                    result = {
                        "id": self.parser.extract_attribute(item, "[data-tid]", "data-tid"),
                        "title": self.parser.extract_text(item, ".thread-title, [class*='title']"),
                        "content": self.parser.extract_text(item, ".thread-excerpt, [class*='excerpt']"),
                        "author": self.parser.extract_text(item, ".author, [class*='author']"),
                        "author_id": self.parser.extract_attribute(item, ".author", "data-uid"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".thread-time, [class*='time']")
                        ),
                        "replies": self.parser.parse_count(
                            self.parser.extract_text(item, ".reply-count, [class*='reply']")
                        ),
                        "views": self.parser.parse_count(
                            self.parser.extract_text(item, ".view-count, [class*='view']")
                        ),
                        "forum": self.parser.extract_text(item, ".forum-name, [class*='forum']"),
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
        """
        Get user profile information

        Args:
            user_id: User ID

        Returns:
            User profile dictionary
        """
        try:
            self.logger.info(f"Getting profile for user: {user_id}")

            profile_url = f"{self.base_url}/space/{user_id}"
            if not await self.navigate(profile_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            profile = {
                "user_id": user_id,
                "username": self.parser.extract_text(soup, ".username, [class*='name']"),
                "avatar": self.parser.extract_attribute(soup, ".avatar img", "src"),
                "level": self.parser.extract_text(soup, ".level, [class*='level']"),
                "reputation": self.parser.parse_count(
                    self.parser.extract_text(soup, ".reputation, [class*='reputation']")
                ),
                "posts_count": self.parser.parse_count(
                    self.parser.extract_text(soup, ".posts-count, [class*='post']")
                ),
                "followers": self.parser.parse_count(
                    self.parser.extract_text(soup, ".followers, [class*='follower']")
                ),
                "registration_date": self.parser.parse_date(
                    self.parser.extract_text(soup, ".reg-date, [class*='reg']")
                ),
                "platform": self.platform,
            }

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """
        Get posts from a user

        Args:
            user_id: User ID
            max_posts: Maximum number of posts

        Returns:
            List of post dictionaries
        """
        try:
            self.logger.info(f"Getting posts for user: {user_id}")

            posts_url = f"{self.base_url}/space/{user_id}/thread"
            if not await self.navigate(posts_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=5)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            posts = []
            post_items = soup.select(".thread-item, [class*='thread']")[:max_posts]

            for item in post_items:
                try:
                    post = {
                        "id": self.parser.extract_attribute(item, "[data-tid]", "data-tid"),
                        "user_id": user_id,
                        "title": self.parser.extract_text(item, ".thread-title, [class*='title']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".thread-time, [class*='time']")
                        ),
                        "replies": self.parser.parse_count(
                            self.parser.extract_text(item, ".reply-count, [class*='reply']")
                        ),
                        "views": self.parser.parse_count(
                            self.parser.extract_text(item, ".view-count, [class*='view']")
                        ),
                        "platform": self.platform,
                    }

                    posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} posts")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get user posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a post

        Args:
            post_id: Post ID

        Returns:
            Post detail dictionary
        """
        try:
            self.logger.info(f"Getting post detail: {post_id}")

            post_url = f"{self.bbs_url}/{post_id}.html"
            if not await self.navigate(post_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post = {
                "id": post_id,
                "title": self.parser.extract_text(soup, ".thread-title, h1, [class*='title']"),
                "content": self.parser.extract_text(soup, ".thread-content, [class*='content']"),
                "author_id": self.parser.extract_attribute(soup, ".author", "data-uid"),
                "author_name": self.parser.extract_text(soup, ".author, [class*='author']"),
                "url": post_url,
                "created_at": self.parser.parse_date(
                    self.parser.extract_text(soup, ".thread-time, [class*='time']")
                ),
                "replies": self.parser.parse_count(
                    self.parser.extract_text(soup, ".reply-count, [class*='reply']")
                ),
                "views": self.parser.parse_count(
                    self.parser.extract_text(soup, ".view-count, [class*='view']")
                ),
                "likes": self.parser.parse_count(
                    self.parser.extract_text(soup, ".like-count, [class*='like']")
                ),
                "images": self.parser.extract_images(soup, base_url=self.base_url),
                "platform": self.platform,
            }

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Get comments for a post

        Args:
            post_id: Post ID
            max_comments: Maximum number of comments

        Returns:
            List of comment dictionaries
        """
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            post_url = f"{self.bbs_url}/{post_id}.html"
            if not await self.navigate(post_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            comments = []
            comment_items = soup.select(".reply-item, [class*='reply']")[:max_comments]

            for item in comment_items:
                try:
                    comment = {
                        "id": self.parser.extract_attribute(item, "[data-pid]", "data-pid"),
                        "post_id": post_id,
                        "user_id": self.parser.extract_attribute(item, ".reply-author", "data-uid"),
                        "username": self.parser.extract_text(item, ".reply-author, [class*='author']"),
                        "content": self.parser.extract_text(item, ".reply-content, [class*='content']"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".reply-time, [class*='time']")
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

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []
