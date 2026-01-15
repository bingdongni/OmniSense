"""StackOverflow Spider - Developer Q&A platform"""
from typing import Any, Dict, List, Optional
import asyncio
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)

class StackOverflowSpider(BaseSpider):
    """StackOverflow Spider - Programming Q&A community"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="stackoverflow", headless=headless, proxy=proxy)
        self.base_url = "https://stackoverflow.com"

    async def login(self, username: str, password: str) -> bool:
        try:
            login_url = f"{self.base_url}/users/login"
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
            for item in soup.select(".question-summary, [class*='search-result']")[:max_results]:
                try:
                    results.append({
                        "id": self.parser.extract_attribute(item, "[data-questionid]", "data-questionid"),
                        "title": self.parser.extract_text(item, ".question-hyperlink, h3"),
                        "excerpt": self.parser.extract_text(item, ".excerpt"),
                        "author": self.parser.extract_text(item, ".user-details a"),
                        "url": self.parser.extract_attribute(item, ".question-hyperlink", "href"),
                        "votes": self.parser.parse_count(self.parser.extract_text(item, ".vote-count-post")),
                        "answers": self.parser.parse_count(self.parser.extract_text(item, "[class*='answer']")),
                        "views": self.parser.parse_count(self.parser.extract_text(item, ".views")),
                        "tags": [self.parser.extract_text(tag, None) for tag in item.select(".post-tag")],
                        "platform": self.platform,
                    })
                except: pass
            return results
        except: return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            profile_url = f"{self.base_url}/users/{user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(2)
            html = await self._page.content()
            soup = self.parser.parse_html(html)
            return {
                "user_id": user_id,
                "username": self.parser.extract_text(soup, ".user-details h1"),
                "reputation": self.parser.parse_count(self.parser.extract_text(soup, ".reputation-score")),
                "platform": self.platform,
            }
        except: return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        return {"id": post_id, "platform": self.platform}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        return []
