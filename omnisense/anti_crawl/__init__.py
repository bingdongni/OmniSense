"""
OmniSense Anti-Crawl Module

This module provides comprehensive anti-detection capabilities for web scraping:
- Dynamic proxy rotation with health checks
- Browser fingerprint randomization
- User-agent rotation
- Request delay randomization
- Captcha solving integration
- Cookie rotation
- HTTP header randomization
"""

from .base import AntiCrawlHandler
from .manager import AntiCrawlManager

__all__ = [
    "AntiCrawlHandler",
    "AntiCrawlManager",
]

__version__ = "1.0.0"
