"""
Reddit Spider Implementation
完整的Reddit平台爬虫实现
"""

import asyncio
import hashlib
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from omnisense.spider.base import BaseSpider


class RedditSpider(BaseSpider):
    """Reddit社区平台爬虫"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="reddit", headless=headless, proxy=proxy)
        self.base_url = "https://www.reddit.com"
        self.api_base_url = "https://oauth.reddit.com"

    async def login(self, username: str, password: str) -> bool:
        """Login to Reddit"""
        try:
            self.logger.info(f"Logging in to Reddit as {username}...")

            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)
                if await self._page.query_selector('[id="USER_DROPDOWN_ID"]'):
                    self._is_logged_in = True
                    self.logger.info("Logged in with saved cookies")
                    return True

            await self.navigate(f"{self.base_url}/login")
            await asyncio.sleep(2)

            username_input = await self._page.wait_for_selector('#loginUsername', timeout=10000)
            await username_input.fill(username)

            password_input = await self._page.wait_for_selector('#loginPassword', timeout=10000)
            await password_input.fill(password)

            login_btn = await self._page.wait_for_selector('button[type="submit"]', timeout=10000)
            await login_btn.click()
            await asyncio.sleep(5)

            if await self._page.query_selector('[id="USER_DROPDOWN_ID"]'):
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Reddit posts"""
        try:
            self.logger.info(f"Searching Reddit for '{keyword}'")

            search_url = f"{self.base_url}/search/?q={keyword}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            post_elements = await self._page.query_selector_all('[data-testid="post-container"]')

            for elem in post_elements[:max_results]:
                try:
                    result = {'platform': self.platform}

                    # Title
                    title = await elem.query_selector('h3')
                    if title:
                        result['title'] = await title.inner_text()

                    # Link
                    link = await elem.query_selector('a[data-click-id="body"]')
                    if link:
                        href = await link.get_attribute('href')
                        result['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if '/comments/' in href:
                            result['id'] = href.split('/comments/')[-1].split('/')[0]

                    # Author and subreddit
                    author = await elem.query_selector('[data-testid="post_author_link"]')
                    if author:
                        result['author'] = await author.inner_text()

                    subreddit = await elem.query_selector('[data-click-id="subreddit"]')
                    if subreddit:
                        result['subreddit'] = await subreddit.inner_text()

                    # Votes
                    votes = await elem.query_selector('[aria-label*="votes"]')
                    if votes:
                        vote_text = await votes.inner_text()
                        result['votes'] = self.parser.parse_count(vote_text)

                    # Comments count
                    comments = await elem.query_selector('[data-click-id="comments"]')
                    if comments:
                        comment_text = await comments.inner_text()
                        result['comments_count'] = self.parser.parse_count(comment_text)

                    if result.get('id'):
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
        """Get Reddit user profile"""
        try:
            self.logger.info(f"Getting profile: {user_id}")

            profile_url = f"{self.base_url}/user/{user_id}/"
            await self.navigate(profile_url)
            await asyncio.sleep(3)

            profile = {'user_id': user_id, 'platform': self.platform}

            # Username
            name = await self._page.query_selector('h1')
            if name:
                profile['username'] = await name.inner_text()

            # Karma
            karma = await self._page.query_selector('[id*="profile-hover-card"] span')
            if karma:
                profile['karma'] = self.parser.parse_count(await karma.inner_text())

            # Avatar
            avatar = await self._page.query_selector('img[alt="User Avatar"]')
            if avatar:
                profile['avatar'] = await avatar.get_attribute('src')

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get posts from Reddit user"""
        try:
            self.logger.info(f"Getting posts from: {user_id}")

            profile_url = f"{self.base_url}/user/{user_id}/submitted/"
            await self.navigate(profile_url)
            await asyncio.sleep(3)

            for _ in range(max_posts // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            posts = []
            post_elements = await self._page.query_selector_all('[data-testid="post-container"]')

            for elem in post_elements[:max_posts]:
                try:
                    post = {'user_id': user_id, 'platform': self.platform}

                    title = await elem.query_selector('h3')
                    if title:
                        post['title'] = await title.inner_text()

                    link = await elem.query_selector('a[data-click-id="body"]')
                    if link:
                        href = await link.get_attribute('href')
                        post['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if '/comments/' in href:
                            post['id'] = href.split('/comments/')[-1].split('/')[0]

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
        """Get detailed Reddit post information"""
        try:
            self.logger.info(f"Getting post detail: {post_id}")

            # Reddit post URLs need subreddit info, try to find it
            post_url = f"{self.base_url}/comments/{post_id}/"
            await self.navigate(post_url)
            await asyncio.sleep(3)

            post = {'id': post_id, 'url': post_url, 'platform': self.platform}

            # Title
            title = await self._page.query_selector('h1')
            if title:
                post['title'] = await title.inner_text()

            # Content
            content = await self._page.query_selector('[data-test-id="post-content"]')
            if content:
                post['content'] = await content.inner_text()

            # Author
            author = await self._page.query_selector('[data-testid="post_author_link"]')
            if author:
                post['author'] = await author.inner_text()

            # Subreddit
            subreddit = await self._page.query_selector('[data-click-id="subreddit"]')
            if subreddit:
                post['subreddit'] = await subreddit.inner_text()

            # Votes
            votes = await self._page.query_selector('[aria-label*="votes"]')
            if votes:
                post['votes'] = self.parser.parse_count(await votes.inner_text())

            # Comments count
            comments = await self._page.query_selector('[data-click-id="comments"]')
            if comments:
                post['comments_count'] = self.parser.parse_count(await comments.inner_text())

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments for a Reddit post"""
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            post_url = f"{self.base_url}/comments/{post_id}/"
            if post_id not in self._page.url:
                await self.navigate(post_url)
                await asyncio.sleep(3)

            # Expand comments
            for _ in range(max_comments // 20):
                expand_btns = await self._page.query_selector_all('button:has-text("more replies")')
                for btn in expand_btns[:5]:
                    try:
                        await btn.click()
                        await asyncio.sleep(random.uniform(0.5, 1))
                    except:
                        pass

            comments = []
            comment_elements = await self._page.query_selector_all('[data-testid="comment"]')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Author
                    author = await elem.query_selector('a[href*="/user/"]')
                    if author:
                        comment['username'] = await author.inner_text()

                    # Content
                    content = await elem.query_selector('[data-testid="comment"] > div > div')
                    if content:
                        comment['content'] = await content.inner_text()

                    # Votes
                    votes = await elem.query_selector('[aria-label*="votes"]')
                    if votes:
                        vote_text = await votes.inner_text()
                        comment['votes'] = self.parser.parse_count(vote_text) if vote_text else 0

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
