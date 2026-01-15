"""
WeChat MP (微信公众号) Spider Implementation
完整的微信公众号平台爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class WeChatMPSpider(BaseSpider):
    """微信公众号爬虫"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="wechat_mp", headless=headless, proxy=proxy)
        self.base_url = "https://mp.weixin.qq.com"
        self.api_base_url = "https://mp.weixin.qq.com/cgi-bin"

    async def login(self, username: str, password: str) -> bool:
        """Login to WeChat MP (requires scan)"""
        try:
            self.logger.info("Logging in to WeChat MP...")

            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(f"{self.base_url}/")
                await asyncio.sleep(2)
                if await self._page.query_selector('.weui-desktop-account__nickname'):
                    self._is_logged_in = True
                    self.logger.info("Logged in with saved cookies")
                    return True

            await self.navigate(f"{self.base_url}/")
            await asyncio.sleep(2)

            self.logger.info("Please scan QR code to login (waiting 60 seconds)...")

            for _ in range(60):
                if await self._page.query_selector('.weui-desktop-account__nickname'):
                    self._is_logged_in = True
                    await self._save_cookies()
                    self.logger.info("Login successful")
                    return True
                await asyncio.sleep(1)

            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search WeChat MP articles"""
        try:
            self.logger.info(f"Searching WeChat MP for '{keyword}'")

            search_url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            results = []
            article_elements = await self._page.query_selector_all('.news-box')

            for elem in article_elements[:max_results]:
                try:
                    result = {'platform': self.platform}

                    # Title and link
                    title_elem = await elem.query_selector('h3 a')
                    if title_elem:
                        result['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        result['url'] = href

                    # Summary
                    summary = await elem.query_selector('.txt-box p')
                    if summary:
                        result['description'] = await summary.inner_text()

                    # Author (account)
                    author = await elem.query_selector('.account a')
                    if author:
                        result['author'] = await author.inner_text()

                    # Date
                    date = await elem.query_selector('.s-p')
                    if date:
                        result['created_at'] = self.parser.parse_date(await date.inner_text())

                    if result.get('url'):
                        result['id'] = hashlib.md5(result['url'].encode()).hexdigest()[:16]
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"Failed to parse article: {e}")
                    continue

            self.logger.info(f"Found {len(results)} articles")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get WeChat MP account profile"""
        try:
            self.logger.info(f"Getting profile: {user_id}")

            search_url = f"https://weixin.sogou.com/weixin?type=1&query={user_id}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            profile = {'user_id': user_id, 'platform': self.platform}

            # Account info from search results
            account_elem = await self._page.query_selector('.wx-rb')
            if account_elem:
                name = await account_elem.query_selector('.txt-box h3 a')
                if name:
                    profile['username'] = await name.inner_text()

                # Description
                desc = await account_elem.query_selector('.txt-box .info')
                if desc:
                    profile['bio'] = await desc.inner_text()

                # WeChat ID
                wechat_id = await account_elem.query_selector('.info label:has-text("微信号")')
                if wechat_id:
                    id_text = await wechat_id.inner_text()
                    profile['wechat_id'] = id_text.replace('微信号：', '').strip()

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get articles from WeChat MP account"""
        try:
            self.logger.info(f"Getting articles from: {user_id}")

            search_url = f"https://weixin.sogou.com/weixin?type=1&query={user_id}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            # Click on account to view articles
            account_link = await self._page.query_selector('.txt-box h3 a')
            if account_link:
                await account_link.click()
                await asyncio.sleep(3)

            posts = []
            article_elements = await self._page.query_selector_all('.news-box')

            for elem in article_elements[:max_posts]:
                try:
                    post = {'user_id': user_id, 'platform': self.platform}

                    title_elem = await elem.query_selector('h3 a')
                    if title_elem:
                        post['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        post['url'] = href
                        post['id'] = hashlib.md5(href.encode()).hexdigest()[:16]

                    date = await elem.query_selector('.s-p')
                    if date:
                        post['created_at'] = self.parser.parse_date(await date.inner_text())

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse article: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} articles")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get articles: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed WeChat MP article information"""
        try:
            self.logger.info(f"Getting article detail: {post_id}")

            # post_id should be the article URL
            await self.navigate(post_id)
            await asyncio.sleep(3)

            post = {'id': post_id, 'url': post_id, 'platform': self.platform}

            # Title
            title = await self._page.query_selector('#activity-name')
            if title:
                post['title'] = await title.inner_text()

            # Author
            author = await self._page.query_selector('#js_name')
            if author:
                post['author'] = await author.inner_text()

            # Content
            content = await self._page.query_selector('#js_content')
            if content:
                post['content'] = await content.inner_text()

            # Publish date
            date = await self._page.query_selector('#publish_time')
            if date:
                post['created_at'] = self.parser.parse_date(await date.inner_text())

            # Read count (if available)
            read_count = await self._page.query_selector('#readNum')
            if read_count:
                post['views'] = self.parser.parse_count(await read_count.inner_text())

            # Like count
            like_count = await self._page.query_selector('#likeNum')
            if like_count:
                post['likes'] = self.parser.parse_count(await like_count.inner_text())

            return post

        except Exception as e:
            self.logger.error(f"Failed to get article detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments for WeChat MP article (limited access)"""
        try:
            self.logger.info(f"Getting comments for article: {post_id}")

            if post_id not in self._page.url:
                await self.navigate(post_id)
                await asyncio.sleep(3)

            # WeChat MP comments are limited and require authorization
            comments = []
            comment_elements = await self._page.query_selector_all('.discuss_item')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Author
                    author = await elem.query_selector('.discuss_author')
                    if author:
                        comment['username'] = await author.inner_text()

                    # Content
                    content = await elem.query_selector('.discuss_message')
                    if content:
                        comment['content'] = await content.inner_text()

                    # Likes
                    likes = await elem.query_selector('.like_num')
                    if likes:
                        comment['likes'] = self.parser.parse_count(await likes.inner_text())

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
