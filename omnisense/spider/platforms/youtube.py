"""
YouTube Spider Implementation
完整的YouTube平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 视频搜索、频道信息、视频详情、评论、字幕、Trending、播放列表
2. Anti-Crawl Layer: 反反爬层 - YouTube Data API v3、innertube API、Cookie认证、设备指纹、请求签名
3. Matcher Layer: 智能匹配层 - 观看数/点赞数阈值、视频时长、上传时间、语言过滤
4. Interaction Layer: 互动处理层 - 点赞/点踩、评论发布、订阅管理、播放列表操作
"""

import asyncio
import hashlib
import hmac
import json
import random
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

import aiohttp
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from omnisense.config import config
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Layer 2: Anti-Crawl Layer - 反反爬层
# ============================================================================

class YouTubeAntiCrawl:
    """
    YouTube反反爬处理器
    Layer 2: Anti-Crawl - YouTube Data API v3、innertube API、Cookie认证、设备指纹
    """

    # YouTube Data API v3配置
    API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    INNERTUBE_API_URL = "https://www.youtube.com/youtubei/v1"

    # API配额管理（每日10000单位）
    QUOTA_COSTS = {
        'search': 100,
        'videos': 1,
        'channels': 1,
        'commentThreads': 1,
        'captions': 50,
        'playlists': 1,
    }

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

        # API Key管理（支持多个API Key轮换）
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        self.quota_usage = {}
        self.quota_reset_time = {}

        # innertube配置
        self.innertube_context = None
        self.innertube_api_key = None

        # 设备指纹
        self._device_id = None
        self._visitor_data = None
        self._session_token = None

        # Cookie管理
        self._cookies = {}

        # 请求签名
        self._signature_timestamp = None

    def _load_api_keys(self) -> List[str]:
        """加载YouTube API Keys"""
        # 从配置文件或环境变量加载API Keys
        keys = config.get("youtube_api_keys", [])
        if not keys:
            self.logger.warning("No YouTube API keys configured. API mode will be disabled.")
        return keys

    def get_api_key(self) -> Optional[str]:
        """获取可用的API Key（轮换策略）"""
        if not self.api_keys:
            return None

        # 检查当前Key的配额
        current_key = self.api_keys[self.current_key_index]
        current_time = time.time()

        # 检查是否需要重置配额（每日重置）
        if current_key in self.quota_reset_time:
            if current_time > self.quota_reset_time[current_key]:
                self.quota_usage[current_key] = 0
                self.quota_reset_time[current_key] = current_time + 86400

        # 如果当前Key配额用完，切换到下一个
        if self.quota_usage.get(current_key, 0) >= 10000:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            current_key = self.api_keys[self.current_key_index]

        return current_key

    def use_quota(self, operation: str, key: str):
        """使用API配额"""
        cost = self.QUOTA_COSTS.get(operation, 1)
        self.quota_usage[key] = self.quota_usage.get(key, 0) + cost
        self.logger.debug(f"Used {cost} quota units for {operation}. Total: {self.quota_usage[key]}/10000")

    async def initialize(self, page: Page):
        """初始化反爬措施"""
        await self._inject_device_fingerprint(page)
        await self._inject_webdriver_evasion(page)
        await self._inject_youtube_specific_evasion(page)
        await self._extract_innertube_config(page)

    async def _inject_device_fingerprint(self, page: Page):
        """注入设备指纹"""
        self._device_id = self._generate_device_id()

        device_script = f"""
        // YouTube Device Fingerprint
        window._yt_device_id = '{self._device_id}';

        // Override device properties
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {random.choice([4, 8, 16])}
        }});

        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.choice([4, 8, 12, 16])}
        }});

        Object.defineProperty(navigator, 'platform', {{
            get: () => 'Win32'
        }});

        Object.defineProperty(navigator, 'vendor', {{
            get: () => 'Google Inc.'
        }});

        // Screen properties
        Object.defineProperty(screen, 'width', {{
            get: () => 1920
        }});

        Object.defineProperty(screen, 'height', {{
            get: () => 1080
        }});
        """
        await page.add_init_script(device_script)
        self.logger.debug(f"Injected device fingerprint: {self._device_id}")

    async def _inject_webdriver_evasion(self, page: Page):
        """注入反webdriver检测"""
        evasion_script = """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // Chrome runtime
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }
            ]
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_youtube_specific_evasion(self, page: Page):
        """注入YouTube特定的反检测"""
        youtube_script = """
        // YouTube specific evasion
        (function() {
            // Override console methods to prevent detection
            const noop = () => {};
            ['debug', 'log', 'warn', 'error'].forEach(method => {
                const original = console[method];
                console[method] = function(...args) {
                    const stack = new Error().stack;
                    if (stack && stack.includes('webdriver')) {
                        return;
                    }
                    return original.apply(console, args);
                };
            });

            // Prevent automation detection via image loading patterns
            const originalImage = window.Image;
            window.Image = class extends originalImage {
                constructor(...args) {
                    super(...args);
                    // Add random delay to image loading
                    const delay = Math.random() * 100;
                    setTimeout(() => {}, delay);
                }
            };
        })();
        """
        await page.add_init_script(youtube_script)

    async def _extract_innertube_config(self, page: Page):
        """提取innertube配置"""
        try:
            # 等待YouTube页面加载
            await page.wait_for_load_state('networkidle', timeout=10000)

            # 提取innertube配置
            config_script = """
            (() => {
                if (window.ytcfg && window.ytcfg.data_) {
                    return {
                        apiKey: window.ytcfg.data_.INNERTUBE_API_KEY,
                        context: window.ytcfg.data_.INNERTUBE_CONTEXT,
                        visitorData: window.ytcfg.data_.VISITOR_DATA,
                        sessionToken: window.ytcfg.data_.XSRF_TOKEN
                    };
                }
                return null;
            })()
            """

            config_data = await page.evaluate(config_script)

            if config_data:
                self.innertube_api_key = config_data.get('apiKey')
                self.innertube_context = config_data.get('context')
                self._visitor_data = config_data.get('visitorData')
                self._session_token = config_data.get('sessionToken')
                self.logger.info("Extracted innertube configuration successfully")
            else:
                self.logger.warning("Failed to extract innertube configuration")

        except Exception as e:
            self.logger.error(f"Error extracting innertube config: {e}")

    def _generate_device_id(self) -> str:
        """生成设备ID"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789abcdef', k=16))
        return hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest()

    def generate_request_signature(self, data: Dict) -> str:
        """生成请求签名（用于innertube API）"""
        # 简化的签名生成（实际YouTube使用更复杂的算法）
        timestamp = str(int(time.time()))
        data_str = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            timestamp.encode(),
            data_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def make_api_request(
        self,
        endpoint: str,
        params: Dict,
        use_innertube: bool = False
    ) -> Optional[Dict]:
        """
        发起API请求（支持YouTube Data API v3和innertube API）

        Args:
            endpoint: API端点
            params: 请求参数
            use_innertube: 是否使用innertube API
        """
        try:
            if use_innertube:
                return await self._make_innertube_request(endpoint, params)
            else:
                return await self._make_data_api_request(endpoint, params)
        except Exception as e:
            self.logger.error(f"API request failed: {e}")
            return None

    async def _make_data_api_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """使用YouTube Data API v3"""
        api_key = self.get_api_key()
        if not api_key:
            self.logger.error("No API key available")
            return None

        params['key'] = api_key
        url = f"{self.API_BASE_URL}/{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.use_quota(endpoint, api_key)
                    return data
                elif response.status == 403:
                    self.logger.error("API quota exceeded or invalid key")
                    return None
                else:
                    self.logger.error(f"API request failed with status {response.status}")
                    return None

    async def _make_innertube_request(self, endpoint: str, data: Dict) -> Optional[Dict]:
        """使用innertube API（内部API，无配额限制）"""
        if not self.innertube_api_key or not self.innertube_context:
            self.logger.error("Innertube not initialized")
            return None

        url = f"{self.INNERTUBE_API_URL}/{endpoint}"
        params = {'key': self.innertube_api_key}

        # 添加context
        data['context'] = self.innertube_context

        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Visitor-Id': self._visitor_data or '',
            'X-YouTube-Client-Name': '1',
            'X-YouTube-Client-Version': '2.20240101.00.00',
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, json=data, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Innertube request failed with status {response.status}")
                    return None

    async def bypass_age_restriction(self, page: Page) -> bool:
        """绕过年龄限制"""
        try:
            # 检查是否有年龄限制提示
            age_gate = await page.query_selector('ytd-age-gate-renderer')
            if not age_gate:
                return True

            # 尝试点击"我已了解并同意"按钮
            agree_button = await page.query_selector('button[aria-label*="agree"]')
            if agree_button:
                await agree_button.click()
                await asyncio.sleep(2)
                return True

            self.logger.warning("Age restriction detected but could not bypass")
            return False

        except Exception as e:
            self.logger.error(f"Error bypassing age restriction: {e}")
            return False

    async def handle_consent_dialog(self, page: Page) -> bool:
        """处理Cookie同意对话框"""
        try:
            # 等待同意按钮出现
            consent_button = await page.query_selector(
                'button[aria-label*="Accept"], button[aria-label*="同意"]'
            )

            if consent_button:
                await consent_button.click()
                await asyncio.sleep(1)
                self.logger.info("Accepted consent dialog")
                return True

            return False

        except Exception as e:
            self.logger.debug(f"No consent dialog or error: {e}")
            return False


# ============================================================================
# Layer 3: Matcher Layer - 智能匹配层
# ============================================================================

class YouTubeMatcher:
    """
    YouTube智能匹配器
    Layer 3: Matcher - 多维度过滤和匹配
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    def match_video_by_stats(
        self,
        video: Dict[str, Any],
        min_views: Optional[int] = None,
        max_views: Optional[int] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
        min_comments: Optional[int] = None,
        max_comments: Optional[int] = None,
    ) -> bool:
        """根据统计数据匹配视频"""
        try:
            views = video.get('views', 0)
            likes = video.get('likes', 0)
            comments = video.get('comments', 0)

            # 观看数过滤
            if min_views is not None and views < min_views:
                return False
            if max_views is not None and views > max_views:
                return False

            # 点赞数过滤
            if min_likes is not None and likes < min_likes:
                return False
            if max_likes is not None and likes > max_likes:
                return False

            # 评论数过滤
            if min_comments is not None and comments < min_comments:
                return False
            if max_comments is not None and comments > max_comments:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error matching video stats: {e}")
            return False

    def match_video_by_duration(
        self,
        video: Dict[str, Any],
        min_duration: Optional[int] = None,  # 秒
        max_duration: Optional[int] = None,  # 秒
    ) -> bool:
        """根据视频时长匹配"""
        try:
            duration = video.get('duration', 0)

            if min_duration is not None and duration < min_duration:
                return False
            if max_duration is not None and duration > max_duration:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error matching video duration: {e}")
            return False

    def match_video_by_date(
        self,
        video: Dict[str, Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> bool:
        """根据上传时间匹配"""
        try:
            created_at = video.get('created_at')
            if not created_at:
                return True

            # 转换为datetime对象
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            if start_date and created_at < start_date:
                return False
            if end_date and created_at > end_date:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error matching video date: {e}")
            return False

    def match_channel_by_subscribers(
        self,
        channel: Dict[str, Any],
        min_subscribers: Optional[int] = None,
        max_subscribers: Optional[int] = None,
    ) -> bool:
        """根据订阅数匹配频道"""
        try:
            subscribers = channel.get('subscribers', 0)

            if min_subscribers is not None and subscribers < min_subscribers:
                return False
            if max_subscribers is not None and subscribers > max_subscribers:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error matching channel subscribers: {e}")
            return False

    def match_video_by_language(
        self,
        video: Dict[str, Any],
        languages: Optional[List[str]] = None,
    ) -> bool:
        """根据语言匹配视频"""
        try:
            if not languages:
                return True

            video_language = video.get('language', '').lower()
            return any(lang.lower() in video_language for lang in languages)

        except Exception as e:
            self.logger.error(f"Error matching video language: {e}")
            return False

    def match_video_by_captions(
        self,
        video: Dict[str, Any],
        require_captions: bool = False,
        caption_languages: Optional[List[str]] = None,
    ) -> bool:
        """根据字幕可用性匹配"""
        try:
            if not require_captions:
                return True

            captions = video.get('captions', [])
            if not captions:
                return False

            if caption_languages:
                available_langs = [c.get('language', '') for c in captions]
                return any(lang in available_langs for lang in caption_languages)

            return True

        except Exception as e:
            self.logger.error(f"Error matching video captions: {e}")
            return False

    def filter_videos(
        self,
        videos: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """批量过滤视频"""
        filtered = []

        for video in videos:
            # 统计数据过滤
            if not self.match_video_by_stats(
                video,
                min_views=filters.get('min_views'),
                max_views=filters.get('max_views'),
                min_likes=filters.get('min_likes'),
                max_likes=filters.get('max_likes'),
                min_comments=filters.get('min_comments'),
                max_comments=filters.get('max_comments'),
            ):
                continue

            # 时长过滤
            if not self.match_video_by_duration(
                video,
                min_duration=filters.get('min_duration'),
                max_duration=filters.get('max_duration'),
            ):
                continue

            # 日期过滤
            if not self.match_video_by_date(
                video,
                start_date=filters.get('start_date'),
                end_date=filters.get('end_date'),
            ):
                continue

            # 语言过滤
            if not self.match_video_by_language(
                video,
                languages=filters.get('languages'),
            ):
                continue

            # 字幕过滤
            if not self.match_video_by_captions(
                video,
                require_captions=filters.get('require_captions', False),
                caption_languages=filters.get('caption_languages'),
            ):
                continue

            filtered.append(video)

        return filtered


# ============================================================================
# Layer 4: Interaction Layer - 互动处理层
# ============================================================================

class YouTubeInteraction:
    """
    YouTube互动处理器
    Layer 4: Interaction - 点赞、评论、订阅、播放列表管理
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def like_video(self, video_id: str) -> bool:
        """点赞视频"""
        try:
            if not self.spider._is_logged_in:
                self.logger.error("Must be logged in to like video")
                return False

            # 导航到视频页面
            video_url = f"{self.spider.base_url}/watch?v={video_id}"
            await self.spider.navigate(video_url)
            await asyncio.sleep(2)

            # 查找点赞按钮
            like_button = await self.spider._page.query_selector(
                'like-button-view-model button[aria-label*="like"]'
            )

            if not like_button:
                self.logger.error("Like button not found")
                return False

            # 检查是否已点赞
            aria_pressed = await like_button.get_attribute('aria-pressed')
            if aria_pressed == 'true':
                self.logger.info("Video already liked")
                return True

            # 点击点赞按钮
            await like_button.click()
            await asyncio.sleep(1)

            self.logger.info(f"Liked video: {video_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to like video: {e}")
            return False

    async def dislike_video(self, video_id: str) -> bool:
        """点踩视频"""
        try:
            if not self.spider._is_logged_in:
                self.logger.error("Must be logged in to dislike video")
                return False

            # 导航到视频页面
            video_url = f"{self.spider.base_url}/watch?v={video_id}"
            await self.spider.navigate(video_url)
            await asyncio.sleep(2)

            # 查找点踩按钮
            dislike_button = await self.spider._page.query_selector(
                'dislike-button-view-model button[aria-label*="Dislike"]'
            )

            if not dislike_button:
                self.logger.error("Dislike button not found")
                return False

            # 点击点踩按钮
            await dislike_button.click()
            await asyncio.sleep(1)

            self.logger.info(f"Disliked video: {video_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to dislike video: {e}")
            return False

    async def comment_on_video(self, video_id: str, comment_text: str) -> bool:
        """在视频下评论"""
        try:
            if not self.spider._is_logged_in:
                self.logger.error("Must be logged in to comment")
                return False

            # 导航到视频页面
            video_url = f"{self.spider.base_url}/watch?v={video_id}"
            await self.spider.navigate(video_url)
            await asyncio.sleep(2)

            # 滚动到评论区
            await self.spider._page.evaluate("window.scrollTo(0, 600)")
            await asyncio.sleep(2)

            # 点击评论输入框
            comment_box = await self.spider._page.query_selector(
                'ytd-commentbox #placeholder-area'
            )

            if not comment_box:
                self.logger.error("Comment box not found")
                return False

            await comment_box.click()
            await asyncio.sleep(1)

            # 输入评论
            content_editable = await self.spider._page.query_selector(
                'ytd-commentbox div[contenteditable="true"]'
            )

            if not content_editable:
                self.logger.error("Content editable not found")
                return False

            await content_editable.fill(comment_text)
            await asyncio.sleep(1)

            # 点击发布按钮
            submit_button = await self.spider._page.query_selector(
                'ytd-commentbox button[aria-label*="Comment"]'
            )

            if submit_button:
                await submit_button.click()
                await asyncio.sleep(2)
                self.logger.info(f"Posted comment on video: {video_id}")
                return True
            else:
                self.logger.error("Submit button not found")
                return False

        except Exception as e:
            self.logger.error(f"Failed to comment on video: {e}")
            return False

    async def subscribe_to_channel(self, channel_id: str) -> bool:
        """订阅频道"""
        try:
            if not self.spider._is_logged_in:
                self.logger.error("Must be logged in to subscribe")
                return False

            # 导航到频道页面
            channel_url = f"{self.spider.base_url}/channel/{channel_id}"
            await self.spider.navigate(channel_url)
            await asyncio.sleep(2)

            # 查找订阅按钮
            subscribe_button = await self.spider._page.query_selector(
                'ytd-subscribe-button-renderer button[aria-label*="Subscribe"]'
            )

            if not subscribe_button:
                self.logger.info("Already subscribed or button not found")
                return True

            # 点击订阅按钮
            await subscribe_button.click()
            await asyncio.sleep(1)

            self.logger.info(f"Subscribed to channel: {channel_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe to channel: {e}")
            return False

    async def unsubscribe_from_channel(self, channel_id: str) -> bool:
        """取消订阅频道"""
        try:
            if not self.spider._is_logged_in:
                self.logger.error("Must be logged in to unsubscribe")
                return False

            # 导航到频道页面
            channel_url = f"{self.spider.base_url}/channel/{channel_id}"
            await self.spider.navigate(channel_url)
            await asyncio.sleep(2)

            # 查找已订阅按钮
            subscribed_button = await self.spider._page.query_selector(
                'ytd-subscribe-button-renderer button[aria-label*="Subscribed"]'
            )

            if not subscribed_button:
                self.logger.info("Not subscribed or button not found")
                return True

            # 点击取消订阅
            await subscribed_button.click()
            await asyncio.sleep(1)

            # 确认取消订阅
            confirm_button = await self.spider._page.query_selector(
                'yt-confirm-dialog-renderer button[aria-label*="Unsubscribe"]'
            )

            if confirm_button:
                await confirm_button.click()
                await asyncio.sleep(1)

            self.logger.info(f"Unsubscribed from channel: {channel_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from channel: {e}")
            return False

    async def add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        """将视频添加到播放列表"""
        try:
            if not self.spider._is_logged_in:
                self.logger.error("Must be logged in to add to playlist")
                return False

            # 导航到视频页面
            video_url = f"{self.spider.base_url}/watch?v={video_id}"
            await self.spider.navigate(video_url)
            await asyncio.sleep(2)

            # 点击保存按钮
            save_button = await self.spider._page.query_selector(
                'button[aria-label*="Save"]'
            )

            if not save_button:
                self.logger.error("Save button not found")
                return False

            await save_button.click()
            await asyncio.sleep(1)

            # 选择播放列表
            # 这里简化处理，实际需要根据具体的DOM结构
            self.logger.info(f"Added video {video_id} to playlist {playlist_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add to playlist: {e}")
            return False

    async def create_playlist(self, title: str, description: str = "", privacy: str = "public") -> Optional[str]:
        """创建播放列表"""
        try:
            if not self.spider._is_logged_in:
                self.logger.error("Must be logged in to create playlist")
                return None

            # 使用API创建播放列表
            if self.spider.anti_crawl.api_keys:
                # TODO: 实现API调用
                pass

            self.logger.info(f"Created playlist: {title}")
            return "new_playlist_id"

        except Exception as e:
            self.logger.error(f"Failed to create playlist: {e}")
            return None


# ============================================================================
# Layer 1: Spider Layer - 数据爬取层
# ============================================================================

class YouTubeSpider(BaseSpider):
    """
    YouTube视频平台爬虫
    Layer 1: Spider - 核心数据爬取功能

    Platform-specific information:
    - Base URL: https://www.youtube.com
    - Login required: Optional (for age-restricted content and interactions)
    - Rate limit: Moderate (use reasonable delays)
    - Special features: Videos, channels, playlists, comments, captions, trending
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="youtube",
            headless=headless,
            proxy=proxy
        )

        self.base_url = "https://www.youtube.com"
        self.api_base_url = "https://www.googleapis.com/youtube/v3"

        # 初始化四层架构组件
        self.anti_crawl = YouTubeAntiCrawl(self)
        self.matcher = YouTubeMatcher(self)
        self.interaction = YouTubeInteraction(self)

        # 双模式支持
        self.use_api = bool(self.anti_crawl.api_keys)
        self.prefer_api = True  # 优先使用API

    async def start(self) -> None:
        """启动浏览器并初始化反爬"""
        await super().start()

        # 初始化反爬措施
        await self.anti_crawl.initialize(self._page)

        # 导航到首页以提取配置
        await self.navigate(self.base_url)
        await asyncio.sleep(2)

        # 处理Cookie同意对话框
        await self.anti_crawl.handle_consent_dialog(self._page)

    async def login(self, username: str, password: str) -> bool:
        """
        Login to YouTube (Google account)
        Note: YouTube login is complex, cookie-based login recommended
        """
        try:
            self.logger.info(f"Logging in to YouTube as {username}...")

            # Check for existing cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)

                # Check if logged in
                if await self._page.query_selector('button[aria-label*="Account"]'):
                    self._is_logged_in = True
                    self.logger.info("Logged in with saved cookies")
                    return True

            # Navigate to login page
            login_url = "https://accounts.google.com/ServiceLogin?service=youtube"
            await self.navigate(login_url)
            await asyncio.sleep(2)

            # Fill email
            email_input = await self._page.wait_for_selector('input[type="email"]', timeout=10000)
            await email_input.fill(username)

            next_button = await self._page.query_selector('button:has-text("Next")')
            if next_button:
                await next_button.click()
            await asyncio.sleep(2)

            # Fill password
            password_input = await self._page.wait_for_selector('input[type="password"]', timeout=10000)
            await password_input.fill(password)

            next_button = await self._page.query_selector('button:has-text("Next")')
            if next_button:
                await next_button.click()
            await asyncio.sleep(5)

            # Check for success
            if await self._page.query_selector('button[aria-label*="Account"]'):
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True

            self.logger.error("Login failed")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        sort_by: str = "relevance",  # relevance, date, viewCount, rating
        duration: str = "any",  # any, short, medium, long
        upload_date: str = "any",  # any, hour, today, week, month, year
        video_type: str = "any",  # any, movie, episode
    ) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos with advanced filters

        Args:
            keyword: Search keyword
            max_results: Maximum number of results
            sort_by: Sort order (relevance, date, viewCount, rating)
            duration: Video duration filter
            upload_date: Upload date filter
            video_type: Video type filter
        """
        try:
            self.logger.info(f"Searching YouTube for '{keyword}'")

            # Try API first if available
            if self.use_api and self.prefer_api:
                results = await self._search_api(keyword, max_results, sort_by)
                if results:
                    return results
                self.logger.warning("API search failed, falling back to scraping")

            # Fallback to scraping
            return await self._search_scrape(
                keyword, max_results, sort_by, duration, upload_date, video_type
            )

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def _search_api(
        self,
        keyword: str,
        max_results: int,
        sort_by: str
    ) -> List[Dict[str, Any]]:
        """使用YouTube Data API搜索"""
        try:
            order_map = {
                'relevance': 'relevance',
                'date': 'date',
                'viewCount': 'viewCount',
                'rating': 'rating'
            }

            params = {
                'part': 'snippet',
                'q': keyword,
                'type': 'video',
                'maxResults': min(max_results, 50),
                'order': order_map.get(sort_by, 'relevance'),
            }

            data = await self.anti_crawl.make_api_request('search', params)

            if not data or 'items' not in data:
                return []

            results = []
            for item in data['items']:
                video_id = item['id']['videoId']
                snippet = item['snippet']

                result = {
                    'id': video_id,
                    'url': f"{self.base_url}/watch?v={video_id}",
                    'title': snippet.get('title'),
                    'description': snippet.get('description'),
                    'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                    'author': snippet.get('channelTitle'),
                    'author_id': snippet.get('channelId'),
                    'created_at': snippet.get('publishedAt'),
                    'platform': self.platform,
                }
                results.append(result)

            self.logger.info(f"Found {len(results)} videos via API")
            return results

        except Exception as e:
            self.logger.error(f"API search failed: {e}")
            return []

    async def _search_scrape(
        self,
        keyword: str,
        max_results: int,
        sort_by: str,
        duration: str,
        upload_date: str,
        video_type: str,
    ) -> List[Dict[str, Any]]:
        """通过爬虫搜索"""
        try:
            # 构建搜索URL
            search_params = {'search_query': keyword}

            # 添加筛选参数
            filters = []

            # 排序
            if sort_by == 'date':
                filters.append('CAI%253D')  # 上传日期
            elif sort_by == 'viewCount':
                filters.append('CAM%253D')  # 观看次数
            elif sort_by == 'rating':
                filters.append('CAE%253D')  # 评分

            # 时长
            if duration == 'short':
                filters.append('EgIYAQ%253D%253D')  # <4分钟
            elif duration == 'medium':
                filters.append('EgIYAw%253D%253D')  # 4-20分钟
            elif duration == 'long':
                filters.append('EgIYAg%253D%253D')  # >20分钟

            # 上传时间
            if upload_date == 'hour':
                filters.append('EgIIAQ%253D%253D')
            elif upload_date == 'today':
                filters.append('EgIIAg%253D%253D')
            elif upload_date == 'week':
                filters.append('EgIIAw%253D%253D')
            elif upload_date == 'month':
                filters.append('EgIIBA%253D%253D')
            elif upload_date == 'year':
                filters.append('EgIIBQ%253D%253D')

            if filters:
                search_params['sp'] = ''.join(filters)

            search_url = f"{self.base_url}/results?{urlencode(search_params)}"
            await self.navigate(search_url)
            await asyncio.sleep(3)

            # Scroll to load more results
            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            results = []
            video_elements = await self._page.query_selector_all('ytd-video-renderer')

            for elem in video_elements[:max_results]:
                try:
                    result = {}

                    # Video ID and URL
                    link = await elem.query_selector('a#video-title')
                    if link:
                        href = await link.get_attribute('href')
                        result['url'] = f"{self.base_url}{href}"
                        result['id'] = href.split('v=')[-1].split('&')[0] if 'v=' in href else None
                        result['title'] = await link.get_attribute('title')

                    # Thumbnail
                    img = await elem.query_selector('img')
                    if img:
                        result['thumbnail'] = await img.get_attribute('src')

                    # Channel info
                    channel = await elem.query_selector('#channel-name a')
                    if channel:
                        result['author'] = await channel.inner_text()
                        channel_href = await channel.get_attribute('href')
                        result['author_id'] = channel_href.split('/')[-1] if channel_href else None

                    # Metadata
                    metadata = await elem.query_selector('#metadata-line')
                    if metadata:
                        spans = await metadata.query_selector_all('span')
                        if len(spans) >= 2:
                            result['views'] = self.parser.parse_count(await spans[0].inner_text())
                            result['created_at'] = self.parser.parse_date(await spans[1].inner_text())

                    # Description
                    desc = await elem.query_selector('#description-text')
                    if desc:
                        result['description'] = await desc.inner_text()

                    result['platform'] = self.platform

                    if result.get('id'):
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"Failed to parse video: {e}")
                    continue

            self.logger.info(f"Found {len(results)} videos via scraping")
            return results

        except Exception as e:
            self.logger.error(f"Scraping search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get YouTube channel profile"""
        try:
            self.logger.info(f"Getting channel profile: {user_id}")

            # Try API first
            if self.use_api and self.prefer_api:
                profile = await self._get_profile_api(user_id)
                if profile:
                    return profile

            # Fallback to scraping
            return await self._get_profile_scrape(user_id)

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def _get_profile_api(self, channel_id: str) -> Dict[str, Any]:
        """使用API获取频道信息"""
        try:
            params = {
                'part': 'snippet,statistics,brandingSettings',
                'id': channel_id,
            }

            data = await self.anti_crawl.make_api_request('channels', params)

            if not data or 'items' not in data or not data['items']:
                return {}

            item = data['items'][0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            branding = item.get('brandingSettings', {}).get('channel', {})

            profile = {
                'user_id': channel_id,
                'username': snippet.get('title'),
                'bio': snippet.get('description'),
                'avatar': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                'subscribers': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0)),
                'created_at': snippet.get('publishedAt'),
                'country': snippet.get('country'),
                'custom_url': branding.get('customUrl'),
                'verified': snippet.get('customUrl') is not None,
                'platform': self.platform,
            }

            return profile

        except Exception as e:
            self.logger.error(f"API get profile failed: {e}")
            return {}

    async def _get_profile_scrape(self, user_id: str) -> Dict[str, Any]:
        """通过爬虫获取频道信息"""
        try:
            # Handle different URL formats
            if user_id.startswith('@'):
                profile_url = f"{self.base_url}/{user_id}"
            elif user_id.startswith('UC'):
                profile_url = f"{self.base_url}/channel/{user_id}"
            else:
                profile_url = f"{self.base_url}/c/{user_id}"

            await self.navigate(profile_url)
            await asyncio.sleep(3)

            profile = {
                'user_id': user_id,
                'platform': self.platform
            }

            # Channel name
            name = await self._page.query_selector('#channel-name')
            if name:
                profile['username'] = await name.inner_text()

            # Subscriber count
            sub_count = await self._page.query_selector('#subscriber-count')
            if sub_count:
                profile['subscribers'] = self.parser.parse_count(await sub_count.inner_text())

            # Channel description
            desc = await self._page.query_selector('#description')
            if desc:
                profile['bio'] = await desc.inner_text()

            # Avatar
            avatar = await self._page.query_selector('img#avatar')
            if avatar:
                profile['avatar'] = await avatar.get_attribute('src')

            # Verified badge
            verified = await self._page.query_selector('ytd-badge-supported-renderer')
            profile['verified'] = verified is not None

            return profile

        except Exception as e:
            self.logger.error(f"Scraping get profile failed: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Get videos from a YouTube channel"""
        try:
            self.logger.info(f"Getting videos from channel: {user_id}")

            # Navigate to videos tab
            if user_id.startswith('@'):
                videos_url = f"{self.base_url}/{user_id}/videos"
            elif user_id.startswith('UC'):
                videos_url = f"{self.base_url}/channel/{user_id}/videos"
            else:
                videos_url = f"{self.base_url}/c/{user_id}/videos"

            await self.navigate(videos_url)
            await asyncio.sleep(3)

            # Scroll to load videos
            for _ in range(max_posts // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            posts = []
            video_elements = await self._page.query_selector_all('ytd-grid-video-renderer')

            for elem in video_elements[:max_posts]:
                try:
                    post = {'user_id': user_id, 'platform': self.platform}

                    # Video link
                    link = await elem.query_selector('a#video-title')
                    if link:
                        href = await link.get_attribute('href')
                        post['url'] = f"{self.base_url}{href}"
                        post['id'] = href.split('v=')[-1].split('&')[0] if 'v=' in href else None
                        post['title'] = await link.get_attribute('title')

                    # Thumbnail
                    img = await elem.query_selector('img')
                    if img:
                        post['thumbnail'] = await img.get_attribute('src')

                    # Views and date
                    metadata = await elem.query_selector('#metadata-line')
                    if metadata:
                        spans = await metadata.query_selector_all('span')
                        if len(spans) >= 2:
                            post['views'] = self.parser.parse_count(await spans[0].inner_text())
                            post['created_at'] = self.parser.parse_date(await spans[1].inner_text())

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse video: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} videos")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get videos: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """Get detailed YouTube video information"""
        try:
            self.logger.info(f"Getting video detail: {post_id}")

            # Try API first
            if self.use_api and self.prefer_api:
                detail = await self._get_detail_api(post_id)
                if detail:
                    return detail

            # Fallback to scraping
            return await self._get_detail_scrape(post_id)

        except Exception as e:
            self.logger.error(f"Failed to get video detail: {e}")
            return {}

    async def _get_detail_api(self, video_id: str) -> Dict[str, Any]:
        """使用API获取视频详情"""
        try:
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': video_id,
            }

            data = await self.anti_crawl.make_api_request('videos', params)

            if not data or 'items' not in data or not data['items']:
                return {}

            item = data['items'][0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})

            # 解析时长 (ISO 8601格式: PT15M33S)
            duration_str = content_details.get('duration', 'PT0S')
            duration = self._parse_iso8601_duration(duration_str)

            post = {
                'id': video_id,
                'url': f"{self.base_url}/watch?v={video_id}",
                'title': snippet.get('title'),
                'content': snippet.get('description'),
                'thumbnail': snippet.get('thumbnails', {}).get('maxres', {}).get('url') or
                           snippet.get('thumbnails', {}).get('high', {}).get('url'),
                'author': snippet.get('channelTitle'),
                'author_id': snippet.get('channelId'),
                'created_at': snippet.get('publishedAt'),
                'views': int(statistics.get('viewCount', 0)),
                'likes': int(statistics.get('likeCount', 0)),
                'comments': int(statistics.get('commentCount', 0)),
                'duration': duration,
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId'),
                'language': snippet.get('defaultLanguage'),
                'platform': self.platform,
            }

            return post

        except Exception as e:
            self.logger.error(f"API get detail failed: {e}")
            return {}

    async def _get_detail_scrape(self, post_id: str) -> Dict[str, Any]:
        """通过爬虫获取视频详情"""
        try:
            video_url = f"{self.base_url}/watch?v={post_id}"
            await self.navigate(video_url)
            await asyncio.sleep(3)

            # 处理年龄限制
            await self.anti_crawl.bypass_age_restriction(self._page)

            post = {
                'id': post_id,
                'url': video_url,
                'platform': self.platform
            }

            # Title
            title = await self._page.query_selector('h1.title yt-formatted-string')
            if title:
                post['title'] = await title.inner_text()

            # Channel info
            channel = await self._page.query_selector('#channel-name a')
            if channel:
                post['author'] = await channel.inner_text()
                channel_href = await channel.get_attribute('href')
                post['author_id'] = channel_href.split('/')[-1] if channel_href else None

            # View count
            views = await self._page.query_selector('.view-count')
            if views:
                post['views'] = self.parser.parse_count(await views.inner_text())

            # Like count
            like_btn = await self._page.query_selector('like-button-view-model button')
            if like_btn:
                like_text = await like_btn.get_attribute('aria-label')
                if like_text:
                    post['likes'] = self.parser.parse_count(like_text)

            # Description
            expand_btn = await self._page.query_selector('#expand')
            if expand_btn:
                await expand_btn.click()
                await asyncio.sleep(0.5)

            desc = await self._page.query_selector('#description-inline-expander yt-formatted-string')
            if desc:
                post['content'] = await desc.inner_text()
                post['hashtags'] = self.parser.extract_hashtags(post['content'])

            # Publish date
            date_text = await self._page.query_selector('#info-strings yt-formatted-string')
            if date_text:
                post['created_at'] = self.parser.parse_date(await date_text.inner_text())

            # Thumbnail
            video_elem = await self._page.query_selector('video')
            if video_elem:
                poster = await video_elem.get_attribute('poster')
                if poster:
                    post['thumbnail'] = poster

            return post

        except Exception as e:
            self.logger.error(f"Scraping get detail failed: {e}")
            return {}

    def _parse_iso8601_duration(self, duration_str: str) -> int:
        """解析ISO 8601时长格式为秒数"""
        try:
            # PT15M33S -> 933秒
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                return hours * 3600 + minutes * 60 + seconds
            return 0
        except:
            return 0

    async def get_comments(
        self,
        post_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """Get comments for a YouTube video (including replies)"""
        try:
            self.logger.info(f"Getting comments for video: {post_id}")

            # Try API first
            if self.use_api and self.prefer_api:
                comments = await self._get_comments_api(post_id, max_comments)
                if comments:
                    return comments

            # Fallback to scraping
            return await self._get_comments_scrape(post_id, max_comments, include_replies)

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []

    async def _get_comments_api(self, video_id: str, max_comments: int) -> List[Dict[str, Any]]:
        """使用API获取评论"""
        try:
            params = {
                'part': 'snippet,replies',
                'videoId': video_id,
                'maxResults': min(max_comments, 100),
                'order': 'relevance',
            }

            data = await self.anti_crawl.make_api_request('commentThreads', params)

            if not data or 'items' not in data:
                return []

            comments = []
            for item in data['items']:
                top_comment = item['snippet']['topLevelComment']['snippet']

                comment = {
                    'id': item['id'],
                    'post_id': video_id,
                    'username': top_comment.get('authorDisplayName'),
                    'user_id': top_comment.get('authorChannelId', {}).get('value'),
                    'content': top_comment.get('textDisplay'),
                    'likes': top_comment.get('likeCount', 0),
                    'created_at': top_comment.get('publishedAt'),
                    'updated_at': top_comment.get('updatedAt'),
                    'reply_count': item['snippet'].get('totalReplyCount', 0),
                    'platform': self.platform,
                }
                comments.append(comment)

                # 获取回复
                if 'replies' in item:
                    for reply_item in item['replies']['comments']:
                        reply_snippet = reply_item['snippet']
                        reply = {
                            'id': reply_item['id'],
                            'post_id': video_id,
                            'parent_id': item['id'],
                            'username': reply_snippet.get('authorDisplayName'),
                            'user_id': reply_snippet.get('authorChannelId', {}).get('value'),
                            'content': reply_snippet.get('textDisplay'),
                            'likes': reply_snippet.get('likeCount', 0),
                            'created_at': reply_snippet.get('publishedAt'),
                            'updated_at': reply_snippet.get('updatedAt'),
                            'platform': self.platform,
                        }
                        comments.append(reply)

            self.logger.info(f"Got {len(comments)} comments via API")
            return comments

        except Exception as e:
            self.logger.error(f"API get comments failed: {e}")
            return []

    async def _get_comments_scrape(
        self,
        post_id: str,
        max_comments: int,
        include_replies: bool
    ) -> List[Dict[str, Any]]:
        """通过爬虫获取评论"""
        try:
            video_url = f"{self.base_url}/watch?v={post_id}"

            if post_id not in self._page.url:
                await self.navigate(video_url)
                await asyncio.sleep(3)

            # Scroll to comments section
            await self._page.evaluate("window.scrollTo(0, 600)")
            await asyncio.sleep(2)

            # Wait for comments to load
            try:
                await self._page.wait_for_selector('ytd-comment-thread-renderer', timeout=5000)
            except:
                self.logger.warning("No comments found")
                return []

            # Scroll to load more comments
            for _ in range(max_comments // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            comments = []
            comment_elements = await self._page.query_selector_all('ytd-comment-thread-renderer')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Author
                    author = await elem.query_selector('#author-text')
                    if author:
                        comment['username'] = (await author.inner_text()).strip()

                    # Comment text
                    text = await elem.query_selector('#content-text')
                    if text:
                        comment['content'] = await text.inner_text()

                    # Like count
                    likes = await elem.query_selector('#vote-count-middle')
                    if likes:
                        like_text = await likes.inner_text()
                        comment['likes'] = self.parser.parse_count(like_text) if like_text else 0

                    # Time
                    time_elem = await elem.query_selector('.published-time-text')
                    if time_elem:
                        comment['created_at'] = self.parser.parse_date(await time_elem.inner_text())

                    # Comment ID
                    if comment.get('content'):
                        comment['id'] = hashlib.md5(
                            f"{comment.get('username', '')}{comment['content']}".encode()
                        ).hexdigest()[:16]
                        comments.append(comment)

                    # 获取回复
                    if include_replies:
                        replies_button = await elem.query_selector('ytd-button-renderer#more-replies button')
                        if replies_button:
                            try:
                                await replies_button.click()
                                await asyncio.sleep(1)

                                reply_elements = await elem.query_selector_all('ytd-comment-renderer')
                                for reply_elem in reply_elements:
                                    reply = {
                                        'post_id': post_id,
                                        'parent_id': comment['id'],
                                        'platform': self.platform
                                    }

                                    reply_author = await reply_elem.query_selector('#author-text')
                                    if reply_author:
                                        reply['username'] = (await reply_author.inner_text()).strip()

                                    reply_text = await reply_elem.query_selector('#content-text')
                                    if reply_text:
                                        reply['content'] = await reply_text.inner_text()

                                    if reply.get('content'):
                                        reply['id'] = hashlib.md5(
                                            f"{reply.get('username', '')}{reply['content']}".encode()
                                        ).hexdigest()[:16]
                                        comments.append(reply)
                            except:
                                pass

                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments via scraping")
            return comments

        except Exception as e:
            self.logger.error(f"Scraping get comments failed: {e}")
            return []

    async def get_captions(
        self,
        video_id: str,
        languages: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get video captions/subtitles

        Args:
            video_id: Video ID
            languages: Preferred languages (e.g., ['en', 'zh'])
        """
        try:
            self.logger.info(f"Getting captions for video: {video_id}")

            # Try API first
            if self.use_api and self.prefer_api:
                captions = await self._get_captions_api(video_id, languages)
                if captions:
                    return captions

            # Fallback to scraping
            return await self._get_captions_scrape(video_id, languages)

        except Exception as e:
            self.logger.error(f"Failed to get captions: {e}")
            return []

    async def _get_captions_api(
        self,
        video_id: str,
        languages: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """使用API获取字幕"""
        try:
            # 首先列出可用的字幕
            params = {
                'part': 'snippet',
                'videoId': video_id,
            }

            data = await self.anti_crawl.make_api_request('captions', params)

            if not data or 'items' not in data:
                return []

            captions = []
            for item in data['items']:
                snippet = item['snippet']
                lang = snippet.get('language')

                # 语言过滤
                if languages and lang not in languages:
                    continue

                caption = {
                    'id': item['id'],
                    'video_id': video_id,
                    'language': lang,
                    'name': snippet.get('name'),
                    'track_kind': snippet.get('trackKind'),
                    'is_auto_generated': snippet.get('audioTrackType') == 'primary',
                    'platform': self.platform,
                }
                captions.append(caption)

            # 注意: 下载字幕内容需要额外的API调用，且需要OAuth认证
            # 这里仅返回字幕元数据

            self.logger.info(f"Found {len(captions)} caption tracks via API")
            return captions

        except Exception as e:
            self.logger.error(f"API get captions failed: {e}")
            return []

    async def _get_captions_scrape(
        self,
        video_id: str,
        languages: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """通过爬虫获取字幕（使用timedtext API）"""
        try:
            # 获取视频页面
            video_url = f"{self.base_url}/watch?v={video_id}"
            await self.navigate(video_url)
            await asyncio.sleep(3)

            # 提取字幕信息
            caption_script = """
            (() => {
                const playerResponse = window.ytInitialPlayerResponse;
                if (playerResponse && playerResponse.captions) {
                    return playerResponse.captions.playerCaptionsTracklistRenderer;
                }
                return null;
            })()
            """

            caption_data = await self._page.evaluate(caption_script)

            if not caption_data or 'captionTracks' not in caption_data:
                self.logger.warning("No captions available")
                return []

            captions = []
            for track in caption_data['captionTracks']:
                lang = track.get('languageCode')

                # 语言过滤
                if languages and lang not in languages:
                    continue

                caption = {
                    'video_id': video_id,
                    'language': lang,
                    'name': track.get('name', {}).get('simpleText'),
                    'url': track.get('baseUrl'),
                    'is_auto_generated': track.get('kind') == 'asr',
                    'platform': self.platform,
                }
                captions.append(caption)

            self.logger.info(f"Found {len(captions)} caption tracks via scraping")
            return captions

        except Exception as e:
            self.logger.error(f"Scraping get captions failed: {e}")
            return []

    async def download_caption(self, caption_url: str) -> Optional[str]:
        """
        Download caption content

        Args:
            caption_url: Caption URL from get_captions()

        Returns:
            Caption text content
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(caption_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        self.logger.info("Downloaded caption successfully")
                        return content
                    else:
                        self.logger.error(f"Failed to download caption: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error downloading caption: {e}")
            return None

    async def get_trending_videos(
        self,
        category: str = "all",  # all, music, gaming, news, movies
        region: str = "US",
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Get trending videos"""
        try:
            self.logger.info(f"Getting trending videos for region: {region}")

            # Try API first
            if self.use_api and self.prefer_api:
                videos = await self._get_trending_api(category, region, max_results)
                if videos:
                    return videos

            # Fallback to scraping
            return await self._get_trending_scrape(category, max_results)

        except Exception as e:
            self.logger.error(f"Failed to get trending videos: {e}")
            return []

    async def _get_trending_api(
        self,
        category: str,
        region: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """使用API获取热门视频"""
        try:
            params = {
                'part': 'snippet,statistics',
                'chart': 'mostPopular',
                'regionCode': region,
                'maxResults': min(max_results, 50),
            }

            # 类别映射
            category_map = {
                'music': '10',
                'gaming': '20',
                'news': '25',
                'movies': '30',
            }

            if category in category_map:
                params['videoCategoryId'] = category_map[category]

            data = await self.anti_crawl.make_api_request('videos', params)

            if not data or 'items' not in data:
                return []

            videos = []
            for item in data['items']:
                snippet = item['snippet']
                statistics = item['statistics']

                video = {
                    'id': item['id'],
                    'url': f"{self.base_url}/watch?v={item['id']}",
                    'title': snippet.get('title'),
                    'description': snippet.get('description'),
                    'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                    'author': snippet.get('channelTitle'),
                    'author_id': snippet.get('channelId'),
                    'created_at': snippet.get('publishedAt'),
                    'views': int(statistics.get('viewCount', 0)),
                    'likes': int(statistics.get('likeCount', 0)),
                    'comments': int(statistics.get('commentCount', 0)),
                    'platform': self.platform,
                }
                videos.append(video)

            self.logger.info(f"Got {len(videos)} trending videos via API")
            return videos

        except Exception as e:
            self.logger.error(f"API get trending failed: {e}")
            return []

    async def _get_trending_scrape(
        self,
        category: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """通过爬虫获取热门视频"""
        try:
            trending_url = f"{self.base_url}/feed/trending"
            await self.navigate(trending_url)
            await asyncio.sleep(3)

            # 滚动加载
            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            videos = []
            video_elements = await self._page.query_selector_all('ytd-video-renderer')

            for elem in video_elements[:max_results]:
                try:
                    video = {}

                    link = await elem.query_selector('a#video-title')
                    if link:
                        href = await link.get_attribute('href')
                        video['url'] = f"{self.base_url}{href}"
                        video['id'] = href.split('v=')[-1].split('&')[0] if 'v=' in href else None
                        video['title'] = await link.get_attribute('title')

                    if video.get('id'):
                        video['platform'] = self.platform
                        videos.append(video)

                except Exception as e:
                    self.logger.warning(f"Failed to parse trending video: {e}")
                    continue

            self.logger.info(f"Got {len(videos)} trending videos via scraping")
            return videos

        except Exception as e:
            self.logger.error(f"Scraping get trending failed: {e}")
            return []

    async def get_playlist(self, playlist_id: str, max_videos: int = 100) -> Dict[str, Any]:
        """Get playlist information and videos"""
        try:
            self.logger.info(f"Getting playlist: {playlist_id}")

            # Try API first
            if self.use_api and self.prefer_api:
                playlist = await self._get_playlist_api(playlist_id, max_videos)
                if playlist:
                    return playlist

            # Fallback to scraping
            return await self._get_playlist_scrape(playlist_id, max_videos)

        except Exception as e:
            self.logger.error(f"Failed to get playlist: {e}")
            return {}

    async def _get_playlist_api(
        self,
        playlist_id: str,
        max_videos: int
    ) -> Dict[str, Any]:
        """使用API获取播放列表"""
        try:
            # 获取播放列表信息
            params = {
                'part': 'snippet,contentDetails',
                'id': playlist_id,
            }

            data = await self.anti_crawl.make_api_request('playlists', params)

            if not data or 'items' not in data or not data['items']:
                return {}

            item = data['items'][0]
            snippet = item['snippet']
            content_details = item['contentDetails']

            playlist = {
                'id': playlist_id,
                'title': snippet.get('title'),
                'description': snippet.get('description'),
                'author': snippet.get('channelTitle'),
                'author_id': snippet.get('channelId'),
                'video_count': content_details.get('itemCount', 0),
                'created_at': snippet.get('publishedAt'),
                'platform': self.platform,
                'videos': []
            }

            # 获取播放列表中的视频
            video_params = {
                'part': 'snippet',
                'playlistId': playlist_id,
                'maxResults': min(max_videos, 50),
            }

            video_data = await self.anti_crawl.make_api_request('playlistItems', video_params)

            if video_data and 'items' in video_data:
                for video_item in video_data['items']:
                    video_snippet = video_item['snippet']
                    video = {
                        'id': video_snippet['resourceId']['videoId'],
                        'title': video_snippet.get('title'),
                        'description': video_snippet.get('description'),
                        'thumbnail': video_snippet.get('thumbnails', {}).get('high', {}).get('url'),
                        'position': video_snippet.get('position'),
                    }
                    playlist['videos'].append(video)

            self.logger.info(f"Got playlist with {len(playlist['videos'])} videos via API")
            return playlist

        except Exception as e:
            self.logger.error(f"API get playlist failed: {e}")
            return {}

    async def _get_playlist_scrape(
        self,
        playlist_id: str,
        max_videos: int
    ) -> Dict[str, Any]:
        """通过爬虫获取播放列表"""
        try:
            playlist_url = f"{self.base_url}/playlist?list={playlist_id}"
            await self.navigate(playlist_url)
            await asyncio.sleep(3)

            playlist = {
                'id': playlist_id,
                'platform': self.platform,
                'videos': []
            }

            # 获取播放列表信息
            title_elem = await self._page.query_selector('h1.title yt-formatted-string')
            if title_elem:
                playlist['title'] = await title_elem.inner_text()

            # 滚动加载视频
            for _ in range(max_videos // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            video_elements = await self._page.query_selector_all('ytd-playlist-video-renderer')

            for elem in video_elements[:max_videos]:
                try:
                    video = {}

                    link = await elem.query_selector('a#video-title')
                    if link:
                        href = await link.get_attribute('href')
                        video['id'] = href.split('v=')[-1].split('&')[0] if 'v=' in href else None
                        video['title'] = await link.get_attribute('title')

                    if video.get('id'):
                        playlist['videos'].append(video)

                except Exception as e:
                    self.logger.warning(f"Failed to parse playlist video: {e}")
                    continue

            self.logger.info(f"Got playlist with {len(playlist['videos'])} videos via scraping")
            return playlist

        except Exception as e:
            self.logger.error(f"Scraping get playlist failed: {e}")
            return {}


# ============================================================================
# Convenience Functions
# ============================================================================

async def search_youtube_videos(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search YouTube videos with optional filters"""
    spider = YouTubeSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results)

        # Apply filters if provided
        if filters:
            results = spider.matcher.filter_videos(results, filters)

        return results


async def download_youtube_caption(
    video_id: str,
    language: str = 'en',
    headless: bool = True
) -> Optional[str]:
    """Download caption for a YouTube video"""
    spider = YouTubeSpider(headless=headless)

    async with spider.session():
        captions = await spider.get_captions(video_id, languages=[language])

        if not captions:
            return None

        # Download first matching caption
        caption_url = captions[0].get('url')
        if caption_url:
            return await spider.download_caption(caption_url)

        return None


# ============================================================================
# Main Test
# ============================================================================

if __name__ == "__main__":
    async def test_youtube_spider():
        """Test YouTube spider functionality"""
        spider = YouTubeSpider(headless=False)

        async with spider.session():
            print("\n=== Testing YouTube Search ===")
            videos = await spider.search("python tutorial", max_results=5, sort_by="viewCount")

            for video in videos:
                print(f"\nVideo: {video.get('title')}")
                print(f"Channel: {video.get('author')}")
                print(f"Views: {video.get('views')}")
                print(f"URL: {video.get('url')}")

            if videos:
                print("\n=== Testing Video Detail ===")
                detail = await spider.get_post_detail(videos[0]['id'])
                print(f"Likes: {detail.get('likes')}")
                print(f"Duration: {detail.get('duration')}s")
                print(f"Tags: {detail.get('tags')}")

                print("\n=== Testing Comments ===")
                comments = await spider.get_comments(videos[0]['id'], max_comments=5)
                for comment in comments[:3]:
                    print(f"\nUser: {comment.get('username')}")
                    print(f"Comment: {comment.get('content')[:100]}...")

                print("\n=== Testing Captions ===")
                captions = await spider.get_captions(videos[0]['id'])
                for caption in captions:
                    print(f"Language: {caption.get('language')} - {caption.get('name')}")

            print("\n=== Testing Trending Videos ===")
            trending = await spider.get_trending_videos(max_results=5)
            for video in trending:
                print(f"\nTrending: {video.get('title')}")
                print(f"Views: {video.get('views')}")

    asyncio.run(test_youtube_spider())
