# OmniSense Anti-Crawl System

A comprehensive anti-detection system for web scraping that helps bypass anti-bot measures and avoid detection.

## Features

- **Dynamic Proxy Rotation**: Automatic proxy pool management with health checking and multiple rotation strategies
- **Browser Fingerprint Randomization**: Randomizes Canvas, WebGL, fonts, screen resolution, and hardware properties
- **User-Agent Rotation**: Intelligent user-agent rotation supporting Chrome, Firefox, Safari, Edge, and mobile browsers
- **Request Delay Randomization**: Human-like request delays with multiple crawling strategies
- **Captcha Solving**: Integration with popular captcha services (2Captcha, Anti-Captcha, CapSolver)
- **HTTP Header Randomization**: Realistic browser headers with proper ordering
- **Rate Limiting**: Configurable request rate limiting to avoid triggering anti-bot measures
- **Retry Logic**: Exponential backoff retry mechanism with automatic proxy rotation on failure

## Installation

The required dependencies are already included in the main `requirements.txt`:

```bash
pip install -r requirements.txt
```

Key dependencies:
- `aiohttp` - Async HTTP client
- `fake-useragent` - User agent rotation
- `python-socks` - SOCKS proxy support
- `playwright` - Browser automation (optional)

## Quick Start

### Basic Usage

```python
import asyncio
from omnisense.anti_crawl import AntiCrawlManager
from omnisense.anti_crawl.base import RequestContext

async def main():
    # Create manager with default settings
    manager = AntiCrawlManager()
    await manager.initialize()

    # Prepare a request
    context = RequestContext(url="https://example.com")
    context = await manager.prepare_request(context)

    # Use the prepared context for your HTTP request
    print(f"User-Agent: {context.user_agent}")
    print(f"Headers: {context.headers}")
    print(f"Delay: {context.delay}s")

    await manager.close()

asyncio.run(main())
```

### With Proxy Rotation

```python
from omnisense.anti_crawl import AntiCrawlManager
from omnisense.anti_crawl.utils import ProxyConfig

proxy_config = ProxyConfig(
    initial_proxies=[
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        "socks5://proxy3.example.com:1080",
    ],
    health_check_enabled=True,
    rotation_strategy="least_used",
)

manager = AntiCrawlManager(proxy_config=proxy_config)
await manager.initialize()
```

### With Captcha Solving

```python
from omnisense.anti_crawl import AntiCrawlManager
from omnisense.anti_crawl.base import AntiCrawlConfig

config = AntiCrawlConfig(
    solve_captcha=True,
    captcha_service="2captcha",
    captcha_api_key="YOUR_API_KEY",
)

manager = AntiCrawlManager(config=config)
await manager.initialize()

# Solve a reCAPTCHA v2
solution = await manager.solve_captcha(
    captcha_type="recaptcha_v2",
    site_key="SITE_KEY",
    page_url="https://example.com",
)
```

### With Playwright

```python
from playwright.async_api import async_playwright
from omnisense.anti_crawl import AntiCrawlManager

manager = AntiCrawlManager()
await manager.initialize()

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()

    # Apply fingerprint to page
    await manager.apply_fingerprint_to_playwright(page)

    await page.goto("https://example.com")
    await browser.close()
```

## Configuration

### Crawling Strategies

Choose from three predefined strategies:

- **CONSERVATIVE**: Slower, more human-like (1.5x delay multiplier)
- **BALANCED**: Balance between speed and stealth (1.0x delay multiplier)
- **AGGRESSIVE**: Faster, less cautious (0.5x delay multiplier)

```python
from omnisense.anti_crawl.base import CrawlStrategy, AntiCrawlConfig

config = AntiCrawlConfig(
    strategy=CrawlStrategy.BALANCED,
    min_delay=1.0,
    max_delay=3.0,
)
```

### Full Configuration

```python
from omnisense.anti_crawl.base import AntiCrawlConfig

config = AntiCrawlConfig(
    # Proxy settings
    use_proxies=True,
    proxy_rotation_interval=10,
    proxy_health_check=True,

    # User agent settings
    rotate_user_agent=True,
    user_agent_types=["chrome", "firefox", "safari", "edge"],

    # Fingerprint settings
    randomize_fingerprint=True,
    fingerprint_rotation_interval=50,

    # Delay settings
    min_delay=1.0,
    max_delay=3.0,
    use_random_delay=True,

    # Header settings
    randomize_headers=True,
    accept_languages=["en-US", "en", "zh-CN"],

    # Retry settings
    max_retries=3,
    retry_delay=5.0,
    backoff_factor=2.0,

    # Rate limiting
    requests_per_minute=30,
    concurrent_requests=5,
)
```

## Components

### 1. Proxy Pool (`proxy_pool.py`)

Manages a pool of proxies with automatic health checking and rotation.

**Features:**
- HTTP, HTTPS, SOCKS4, SOCKS5 support
- Automatic health checking
- Multiple rotation strategies (random, least_used, round_robin)
- Failure tracking and auto-removal
- Performance metrics

**Usage:**
```python
from omnisense.anti_crawl.utils import ProxyPool, ProxyConfig

config = ProxyConfig(
    initial_proxies=["http://proxy1:8080"],
    health_check_enabled=True,
    rotation_strategy="least_used",
)

pool = ProxyPool(config)
await pool.initialize()

proxy = await pool.get_proxy()
```

### 2. Fingerprint Generator (`fingerprint.py`)

Generates and manages randomized browser fingerprints.

**Features:**
- Canvas fingerprint randomization
- WebGL fingerprint randomization
- Screen resolution randomization
- Font fingerprint randomization
- Hardware properties randomization
- Timezone and language randomization
- Playwright integration

**Usage:**
```python
from omnisense.anti_crawl.utils import FingerprintGenerator

generator = FingerprintGenerator()
fingerprint = generator.generate()

print(fingerprint["screen"]["width"])  # 1920
print(fingerprint["webgl"]["vendor"])  # "Intel Inc."
print(fingerprint["hardware"]["cpu_cores"])  # 8
```

### 3. User Agent Rotator (`user_agent.py`)

Rotates user agent strings with realistic browser profiles.

**Features:**
- Multiple browser types (Chrome, Firefox, Safari, Edge)
- Desktop and mobile user agents
- Multiple operating systems
- Integration with fake-useragent library
- User agent parsing

**Usage:**
```python
from omnisense.anti_crawl.utils import UserAgentRotator

rotator = UserAgentRotator()
user_agent = rotator.get_random_user_agent()

# Get specific browser
chrome_ua = rotator.get_user_agent_by_browser("chrome")
mobile_ua = rotator.get_user_agent_by_browser("chrome", mobile=True)
```

### 4. Captcha Resolver (`captcha.py`)

Integrates with captcha solving services.

**Supported Services:**
- 2Captcha
- Anti-Captcha
- CapSolver
- DeathByCaptcha (coming soon)

**Supported Captcha Types:**
- reCAPTCHA v2
- reCAPTCHA v3
- hCaptcha
- FunCaptcha
- Image captcha

**Usage:**
```python
from omnisense.anti_crawl.utils import CaptchaResolver, CaptchaConfig

config = CaptchaConfig(
    service="2captcha",
    api_key="YOUR_API_KEY",
    timeout=120,
)

resolver = CaptchaResolver(config)
await resolver.initialize()

solution = await resolver.solve(
    captcha_type="recaptcha_v2",
    site_key="SITE_KEY",
    page_url="https://example.com",
)
```

## Architecture

```
anti_crawl/
├── __init__.py           # Module exports
├── base.py               # Base handler class and configurations
├── manager.py            # Main anti-crawl manager
└── utils/
    ├── __init__.py       # Utils exports
    ├── proxy_pool.py     # Proxy pool management
    ├── fingerprint.py    # Browser fingerprint randomization
    ├── user_agent.py     # User agent rotation
    └── captcha.py        # Captcha solving integration
```

## Best Practices

1. **Use Conservative Strategy for Sensitive Sites**: When scraping sites with strict anti-bot measures, use `CrawlStrategy.CONSERVATIVE`

2. **Rotate Proxies Regularly**: Set appropriate `proxy_rotation_interval` based on target site behavior

3. **Enable Health Checks**: Always enable proxy health checking in production to avoid using dead proxies

4. **Monitor Statistics**: Regularly check manager statistics to identify issues:
   ```python
   stats = manager.get_stats()
   print(stats)
   ```

5. **Handle Captchas Gracefully**: Always have fallback logic when captcha solving fails

6. **Respect Rate Limits**: Configure `requests_per_minute` appropriately to avoid overwhelming target sites

7. **Use Realistic Fingerprints**: Don't rotate fingerprints too frequently - maintain consistency for a session

8. **Log Everything**: The system uses loguru for comprehensive logging - monitor logs for issues

## Error Handling

The system includes comprehensive error handling:

```python
success, result = await manager.execute_request(
    context,
    executor_func=your_request_function
)

if success:
    # Process result
    pass
else:
    # Handle failure
    logger.error("Request failed after all retries")
```

## Performance

- **Async/Await**: All operations are asynchronous for maximum performance
- **Connection Pooling**: Uses aiohttp session for connection reuse
- **Concurrent Requests**: Configurable semaphore for concurrent request limiting
- **Efficient Proxy Rotation**: O(1) proxy selection with all strategies

## Monitoring and Health Checks

```python
# Perform health check
health = await manager.health_check()
print(health["status"])  # "healthy", "degraded", or "unhealthy"

# Get detailed statistics
stats = manager.get_stats()
print(stats["total_requests"])
print(stats["proxy_pool"]["healthy_proxies"])
```

## Examples

See `examples/anti_crawl_usage.py` for comprehensive usage examples including:
- Basic usage
- Proxy rotation
- Fingerprint randomization
- Captcha solving
- Different crawling strategies
- Custom configuration
- Playwright integration
- Health monitoring

## Troubleshooting

### Proxies Not Working

1. Verify proxy format: `protocol://host:port` or `protocol://user:pass@host:port`
2. Check proxy health: `await pool.health_check()`
3. Enable debug logging: `logger.level("DEBUG")`

### Fingerprints Not Applied

1. Ensure `randomize_fingerprint=True` in config
2. Check Playwright version compatibility
3. Verify fingerprint is generated: `manager.get_current_fingerprint()`

### Captcha Solving Fails

1. Verify API key is correct
2. Check account balance on captcha service
3. Ensure captcha type matches site requirements
4. Increase timeout if needed

## Contributing

When contributing to the anti-crawl system:

1. Follow existing code style and patterns
2. Add comprehensive docstrings
3. Include error handling
4. Add tests for new features
5. Update this README with new features

## License

This anti-crawl system is part of the OmniSense project. Use responsibly and in accordance with target websites' Terms of Service and robots.txt.

## Disclaimer

This tool is provided for educational and legitimate web scraping purposes only. Users are responsible for ensuring their use complies with applicable laws and website terms of service. The developers are not responsible for any misuse of this tool.
