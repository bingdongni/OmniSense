"""
Practical Integration Example

Shows how to integrate the anti-crawl system with actual HTTP requests
using aiohttp and Playwright.
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from loguru import logger

from omnisense.anti_crawl import AntiCrawlManager
from omnisense.anti_crawl.base import (
    AntiCrawlConfig,
    CrawlStrategy,
    RequestContext,
)
from omnisense.anti_crawl.utils import ProxyConfig


class AntiCrawlHTTPClient:
    """
    HTTP client with built-in anti-crawl capabilities.

    Wraps aiohttp with automatic anti-detection measures.
    """

    def __init__(
        self,
        manager: Optional[AntiCrawlManager] = None,
        config: Optional[AntiCrawlConfig] = None,
    ):
        """
        Initialize HTTP client.

        Args:
            manager: Anti-crawl manager (creates default if None)
            config: Anti-crawl configuration
        """
        self.manager = manager or AntiCrawlManager(config)
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize client."""
        await self.manager.initialize()
        self._session = aiohttp.ClientSession()
        logger.info("AntiCrawlHTTPClient initialized")

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Optional[aiohttp.ClientResponse]:
        """
        Perform GET request with anti-detection.

        Args:
            url: URL to request
            headers: Additional headers
            **kwargs: Additional aiohttp arguments

        Returns:
            Response or None on failure
        """
        context = RequestContext(
            url=url,
            method="GET",
            headers=headers,
        )

        return await self._execute_request(context, **kwargs)

    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Optional[aiohttp.ClientResponse]:
        """
        Perform POST request with anti-detection.

        Args:
            url: URL to request
            data: Form data
            json: JSON data
            headers: Additional headers
            **kwargs: Additional aiohttp arguments

        Returns:
            Response or None on failure
        """
        context = RequestContext(
            url=url,
            method="POST",
            headers=headers,
        )

        return await self._execute_request(context, data=data, json=json, **kwargs)

    async def _execute_request(
        self,
        context: RequestContext,
        **kwargs: Any,
    ) -> Optional[aiohttp.ClientResponse]:
        """
        Execute HTTP request with retry logic.

        Args:
            context: Request context
            **kwargs: Additional request arguments

        Returns:
            Response or None
        """
        async def request_executor(ctx: RequestContext) -> aiohttp.ClientResponse:
            """Execute the actual request."""
            # Build request kwargs
            request_kwargs = {
                "headers": ctx.headers,
                "timeout": aiohttp.ClientTimeout(total=30),
                **kwargs,
            }

            # Add proxy if available
            if ctx.proxy:
                request_kwargs["proxy"] = ctx.proxy

            # Execute request
            response = await self._session.request(
                method=ctx.method,
                url=ctx.url,
                **request_kwargs,
            )

            # Mark proxy as successful
            if ctx.proxy:
                await self.manager.proxy_pool.mark_success(
                    ctx.proxy,
                    response_time=0.0  # Could track actual response time
                )

            return response

        # Execute with retry logic
        success, result = await self.manager.execute_request(context, request_executor)

        if success:
            return result
        else:
            logger.error(f"Failed to fetch {context.url}")
            return None

    async def close(self):
        """Cleanup resources."""
        if self._session:
            await self._session.close()
        await self.manager.close()
        logger.info("AntiCrawlHTTPClient closed")


async def example_http_client():
    """Example using the HTTP client."""
    print("\n=== HTTP Client Example ===\n")

    # Create client
    config = AntiCrawlConfig(
        use_proxies=False,  # Set to True and add proxies in production
        strategy=CrawlStrategy.BALANCED,
    )

    client = AntiCrawlHTTPClient(config=config)
    await client.initialize()

    # Make requests
    urls = [
        "https://httpbin.org/user-agent",
        "https://httpbin.org/headers",
        "https://httpbin.org/get",
    ]

    for url in urls:
        print(f"\nFetching: {url}")
        response = await client.get(url)

        if response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Response: {data}")
        else:
            print("Failed to fetch")

    # Get statistics
    stats = client.manager.get_stats()
    print(f"\nStatistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Strategy: {stats['strategy']}")

    await client.close()


async def example_with_playwright():
    """Example using Playwright with anti-detection."""
    print("\n=== Playwright Example ===\n")

    try:
        from playwright.async_api import async_playwright

        # Create manager
        config = AntiCrawlConfig(
            randomize_fingerprint=True,
            strategy=CrawlStrategy.BALANCED,
        )

        manager = AntiCrawlManager(config=config)
        await manager.initialize()

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )

            # Get user agent
            user_agent = await manager._get_user_agent()

            # Create context
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={
                    "width": 1920,
                    "height": 1080,
                },
            )

            # Create page
            page = await context.new_page()

            # Apply fingerprint
            await manager.apply_fingerprint_to_playwright(page)

            # Navigate
            print("Navigating to test page...")
            await page.goto("https://bot.sannysoft.com/")

            # Wait a bit
            await asyncio.sleep(3)

            # Take screenshot
            screenshot_path = "anti_detection_test.png"
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved: {screenshot_path}")

            # Get some properties
            props = await page.evaluate("""
                () => ({
                    userAgent: navigator.userAgent,
                    webdriver: navigator.webdriver,
                    languages: navigator.languages,
                    platform: navigator.platform,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory,
                })
            """)

            print(f"\nBrowser Properties:")
            for key, value in props.items():
                print(f"  {key}: {value}")

            await browser.close()

        await manager.close()

    except ImportError:
        print("Playwright not installed. Install with: pip install playwright")
        print("Then run: playwright install")


async def example_scraping_workflow():
    """Example of a complete scraping workflow."""
    print("\n=== Complete Scraping Workflow ===\n")

    # Configuration
    config = AntiCrawlConfig(
        use_proxies=False,
        rotate_user_agent=True,
        randomize_fingerprint=True,
        randomize_headers=True,
        min_delay=1.0,
        max_delay=2.0,
        strategy=CrawlStrategy.BALANCED,
        requests_per_minute=20,
        max_retries=3,
    )

    # Create client
    client = AntiCrawlHTTPClient(config=config)
    await client.initialize()

    # List of pages to scrape
    pages = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/xml",
    ]

    results = []

    print("Starting scraping workflow...")

    for i, url in enumerate(pages, 1):
        print(f"\n[{i}/{len(pages)}] Scraping: {url}")

        try:
            response = await client.get(url)

            if response:
                content = await response.text()
                results.append({
                    "url": url,
                    "status": response.status,
                    "content_length": len(content),
                    "content_type": response.headers.get("Content-Type"),
                })
                print(f"  ✓ Success: {response.status}, {len(content)} bytes")
            else:
                print(f"  ✗ Failed")

        except Exception as e:
            print(f"  ✗ Error: {str(e)}")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Total pages: {len(pages)}")
    print(f"Successful: {len(results)}")
    print(f"Failed: {len(pages) - len(results)}")

    # Statistics
    stats = client.manager.get_stats()
    print(f"\nPerformance Statistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Requests last minute: {stats['requests_last_minute']}")
    print(f"  Strategy: {stats['strategy']}")

    await client.close()


async def example_with_session_consistency():
    """Example maintaining session consistency."""
    print("\n=== Session Consistency Example ===\n")

    # Create manager
    manager = AntiCrawlManager()
    await manager.initialize()

    # Get consistent fingerprint
    fingerprint = manager.get_current_fingerprint()
    print(f"Session Fingerprint ID: {fingerprint.get('id', 'none')}")

    # Create HTTP client
    client = AntiCrawlHTTPClient(manager=manager)
    await client.initialize()

    # Make multiple requests with same fingerprint
    print("\nMaking requests with consistent identity:")

    for i in range(3):
        response = await client.get("https://httpbin.org/user-agent")
        if response:
            data = await response.json()
            print(f"  Request {i+1}: {data.get('user-agent', 'N/A')[:50]}...")

    print(f"\nSame fingerprint maintained: {manager.get_current_fingerprint().get('id')}")

    await client.close()


async def example_with_error_handling():
    """Example with comprehensive error handling."""
    print("\n=== Error Handling Example ===\n")

    client = AntiCrawlHTTPClient()
    await client.initialize()

    # URLs with different scenarios
    urls = [
        "https://httpbin.org/status/200",  # Success
        "https://httpbin.org/status/404",  # Not found
        "https://httpbin.org/status/500",  # Server error
        "https://httpbin.org/delay/10",    # Timeout
        "https://invalid-domain-12345.com",  # Invalid domain
    ]

    for url in urls:
        print(f"\nTesting: {url}")

        try:
            response = await client.get(url)

            if response:
                print(f"  Status: {response.status}")

                if response.status == 200:
                    print("  ✓ Success")
                elif response.status == 404:
                    print("  ⚠ Not found")
                elif response.status >= 500:
                    print("  ✗ Server error")

            else:
                print("  ✗ Request failed after retries")

        except asyncio.TimeoutError:
            print("  ✗ Timeout")
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__}")

    await client.close()


async def main():
    """Run all examples."""
    # Run examples
    await example_http_client()
    await example_scraping_workflow()
    await example_with_session_consistency()
    await example_with_error_handling()

    # Playwright example (optional)
    # await example_with_playwright()


if __name__ == "__main__":
    # Configure logger
    logger.add(
        "anti_crawl_integration.log",
        rotation="10 MB",
        level="INFO",
    )

    print("=" * 60)
    print("OmniSense Anti-Crawl System - Practical Integration")
    print("=" * 60)

    # Run examples
    asyncio.run(main())

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
