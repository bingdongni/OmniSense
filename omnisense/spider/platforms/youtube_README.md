# YouTube Spider - 完整4层架构实现

## 概述

完整的YouTube平台爬虫实现，支持API和爬虫双模式，实现了完整的4层架构设计。

**代码行数**: 2211行

## 四层架构

### Layer 1: Spider Layer (数据爬取层)

**核心功能**:
- ✅ 视频搜索（关键词、排序、时长、上传时间过滤）
- ✅ 频道信息（订阅数、视频数、频道描述）
- ✅ 视频详情（标题、描述、标签、统计数据、时长）
- ✅ 评论获取（含嵌套回复）
- ✅ 字幕提取（多语言支持）
- ✅ Trending热门视频
- ✅ 播放列表管理

**支持的API端点**:
- `search()` - 视频搜索
- `get_user_profile()` - 频道信息
- `get_user_posts()` - 频道视频列表
- `get_post_detail()` - 视频详情
- `get_comments()` - 评论获取（含回复）
- `get_captions()` - 字幕列表
- `download_caption()` - 字幕下载
- `get_trending_videos()` - 热门视频
- `get_playlist()` - 播放列表

### Layer 2: Anti-Crawl Layer (反反爬层)

**反爬技术**:
- ✅ **YouTube Data API v3集成**
  - 多API Key轮换
  - 配额管理（10000单位/天）
  - 自动配额重置

- ✅ **innertube API集成**
  - 无配额限制
  - 动态配置提取
  - 请求签名生成

- ✅ **设备指纹伪装**
  - 随机设备ID
  - 硬件参数模拟
  - Canvas指纹混淆

- ✅ **Webdriver检测绕过**
  - navigator.webdriver隐藏
  - Chrome runtime注入
  - Permissions API模拟

- ✅ **Cookie认证**
  - 同意对话框自动处理
  - Cookie持久化
  - Session管理

- ✅ **年龄限制绕过**
  - 自动同意年龄验证
  - 受限内容访问

**双模式支持**:
- API模式：优先使用YouTube Data API v3
- 爬虫模式：API失败时自动降级到网页爬取

### Layer 3: Matcher Layer (智能匹配层)

**过滤维度**:
- ✅ **统计数据过滤**
  - 观看数范围 (min_views, max_views)
  - 点赞数范围 (min_likes, max_likes)
  - 评论数范围 (min_comments, max_comments)

- ✅ **视频时长过滤**
  - 最短时长 (min_duration)
  - 最长时长 (max_duration)
  - 短/中/长视频分类

- ✅ **上传时间过滤**
  - 开始日期 (start_date)
  - 结束日期 (end_date)
  - 时间范围筛选

- ✅ **频道订阅数过滤**
  - 最少订阅数 (min_subscribers)
  - 最多订阅数 (max_subscribers)

- ✅ **语言过滤**
  - 多语言支持
  - 语言代码匹配

- ✅ **字幕可用性过滤**
  - 要求字幕存在 (require_captions)
  - 特定语言字幕 (caption_languages)
  - 自动生成/人工字幕区分

**使用示例**:
```python
filters = {
    'min_views': 10000,
    'max_views': 1000000,
    'min_duration': 300,  # 5分钟
    'max_duration': 1800,  # 30分钟
    'languages': ['en', 'zh'],
    'require_captions': True,
}
filtered_videos = spider.matcher.filter_videos(videos, filters)
```

### Layer 4: Interaction Layer (互动处理层)

**互动功能**:
- ✅ **点赞/点踩**
  - `like_video()` - 视频点赞
  - `dislike_video()` - 视频点踩
  - 重复点赞检测

- ✅ **评论发布**
  - `comment_on_video()` - 发布评论
  - 评论框自动定位
  - 评论内容填充

- ✅ **订阅管理**
  - `subscribe_to_channel()` - 订阅频道
  - `unsubscribe_from_channel()` - 取消订阅
  - 订阅状态检测

- ✅ **播放列表操作**
  - `add_to_playlist()` - 添加到播放列表
  - `create_playlist()` - 创建播放列表
  - 播放列表管理

**注意**: 所有互动功能需要登录状态

## 高级特性

### 1. 搜索高级过滤
```python
videos = await spider.search(
    keyword="python tutorial",
    max_results=50,
    sort_by="viewCount",  # relevance, date, viewCount, rating
    duration="medium",     # short(<4min), medium(4-20min), long(>20min)
    upload_date="week",    # hour, today, week, month, year
)
```

### 2. 字幕下载
```python
# 获取字幕列表
captions = await spider.get_captions(video_id, languages=['en', 'zh'])

# 下载字幕内容
for caption in captions:
    content = await spider.download_caption(caption['url'])
    print(content)
```

### 3. 评论回复获取
```python
# 获取评论（包含回复）
comments = await spider.get_comments(
    post_id=video_id,
    max_comments=100,
    include_replies=True
)

# 区分主评论和回复
for comment in comments:
    if 'parent_id' in comment:
        print(f"  └─ Reply: {comment['content']}")
    else:
        print(f"Comment: {comment['content']}")
```

### 4. API配额管理
```python
# 查看配额使用情况
print(f"API配额使用: {spider.anti_crawl.quota_usage}")

# 强制使用爬虫模式
spider.prefer_api = False
```

## 使用示例

### 基础使用
```python
import asyncio
from omnisense.spider.platforms.youtube import YouTubeSpider

async def main():
    spider = YouTubeSpider(headless=True)

    async with spider.session():
        # 搜索视频
        videos = await spider.search("AI tutorial", max_results=10)

        # 获取视频详情
        detail = await spider.get_post_detail(videos[0]['id'])

        # 获取评论
        comments = await spider.get_comments(videos[0]['id'])

        print(f"找到 {len(videos)} 个视频")
        print(f"第一个视频: {detail['title']}")
        print(f"评论数: {len(comments)}")

asyncio.run(main())
```

### 带过滤的搜索
```python
from omnisense.spider.platforms.youtube import search_youtube_videos

videos = await search_youtube_videos(
    keyword="python programming",
    max_results=50,
    filters={
        'min_views': 100000,
        'min_duration': 600,  # 至少10分钟
        'require_captions': True,
        'languages': ['en']
    }
)
```

### 字幕下载
```python
from omnisense.spider.platforms.youtube import download_youtube_caption

# 下载英文字幕
caption_text = await download_youtube_caption(
    video_id='dQw4w9WgXcQ',
    language='en'
)
```

## 配置说明

### API Keys配置
在配置文件中添加YouTube API Keys：

```yaml
youtube_api_keys:
  - "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
  - "AIzaSyYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"
  - "AIzaSyZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
```

### 代理配置
```python
spider = YouTubeSpider(
    headless=True,
    proxy="http://proxy.example.com:8080"
)
```

## 错误处理

所有方法都包含完整的错误处理：
- API失败自动降级到爬虫模式
- 网络错误自动重试
- 超时处理
- 详细日志记录

## 性能优化

1. **API优先策略**: 优先使用YouTube Data API，速度快且稳定
2. **配额管理**: 自动轮换API Key，避免配额耗尽
3. **innertube降级**: API失败时使用innertube API
4. **爬虫兜底**: 最终降级到网页爬取
5. **并发控制**: 合理的请求延迟和速率限制

## 限制说明

1. **API配额**: YouTube Data API每天10000单位配额
2. **登录要求**: 互动功能（点赞、评论、订阅）需要登录
3. **年龄限制**: 部分视频可能需要年龄验证
4. **区域限制**: 某些视频可能有地理位置限制
5. **私有视频**: 无法访问私有或未列出的视频

## 技术栈

- **Playwright**: 浏览器自动化
- **aiohttp**: 异步HTTP请求
- **YouTube Data API v3**: 官方API
- **innertube API**: YouTube内部API

## 测试

运行测试：
```bash
python -m omnisense.spider.platforms.youtube
```

测试覆盖：
- ✅ 视频搜索
- ✅ 视频详情获取
- ✅ 评论获取
- ✅ 字幕提取
- ✅ 热门视频
- ✅ 播放列表

## 许可证

MIT License

---

**作者**: OmniSense Team
**版本**: 1.0.0
**最后更新**: 2026-01-14
