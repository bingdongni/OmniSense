"""
Platform Spider Template
Copy this file to create new platform-specific spiders

Usage:
1. Copy this file to omnisense/spider/platforms/your_platform.py
2. Replace "YourPlatform" with your platform name
3. Implement all abstract methods
4. Add platform-specific logic
"""

from typing import Any, Dict, List, Optional
from omnisense.spider.base import BaseSpider


class YourPlatformSpider(BaseSpider):
    """
    Spider for YourPlatform

    Platform-specific information:
    - Base URL: https://yourplatform.com
    - Login required: Yes/No
    - Rate limit: X requests per minute
    - Special features: List any special considerations
    """

    def __init__(self, *args, **kwargs):
        """Initialize YourPlatform spider"""
        super().__init__(*args, **kwargs)

        # Platform-specific configuration
        self.base_url = "https://yourplatform.com"
        self.api_base_url = "https://api.yourplatform.com"

        # Add any platform-specific initialization here

    async def login(self, username: str, password: str) -> bool:
        """
        Login to YourPlatform

        Args:
            username: Username, email, or phone number
            password: Password

        Returns:
            True if login successful

        Implementation steps:
        1. Navigate to login page
        2. Fill in credentials
        3. Handle CAPTCHA if needed
        4. Click login button
        5. Wait for login to complete
        6. Verify login success
        7. Save cookies/session
        """
        try:
            self.logger.info(f"Logging in to {self.platform} as {username}...")

            # Navigate to login page
            login_url = f"{self.base_url}/login"
            if not await self.navigate(login_url):
                return False

            # Wait for login form
            if not await self.wait_for_selector("#username-input"):
                self.logger.error("Login form not found")
                return False

            # Fill in credentials
            await self.type_text("#username-input", username)
            await self.type_text("#password-input", password)

            # Handle CAPTCHA if present
            # TODO: Implement CAPTCHA handling if needed

            # Click login button
            await self.click_element("#login-button")

            # Wait for login to complete
            # Check for success indicator (e.g., user profile element)
            if await self.wait_for_selector("#user-profile", timeout=10000):
                self._is_logged_in = True
                self.logger.info("Login successful")
                return True
            else:
                self.logger.error("Login failed - profile not found")
                return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for content by keyword

        Args:
            keyword: Search keyword
            max_results: Maximum number of results to return

        Returns:
            List of search result dictionaries

        Result format:
            {
                "id": "unique_id",
                "title": "result title",
                "description": "result description",
                "author": "author_name",
                "author_id": "author_id",
                "url": "result_url",
                "thumbnail": "thumbnail_url",
                "created_at": datetime object,
                "likes": int,
                "comments": int,
                "shares": int,
                "platform": "yourplatform"
            }
        """
        try:
            self.logger.info(f"Searching for '{keyword}' on {self.platform}")

            # Navigate to search page
            search_url = f"{self.base_url}/search?q={keyword}"
            if not await self.navigate(search_url):
                return []

            # Wait for results to load
            if not await self.wait_for_selector(".search-result"):
                self.logger.warning("No search results found")
                return []

            # Scroll to load more results
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            # Extract results
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            results = []
            result_elements = soup.select(".search-result")[:max_results]

            for element in result_elements:
                try:
                    result = {
                        "id": self.parser.extract_attribute(element, "[data-id]", "data-id"),
                        "title": self.parser.extract_text(element, ".result-title"),
                        "description": self.parser.extract_text(element, ".result-desc"),
                        "author": self.parser.extract_text(element, ".author-name"),
                        "author_id": self.parser.extract_attribute(element, ".author", "data-author-id"),
                        "url": self.parser.extract_attribute(element, "a.result-link", "href"),
                        "thumbnail": self.parser.extract_attribute(element, "img.thumbnail", "src"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(element, ".post-time")
                        ),
                        "likes": self.parser.parse_count(
                            self.parser.extract_text(element, ".likes-count")
                        ),
                        "comments": self.parser.parse_count(
                            self.parser.extract_text(element, ".comments-count")
                        ),
                        "shares": self.parser.parse_count(
                            self.parser.extract_text(element, ".shares-count")
                        ),
                        "platform": self.platform,
                    }

                    # Download thumbnail if enabled
                    if result["thumbnail"] and self.config.spider.download_media:
                        await self.download_media(result["thumbnail"])

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
        """
        Get user profile information

        Args:
            user_id: User ID

        Returns:
            User profile dictionary

        Profile format:
            {
                "user_id": "user_id",
                "username": "username",
                "display_name": "display name",
                "bio": "user bio",
                "avatar": "avatar_url",
                "followers": int,
                "following": int,
                "posts_count": int,
                "verified": bool,
                "created_at": datetime object,
                "platform": "yourplatform"
            }
        """
        try:
            self.logger.info(f"Getting profile for user: {user_id}")

            # Navigate to user profile
            profile_url = f"{self.base_url}/user/{user_id}"
            if not await self.navigate(profile_url):
                return {}

            # Wait for profile to load
            if not await self.wait_for_selector(".user-profile"):
                self.logger.error("Profile not found")
                return {}

            # Extract profile data
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            profile = {
                "user_id": user_id,
                "username": self.parser.extract_text(soup, ".username"),
                "display_name": self.parser.extract_text(soup, ".display-name"),
                "bio": self.parser.extract_text(soup, ".bio"),
                "avatar": self.parser.extract_attribute(soup, ".avatar img", "src"),
                "followers": self.parser.parse_count(
                    self.parser.extract_text(soup, ".followers-count")
                ),
                "following": self.parser.parse_count(
                    self.parser.extract_text(soup, ".following-count")
                ),
                "posts_count": self.parser.parse_count(
                    self.parser.extract_text(soup, ".posts-count")
                ),
                "verified": soup.select_one(".verified-badge") is not None,
                "created_at": self.parser.parse_date(
                    self.parser.extract_text(soup, ".join-date")
                ),
                "platform": self.platform,
            }

            # Download avatar if enabled
            if profile["avatar"] and self.config.spider.download_media:
                await self.download_media(profile["avatar"])

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """
        Get posts from a user

        Args:
            user_id: User ID
            max_posts: Maximum number of posts to retrieve

        Returns:
            List of post dictionaries

        Post format:
            {
                "id": "post_id",
                "user_id": "user_id",
                "title": "post title",
                "content": "post content",
                "url": "post_url",
                "created_at": datetime object,
                "likes": int,
                "comments": int,
                "shares": int,
                "views": int,
                "images": [{"src": "url", "alt": "text"}],
                "videos": [{"src": "url", "poster": "url"}],
                "platform": "yourplatform"
            }
        """
        try:
            self.logger.info(f"Getting posts for user: {user_id}")

            # Navigate to user posts
            posts_url = f"{self.base_url}/user/{user_id}/posts"
            if not await self.navigate(posts_url):
                return []

            # Wait for posts to load
            if not await self.wait_for_selector(".post-item"):
                self.logger.warning("No posts found")
                return []

            # Scroll to load more posts
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=5)

            # Extract posts
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            posts = []
            post_elements = soup.select(".post-item")[:max_posts]

            for element in post_elements:
                try:
                    post = {
                        "id": self.parser.extract_attribute(element, "[data-post-id]", "data-post-id"),
                        "user_id": user_id,
                        "title": self.parser.extract_text(element, ".post-title"),
                        "content": self.parser.extract_text(element, ".post-content"),
                        "url": self.parser.extract_attribute(element, "a.post-link", "href"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(element, ".post-time")
                        ),
                        "likes": self.parser.parse_count(
                            self.parser.extract_text(element, ".likes-count")
                        ),
                        "comments": self.parser.parse_count(
                            self.parser.extract_text(element, ".comments-count")
                        ),
                        "shares": self.parser.parse_count(
                            self.parser.extract_text(element, ".shares-count")
                        ),
                        "views": self.parser.parse_count(
                            self.parser.extract_text(element, ".views-count")
                        ),
                        "images": self.parser.extract_images(element, base_url=self.base_url),
                        "videos": self.parser.extract_videos(element, base_url=self.base_url),
                        "platform": self.platform,
                    }

                    # Download media if enabled
                    if self.config.spider.download_media:
                        for img in post["images"][:3]:  # Limit to first 3 images
                            await self.download_media(img["src"])

                    posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse post: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} posts")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get user posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a post

        Args:
            post_id: Post ID

        Returns:
            Post detail dictionary (same format as get_user_posts)
        """
        try:
            self.logger.info(f"Getting post detail: {post_id}")

            # Navigate to post
            post_url = f"{self.base_url}/post/{post_id}"
            if not await self.navigate(post_url):
                return {}

            # Wait for post to load
            if not await self.wait_for_selector(".post-detail"):
                self.logger.error("Post not found")
                return {}

            # Extract post data
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post = {
                "id": post_id,
                "title": self.parser.extract_text(soup, ".post-title"),
                "content": self.parser.extract_text(soup, ".post-content"),
                "author_id": self.parser.extract_attribute(soup, ".author", "data-user-id"),
                "author_name": self.parser.extract_text(soup, ".author-name"),
                "url": post_url,
                "created_at": self.parser.parse_date(
                    self.parser.extract_text(soup, ".post-time")
                ),
                "likes": self.parser.parse_count(
                    self.parser.extract_text(soup, ".likes-count")
                ),
                "comments": self.parser.parse_count(
                    self.parser.extract_text(soup, ".comments-count")
                ),
                "shares": self.parser.parse_count(
                    self.parser.extract_text(soup, ".shares-count")
                ),
                "views": self.parser.parse_count(
                    self.parser.extract_text(soup, ".views-count")
                ),
                "images": self.parser.extract_images(soup, base_url=self.base_url),
                "videos": self.parser.extract_videos(soup, base_url=self.base_url),
                "hashtags": self.parser.extract_hashtags(
                    self.parser.extract_text(soup, ".post-content")
                ),
                "platform": self.platform,
            }

            # Download media if enabled
            if self.config.spider.download_media:
                for img in post["images"]:
                    await self.download_media(img["src"])
                for video in post["videos"]:
                    await self.download_media(video["src"])

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Get comments for a post

        Args:
            post_id: Post ID
            max_comments: Maximum number of comments to retrieve

        Returns:
            List of comment dictionaries

        Comment format:
            {
                "id": "comment_id",
                "post_id": "post_id",
                "user_id": "user_id",
                "username": "username",
                "content": "comment content",
                "created_at": datetime object,
                "likes": int,
                "parent_id": "parent_comment_id" (for replies),
                "platform": "yourplatform"
            }
        """
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            # Navigate to post
            post_url = f"{self.base_url}/post/{post_id}"
            if not await self.navigate(post_url):
                return []

            # Wait for comments to load
            if not await self.wait_for_selector(".comment-item"):
                self.logger.warning("No comments found")
                return []

            # Scroll to load more comments
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            # Extract comments
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            comments = []
            comment_elements = soup.select(".comment-item")[:max_comments]

            for element in comment_elements:
                try:
                    comment = {
                        "id": self.parser.extract_attribute(element, "[data-comment-id]", "data-comment-id"),
                        "post_id": post_id,
                        "user_id": self.parser.extract_attribute(element, ".comment-author", "data-user-id"),
                        "username": self.parser.extract_text(element, ".comment-author"),
                        "content": self.parser.extract_text(element, ".comment-content"),
                        "created_at": self.parser.parse_date(
                            self.parser.extract_text(element, ".comment-time")
                        ),
                        "likes": self.parser.parse_count(
                            self.parser.extract_text(element, ".comment-likes")
                        ),
                        "parent_id": self.parser.extract_attribute(element, "[data-parent-id]", "data-parent-id"),
                        "platform": self.platform,
                    }

                    comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []

    # Optional: Add platform-specific methods

    async def get_trending(self, category: Optional[str] = None, max_results: int = 20) -> List[Dict[str, Any]]:
        """Get trending content (optional method)"""
        pass

    async def get_recommendations(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """Get recommended content (optional method)"""
        pass


# Usage example
async def main():
    """Example usage"""
    import asyncio

    spider = YourPlatformSpider(
        platform="yourplatform",
        headless=True,
        proxy=None,  # Optional proxy
    )

    async with spider.session():
        # Login if required
        # await spider.login("username", "password")

        # Search
        results = await spider.search("keyword", max_results=10)
        print(f"Found {len(results)} results")

        # Get user profile
        if results:
            user_id = results[0].get("author_id")
            if user_id:
                profile = await spider.get_user_profile(user_id)
                print(f"User: {profile.get('username')}")

                # Get user posts
                posts = await spider.get_user_posts(user_id, max_posts=5)
                print(f"User posts: {len(posts)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
