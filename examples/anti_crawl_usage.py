"""
Example Usage of OmniSense Anti-Crawl System

This file demonstrates various ways to use the anti-crawl system.
"""

import asyncio
from loguru import logger

from omnisense.anti_crawl import AntiCrawlManager
from omnisense.anti_crawl.base import (
    AntiCrawlConfig,
    CrawlStrategy,
    RequestContext,
)
from omnisense.anti_crawl.utils import (
    ProxyConfig,
    FingerprintConfig,
    UserAgentConfig,
    CaptchaConfig,
)


async def example_basic_usage():
    """Basic usage with default settings."""
    print("\n=== Basic Usage ===\n")

    # Create manager with default settings
    manager = AntiCrawlManager()

    # Initialize
    await manager.initialize()

    # Prepare a request
    context = RequestContext(
        url="https://example.com",
        method="GET",
    )

    # Prepare request with anti-detection measures
    context = await manager.prepare_request(context)

    print(f"URL: {context.url}")
    print(f"User-Agent: {context.user_agent}")
    print(f"Proxy: {context.proxy}")
    print(f"Delay: {context.delay:.2f}s")
    print(f"Headers: {list(context.headers.keys())}")

    # Get statistics
    stats = manager.get_stats()
    print(f"\nStats: {stats}")

    await manager.close()


async def example_with_proxies():
    """Example with proxy rotation."""
    print("\n=== Proxy Rotation ===\n")

    # Configure proxies
    proxy_list = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        "http://proxy3.example.com:8080",
    ]

    proxy_config = ProxyConfig(
        initial_proxies=proxy_list,
        health_check_enabled=True,
        rotation_strategy="least_used",
    )

    config = AntiCrawlConfig(
        use_proxies=True,
        proxy_rotation_interval=5,  # Rotate every 5 requests
    )

    manager = AntiCrawlManager(
        config=config,
        proxy_config=proxy_config,
    )

    await manager.initialize()

    # Make multiple requests to see proxy rotation
    for i in range(10):
        context = RequestContext(url=f"https://example.com/page{i}")
        context = await manager.prepare_request(context)
        print(f"Request {i + 1}: Proxy = {context.proxy}")

    # Get proxy pool stats
    stats = manager.get_stats()
    print(f"\nProxy Pool Stats: {stats.get('proxy_pool', {})}")

    await manager.close()


async def example_with_fingerprinting():
    """Example with browser fingerprint randomization."""
    print("\n=== Fingerprint Randomization ===\n")

    fingerprint_config = FingerprintConfig(
        randomize_canvas=True,
        randomize_webgl=True,
        randomize_screen=True,
        randomize_fonts=True,
    )

    config = AntiCrawlConfig(
        randomize_fingerprint=True,
        fingerprint_rotation_interval=50,
    )

    manager = AntiCrawlManager(
        config=config,
        fingerprint_config=fingerprint_config,
    )

    await manager.initialize()

    # Get fingerprint
    fingerprint = await manager._get_fingerprint()
    print(f"Fingerprint ID: {fingerprint.get('id')}")
    print(f"Screen Resolution: {fingerprint.get('screen', {}).get('width')}x{fingerprint.get('screen', {}).get('height')}")
    print(f"WebGL Vendor: {fingerprint.get('webgl', {}).get('vendor')}")
    print(f"Hardware Cores: {fingerprint.get('hardware', {}).get('cpu_cores')}")
    print(f"Timezone: {fingerprint.get('timezone')}")

    await manager.close()


async def example_with_captcha():
    """Example with captcha solving."""
    print("\n=== Captcha Solving ===\n")

    # Note: You need a valid API key for this to work
    captcha_config = CaptchaConfig(
        service="2captcha",
        api_key="YOUR_API_KEY_HERE",
        timeout=120,
    )

    config = AntiCrawlConfig(
        solve_captcha=True,
        captcha_api_key="YOUR_API_KEY_HERE",
    )

    manager = AntiCrawlManager(
        config=config,
        captcha_config=captcha_config,
    )

    await manager.initialize()

    # Solve a reCAPTCHA v2
    print("Solving reCAPTCHA v2...")
    solution = await manager.solve_captcha(
        captcha_type="recaptcha_v2",
        site_key="6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        page_url="https://www.google.com/recaptcha/api2/demo",
    )

    if solution:
        print(f"Captcha solved! Token: {solution[:50]}...")
    else:
        print("Failed to solve captcha")

    await manager.close()


async def example_with_strategies():
    """Example with different crawling strategies."""
    print("\n=== Crawling Strategies ===\n")

    strategies = [
        CrawlStrategy.CONSERVATIVE,
        CrawlStrategy.BALANCED,
        CrawlStrategy.AGGRESSIVE,
    ]

    for strategy in strategies:
        print(f"\nTesting {strategy.value} strategy:")

        config = AntiCrawlConfig(
            strategy=strategy,
            min_delay=1.0,
            max_delay=3.0,
        )

        manager = AntiCrawlManager(config=config)
        await manager.initialize()

        # Make a few requests to see delays
        delays = []
        for _ in range(5):
            context = RequestContext(url="https://example.com")
            context = await manager.prepare_request(context)
            delays.append(context.delay)

        avg_delay = sum(delays) / len(delays)
        print(f"  Average delay: {avg_delay:.2f}s")
        print(f"  Delays: {[f'{d:.2f}' for d in delays]}")

        await manager.close()


async def example_custom_configuration():
    """Example with custom configuration."""
    print("\n=== Custom Configuration ===\n")

    config = AntiCrawlConfig(
        # Proxy settings
        use_proxies=False,

        # User agent settings
        rotate_user_agent=True,
        user_agent_types=["chrome", "firefox"],

        # Fingerprint settings
        randomize_fingerprint=True,
        fingerprint_rotation_interval=25,

        # Delay settings
        min_delay=2.0,
        max_delay=5.0,
        use_random_delay=True,

        # Header settings
        randomize_headers=True,
        accept_languages=["en-US", "en-GB"],

        # Retry settings
        max_retries=5,
        retry_delay=3.0,
        backoff_factor=1.5,

        # Strategy
        strategy=CrawlStrategy.BALANCED,

        # Rate limiting
        requests_per_minute=20,
        concurrent_requests=3,
    )

    manager = AntiCrawlManager(config=config)
    await manager.initialize()

    # Test request
    context = RequestContext(url="https://example.com")
    context = await manager.prepare_request(context)

    print(f"Configuration applied:")
    print(f"  User-Agent: {context.user_agent[:50]}...")
    print(f"  Delay: {context.delay:.2f}s")
    print(f"  Accept-Language: {context.headers.get('Accept-Language')}")
    print(f"  Max Retries: {context.max_retries}")

    await manager.close()


async def example_with_playwright():
    """Example with Playwright integration."""
    print("\n=== Playwright Integration ===\n")

    try:
        from playwright.async_api import async_playwright

        manager = AntiCrawlManager()
        await manager.initialize()

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)

            # Create context with proxy if available
            proxy = await manager._get_proxy()
            context_options = {}
            if proxy:
                context_options["proxy"] = {"server": proxy}

            context = await browser.new_context(**context_options)
            page = await context.new_page()

            # Apply fingerprint
            fingerprint = await manager._get_fingerprint()
            await manager.apply_fingerprint_to_playwright(page, fingerprint)

            print("Fingerprint applied to Playwright page")
            print(f"Fingerprint ID: {fingerprint.get('id')}")

            # Navigate to page
            # await page.goto("https://example.com")

            await browser.close()

        await manager.close()

    except ImportError:
        print("Playwright not installed. Install with: pip install playwright")


async def example_health_check():
    """Example health check and monitoring."""
    print("\n=== Health Check ===\n")

    # Setup with proxies
    proxy_config = ProxyConfig(
        initial_proxies=[
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
        ],
        health_check_enabled=True,
    )

    manager = AntiCrawlManager(
        config=AntiCrawlConfig(use_proxies=True),
        proxy_config=proxy_config,
    )

    await manager.initialize()

    # Perform health check
    health = await manager.health_check()
    print(f"Health Status: {health['status']}")
    print(f"Available Proxies: {health['available_proxies']}")
    print(f"Components: {health['components']}")

    # Get detailed stats
    stats = manager.get_stats()
    print(f"\nDetailed Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    await manager.close()


async def example_factory_function():
    """Example using factory function."""
    print("\n=== Factory Function ===\n")

    from omnisense.anti_crawl.manager import create_anti_crawl_manager

    # Create manager with factory function
    manager = create_anti_crawl_manager(
        strategy=CrawlStrategy.BALANCED,
        use_proxies=True,
        proxy_list=[
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
        ],
        solve_captcha=False,
    )

    await manager.initialize()

    print("Manager created with factory function")
    stats = manager.get_stats()
    print(f"Stats: {stats}")

    await manager.close()


async def main():
    """Run all examples."""
    # Run examples
    await example_basic_usage()
    await example_with_proxies()
    await example_with_fingerprinting()
    # await example_with_captcha()  # Requires API key
    await example_with_strategies()
    await example_custom_configuration()
    # await example_with_playwright()  # Requires playwright
    await example_health_check()
    await example_factory_function()


if __name__ == "__main__":
    # Configure logger
    logger.add(
        "anti_crawl_examples.log",
        rotation="10 MB",
        level="DEBUG",
    )

    print("OmniSense Anti-Crawl System Examples")
    print("=" * 50)

    # Run examples
    asyncio.run(main())

    print("\n" + "=" * 50)
    print("Examples completed!")
