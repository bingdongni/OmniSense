"""Sohu (搜狐) Spider - News and content platform"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class SohuSpider(BaseSpider):
    """Sohu Spider - Chinese internet media company"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="sohu", headless=headless, proxy=proxy)
        self.base_url = "https://www.sohu.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            self.logger.info(f"Logging in to {self.platform}")
            login_url = f"{self.base_url}/login"
            await self.navigate(login_url)
            await asyncio.sleep(2)
            if self._cookies_file.exists():
                await self._load_cookies()
                self._is_logged_in = True
                return True
            return False
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        try:
            search_url = f"{self.base_url}/search?keyword={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(2)
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            results = []
            for item in soup.select(".news-item, [class*='article']")[:max_results]:
                try:
                    results.append({
                        "title": self.parser.extract_text(item, ".title, h3"),
                        "url": self.parser.extract_attribute(item, "a", "href"),
                        "author": self.parser.extract_text(item, ".author, [class*='source']"),
                        "created_at": self.parser.parse_date(self.parser.extract_text(item, ".time")),
                        "platform": self.platform,
                    })
                except: pass
            return results
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        return {"user_id": user_id, "platform": self.platform}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        try:
            await self.navigate(post_id if post_id.startswith("http") else f"{self.base_url}/{post_id}")
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            return {
                "id": post_id,
                "title": self.parser.extract_text(soup, "h1, .article-title"),
                "content": self.parser.extract_text(soup, ".article-content, [class*='content']"),
                "platform": self.platform,
            }
        except: return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        return []
