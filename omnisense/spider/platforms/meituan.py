"""Meituan (美团) Spider - Local services platform"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class MeituanSpider(BaseSpider):
    """Meituan Spider - Chinese e-commerce platform for local services"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="meituan", headless=headless, proxy=proxy)
        self.base_url = "https://www.meituan.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            login_url = f"{self.base_url}/account/unitivelogin"
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
            search_url = f"{self.base_url}/s/{keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            results = []
            for item in soup.select(".poi-list-item, [class*='shop']")[:max_results]:
                try:
                    results.append({
                        "name": self.parser.extract_text(item, ".title, [class*='name']"),
                        "category": self.parser.extract_text(item, ".category"),
                        "rating": self.parser.extract_text(item, ".comment-score, [class*='rating']"),
                        "price": self.parser.extract_text(item, ".price, [class*='price']"),
                        "address": self.parser.extract_text(item, ".address"),
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
        try:
            shop_url = post_id if post_id.startswith("http") else f"{self.base_url}/shop/{post_id}"
            await self.navigate(shop_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            return {
                "id": post_id,
                "name": self.parser.extract_text(soup, ".shop-name, h1"),
                "rating": self.parser.extract_text(soup, ".shop-score"),
                "reviews": self.parser.extract_text(soup, ".review-count"),
                "platform": self.platform,
            }
        except: return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        try:
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            comments = []
            for item in soup.select(".comment-item, [class*='review']")[:max_comments]:
                try:
                    comments.append({
                        "username": self.parser.extract_text(item, ".username"),
                        "content": self.parser.extract_text(item, ".comment-content"),
                        "rating": self.parser.extract_text(item, ".rating"),
                        "date": self.parser.parse_date(self.parser.extract_text(item, ".date")),
                        "platform": self.platform,
                    })
                except: pass
            return comments
        except: return []
