"""
Douban (豆瓣) Spider Implementation
文艺社区爬虫实现
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import random

from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class DoubanSpider(BaseSpider):
    """
    Douban (豆瓣) Spider

    Platform: Chinese social networking service for books, movies, music
    Base URL: https://www.douban.com
    Features: Book reviews, movie ratings, group discussions
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="douban", headless=headless, proxy=proxy)
        self.base_url = "https://www.douban.com"
        self.movie_url = "https://movie.douban.com"
        self.book_url = "https://book.douban.com"

    async def login(self, username: str, password: str) -> bool:
        """
        Login to Douban

        Args:
            username: Email or phone
            password: Password

        Returns:
            True if login successful
        """
        try:
            self.logger.info(f"Logging in to {self.platform} as {username}...")

            login_url = "https://accounts.douban.com/passport/login"
            if not await self.navigate(login_url):
                return False

            await asyncio.sleep(2)

            # Check if already logged in
            if await self._page.query_selector(".nav-user-account"):
                self._is_logged_in = True
                self.logger.info("Already logged in")
                return True

            # Try loading cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self._page.reload()
                await asyncio.sleep(2)

                if await self._page.query_selector(".nav-user-account"):
                    self._is_logged_in = True
                    self.logger.info("Logged in with cookies")
                    return True

            # Switch to password login
            password_tab = await self._page.query_selector("#account")
            if password_tab:
                await password_tab.click()
                await asyncio.sleep(1)

            # Fill in credentials
            if not await self.wait_for_selector("#username"):
                self.logger.error("Login form not found")
                return False

            await self.type_text("#username", username)
            await asyncio.sleep(random.uniform(0.5, 1))
            await self.type_text("#password", password)

            # Click login
            await self.click_element(".btn-account")
            await asyncio.sleep(3)

            if await self._page.query_selector(".nav-user-account"):
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

    async def search(self, keyword: str, max_results: int = 20, search_type: str = "group") -> List[Dict[str, Any]]:
        """
        Search Douban content

        Args:
            keyword: Search keyword
            max_results: Maximum number of results
            search_type: Type (group/movie/book)

        Returns:
            List of result dictionaries
        """
        try:
            self.logger.info(f"Searching for '{keyword}' on {self.platform}")

            search_url = f"{self.base_url}/search?q={keyword}&cat={search_type}"
            if not await self.navigate(search_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            results = []
            items = soup.select(".result, [class*='item']")[:max_results]

            for item in items:
                try:
                    result = {
                        "title": self.parser.extract_text(item, ".title, h3, [class*='title']"),
                        "content": self.parser.extract_text(item, ".content, .abstract, [class*='content']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "author": self.parser.extract_text(item, ".author, [class*='author']"),
                        "rating": self.parser.extract_text(item, ".rating, [class*='rating']"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".time, [class*='time']")
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

            profile_url = f"{self.base_url}/people/{user_id}/"
            if not await self.navigate(profile_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            profile = {
                "user_id": user_id,
                "username": self.parser.extract_text(soup, ".name, [class*='name']"),
                "avatar": self.parser.extract_attribute(soup, ".avatar img", "src"),
                "bio": self.parser.extract_text(soup, ".bio, [class*='signature']"),
                "location": self.parser.extract_text(soup, ".user-info a[href*='loc']"),
                "followers": self.parser.parse_count(
                    self.parser.extract_text(soup, "[class*='follower']")
                ),
                "following": self.parser.parse_count(
                    self.parser.extract_text(soup, "[class*='following']")
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

            posts_url = f"{self.base_url}/people/{user_id}/statuses"
            if not await self.navigate(posts_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=5)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            posts = []
            post_items = soup.select(".status-item, [class*='status']")[:max_posts]

            for item in post_items:
                try:
                    post = {
                        "id": self.parser.extract_attribute(item, "[data-sid]", "data-sid"),
                        "user_id": user_id,
                        "content": self.parser.extract_text(item, ".status-saying, [class*='content']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".created_at, [class*='time']")
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

            post_url = f"{self.base_url}/status/{post_id}/"
            if not await self.navigate(post_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post = {
                "id": post_id,
                "content": self.parser.extract_text(soup, ".status-saying, [class*='content']"),
                "author_id": self.parser.extract_attribute(soup, ".user-face", "href"),
                "author_name": self.parser.extract_text(soup, ".author-name, [class*='author']"),
                "url": post_url,
                "created_at": self.parser.parse_date(
                    self.parser.extract_text(soup, ".created_at, [class*='time']")
                ),
                "likes": self.parser.parse_count(
                    self.parser.extract_text(soup, ".like-count, [class*='like']")
                ),
                "comments": self.parser.parse_count(
                    self.parser.extract_text(soup, ".comment-count, [class*='comment']")
                ),
                "reshares": self.parser.parse_count(
                    self.parser.extract_text(soup, ".reshare-count, [class*='reshare']")
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

            post_url = f"{self.base_url}/status/{post_id}/"
            if not await self.navigate(post_url):
                return []

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            comments = []
            comment_items = soup.select(".comment-item, [class*='comment']")[:max_comments]

            for item in comment_items:
                try:
                    comment = {
                        "id": self.parser.extract_attribute(item, "[data-cid]", "data-cid"),
                        "post_id": post_id,
                        "user_id": self.parser.extract_attribute(item, ".comment-author", "href"),
                        "username": self.parser.extract_text(item, ".comment-author, [class*='author']"),
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

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []

    async def search_movies(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search for movies on Douban"""
        try:
            search_url = f"{self.movie_url}/subject_search?search_text={keyword}"
            if not await self.navigate(search_url):
                return []

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            results = []
            items = soup.select(".item-root")[:max_results]

            for item in items:
                try:
                    result = {
                        "title": self.parser.extract_text(item, ".title"),
                        "rating": self.parser.extract_text(item, ".rating_nums"),
                        "year": self.parser.extract_text(item, ".year"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "poster": self.parser.extract_attribute(item, "img", "src"),
                        "type": "movie",
                        "platform": self.platform,
                    }
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to parse movie: {e}")
                    continue

            return results

        except Exception as e:
            self.logger.error(f"Movie search failed: {e}")
            return []
