"""Xueqiu (雪球) Spider - Stock investment community"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class XueqiuSpider(BaseSpider):
    """Xueqiu Spider - Chinese stock trading social platform"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="xueqiu", headless=headless, proxy=proxy)
        self.base_url = "https://xueqiu.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            login_url = f"{self.base_url}/account/login"
            await self.navigate(login_url)
            await asyncio.sleep(2)
            if self._cookies_file.exists():
                await self._load_cookies()
                self._is_logged_in = True
                return True
            return False
        except: return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        try:
            search_url = f"{self.base_url}/k?q={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            results = []
            for item in soup.select(".timeline-item, [class*='status']")[:max_results]:
                try:
                    results.append({
                        "id": self.parser.extract_attribute(item, "[data-id]", "data-id"),
                        "content": self.parser.extract_text(item, ".status-content, [class*='content']"),
                        "author": self.parser.extract_text(item, ".username"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "likes": self.parser.parse_count(self.parser.extract_text(item, ".like-count")),
                        "comments": self.parser.parse_count(self.parser.extract_text(item, ".comment-count")),
                        "platform": self.platform,
                    })
                except: pass
            return results
        except: return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            profile_url = f"{self.base_url}/u/{user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            return {
                "user_id": user_id,
                "username": self.parser.extract_text(soup, ".username"),
                "avatar": self.parser.extract_attribute(soup, ".avatar img", "src"),
                "followers": self.parser.parse_count(self.parser.extract_text(soup, ".followers-count")),
                "platform": self.platform,
            }
        except: return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        return {"id": post_id, "platform": self.platform}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        return []
