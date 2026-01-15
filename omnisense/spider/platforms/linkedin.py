"""
LinkedIn Spider Implementation
完整的LinkedIn平台爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class LinkedInSpider(BaseSpider):
    """
    LinkedIn职业社交平台爬虫

    Platform-specific information:
    - Base URL: https://www.linkedin.com
    - Login required: Yes
    - Rate limit: Strict
    - Special features: Posts, jobs, company pages, articles
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="linkedin", headless=headless, proxy=proxy)
        self.base_url = "https://www.linkedin.com"
        self.api_base_url = "https://www.linkedin.com/voyager/api"

    async def login(self, username: str, password: str) -> bool:
        """Login to LinkedIn"""
        try:
            self.logger.info(f"Logging in to LinkedIn as {username}...")

            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(f"{self.base_url}/feed/")
                await asyncio.sleep(2)
                if await self._page.query_selector('[data-control-name="nav.settings"]'):
                    self._is_logged_in = True
                    self.logger.info("Logged in with saved cookies")
                    return True

            await self.navigate(f"{self.base_url}/login")
            await asyncio.sleep(2)

            # Fill email
            username_input = await self._page.wait_for_selector('#username', timeout=10000)
            await username_input.fill(username)

            # Fill password
            password_input = await self._page.wait_for_selector('#password', timeout=10000)
            await password_input.fill(password)

            # Click login
            login_btn = await self._page.wait_for_selector('button[type="submit"]', timeout=10000)
            await login_btn.click()
            await asyncio.sleep(5)

            # Check for success
            if await self._page.query_selector('[data-control-name="nav.settings"]'):
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True

            self.logger.error("Login failed - may require verification")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search LinkedIn posts"""
        try:
            self.logger.info(f"Searching LinkedIn for '{keyword}'")

            search_url = f"{self.base_url}/search/results/content/?keywords={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            # Scroll to load more
            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            post_elements = await self._page.query_selector_all('.feed-shared-update-v2')

            for elem in post_elements[:max_results]:
                try:
                    result = {'platform': self.platform}

                    # Author
                    author = await elem.query_selector('.update-components-actor__name')
                    if author:
                        result['author'] = await author.inner_text()

                    # Content
                    content = await elem.query_selector('.feed-shared-text')
                    if content:
                        result['content'] = await content.inner_text()

                    # Link
                    link = await elem.query_selector('a[href*="/feed/update/"]')
                    if link:
                        href = await link.get_attribute('href')
                        result['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if 'update:urn' in href:
                            result['id'] = href.split('update:')[-1].split('?')[0]

                    # Timestamp
                    time_elem = await elem.query_selector('.update-components-actor__sub-description')
                    if time_elem:
                        result['created_at'] = self.parser.parse_date(await time_elem.inner_text())

                    # Reactions
                    reactions = await elem.query_selector('.social-details-social-counts__reactions-count')
                    if reactions:
                        result['likes'] = self.parser.parse_count(await reactions.inner_text())

                    # Comments
                    comments = await elem.query_selector('.social-details-social-counts__comments')
                    if comments:
                        result['comments'] = self.parser.parse_count(await comments.inner_text())

                    if result.get('content') or result.get('id'):
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Found {len(results)} posts")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get LinkedIn user profile"""
        try:
            self.logger.info(f"Getting profile: {user_id}")

            profile_url = f"{self.base_url}/in/{user_id}/"
            await self.navigate(profile_url)
            await asyncio.sleep(3)

            profile = {'user_id': user_id, 'platform': self.platform}

            # Name
            name = await self._page.query_selector('h1')
            if name:
                profile['username'] = await name.inner_text()

            # Headline
            headline = await self._page.query_selector('.text-body-medium')
            if headline:
                profile['headline'] = await headline.inner_text()

            # Location
            location = await self._page.query_selector('.text-body-small.inline')
            if location:
                profile['location'] = await location.inner_text()

            # Connections
            connections = await self._page.query_selector('.t-black--light span')
            if connections:
                profile['connections'] = self.parser.parse_count(await connections.inner_text())

            # Avatar
            avatar = await self._page.query_selector('img.pv-top-card-profile-picture__image')
            if avatar:
                profile['avatar'] = await avatar.get_attribute('src')

            # About
            about = await self._page.query_selector('.pv-about__summary-text')
            if about:
                profile['bio'] = await about.inner_text()

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get posts from LinkedIn user"""
        try:
            self.logger.info(f"Getting posts from: {user_id}")

            # Navigate to activity page
            activity_url = f"{self.base_url}/in/{user_id}/recent-activity/all/"
            await self.navigate(activity_url)
            await asyncio.sleep(3)

            # Scroll to load posts
            for _ in range(max_posts // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            posts = []
            post_elements = await self._page.query_selector_all('.feed-shared-update-v2')

            for elem in post_elements[:max_posts]:
                try:
                    post = {'user_id': user_id, 'platform': self.platform}

                    # Content
                    content = await elem.query_selector('.feed-shared-text')
                    if content:
                        post['content'] = await content.inner_text()

                    # Link
                    link = await elem.query_selector('a[href*="/feed/update/"]')
                    if link:
                        href = await link.get_attribute('href')
                        post['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if 'update:urn' in href:
                            post['id'] = href.split('update:')[-1].split('?')[0]

                    # Timestamp
                    time_elem = await elem.query_selector('.update-components-actor__sub-description')
                    if time_elem:
                        post['created_at'] = self.parser.parse_date(await time_elem.inner_text())

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} posts")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed LinkedIn post information"""
        try:
            self.logger.info(f"Getting post detail: {post_id}")

            # Construct URL
            post_url = f"{self.base_url}/feed/update/{post_id}/"
            await self.navigate(post_url)
            await asyncio.sleep(3)

            post = {'id': post_id, 'url': post_url, 'platform': self.platform}

            # Author
            author = await self._page.query_selector('.update-components-actor__name')
            if author:
                post['author'] = await author.inner_text()

            # Content
            content = await self._page.query_selector('.feed-shared-text')
            if content:
                post['content'] = await content.inner_text()

            # Reactions
            reactions = await self._page.query_selector('.social-details-social-counts__reactions-count')
            if reactions:
                post['likes'] = self.parser.parse_count(await reactions.inner_text())

            # Comments count
            comments = await self._page.query_selector('.social-details-social-counts__comments')
            if comments:
                post['comments_count'] = self.parser.parse_count(await comments.inner_text())

            # Images
            images = await self._page.query_selector_all('.feed-shared-image__image-link img')
            post['images'] = []
            for img in images:
                src = await img.get_attribute('src')
                if src:
                    post['images'].append({'src': src})

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments for a LinkedIn post"""
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            post_url = f"{self.base_url}/feed/update/{post_id}/"
            if post_id not in self._page.url:
                await self.navigate(post_url)
                await asyncio.sleep(3)

            # Click to load more comments
            for _ in range(max_comments // 10):
                load_more = await self._page.query_selector('button:has-text("Load more comments")')
                if load_more:
                    await load_more.click()
                    await asyncio.sleep(random.uniform(1, 2))

            comments = []
            comment_elements = await self._page.query_selector_all('.comments-comment-item')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Author
                    author = await elem.query_selector('.comments-comment-item__main-content a span')
                    if author:
                        comment['username'] = await author.inner_text()

                    # Content
                    content = await elem.query_selector('.comments-comment-item__main-content span[dir="ltr"]')
                    if content:
                        comment['content'] = await content.inner_text()

                    # Likes
                    likes = await elem.query_selector('.social-details-social-counts__reactions-count')
                    if likes:
                        comment['likes'] = self.parser.parse_count(await likes.inner_text())

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(f"{comment.get('username', '')}{comment['content']}".encode()).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []
