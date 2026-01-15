"""
Example usage of OmniSense spider framework
Demonstrates how to create platform-specific spiders and use the spider manager
"""

import asyncio
from typing import Any, Dict, List
from omnisense.spider.base import BaseSpider
from omnisense.spider.manager import SpiderManager


class ExamplePlatformSpider(BaseSpider):
    """
    Example implementation of a platform-specific spider
    This demonstrates how to implement the abstract methods from BaseSpider
    """

    async def login(self, username: str, password: str) -> bool:
        """Login to the platform"""
        try:
            self.logger.info(f"Logging in as {username}...")

            # Navigate to login page
            await self.navigate("https://example.com/login")

            # Fill in credentials
            await self.type_text("#username", username)
            await self.type_text("#password", password)

            # Click login button
            await self.click_element("#login-btn")

            # Wait for login to complete
            await self.wait_for_selector("#user-profile", timeout=10000)

            self._is_logged_in = True
            self.logger.info("Login successful")
            return True

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search for content by keyword"""
        try:
            self.logger.info(f"Searching for: {keyword}")

            # Navigate to search page
            search_url = f"https://example.com/search?q={keyword}"
            await self.navigate(search_url)

            # Wait for results to load
            await self.wait_for_selector(".search-result")

            # Scroll to load more results
            await self.scroll_to_bottom(wait_time=2.0)

            # Extract results
            results = []
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            result_elements = soup.select(".search-result")[:max_results]

            for element in result_elements:
                result = {
                    "id": self.parser.extract_attribute(element, ".result-id", "data-id"),
                    "title": self.parser.extract_text(element, ".result-title"),
                    "author": self.parser.extract_text(element, ".result-author"),
                    "description": self.parser.extract_text(element, ".result-desc"),
                    "url": self.parser.extract_attribute(element, "a", "href"),
                    "thumbnail": self.parser.extract_attribute(element, "img", "src"),
                    "platform": self.platform,
                }
                results.append(result)

            self.logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            self.logger.info(f"Getting profile for user: {user_id}")

            # Navigate to user profile
            await self.navigate(f"https://example.com/user/{user_id}")

            # Wait for profile to load
            await self.wait_for_selector(".user-profile")

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
                "platform": self.platform,
            }

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get posts from a user"""
        try:
            self.logger.info(f"Getting posts for user: {user_id}")

            # Navigate to user posts
            await self.navigate(f"https://example.com/user/{user_id}/posts")

            # Wait for posts to load
            await self.wait_for_selector(".post-item")

            # Scroll to load more posts
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=5)

            # Extract posts
            posts = []
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post_elements = soup.select(".post-item")[:max_posts]

            for element in post_elements:
                post = {
                    "id": self.parser.extract_attribute(element, ".post-id", "data-id"),
                    "user_id": user_id,
                    "title": self.parser.extract_text(element, ".post-title"),
                    "content": self.parser.extract_text(element, ".post-content"),
                    "url": self.parser.extract_attribute(element, "a", "href"),
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

                # Download media if enabled
                thumbnail = self.parser.extract_attribute(element, ".post-image", "src")
                if thumbnail:
                    media_path = await self.download_media(thumbnail)
                    post["media_local_path"] = str(media_path) if media_path else None

                posts.append(post)

            self.logger.info(f"Got {len(posts)} posts")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get user posts: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed information about a post"""
        try:
            self.logger.info(f"Getting post detail: {post_id}")

            # Navigate to post
            await self.navigate(f"https://example.com/post/{post_id}")

            # Wait for post to load
            await self.wait_for_selector(".post-detail")

            # Extract post data
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            post = {
                "id": post_id,
                "title": self.parser.extract_text(soup, ".post-title"),
                "content": self.parser.extract_text(soup, ".post-content"),
                "author_id": self.parser.extract_attribute(soup, ".author", "data-user-id"),
                "author_name": self.parser.extract_text(soup, ".author-name"),
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
                "hashtags": self.parser.extract_hashtags(
                    self.parser.extract_text(soup, ".post-content")
                ),
                "platform": self.platform,
            }

            # Extract media
            images = self.parser.extract_images(soup, base_url="https://example.com")
            videos = self.parser.extract_videos(soup, base_url="https://example.com")

            post["images"] = images
            post["videos"] = videos

            # Download media
            if images:
                for img in images[:5]:  # Limit to first 5 images
                    await self.download_media(img["src"])

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments for a post"""
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            # Navigate to post
            await self.navigate(f"https://example.com/post/{post_id}")

            # Wait for comments to load
            await self.wait_for_selector(".comment-item")

            # Scroll to load more comments
            await self.scroll_to_bottom(wait_time=2.0, max_scrolls=3)

            # Extract comments
            comments = []
            html = await self._page.content()
            soup = self.parser.parse_html(html)

            comment_elements = soup.select(".comment-item")[:max_comments]

            for element in comment_elements:
                comment = {
                    "id": self.parser.extract_attribute(element, ".comment-id", "data-id"),
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
                    "platform": self.platform,
                }
                comments.append(comment)

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []


async def example_basic_usage():
    """Example of basic spider usage"""
    print("\n=== Basic Spider Usage ===\n")

    # Create spider instance
    spider = ExamplePlatformSpider(
        platform="example_platform",
        headless=True,  # Run in headless mode
    )

    # Use context manager for automatic cleanup
    async with spider.session():
        # Search for content
        results = await spider.search("python programming", max_results=10)
        print(f"Found {len(results)} search results")

        # Get user profile
        if results:
            first_result = results[0]
            user_id = first_result.get("author")
            if user_id:
                profile = await spider.get_user_profile(user_id)
                print(f"User profile: {profile.get('username')}")

                # Get user posts
                posts = await spider.get_user_posts(user_id, max_posts=5)
                print(f"User has {len(posts)} recent posts")


async def example_manager_usage():
    """Example of spider manager usage"""
    print("\n=== Spider Manager Usage ===\n")

    # Create spider manager
    manager = SpiderManager(max_concurrent=3)

    # Register spiders
    manager.register_spider("example_platform", ExamplePlatformSpider)
    # You would register more platforms here:
    # manager.register_spider("douyin", DouyinSpider)
    # manager.register_spider("xiaohongshu", XiaohongshuSpider)

    async with manager:
        # Search across multiple platforms
        results = await manager.search_all_platforms(
            keyword="python programming",
            platforms=["example_platform"],
            max_results=20,
        )

        for platform, platform_results in results.items():
            print(f"{platform}: {len(platform_results)} results")

        # Get statistics
        stats = manager.get_stats()
        print(f"\nManager stats: {stats}")


async def example_concurrent_operations():
    """Example of concurrent operations with multiple spiders"""
    print("\n=== Concurrent Operations ===\n")

    manager = SpiderManager(max_concurrent=5)
    manager.register_spider("example_platform", ExamplePlatformSpider)

    async with manager:
        # Create multiple tasks
        tasks = []

        # Search for different keywords concurrently
        keywords = ["python", "javascript", "rust", "golang"]
        for keyword in keywords:
            task = manager.execute_task(
                "example_platform",
                "search",
                keyword,
                10
            )
            tasks.append((keyword, task))

        # Wait for all tasks to complete
        for keyword, task in tasks:
            try:
                results = await task
                print(f"'{keyword}': {len(results)} results")
            except Exception as e:
                print(f"'{keyword}': failed - {e}")


async def example_monitoring():
    """Example of monitoring user activity"""
    print("\n=== User Activity Monitoring ===\n")

    manager = SpiderManager()
    manager.register_spider("example_platform", ExamplePlatformSpider)

    async def on_new_post(platform: str, user_id: str, posts: List[Dict]):
        """Callback for new posts"""
        print(f"[{platform}] New posts from {user_id}: {len(posts)}")
        for post in posts:
            print(f"  - {post.get('title')}")

    async with manager:
        # Monitor user activity (this will run indefinitely)
        # Use Ctrl+C to stop
        try:
            await manager.monitor_user_activity(
                user_ids={"example_platform": "user123"},
                interval=300,  # Check every 5 minutes
                callback=on_new_post,
            )
        except KeyboardInterrupt:
            print("\nMonitoring stopped")


async def main():
    """Run examples"""
    print("OmniSense Spider Framework Examples")
    print("=" * 50)

    # Run examples
    try:
        await example_basic_usage()
    except Exception as e:
        print(f"Basic usage example failed: {e}")

    try:
        await example_manager_usage()
    except Exception as e:
        print(f"Manager usage example failed: {e}")

    try:
        await example_concurrent_operations()
    except Exception as e:
        print(f"Concurrent operations example failed: {e}")

    # Uncomment to run monitoring example
    # await example_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
