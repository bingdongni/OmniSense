# Douyin Spider - Quick Reference Guide

## 🚀 Quick Start (30 seconds)

```python
import asyncio
from omnisense.spider.platforms import DouyinSpider

async def quick_search():
    spider = DouyinSpider(headless=True)
    async with spider.session():
        videos = await spider.search("AI", max_results=5)
        return videos

videos = asyncio.run(quick_search())
```

## 📚 Common Operations

### Search Videos
```python
videos = await spider.search(
    keyword="Python教程",
    max_results=20,
    sort_type="popular"  # comprehensive/latest/popular
)
```

### Get User Videos
```python
profile = await spider.get_user_profile(user_id)
videos = await spider.get_user_posts(user_id, max_posts=30)
```

### Get Comments
```python
comments = await spider.get_comments(
    post_id=video_id,
    max_comments=100,
    include_replies=True
)
```

### Download Video
```python
path = await spider.download_video(video_url, save_path="video.mp4")
```

### Search with Filters
```python
criteria = {
    'keywords': ['Python', 'AI'],
    'min_likes': 1000,
    'min_views': 10000,
}
videos = await spider.search("Python", criteria=criteria)
```

## 🎯 Important Selectors (Update if UI changes)

```python
# Search results
'[data-e2e="search-result-item"]'

# Video details
'[data-e2e="video-title"]'
'[data-e2e="video-desc"]'
'[data-e2e="video-cover"]'
'[data-e2e="video-author"]'
'[data-e2e="like-count"]'
'[data-e2e="comment-count"]'
'[data-e2e="share-count"]'

# Comments
'[data-e2e="comment-item"]'
'[data-e2e="comment-username"]'
'[data-e2e="comment-text"]'
'[data-e2e="reply-item"]'

# User page
'[data-e2e="user-info-nickname"]'
'[data-e2e="user-stats"]'
'[data-e2e="user-video-item"]'
```

## 🛠️ Configuration

### Global Settings
```python
from omnisense.config import config

# Anti-crawl settings
config.anti_crawl.request_delay_min = 2.0
config.anti_crawl.request_delay_max = 5.0
config.anti_crawl.max_retries = 5

# Spider settings
config.spider.download_media = True
config.spider.timeout = 60
```

### Spider Instance Settings
```python
spider = DouyinSpider(
    headless=True,  # Run in background
    proxy="http://proxy:8080"  # Use proxy
)
```

## 🔍 Debugging

### Enable Debug Logging
```python
from omnisense.utils.logger import get_logger
logger = get_logger(__name__)
logger.setLevel('DEBUG')
```

### Show Browser (Visual Debugging)
```python
spider = DouyinSpider(headless=False)
```

### Take Screenshot
```python
await spider.screenshot("debug.png")
```

## ⚡ Performance Tips

1. **Use headless mode** for production
2. **Set appropriate delays** to avoid detection
3. **Reuse spider instance** for multiple operations
4. **Use criteria** to filter early
5. **Batch operations** when possible

## 🐛 Common Issues & Solutions

### Issue: Captcha Detected
**Solution**: Increase delays, use proxy, or manually solve
```python
config.anti_crawl.request_delay_min = 3.0
await spider.anti_crawl.handle_slider_captcha(page)
```

### Issue: Login Required
**Solution**: Use login method or provide cookies
```python
await spider.login()  # Manual QR code scan
```

### Issue: Rate Limited
**Solution**: Increase delays and reduce concurrency
```python
config.anti_crawl.request_delay_min = 5.0
await asyncio.sleep(60)  # Wait before retry
```

### Issue: Element Not Found
**Solution**: Update selectors or increase timeout
```python
config.spider.timeout = 60
await spider.wait_for_selector(selector, timeout=30000)
```

### Issue: Network Error
**Solution**: Check proxy and retry
```python
config.anti_crawl.max_retries = 5
```

## 📊 Data Fields Reference

| Field | Type | Description |
|-------|------|-------------|
| content_id | str | Video ID |
| title | str | Video title |
| description | str | Video description |
| author | dict | Author info (nickname, avatar, user_id) |
| like_count | int | Number of likes |
| comment_count | int | Number of comments |
| share_count | int | Number of shares |
| view_count | int | Number of views |
| publish_time | datetime | When published |
| hashtags | list | List of hashtags |
| video_url | str | Direct video URL |
| cover_image | str | Cover image URL |
| duration | int | Duration in seconds |
| music | dict | Music information |
| location | str | Video location |
| poi_info | dict | POI information |

## 🔐 Security Best Practices

1. ✅ Never commit cookies or credentials
2. ✅ Use environment variables for sensitive data
3. ✅ Respect rate limits
4. ✅ Use proxies for large-scale collection
5. ✅ Monitor for platform changes
6. ✅ Read and follow ToS

## 🧪 Testing Commands

```bash
# Run all tests
pytest tests/test_douyin_spider.py -v

# Run specific test
pytest tests/test_douyin_spider.py::TestDouyinSpider::test_extract_video_id -v

# Run with coverage
pytest tests/test_douyin_spider.py --cov=omnisense.spider.platforms.douyin

# Run examples
python examples/douyin_example.py 1
python examples/douyin_example.py all
```

## 📦 Import Reference

```python
# Main spider
from omnisense.spider.platforms import DouyinSpider

# Components
from omnisense.spider.platforms.douyin import (
    DouyinAntiCrawl,
    DouyinMatcher,
    DouyinInteraction
)

# Convenience functions
from omnisense.spider.platforms import (
    search_douyin_videos,
    get_douyin_user_videos
)

# Registry
from omnisense.spider.platforms import (
    get_spider,
    list_platforms
)
```

## 🎨 Architecture Layers

```
┌─────────────────────────────────────────────────┐
│          DouyinSpider (Layer 1)                 │
│  • search() • get_user_posts()                  │
│  • get_post_detail() • get_comments()           │
├─────────────────────────────────────────────────┤
│      DouyinAntiCrawl (Layer 2)                  │
│  • Device fingerprinting                        │
│  • Behavior simulation                          │
│  • Captcha solving                              │
├─────────────────────────────────────────────────┤
│        DouyinMatcher (Layer 3)                  │
│  • Content matching                             │
│  • Filtering logic                              │
│  • Score calculation                            │
├─────────────────────────────────────────────────┤
│     DouyinInteraction (Layer 4)                 │
│  • Comment collection                           │
│  • User profiles                                │
│  • Engagement data                              │
└─────────────────────────────────────────────────┘
```

## 🔄 Typical Workflow

```python
# 1. Initialize
spider = DouyinSpider(headless=True)

# 2. Start session
async with spider.session():

    # 3. Optional: Login
    await spider.login()

    # 4. Search or navigate
    videos = await spider.search("keyword", max_results=20)

    # 5. Get details
    for video in videos:
        detail = await spider.get_post_detail(video['content_id'])
        comments = await spider.get_comments(video['content_id'])

    # 6. Download media
    await spider.download_video(video['video_url'])

# 7. Session auto-closes, cookies saved
```

## 📞 Getting Help

1. **Check Documentation**: `README_DOUYIN.md`
2. **Review Examples**: `examples/douyin_example.py`
3. **Run Tests**: `tests/test_douyin_spider.py`
4. **Read Implementation**: `IMPLEMENTATION_SUMMARY.md`
5. **GitHub Issues**: Report bugs or ask questions

## 💡 Pro Tips

- Use `criteria` to filter before downloading full details
- Reuse spider sessions to maintain cookies
- Monitor logs for warnings and errors
- Test with small batches first
- Save progress regularly
- Use exception handling for robustness

---

**Quick Links:**
- [Full Documentation](README_DOUYIN.md)
- [Examples](../../examples/douyin_example.py)
- [Tests](../../tests/test_douyin_spider.py)
- [Implementation Details](IMPLEMENTATION_SUMMARY.md)
