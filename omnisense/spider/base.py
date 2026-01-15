"""
Base spider class with Playwright integration
Provides core functionality for all platform-specific spiders
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from contextlib import asynccontextmanager

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from omnisense.config import config
from omnisense.utils.logger import get_logger
from omnisense.spider.utils.playwright_helper import PlaywrightHelper
from omnisense.spider.utils.parser import ContentParser


class BaseSpider(ABC):
    """
    Base spider class with Playwright integration

    Features:
    - Async Playwright browser automation
    - Cookie management and session persistence
    - Configurable timeouts and retries
    - Media download support
    - Rate limiting
    - Error handling and logging
    - Abstract methods for platform-specific implementation
    """

    def __init__(
        self,
        platform: str,
        headless: bool = True,
        proxy: Optional[str] = None,
        user_data_dir: Optional[Path] = None,
    ):
        """
        Initialize base spider

        Args:
            platform: Platform name (e.g., 'douyin', 'xiaohongshu')
            headless: Run browser in headless mode
            proxy: Proxy server URL
            user_data_dir: Directory for user data and cookies
        """
        self.platform = platform
        self.headless = headless
        self.proxy = proxy
        self.user_data_dir = user_data_dir or config.cache_dir / "cookies" / platform
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        # Logger
        self.logger = get_logger(f"spider.{platform}")

        # Browser instances
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # Helpers
        self.helper = PlaywrightHelper(self.logger)
        self.parser = ContentParser(self.logger)

        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0
        self._rate_limit_window_start = time.time()

        # Session management
        self._cookies_file = self.user_data_dir / "cookies.json"
        self._session_file = self.user_data_dir / "session.json"
        self._is_logged_in = False

        # Download tracking
        self._downloaded_urls: Set[str] = set()
        self._download_dir = config.cache_dir / "downloads" / platform
        self._download_dir.mkdir(parents=True, exist_ok=True)

        # Retry configuration
        self.max_retries = config.anti_crawl.max_retries
        self.timeout = config.spider.timeout * 1000  # Convert to milliseconds

        # Request delays
        self.request_delay_min = config.anti_crawl.request_delay_min
        self.request_delay_max = config.anti_crawl.request_delay_max

        self.logger.info(f"Initialized {platform} spider")

    @abstractmethod
    async def login(self, username: str, password: str) -> bool:
        """
        Login to the platform

        Args:
            username: Username or phone number
            password: Password

        Returns:
            True if login successful
        """
        pass

    @abstractmethod
    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for content by keyword

        Args:
            keyword: Search keyword
            max_results: Maximum number of results to return

        Returns:
            List of content items
        """
        pass

    @abstractmethod
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile information

        Args:
            user_id: User ID

        Returns:
            User profile data
        """
        pass

    @abstractmethod
    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """
        Get posts from a user

        Args:
            user_id: User ID
            max_posts: Maximum number of posts to retrieve

        Returns:
            List of post items
        """
        pass

    @abstractmethod
    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a post

        Args:
            post_id: Post ID

        Returns:
            Post detail data
        """
        pass

    @abstractmethod
    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Get comments for a post

        Args:
            post_id: Post ID
            max_comments: Maximum number of comments to retrieve

        Returns:
            List of comment items
        """
        pass

    async def start(self) -> None:
        """Start the browser and create context"""
        try:
            self.logger.info("Starting browser...")

            # Launch Playwright
            self._playwright = await async_playwright().start()

            # Browser launch options
            launch_options = {
                "headless": self.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            }

            if self.proxy:
                launch_options["proxy"] = {"server": self.proxy}

            # Launch browser
            self._browser = await self._playwright.chromium.launch(**launch_options)

            # Create context with anti-detection settings
            context_options = await self.helper.get_browser_context_options()
            if self.proxy:
                context_options["proxy"] = {"server": self.proxy}

            self._context = await self._browser.new_context(**context_options)

            # Load cookies if exists
            if self._cookies_file.exists():
                await self._load_cookies()

            # Create page
            self._page = await self._context.new_page()

            # Apply stealth scripts
            await self.helper.apply_stealth_scripts(self._page)

            # Set default timeout
            self._page.set_default_timeout(self.timeout)

            self.logger.info("Browser started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            raise

    async def stop(self) -> None:
        """Stop the browser and clean up resources"""
        try:
            self.logger.info("Stopping browser...")

            # Save cookies before closing
            if self._context and config.spider.cookie_persist:
                await self._save_cookies()

            # Close browser
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()

            self.logger.info("Browser stopped")

        except Exception as e:
            self.logger.error(f"Error stopping browser: {e}")

    async def _load_cookies(self) -> None:
        """Load cookies from file"""
        try:
            with open(self._cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            await self._context.add_cookies(cookies)
            self.logger.info(f"Loaded {len(cookies)} cookies")
        except Exception as e:
            self.logger.error(f"Failed to load cookies: {e}")

    async def _save_cookies(self) -> None:
        """Save cookies to file"""
        try:
            cookies = await self._context.cookies()
            with open(self._cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(cookies)} cookies")
        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")

    async def _wait_for_rate_limit(self) -> None:
        """Apply rate limiting between requests"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        # Random delay between requests
        import random
        delay = random.uniform(self.request_delay_min, self.request_delay_max)

        if elapsed < delay:
            wait_time = delay - elapsed
            self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.time()
        self._request_count += 1

    async def _retry_on_error(
        self,
        func: Callable,
        *args,
        max_retries: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Retry a function on error with exponential backoff

        Args:
            func: Function to retry
            *args: Positional arguments for the function
            max_retries: Maximum number of retries (default from config)
            **kwargs: Keyword arguments for the function

        Returns:
            Function result
        """
        max_retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries} attempts failed")

        raise last_error

    async def download_media(
        self,
        url: str,
        filename: Optional[str] = None,
        force: bool = False,
    ) -> Optional[Path]:
        """
        Download media file (image, video, audio)

        Args:
            url: Media URL
            filename: Custom filename (optional)
            force: Force re-download even if file exists

        Returns:
            Path to downloaded file or None if failed
        """
        if not config.spider.download_media:
            self.logger.debug("Media download disabled")
            return None

        # Check if already downloaded
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if not force and url_hash in self._downloaded_urls:
            self.logger.debug(f"Media already downloaded: {url}")
            return None

        try:
            # Generate filename if not provided
            if not filename:
                ext = url.split("?")[0].split(".")[-1].lower()
                if ext not in config.spider.media_formats:
                    self.logger.warning(f"Unsupported media format: {ext}")
                    return None
                filename = f"{url_hash}.{ext}"

            filepath = self._download_dir / filename

            # Skip if file exists and not forcing
            if filepath.exists() and not force:
                self.logger.debug(f"File already exists: {filepath}")
                self._downloaded_urls.add(url_hash)
                return filepath

            # Download using helper
            success = await self.helper.download_file(
                self._page,
                url,
                str(filepath),
                max_size=config.spider.max_media_size,
            )

            if success:
                self._downloaded_urls.add(url_hash)
                self.logger.info(f"Downloaded media: {filepath.name}")
                return filepath
            else:
                self.logger.warning(f"Failed to download media: {url}")
                return None

        except Exception as e:
            self.logger.error(f"Error downloading media {url}: {e}")
            return None

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """
        Navigate to a URL with retry logic

        Args:
            url: URL to navigate to
            wait_until: Wait until event ('load', 'domcontentloaded', 'networkidle')

        Returns:
            True if navigation successful
        """
        try:
            await self._wait_for_rate_limit()

            async def _navigate():
                await self._page.goto(url, wait_until=wait_until, timeout=self.timeout)
                return True

            return await self._retry_on_error(_navigate)

        except Exception as e:
            self.logger.error(f"Failed to navigate to {url}: {e}")
            return False

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None,
        state: str = "visible",
    ) -> bool:
        """
        Wait for a selector to appear

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds
            state: Element state ('attached', 'detached', 'visible', 'hidden')

        Returns:
            True if element found
        """
        try:
            timeout = timeout or self.timeout
            await self._page.wait_for_selector(
                selector,
                timeout=timeout,
                state=state,
            )
            return True
        except PlaywrightTimeoutError:
            self.logger.warning(f"Timeout waiting for selector: {selector}")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for selector {selector}: {e}")
            return False

    async def click_element(self, selector: str, timeout: Optional[int] = None) -> bool:
        """
        Click an element by selector

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            True if click successful
        """
        try:
            timeout = timeout or self.timeout
            await self._page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.error(f"Failed to click element {selector}: {e}")
            return False

    async def type_text(
        self,
        selector: str,
        text: str,
        delay: int = 100,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Type text into an input element

        Args:
            selector: CSS selector
            text: Text to type
            delay: Delay between keystrokes in milliseconds
            timeout: Timeout in milliseconds

        Returns:
            True if typing successful
        """
        try:
            timeout = timeout or self.timeout
            await self._page.fill(selector, "", timeout=timeout)
            await self._page.type(selector, text, delay=delay, timeout=timeout)
            return True
        except Exception as e:
            self.logger.error(f"Failed to type text into {selector}: {e}")
            return False

    async def get_element_text(self, selector: str) -> Optional[str]:
        """Get text content of an element"""
        try:
            return await self._page.text_content(selector)
        except Exception as e:
            self.logger.error(f"Failed to get text from {selector}: {e}")
            return None

    async def get_element_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> Optional[str]:
        """Get attribute value of an element"""
        try:
            return await self._page.get_attribute(selector, attribute)
        except Exception as e:
            self.logger.error(f"Failed to get attribute {attribute} from {selector}: {e}")
            return None

    async def screenshot(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        Take a screenshot of the current page

        Args:
            filename: Custom filename (optional)

        Returns:
            Path to screenshot file
        """
        try:
            if not filename:
                timestamp = int(time.time())
                filename = f"screenshot_{self.platform}_{timestamp}.png"

            filepath = self._download_dir / filename
            await self._page.screenshot(path=str(filepath), full_page=True)
            self.logger.info(f"Screenshot saved: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return None

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript on the page"""
        try:
            return await self._page.evaluate(script)
        except Exception as e:
            self.logger.error(f"Failed to execute script: {e}")
            return None

    async def scroll_to_bottom(self, wait_time: float = 1.0, max_scrolls: int = 10) -> None:
        """
        Scroll to the bottom of the page

        Args:
            wait_time: Wait time between scrolls in seconds
            max_scrolls: Maximum number of scroll attempts
        """
        for i in range(max_scrolls):
            previous_height = await self._page.evaluate("document.body.scrollHeight")
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(wait_time)
            new_height = await self._page.evaluate("document.body.scrollHeight")

            if new_height == previous_height:
                self.logger.debug(f"Reached bottom after {i + 1} scrolls")
                break

    @asynccontextmanager
    async def session(self):
        """Context manager for spider session"""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(platform='{self.platform}')>"
