"""
Anti-Crawl Manager

Central manager for coordinating all anti-crawl mechanisms including
proxy rotation, fingerprint randomization, and captcha solving.
"""

import asyncio
from typing import Any, Dict, List, Optional, Type

from loguru import logger

from .base import (
    AntiCrawlConfig,
    AntiCrawlHandler,
    CrawlStrategy,
    RequestContext,
)
from .utils.proxy_pool import ProxyPool, ProxyConfig
from .utils.fingerprint import FingerprintGenerator, FingerprintConfig
from .utils.user_agent import UserAgentRotator, UserAgentConfig
from .utils.captcha import CaptchaResolver, CaptchaConfig


class AntiCrawlManager(AntiCrawlHandler):
    """
    Main manager for anti-crawl functionality.

    Coordinates all anti-detection mechanisms:
    - Proxy pool management
    - Browser fingerprint randomization
    - User agent rotation
    - Captcha solving
    - Request delays and rate limiting
    """

    def __init__(
        self,
        config: Optional[AntiCrawlConfig] = None,
        proxy_config: Optional[ProxyConfig] = None,
        fingerprint_config: Optional[FingerprintConfig] = None,
        user_agent_config: Optional[UserAgentConfig] = None,
        captcha_config: Optional[CaptchaConfig] = None,
    ):
        """
        Initialize the anti-crawl manager.

        Args:
            config: General anti-crawl configuration
            proxy_config: Proxy pool configuration
            fingerprint_config: Fingerprint generator configuration
            user_agent_config: User agent rotator configuration
            captcha_config: Captcha resolver configuration
        """
        super().__init__(config)

        # Initialize components
        self.proxy_pool: Optional[ProxyPool] = None
        self.fingerprint_generator: Optional[FingerprintGenerator] = None
        self.user_agent_rotator: Optional[UserAgentRotator] = None
        self.captcha_resolver: Optional[CaptchaResolver] = None

        # Initialize proxy pool
        if self.config.use_proxies:
            self.proxy_pool = ProxyPool(proxy_config or ProxyConfig())
            logger.info("Proxy pool initialized")

        # Initialize fingerprint generator
        if self.config.randomize_fingerprint:
            self.fingerprint_generator = FingerprintGenerator(
                fingerprint_config or FingerprintConfig()
            )
            logger.info("Fingerprint generator initialized")

        # Initialize user agent rotator
        if self.config.rotate_user_agent:
            self.user_agent_rotator = UserAgentRotator(
                user_agent_config or UserAgentConfig(
                    browser_types=self.config.user_agent_types
                )
            )
            logger.info("User agent rotator initialized")

        # Initialize captcha resolver
        if self.config.solve_captcha and self.config.captcha_api_key:
            self.captcha_resolver = CaptchaResolver(
                captcha_config or CaptchaConfig(
                    service=self.config.captcha_service,
                    api_key=self.config.captcha_api_key,
                )
            )
            logger.info(f"Captcha resolver initialized with {self.config.captcha_service}")

        self._proxy_rotation_counter = 0
        self._fingerprint_rotation_counter = 0
        self._current_proxy: Optional[str] = None
        self._current_fingerprint: Optional[Dict[str, Any]] = None

        logger.info(
            f"AntiCrawlManager initialized with strategy: {self.config.strategy.value}"
        )

    async def initialize(self) -> None:
        """Initialize all components asynchronously."""
        tasks = []

        if self.proxy_pool:
            tasks.append(self.proxy_pool.initialize())

        if tasks:
            await asyncio.gather(*tasks)

        logger.info("AntiCrawlManager components initialized")

    async def _get_user_agent(self) -> str:
        """
        Get a user agent string.

        Returns:
            User agent string
        """
        if not self.user_agent_rotator:
            return (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

        return self.user_agent_rotator.get_random_user_agent()

    async def _get_proxy(self) -> Optional[str]:
        """
        Get a proxy from the pool.

        Returns:
            Proxy URL or None
        """
        if not self.proxy_pool:
            return None

        # Check if we need to rotate proxy
        if self._proxy_rotation_counter >= self.config.proxy_rotation_interval:
            self._current_proxy = None
            self._proxy_rotation_counter = 0

        # Get new proxy if needed
        if not self._current_proxy:
            self._current_proxy = await self.proxy_pool.get_proxy()
            logger.debug(f"Selected proxy: {self._current_proxy}")

        self._proxy_rotation_counter += 1
        return self._current_proxy

    async def _get_fingerprint(self) -> Dict[str, Any]:
        """
        Get browser fingerprint.

        Returns:
            Fingerprint dictionary
        """
        if not self.fingerprint_generator:
            return {}

        # Check if we need to rotate fingerprint
        if self._fingerprint_rotation_counter >= self.config.fingerprint_rotation_interval:
            self._current_fingerprint = None
            self._fingerprint_rotation_counter = 0

        # Generate new fingerprint if needed
        if not self._current_fingerprint:
            self._current_fingerprint = self.fingerprint_generator.generate()
            logger.debug("Generated new fingerprint")

        self._fingerprint_rotation_counter += 1
        return self._current_fingerprint

    async def _mark_proxy_failed(self, proxy: Optional[str]) -> None:
        """
        Mark a proxy as failed.

        Args:
            proxy: Proxy URL
        """
        if proxy and self.proxy_pool:
            await self.proxy_pool.mark_failed(proxy)
            # Reset current proxy to force getting a new one
            if self._current_proxy == proxy:
                self._current_proxy = None
            logger.debug(f"Marked proxy as failed: {proxy}")

    async def solve_captcha(
        self,
        captcha_type: str,
        site_key: str,
        page_url: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Solve a captcha.

        Args:
            captcha_type: Type of captcha (recaptcha_v2, recaptcha_v3, hcaptcha, etc.)
            site_key: Site key for the captcha
            page_url: URL of the page with captcha
            **kwargs: Additional captcha-specific parameters

        Returns:
            Captcha solution token or None
        """
        if not self.captcha_resolver:
            logger.warning("Captcha resolver not initialized")
            return None

        try:
            solution = await self.captcha_resolver.solve(
                captcha_type=captcha_type,
                site_key=site_key,
                page_url=page_url,
                **kwargs,
            )
            logger.info(f"Captcha solved successfully: {captcha_type}")
            return solution
        except Exception as e:
            logger.error(f"Failed to solve captcha: {str(e)}")
            return None

    async def apply_fingerprint_to_playwright(
        self,
        page: Any,
        fingerprint: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Apply browser fingerprint to Playwright page.

        Args:
            page: Playwright page object
            fingerprint: Fingerprint to apply (uses current if None)
        """
        if not self.fingerprint_generator:
            return

        fingerprint = fingerprint or self._current_fingerprint or self.fingerprint_generator.generate()

        await self.fingerprint_generator.apply_to_playwright(page, fingerprint)
        logger.debug("Applied fingerprint to Playwright page")

    def get_current_fingerprint(self) -> Optional[Dict[str, Any]]:
        """
        Get the current fingerprint.

        Returns:
            Current fingerprint or None
        """
        return self._current_fingerprint

    def get_current_proxy(self) -> Optional[str]:
        """
        Get the current proxy.

        Returns:
            Current proxy or None
        """
        return self._current_proxy

    async def add_proxies(self, proxies: List[str]) -> None:
        """
        Add proxies to the pool.

        Args:
            proxies: List of proxy URLs
        """
        if self.proxy_pool:
            await self.proxy_pool.add_proxies(proxies)
            logger.info(f"Added {len(proxies)} proxies to pool")

    async def remove_proxy(self, proxy: str) -> None:
        """
        Remove a proxy from the pool.

        Args:
            proxy: Proxy URL to remove
        """
        if self.proxy_pool:
            await self.proxy_pool.remove_proxy(proxy)
            logger.info(f"Removed proxy: {proxy}")

    def set_strategy(self, strategy: CrawlStrategy) -> None:
        """
        Change the crawling strategy.

        Args:
            strategy: New crawling strategy
        """
        self.config.strategy = strategy
        logger.info(f"Changed strategy to: {strategy.value}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Statistics dictionary
        """
        stats = super().get_stats()

        # Add component stats
        if self.proxy_pool:
            stats["proxy_pool"] = self.proxy_pool.get_stats()

        if self.user_agent_rotator:
            stats["user_agent"] = {
                "current": self.user_agent_rotator.current_user_agent,
            }

        if self.fingerprint_generator:
            stats["fingerprint"] = {
                "rotation_counter": self._fingerprint_rotation_counter,
                "has_current": self._current_fingerprint is not None,
            }

        if self.captcha_resolver:
            stats["captcha"] = self.captcha_resolver.get_stats()

        return stats

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.

        Returns:
            Health check results
        """
        health = {
            "status": "healthy",
            "components": {},
        }

        # Check proxy pool
        if self.proxy_pool:
            try:
                pool_health = await self.proxy_pool.health_check()
                health["components"]["proxy_pool"] = pool_health
                if pool_health["available_proxies"] == 0:
                    health["status"] = "degraded"
            except Exception as e:
                health["components"]["proxy_pool"] = {"status": "error", "error": str(e)}
                health["status"] = "degraded"

        # Check other components
        health["components"]["user_agent_rotator"] = {
            "status": "healthy" if self.user_agent_rotator else "disabled"
        }
        health["components"]["fingerprint_generator"] = {
            "status": "healthy" if self.fingerprint_generator else "disabled"
        }
        health["components"]["captcha_resolver"] = {
            "status": "healthy" if self.captcha_resolver else "disabled"
        }

        return health

    async def reset(self) -> None:
        """Reset manager state."""
        await super().reset()

        self._proxy_rotation_counter = 0
        self._fingerprint_rotation_counter = 0
        self._current_proxy = None
        self._current_fingerprint = None

        if self.proxy_pool:
            await self.proxy_pool.reset_stats()

        logger.info("AntiCrawlManager reset complete")

    async def close(self) -> None:
        """Cleanup all resources."""
        await super().close()

        if self.proxy_pool:
            await self.proxy_pool.close()

        if self.captcha_resolver:
            await self.captcha_resolver.close()

        logger.info("AntiCrawlManager closed")


# Factory function for easy manager creation
def create_anti_crawl_manager(
    strategy: CrawlStrategy = CrawlStrategy.BALANCED,
    use_proxies: bool = True,
    proxy_list: Optional[List[str]] = None,
    solve_captcha: bool = False,
    captcha_api_key: Optional[str] = None,
    **kwargs: Any,
) -> AntiCrawlManager:
    """
    Factory function to create an AntiCrawlManager with common settings.

    Args:
        strategy: Crawling strategy
        use_proxies: Whether to use proxies
        proxy_list: Initial list of proxies
        solve_captcha: Whether to enable captcha solving
        captcha_api_key: API key for captcha service
        **kwargs: Additional configuration options

    Returns:
        Configured AntiCrawlManager instance
    """
    config = AntiCrawlConfig(
        strategy=strategy,
        use_proxies=use_proxies,
        solve_captcha=solve_captcha,
        captcha_api_key=captcha_api_key,
        **kwargs,
    )

    proxy_config = None
    if use_proxies and proxy_list:
        proxy_config = ProxyConfig(initial_proxies=proxy_list)

    manager = AntiCrawlManager(
        config=config,
        proxy_config=proxy_config,
    )

    logger.info(f"Created AntiCrawlManager with strategy: {strategy.value}")
    return manager
