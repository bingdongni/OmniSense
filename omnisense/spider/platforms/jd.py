"""JD (京东) Spider - E-commerce platform"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class JDSpider(BaseSpider):
    """JD Spider - Chinese e-commerce company"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="jd", headless=headless, proxy=proxy)
        self.base_url = "https://www.jd.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            login_url = "https://passport.jd.com/new/login.aspx"
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
            search_url = f"https://search.jd.com/Search?keyword={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            results = []
            for item in soup.select(".gl-item, [class*='item']")[:max_results]:
                try:
                    results.append({
                        "id": self.parser.extract_attribute(item, "[data-sku]", "data-sku"),
                        "title": self.parser.extract_text(item, ".p-name em"),
                        "price": self.parser.extract_text(item, ".p-price"),
                        "shop": self.parser.extract_text(item, ".p-shop"),
                        "comments": self.parser.extract_text(item, ".p-commit"),
                        "url": self.parser.extract_attribute(item, ".p-img a", "href"),
                        "image": self.parser.extract_attribute(item, ".p-img img", "src"),
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
            product_url = f"https://item.jd.com/{post_id}.html"
            await self.navigate(product_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            return {
                "id": post_id,
                "title": self.parser.extract_text(soup, ".sku-name"),
                "price": self.parser.extract_text(soup, ".price"),
                "description": self.parser.extract_text(soup, "#detail"),
                "platform": self.platform,
            }
        except: return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        return []
