"""
WeChat Video (微信视频号) Spider Implementation
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class WeChatVideoSpider(BaseSpider):
    """微信视频号爬虫"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="wechat_video", headless=headless, proxy=proxy)
        self.base_url = "https://channels.weixin.qq.com"
        self.api_base_url = "https://channels.weixin.qq.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            self.logger.info("Logging in to WeChat Video...")
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)
                if await self._page.query_selector('[class*="user"]'):
                    self._is_logged_in = True
                    return True
            self.logger.info("Please scan QR code to login")
            await self.navigate(self.base_url)
            await asyncio.sleep(60)
            return False
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        try:
            self.logger.info(f"Searching for '{keyword}'")
            search_url = f"{self.base_url}/search?q={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            results = []
            elements = await self._page.query_selector_all('[class*="item"]')

            for elem in elements[:max_results]:
                try:
                    result = {'platform': self.platform}
                    title = await elem.query_selector('[class*="title"]')
                    if title:
                        result['title'] = await title.inner_text()
                    link = await elem.query_selector('a[href]')
                    if link:
                        href = await link.get_attribute('href')
                        result['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        result['id'] = hashlib.md5(href.encode()).hexdigest()[:16]
                    if result.get('id'):
                        results.append(result)
                except Exception as e:
                    continue

            return results
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            profile_url = f"{self.base_url}/user/{user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(3)
            return {'user_id': user_id, 'platform': self.platform}
        except Exception as e:
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        try:
            posts_url = f"{self.base_url}/user/{user_id}/posts"
            await self.navigate(posts_url)
            await asyncio.sleep(3)
            return []
        except Exception as e:
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        try:
            post_url = f"{self.base_url}/post/{post_id}"
            await self.navigate(post_url)
            await asyncio.sleep(3)
            return {'id': post_id, 'url': post_url, 'platform': self.platform}
        except Exception as e:
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        try:
            return []
        except Exception as e:
            return []
