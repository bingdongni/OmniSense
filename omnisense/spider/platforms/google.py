"""
Google Spider Implementation
完整的Google搜索引擎爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class GoogleSpider(BaseSpider):
    """Google搜索引擎爬虫"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="google", headless=headless, proxy=proxy)
        self.base_url = "https://www.google.com"
        self.api_base_url = "https://www.googleapis.com"

    async def login(self, username: str, password: str) -> bool:
        """Login to Google (optional for search)"""
        try:
            self.logger.info("Logging in to Google...")

            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)
                if await self._page.query_selector('[aria-label="Google Account"]'):
                    self._is_logged_in = True
                    return True

            # Google login is complex with 2FA, returning False
            self.logger.info("Google login requires manual authentication")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Google"""
        try:
            self.logger.info(f"Searching Google for '{keyword}'")

            search_url = f"{self.base_url}/search?q={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            results = []
            result_elements = await self._page.query_selector_all('.g, [data-async-context*="query"]')

            for elem in result_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'search_result'}

                    # Title and link
                    title_elem = await elem.query_selector('h3')
                    link_elem = await elem.query_selector('a[href^="http"], a[href^="/url"]')

                    if title_elem and link_elem:
                        result['title'] = await title_elem.inner_text()
                        href = await link_elem.get_attribute('href')

                        # Clean Google redirect URL
                        if '/url?q=' in href:
                            actual_url = href.split('/url?q=')[-1].split('&')[0]
                            result['url'] = actual_url
                        else:
                            result['url'] = href

                        result['id'] = hashlib.md5(result['url'].encode()).hexdigest()[:16]

                    # Description/snippet
                    desc = await elem.query_selector('[data-sncf], .VwiC3b, .IsZvec')
                    if desc:
                        result['description'] = await desc.inner_text()

                    # Cite (displayed URL)
                    cite = await elem.query_selector('cite')
                    if cite:
                        result['display_url'] = await cite.inner_text()

                    # Date (if available in snippet)
                    date_elem = await elem.query_selector('.LEwnzc.Sqrs4e')
                    if date_elem:
                        result['date'] = await date_elem.inner_text()

                    # Rich snippet data
                    rating = await elem.query_selector('[aria-label*="star"]')
                    if rating:
                        rating_text = await rating.get_attribute('aria-label')
                        result['rating'] = rating_text

                    if result.get('url'):
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"Failed to parse result: {e}")
                    continue

            self.logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get Google user profile (limited)"""
        try:
            # Google doesn't have public user profiles in the traditional sense
            return {'user_id': user_id, 'platform': self.platform}
        except Exception as e:
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get posts from user (not applicable for Google search)"""
        try:
            return []
        except Exception as e:
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed information (search result URL)"""
        try:
            self.logger.info(f"Getting page detail: {post_id}")

            # post_id should be a URL
            await self.navigate(post_id)
            await asyncio.sleep(3)

            post = {'id': post_id, 'url': post_id, 'platform': self.platform}

            # Page title
            title = await self._page.title()
            post['title'] = title

            # Meta description
            meta_desc = await self._page.query_selector('meta[name="description"]')
            if meta_desc:
                post['description'] = await meta_desc.get_attribute('content')

            # Canonical URL
            canonical = await self._page.query_selector('link[rel="canonical"]')
            if canonical:
                post['canonical_url'] = await canonical.get_attribute('href')

            return post

        except Exception as e:
            self.logger.error(f"Failed to get page detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments (not applicable for Google search)"""
        try:
            return []
        except Exception as e:
            return []

    async def search_images(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Google Images"""
        try:
            self.logger.info(f"Searching Google Images for '{keyword}'")

            search_url = f"{self.base_url}/search?q={keyword}&tbm=isch"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            # Scroll to load more images
            for _ in range(max_results // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            results = []
            image_elements = await self._page.query_selector_all('[data-id]')

            for elem in image_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'image'}

                    # Get image URL by clicking
                    await elem.click()
                    await asyncio.sleep(0.5)

                    # Get high-res image
                    img = await self._page.query_selector('[data-iml] img')
                    if img:
                        src = await img.get_attribute('src')
                        if src and src.startswith('http'):
                            result['image_url'] = src
                            result['id'] = hashlib.md5(src.encode()).hexdigest()[:16]

                            # Get source page
                            source_link = await self._page.query_selector('[data-lpage]')
                            if source_link:
                                result['source_url'] = await source_link.get_attribute('href')

                            results.append(result)

                except Exception as e:
                    continue

            self.logger.info(f"Found {len(results)} images")
            return results

        except Exception as e:
            self.logger.error(f"Image search failed: {e}")
            return []

    async def search_news(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Google News"""
        try:
            self.logger.info(f"Searching Google News for '{keyword}'")

            search_url = f"{self.base_url}/search?q={keyword}&tbm=nws"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            results = []
            news_elements = await self._page.query_selector_all('.SoaBEf, [data-hveid]')

            for elem in news_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'news'}

                    # Title and link
                    title_elem = await elem.query_selector('[role="heading"]')
                    link_elem = await elem.query_selector('a')

                    if title_elem and link_elem:
                        result['title'] = await title_elem.inner_text()
                        href = await link_elem.get_attribute('href')
                        result['url'] = href
                        result['id'] = hashlib.md5(href.encode() if href else b'').hexdigest()[:16]

                    # Snippet
                    snippet = await elem.query_selector('.GI74Re')
                    if snippet:
                        result['description'] = await snippet.inner_text()

                    # Source
                    source = await elem.query_selector('.CEMjEf span')
                    if source:
                        result['source'] = await source.inner_text()

                    # Time
                    time_elem = await elem.query_selector('.OSrXXb span')
                    if time_elem:
                        result['published_at'] = await time_elem.inner_text()

                    if result.get('url'):
                        results.append(result)

                except Exception as e:
                    continue

            self.logger.info(f"Found {len(results)} news articles")
            return results

        except Exception as e:
            self.logger.error(f"News search failed: {e}")
            return []


if __name__ == "__main__":
    async def test_google_spider():
        spider = GoogleSpider(headless=False)

        async with spider.session():
            print("Testing Google search...")
            results = await spider.search("artificial intelligence", max_results=5)

            for result in results:
                print(f"\nTitle: {result.get('title')}")
                print(f"URL: {result.get('url')}")
                print(f"Description: {result.get('description', '')[:100]}")
