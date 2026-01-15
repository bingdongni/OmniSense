"""
CNKI (中国知网) Spider Implementation
完整的中国知网爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class CNKISpider(BaseSpider):
    """中国知网爬虫 - China National Knowledge Infrastructure"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="cnki", headless=headless, proxy=proxy)
        self.base_url = "https://www.cnki.net"
        self.kns_url = "https://kns.cnki.net"
        self.api_url = "https://knavi.cnki.net/knavi"

    async def login(self, username: str, password: str) -> bool:
        """Login to CNKI"""
        try:
            self.logger.info("Logging in to CNKI...")

            login_url = f"{self.base_url}/KXReader/Login"
            await self.navigate(login_url)
            await asyncio.sleep(2)

            # Try to fill login form
            username_elem = await self._page.query_selector('input[name="username"], input[placeholder*="用户"]')
            password_elem = await self._page.query_selector('input[name="password"], input[placeholder*="密码"]')

            if username_elem and password_elem:
                await self.type_text('input[name="username"]', username)
                await self.type_text('input[name="password"]', password)
                await self.click_element('button[type="submit"], button.login-btn')
                await asyncio.sleep(3)

                # Check if login successful
                if await self._page.query_selector('.username, [class*="user-name"]'):
                    await self._save_cookies()
                    self._is_logged_in = True
                    self.logger.info("CNKI login successful")
                    return True

            # Try to load existing cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.kns_url)
                await asyncio.sleep(2)
                if not await self._page.query_selector('[class*="login"], [class*="sign-in"]'):
                    self._is_logged_in = True
                    return True

            self.logger.warning("CNKI login failed, continuing without login")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search CNKI"""
        try:
            self.logger.info(f"Searching CNKI for '{keyword}'")

            search_url = f"{self.kns_url}/kns8/DefaultResult/Index?txt={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            results = []
            # Try multiple selector patterns
            result_elements = await self._page.query_selector_all(
                'tr.GridTableContent, .result-item, [data-row-id]'
            )

            if not result_elements:
                result_elements = await self._page.query_selector_all('div[class*="result"]')

            for elem in result_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'paper'}

                    # Title and link
                    title_elem = await elem.query_selector('.name a, td:first-child a, [class*="title"] a')
                    if title_elem:
                        result['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        if href:
                            result['url'] = href if href.startswith('http') else f"{self.kns_url}{href}"
                            result['id'] = hashlib.md5(result['url'].encode()).hexdigest()[:16]

                    # Authors
                    author_elem = await elem.query_selector('.author, td:nth-child(2), [class*="author"]')
                    if author_elem:
                        result['authors'] = await author_elem.inner_text()

                    # Source/Journal
                    source_elem = await elem.query_selector('.source, td:nth-child(3), [class*="source"]')
                    if source_elem:
                        result['source'] = await source_elem.inner_text()

                    # Date
                    date_elem = await elem.query_selector('.date, td:nth-child(4), [class*="date"]')
                    if date_elem:
                        result['date'] = await date_elem.inner_text()

                    # Download count
                    download_elem = await elem.query_selector('[class*="download"]')
                    if download_elem:
                        download_text = await download_elem.inner_text()
                        if download_text.isdigit():
                            result['downloads'] = int(download_text)

                    # Citation count
                    cite_elem = await elem.query_selector('[class*="cite"]')
                    if cite_elem:
                        cite_text = await cite_elem.inner_text()
                        if cite_text.isdigit():
                            result['citations'] = int(cite_text)

                    if result.get('url') or result.get('title'):
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
        """Get CNKI author profile (limited)"""
        try:
            self.logger.info(f"Getting profile: {user_id}")

            # CNKI author search
            search_url = f"{self.kns_url}/kns8/DefaultResult/Index?txt={user_id}&SearchField=AU"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            profile = {'user_id': user_id, 'platform': self.platform, 'type': 'author'}

            # Try to extract author info from search results
            result_count = await self._page.query_selector('[class*="result-count"], .result-count')
            if result_count:
                profile['publication_count'] = await result_count.inner_text()

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get papers from CNKI author"""
        try:
            self.logger.info(f"Getting papers from author: {user_id}")

            # Author search
            search_url = f"{self.kns_url}/kns8/DefaultResult/Index?txt={user_id}&SearchField=AU"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            posts = []
            post_elements = await self._page.query_selector_all('tr.GridTableContent, [data-row-id]')

            for elem in post_elements[:max_posts]:
                try:
                    post = {'author': user_id, 'platform': self.platform, 'type': 'paper'}

                    # Title
                    title_elem = await elem.query_selector('.name a, td:first-child a')
                    if title_elem:
                        post['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        if href:
                            post['url'] = href if href.startswith('http') else f"{self.kns_url}{href}"
                            post['id'] = hashlib.md5(post['url'].encode()).hexdigest()[:16]

                    # Source
                    source_elem = await elem.query_selector('td:nth-child(3), [class*="source"]')
                    if source_elem:
                        post['source'] = await source_elem.inner_text()

                    # Year
                    year_elem = await elem.query_selector('td:nth-child(4), [class*="year"]')
                    if year_elem:
                        year_text = await year_elem.inner_text()
                        if year_text.isdigit():
                            post['year'] = int(year_text)

                    if post.get('title'):
                        posts.append(post)

                except Exception as e:
                    self.logger.debug(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} papers")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed paper information from CNKI"""
        try:
            self.logger.info(f"Getting paper detail: {post_id}")

            # Construct URL if post_id is not already a URL
            if post_id.startswith('http'):
                url = post_id
            else:
                url = f"{self.kns_url}/kcms/detail/{post_id}"

            await self.navigate(url)
            await asyncio.sleep(random.uniform(2, 3))

            post = {'id': post_id, 'url': url, 'platform': self.platform}

            # Title
            title_elem = await self._page.query_selector('.wx-tit, h1, [class*="title"]')
            if title_elem:
                post['title'] = await title_elem.inner_text()

            # Authors
            author_elem = await self._page.query_selector('#author_select, [class*="author-list"]')
            if author_elem:
                post['authors'] = await author_elem.inner_text()

            # Abstract
            abstract_elem = await self._page.query_selector('#ChDivSummary, [class*="abstract"]')
            if abstract_elem:
                post['abstract'] = await abstract_elem.inner_text()

            # Keywords
            keywords_elem = await self._page.query_selector('.keywords, [class*="keyword"]')
            if keywords_elem:
                post['keywords'] = await keywords_elem.inner_text()

            # Source/Journal
            source_elem = await self._page.query_selector('[class*="source"], .journal-name')
            if source_elem:
                post['source'] = await source_elem.inner_text()

            # Year
            year_elem = await self._page.query_selector('[class*="year"], .publish-year')
            if year_elem:
                post['year'] = await year_elem.inner_text()

            # Volume, issue, page
            volume_elem = await self._page.query_selector('[class*="volume"]')
            if volume_elem:
                post['volume'] = await volume_elem.inner_text()

            issue_elem = await self._page.query_selector('[class*="issue"]')
            if issue_elem:
                post['issue'] = await issue_elem.inner_text()

            page_elem = await self._page.query_selector('[class*="page"]')
            if page_elem:
                post['pages'] = await page_elem.inner_text()

            # DOI
            doi_elem = await self._page.query_selector('[class*="doi"]')
            if doi_elem:
                post['doi'] = await doi_elem.inner_text()

            return post

        except Exception as e:
            self.logger.error(f"Failed to get paper detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments/reviews for a paper (limited support)"""
        try:
            self.logger.info(f"Getting comments for paper: {post_id}")

            # CNKI has limited comment functionality
            # Comments are typically accessed through reviews or feedback sections

            if post_id.startswith('http'):
                url = post_id
            else:
                url = f"{self.kns_url}/kcms/detail/{post_id}"

            if post_id not in self._page.url:
                await self.navigate(url)
                await asyncio.sleep(random.uniform(2, 3))

            comments = []
            comment_elements = await self._page.query_selector_all('[class*="comment"], [class*="review"]')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Author
                    author = await elem.query_selector('[class*="author"], .comment-author')
                    if author:
                        comment['username'] = await author.inner_text()

                    # Content
                    content = await elem.query_selector('[class*="content"], .comment-text')
                    if content:
                        comment['content'] = await content.inner_text()

                    # Time
                    time_elem = await elem.query_selector('[class*="time"], .comment-time')
                    if time_elem:
                        comment['created_at'] = await time_elem.inner_text()

                    # Rating
                    rating = await elem.query_selector('[class*="rating"], .comment-rating')
                    if rating:
                        comment['rating'] = await rating.inner_text()

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(f"{comment.get('username', '')}{comment['content']}".encode()).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.debug(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []


if __name__ == "__main__":
    async def test_cnki_spider():
        spider = CNKISpider(headless=False)

        async with spider.session():
            print("Testing CNKI search...")
            results = await spider.search("人工智能", max_results=5)

            for result in results:
                print(f"\nTitle: {result.get('title')}")
                print(f"Authors: {result.get('authors')}")
                print(f"Source: {result.get('source')}")
                print(f"Date: {result.get('date')}")

