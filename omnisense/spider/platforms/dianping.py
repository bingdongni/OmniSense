"""Dianping (大众点评) Spider - Reviews platform"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class DianpingSpider(BaseSpider):
    """Dianping Spider - Chinese local business reviews platform"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="dianping", headless=headless, proxy=proxy)
        self.base_url = "https://www.dianping.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            login_url = f"{self.base_url}/account/iframeLogin"
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
            search_url = f"{self.base_url}/search/keyword/1/0_{keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            results = []
            for item in soup.select(".shop-list li, [class*='shop']")[:max_results]:
                try:
                    results.append({
                        "name": self.parser.extract_text(item, ".tit, h4"),
                        "category": self.parser.extract_text(item, ".tag-addr .tag"),
                        "rating": self.parser.extract_text(item, ".star, [class*='rating']"),
                        "price": self.parser.extract_text(item, ".mean-price"),
                        "address": self.parser.extract_text(item, ".tag-addr .addr"),
                        "reviews": self.parser.extract_text(item, ".review-num"),
                        "url": self.parser.extract_attribute(item, "a.tit", "href"),
                        "image": self.parser.extract_attribute(item, "img", "src"),
                        "platform": self.platform,
                    })
                except: pass
            return results
        except: return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            profile_url = f"{self.base_url}/member/{user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            return {
                "user_id": user_id,
                "username": self.parser.extract_text(soup, ".username, .name"),
                "avatar": self.parser.extract_attribute(soup, ".avatar img", "src"),
                "reviews": self.parser.parse_count(self.parser.extract_text(soup, ".review-count")),
                "followers": self.parser.parse_count(self.parser.extract_text(soup, ".follow-count")),
                "platform": self.platform,
            }
        except: return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        return {"id": post_id, "platform": self.platform}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        return []
