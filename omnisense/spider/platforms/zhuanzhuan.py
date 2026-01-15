"""Zhuanzhuan (转转) Spider - Second-hand marketplace"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class ZhuanzhuanSpider(BaseSpider):
    """Zhuanzhuan Spider - Chinese second-hand marketplace"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="zhuanzhuan", headless=headless, proxy=proxy)
        self.base_url = "https://www.zhuanzhuan.com"

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
            search_url = f"{self.base_url}/search?keyword={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            results = []
            for item in soup.select("[class*='item'], [class*='product']")[:max_results]:
                try:
                    results.append({
                        "title": self.parser.extract_text(item, "[class*='title']"),
                        "price": self.parser.extract_text(item, "[class*='price']"),
                        "seller": self.parser.extract_text(item, "[class*='seller']"),
                        "location": self.parser.extract_text(item, "[class*='location']"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "image": self.parser.extract_attribute(item, "img", "src"),
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
