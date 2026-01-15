"""
Baidu (百度) Spider Implementation
完整的百度搜索引擎爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class BaiduSpider(BaseSpider):
    """百度搜索引擎爬虫"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="baidu", headless=headless, proxy=proxy)
        self.base_url = "https://www.baidu.com"
        self.api_base_url = "https://www.baidu.com"

    async def login(self, username: str, password: str) -> bool:
        """Login to Baidu (optional for search)"""
        try:
            self.logger.info("Logging in to Baidu...")

            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)
                if await self._page.query_selector('.username'):
                    self._is_logged_in = True
                    return True

            # Baidu login is complex, returning False for now
            self.logger.info("Baidu login not implemented, continuing without login")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Baidu"""
        try:
            self.logger.info(f"Searching Baidu for '{keyword}'")

            search_url = f"{self.base_url}/s?wd={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            results = []
            result_elements = await self._page.query_selector_all('#content_left > div[id]')

            for elem in result_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'search_result'}

                    # Title and link
                    title_elem = await elem.query_selector('h3 a, .c-title a')
                    if title_elem:
                        result['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        result['url'] = href
                        result['id'] = hashlib.md5(href.encode() if href else b'').hexdigest()[:16]

                    # Description/snippet
                    desc = await elem.query_selector('.c-abstract, .c-span-last')
                    if desc:
                        result['description'] = await desc.inner_text()

                    # Source website
                    source = await elem.query_selector('.c-showurl, .c-color-gray')
                    if source:
                        result['source'] = await source.inner_text()

                    # Date (if available)
                    date = await elem.query_selector('.c-color-gray2')
                    if date:
                        date_text = await date.inner_text()
                        if any(char.isdigit() for char in date_text):
                            result['date'] = date_text

                    if result.get('url'):
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
        """Get Baidu user profile (Baidu Tieba user)"""
        try:
            self.logger.info(f"Getting profile: {user_id}")

            # Baidu Tieba user home
            profile_url = f"https://tieba.baidu.com/home/main?un={user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(3)

            profile = {'user_id': user_id, 'platform': self.platform}

            # Username
            name = await self._page.query_selector('.userinfo_username')
            if name:
                profile['username'] = await name.inner_text()

            # Level
            level = await self._page.query_selector('.userinfo_left_rank')
            if level:
                profile['level'] = await level.inner_text()

            # Stats
            stats = await self._page.query_selector_all('.userinfo_right_info li')
            for stat in stats:
                text = await stat.inner_text()
                if '关注' in text:
                    profile['following'] = self.parser.parse_count(text)
                elif '粉丝' in text:
                    profile['followers'] = self.parser.parse_count(text)
                elif '发帖' in text:
                    profile['posts_count'] = self.parser.parse_count(text)

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get posts from Baidu Tieba user"""
        try:
            self.logger.info(f"Getting posts from: {user_id}")

            # User's posts page
            posts_url = f"https://tieba.baidu.com/home/main?un={user_id}&fr=pb"
            await self.navigate(posts_url)
            await asyncio.sleep(3)

            posts = []
            post_elements = await self._page.query_selector_all('.n_topic_item')

            for elem in post_elements[:max_posts]:
                try:
                    post = {'user_id': user_id, 'platform': self.platform}

                    # Title and link
                    title_elem = await elem.query_selector('.n_topic_link')
                    if title_elem:
                        post['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        post['url'] = f"https://tieba.baidu.com{href}" if not href.startswith('http') else href
                        if '/p/' in href:
                            post['id'] = href.split('/p/')[-1].split('?')[0]

                    # Tieba name
                    tieba = await elem.query_selector('.n_forum_link')
                    if tieba:
                        post['tieba'] = await tieba.inner_text()

                    # Time
                    time_elem = await elem.query_selector('.n_date')
                    if time_elem:
                        post['created_at'] = self.parser.parse_date(await time_elem.inner_text())

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} posts")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed Baidu Tieba post information"""
        try:
            self.logger.info(f"Getting post detail: {post_id}")

            post_url = f"https://tieba.baidu.com/p/{post_id}"
            await self.navigate(post_url)
            await asyncio.sleep(3)

            post = {'id': post_id, 'url': post_url, 'platform': self.platform}

            # Title
            title = await self._page.query_selector('.core_title_txt')
            if title:
                post['title'] = (await title.inner_text()).strip()

            # Author
            author = await self._page.query_selector('.p_author_name')
            if author:
                post['author'] = await author.inner_text()

            # Content (first floor)
            content = await self._page.query_selector('.d_post_content')
            if content:
                post['content'] = await content.inner_text()

            # Stats
            reply_count = await self._page.query_selector('.red_text')
            if reply_count:
                post['replies_count'] = self.parser.parse_count(await reply_count.inner_text())

            # Tieba name
            tieba = await self._page.query_selector('.card_title_fname')
            if tieba:
                post['tieba'] = await tieba.inner_text()

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments/replies for a Baidu Tieba post"""
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            post_url = f"https://tieba.baidu.com/p/{post_id}"
            if post_id not in self._page.url:
                await self.navigate(post_url)
                await asyncio.sleep(3)

            # Scroll to load more
            for _ in range(max_comments // 30):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            comments = []
            comment_elements = await self._page.query_selector_all('.l_post')

            for elem in comment_elements[1:max_comments+1]:  # Skip first (original post)
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Author
                    author = await elem.query_selector('.p_author_name')
                    if author:
                        comment['username'] = await author.inner_text()

                    # Content
                    content = await elem.query_selector('.d_post_content')
                    if content:
                        comment['content'] = await content.inner_text()

                    # Floor number
                    floor = await elem.query_selector('.tail-info')
                    if floor:
                        floor_text = await floor.inner_text()
                        if '楼' in floor_text:
                            comment['floor'] = floor_text

                    # Time
                    time_elem = await elem.query_selector('.tail-info')
                    if time_elem:
                        time_text = await time_elem.inner_text()
                        comment['created_at'] = self.parser.parse_date(time_text)

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(f"{comment.get('username', '')}{comment['content']}".encode()).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []
