"""
Tieba (百度贴吧) Spider Implementation
贴吧社区爬虫实现
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import random

from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class TiebaSpider(BaseSpider):
    """
    Tieba (百度贴吧) Spider

    Platform: Baidu's online community forum system
    Base URL: https://tieba.baidu.com
    Features: Topic-based discussions, forums
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="tieba", headless=headless, proxy=proxy)
        self.base_url = "https://tieba.baidu.com"

    async def login(self, username: str, password: str) -> bool:
        """
        Login to Tieba

        Args:
            username: Baidu account username
            password: Password

        Returns:
            True if login successful
        """
        try:
            self.logger.info(f"Logging in to {self.platform} as {username}...")

            login_url = "https://passport.baidu.com/v2/?login"
            if not await self.navigate(login_url):
                return False

            await asyncio.sleep(2)

            # Check if already logged in
            if await self._page.query_selector(".user-name, [class*='user']"):
                self._is_logged_in = True
                self.logger.info("Already logged in")
                return True

            # Try loading cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)

                if await self._page.query_selector(".user-name, [class*='user']"):
                    self._is_logged_in = True
                    self.logger.info("Logged in with cookies")
                    return True

            # Fill in credentials
            if not await self.wait_for_selector("#TANGRAM__PSP_11__userName"):
                self.logger.error("Login form not found")
                return False

            await self.type_text("#TANGRAM__PSP_11__userName", username)
            await asyncio.sleep(random.uniform(0.5, 1))
            await self.type_text("#TANGRAM__PSP_11__password", password)

            # Click login
            await self.click_element("#TANGRAM__PSP_11__submit")
            await asyncio.sleep(3)

            await self.navigate(self.base_url)
            await asyncio.sleep(2)

            if await self._page.query_selector(".user-name, [class*='user']"):
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

            search_url = f"{self.base_url}/f/search/res?ie=utf-8&qw={keyword}"
            if not await self.navigate(search_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            results = []
            items = soup.select(".s_post, [class*='post']")[:max_results]

            for item in items:
                try:
                    result = {
                        "id": self.parser.extract_attribute(item, "[data-tid]", "data-tid"),
                        "title": self.parser.extract_text(item, ".p_title, [class*='title']"),
                        "content": self.parser.extract_text(item, ".p_content, [class*='content']"),
                        "author": self.parser.extract_text(item, ".p_author, [class*='author']"),
                        "author_id": self.parser.extract_attribute(item, ".p_author", "data-uid"),
                        "forum": self.parser.extract_text(item, ".p_forum, [class*='forum']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".p_date, [class*='date']")
                        ),
                        "replies": self.parser.parse_count(
                            self.parser.extract_text(item, ".p_reply, [class*='reply']")
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

            profile_url = f"{self.base_url}/home/main?un={user_id}&ie=utf-8"
            if not await self.navigate(profile_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            profile = {
                "user_id": user_id,
                "username": self.parser.extract_text(soup, ".userinfo_username, [class*='username']"),
                "avatar": self.parser.extract_attribute(soup, ".userinfo_head img", "src"),
                "level": self.parser.extract_text(soup, ".user_level, [class*='level']"),
                "posts_count": self.parser.parse_count(
                    self.parser.extract_text(soup, ".concern_num [class*='post']")
                ),
                "followers": self.parser.parse_count(
                    self.parser.extract_text(soup, ".concern_num [class*='fans']")
                ),
                "following": self.parser.parse_count(
                    self.parser.extract_text(soup, ".concern_num [class*='concern']")
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

            posts_url = f"{self.base_url}/home/main?un={user_id}&ie=utf-8&tab=post"
            if not await self.navigate(posts_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=5)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            posts = []
            post_items = soup.select(".post_item, [class*='post']")[:max_posts]

            for item in post_items:
                try:
                    post = {
                        "id": self.parser.extract_attribute(item, "[data-tid]", "data-tid"),
                        "user_id": user_id,
                        "title": self.parser.extract_text(item, ".post_title, [class*='title']"),
                        "content": self.parser.extract_text(item, ".post_content, [class*='content']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".post_time, [class*='time']")
                        ),
                        "replies": self.parser.parse_count(
                            self.parser.extract_text(item, ".post_reply, [class*='reply']")
                        ),
                        "forum": self.parser.extract_text(item, ".post_forum, [class*='forum']"),
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

            post_url = f"{self.base_url}/p/{post_id}"
            if not await self.navigate(post_url):
                return {}

            await asyncio.sleep(2)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post = {
                "id": post_id,
                "title": self.parser.extract_text(soup, ".core_title_txt, h1, [class*='title']"),
                "content": self.parser.extract_text(soup, ".d_post_content, [class*='content']"),
                "author_id": self.parser.extract_attribute(soup, ".d_author", "data-uid"),
                "author_name": self.parser.extract_text(soup, ".d_name, [class*='author']"),
                "url": post_url,
                "created_at": self.parser.parse_date(
                    self.parser.extract_text(soup, ".post-tail-wrap .tail-info")
                ),
                "replies": self.parser.parse_count(
                    self.parser.extract_text(soup, ".l_reply_num, [class*='reply']")
                ),
                "likes": self.parser.parse_count(
                    self.parser.extract_text(soup, ".like_num, [class*='like']")
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

            post_url = f"{self.base_url}/p/{post_id}"
            if not await self.navigate(post_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            comments = []
            comment_items = soup.select(".l_post, [class*='post']")[1:max_comments+1]  # Skip first (main post)

            for item in comment_items:
                try:
                    comment = {
                        "id": self.parser.extract_attribute(item, "[data-pid]", "data-pid"),
                        "post_id": post_id,
                        "user_id": self.parser.extract_attribute(item, ".d_name", "data-uid"),
                        "username": self.parser.extract_text(item, ".d_name, [class*='author']"),
                        "content": self.parser.extract_text(item, ".d_post_content, [class*='content']"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(item, ".tail-info")
                        ),
                        "floor": self.parser.extract_text(item, ".tail-info .tail-info-text"),
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

    async def get_forum_posts(self, forum_name: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """
        Get posts from a specific forum

        Args:
            forum_name: Forum name
            max_posts: Maximum number of posts

        Returns:
            List of post dictionaries
        """
        try:
            self.logger.info(f"Getting posts from forum: {forum_name}")

            forum_url = f"{self.base_url}/f?kw={forum_name}&ie=utf-8"
            if not await self.navigate(forum_url):
                return []

            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            html = await self._page.content()
            soup = self.parser.parse_html(html)

            posts = []
            post_items = soup.select(".j_thread_list, [class*='thread']")[:max_posts]

            for item in post_items:
                try:
                    post = {
                        "id": self.parser.extract_attribute(item, "[data-tid]", "data-tid"),
                        "title": self.parser.extract_text(item, ".j_th_tit, [class*='title']"),
                        "author": self.parser.extract_text(item, ".tb_icon_author, [class*='author']"),
                        "url": self.parser.extract_attribute(item, "a.j_th_tit", "href"),
                        "replies": self.parser.parse_count(
                            self.parser.extract_text(item, ".threadlist_rep_num, [class*='reply']")
                        ),
                        "forum": forum_name,
                        "platform": self.platform,
                    }

                    posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} posts from forum")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get forum posts: {e}")
            return []
