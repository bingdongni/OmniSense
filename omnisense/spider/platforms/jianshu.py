"""Jianshu (简书) Spider - Chinese writing community"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class JianshuSpider(BaseSpider):
    """Jianshu Spider - Chinese online writing platform"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="jianshu", headless=headless, proxy=proxy)
        self.base_url = "https://www.jianshu.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            login_url = f"{self.base_url}/sign_in"
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
            search_url = f"{self.base_url}/search?q={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            results = []
            for item in soup.select(".note-list li, [class*='article']")[:max_results]:
                try:
                    results.append({
                        "title": self.parser.extract_text(item, ".title"),
                        "excerpt": self.parser.extract_text(item, ".abstract"),
                        "author": self.parser.extract_text(item, ".nickname"),
                        "url": self.parser.extract_attribute(item, "a.title", "href"),
                        "likes": self.parser.parse_count(self.parser.extract_text(item, ".likes-count")),
                        "views": self.parser.parse_count(self.parser.extract_text(item, ".views-count")),
                        "platform": self.platform,
                    })
                except: pass
            return results
        except: return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": self.platform}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        return {"id": post_id, "platform": self.platform}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        return []
