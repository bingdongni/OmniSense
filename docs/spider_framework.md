# OmniSense Spider Framework

A production-ready, async-first web scraping framework built on Playwright with advanced anti-detection capabilities.

## Features

- **Async Playwright Integration**: High-performance browser automation with async/await
- **Anti-Detection**: Built-in stealth scripts, fingerprint randomization, and user-agent rotation
- **Cookie & Session Management**: Automatic cookie persistence and session handling
- **Rate Limiting**: Configurable delays and request throttling
- **Media Download**: Automatic downloading of images, videos, and other media files
- **Error Handling**: Robust retry logic with exponential backoff
- **Multi-Platform Support**: Unified interface for managing multiple platform spiders
- **Concurrent Execution**: Efficient task scheduling and resource pooling

## Architecture

```
omnisense/spider/
├── __init__.py              # Module exports
├── base.py                  # BaseSpider abstract class
├── manager.py               # SpiderManager for coordinating multiple spiders
├── utils/
│   ├── __init__.py
│   ├── playwright_helper.py # Playwright utilities and anti-detection
│   └── parser.py            # HTML/JSON parsing utilities
└── platforms/               # Platform-specific spider implementations
    ├── douyin.py
    ├── xiaohongshu.py
    └── ...
```

## Installation

Install the required dependencies:

```bash
pip install playwright beautifulsoup4 lxml fake-useragent
playwright install chromium
```

## Quick Start

### 1. Create a Platform-Specific Spider

```python
from omnisense.spider.base import BaseSpider
from typing import Any, Dict, List

class MyPlatformSpider(BaseSpider):
    """Spider for MyPlatform"""

    async def login(self, username: str, password: str) -> bool:
        """Implement login logic"""
        await self.navigate("https://myplatform.com/login")
        await self.type_text("#username", username)
        await self.type_text("#password", password)
        await self.click_element("#login-btn")
        return await self.wait_for_selector("#user-profile")

    async def search(self, keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Implement search logic"""
        await self.navigate(f"https://myplatform.com/search?q={keyword}")
        await self.wait_for_selector(".search-result")

        # Extract results using the parser
        html = await self._page.content()
        soup = self.parser.parse_html(html)
        results = []

        for element in soup.select(".search-result")[:max_results]:
            result = {
                "title": self.parser.extract_text(element, ".title"),
                "url": self.parser.extract_attribute(element, "a", "href"),
                "platform": self.platform,
            }
            results.append(result)

        return results

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Implement user profile retrieval"""
        # Implementation here
        pass

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Implement user posts retrieval"""
        # Implementation here
        pass

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Implement post detail retrieval"""
        # Implementation here
        pass

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Implement comments retrieval"""
        # Implementation here
        pass
```

### 2. Use the Spider

```python
import asyncio

async def main():
    # Create spider instance
    spider = MyPlatformSpider(
        platform="myplatform",
        headless=True,  # Run in headless mode
        proxy="http://proxy.example.com:8080",  # Optional proxy
    )

    # Use context manager for automatic cleanup
    async with spider.session():
        # Login if required
        await spider.login("username", "password")

        # Search for content
        results = await spider.search("python programming", max_results=10)
        print(f"Found {len(results)} results")

        # Get user profile
        profile = await spider.get_user_profile("user123")
        print(f"User: {profile}")

        # Get user posts
        posts = await spider.get_user_posts("user123", max_posts=20)
        print(f"Posts: {len(posts)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Use Spider Manager for Multiple Platforms

```python
from omnisense.spider.manager import SpiderManager

async def main():
    # Create manager
    manager = SpiderManager(max_concurrent=5)

    # Register spiders
    manager.register_spider("platform1", Platform1Spider)
    manager.register_spider("platform2", Platform2Spider)

    async with manager:
        # Search across all platforms
        results = await manager.search_all_platforms(
            keyword="AI trends",
            max_results=20,
        )

        for platform, platform_results in results.items():
            print(f"{platform}: {len(platform_results)} results")

        # Get user data from multiple platforms
        user_data = await manager.get_user_data_from_multiple(
            user_ids={
                "platform1": "user123",
                "platform2": "user456",
            },
            include_posts=True,
            max_posts=10,
        )

        # Monitor user activity
        async def on_new_post(platform, user_id, posts):
            print(f"New posts from {user_id} on {platform}: {len(posts)}")

        await manager.monitor_user_activity(
            user_ids={"platform1": "user123"},
            interval=3600,  # Check every hour
            callback=on_new_post,
        )
```

## BaseSpider API Reference

### Core Methods

#### `async def start() -> None`
Start the browser and create context. Called automatically when using `session()` context manager.

#### `async def stop() -> None`
Stop the browser and clean up resources. Called automatically when exiting `session()` context manager.

#### `async def navigate(url: str, wait_until: str = "domcontentloaded") -> bool`
Navigate to a URL with retry logic.

#### `async def wait_for_selector(selector: str, timeout: Optional[int] = None, state: str = "visible") -> bool`
Wait for an element to appear.

#### `async def click_element(selector: str, timeout: Optional[int] = None) -> bool`
Click an element by CSS selector.

#### `async def type_text(selector: str, text: str, delay: int = 100, timeout: Optional[int] = None) -> bool`
Type text into an input element.

#### `async def download_media(url: str, filename: Optional[str] = None, force: bool = False) -> Optional[Path]`
Download media file (image, video, audio).

#### `async def screenshot(filename: Optional[str] = None) -> Optional[Path]`
Take a screenshot of the current page.

#### `async def scroll_to_bottom(wait_time: float = 1.0, max_scrolls: int = 10) -> None`
Scroll to the bottom of the page to load more content.

### Abstract Methods (Must Implement)

#### `async def login(username: str, password: str) -> bool`
Login to the platform. Return `True` if successful.

#### `async def search(keyword: str, max_results: int = 20) -> List[Dict[str, Any]]`
Search for content by keyword. Return list of result dictionaries.

#### `async def get_user_profile(user_id: str) -> Dict[str, Any]`
Get user profile information. Return user data dictionary.

#### `async def get_user_posts(user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]`
Get posts from a user. Return list of post dictionaries.

#### `async def get_post_detail(post_id: str) -> Dict[str, Any]`
Get detailed information about a post. Return post data dictionary.

#### `async def get_comments(post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]`
Get comments for a post. Return list of comment dictionaries.

## PlaywrightHelper API Reference

### Anti-Detection Methods

#### `async def get_browser_context_options() -> Dict[str, Any]`
Get browser context options with anti-detection settings (viewport, user-agent, headers).

#### `async def apply_stealth_scripts(page: Page) -> None`
Apply stealth scripts to evade detection (override webdriver, plugins, canvas fingerprint).

#### `async def random_mouse_move(page: Page) -> None`
Perform random mouse movements to simulate human behavior.

#### `async def random_scroll(page: Page) -> None`
Perform random scrolling to simulate human behavior.

#### `async def human_like_type(page: Page, selector: str, text: str, min_delay: int = 50, max_delay: int = 150) -> None`
Type text with human-like delays between keystrokes.

### Utility Methods

#### `async def download_file(page: Page, url: str, save_path: str, max_size: Optional[int] = None) -> bool`
Download a file from URL.

#### `async def intercept_requests(page: Page, block_resources: Optional[List[str]] = None) -> None`
Intercept and block certain resources (images, stylesheets, fonts) to speed up page load.

#### `async def wait_for_network_idle(page: Page, timeout: int = 30000, idle_time: int = 500) -> bool`
Wait for network to become idle.

#### `async def get_all_cookies(page: Page) -> List[Dict[str, Any]]`
Get all cookies from the page.

#### `async def extract_links(page: Page, selector: str = "a") -> List[str]`
Extract all links from page.

## ContentParser API Reference

### HTML Parsing

#### `def parse_html(html: str, parser: str = "lxml") -> BeautifulSoup`
Parse HTML content with BeautifulSoup.

#### `def extract_text(soup: BeautifulSoup, selector: str) -> Optional[str]`
Extract text content using CSS selector.

#### `def extract_texts(soup: BeautifulSoup, selector: str) -> List[str]`
Extract multiple text contents using CSS selector.

#### `def extract_attribute(soup: BeautifulSoup, selector: str, attribute: str) -> Optional[str]`
Extract attribute value using CSS selector.

#### `def extract_links(soup: BeautifulSoup, base_url: str = "") -> List[str]`
Extract all links from page.

#### `def extract_images(soup: BeautifulSoup, base_url: str = "") -> List[Dict[str, str]]`
Extract all images with src and alt.

#### `def extract_videos(soup: BeautifulSoup, base_url: str = "") -> List[Dict[str, str]]`
Extract all videos with src and poster.

### Content Extraction

#### `def extract_numbers(text: str) -> List[float]`
Extract all numbers from text (handles Chinese numbers).

#### `def extract_phone_numbers(text: str) -> List[str]`
Extract phone numbers from text.

#### `def extract_emails(text: str) -> List[str]`
Extract email addresses from text.

#### `def extract_urls(text: str) -> List[str]`
Extract URLs from text.

#### `def extract_hashtags(text: str) -> List[str]`
Extract hashtags from text.

#### `def extract_mentions(text: str) -> List[str]`
Extract user mentions from text.

### Data Parsing

#### `def parse_date(date_str: str) -> Optional[datetime]`
Parse date string to datetime object (handles relative dates like "3小时前").

#### `def parse_count(count_str: str) -> int`
Parse count string with units (e.g., '1.2万', '3.5K').

#### `def parse_duration(duration_str: str) -> int`
Parse duration string to seconds (e.g., '01:23', '1:23:45').

#### `def extract_json_from_script(html: str, pattern: Optional[str] = None) -> Optional[Dict]`
Extract JSON data from script tags.

## Configuration

The spider framework uses the OmniSense configuration system. Key settings:

```python
# In config.py or .env

# Spider Configuration
SPIDER__CONCURRENT_TASKS=5          # Number of concurrent tasks
SPIDER__TIMEOUT=30                  # Request timeout (seconds)
SPIDER__DOWNLOAD_MEDIA=True         # Download media files
SPIDER__MAX_MEDIA_SIZE=104857600    # Max media size (100MB)
SPIDER__COOKIE_PERSIST=True         # Persist cookies

# Anti-Crawl Configuration
ANTI_CRAWL__USER_AGENT_ROTATION=True
ANTI_CRAWL__FINGERPRINT_RANDOM=True
ANTI_CRAWL__REQUEST_DELAY_MIN=1.0
ANTI_CRAWL__REQUEST_DELAY_MAX=5.0
ANTI_CRAWL__MAX_RETRIES=3

# Proxy Configuration
PROXY__ENABLED=False
PROXY__HTTP_PROXY=http://proxy:8080
PROXY__HTTPS_PROXY=https://proxy:8080
```

## Best Practices

### 1. Always Use Context Managers

```python
# Good - automatic cleanup
async with spider.session():
    results = await spider.search("keyword")

# Bad - manual cleanup required
await spider.start()
results = await spider.search("keyword")
await spider.stop()
```

### 2. Implement Robust Error Handling

```python
async def search(self, keyword: str, max_results: int = 20):
    try:
        await self.navigate(f"https://example.com/search?q={keyword}")
        await self.wait_for_selector(".results")
        # ... extraction logic
        return results
    except Exception as e:
        self.logger.error(f"Search failed: {e}")
        return []  # Return empty list on error
```

### 3. Use Rate Limiting

```python
# Rate limiting is automatic, but you can add additional delays
await self._wait_for_rate_limit()  # Built-in rate limiting
await self.helper.wait_random_time(2, 5)  # Additional random delay
```

### 4. Download Media Selectively

```python
# Check if media download is enabled
if config.spider.download_media:
    # Limit number of downloads
    for img in images[:5]:  # Only first 5 images
        await self.download_media(img["src"])
```

### 5. Use Parser Utilities

```python
# Extract and parse in one go
likes_count = self.parser.parse_count(
    self.parser.extract_text(soup, ".likes")
)  # "1.2万" -> 12000

created_at = self.parser.parse_date(
    self.parser.extract_text(soup, ".time")
)  # "3小时前" -> datetime object
```

### 6. Implement Login Persistence

```python
async def login(self, username: str, password: str) -> bool:
    # Check if already logged in
    if self._is_logged_in:
        return True

    # Try to use saved session
    if self._session_file.exists():
        try:
            # Load and verify session
            if await self._verify_session():
                self._is_logged_in = True
                return True
        except Exception:
            pass

    # Perform actual login
    # ... login logic ...

    self._is_logged_in = True
    await self._save_session()
    return True
```

## Advanced Usage

### Custom Download Directory

```python
spider = MyPlatformSpider(
    platform="myplatform",
    user_data_dir=Path("./custom_data")
)
```

### Block Resources for Faster Loading

```python
await self.helper.intercept_requests(
    self._page,
    block_resources=["image", "stylesheet", "font", "media"]
)
```

### Capture Network Requests

```python
requests = await self.helper.get_network_requests(self._page)
for req in requests:
    if "api" in req["url"]:
        print(f"API call: {req['url']}")
```

### Take Element Screenshots

```python
await self.helper.take_element_screenshot(
    self._page,
    ".user-profile",
    "profile_screenshot.png"
)
```

## Troubleshooting

### Browser Not Launching

```bash
# Install Playwright browsers
playwright install chromium

# Or use system browser
playwright install-deps
```

### Anti-Detection Not Working

- Enable fingerprint randomization in config
- Use residential proxies
- Increase random delays
- Rotate user agents more frequently

### Memory Leaks

- Always use context managers (`async with spider.session()`)
- Close spiders when done (`await manager.close_all_spiders()`)
- Limit concurrent spiders (`SpiderManager(max_concurrent=3)`)

### Rate Limiting Issues

- Increase delay ranges in config
- Reduce concurrent tasks
- Use proxy rotation

## Examples

See `examples/spider_example.py` for comprehensive examples including:
- Basic spider usage
- Spider manager usage
- Concurrent operations
- User activity monitoring

## License

Part of the OmniSense project.
