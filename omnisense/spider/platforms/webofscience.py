"""
Web of Science Spider Implementation
完整的Web of Science爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class WebOfScienceSpider(BaseSpider):
    """Web of Science爬虫 - Clarivate Analytics citation database"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="webofscience", headless=headless, proxy=proxy)
        self.base_url = "https://www.webofscience.com"
        self.wos_api_url = "https://api.clarivate.com/api/wos"

    async def login(self, username: str, password: str) -> bool:
        """Login to Web of Science"""
        try:
            self.logger.info("Logging in to Web of Science...")

            login_url = f"{self.base_url}/wos/woscc/basic-search"
            await self.navigate(login_url)
            await asyncio.sleep(2)

            # Look for login button or form
            login_button = await self._page.query_selector('[aria-label*="Sign in"], button.login-btn, a.login')
            if login_button:
                await self.click_element('[aria-label*="Sign in"]')
                await asyncio.sleep(2)

                # Fill in credentials
                username_elem = await self._page.query_selector('input[type="text"], input[name="username"]')
                password_elem = await self._page.query_selector('input[type="password"]')

                if username_elem and password_elem:
                    await self.type_text('input[type="text"]', username)
                    await self.type_text('input[type="password"]', password)
                    await self.click_element('button[type="submit"]')
                    await asyncio.sleep(3)

                    # Check login success
                    if not await self._page.query_selector('[class*="login"]'):
                        await self._save_cookies()
                        self._is_logged_in = True
                        self.logger.info("Web of Science login successful")
                        return True

            # Try to load existing cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)
                if not await self._page.query_selector('[class*="login"]'):
                    self._is_logged_in = True
                    return True

            self.logger.warning("Web of Science login failed, continuing with limited access")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Web of Science"""
        try:
            self.logger.info(f"Searching Web of Science for '{keyword}'")

            search_url = f"{self.base_url}/wos/woscc/basic-search"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # Fill search input
            search_input = await self._page.query_selector('input[placeholder*="search"], input.search-input')
            if search_input:
                await self.type_text('input[placeholder*="search"]', keyword)
                await self._page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(3, 4))

            results = []
            result_elements = await self._page.query_selector_all(
                '.search-results-item, [class*="result-item"], div[data-wos-id]'
            )

            if not result_elements:
                # Try alternative selectors
                result_elements = await self._page.query_selector_all('.title')

            for elem in result_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'paper'}

                    # Title
                    title_elem = await elem.query_selector('.title, h3, [class*="title"]')
                    if title_elem:
                        result['title'] = await title_elem.inner_text()

                    # URL/Link
                    link_elem = await elem.query_selector('a.title, a[href*="doi"], a.full-record')
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        if href:
                            result['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                            result['id'] = hashlib.md5(result['url'].encode()).hexdigest()[:16]

                    # Authors
                    author_elem = await elem.query_selector('.authors, [class*="author"]')
                    if author_elem:
                        result['authors'] = await author_elem.inner_text()

                    # Source/Journal
                    source_elem = await elem.query_selector('.source-title, [class*="source"]')
                    if source_elem:
                        result['source'] = await source_elem.inner_text()

                    # Year
                    year_elem = await elem.query_selector('.year, [class*="year"]')
                    if year_elem:
                        year_text = await year_elem.inner_text()
                        if year_text.isdigit():
                            result['year'] = int(year_text)

                    # Citation count
                    cite_elem = await elem.query_selector('.times-cited-count, [class*="cited"]')
                    if cite_elem:
                        cite_text = await cite_elem.inner_text()
                        cite_nums = ''.join(filter(str.isdigit, cite_text))
                        if cite_nums:
                            result['citations_count'] = int(cite_nums)

                    # DOI
                    doi_elem = await elem.query_selector('.doi, [class*="doi"]')
                    if doi_elem:
                        result['doi'] = await doi_elem.inner_text()

                    # Document type
                    doc_type = await elem.query_selector('[class*="document-type"]')
                    if doc_type:
                        result['document_type'] = await doc_type.inner_text()

                    if result.get('url') or result.get('title'):
                        results.append(result)

                except Exception as e:
                    self.logger.debug(f"Failed to parse result: {e}")
                    continue

            self.logger.info(f"Found {len(results)} papers")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get Web of Science researcher profile"""
        try:
            self.logger.info(f"Getting profile: {user_id}")

            # Search by researcher ID
            search_url = f"{self.base_url}/wos/woscc/basic-search"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            profile = {'user_id': user_id, 'platform': self.platform, 'type': 'researcher'}

            # Try to find researcher info
            if await self._page.query_selector('[class*="researcher"]'):
                name_elem = await self._page.query_selector('[class*="researcher-name"]')
                if name_elem:
                    profile['name'] = await name_elem.inner_text()

                affiliation_elem = await self._page.query_selector('[class*="affiliation"]')
                if affiliation_elem:
                    profile['affiliation'] = await affiliation_elem.inner_text()

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get papers from Web of Science author/researcher"""
        try:
            self.logger.info(f"Getting papers from author: {user_id}")

            search_url = f"{self.base_url}/wos/woscc/basic-search"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # Search for author
            search_input = await self._page.query_selector('input[placeholder*="search"]')
            if search_input:
                await self.type_text('input[placeholder*="search"]', f"AU={user_id}")
                await self._page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(3, 4))

            posts = []
            post_elements = await self._page.query_selector_all('.search-results-item, [data-wos-id]')

            for elem in post_elements[:max_posts]:
                try:
                    post = {'author': user_id, 'platform': self.platform, 'type': 'paper'}

                    # Title
                    title_elem = await elem.query_selector('.title, h3')
                    if title_elem:
                        post['title'] = await title_elem.inner_text()
                        link = await title_elem.query_selector('a')
                        if link:
                            href = await link.get_attribute('href')
                            if href:
                                post['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                                post['id'] = hashlib.md5(post['url'].encode()).hexdigest()[:16]

                    # Publication year
                    year_elem = await elem.query_selector('.year')
                    if year_elem:
                        year_text = await year_elem.inner_text()
                        if year_text.isdigit():
                            post['year'] = int(year_text)

                    # Citation count
                    cite_elem = await elem.query_selector('.times-cited-count')
                    if cite_elem:
                        cite_text = await cite_elem.inner_text()
                        cite_nums = ''.join(filter(str.isdigit, cite_text))
                        if cite_nums:
                            post['citations'] = int(cite_nums)

                    if post.get('title'):
                        posts.append(post)

                except Exception as e:
                    self.logger.debug(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} papers")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get papers: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed paper information from Web of Science"""
        try:
            self.logger.info(f"Getting paper detail: {post_id}")

            # post_id should be a URL
            if post_id.startswith('http'):
                url = post_id
            else:
                url = f"{self.base_url}/wos/woscc/full-record/{post_id}"

            await self.navigate(url)
            await asyncio.sleep(random.uniform(2, 3))

            post = {'id': post_id, 'url': url, 'platform': self.platform}

            # Title
            title_elem = await self._page.query_selector('.title, h1, [class*="title"]')
            if title_elem:
                post['title'] = await title_elem.inner_text()

            # Authors
            author_elem = await self._page.query_selector('[class*="author-list"]')
            if author_elem:
                post['authors'] = await author_elem.inner_text()

            # Abstract
            abstract_elem = await self._page.query_selector('[class*="abstract"]')
            if abstract_elem:
                post['abstract'] = await abstract_elem.inner_text()

            # Source
            source_elem = await self._page.query_selector('.source-title, [class*="source"]')
            if source_elem:
                post['source'] = await source_elem.inner_text()

            # Year
            year_elem = await self._page.query_selector('[class*="year"]')
            if year_elem:
                post['year'] = await year_elem.inner_text()

            # DOI
            doi_elem = await self._page.query_selector('[class*="doi"]')
            if doi_elem:
                post['doi'] = await doi_elem.inner_text()

            # Keywords
            keywords_elem = await self._page.query_selector('[class*="keywords"]')
            if keywords_elem:
                post['keywords'] = await keywords_elem.inner_text()

            # Citation count
            cite_elem = await self._page.query_selector('[class*="times-cited"]')
            if cite_elem:
                post['citations_count'] = await cite_elem.inner_text()

            # Research areas
            areas_elem = await self._page.query_selector('[class*="research-area"]')
            if areas_elem:
                post['research_areas'] = await areas_elem.inner_text()

            return post

        except Exception as e:
            self.logger.error(f"Failed to get paper detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments/reviews for a paper (limited support)"""
        try:
            self.logger.info(f"Getting comments for paper: {post_id}")

            # Web of Science doesn't have traditional comments
            # Comments are typically in cited references or discussions

            if post_id.startswith('http'):
                url = post_id
            else:
                url = f"{self.base_url}/wos/woscc/full-record/{post_id}"

            if post_id not in self._page.url:
                await self.navigate(url)
                await asyncio.sleep(random.uniform(2, 3))

            comments = []
            # Try to find cited references or discussion sections
            ref_elements = await self._page.query_selector_all('[class*="cited"], [class*="reference"]')

            for elem in ref_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Reference text
                    ref_text = await elem.inner_text()
                    if ref_text:
                        comment['content'] = ref_text
                        comment['type'] = 'cited_reference'

                    # Try to extract metadata
                    author = await elem.query_selector('[class*="author"]')
                    if author:
                        comment['author'] = await author.inner_text()

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(comment['content'].encode()).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.debug(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} references")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []


if __name__ == "__main__":
    async def test_webofscience_spider():
        spider = WebOfScienceSpider(headless=False)

        async with spider.session():
            print("Testing Web of Science search...")
            results = await spider.search("machine learning", max_results=5)

            for result in results:
                print(f"\nTitle: {result.get('title')}")
                print(f"Authors: {result.get('authors')}")
                print(f"Year: {result.get('year')}")
                print(f"Citations: {result.get('citations_count', 0)}")

