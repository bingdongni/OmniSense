# Douyin (抖音) Spider Documentation

## Overview

The Douyin spider is a complete, production-ready implementation for collecting data from the Douyin (Chinese TikTok) platform. It implements all four architectural layers:

1. **Spider Layer**: Data collection (keyword search, user pages, topic pages, video details)
2. **Anti-Crawl Layer**: Anti-detection (device fingerprinting, IP rotation, behavior simulation)
3. **Matcher Layer**: Multi-modal matching (title, description, subtitles, OCR)
4. **Interaction Layer**: User interactions (nested comments, likes, shares, creator info)

## Features

### Core Capabilities
- ✅ **Keyword Search**: Search videos by keywords with multiple filters
- ✅ **User Profile**: Get complete user information and statistics
- ✅ **User Videos**: Collect all videos from a specific user
- ✅ **Topic Videos**: Get videos from specific hashtags/topics
- ✅ **Video Details**: Extract 20+ fields per video
- ✅ **Comments**: Nested comment collection with replies
- ✅ **Barrage (Danmu)**: Video barrage collection (framework provided)
- ✅ **Media Download**: Download videos and images
- ✅ **Creator Info**: Detailed creator profile information

### Anti-Detection Features
- 🛡️ **Device Fingerprinting**: Random device ID generation
- 🛡️ **WebDriver Evasion**: Removes automation detection
- 🛡️ **Canvas Fingerprinting**: Randomized canvas signatures
- 🛡️ **Human Behavior**: Realistic scrolling and mouse movements
- 🛡️ **Slider Captcha**: Automatic slider captcha solving
- 🛡️ **Rate Limiting**: Intelligent request throttling

### Data Fields Extracted (20+ fields)

#### Video Information
```python
{
    'content_id': str,           # Video ID
    'platform': 'douyin',        # Platform name
    'content_type': 'video',     # Content type
    'url': str,                  # Video URL
    'title': str,                # Video title
    'description': str,          # Video description
    'cover_image': str,          # Cover image URL
    'video_url': str,            # Direct video URL
    'images': list,              # Images (for photo albums)
    'duration': int,             # Duration in seconds
    'resolution': str,           # Video resolution
    'hashtags': list,            # Hashtags
    'mentions': list,            # Mentioned users
    'music': dict,               # Music information
    'author': dict,              # Author information
    'view_count': int,           # View count
    'like_count': int,           # Like count
    'comment_count': int,        # Comment count
    'share_count': int,          # Share count
    'collect_count': int,        # Collection count
    'publish_time': datetime,    # Publish time
    'location': str,             # Location
    'is_ad': bool,               # Is advertisement
    'poi_info': dict,            # POI information
    'collected_at': datetime     # Collection time
}
```

## Installation

### Prerequisites
```bash
# Install dependencies
pip install playwright asyncio fake-useragent beautifulsoup4 lxml

# Install Playwright browsers
playwright install chromium
```

### Quick Start
```python
import asyncio
from omnisense.spider.platforms import DouyinSpider

async def main():
    spider = DouyinSpider(headless=True)

    async with spider.session():
        # Search for videos
        videos = await spider.search("AI编程", max_results=10)

        for video in videos:
            print(f"Title: {video['title']}")
            print(f"Likes: {video['like_count']}")
            print(f"URL: {video['url']}\n")

asyncio.run(main())
```

## Usage Examples

### 1. Basic Video Search

```python
import asyncio
from omnisense.spider.platforms import DouyinSpider

async def search_videos():
    spider = DouyinSpider(headless=True)

    async with spider.session():
        videos = await spider.search(
            keyword="人工智能",
            max_results=20,
            search_type="video",      # video/user/topic
            sort_type="comprehensive"  # comprehensive/latest/popular
        )

        return videos

# Run
videos = asyncio.run(search_videos())
```

### 2. Search with Filtering Criteria

```python
async def search_with_filter():
    spider = DouyinSpider(headless=True)

    # Define matching criteria
    criteria = {
        'keywords': ['AI', '编程', 'Python'],
        'min_likes': 1000,
        'min_views': 10000,
        'match_threshold': 0.5
    }

    async with spider.session():
        videos = await spider.search(
            keyword="Python教程",
            max_results=20,
            criteria=criteria
        )

        # Videos are automatically filtered
        return videos

videos = asyncio.run(search_with_filter())
```

### 3. Get User Videos

```python
async def get_user_content():
    spider = DouyinSpider(headless=True)

    async with spider.session():
        # Get user profile
        user_id = "MS4wLjABAAAA..."  # Douyin user ID
        profile = await spider.get_user_profile(user_id)

        print(f"User: {profile['nickname']}")
        print(f"Followers: {profile['follower_count']}")

        # Get user's videos
        videos = await spider.get_user_posts(
            user_id=user_id,
            max_posts=30
        )

        return profile, videos

profile, videos = asyncio.run(get_user_content())
```

### 4. Get Video Comments (with Nested Replies)

```python
async def get_video_comments():
    spider = DouyinSpider(headless=True)

    async with spider.session():
        video_id = "7123456789012345678"

        # Get video details
        video = await spider.get_post_detail(video_id)

        # Get comments with replies
        comments = await spider.get_comments(
            post_id=video_id,
            max_comments=100,
            include_replies=True
        )

        # Process comments
        for comment in comments:
            print(f"{comment['user']['nickname']}: {comment['text']}")
            print(f"  Likes: {comment['like_count']}")

            # Print replies
            for reply in comment.get('replies', []):
                print(f"  └─ {reply['user']['nickname']}: {reply['text']}")

        return comments

comments = asyncio.run(get_video_comments())
```

### 5. Get Topic Videos

```python
async def get_topic_content():
    spider = DouyinSpider(headless=True)

    async with spider.session():
        # Get videos from a topic/hashtag
        videos = await spider.get_topic_videos(
            topic="人工智能",  # Topic name without #
            max_videos=30
        )

        return videos

videos = asyncio.run(get_topic_content())
```

### 6. Download Videos

```python
async def download_video():
    spider = DouyinSpider(headless=True)

    async with spider.session():
        video_id = "7123456789012345678"

        # Get video details
        video = await spider.get_post_detail(video_id)

        # Download video
        if video.get('video_url'):
            file_path = await spider.download_video(
                video_url=video['video_url'],
                save_path=f"downloads/{video_id}.mp4"
            )

            print(f"Downloaded to: {file_path}")

        return file_path

asyncio.run(download_video())
```

### 7. Login with Cookies

```python
async def login_and_search():
    spider = DouyinSpider(headless=False)  # Show browser for login

    async with spider.session():
        # Login (will wait for QR code scan)
        success = await spider.login()

        if success:
            print("Login successful!")

            # Now can access more content
            videos = await spider.search("限定内容", max_results=10)
            return videos
        else:
            print("Login failed or skipped")
            return []

videos = asyncio.run(login_and_search())
```

### 8. Using Convenience Functions

```python
from omnisense.spider.platforms import search_douyin_videos, get_douyin_user_videos

# Quick search
videos = asyncio.run(
    search_douyin_videos(
        keyword="Python教程",
        max_results=20,
        headless=True,
        criteria={'min_likes': 1000}
    )
)

# Quick user videos
user_videos = asyncio.run(
    get_douyin_user_videos(
        user_id="MS4wLjABAAAA...",
        max_videos=30,
        headless=True
    )
)
```

## Advanced Configuration

### Custom Anti-Crawl Settings

```python
from omnisense.config import config

# Modify global settings before creating spider
config.anti_crawl.request_delay_min = 2.0
config.anti_crawl.request_delay_max = 5.0
config.anti_crawl.max_retries = 5

# Use proxy
spider = DouyinSpider(
    headless=True,
    proxy="http://proxy.example.com:8080"
)
```

### Custom Matching Logic

```python
from omnisense.spider.platforms.douyin import DouyinMatcher

class CustomMatcher(DouyinMatcher):
    async def match_video(self, video, criteria):
        # Custom matching logic
        if video.get('like_count', 0) > 10000:
            return True, 1.0
        return False, 0.0

# Use custom matcher
spider = DouyinSpider(headless=True)
spider.matcher = CustomMatcher()
```

## Architecture Details

### Layer 1: Spider Layer (DouyinSpider)
The main spider class that handles all data collection operations.

**Key Methods:**
- `search()`: Search videos by keyword
- `get_user_profile()`: Get user information
- `get_user_posts()`: Get user's videos
- `get_post_detail()`: Get video details
- `get_comments()`: Get video comments
- `get_topic_videos()`: Get topic videos
- `download_video()`: Download video file

### Layer 2: Anti-Crawl Layer (DouyinAntiCrawl)
Handles anti-detection and evasion techniques.

**Features:**
- Device fingerprint injection
- WebDriver property masking
- Canvas fingerprint randomization
- Random scroll behavior simulation
- Mouse movement simulation
- Slider captcha solving

**Key Methods:**
- `initialize()`: Set up anti-detection measures
- `random_scroll_behavior()`: Simulate human scrolling
- `random_mouse_movement()`: Simulate mouse movements
- `handle_slider_captcha()`: Solve slider captchas
- `simulate_read_time()`: Simulate content reading time

### Layer 3: Matcher Layer (DouyinMatcher)
Intelligent content matching and filtering.

**Features:**
- Multi-modal matching (title, description, hashtags)
- Keyword-based filtering
- Engagement metrics filtering
- Time-based filtering
- Custom threshold configuration

**Key Methods:**
- `match_video()`: Match video against criteria

### Layer 4: Interaction Layer (DouyinInteraction)
Handles user interaction data collection.

**Features:**
- Nested comment collection
- Reply thread parsing
- User profile extraction
- Engagement data collection

**Key Methods:**
- `get_video_comments()`: Collect comments with replies
- `get_creator_info()`: Get detailed creator profile

## Error Handling

The spider includes comprehensive error handling:

```python
try:
    async with spider.session():
        videos = await spider.search("keyword", max_results=10)
except Exception as e:
    print(f"Error: {e}")
    # Spider will log detailed error information
```

### Common Issues

1. **Captcha Detection**: The spider includes automatic slider captcha solving, but some captchas may require manual intervention.

2. **Rate Limiting**: If you encounter rate limiting, increase delays:
   ```python
   config.anti_crawl.request_delay_min = 3.0
   config.anti_crawl.request_delay_max = 7.0
   ```

3. **Login Required**: Some content requires login. Use the `login()` method or provide cookies.

4. **Network Errors**: The spider includes retry logic. Adjust `max_retries` if needed.

## Performance Considerations

- **Concurrency**: The spider runs single-threaded by design to avoid detection. For parallel collection, run multiple spider instances.
- **Memory**: Each spider instance uses ~200-500MB of memory.
- **Speed**: Expect ~5-10 videos per minute with full details to maintain stealth.

## Best Practices

1. **Use Delays**: Always use reasonable delays between requests
2. **Rotate Proxies**: Use proxy rotation for large-scale collection
3. **Monitor Logs**: Check logs for warnings and errors
4. **Respect robots.txt**: Follow platform guidelines
5. **Save Cookies**: Reuse cookies to avoid repeated logins
6. **Handle Errors**: Implement proper error handling and retries

## Integration with OmniSense

The Douyin spider integrates seamlessly with the OmniSense system:

```python
from omnisense import OmniSense

# Use through OmniSense main interface
omni = OmniSense()

# Collect data
result = omni.collect(
    platform="douyin",
    keyword="AI编程",
    max_count=100
)

# Analyze with agents
analysis = omni.analyze(
    data=result,
    agents=["analyst", "creator"]
)

# Generate report
omni.generate_report(
    analysis=analysis,
    format="pdf",
    output="douyin_analysis.pdf"
)
```

## License

This implementation is part of the OmniSense project and follows the MIT License.

## Disclaimer

This tool is for educational and research purposes only. Users must:
1. Respect Douyin's Terms of Service
2. Only collect publicly available data
3. Comply with local laws and regulations
4. Use reasonable rate limits
5. Not use for commercial purposes without permission

## Support

For issues, questions, or contributions:
- GitHub Issues: [Report issues](https://github.com/bingdongni/omnisense/issues)
- Documentation: [Full docs](https://github.com/bingdongni/omnisense/docs)
- Email: bingdongni@example.com
