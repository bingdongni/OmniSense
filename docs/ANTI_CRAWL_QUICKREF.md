# Anti-Crawl System - Quick Reference

Quick reference guide for using the OmniSense Anti-Crawl System.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Basic Usage

```python
from omnisense.anti_crawl import AntiCrawlManager
from omnisense.anti_crawl.base import RequestContext

# Create manager
manager = AntiCrawlManager()
await manager.initialize()

# Prepare request
context = RequestContext(url="https://example.com")
context = await manager.prepare_request(context)

# Use the context
print(f"User-Agent: {context.user_agent}")
print(f"Headers: {context.headers}")
print(f"Proxy: {context.proxy}")
print(f"Delay: {context.delay}s")

await manager.close()
```

### 2. With Proxies

```python
from omnisense.anti_crawl.utils import ProxyConfig

proxy_config = ProxyConfig(
    initial_proxies=[
        "http://proxy1.example.com:8080",
        "socks5://proxy2.example.com:1080",
    ],
    rotation_strategy="least_used",
    health_check_enabled=True,
)

manager = AntiCrawlManager(proxy_config=proxy_config)
```

### 3. Factory Function

```python
from omnisense.anti_crawl.manager import create_anti_crawl_manager
from omnisense.anti_crawl.base import CrawlStrategy

manager = create_anti_crawl_manager(
    strategy=CrawlStrategy.BALANCED,
    use_proxies=True,
    proxy_list=["http://proxy:8080"],
)
```

### 4. HTTP Client

```python
from examples.anti_crawl_integration import AntiCrawlHTTPClient

client = AntiCrawlHTTPClient()
await client.initialize()

# GET request
response = await client.get("https://example.com")

# POST request
response = await client.post(
    "https://example.com/api",
    json={"key": "value"}
)

await client.close()
```

## Configuration Options

### Strategies

| Strategy | Description | Delay Multiplier |
|----------|-------------|------------------|
| CONSERVATIVE | Slower, more human-like | 1.5x |
| BALANCED | Balance speed and stealth | 1.0x |
| AGGRESSIVE | Faster, less cautious | 0.5x |

### Common Settings

```python
from omnisense.anti_crawl.base import AntiCrawlConfig

config = AntiCrawlConfig(
    # Proxies
    use_proxies=True,
    proxy_rotation_interval=10,

    # User Agents
    rotate_user_agent=True,
    user_agent_types=["chrome", "firefox"],

    # Fingerprints
    randomize_fingerprint=True,
    fingerprint_rotation_interval=50,

    # Delays
    min_delay=1.0,
    max_delay=3.0,
    use_random_delay=True,

    # Rate Limiting
    requests_per_minute=30,
    concurrent_requests=5,

    # Retries
    max_retries=3,
    retry_delay=5.0,
    backoff_factor=2.0,
)
```

## Components

### Proxy Pool

```python
from omnisense.anti_crawl.utils import ProxyPool, ProxyConfig

pool = ProxyPool(ProxyConfig(
    rotation_strategy="least_used",  # or "random", "round_robin"
))
await pool.initialize()

proxy = await pool.get_proxy()
await pool.mark_success(proxy, response_time=0.5)
await pool.mark_failed(proxy)

stats = pool.get_stats()
```

### Fingerprint Generator

```python
from omnisense.anti_crawl.utils import FingerprintGenerator

generator = FingerprintGenerator()
fingerprint = generator.generate()

# Access properties
screen = fingerprint["screen"]
webgl = fingerprint["webgl"]
hardware = fingerprint["hardware"]

# Consistent fingerprint
fp = generator.generate_consistent_fingerprint("seed123")
```

### User Agent Rotator

```python
from omnisense.anti_crawl.utils import UserAgentRotator

rotator = UserAgentRotator()

# Random user agent
ua = rotator.get_random_user_agent()

# Specific browser
chrome_ua = rotator.get_user_agent_by_browser("chrome")
mobile_ua = rotator.get_user_agent_by_browser("chrome", mobile=True)

# Parse user agent
info = rotator.parse_user_agent(ua)
```

### Captcha Resolver

```python
from omnisense.anti_crawl.utils import CaptchaResolver, CaptchaConfig

resolver = CaptchaResolver(CaptchaConfig(
    service="2captcha",
    api_key="YOUR_API_KEY",
))
await resolver.initialize()

solution = await resolver.solve(
    captcha_type="recaptcha_v2",
    site_key="SITE_KEY",
    page_url="https://example.com",
)
```

## Common Patterns

### Pattern 1: Simple Scraping

```python
manager = AntiCrawlManager()
await manager.initialize()

for url in urls:
    context = RequestContext(url=url)
    context = await manager.prepare_request(context)
    # Make request with context
```

### Pattern 2: With Retry Logic

```python
async def fetch(context):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            context.url,
            headers=context.headers,
            proxy=context.proxy
        ) as response:
            return await response.text()

success, result = await manager.execute_request(context, fetch)
```

### Pattern 3: Playwright Integration

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()

    await manager.apply_fingerprint_to_playwright(page)
    await page.goto("https://example.com")
```

### Pattern 4: Session Management

```python
# Maintain same identity across requests
fingerprint = await manager._get_fingerprint()
proxy = await manager._get_proxy()

for url in urls:
    context = RequestContext(
        url=url,
        proxy=proxy,  # Same proxy
        fingerprint=fingerprint,  # Same fingerprint
    )
    # Process request
```

## Monitoring

### Get Statistics

```python
stats = manager.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Strategy: {stats['strategy']}")
print(f"Proxy pool: {stats['proxy_pool']}")
```

### Health Check

```python
health = await manager.health_check()
print(f"Status: {health['status']}")
print(f"Components: {health['components']}")
```

## Error Handling

```python
try:
    success, result = await manager.execute_request(context, executor)
    if success:
        # Process result
        pass
    else:
        # Handle failure
        logger.error("Request failed")
except Exception as e:
    logger.exception("Error occurred")
```

## Utility Functions

```python
# Proxy utilities
from omnisense.anti_crawl.utils.proxy_pool import (
    parse_proxy_list_file,
    format_proxy_url,
)

proxies = parse_proxy_list_file("proxies.txt")
proxy_url = format_proxy_url("host", 8080, "http", "user", "pass")

# User agent utilities
from omnisense.anti_crawl.utils.user_agent import (
    is_mobile_user_agent,
    get_browser_from_user_agent,
    get_latest_user_agents,
)

is_mobile = is_mobile_user_agent(ua)
browser = get_browser_from_user_agent(ua)
latest = get_latest_user_agents()

# Fingerprint utilities
from omnisense.anti_crawl.utils.fingerprint import (
    get_common_screen_resolutions,
    get_common_user_agents,
)

resolutions = get_common_screen_resolutions()
user_agents = get_common_user_agents()

# Captcha utilities
from omnisense.anti_crawl.utils.captcha import (
    estimate_solve_time,
    get_service_pricing,
)

time_estimate = estimate_solve_time(CaptchaType.RECAPTCHA_V2)
pricing = get_service_pricing(CaptchaService.TWOCAPTCHA)
```

## Best Practices

1. **Always initialize** - Call `await manager.initialize()` before use
2. **Always cleanup** - Call `await manager.close()` when done
3. **Use context managers** - For automatic cleanup
4. **Monitor statistics** - Check regularly with `get_stats()`
5. **Enable health checks** - For production proxy pools
6. **Handle errors** - Use try/except and check success flags
7. **Log appropriately** - Use logger.debug/info/warning/error
8. **Test configurations** - Start with CONSERVATIVE strategy

## Troubleshooting

### No proxies available
```python
# Check proxy pool
health = await manager.health_check()
print(health["available_proxies"])

# Add more proxies
await manager.add_proxies(["http://new-proxy:8080"])
```

### Requests too slow
```python
# Use aggressive strategy
manager.set_strategy(CrawlStrategy.AGGRESSIVE)

# Increase concurrent requests
manager.config.concurrent_requests = 10
```

### Getting blocked
```python
# Increase delays
manager.config.min_delay = 2.0
manager.config.max_delay = 5.0

# Rotate more frequently
manager.config.proxy_rotation_interval = 5
manager.config.fingerprint_rotation_interval = 25
```

## API Reference

See `docs/anti_crawl_README.md` for complete API documentation.

## Examples

See `examples/` directory for complete examples:
- `anti_crawl_usage.py` - Basic usage examples
- `anti_crawl_integration.py` - Integration examples

## Tests

Run tests:
```bash
pytest tests/test_anti_crawl.py -v
```

---

For more details, see the complete documentation in `docs/anti_crawl_README.md`
