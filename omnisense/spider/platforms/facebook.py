"""
Facebook Spider Implementation
完整的Facebook平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 帖子搜索、用户主页、群组、页面、评论
2. Anti-Crawl Layer: 反反爬层 - Graph API、设备指纹、滑动验证、请求频率控制
3. Matcher Layer: 智能匹配层 - 点赞数、评论数、分享数、用户粉丝数、帖子类型
4. Interaction Layer: 互动处理层 - 点赞/反应、评论、分享、好友管理、消息
"""

import asyncio
import hashlib
import json
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

import aiohttp
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from omnisense.config import config
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Layer 2: Anti-Crawl Layer - 反反爬处理
# ============================================================================

class FacebookAntiCrawl:
    """
    Facebook反反爬处理器
    Layer 2: Anti-Crawl - Graph API集成、设备指纹、滑动验证、频率控制
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger
        self._device_id = None
        self._machine_id = None
        self._fp_cache = {}
        self._request_timestamps = []
        self._ip_pool = []
        self._current_ip_index = 0
        self._access_token = None
        self._app_id = None
        self._app_secret = None

    async def initialize(self, page: Page):
        """初始化反爬措施"""
        await self._inject_device_fingerprint(page)
        await self._inject_webdriver_evasion(page)
        await self._inject_canvas_fingerprint(page)
        await self._inject_audio_fingerprint(page)
        await self._inject_webgl_fingerprint(page)
        await self._randomize_browser_features(page)

    def set_graph_api_credentials(self, app_id: str, app_secret: str, access_token: Optional[str] = None):
        """设置Graph API凭证"""
        self._app_id = app_id
        self._app_secret = app_secret
        self._access_token = access_token
        self.logger.info(f"Graph API credentials configured: app_id={app_id}")

    async def get_access_token(self) -> Optional[str]:
        """获取Graph API访问令牌"""
        if self._access_token:
            return self._access_token

        if not self._app_id or not self._app_secret:
            self.logger.warning("Graph API credentials not configured")
            return None

        try:
            url = f"https://graph.facebook.com/oauth/access_token"
            params = {
                "client_id": self._app_id,
                "client_secret": self._app_secret,
                "grant_type": "client_credentials"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._access_token = data.get("access_token")
                        self.logger.info("Graph API access token obtained")
                        return self._access_token
                    else:
                        self.logger.error(f"Failed to get access token: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error getting access token: {e}")
            return None

    async def graph_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """执行Graph API请求"""
        token = await self.get_access_token()
        if not token:
            return None

        try:
            url = f"https://graph.facebook.com/v18.0/{endpoint}"
            params = params or {}
            params["access_token"] = token

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Graph API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            self.logger.error(f"Graph API request failed: {e}")
            return None

    async def _inject_device_fingerprint(self, page: Page):
        """注入设备指纹"""
        self._device_id = str(uuid.uuid4())
        self._machine_id = hashlib.md5(f"{self._device_id}{time.time()}".encode()).hexdigest()

        device_script = f"""
        // Device fingerprint for Facebook
        window._device_id = '{self._device_id}';
        window._machine_id = '{self._machine_id}';

        // Override device memory
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {random.choice([4, 8, 16])}
        }});

        // Override hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.choice([4, 8, 12, 16])}
        }});

        // Override platform
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{random.choice(['Win32', 'MacIntel', 'Linux x86_64'])}'
        }});

        // Override vendor
        Object.defineProperty(navigator, 'vendor', {{
            get: () => 'Google Inc.'
        }});

        // Override connection
        Object.defineProperty(navigator, 'connection', {{
            get: () => ({{
                effectiveType: '{random.choice(['4g', '5g'])}',
                downlink: {random.uniform(5, 10)},
                rtt: {random.randint(20, 50)}
            }})
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
                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                {name: 'Native Client', filename: 'internal-nacl-plugin'}
            ]
        });

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        """
        await page.add_init_script(evasion_script)
        self.logger.debug("Injected webdriver evasion")

    async def _inject_canvas_fingerprint(self, page: Page):
        """注入Canvas指纹随机化"""
        # Generate random noise for canvas fingerprint
        noise_value = random.uniform(0.0001, 0.001)

        canvas_script = f"""
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        const originalToBlob = HTMLCanvasElement.prototype.toBlob;
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

        const noise = {noise_value};

        // Randomize toDataURL
        HTMLCanvasElement.prototype.toDataURL = function() {{
            const context = this.getContext('2d');
            const imageData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                imageData.data[i] = imageData.data[i] + Math.random() * noise;
                imageData.data[i + 1] = imageData.data[i + 1] + Math.random() * noise;
                imageData.data[i + 2] = imageData.data[i + 2] + Math.random() * noise;
            }}
            context.putImageData(imageData, 0, 0);
            return originalToDataURL.apply(this, arguments);
        }};

        // Randomize getImageData
        CanvasRenderingContext2D.prototype.getImageData = function() {{
            const imageData = originalGetImageData.apply(this, arguments);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                imageData.data[i] = imageData.data[i] + Math.random() * noise;
                imageData.data[i + 1] = imageData.data[i + 1] + Math.random() * noise;
                imageData.data[i + 2] = imageData.data[i + 2] + Math.random() * noise;
            }}
            return imageData;
        }};
        """
        await page.add_init_script(canvas_script)
        self.logger.debug("Injected canvas fingerprint randomization")

    async def _inject_audio_fingerprint(self, page: Page):
        """注入Audio指纹随机化"""
        audio_script = """
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;

        AudioBuffer.prototype.getChannelData = function() {
            const channelData = originalGetChannelData.apply(this, arguments);
            for (let i = 0; i < channelData.length; i++) {
                channelData[i] = channelData[i] + Math.random() * 0.0001;
            }
            return channelData;
        };
        """
        await page.add_init_script(audio_script)
        self.logger.debug("Injected audio fingerprint randomization")

    async def _inject_webgl_fingerprint(self, page: Page):
        """注入WebGL指纹随机化"""
        webgl_script = f"""
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            // Randomize UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {{
                return '{random.choice(['Intel Inc.', 'NVIDIA Corporation', 'AMD'])}';
            }}
            // Randomize UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {{
                return '{random.choice(['Intel Iris OpenGL Engine', 'NVIDIA GeForce GTX 1060', 'AMD Radeon RX 580'])}';
            }}
            return getParameter.apply(this, arguments);
        }};
        """
        await page.add_init_script(webgl_script)
        self.logger.debug("Injected WebGL fingerprint randomization")

    async def _randomize_browser_features(self, page: Page):
        """随机化浏览器特征"""
        features_script = f"""
        // Randomize screen resolution
        Object.defineProperty(window.screen, 'width', {{
            get: () => {random.choice([1920, 1366, 1536, 2560])}
        }});
        Object.defineProperty(window.screen, 'height', {{
            get: () => {random.choice([1080, 768, 864, 1440])}
        }});

        // Randomize timezone
        Date.prototype.getTimezoneOffset = function() {{
            return {random.choice([-480, -420, -360, -300, -240, 0, 60, 120])};
        }};

        // Randomize battery
        navigator.getBattery = async () => ({{
            charging: {str(random.choice([True, False])).lower()},
            chargingTime: {random.randint(0, 10000)},
            dischargingTime: {random.randint(10000, 50000)},
            level: {random.uniform(0.3, 1.0)}
        }});
        """
        await page.add_init_script(features_script)
        self.logger.debug("Injected browser feature randomization")

    async def handle_rate_limit(self) -> None:
        """处理请求频率限制"""
        current_time = time.time()

        # 清理1分钟前的时间戳
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if current_time - ts < 60
        ]

        # 检查请求频率（每分钟最多30次）
        if len(self._request_timestamps) >= 30:
            wait_time = 60 - (current_time - self._request_timestamps[0])
            if wait_time > 0:
                self.logger.info(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self._request_timestamps.clear()

        # 添加随机延迟
        delay = random.uniform(1.5, 3.5)
        await asyncio.sleep(delay)

        # 记录请求时间戳
        self._request_timestamps.append(time.time())

    async def rotate_ip(self) -> bool:
        """轮换IP地址"""
        if not self._ip_pool:
            self.logger.warning("IP pool is empty")
            return False

        self._current_ip_index = (self._current_ip_index + 1) % len(self._ip_pool)
        new_ip = self._ip_pool[self._current_ip_index]
        self.logger.info(f"Rotated to IP: {new_ip}")
        return True

    def add_proxy_to_pool(self, proxy: str):
        """添加代理到IP池"""
        if proxy not in self._ip_pool:
            self._ip_pool.append(proxy)
            self.logger.info(f"Added proxy to pool: {proxy}")

    async def handle_captcha(self, page: Page) -> bool:
        """处理验证码"""
        try:
            # 检查是否有验证码
            captcha_selectors = [
                'div[class*="captcha"]',
                'iframe[src*="captcha"]',
                'div[id*="captcha"]',
                '[data-testid*="captcha"]'
            ]

            for selector in captcha_selectors:
                captcha = await page.query_selector(selector)
                if captcha:
                    self.logger.warning("Captcha detected")
                    # 等待用户手动解决验证码
                    self.logger.info("Please solve the captcha manually...")
                    await asyncio.sleep(30)
                    return True

            return True

        except Exception as e:
            self.logger.error(f"Error handling captcha: {e}")
            return False

    async def simulate_human_behavior(self, page: Page):
        """模拟人类行为"""
        try:
            # 随机滚动
            scroll_distance = random.randint(100, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # 随机鼠标移动
            viewport_size = page.viewport_size
            if viewport_size:
                x = random.randint(0, viewport_size['width'])
                y = random.randint(0, viewport_size['height'])
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.5))

            # 偶尔返回顶部
            if random.random() < 0.1:
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            self.logger.error(f"Error simulating human behavior: {e}")

    def _generate_device_id(self) -> str:
        """生成设备ID"""
        return str(uuid.uuid4())


# ============================================================================
# Layer 3: Matcher Layer - 智能匹配层
# ============================================================================

class FacebookMatcher:
    """
    Facebook智能匹配器
    Layer 3: Matcher - 点赞数、评论数、分享数、粉丝数、帖子类型过滤
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger
        self._filters = {}

    def set_filter(self, filter_type: str, **kwargs):
        """设置过滤器"""
        self._filters[filter_type] = kwargs
        self.logger.info(f"Set filter: {filter_type} = {kwargs}")

    def match_post(self, post: Dict[str, Any]) -> bool:
        """匹配帖子是否符合条件"""
        try:
            # 点赞数过滤
            if 'likes' in self._filters:
                likes = post.get('likes', 0)
                min_likes = self._filters['likes'].get('min', 0)
                max_likes = self._filters['likes'].get('max', float('inf'))
                if not (min_likes <= likes <= max_likes):
                    return False

            # 评论数过滤
            if 'comments' in self._filters:
                comments = post.get('comments', 0)
                min_comments = self._filters['comments'].get('min', 0)
                max_comments = self._filters['comments'].get('max', float('inf'))
                if not (min_comments <= comments <= max_comments):
                    return False

            # 分享数过滤
            if 'shares' in self._filters:
                shares = post.get('shares', 0)
                min_shares = self._filters['shares'].get('min', 0)
                max_shares = self._filters['shares'].get('max', float('inf'))
                if not (min_shares <= shares <= max_shares):
                    return False

            # 帖子类型过滤
            if 'post_type' in self._filters:
                allowed_types = self._filters['post_type'].get('types', [])
                post_type = post.get('type', 'text')
                if allowed_types and post_type not in allowed_types:
                    return False

            # 时间范围过滤
            if 'time_range' in self._filters:
                created_at = post.get('created_at')
                if created_at:
                    start_time = self._filters['time_range'].get('start')
                    end_time = self._filters['time_range'].get('end')

                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                    if start_time and created_at < start_time:
                        return False
                    if end_time and created_at > end_time:
                        return False

            # 关键词匹配
            if 'keywords' in self._filters:
                keywords = self._filters['keywords'].get('include', [])
                exclude_keywords = self._filters['keywords'].get('exclude', [])
                content = post.get('content', '').lower()

                if keywords and not any(kw.lower() in content for kw in keywords):
                    return False
                if exclude_keywords and any(kw.lower() in content for kw in exclude_keywords):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error matching post: {e}")
            return True  # 出错时默认通过

    def match_user(self, user: Dict[str, Any]) -> bool:
        """匹配用户是否符合条件"""
        try:
            # 粉丝数过滤
            if 'followers' in self._filters:
                followers = user.get('followers', 0)
                min_followers = self._filters['followers'].get('min', 0)
                max_followers = self._filters['followers'].get('max', float('inf'))
                if not (min_followers <= followers <= max_followers):
                    return False

            # 好友数过滤
            if 'friends' in self._filters:
                friends = user.get('friends', 0)
                min_friends = self._filters['friends'].get('min', 0)
                max_friends = self._filters['friends'].get('max', float('inf'))
                if not (min_friends <= friends <= max_friends):
                    return False

            # 验证状态过滤
            if 'verified' in self._filters:
                required_verified = self._filters['verified'].get('required', False)
                is_verified = user.get('verified', False)
                if required_verified and not is_verified:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error matching user: {e}")
            return True

    def clear_filters(self):
        """清除所有过滤器"""
        self._filters.clear()
        self.logger.info("Cleared all filters")


# ============================================================================
# Layer 4: Interaction Layer - 互动处理层
# ============================================================================

class FacebookInteraction:
    """
    Facebook互动处理器
    Layer 4: Interaction - 点赞、评论、分享、好友管理、消息
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def like_post(self, post_id: str, reaction_type: str = "like") -> bool:
        """
        给帖子点赞或反应

        Args:
            post_id: 帖子ID
            reaction_type: 反应类型 (like, love, haha, wow, sad, angry)
        """
        try:
            page = self.spider._page

            # 导航到帖子
            post_url = f"{self.spider.base_url}/posts/{post_id}"
            await self.spider.navigate(post_url)
            await asyncio.sleep(2)

            # 查找点赞按钮
            like_button = await page.query_selector('[aria-label*="Like"]')
            if not like_button:
                like_button = await page.query_selector('[data-testid*="like"]')

            if like_button:
                # 长按显示反应选项
                if reaction_type != "like":
                    await like_button.hover()
                    await asyncio.sleep(1)

                    # 选择特定反应
                    reaction_selector = f'[aria-label*="{reaction_type.title()}"]'
                    reaction_button = await page.query_selector(reaction_selector)
                    if reaction_button:
                        await reaction_button.click()
                    else:
                        await like_button.click()
                else:
                    await like_button.click()

                await asyncio.sleep(1)
                self.logger.info(f"Posted {reaction_type} reaction to post: {post_id}")
                return True
            else:
                self.logger.warning(f"Like button not found for post: {post_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error liking post {post_id}: {e}")
            return False

    async def comment_on_post(self, post_id: str, comment_text: str) -> bool:
        """
        评论帖子

        Args:
            post_id: 帖子ID
            comment_text: 评论内容
        """
        try:
            page = self.spider._page

            # 导航到帖子
            post_url = f"{self.spider.base_url}/posts/{post_id}"
            await self.spider.navigate(post_url)
            await asyncio.sleep(2)

            # 查找评论框
            comment_selectors = [
                'div[aria-label*="Write a comment"]',
                'div[contenteditable="true"][data-testid*="comment"]',
                'div[role="textbox"]'
            ]

            comment_box = None
            for selector in comment_selectors:
                comment_box = await page.query_selector(selector)
                if comment_box:
                    break

            if comment_box:
                await comment_box.click()
                await asyncio.sleep(0.5)
                await comment_box.type(comment_text, delay=random.randint(50, 150))
                await asyncio.sleep(1)

                # 发送评论
                await page.keyboard.press('Enter')
                await asyncio.sleep(2)

                self.logger.info(f"Posted comment on post: {post_id}")
                return True
            else:
                self.logger.warning(f"Comment box not found for post: {post_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error commenting on post {post_id}: {e}")
            return False

    async def share_post(self, post_id: str, share_type: str = "timeline", message: str = "") -> bool:
        """
        分享帖子

        Args:
            post_id: 帖子ID
            share_type: 分享类型 (timeline, story, group, messenger)
            message: 分享附带的消息
        """
        try:
            page = self.spider._page

            # 导航到帖子
            post_url = f"{self.spider.base_url}/posts/{post_id}"
            await self.spider.navigate(post_url)
            await asyncio.sleep(2)

            # 查找分享按钮
            share_button = await page.query_selector('[aria-label*="Share"]')
            if not share_button:
                share_button = await page.query_selector('[data-testid*="share"]')

            if share_button:
                await share_button.click()
                await asyncio.sleep(1)

                # 选择分享类型
                if share_type == "timeline":
                    option = await page.query_selector('div[role="menuitem"]:has-text("Share to Feed")')
                elif share_type == "story":
                    option = await page.query_selector('div[role="menuitem"]:has-text("Share to Story")')
                elif share_type == "group":
                    option = await page.query_selector('div[role="menuitem"]:has-text("Share to Group")')
                elif share_type == "messenger":
                    option = await page.query_selector('div[role="menuitem"]:has-text("Send in Messenger")')
                else:
                    option = None

                if option:
                    await option.click()
                    await asyncio.sleep(1)

                    # 如果有消息，输入消息
                    if message:
                        message_box = await page.query_selector('div[contenteditable="true"]')
                        if message_box:
                            await message_box.type(message, delay=random.randint(50, 150))
                            await asyncio.sleep(1)

                    # 确认分享
                    post_button = await page.query_selector('div[aria-label*="Post"]')
                    if post_button:
                        await post_button.click()
                        await asyncio.sleep(2)

                        self.logger.info(f"Shared post: {post_id} to {share_type}")
                        return True

        except Exception as e:
            self.logger.error(f"Error sharing post {post_id}: {e}")
            return False

    async def send_friend_request(self, user_id: str) -> bool:
        """
        发送好友请求

        Args:
            user_id: 用户ID或用户名
        """
        try:
            page = self.spider._page

            # 导航到用户主页
            profile_url = f"{self.spider.base_url}/{user_id}"
            await self.spider.navigate(profile_url)
            await asyncio.sleep(2)

            # 查找添加好友按钮
            add_friend_selectors = [
                '[aria-label*="Add Friend"]',
                'div[role="button"]:has-text("Add Friend")',
                '[data-testid*="add_friend"]'
            ]

            for selector in add_friend_selectors:
                add_button = await page.query_selector(selector)
                if add_button:
                    await add_button.click()
                    await asyncio.sleep(2)
                    self.logger.info(f"Sent friend request to: {user_id}")
                    return True

            self.logger.warning(f"Add friend button not found for user: {user_id}")
            return False

        except Exception as e:
            self.logger.error(f"Error sending friend request to {user_id}: {e}")
            return False

    async def send_message(self, user_id: str, message: str) -> bool:
        """
        发送私信

        Args:
            user_id: 用户ID或用户名
            message: 消息内容
        """
        try:
            page = self.spider._page

            # 导航到Messenger
            messenger_url = f"https://www.messenger.com/t/{user_id}"
            await self.spider.navigate(messenger_url)
            await asyncio.sleep(3)

            # 查找消息输入框
            message_selectors = [
                'div[aria-label*="Message"]',
                'div[contenteditable="true"][data-testid*="message"]',
                'div[role="textbox"]'
            ]

            message_box = None
            for selector in message_selectors:
                message_box = await page.query_selector(selector)
                if message_box:
                    break

            if message_box:
                await message_box.click()
                await asyncio.sleep(0.5)
                await message_box.type(message, delay=random.randint(50, 150))
                await asyncio.sleep(1)

                # 发送消息
                await page.keyboard.press('Enter')
                await asyncio.sleep(2)

                self.logger.info(f"Sent message to: {user_id}")
                return True
            else:
                self.logger.warning(f"Message box not found for user: {user_id}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending message to {user_id}: {e}")
            return False

    async def follow_page(self, page_id: str) -> bool:
        """
        关注页面

        Args:
            page_id: 页面ID或页面名
        """
        try:
            page = self.spider._page

            # 导航到页面
            page_url = f"{self.spider.base_url}/{page_id}"
            await self.spider.navigate(page_url)
            await asyncio.sleep(2)

            # 查找关注按钮
            follow_selectors = [
                '[aria-label*="Follow"]',
                'div[role="button"]:has-text("Follow")',
                '[data-testid*="follow"]'
            ]

            for selector in follow_selectors:
                follow_button = await page.query_selector(selector)
                if follow_button:
                    await follow_button.click()
                    await asyncio.sleep(2)
                    self.logger.info(f"Followed page: {page_id}")
                    return True

            self.logger.warning(f"Follow button not found for page: {page_id}")
            return False

        except Exception as e:
            self.logger.error(f"Error following page {page_id}: {e}")
            return False

    async def join_group(self, group_id: str) -> bool:
        """
        加入群组

        Args:
            group_id: 群组ID或群组名
        """
        try:
            page = self.spider._page

            # 导航到群组
            group_url = f"{self.spider.base_url}/groups/{group_id}"
            await self.spider.navigate(group_url)
            await asyncio.sleep(2)

            # 查找加入按钮
            join_selectors = [
                '[aria-label*="Join Group"]',
                'div[role="button"]:has-text("Join")',
                '[data-testid*="join_group"]'
            ]

            for selector in join_selectors:
                join_button = await page.query_selector(selector)
                if join_button:
                    await join_button.click()
                    await asyncio.sleep(2)
                    self.logger.info(f"Joined group: {group_id}")
                    return True

            self.logger.warning(f"Join button not found for group: {group_id}")
            return False

        except Exception as e:
            self.logger.error(f"Error joining group {group_id}: {e}")
            return False


# ============================================================================
# Layer 1: Spider Layer - 数据爬取层
# ============================================================================

class FacebookSpider(BaseSpider):
    """
    Facebook社交平台爬虫
    Layer 1: Spider - 帖子搜索、用户主页、群组、页面、评论等数据爬取

    Platform-specific information:
    - Base URL: https://www.facebook.com
    - Graph API: https://graph.facebook.com
    - Login required: Yes (for most content)
    - Rate limit: Strict (use delays and rotation)
    - Special features: Posts, pages, groups, marketplace, stories
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="facebook", headless=headless, proxy=proxy)
        self.base_url = "https://www.facebook.com"
        self.api_base_url = "https://graph.facebook.com"

        # Initialize layers
        self.anti_crawl = FacebookAntiCrawl(self)
        self.matcher = FacebookMatcher(self)
        self.interaction = FacebookInteraction(self)

    async def start(self) -> None:
        """启动浏览器并初始化反爬措施"""
        await super().start()
        await self.anti_crawl.initialize(self._page)

    async def login(self, username: str, password: str) -> bool:
        """
        登录Facebook

        Args:
            username: 邮箱或手机号
            password: 密码
        """
        try:
            self.logger.info(f"Logging in to Facebook as {username}...")

            # 尝试使用保存的cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)

                # 检查是否已登录
                if await self._page.query_selector('[aria-label*="Account"]'):
                    self._is_logged_in = True
                    self.logger.info("Logged in with saved cookies")
                    return True

            # 导航到登录页面
            await self.navigate(f"{self.base_url}/login")
            await asyncio.sleep(2)

            # 填写邮箱
            email_input = await self._page.wait_for_selector('input[name="email"]', timeout=10000)
            await email_input.fill(username)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # 填写密码
            password_input = await self._page.wait_for_selector('input[name="pass"]', timeout=10000)
            await password_input.fill(password)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # 点击登录按钮
            login_btn = await self._page.wait_for_selector('button[name="login"]', timeout=10000)
            await login_btn.click()
            await asyncio.sleep(5)

            # 处理可能的验证码
            await self.anti_crawl.handle_captcha(self._page)

            # 检查登录是否成功
            if await self._page.query_selector('[aria-label*="Account"]'):
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True

            self.logger.error("Login failed")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(self, keyword: str, max_results: int = 20,
                    search_type: str = "posts", time_range: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索Facebook内容

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型 (posts, people, pages, groups, videos)
            time_range: 时间范围 (recent, today, week, month, year)
        """
        try:
            self.logger.info(f"Searching Facebook for '{keyword}' (type: {search_type})")

            # 构建搜索URL
            search_params = {"q": keyword}

            if search_type == "posts":
                search_url = f"{self.base_url}/search/posts/"
            elif search_type == "people":
                search_url = f"{self.base_url}/search/people/"
            elif search_type == "pages":
                search_url = f"{self.base_url}/search/pages/"
            elif search_type == "groups":
                search_url = f"{self.base_url}/search/groups/"
            elif search_type == "videos":
                search_url = f"{self.base_url}/search/videos/"
            else:
                search_url = f"{self.base_url}/search/posts/"

            search_url += f"?{urlencode(search_params)}"

            # 导航到搜索页面
            await self.navigate(search_url)
            await asyncio.sleep(3)

            # 应用时间过滤
            if time_range:
                await self._apply_time_filter(time_range)

            # 滚动加载更多内容
            results = []
            scroll_count = 0
            max_scrolls = max_results // 5

            while len(results) < max_results and scroll_count < max_scrolls:
                # 模拟人类行为
                await self.anti_crawl.simulate_human_behavior(self._page)

                # 应用频率限制
                await self.anti_crawl.handle_rate_limit()

                # 查找帖子元素
                if search_type == "posts":
                    items = await self._parse_post_search_results()
                elif search_type == "people":
                    items = await self._parse_people_search_results()
                elif search_type == "pages":
                    items = await self._parse_page_search_results()
                elif search_type == "groups":
                    items = await self._parse_group_search_results()
                else:
                    items = await self._parse_post_search_results()

                # 应用匹配过滤
                for item in items:
                    if search_type == "posts" and self.matcher.match_post(item):
                        if item not in results:
                            results.append(item)
                    elif search_type == "people" and self.matcher.match_user(item):
                        if item not in results:
                            results.append(item)
                    else:
                        if item not in results:
                            results.append(item)

                # 滚动加载更多
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 4))
                scroll_count += 1

            results = results[:max_results]
            self.logger.info(f"Found {len(results)} {search_type}")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def _parse_post_search_results(self) -> List[Dict[str, Any]]:
        """解析帖子搜索结果"""
        results = []

        post_elements = await self._page.query_selector_all('[data-pagelet^="FeedUnit"]')

        for elem in post_elements:
            try:
                post = {'platform': self.platform}

                # 帖子内容
                content_elem = await elem.query_selector('[data-ad-comet-preview="message"]')
                if content_elem:
                    post['content'] = await content_elem.inner_text()

                # 作者
                author_elem = await elem.query_selector('a[role="link"] strong')
                if author_elem:
                    post['author'] = await author_elem.inner_text()
                    author_link = await elem.query_selector('a[role="link"]')
                    if author_link:
                        href = await author_link.get_attribute('href')
                        if href:
                            post['author_url'] = href if href.startswith('http') else f"{self.base_url}{href}"

                # 时间戳
                time_elem = await elem.query_selector('a[href*="/posts/"]')
                if time_elem:
                    time_text = await time_elem.get_attribute('aria-label')
                    if time_text:
                        post['created_at'] = self.parser.parse_date(time_text)

                # 帖子链接和ID
                link_elem = await elem.query_selector('a[href*="/posts/"]')
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        post['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if '/posts/' in href:
                            post['id'] = href.split('/posts/')[-1].split('?')[0]

                # 图片
                images = await elem.query_selector_all('img[src*="fbcdn"]')
                post['images'] = []
                for img in images[:5]:
                    src = await img.get_attribute('src')
                    if src and 'emoji' not in src:
                        post['images'].append({'src': src})

                # 视频
                video_elem = await elem.query_selector('video')
                if video_elem:
                    video_src = await video_elem.get_attribute('src')
                    if video_src:
                        post['video_url'] = video_src
                        post['type'] = 'video'
                elif post['images']:
                    post['type'] = 'photo'
                else:
                    post['type'] = 'text'

                # 统计数据
                await self._extract_post_stats(elem, post)

                if post.get('content') or post.get('id'):
                    results.append(post)

            except Exception as e:
                self.logger.warning(f"Failed to parse post: {e}")
                continue

        return results

    async def _extract_post_stats(self, elem, post: Dict[str, Any]):
        """提取帖子统计数据"""
        try:
            # 点赞数
            reactions_elem = await elem.query_selector('[aria-label*="reactions"]')
            if reactions_elem:
                reactions_text = await reactions_elem.get_attribute('aria-label')
                if reactions_text:
                    post['likes'] = self.parser.parse_count(reactions_text)

            # 评论数
            comments_elem = await elem.query_selector('[aria-label*="comments"]')
            if comments_elem:
                comments_text = await comments_elem.inner_text()
                if comments_text:
                    post['comments'] = self.parser.parse_count(comments_text)

            # 分享数
            shares_elem = await elem.query_selector('[aria-label*="shares"]')
            if shares_elem:
                shares_text = await shares_elem.inner_text()
                if shares_text:
                    post['shares'] = self.parser.parse_count(shares_text)

        except Exception as e:
            self.logger.debug(f"Error extracting post stats: {e}")

    async def _parse_people_search_results(self) -> List[Dict[str, Any]]:
        """解析用户搜索结果"""
        results = []

        people_elements = await self._page.query_selector_all('div[role="article"]')

        for elem in people_elements:
            try:
                user = {'platform': self.platform}

                # 用户名
                name_elem = await elem.query_selector('a[role="link"] strong')
                if name_elem:
                    user['username'] = await name_elem.inner_text()

                # 个人资料链接
                link_elem = await elem.query_selector('a[role="link"]')
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        user['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        # 提取用户ID
                        if '/profile.php?id=' in href:
                            user['user_id'] = parse_qs(urlparse(href).query).get('id', [''])[0]
                        else:
                            user['user_id'] = href.strip('/').split('/')[-1].split('?')[0]

                # 头像
                avatar_elem = await elem.query_selector('image')
                if avatar_elem:
                    avatar_src = await avatar_elem.get_attribute('xlink:href')
                    if avatar_src:
                        user['avatar'] = avatar_src

                # 简介
                bio_elem = await elem.query_selector('div[class*="userContent"]')
                if bio_elem:
                    user['bio'] = await bio_elem.inner_text()

                # 好友数
                friends_elem = await elem.query_selector('span:has-text("friends")')
                if friends_elem:
                    friends_text = await friends_elem.inner_text()
                    user['friends'] = self.parser.parse_count(friends_text)

                if user.get('username'):
                    results.append(user)

            except Exception as e:
                self.logger.warning(f"Failed to parse user: {e}")
                continue

        return results

    async def _parse_page_search_results(self) -> List[Dict[str, Any]]:
        """解析页面搜索结果"""
        results = []

        page_elements = await self._page.query_selector_all('div[role="article"]')

        for elem in page_elements:
            try:
                page_data = {'platform': self.platform, 'type': 'page'}

                # 页面名称
                name_elem = await elem.query_selector('a[role="link"] strong')
                if name_elem:
                    page_data['name'] = await name_elem.inner_text()

                # 页面链接
                link_elem = await elem.query_selector('a[role="link"]')
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        page_data['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        page_data['page_id'] = href.strip('/').split('/')[-1].split('?')[0]

                # 分类
                category_elem = await elem.query_selector('span[class*="category"]')
                if category_elem:
                    page_data['category'] = await category_elem.inner_text()

                # 点赞数
                likes_elem = await elem.query_selector('span:has-text("likes")')
                if likes_elem:
                    likes_text = await likes_elem.inner_text()
                    page_data['likes'] = self.parser.parse_count(likes_text)

                if page_data.get('name'):
                    results.append(page_data)

            except Exception as e:
                self.logger.warning(f"Failed to parse page: {e}")
                continue

        return results

    async def _parse_group_search_results(self) -> List[Dict[str, Any]]:
        """解析群组搜索结果"""
        results = []

        group_elements = await self._page.query_selector_all('div[role="article"]')

        for elem in group_elements:
            try:
                group = {'platform': self.platform, 'type': 'group'}

                # 群组名称
                name_elem = await elem.query_selector('a[role="link"] strong')
                if name_elem:
                    group['name'] = await name_elem.inner_text()

                # 群组链接
                link_elem = await elem.query_selector('a[role="link"]')
                if link_elem:
                    href = await link_elem.get_attribute('href')
                    if href:
                        group['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if '/groups/' in href:
                            group['group_id'] = href.split('/groups/')[-1].split('?')[0]

                # 成员数
                members_elem = await elem.query_selector('span:has-text("members")')
                if members_elem:
                    members_text = await members_elem.inner_text()
                    group['members'] = self.parser.parse_count(members_text)

                # 隐私设置
                privacy_elem = await elem.query_selector('span:has-text("Public"), span:has-text("Private")')
                if privacy_elem:
                    group['privacy'] = await privacy_elem.inner_text()

                if group.get('name'):
                    results.append(group)

            except Exception as e:
                self.logger.warning(f"Failed to parse group: {e}")
                continue

        return results

    async def _apply_time_filter(self, time_range: str):
        """应用时间过滤"""
        try:
            # 点击过滤器按钮
            filter_button = await self._page.query_selector('[aria-label*="Filters"]')
            if filter_button:
                await filter_button.click()
                await asyncio.sleep(1)

                # 选择时间范围
                time_options = {
                    "recent": "Recent posts",
                    "today": "Today",
                    "week": "This week",
                    "month": "This month",
                    "year": "This year"
                }

                option_text = time_options.get(time_range, "Recent posts")
                time_option = await self._page.query_selector(f'div[role="menuitem"]:has-text("{option_text}")')
                if time_option:
                    await time_option.click()
                    await asyncio.sleep(2)

        except Exception as e:
            self.logger.warning(f"Failed to apply time filter: {e}")

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户主页信息

        Args:
            user_id: 用户ID或用户名
        """
        try:
            self.logger.info(f"Getting profile: {user_id}")

            # 尝试使用Graph API
            if self.anti_crawl._access_token:
                graph_data = await self.anti_crawl.graph_api_request(
                    user_id,
                    {"fields": "id,name,username,picture,friends,followers_count,verified"}
                )
                if graph_data:
                    return self._format_graph_api_profile(graph_data)

            # 爬虫方式获取
            profile_url = f"{self.base_url}/{user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(3)

            profile = {'user_id': user_id, 'platform': self.platform}

            # 用户名
            name_elem = await self._page.query_selector('h1')
            if name_elem:
                profile['username'] = await name_elem.inner_text()

            # 简介
            bio_elem = await self._page.query_selector('[data-pagelet*="ProfileTimeline"] div[class*="userContent"]')
            if bio_elem:
                profile['bio'] = await bio_elem.inner_text()

            # 粉丝数（页面）
            followers_elem = await self._page.query_selector('a[href*="followers"]')
            if followers_elem:
                followers_text = await followers_elem.inner_text()
                profile['followers'] = self.parser.parse_count(followers_text)

            # 好友数
            friends_elem = await self._page.query_selector('a[href*="friends"]')
            if friends_elem:
                friends_text = await friends_elem.inner_text()
                profile['friends'] = self.parser.parse_count(friends_text)

            # 验证状态
            verified_elem = await self._page.query_selector('svg[aria-label*="Verified"]')
            profile['verified'] = verified_elem is not None

            # 头像
            avatar_elem = await self._page.query_selector('image[xlink:href*="fbcdn"]')
            if avatar_elem:
                profile['avatar'] = await avatar_elem.get_attribute('xlink:href')

            # 封面图
            cover_elem = await self._page.query_selector('img[data-imgperflogname="profileCoverPhoto"]')
            if cover_elem:
                profile['cover'] = await cover_elem.get_attribute('src')

            # 位置
            location_elem = await self._page.query_selector('[class*="location"]')
            if location_elem:
                profile['location'] = await location_elem.inner_text()

            # 工作
            work_elem = await self._page.query_selector('[class*="work"]')
            if work_elem:
                profile['work'] = await work_elem.inner_text()

            # 教育
            education_elem = await self._page.query_selector('[class*="education"]')
            if education_elem:
                profile['education'] = await education_elem.inner_text()

            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    def _format_graph_api_profile(self, data: Dict) -> Dict[str, Any]:
        """格式化Graph API返回的用户资料"""
        return {
            'user_id': data.get('id'),
            'username': data.get('name'),
            'platform': self.platform,
            'avatar': data.get('picture', {}).get('data', {}).get('url'),
            'friends': data.get('friends', {}).get('summary', {}).get('total_count', 0),
            'followers': data.get('followers_count', 0),
            'verified': data.get('verified', False)
        }

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """
        获取用户的帖子列表

        Args:
            user_id: 用户ID或用户名
            max_posts: 最大帖子数
        """
        try:
            self.logger.info(f"Getting posts from: {user_id}")

            # 尝试使用Graph API
            if self.anti_crawl._access_token:
                graph_data = await self.anti_crawl.graph_api_request(
                    f"{user_id}/posts",
                    {"fields": "id,message,created_time,likes.summary(true),comments.summary(true)", "limit": max_posts}
                )
                if graph_data and 'data' in graph_data:
                    return [self._format_graph_api_post(post) for post in graph_data['data']]

            # 爬虫方式获取
            profile_url = f"{self.base_url}/{user_id}"
            await self.navigate(profile_url)
            await asyncio.sleep(3)

            posts = []
            scroll_count = 0
            max_scrolls = max_posts // 5

            while len(posts) < max_posts and scroll_count < max_scrolls:
                await self.anti_crawl.handle_rate_limit()
                await self.anti_crawl.simulate_human_behavior(self._page)

                # 查找帖子
                post_elements = await self._page.query_selector_all('[data-pagelet^="FeedUnit"]')

                for elem in post_elements:
                    if len(posts) >= max_posts:
                        break

                    try:
                        post = {'user_id': user_id, 'platform': self.platform}

                        # 内容
                        content_elem = await elem.query_selector('[data-ad-comet-preview="message"]')
                        if content_elem:
                            post['content'] = await content_elem.inner_text()

                        # 时间
                        time_elem = await elem.query_selector('a[href*="/posts/"]')
                        if time_elem:
                            time_text = await time_elem.get_attribute('aria-label')
                            if time_text:
                                post['created_at'] = self.parser.parse_date(time_text)

                        # 链接和ID
                        link_elem = await elem.query_selector('a[href*="/posts/"]')
                        if link_elem:
                            href = await link_elem.get_attribute('href')
                            if href:
                                post['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                                if '/posts/' in href:
                                    post['id'] = href.split('/posts/')[-1].split('?')[0]

                        # 统计数据
                        await self._extract_post_stats(elem, post)

                        # 图片和视频
                        images = await elem.query_selector_all('img[src*="fbcdn"]')
                        post['images'] = []
                        for img in images[:5]:
                            src = await img.get_attribute('src')
                            if src and 'emoji' not in src:
                                post['images'].append({'src': src})

                        video_elem = await elem.query_selector('video')
                        if video_elem:
                            post['type'] = 'video'
                        elif post['images']:
                            post['type'] = 'photo'
                        else:
                            post['type'] = 'text'

                        # 应用匹配过滤
                        if post.get('id') and self.matcher.match_post(post):
                            if post not in posts:
                                posts.append(post)

                    except Exception as e:
                        self.logger.warning(f"Failed to parse post: {e}")
                        continue

                # 滚动加载更多
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 4))
                scroll_count += 1

            self.logger.info(f"Got {len(posts)} posts")
            return posts[:max_posts]

        except Exception as e:
            self.logger.error(f"Failed to get posts: {e}")
            return []

    def _format_graph_api_post(self, data: Dict) -> Dict[str, Any]:
        """格式化Graph API返回的帖子数据"""
        return {
            'id': data.get('id'),
            'content': data.get('message', ''),
            'created_at': data.get('created_time'),
            'likes': data.get('likes', {}).get('summary', {}).get('total_count', 0),
            'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
            'platform': self.platform
        }

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        获取帖子详细信息

        Args:
            post_id: 帖子ID
        """
        try:
            self.logger.info(f"Getting post detail: {post_id}")

            # 尝试使用Graph API
            if self.anti_crawl._access_token:
                graph_data = await self.anti_crawl.graph_api_request(
                    post_id,
                    {"fields": "id,message,created_time,from,attachments,likes.summary(true),comments.summary(true),shares"}
                )
                if graph_data:
                    return self._format_graph_api_post_detail(graph_data)

            # 爬虫方式获取
            post_url = f"{self.base_url}/posts/{post_id}"
            await self.navigate(post_url)
            await asyncio.sleep(3)

            post = {'id': post_id, 'url': post_url, 'platform': self.platform}

            # 内容
            content_elem = await self._page.query_selector('[data-ad-comet-preview="message"]')
            if content_elem:
                post['content'] = await content_elem.inner_text()

            # 作者
            author_elem = await self._page.query_selector('a[role="link"] strong')
            if author_elem:
                post['author'] = await author_elem.inner_text()
                author_link = await self._page.query_selector('a[role="link"]')
                if author_link:
                    href = await author_link.get_attribute('href')
                    if href:
                        post['author_url'] = href if href.startswith('http') else f"{self.base_url}{href}"

            # 时间
            time_elem = await self._page.query_selector('a[href*="/posts/"]')
            if time_elem:
                time_text = await time_elem.get_attribute('aria-label')
                if time_text:
                    post['created_at'] = self.parser.parse_date(time_text)

            # 统计数据
            reactions_elem = await self._page.query_selector('[aria-label*="reactions"]')
            if reactions_elem:
                reactions_text = await reactions_elem.get_attribute('aria-label')
                if reactions_text:
                    post['likes'] = self.parser.parse_count(reactions_text)

            comments_elem = await self._page.query_selector('[aria-label*="comments"]')
            if comments_elem:
                comments_text = await comments_elem.inner_text()
                post['comments'] = self.parser.parse_count(comments_text)

            shares_elem = await self._page.query_selector('[aria-label*="shares"]')
            if shares_elem:
                shares_text = await shares_elem.inner_text()
                post['shares'] = self.parser.parse_count(shares_text)

            # 图片
            images = await self._page.query_selector_all('img[src*="fbcdn"]')
            post['images'] = []
            for img in images[:10]:
                src = await img.get_attribute('src')
                if src and 'emoji' not in src:
                    post['images'].append({'src': src})

            # 视频
            video_elem = await self._page.query_selector('video')
            if video_elem:
                video_src = await video_elem.get_attribute('src')
                if video_src:
                    post['video_url'] = video_src

            # 链接
            link_elem = await self._page.query_selector('a[href^="http"]:not([href*="facebook.com"])')
            if link_elem:
                post['external_link'] = await link_elem.get_attribute('href')

            return post

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return {}

    def _format_graph_api_post_detail(self, data: Dict) -> Dict[str, Any]:
        """格式化Graph API返回的帖子详情"""
        post = {
            'id': data.get('id'),
            'content': data.get('message', ''),
            'created_at': data.get('created_time'),
            'likes': data.get('likes', {}).get('summary', {}).get('total_count', 0),
            'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
            'shares': data.get('shares', {}).get('count', 0),
            'platform': self.platform
        }

        # 作者信息
        if 'from' in data:
            post['author'] = data['from'].get('name')
            post['author_id'] = data['from'].get('id')

        # 附件（图片、视频等）
        if 'attachments' in data:
            attachments = data['attachments'].get('data', [])
            post['images'] = []
            for attachment in attachments:
                if attachment.get('type') == 'photo':
                    post['images'].append({'src': attachment.get('media', {}).get('image', {}).get('src')})
                elif attachment.get('type') == 'video':
                    post['video_url'] = attachment.get('media', {}).get('source')

        return post

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        获取帖子的评论

        Args:
            post_id: 帖子ID
            max_comments: 最大评论数
        """
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            # 尝试使用Graph API
            if self.anti_crawl._access_token:
                graph_data = await self.anti_crawl.graph_api_request(
                    f"{post_id}/comments",
                    {"fields": "id,from,message,created_time,like_count", "limit": max_comments}
                )
                if graph_data and 'data' in graph_data:
                    return [self._format_graph_api_comment(comment) for comment in graph_data['data']]

            # 爬虫方式获取
            post_url = f"{self.base_url}/posts/{post_id}"
            if post_id not in self._page.url:
                await self.navigate(post_url)
                await asyncio.sleep(3)

            comments = []

            # 点击查看更多评论
            for _ in range(max_comments // 10):
                load_more = await self._page.query_selector('div[role="button"]:has-text("View more comments")')
                if load_more:
                    await load_more.click()
                    await asyncio.sleep(random.uniform(1.5, 2.5))
                    await self.anti_crawl.handle_rate_limit()
                else:
                    break

            # 解析评论
            comment_elements = await self._page.query_selector_all('[aria-label="Comment"]')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # 作者
                    author_elem = await elem.query_selector('a[role="link"] span')
                    if author_elem:
                        comment['username'] = await author_elem.inner_text()

                    # 内容
                    content_elem = await elem.query_selector('[dir="auto"]')
                    if content_elem:
                        comment['content'] = await content_elem.inner_text()

                    # 时间
                    time_elem = await elem.query_selector('a[href*="comment_id"]')
                    if time_elem:
                        time_text = await time_elem.inner_text()
                        comment['created_at'] = self.parser.parse_date(time_text)

                    # 点赞数
                    like_elem = await elem.query_selector('[aria-label*="reaction"]')
                    if like_elem:
                        like_text = await like_elem.get_attribute('aria-label')
                        comment['likes'] = self.parser.parse_count(like_text) if like_text else 0

                    # 回复数
                    reply_elem = await elem.query_selector('[role="button"]:has-text("Reply")')
                    if reply_elem:
                        reply_text = await reply_elem.inner_text()
                        if 'Reply' in reply_text and len(reply_text) > 5:
                            comment['replies'] = self.parser.parse_count(reply_text)

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(
                            f"{comment.get('username', '')}{comment['content']}".encode()
                        ).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []

    def _format_graph_api_comment(self, data: Dict) -> Dict[str, Any]:
        """格式化Graph API返回的评论数据"""
        return {
            'id': data.get('id'),
            'username': data.get('from', {}).get('name'),
            'user_id': data.get('from', {}).get('id'),
            'content': data.get('message', ''),
            'created_at': data.get('created_time'),
            'likes': data.get('like_count', 0),
            'platform': self.platform
        }

    async def get_user_photos(self, user_id: str, max_photos: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户的照片

        Args:
            user_id: 用户ID或用户名
            max_photos: 最大照片数
        """
        try:
            self.logger.info(f"Getting photos from: {user_id}")

            photos_url = f"{self.base_url}/{user_id}/photos"
            await self.navigate(photos_url)
            await asyncio.sleep(3)

            photos = []
            scroll_count = 0
            max_scrolls = max_photos // 10

            while len(photos) < max_photos and scroll_count < max_scrolls:
                await self.anti_crawl.handle_rate_limit()

                # 查找照片元素
                photo_elements = await self._page.query_selector_all('a[href*="/photo"]')

                for elem in photo_elements[:max_photos]:
                    try:
                        photo = {'user_id': user_id, 'platform': self.platform}

                        # 照片链接
                        href = await elem.get_attribute('href')
                        if href:
                            photo['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                            if 'fbid=' in href:
                                photo['id'] = parse_qs(urlparse(href).query).get('fbid', [''])[0]

                        # 缩略图
                        img_elem = await elem.query_selector('img')
                        if img_elem:
                            photo['thumbnail'] = await img_elem.get_attribute('src')

                        if photo.get('url') and photo not in photos:
                            photos.append(photo)

                    except Exception as e:
                        self.logger.warning(f"Failed to parse photo: {e}")
                        continue

                # 滚动加载更多
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))
                scroll_count += 1

            self.logger.info(f"Got {len(photos)} photos")
            return photos[:max_photos]

        except Exception as e:
            self.logger.error(f"Failed to get photos: {e}")
            return []

    async def get_group_posts(self, group_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """
        获取群组的帖子

        Args:
            group_id: 群组ID
            max_posts: 最大帖子数
        """
        try:
            self.logger.info(f"Getting posts from group: {group_id}")

            group_url = f"{self.base_url}/groups/{group_id}"
            await self.navigate(group_url)
            await asyncio.sleep(3)

            posts = []
            scroll_count = 0
            max_scrolls = max_posts // 5

            while len(posts) < max_posts and scroll_count < max_scrolls:
                await self.anti_crawl.handle_rate_limit()
                await self.anti_crawl.simulate_human_behavior(self._page)

                # 查找帖子
                post_elements = await self._page.query_selector_all('[data-pagelet^="FeedUnit"]')

                for elem in post_elements:
                    if len(posts) >= max_posts:
                        break

                    try:
                        post = {'group_id': group_id, 'platform': self.platform, 'source': 'group'}

                        # 内容
                        content_elem = await elem.query_selector('[data-ad-comet-preview="message"]')
                        if content_elem:
                            post['content'] = await content_elem.inner_text()

                        # 作者
                        author_elem = await elem.query_selector('a[role="link"] strong')
                        if author_elem:
                            post['author'] = await author_elem.inner_text()

                        # 时间和链接
                        link_elem = await elem.query_selector('a[href*="/posts/"]')
                        if link_elem:
                            href = await link_elem.get_attribute('href')
                            if href:
                                post['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                                if '/posts/' in href:
                                    post['id'] = href.split('/posts/')[-1].split('?')[0]

                            time_text = await link_elem.get_attribute('aria-label')
                            if time_text:
                                post['created_at'] = self.parser.parse_date(time_text)

                        # 统计数据
                        await self._extract_post_stats(elem, post)

                        if post.get('id') and self.matcher.match_post(post):
                            if post not in posts:
                                posts.append(post)

                    except Exception as e:
                        self.logger.warning(f"Failed to parse group post: {e}")
                        continue

                # 滚动加载更多
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 4))
                scroll_count += 1

            self.logger.info(f"Got {len(posts)} group posts")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get group posts: {e}")
            return []

    async def get_page_info(self, page_id: str) -> Dict[str, Any]:
        """
        获取页面信息

        Args:
            page_id: 页面ID或页面名
        """
        try:
            self.logger.info(f"Getting page info: {page_id}")

            # 尝试使用Graph API
            if self.anti_crawl._access_token:
                graph_data = await self.anti_crawl.graph_api_request(
                    page_id,
                    {"fields": "id,name,username,about,category,followers_count,website,phone"}
                )
                if graph_data:
                    return {
                        'page_id': graph_data.get('id'),
                        'name': graph_data.get('name'),
                        'username': graph_data.get('username'),
                        'about': graph_data.get('about'),
                        'category': graph_data.get('category'),
                        'followers': graph_data.get('followers_count', 0),
                        'website': graph_data.get('website'),
                        'phone': graph_data.get('phone'),
                        'platform': self.platform
                    }

            # 爬虫方式获取
            page_url = f"{self.base_url}/{page_id}"
            await self.navigate(page_url)
            await asyncio.sleep(3)

            page_info = {'page_id': page_id, 'platform': self.platform, 'type': 'page'}

            # 页面名称
            name_elem = await self._page.query_selector('h1')
            if name_elem:
                page_info['name'] = await name_elem.inner_text()

            # 分类
            category_elem = await self._page.query_selector('div[class*="category"]')
            if category_elem:
                page_info['category'] = await category_elem.inner_text()

            # 点赞数
            likes_elem = await self._page.query_selector('a[href*="likes"]')
            if likes_elem:
                likes_text = await likes_elem.inner_text()
                page_info['likes'] = self.parser.parse_count(likes_text)

            # 关注数
            followers_elem = await self._page.query_selector('a[href*="followers"]')
            if followers_elem:
                followers_text = await followers_elem.inner_text()
                page_info['followers'] = self.parser.parse_count(followers_text)

            # 简介
            about_elem = await self._page.query_selector('div[class*="about"]')
            if about_elem:
                page_info['about'] = await about_elem.inner_text()

            return page_info

        except Exception as e:
            self.logger.error(f"Failed to get page info: {e}")
            return {}
