"""
Playwright helper utilities
Provides common Playwright operations and anti-detection features
"""

import asyncio
import random
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.async_api import Page, Download
from fake_useragent import UserAgent

from omnisense.config import config


class PlaywrightHelper:
    """Helper class for Playwright operations with anti-detection features"""

    def __init__(self, logger):
        """
        Initialize Playwright helper

        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.user_agent = UserAgent()

    async def get_browser_context_options(self) -> Dict[str, Any]:
        """
        Get browser context options with anti-detection settings

        Returns:
            Dictionary of context options
        """
        # Generate random viewport
        viewport = self._get_random_viewport()

        # Get user agent
        user_agent = self._get_user_agent()

        # Context options
        options = {
            "viewport": viewport,
            "user_agent": user_agent,
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "permissions": ["geolocation", "notifications"],
            "geolocation": {"latitude": 39.9042, "longitude": 116.4074},  # Beijing
            "color_scheme": "light",
            "accept_downloads": True,
            "java_script_enabled": True,
            "has_touch": random.choice([True, False]),
            "is_mobile": False,
        }

        # Add extra headers
        options["extra_http_headers"] = {
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
        }

        return options

    def _get_random_viewport(self) -> Dict[str, int]:
        """
        Get random viewport size

        Returns:
            Dictionary with width and height
        """
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
        ]
        return random.choice(viewports)

    def _get_user_agent(self) -> str:
        """
        Get user agent string

        Returns:
            User agent string
        """
        if config.anti_crawl.user_agent_rotation:
            return self.user_agent.random
        else:
            # Default modern Chrome user agent
            return (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

    async def apply_stealth_scripts(self, page: Page) -> None:
        """
        Apply stealth scripts to evade detection

        Args:
            page: Playwright page instance
        """
        # Override navigator.webdriver
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Override chrome property
        await page.add_init_script("""
            window.chrome = {
                runtime: {},
            };
        """)

        # Override permissions
        await page.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        # Override plugins
        await page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)

        # Override languages
        await page.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en']
            });
        """)

        # Canvas fingerprint randomization
        if config.anti_crawl.fingerprint_random:
            await page.add_init_script("""
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.call(this, parameter);
                };
            """)

        self.logger.debug("Applied stealth scripts to page")

    async def random_mouse_move(self, page: Page) -> None:
        """
        Perform random mouse movements to simulate human behavior

        Args:
            page: Playwright page instance
        """
        try:
            viewport = page.viewport_size
            if not viewport:
                return

            # Random positions
            x1, y1 = random.randint(0, viewport["width"]), random.randint(0, viewport["height"])
            x2, y2 = random.randint(0, viewport["width"]), random.randint(0, viewport["height"])

            # Move mouse
            await page.mouse.move(x1, y1)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.move(x2, y2)

        except Exception as e:
            self.logger.debug(f"Random mouse move failed: {e}")

    async def random_scroll(self, page: Page) -> None:
        """
        Perform random scrolling to simulate human behavior

        Args:
            page: Playwright page instance
        """
        try:
            # Get page height
            height = await page.evaluate("document.body.scrollHeight")

            # Random scroll positions
            positions = [random.randint(0, height) for _ in range(3)]

            for pos in positions:
                await page.evaluate(f"window.scrollTo(0, {pos})")
                await asyncio.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            self.logger.debug(f"Random scroll failed: {e}")

    async def wait_random_time(self, min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
        """
        Wait for a random amount of time

        Args:
            min_seconds: Minimum wait time
            max_seconds: Maximum wait time
        """
        wait_time = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(wait_time)

    async def human_like_type(
        self,
        page: Page,
        selector: str,
        text: str,
        min_delay: int = 50,
        max_delay: int = 150,
    ) -> None:
        """
        Type text with human-like delays

        Args:
            page: Playwright page instance
            selector: Element selector
            text: Text to type
            min_delay: Minimum delay between keystrokes (ms)
            max_delay: Maximum delay between keystrokes (ms)
        """
        await page.click(selector)
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for char in text:
            await page.keyboard.type(char)
            delay = random.randint(min_delay, max_delay)
            await asyncio.sleep(delay / 1000)

    async def download_file(
        self,
        page: Page,
        url: str,
        save_path: str,
        max_size: Optional[int] = None,
    ) -> bool:
        """
        Download a file from URL

        Args:
            page: Playwright page instance
            url: File URL
            save_path: Path to save file
            max_size: Maximum file size in bytes

        Returns:
            True if download successful
        """
        try:
            # Start waiting for download
            async with page.expect_download() as download_info:
                # Navigate to download URL
                await page.goto(url)

            download: Download = await download_info.value

            # Check file size if max_size specified
            if max_size:
                # Note: Playwright doesn't provide file size before download
                # This is a limitation, we download first then check
                pass

            # Save file
            await download.save_as(save_path)

            # Check file size after download
            if max_size:
                file_size = Path(save_path).stat().st_size
                if file_size > max_size:
                    Path(save_path).unlink()  # Delete file
                    self.logger.warning(
                        f"File size {file_size} exceeds max {max_size}, deleted"
                    )
                    return False

            self.logger.debug(f"Downloaded file: {save_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to download file from {url}: {e}")
            return False

    async def handle_dialog(self, page: Page, accept: bool = True) -> None:
        """
        Set up dialog handler for alerts, confirms, prompts

        Args:
            page: Playwright page instance
            accept: Accept or dismiss dialogs
        """
        async def dialog_handler(dialog):
            self.logger.debug(f"Dialog: {dialog.type} - {dialog.message}")
            if accept:
                await dialog.accept()
            else:
                await dialog.dismiss()

        page.on("dialog", dialog_handler)

    async def intercept_requests(
        self,
        page: Page,
        block_resources: Optional[List[str]] = None,
    ) -> None:
        """
        Intercept and block certain resources to speed up page load

        Args:
            page: Playwright page instance
            block_resources: List of resource types to block
                             (e.g., ['image', 'stylesheet', 'font', 'media'])
        """
        if not block_resources:
            block_resources = []

        async def route_handler(route, request):
            if request.resource_type in block_resources:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)
        self.logger.debug(f"Blocking resources: {block_resources}")

    async def wait_for_network_idle(
        self,
        page: Page,
        timeout: int = 30000,
        idle_time: int = 500,
    ) -> bool:
        """
        Wait for network to become idle

        Args:
            page: Playwright page instance
            timeout: Maximum wait time in milliseconds
            idle_time: Time to consider network idle in milliseconds

        Returns:
            True if network became idle within timeout
        """
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            self.logger.debug(f"Network idle timeout: {e}")
            return False

    async def get_all_cookies(self, page: Page) -> List[Dict[str, Any]]:
        """
        Get all cookies from the page

        Args:
            page: Playwright page instance

        Returns:
            List of cookie dictionaries
        """
        return await page.context.cookies()

    async def set_cookies(self, page: Page, cookies: List[Dict[str, Any]]) -> None:
        """
        Set cookies on the page

        Args:
            page: Playwright page instance
            cookies: List of cookie dictionaries
        """
        await page.context.add_cookies(cookies)
        self.logger.debug(f"Set {len(cookies)} cookies")

    async def get_local_storage(self, page: Page) -> Dict[str, str]:
        """
        Get all localStorage items

        Args:
            page: Playwright page instance

        Returns:
            Dictionary of localStorage items
        """
        return await page.evaluate("""
            () => {
                let items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }
        """)

    async def set_local_storage(self, page: Page, items: Dict[str, str]) -> None:
        """
        Set localStorage items

        Args:
            page: Playwright page instance
            items: Dictionary of items to set
        """
        await page.evaluate("""
            (items) => {
                for (let key in items) {
                    localStorage.setItem(key, items[key]);
                }
            }
        """, items)

    async def take_element_screenshot(
        self,
        page: Page,
        selector: str,
        save_path: str,
    ) -> bool:
        """
        Take screenshot of a specific element

        Args:
            page: Playwright page instance
            selector: Element selector
            save_path: Path to save screenshot

        Returns:
            True if screenshot taken successfully
        """
        try:
            element = await page.query_selector(selector)
            if element:
                await element.screenshot(path=save_path)
                return True
            else:
                self.logger.warning(f"Element not found: {selector}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to take element screenshot: {e}")
            return False

    async def get_network_requests(self, page: Page) -> List[Dict[str, Any]]:
        """
        Capture network requests

        Args:
            page: Playwright page instance

        Returns:
            List of request information
        """
        requests = []

        def request_handler(request):
            requests.append({
                "url": request.url,
                "method": request.method,
                "headers": request.headers,
                "resource_type": request.resource_type,
            })

        page.on("request", request_handler)
        return requests

    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid

        Args:
            url: URL to check

        Returns:
            True if URL is valid
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    async def extract_links(self, page: Page, selector: str = "a") -> List[str]:
        """
        Extract all links from page

        Args:
            page: Playwright page instance
            selector: Link selector (default: 'a')

        Returns:
            List of URLs
        """
        try:
            links = await page.evaluate(f"""
                () => {{
                    return Array.from(document.querySelectorAll('{selector}'))
                        .map(a => a.href)
                        .filter(href => href);
                }}
            """)
            return [link for link in links if self.is_valid_url(link)]
        except Exception as e:
            self.logger.error(f"Failed to extract links: {e}")
            return []

    async def bypass_cloudflare(self, page: Page, max_wait: int = 30) -> bool:
        """
        Attempt to bypass Cloudflare challenge

        Args:
            page: Playwright page instance
            max_wait: Maximum wait time in seconds

        Returns:
            True if bypass successful
        """
        try:
            # Wait for Cloudflare challenge to complete
            await page.wait_for_load_state("networkidle", timeout=max_wait * 1000)

            # Check if still on Cloudflare page
            title = await page.title()
            if "cloudflare" in title.lower() or "checking your browser" in title.lower():
                self.logger.warning("Cloudflare challenge not bypassed")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error bypassing Cloudflare: {e}")
            return False

    async def solve_simple_captcha(self, page: Page) -> bool:
        """
        Attempt to solve simple captchas (placeholder for future implementation)

        Args:
            page: Playwright page instance

        Returns:
            True if captcha solved
        """
        # TODO: Implement captcha solving using service like 2captcha
        # This is a placeholder for future implementation
        self.logger.warning("Captcha solving not implemented")
        return False
