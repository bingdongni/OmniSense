"""
Base Anti-Crawl Handler

Provides the base class for all anti-crawl handlers with common functionality
for evading detection and bypassing anti-bot measures.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

from loguru import logger


class CrawlStrategy(Enum):
    """Crawling strategy types"""
    CONSERVATIVE = "conservative"  # Slower, more human-like
    BALANCED = "balanced"          # Balance between speed and stealth
    AGGRESSIVE = "aggressive"      # Faster, less cautious


@dataclass
class RequestContext:
    """Context for a single request"""
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    cookies: Optional[Dict[str, str]] = None
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    fingerprint: Optional[Dict[str, Any]] = None
    delay: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AntiCrawlConfig:
    """Configuration for anti-crawl mechanisms"""
    # Proxy settings
    use_proxies: bool = True
    proxy_rotation_interval: int = 10  # Requests before rotating proxy
    proxy_health_check: bool = True

    # User agent settings
    rotate_user_agent: bool = True
    user_agent_types: List[str] = field(default_factory=lambda: ["chrome", "firefox", "safari", "edge"])

    # Fingerprint settings
    randomize_fingerprint: bool = True
    fingerprint_rotation_interval: int = 50  # Requests before rotating fingerprint

    # Delay settings
    min_delay: float = 1.0  # Minimum delay between requests (seconds)
    max_delay: float = 3.0  # Maximum delay between requests (seconds)
    use_random_delay: bool = True

    # Header settings
    randomize_headers: bool = True
    accept_languages: List[str] = field(default_factory=lambda: ["en-US", "en", "zh-CN", "zh"])

    # Cookie settings
    rotate_cookies: bool = False
    cookie_rotation_interval: int = 100

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 5.0
    backoff_factor: float = 2.0  # Exponential backoff multiplier

    # Captcha settings
    solve_captcha: bool = False
    captcha_service: str = "2captcha"  # 2captcha, anticaptcha, etc.
    captcha_api_key: Optional[str] = None

    # Strategy
    strategy: CrawlStrategy = CrawlStrategy.BALANCED

    # Rate limiting
    requests_per_minute: int = 30
    concurrent_requests: int = 5


class AntiCrawlHandler(ABC):
    """
    Base class for anti-crawl handlers.

    Provides core functionality for:
    - Request preparation with anti-detection measures
    - Retry logic with exponential backoff
    - Rate limiting
    - Proxy rotation
    - Fingerprint randomization
    """

    def __init__(self, config: Optional[AntiCrawlConfig] = None):
        """
        Initialize the anti-crawl handler.

        Args:
            config: Anti-crawl configuration
        """
        self.config = config or AntiCrawlConfig()
        self.request_count = 0
        self.last_request_time = 0.0
        self._request_times: List[float] = []
        self._semaphore = asyncio.Semaphore(self.config.concurrent_requests)

        logger.info(f"Initialized {self.__class__.__name__} with strategy: {self.config.strategy.value}")

    async def prepare_request(self, context: RequestContext) -> RequestContext:
        """
        Prepare a request with anti-detection measures.

        Args:
            context: Request context

        Returns:
            Updated request context
        """
        # Apply rate limiting
        await self._apply_rate_limit()

        # Apply random delay
        if self.config.use_random_delay:
            context.delay = self._calculate_delay()
            await asyncio.sleep(context.delay)

        # Set user agent
        if self.config.rotate_user_agent and not context.user_agent:
            context.user_agent = await self._get_user_agent()

        # Set headers
        if self.config.randomize_headers:
            context.headers = await self._build_headers(context)

        # Set proxy
        if self.config.use_proxies and not context.proxy:
            context.proxy = await self._get_proxy()

        # Set fingerprint
        if self.config.randomize_fingerprint and not context.fingerprint:
            context.fingerprint = await self._get_fingerprint()

        self.request_count += 1
        self.last_request_time = time.time()
        self._request_times.append(self.last_request_time)

        logger.debug(f"Prepared request {self.request_count} for {context.url}")
        return context

    async def execute_request(
        self,
        context: RequestContext,
        executor_func: callable
    ) -> Tuple[bool, Any]:
        """
        Execute a request with retry logic.

        Args:
            context: Request context
            executor_func: Async function to execute the request

        Returns:
            Tuple of (success, result)
        """
        async with self._semaphore:
            for attempt in range(context.max_retries):
                context.retry_count = attempt

                try:
                    # Prepare request
                    context = await self.prepare_request(context)

                    # Execute request
                    result = await executor_func(context)

                    logger.debug(f"Request successful for {context.url}")
                    return True, result

                except Exception as e:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{context.max_retries}): {str(e)}"
                    )

                    if attempt < context.max_retries - 1:
                        # Exponential backoff
                        retry_delay = self.config.retry_delay * (
                            self.config.backoff_factor ** attempt
                        )
                        await asyncio.sleep(retry_delay)

                        # Rotate proxy on failure
                        if self.config.use_proxies:
                            await self._mark_proxy_failed(context.proxy)
                            context.proxy = None
                    else:
                        logger.error(f"Request failed after {context.max_retries} attempts: {context.url}")
                        return False, None

        return False, None

    def _calculate_delay(self) -> float:
        """
        Calculate random delay between requests.

        Returns:
            Delay in seconds
        """
        strategy_multipliers = {
            CrawlStrategy.CONSERVATIVE: 1.5,
            CrawlStrategy.BALANCED: 1.0,
            CrawlStrategy.AGGRESSIVE: 0.5,
        }

        multiplier = strategy_multipliers[self.config.strategy]
        min_delay = self.config.min_delay * multiplier
        max_delay = self.config.max_delay * multiplier

        # Use normal distribution for more human-like delays
        mean = (min_delay + max_delay) / 2
        std = (max_delay - min_delay) / 4
        delay = random.gauss(mean, std)

        # Clamp to min/max
        return max(min_delay, min(max_delay, delay))

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting based on requests per minute."""
        if not self._request_times:
            return

        # Clean old request times (older than 1 minute)
        current_time = time.time()
        self._request_times = [
            t for t in self._request_times if current_time - t < 60
        ]

        # Check if we've exceeded rate limit
        if len(self._request_times) >= self.config.requests_per_minute:
            # Calculate how long to wait
            oldest_request = self._request_times[0]
            wait_time = 60 - (current_time - oldest_request)

            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

    async def _build_headers(self, context: RequestContext) -> Dict[str, str]:
        """
        Build HTTP headers with randomization.

        Args:
            context: Request context

        Returns:
            HTTP headers dictionary
        """
        headers = context.headers or {}

        # Set user agent
        if context.user_agent:
            headers["User-Agent"] = context.user_agent

        # Set accept language
        if "Accept-Language" not in headers:
            lang = random.choice(self.config.accept_languages)
            headers["Accept-Language"] = f"{lang},en;q=0.9"

        # Set accept
        if "Accept" not in headers:
            headers["Accept"] = (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            )

        # Set accept encoding
        if "Accept-Encoding" not in headers:
            headers["Accept-Encoding"] = "gzip, deflate, br"

        # Set connection
        if "Connection" not in headers:
            headers["Connection"] = "keep-alive"

        # Set upgrade insecure requests
        if "Upgrade-Insecure-Requests" not in headers:
            headers["Upgrade-Insecure-Requests"] = "1"

        # Set sec-fetch headers (modern browsers)
        if "Sec-Fetch-Dest" not in headers:
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = "none"
            headers["Sec-Fetch-User"] = "?1"

        # Randomize header order
        header_items = list(headers.items())
        random.shuffle(header_items)

        return dict(header_items)

    @abstractmethod
    async def _get_user_agent(self) -> str:
        """Get a user agent string. Must be implemented by subclass."""
        pass

    @abstractmethod
    async def _get_proxy(self) -> Optional[str]:
        """Get a proxy. Must be implemented by subclass."""
        pass

    @abstractmethod
    async def _get_fingerprint(self) -> Dict[str, Any]:
        """Get browser fingerprint. Must be implemented by subclass."""
        pass

    @abstractmethod
    async def _mark_proxy_failed(self, proxy: Optional[str]) -> None:
        """Mark a proxy as failed. Must be implemented by subclass."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """
        Get handler statistics.

        Returns:
            Statistics dictionary
        """
        current_time = time.time()
        recent_requests = [
            t for t in self._request_times if current_time - t < 60
        ]

        return {
            "total_requests": self.request_count,
            "requests_last_minute": len(recent_requests),
            "avg_requests_per_minute": (
                len(recent_requests) if recent_requests else 0
            ),
            "last_request_time": self.last_request_time,
            "strategy": self.config.strategy.value,
        }

    async def reset(self) -> None:
        """Reset handler state."""
        self.request_count = 0
        self.last_request_time = 0.0
        self._request_times.clear()
        logger.info(f"Reset {self.__class__.__name__}")

    async def close(self) -> None:
        """Cleanup resources."""
        logger.info(f"Closing {self.__class__.__name__}")
