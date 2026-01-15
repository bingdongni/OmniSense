"""
Proxy Pool Management

Manages a pool of proxies with health checking, rotation, and failover.
Supports HTTP, HTTPS, SOCKS4, and SOCKS5 proxies.
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
from enum import Enum

import aiohttp
from loguru import logger


class ProxyType(Enum):
    """Proxy protocol types"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(Enum):
    """Proxy status"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"


@dataclass
class ProxyInfo:
    """Information about a proxy"""
    url: str
    protocol: ProxyType
    status: ProxyStatus = ProxyStatus.UNKNOWN
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    last_checked: float = 0.0
    avg_response_time: float = 0.0
    consecutive_failures: int = 0
    total_bytes: int = 0


@dataclass
class ProxyConfig:
    """Configuration for proxy pool"""
    # Initial proxies
    initial_proxies: List[str] = field(default_factory=list)

    # Health check settings
    health_check_enabled: bool = True
    health_check_url: str = "https://httpbin.org/ip"
    health_check_timeout: float = 10.0
    health_check_interval: int = 300  # seconds
    max_consecutive_failures: int = 3

    # Pool settings
    min_pool_size: int = 5
    max_pool_size: int = 100
    rotation_strategy: str = "least_used"  # least_used, random, round_robin

    # Retry settings
    max_proxy_retries: int = 3
    proxy_retry_delay: float = 1.0


class ProxyPool:
    """
    Manages a pool of proxies with automatic health checking and rotation.

    Features:
    - Automatic proxy health checking
    - Multiple rotation strategies
    - Failure tracking and auto-removal
    - Performance metrics
    """

    def __init__(self, config: Optional[ProxyConfig] = None):
        """
        Initialize proxy pool.

        Args:
            config: Proxy pool configuration
        """
        self.config = config or ProxyConfig()
        self._proxies: Dict[str, ProxyInfo] = {}
        self._healthy_proxies: Set[str] = set()
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info("ProxyPool initialized")

    async def initialize(self) -> None:
        """Initialize the proxy pool."""
        # Create HTTP session
        self._session = aiohttp.ClientSession()

        # Add initial proxies
        if self.config.initial_proxies:
            await self.add_proxies(self.config.initial_proxies)

        # Start health check task
        if self.config.health_check_enabled:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("Started proxy health check task")

        logger.info(f"ProxyPool initialized with {len(self._proxies)} proxies")

    async def add_proxies(self, proxies: List[str]) -> None:
        """
        Add proxies to the pool.

        Args:
            proxies: List of proxy URLs
        """
        async with self._lock:
            for proxy_url in proxies:
                if proxy_url not in self._proxies:
                    protocol = self._parse_proxy_protocol(proxy_url)
                    proxy_info = ProxyInfo(
                        url=proxy_url,
                        protocol=protocol,
                    )
                    self._proxies[proxy_url] = proxy_info

                    # Add to healthy set initially
                    self._healthy_proxies.add(proxy_url)

                    logger.debug(f"Added proxy: {proxy_url}")

        logger.info(f"Added {len(proxies)} proxies to pool (total: {len(self._proxies)})")

    async def remove_proxy(self, proxy_url: str) -> None:
        """
        Remove a proxy from the pool.

        Args:
            proxy_url: Proxy URL to remove
        """
        async with self._lock:
            if proxy_url in self._proxies:
                del self._proxies[proxy_url]
                self._healthy_proxies.discard(proxy_url)
                logger.info(f"Removed proxy: {proxy_url}")

    async def get_proxy(self) -> Optional[str]:
        """
        Get a proxy from the pool.

        Returns:
            Proxy URL or None if no proxies available
        """
        async with self._lock:
            if not self._healthy_proxies:
                logger.warning("No healthy proxies available")
                return None

            # Select proxy based on strategy
            if self.config.rotation_strategy == "random":
                proxy_url = random.choice(list(self._healthy_proxies))
            elif self.config.rotation_strategy == "least_used":
                proxy_url = self._get_least_used_proxy()
            elif self.config.rotation_strategy == "round_robin":
                proxy_url = self._get_round_robin_proxy()
            else:
                proxy_url = random.choice(list(self._healthy_proxies))

            # Update usage stats
            if proxy_url:
                proxy_info = self._proxies[proxy_url]
                proxy_info.last_used = time.time()
                logger.debug(f"Selected proxy: {proxy_url}")

            return proxy_url

    async def mark_success(self, proxy_url: str, response_time: float = 0.0) -> None:
        """
        Mark a proxy as successful.

        Args:
            proxy_url: Proxy URL
            response_time: Response time in seconds
        """
        async with self._lock:
            if proxy_url in self._proxies:
                proxy_info = self._proxies[proxy_url]
                proxy_info.success_count += 1
                proxy_info.consecutive_failures = 0
                proxy_info.status = ProxyStatus.HEALTHY

                # Update average response time
                if proxy_info.avg_response_time == 0:
                    proxy_info.avg_response_time = response_time
                else:
                    proxy_info.avg_response_time = (
                        proxy_info.avg_response_time * 0.8 + response_time * 0.2
                    )

                self._healthy_proxies.add(proxy_url)
                logger.debug(f"Marked proxy as successful: {proxy_url}")

    async def mark_failed(self, proxy_url: str) -> None:
        """
        Mark a proxy as failed.

        Args:
            proxy_url: Proxy URL
        """
        async with self._lock:
            if proxy_url in self._proxies:
                proxy_info = self._proxies[proxy_url]
                proxy_info.failure_count += 1
                proxy_info.consecutive_failures += 1

                logger.debug(
                    f"Marked proxy as failed: {proxy_url} "
                    f"(consecutive failures: {proxy_info.consecutive_failures})"
                )

                # Remove from healthy set if too many failures
                if proxy_info.consecutive_failures >= self.config.max_consecutive_failures:
                    proxy_info.status = ProxyStatus.FAILED
                    self._healthy_proxies.discard(proxy_url)
                    logger.warning(f"Proxy marked as failed after {proxy_info.consecutive_failures} failures: {proxy_url}")

    def _get_least_used_proxy(self) -> Optional[str]:
        """
        Get the least used proxy.

        Returns:
            Proxy URL or None
        """
        if not self._healthy_proxies:
            return None

        # Find proxy with lowest usage
        least_used = min(
            self._healthy_proxies,
            key=lambda p: self._proxies[p].success_count + self._proxies[p].failure_count
        )

        return least_used

    def _get_round_robin_proxy(self) -> Optional[str]:
        """
        Get proxy using round-robin strategy.

        Returns:
            Proxy URL or None
        """
        if not self._healthy_proxies:
            return None

        healthy_list = list(self._healthy_proxies)
        proxy_url = healthy_list[self._current_index % len(healthy_list)]
        self._current_index += 1

        return proxy_url

    async def _health_check_loop(self) -> None:
        """Continuously check proxy health."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._check_all_proxies()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")

    async def _check_all_proxies(self) -> None:
        """Check health of all proxies."""
        if not self._proxies:
            return

        logger.info(f"Starting health check for {len(self._proxies)} proxies")

        tasks = []
        for proxy_url in list(self._proxies.keys()):
            tasks.append(self._check_proxy_health(proxy_url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy_count = sum(1 for r in results if r is True)
        logger.info(f"Health check complete: {healthy_count}/{len(self._proxies)} proxies healthy")

    async def _check_proxy_health(self, proxy_url: str) -> bool:
        """
        Check health of a single proxy.

        Args:
            proxy_url: Proxy URL

        Returns:
            True if healthy, False otherwise
        """
        if not self._session:
            return False

        try:
            start_time = time.time()

            async with self._session.get(
                self.config.health_check_url,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=self.config.health_check_timeout),
            ) as response:
                if response.status == 200:
                    response_time = time.time() - start_time
                    await self.mark_success(proxy_url, response_time)

                    async with self._lock:
                        proxy_info = self._proxies[proxy_url]
                        proxy_info.last_checked = time.time()

                    return True

        except Exception as e:
            logger.debug(f"Health check failed for {proxy_url}: {str(e)}")
            await self.mark_failed(proxy_url)

        return False

    def _parse_proxy_protocol(self, proxy_url: str) -> ProxyType:
        """
        Parse proxy protocol from URL.

        Args:
            proxy_url: Proxy URL

        Returns:
            Proxy type
        """
        parsed = urlparse(proxy_url)
        scheme = parsed.scheme.lower()

        if scheme == "http":
            return ProxyType.HTTP
        elif scheme == "https":
            return ProxyType.HTTPS
        elif scheme == "socks4":
            return ProxyType.SOCKS4
        elif scheme == "socks5":
            return ProxyType.SOCKS5
        else:
            return ProxyType.HTTP

    def get_stats(self) -> Dict[str, any]:
        """
        Get proxy pool statistics.

        Returns:
            Statistics dictionary
        """
        total_proxies = len(self._proxies)
        healthy_proxies = len(self._healthy_proxies)

        # Calculate success rate
        total_success = sum(p.success_count for p in self._proxies.values())
        total_failure = sum(p.failure_count for p in self._proxies.values())
        total_requests = total_success + total_failure
        success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0

        # Get average response time
        avg_response_times = [
            p.avg_response_time
            for p in self._proxies.values()
            if p.avg_response_time > 0
        ]
        avg_response_time = (
            sum(avg_response_times) / len(avg_response_times)
            if avg_response_times else 0
        )

        return {
            "total_proxies": total_proxies,
            "healthy_proxies": healthy_proxies,
            "unhealthy_proxies": total_proxies - healthy_proxies,
            "total_requests": total_requests,
            "success_rate": round(success_rate, 2),
            "avg_response_time": round(avg_response_time, 3),
            "rotation_strategy": self.config.rotation_strategy,
        }

    async def health_check(self) -> Dict[str, any]:
        """
        Perform immediate health check.

        Returns:
            Health check results
        """
        await self._check_all_proxies()
        return {
            "status": "healthy" if self._healthy_proxies else "unhealthy",
            "available_proxies": len(self._healthy_proxies),
            "total_proxies": len(self._proxies),
        }

    async def reset_stats(self) -> None:
        """Reset proxy statistics."""
        async with self._lock:
            for proxy_info in self._proxies.values():
                proxy_info.success_count = 0
                proxy_info.failure_count = 0
                proxy_info.consecutive_failures = 0
                proxy_info.avg_response_time = 0.0

        logger.info("Reset proxy statistics")

    async def close(self) -> None:
        """Cleanup resources."""
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close HTTP session
        if self._session:
            await self._session.close()

        logger.info("ProxyPool closed")


# Utility functions
def parse_proxy_list_file(file_path: str) -> List[str]:
    """
    Parse a file containing proxy URLs (one per line).

    Args:
        file_path: Path to proxy list file

    Returns:
        List of proxy URLs
    """
    proxies = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)

        logger.info(f"Loaded {len(proxies)} proxies from {file_path}")
    except Exception as e:
        logger.error(f"Failed to load proxies from {file_path}: {str(e)}")

    return proxies


def format_proxy_url(host: str, port: int, protocol: str = "http", username: Optional[str] = None, password: Optional[str] = None) -> str:
    """
    Format proxy URL.

    Args:
        host: Proxy host
        port: Proxy port
        protocol: Proxy protocol (http, https, socks4, socks5)
        username: Optional username
        password: Optional password

    Returns:
        Formatted proxy URL
    """
    if username and password:
        return f"{protocol}://{username}:{password}@{host}:{port}"
    else:
        return f"{protocol}://{host}:{port}"
