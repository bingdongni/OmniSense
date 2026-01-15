"""
arXiv Spider Implementation
完整的arXiv预印本库爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class ArxivSpider(BaseSpider):
    """arXiv爬虫 - Open-access repository for research preprints"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="arxiv", headless=headless, proxy=proxy)
        self.base_url = "https://arxiv.org"
        self.api_url = "https://export.arxiv.org/api/query"

    async def login(self, username: str, password: str) -> bool:
        """
        Login to arXiv (not required)
        arXiv is an open access repository, no login needed
        """
        try:
            self.logger.info("arXiv login not required - open access repository")
            self._is_logged_in = True
            return True
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search arXiv for preprints"""
        try:
            self.logger.info(f"Searching arXiv for '{keyword}'")

            search_url = f"{self.base_url}/search/?query={keyword}&searchtype=all&abstracts=show&order=-announced_date_first&size=200"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            results = []
            result_elements = await self._page.query_selector_all('.arxiv-result, div[data-resultid]')

            if not result_elements:
                # Try alternative selectors
                result_elements = await self._page.query_selector_all('li.arxiv-result')

            for elem in result_elements[:max_results]:
                try:
                    result = {'platform': self.platform, 'type': 'preprint'}

                    # Paper ID and title
                    title_elem = await elem.query_selector('p.title')
                    if title_elem:
                        result['title'] = (await title_elem.inner_text()).strip()

                    # arXiv ID
                    id_link = await elem.query_selector('p.list-title a')
                    if id_link:
                        href = await id_link.get_attribute('href')
                        if href:
                            # Extract arxiv ID from URL
                            arxiv_id = href.split('/abs/')[-1] if '/abs/' in href else href
                            result['arxiv_id'] = arxiv_id
                            result['url'] = f"{self.base_url}/abs/{arxiv_id}"
                            result['id'] = hashlib.md5(arxiv_id.encode()).hexdigest()[:16]

                    # Authors
                    authors_elem = await elem.query_selector('p.authors')
                    if authors_elem:
                        authors_text = await authors_elem.inner_text()
                        # Remove "Authors:" prefix
                        result['authors'] = authors_text.replace('Authors:', '').strip()

                    # Abstract
                    abstract_elem = await elem.query_selector('span.abstract-short')
                    if abstract_elem:
                        result['abstract'] = await abstract_elem.inner_text()

                    # Subject areas/categories
                    subjects_elem = await elem.query_selector('span.primary-subject')
                    if subjects_elem:
                        result['primary_category'] = await subjects_elem.inner_text()

                    # Submission date
                    date_elem = await elem.query_selector('p.is-size-7')
                    if date_elem:
                        date_text = await date_elem.inner_text()
                        result['submitted_date'] = date_text

                    # PDF link
                    pdf_link = await elem.query_selector('a[href*="/pdf/"]')
                    if pdf_link:
                        pdf_href = await pdf_link.get_attribute('href')
                        result['pdf_url'] = pdf_href if pdf_href.startswith('http') else f"{self.base_url}{pdf_href}"

                    if result.get('url') or result.get('title'):
                        results.append(result)

                except Exception as e:
                    self.logger.debug(f"Failed to parse result: {e}")
                    continue

            self.logger.info(f"Found {len(results)} preprints")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get arXiv author profile (limited - arXiv doesn't have user profiles)"""
        try:
            self.logger.info(f"Getting author papers: {user_id}")

            # Search by author name
            search_url = f"{self.base_url}/search/?query=au:{user_id}&searchtype=author&abstracts=show&order=-announced_date_first&size=200"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            profile = {'author_name': user_id, 'platform': self.platform, 'type': 'author'}

            # Try to get result count
            result_count_elem = await self._page.query_selector('[class*="search-info"]')
            if result_count_elem:
                count_text = await result_count_elem.inner_text()
                # Parse result count from text like "1 to 25 of 123 results"
                if 'of' in count_text:
                    try:
                        parts = count_text.split('of')
                        if len(parts) > 1:
                            count_str = parts[1].strip().split()[0]
                            if count_str.isdigit():
                                profile['publication_count'] = int(count_str)
                    except:
                        pass

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get preprints from arXiv author"""
        try:
            self.logger.info(f"Getting preprints from author: {user_id}")

            # Search by author
            search_url = f"{self.base_url}/search/?query=au:{user_id}&searchtype=author&abstracts=show&order=-announced_date_first&size=200"
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            posts = []
            post_elements = await self._page.query_selector_all('.arxiv-result, li.arxiv-result')

            for elem in post_elements[:max_posts]:
                try:
                    post = {'author': user_id, 'platform': self.platform, 'type': 'preprint'}

                    # Title
                    title_elem = await elem.query_selector('p.title')
                    if title_elem:
                        post['title'] = (await title_elem.inner_text()).strip()

                    # arXiv ID and URL
                    id_link = await elem.query_selector('p.list-title a')
                    if id_link:
                        href = await id_link.get_attribute('href')
                        if href:
                            arxiv_id = href.split('/abs/')[-1] if '/abs/' in href else href
                            post['arxiv_id'] = arxiv_id
                            post['url'] = f"{self.base_url}/abs/{arxiv_id}"
                            post['id'] = hashlib.md5(arxiv_id.encode()).hexdigest()[:16]

                    # Abstract
                    abstract_elem = await elem.query_selector('span.abstract-short')
                    if abstract_elem:
                        post['abstract'] = await abstract_elem.inner_text()

                    # Category
                    category_elem = await elem.query_selector('span.primary-subject')
                    if category_elem:
                        post['category'] = await category_elem.inner_text()

                    # Date
                    date_elem = await elem.query_selector('p.is-size-7')
                    if date_elem:
                        post['submitted_date'] = await date_elem.inner_text()

                    if post.get('title'):
                        posts.append(post)

                except Exception as e:
                    self.logger.debug(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} preprints")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed preprint information from arXiv"""
        try:
            self.logger.info(f"Getting preprint detail: {post_id}")

            # post_id should be arxiv ID or URL
            if post_id.startswith('http'):
                url = post_id
                arxiv_id = post_id.split('/abs/')[-1] if '/abs/' in post_id else post_id
            else:
                arxiv_id = post_id.replace("arXiv:", "").strip()
                url = f"{self.base_url}/abs/{arxiv_id}"

            await self.navigate(url)
            await asyncio.sleep(random.uniform(2, 3))

            post = {'id': arxiv_id, 'arxiv_id': arxiv_id, 'url': url, 'platform': self.platform}

            # Title
            title_elem = await self._page.query_selector('.title, h1')
            if title_elem:
                post['title'] = (await title_elem.inner_text()).strip()

            # Authors
            authors_elem = await self._page.query_selector('[class*="authors"]')
            if authors_elem:
                post['authors'] = await authors_elem.inner_text()

            # Abstract
            abstract_elem = await self._page.query_selector('[class*="abstract"]')
            if abstract_elem:
                post['abstract'] = await abstract_elem.inner_text()

            # Primary category
            category_elem = await self._page.query_selector('[class*="primary-subject"]')
            if category_elem:
                post['primary_category'] = await category_elem.inner_text()

            # All categories
            all_cats = await self._page.query_selector('[class*="subjects"]')
            if all_cats:
                post['categories'] = await all_cats.inner_text()

            # Submission date
            date_elem = await self._page.query_selector('[class*="dateline"]')
            if date_elem:
                post['submitted_date'] = await date_elem.inner_text()

            # Comments
            comments_elem = await self._page.query_selector('[class*="comments"]')
            if comments_elem:
                post['comments'] = await comments_elem.inner_text()

            # DOI
            doi_elem = await self._page.query_selector('[class*="doi"]')
            if doi_elem:
                post['doi'] = await doi_elem.inner_text()

            # PDF URL
            pdf_link = await self._page.query_selector('a[href*="/pdf/"]')
            if pdf_link:
                pdf_href = await pdf_link.get_attribute('href')
                post['pdf_url'] = pdf_href if pdf_href.startswith('http') else f"{self.base_url}{pdf_href}"

            # Related papers (if available)
            related_elem = await self._page.query_selector('[class*="related"]')
            if related_elem:
                post['related_papers'] = await related_elem.inner_text()

            return post

        except Exception as e:
            self.logger.error(f"Failed to get preprint detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments/discussions for a preprint (arXiv has no comments)"""
        try:
            self.logger.info(f"Getting comments for preprint: {post_id}")

            # arXiv doesn't have a built-in comment system
            # Comments are typically through external platforms like Twitter, Reddit, or dedicated discussion sites
            self.logger.warning("arXiv doesn't have a native comment system")
            return []

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []


if __name__ == "__main__":
    async def test_arxiv_spider():
        spider = ArxivSpider(headless=False)

        async with spider.session():
            print("Testing arXiv search...")
            results = await spider.search("machine learning", max_results=5)

            for result in results:
                print(f"\nTitle: {result.get('title')}")
                print(f"Authors: {result.get('authors')}")
                print(f"arXiv ID: {result.get('arxiv_id')}")
                print(f"Submitted: {result.get('submitted_date')}")
                print(f"PDF URL: {result.get('pdf_url')}")

