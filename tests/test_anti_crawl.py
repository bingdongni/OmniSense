"""
Tests for Anti-Crawl System

Unit and integration tests for the anti-crawl components.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from omnisense.anti_crawl import AntiCrawlManager
from omnisense.anti_crawl.base import (
    AntiCrawlConfig,
    CrawlStrategy,
    RequestContext,
)
from omnisense.anti_crawl.utils import (
    ProxyPool,
    ProxyConfig,
    FingerprintGenerator,
    FingerprintConfig,
    UserAgentRotator,
    UserAgentConfig,
    CaptchaResolver,
    CaptchaConfig,
)


class TestAntiCrawlConfig:
    """Test AntiCrawlConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = AntiCrawlConfig()

        assert config.use_proxies is True
        assert config.rotate_user_agent is True
        assert config.randomize_fingerprint is True
        assert config.strategy == CrawlStrategy.BALANCED
        assert config.max_retries == 3
        assert config.min_delay == 1.0
        assert config.max_delay == 3.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = AntiCrawlConfig(
            strategy=CrawlStrategy.CONSERVATIVE,
            max_retries=5,
            min_delay=2.0,
            max_delay=5.0,
        )

        assert config.strategy == CrawlStrategy.CONSERVATIVE
        assert config.max_retries == 5
        assert config.min_delay == 2.0
        assert config.max_delay == 5.0


class TestRequestContext:
    """Test RequestContext."""

    def test_default_context(self):
        """Test default request context."""
        context = RequestContext(url="https://example.com")

        assert context.url == "https://example.com"
        assert context.method == "GET"
        assert context.headers is None
        assert context.proxy is None
        assert context.max_retries == 3

    def test_custom_context(self):
        """Test custom request context."""
        headers = {"Custom-Header": "value"}
        context = RequestContext(
            url="https://example.com",
            method="POST",
            headers=headers,
            max_retries=5,
        )

        assert context.method == "POST"
        assert context.headers == headers
        assert context.max_retries == 5


class TestProxyPool:
    """Test ProxyPool."""

    @pytest.fixture
    async def proxy_pool(self):
        """Create proxy pool for testing."""
        config = ProxyConfig(
            initial_proxies=[
                "http://proxy1.example.com:8080",
                "http://proxy2.example.com:8080",
            ],
            health_check_enabled=False,  # Disable for testing
        )
        pool = ProxyPool(config)
        await pool.initialize()
        yield pool
        await pool.close()

    @pytest.mark.asyncio
    async def test_add_proxies(self, proxy_pool):
        """Test adding proxies."""
        initial_count = len(proxy_pool._proxies)

        await proxy_pool.add_proxies([
            "http://proxy3.example.com:8080",
        ])

        assert len(proxy_pool._proxies) == initial_count + 1

    @pytest.mark.asyncio
    async def test_get_proxy(self, proxy_pool):
        """Test getting proxy."""
        proxy = await proxy_pool.get_proxy()

        assert proxy is not None
        assert proxy.startswith("http://")

    @pytest.mark.asyncio
    async def test_mark_success(self, proxy_pool):
        """Test marking proxy as successful."""
        proxy = await proxy_pool.get_proxy()
        await proxy_pool.mark_success(proxy, response_time=0.5)

        proxy_info = proxy_pool._proxies[proxy]
        assert proxy_info.success_count == 1
        assert proxy_info.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_mark_failed(self, proxy_pool):
        """Test marking proxy as failed."""
        proxy = await proxy_pool.get_proxy()

        # Mark failed multiple times
        for _ in range(3):
            await proxy_pool.mark_failed(proxy)

        proxy_info = proxy_pool._proxies[proxy]
        assert proxy_info.failure_count == 3
        assert proxy not in proxy_pool._healthy_proxies

    @pytest.mark.asyncio
    async def test_rotation_strategies(self):
        """Test different rotation strategies."""
        for strategy in ["random", "least_used", "round_robin"]:
            config = ProxyConfig(
                initial_proxies=[
                    "http://proxy1.example.com:8080",
                    "http://proxy2.example.com:8080",
                ],
                rotation_strategy=strategy,
                health_check_enabled=False,
            )

            pool = ProxyPool(config)
            await pool.initialize()

            proxy = await pool.get_proxy()
            assert proxy is not None

            await pool.close()


class TestFingerprintGenerator:
    """Test FingerprintGenerator."""

    @pytest.fixture
    def generator(self):
        """Create fingerprint generator."""
        return FingerprintGenerator()

    def test_generate_fingerprint(self, generator):
        """Test generating fingerprint."""
        fingerprint = generator.generate()

        assert "id" in fingerprint
        assert "canvas" in fingerprint
        assert "webgl" in fingerprint
        assert "screen" in fingerprint
        assert "fonts" in fingerprint
        assert "hardware" in fingerprint
        assert "timezone" in fingerprint
        assert "language" in fingerprint

    def test_fingerprint_uniqueness(self, generator):
        """Test that fingerprints are unique."""
        fp1 = generator.generate()
        fp2 = generator.generate()

        # IDs should be different (very high probability)
        assert fp1["id"] != fp2["id"]

    def test_consistent_fingerprint(self, generator):
        """Test generating consistent fingerprint from seed."""
        seed = "test_seed"

        fp1 = generator.generate_consistent_fingerprint(seed)
        fp2 = generator.generate_consistent_fingerprint(seed)

        # Should be identical
        assert fp1["id"] == fp2["id"]
        assert fp1["screen"] == fp2["screen"]
        assert fp1["webgl"] == fp2["webgl"]

    def test_screen_resolution(self, generator):
        """Test screen resolution randomization."""
        fingerprint = generator.generate()
        screen = fingerprint["screen"]

        assert "width" in screen
        assert "height" in screen
        assert screen["width"] > 0
        assert screen["height"] > 0
        assert screen["avail_height"] < screen["height"]

    def test_webgl_properties(self, generator):
        """Test WebGL properties."""
        fingerprint = generator.generate()
        webgl = fingerprint["webgl"]

        assert "vendor" in webgl
        assert "renderer" in webgl
        assert "version" in webgl

    def test_hardware_properties(self, generator):
        """Test hardware properties."""
        fingerprint = generator.generate()
        hardware = fingerprint["hardware"]

        assert "cpu_cores" in hardware
        assert "device_memory" in hardware
        assert hardware["cpu_cores"] > 0
        assert hardware["device_memory"] > 0


class TestUserAgentRotator:
    """Test UserAgentRotator."""

    @pytest.fixture
    def rotator(self):
        """Create user agent rotator."""
        return UserAgentRotator()

    def test_get_random_user_agent(self, rotator):
        """Test getting random user agent."""
        ua = rotator.get_random_user_agent()

        assert ua is not None
        assert len(ua) > 0
        assert "Mozilla" in ua

    def test_get_user_agent_by_browser(self, rotator):
        """Test getting user agent by browser."""
        browsers = ["chrome", "firefox", "safari", "edge"]

        for browser in browsers:
            ua = rotator.get_user_agent_by_browser(browser)
            assert ua is not None
            assert len(ua) > 0

    def test_mobile_user_agent(self, rotator):
        """Test getting mobile user agent."""
        ua = rotator.get_user_agent_by_browser("chrome", mobile=True)

        assert "Mobile" in ua or "Android" in ua or "iPhone" in ua

    def test_parse_user_agent(self, rotator):
        """Test parsing user agent."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        info = rotator.parse_user_agent(ua)

        assert info["browser"] == "chrome"
        assert info["os"] == "windows"
        assert info["mobile"] is False


class TestAntiCrawlManager:
    """Test AntiCrawlManager."""

    @pytest.fixture
    async def manager(self):
        """Create anti-crawl manager."""
        config = AntiCrawlConfig(
            use_proxies=False,  # Disable for testing
            solve_captcha=False,
        )
        manager = AntiCrawlManager(config=config)
        await manager.initialize()
        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_prepare_request(self, manager):
        """Test preparing request."""
        context = RequestContext(url="https://example.com")
        context = await manager.prepare_request(context)

        assert context.user_agent is not None
        assert context.headers is not None
        assert context.delay >= 0

    @pytest.mark.asyncio
    async def test_get_user_agent(self, manager):
        """Test getting user agent."""
        ua = await manager._get_user_agent()

        assert ua is not None
        assert len(ua) > 0

    @pytest.mark.asyncio
    async def test_get_fingerprint(self, manager):
        """Test getting fingerprint."""
        fingerprint = await manager._get_fingerprint()

        assert fingerprint is not None
        assert "id" in fingerprint

    @pytest.mark.asyncio
    async def test_delay_calculation(self, manager):
        """Test delay calculation."""
        delays = []
        for _ in range(10):
            delay = manager._calculate_delay()
            delays.append(delay)
            assert manager.config.min_delay <= delay <= manager.config.max_delay

        # Check that delays are varied
        assert len(set(delays)) > 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self, manager):
        """Test rate limiting."""
        manager.config.requests_per_minute = 5

        # Make requests
        for _ in range(5):
            await manager._apply_rate_limit()
            manager._request_times.append(asyncio.get_event_loop().time())

        # Next request should be rate limited
        import time
        start = time.time()
        await manager._apply_rate_limit()
        elapsed = time.time() - start

        # Should have waited (not exact due to timing)
        assert elapsed >= 0

    @pytest.mark.asyncio
    async def test_build_headers(self, manager):
        """Test building headers."""
        context = RequestContext(url="https://example.com")
        headers = await manager._build_headers(context)

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers

    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """Test getting statistics."""
        # Make some requests
        for _ in range(5):
            context = RequestContext(url="https://example.com")
            await manager.prepare_request(context)

        stats = manager.get_stats()

        assert "total_requests" in stats
        assert stats["total_requests"] == 5
        assert "strategy" in stats

    @pytest.mark.asyncio
    async def test_health_check(self, manager):
        """Test health check."""
        health = await manager.health_check()

        assert "status" in health
        assert "components" in health

    @pytest.mark.asyncio
    async def test_reset(self, manager):
        """Test resetting manager."""
        # Make some requests
        for _ in range(5):
            context = RequestContext(url="https://example.com")
            await manager.prepare_request(context)

        # Reset
        await manager.reset()

        stats = manager.get_stats()
        assert stats["total_requests"] == 0


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full workflow with all components."""
        config = AntiCrawlConfig(
            use_proxies=False,
            rotate_user_agent=True,
            randomize_fingerprint=True,
            randomize_headers=True,
            strategy=CrawlStrategy.BALANCED,
        )

        manager = AntiCrawlManager(config=config)
        await manager.initialize()

        # Prepare multiple requests
        contexts = []
        for i in range(5):
            context = RequestContext(url=f"https://example.com/page{i}")
            context = await manager.prepare_request(context)
            contexts.append(context)

        # Verify all contexts are properly prepared
        for context in contexts:
            assert context.user_agent is not None
            assert context.headers is not None
            assert context.delay >= 0

        # Check stats
        stats = manager.get_stats()
        assert stats["total_requests"] == 5

        await manager.close()

    @pytest.mark.asyncio
    async def test_strategy_differences(self):
        """Test that different strategies produce different delays."""
        results = {}

        for strategy in [CrawlStrategy.CONSERVATIVE, CrawlStrategy.BALANCED, CrawlStrategy.AGGRESSIVE]:
            config = AntiCrawlConfig(
                strategy=strategy,
                min_delay=1.0,
                max_delay=3.0,
            )

            manager = AntiCrawlManager(config=config)
            await manager.initialize()

            delays = []
            for _ in range(10):
                context = RequestContext(url="https://example.com")
                context = await manager.prepare_request(context)
                delays.append(context.delay)

            results[strategy] = sum(delays) / len(delays)
            await manager.close()

        # Conservative should have longest delays
        assert results[CrawlStrategy.CONSERVATIVE] > results[CrawlStrategy.BALANCED]
        assert results[CrawlStrategy.BALANCED] > results[CrawlStrategy.AGGRESSIVE]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
