"""Medium Spider - Blogging platform"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class MediumSpider(BaseSpider):
    """Medium Spider - Online publishing platform"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="medium", headless=headless, proxy=proxy)
        self.base_url = "https://medium.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            await self.navigate(self.base_url)
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
            for item in soup.select("article, [class*='post']")[:max_results]:
                try:
                    results.append({
                        "title": self.parser.extract_text(item, "h2, h3"),
                        "excerpt": self.parser.extract_text(item, "[class*='excerpt'], p"),
                        "author": self.parser.extract_text(item, "[class*='author']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "claps": self.parser.parse_count(self.parser.extract_text(item, "[class*='claps']")),
                        "platform": self.platform,
                    })
                except: pass
            return results
        except: return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            profile_url = f"{self.base_url}/@{user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            return {
                "user_id": user_id,
                "name": self.parser.extract_text(soup, "h1, [class*='name']"),
                "bio": self.parser.extract_text(soup, "[class*='bio']"),
                "followers": self.parser.parse_count(self.parser.extract_text(soup, "[class*='followers']")),
                "platform": self.platform,
            }
        except: return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        return {"id": post_id, "platform": self.platform}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        return []
