"""
Quark (夸克) Spider Implementation
完整的夸克搜索引擎爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class QuarkSpider(BaseSpider):
    """夸克搜索引擎爬虫"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="quark", headless=headless, proxy=proxy)
        self.base_url = "https://quark.sm.cn"
        self.api_base_url = "https://quark.sm.cn/api"

    async def login(self, username: str, password: str) -> bool:
        """Login to Quark (optional for search)"""
        try:
            self.logger.info("Logging in to Quark...")

            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)
                # Check if logged in by looking for user profile element
                user_elem = await self._page.query_selector('[class*="user"], [class*="profile"]')
                if user_elem:
                    self._is_logged_in = True
                    return True

            # Quark doesn't require login for search
            self.logger.info("Quark search doesn't require login")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Quark"""
        try:
            self.logger.info(f"Searching Quark for '{keyword}'")

            search_url = f"{self.base_url}/s?q={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            results = []
            # Quark uses dynamic selectors, try multiple patterns
            result_elements = await self._page.query_selector_all(
                '.result-item, [class*="search-item"], [class*="result-box"]'
            )

            if not result_elements:
                # Try alternative selectors
                result_elements = await self._page.query_selector_all(
                    'div[data-resultid], li[class*="result"]'
                )

            for elem in result_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'search_result'}

                    # Title and link
                    title_elem = await elem.query_selector('h3, .title, [class*="title"]')
                    link_elem = await elem.query_selector('a[href^="http"], a[href*="quark"]')

                    if title_elem and link_elem:
                        result['title'] = await title_elem.inner_text()
                        href = await link_elem.get_attribute('href')

                        if href:
                            result['url'] = href
                            result['id'] = hashlib.md5(href.encode()).hexdigest()[:16]

                    # Description/snippet
                    desc = await elem.query_selector('.snippet, [class*="desc"], .result-desc')
                    if desc:
                        result['description'] = await desc.inner_text()

                    # Domain
                    domain = await elem.query_selector('.domain, [class*="domain"]')
                    if domain:
                        result['domain'] = await domain.inner_text()

                    # Date if available
                    date_elem = await elem.query_selector('[class*="date"], .time')
                    if date_elem:
                        result['date'] = await date_elem.inner_text()

                    if result.get('url'):
                        results.append(result)

                except Exception as e:
                    self.logger.debug(f"Failed to parse result: {e}")
                    continue

            self.logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get Quark user profile (limited)"""
        try:
            # Quark doesn't have traditional user profiles
            return {'user_id': user_id, 'platform': self.platform}
        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get posts from user (not applicable for Quark search)"""
        try:
            self.logger.warning("Quark search doesn't support user posts")
            return []
        except Exception as e:
            self.logger.error(f"Failed to get user posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed information about a search result"""
        try:
            self.logger.info(f"Getting page detail: {post_id}")

            # post_id should be a URL
            await self.navigate(post_id)
            await asyncio.sleep(random.uniform(2, 3))

            post = {'id': post_id, 'url': post_id, 'platform': self.platform}

            # Page title
            title = await self._page.title()
            post['title'] = title

            # Meta description
            meta_desc = await self._page.query_selector('meta[name="description"]')
            if meta_desc:
                post['description'] = await meta_desc.get_attribute('content')

            # Meta keywords
            meta_keywords = await self._page.query_selector('meta[name="keywords"]')
            if meta_keywords:
                post['keywords'] = await meta_keywords.get_attribute('content')

            # Canonical URL
            canonical = await self._page.query_selector('link[rel="canonical"]')
            if canonical:
                post['canonical_url'] = await canonical.get_attribute('href')

            return post

        except Exception as e:
            self.logger.error(f"Failed to get page detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments (not applicable for Quark search)"""
        try:
            self.logger.warning("Quark search doesn't have comments")
            return []
        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []


if __name__ == "__main__":
    async def test_quark_spider():
        spider = QuarkSpider(headless=False)

        async with spider.session():
            print("Testing Quark search...")
            results = await spider.search("人工智能", max_results=5)

            for result in results:
                print(f"\nTitle: {result.get('title')}")
                print(f"URL: {result.get('url')}")
                print(f"Description: {result.get('description', '')[:100]}")
