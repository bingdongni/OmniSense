"""
Maimai (脉脉) Spider Implementation
职场社交平台爬虫实现
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import random

from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class MaimaiSpider(BaseSpider):
    """
    Maimai (脉脉) Spider

    Platform: Professional social network in China
    Base URL: https://maimai.cn
    Features: Job posts, industry insights, professional networking
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="maimai", headless=headless, proxy=proxy)
        self.base_url = "https://maimai.cn"
        self.api_base_url = "https://open.taou.com"

    async def login(self, username: str, password: str) -> bool:
        """
        Login to Maimai

        Args:
            username: Phone number or email
            password: Password

        Returns:
            True if login successful
        """
        try:
            self.logger.info(f"Logging in to {self.platform} as {username}...")

            # Navigate to login page
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

            # Wait for phone input
            if not await self.wait_for_selector("input[type='tel'], input[name='phone']"):
                self.logger.error("Login form not found")
                return False

            # Fill in credentials
            await self.type_text("input[type='tel'], input[name='phone']", username)
            await asyncio.sleep(random.uniform(0.5, 1))
            await self.type_text("input[type='password'], input[name='password']", password)

            # Click login button
            await self.click_element("button[type='submit'], .login-btn")

            # Wait for login
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

            # Navigate to search
            search_url = f"{self.base_url}/search/feeds?query={keyword}"
            if not await self.navigate(search_url):
                return []

            await asyncio.sleep(2)

            # Scroll to load more
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            # Extract results
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            results = []
            feed_items = soup.select(".feed-item, [class*='feed']")[:max_results]

            for item in feed_items:
                try:
                    result = {
                        "id": self.parser.extract_attribute(item, "[data-id]", "data-id"),
                        "title": self.parser.extract_text(item, ".feed-title, [class*='title']"),
                        "content": self.parser.extract_text(item, ".feed-content, [class*='content']"),
                        "author": self.parser.extract_text(item, ".author-name, [class*='author']"),
                        "author_id": self.parser.extract_attribute(item, ".author", "data-user-id"),
                        "company": self.parser.extract_text(item, ".company, [class*='company']"),
                        "position": self.parser.extract_text(item, ".position, [class*='position']"),
                        "url": self.parser.extract_attribute(item, "a.feed-link", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".feed-time, [class*='time']")
                        ),
                        "likes": self.parser.parse_count(
                            self.parser.extract_text(item, ".like-count, [class*='like']")
                        ),
                        "comments": self.parser.parse_count(
                            self.parser.extract_text(item, ".comment-count, [class*='comment']")
                        ),
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

            profile_url = f"{self.base_url}/contact/{user_id}"
            if not await self.navigate(profile_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            profile = {
                "user_id": user_id,
                "name": self.parser.extract_text(soup, ".user-name, [class*='name']"),
                "company": self.parser.extract_text(soup, ".company, [class*='company']"),
                "position": self.parser.extract_text(soup, ".position, [class*='position']"),
                "avatar": self.parser.extract_attribute(soup, ".avatar img", "src"),
                "bio": self.parser.extract_text(soup, ".bio, [class*='signature']"),
                "followers": self.parser.parse_count(
                    self.parser.extract_text(soup, ".followers-count, [class*='follower']")
                ),
                "following": self.parser.parse_count(
                    self.parser.extract_text(soup, ".following-count, [class*='following']")
                ),
                "posts_count": self.parser.parse_count(
                    self.parser.extract_text(soup, ".posts-count, [class*='post']")
                ),
                "industry": self.parser.extract_text(soup, ".industry, [class*='industry']"),
                "location": self.parser.extract_text(soup, ".location, [class*='location']"),
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

            profile_url = f"{self.base_url}/contact/{user_id}"
            if not await self.navigate(profile_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=5)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            posts = []
            post_items = soup.select(".feed-item, [class*='feed']")[:max_posts]

            for item in post_items:
                try:
                    post = {
                        "id": self.parser.extract_attribute(item, "[data-id]", "data-id"),
                        "user_id": user_id,
                        "content": self.parser.extract_text(item, ".feed-content, [class*='content']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".feed-time, [class*='time']")
                        ),
                        "likes": self.parser.parse_count(
                            self.parser.extract_text(item, ".like-count, [class*='like']")
                        ),
                        "comments": self.parser.parse_count(
                            self.parser.extract_text(item, ".comment-count, [class*='comment']")
                        ),
                        "images": self.parser.extract_images(item, base_url=self.base_url),
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

            post_url = f"{self.base_url}/feed/{post_id}"
            if not await self.navigate(post_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post = {
                "id": post_id,
                "content": self.parser.extract_text(soup, ".feed-content, [class*='content']"),
                "author_id": self.parser.extract_attribute(soup, ".author", "data-user-id"),
                "author_name": self.parser.extract_text(soup, ".author-name, [class*='author']"),
                "company": self.parser.extract_text(soup, ".company, [class*='company']"),
                "position": self.parser.extract_text(soup, ".position, [class*='position']"),
                "url": post_url,
                "created_at": self.parser.parse_date(
                    self.parser.extract_text(soup, ".feed-time, [class*='time']")
                ),
                "likes": self.parser.parse_count(
                    self.parser.extract_text(soup, ".like-count, [class*='like']")
                ),
                "comments": self.parser.parse_count(
                    self.parser.extract_text(soup, ".comment-count, [class*='comment']")
                ),
                "shares": self.parser.parse_count(
                    self.parser.extract_text(soup, ".share-count, [class*='share']")
                ),
                "images": self.parser.extract_images(soup, base_url=self.base_url),
                "hashtags": self.parser.extract_hashtags(
                    self.parser.extract_text(soup, ".feed-content")
                ),
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

            post_url = f"{self.base_url}/feed/{post_id}"
            if not await self.navigate(post_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            comments = []
            comment_items = soup.select(".comment-item, [class*='comment']")[:max_comments]

            for item in comment_items:
                try:
                    comment = {
                        "id": self.parser.extract_attribute(item, "[data-id]", "data-id"),
                        "post_id": post_id,
                        "user_id": self.parser.extract_attribute(item, ".comment-author", "data-user-id"),
                        "username": self.parser.extract_text(item, ".comment-author, [class*='author']"),
                        "content": self.parser.extract_text(item, ".comment-content, [class*='content']"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".comment-time, [class*='time']")
                        ),
                        "likes": self.parser.parse_count(
                            self.parser.extract_text(item, ".comment-likes, [class*='like']")
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
