"""
Spider manager for handling multiple platforms
Provides unified interface for managing and coordinating multiple spiders
"""

import asyncio
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

from omnisense.config import config
from omnisense.utils.logger import get_logger
from omnisense.spider.base import BaseSpider


class SpiderManager:
    """
    Spider manager for coordinating multiple platform spiders

    Features:
    - Dynamic spider registration and loading
    - Concurrent spider execution
    - Task scheduling and queue management
    - Resource pooling and cleanup
    - Error handling and recovery
    """

    def __init__(self, max_concurrent: Optional[int] = None):
        """
        Initialize spider manager

        Args:
            max_concurrent: Maximum number of concurrent spiders (default from config)
        """
        self.logger = get_logger("spider.manager")
        self.max_concurrent = max_concurrent or config.spider.concurrent_tasks

        # Spider registry
        self._spider_classes: Dict[str, Type[BaseSpider]] = {}
        self._spider_instances: Dict[str, BaseSpider] = {}

        # Task management
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        # Statistics
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_spiders": 0,
        }

        self.logger.info(
            f"Spider manager initialized (max_concurrent={self.max_concurrent})"
        )

    def register_spider(
        self,
        platform: str,
        spider_class: Type[BaseSpider],
    ) -> None:
        """
        Register a spider class for a platform

        Args:
            platform: Platform name
            spider_class: Spider class (subclass of BaseSpider)
        """
        if not issubclass(spider_class, BaseSpider):
            raise ValueError(f"{spider_class} must be a subclass of BaseSpider")

        self._spider_classes[platform] = spider_class
        self.logger.info(f"Registered spider for platform: {platform}")

    def unregister_spider(self, platform: str) -> None:
        """
        Unregister a spider for a platform

        Args:
            platform: Platform name
        """
        if platform in self._spider_classes:
            del self._spider_classes[platform]
            self.logger.info(f"Unregistered spider for platform: {platform}")

    async def get_spider(
        self,
        platform: str,
        headless: bool = True,
        proxy: Optional[str] = None,
        **kwargs,
    ) -> BaseSpider:
        """
        Get or create a spider instance for a platform

        Args:
            platform: Platform name
            headless: Run browser in headless mode
            proxy: Proxy server URL
            **kwargs: Additional spider-specific arguments

        Returns:
            Spider instance
        """
        # Return existing instance if available
        if platform in self._spider_instances:
            return self._spider_instances[platform]

        # Check if spider is registered
        if platform not in self._spider_classes:
            raise ValueError(f"No spider registered for platform: {platform}")

        # Create new spider instance
        spider_class = self._spider_classes[platform]

        # Get proxy from config if enabled
        if config.proxy.enabled and not proxy:
            proxy = config.proxy.http_proxy

        spider = spider_class(
            platform=platform,
            headless=headless,
            proxy=proxy,
            **kwargs,
        )

        self._spider_instances[platform] = spider
        self._stats["active_spiders"] += 1
        self.logger.info(f"Created spider instance for platform: {platform}")

        return spider

    async def close_spider(self, platform: str) -> None:
        """
        Close and remove a spider instance

        Args:
            platform: Platform name
        """
        if platform in self._spider_instances:
            spider = self._spider_instances[platform]
            await spider.stop()
            del self._spider_instances[platform]
            self._stats["active_spiders"] -= 1
            self.logger.info(f"Closed spider for platform: {platform}")

    async def close_all_spiders(self) -> None:
        """Close all active spider instances"""
        platforms = list(self._spider_instances.keys())
        for platform in platforms:
            await self.close_spider(platform)
        self.logger.info("All spiders closed")

    async def execute_task(
        self,
        platform: str,
        method: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a method on a spider

        Args:
            platform: Platform name
            method: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Method result
        """
        async with self._semaphore:
            try:
                # Get or create spider
                spider = await self.get_spider(platform)

                # Start spider if not already started
                if not spider._browser:
                    await spider.start()

                # Execute method
                if not hasattr(spider, method):
                    raise AttributeError(
                        f"Spider '{platform}' has no method '{method}'"
                    )

                method_func = getattr(spider, method)
                result = await method_func(*args, **kwargs)

                self._stats["completed_tasks"] += 1
                return result

            except Exception as e:
                self._stats["failed_tasks"] += 1
                self.logger.error(
                    f"Error executing {method} on {platform}: {e}"
                )
                raise

    async def execute_on_multiple(
        self,
        platforms: List[str],
        method: str,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a method on multiple spiders concurrently

        Args:
            platforms: List of platform names
            method: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Dictionary mapping platform to result
        """
        tasks = []
        for platform in platforms:
            task = self.execute_task(platform, method, *args, **kwargs)
            tasks.append((platform, task))

        results = {}
        for platform, task in tasks:
            try:
                result = await task
                results[platform] = {"success": True, "data": result}
            except Exception as e:
                results[platform] = {"success": False, "error": str(e)}
                self.logger.error(f"Task failed for {platform}: {e}")

        return results

    async def search_all_platforms(
        self,
        keyword: str,
        platforms: Optional[List[str]] = None,
        max_results: int = 20,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across multiple platforms

        Args:
            keyword: Search keyword
            platforms: List of platforms to search (default: all registered)
            max_results: Maximum results per platform

        Returns:
            Dictionary mapping platform to search results
        """
        if platforms is None:
            platforms = list(self._spider_classes.keys())

        self.logger.info(
            f"Searching '{keyword}' across {len(platforms)} platforms"
        )

        results = await self.execute_on_multiple(
            platforms,
            "search",
            keyword,
            max_results,
        )

        # Extract successful results
        search_results = {}
        for platform, result in results.items():
            if result["success"]:
                search_results[platform] = result["data"]
            else:
                search_results[platform] = []
                self.logger.warning(
                    f"Search failed for {platform}: {result.get('error')}"
                )

        total_results = sum(len(v) for v in search_results.values())
        self.logger.info(
            f"Search completed: {total_results} total results from "
            f"{len(search_results)} platforms"
        )

        return search_results

    async def get_user_data_from_multiple(
        self,
        user_ids: Dict[str, str],
        include_posts: bool = True,
        max_posts: int = 20,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get user data from multiple platforms

        Args:
            user_ids: Dictionary mapping platform to user_id
            include_posts: Whether to include user posts
            max_posts: Maximum number of posts per user

        Returns:
            Dictionary mapping platform to user data
        """
        results = {}

        for platform, user_id in user_ids.items():
            try:
                spider = await self.get_spider(platform)
                if not spider._browser:
                    await spider.start()

                # Get user profile
                profile = await spider.get_user_profile(user_id)
                results[platform] = {"profile": profile}

                # Get user posts if requested
                if include_posts:
                    posts = await spider.get_user_posts(user_id, max_posts)
                    results[platform]["posts"] = posts

                self.logger.info(
                    f"Retrieved user data from {platform}: {user_id}"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to get user data from {platform}: {e}"
                )
                results[platform] = {"error": str(e)}

        return results

    async def monitor_user_activity(
        self,
        user_ids: Dict[str, str],
        interval: int = 3600,
        callback: Optional[callable] = None,
    ) -> None:
        """
        Monitor user activity across platforms

        Args:
            user_ids: Dictionary mapping platform to user_id
            interval: Check interval in seconds
            callback: Callback function for new posts
        """
        self.logger.info(
            f"Starting user activity monitoring (interval={interval}s)"
        )

        seen_posts = {platform: set() for platform in user_ids.keys()}

        while True:
            try:
                for platform, user_id in user_ids.items():
                    try:
                        spider = await self.get_spider(platform)
                        if not spider._browser:
                            await spider.start()

                        # Get recent posts
                        posts = await spider.get_user_posts(user_id, max_posts=10)

                        # Check for new posts
                        new_posts = []
                        for post in posts:
                            post_id = post.get("id") or post.get("post_id")
                            if post_id not in seen_posts[platform]:
                                seen_posts[platform].add(post_id)
                                new_posts.append(post)

                        # Call callback for new posts
                        if new_posts and callback:
                            await callback(platform, user_id, new_posts)

                        self.logger.debug(
                            f"Monitored {platform}/{user_id}: "
                            f"{len(new_posts)} new posts"
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Error monitoring {platform}/{user_id}: {e}"
                        )

                # Wait for next interval
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                self.logger.info("Monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        return {
            **self._stats,
            "registered_platforms": list(self._spider_classes.keys()),
            "active_platforms": list(self._spider_instances.keys()),
        }

    def reset_stats(self) -> None:
        """Reset statistics"""
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_spiders": len(self._spider_instances),
        }
        self.logger.info("Statistics reset")

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health status of all active spiders

        Returns:
            Dictionary mapping platform to health status
        """
        health = {}

        for platform, spider in self._spider_instances.items():
            try:
                # Check if browser is active
                if spider._browser and spider._browser.is_connected():
                    health[platform] = True
                else:
                    health[platform] = False
            except Exception:
                health[platform] = False

        return health

    async def restart_unhealthy_spiders(self) -> List[str]:
        """
        Restart spiders that are unhealthy

        Returns:
            List of restarted platform names
        """
        health = await self.health_check()
        restarted = []

        for platform, is_healthy in health.items():
            if not is_healthy:
                try:
                    self.logger.warning(f"Restarting unhealthy spider: {platform}")
                    await self.close_spider(platform)
                    spider = await self.get_spider(platform)
                    await spider.start()
                    restarted.append(platform)
                except Exception as e:
                    self.logger.error(f"Failed to restart spider {platform}: {e}")

        return restarted

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_all_spiders()

    def __repr__(self) -> str:
        return (
            f"<SpiderManager("
            f"registered={len(self._spider_classes)}, "
            f"active={len(self._spider_instances)}, "
            f"max_concurrent={self.max_concurrent})>"
        )
