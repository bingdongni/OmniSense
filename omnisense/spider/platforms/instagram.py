"""
Instagram Spider Implementation
完整的Instagram平台爬虫实现 - 4层架构

Layer 1 - Spider Layer: 数据爬取层
Layer 2 - Anti-Crawl Layer: 反爬虫层
Layer 3 - Matcher Layer: 内容过滤层
Layer 4 - Interaction Layer: 互动操作层
"""

import asyncio
import hashlib
import hmac
import json
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

import httpx
from playwright.async_api import Page, ElementHandle

from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger


# ============================================================================
# Constants and Enums
# ============================================================================

class MediaType(Enum):
    """Instagram媒体类型"""
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    REELS = "reels"
    IGTV = "igtv"
    STORY = "story"


class SearchType(Enum):
    """搜索类型"""
    HASHTAG = "hashtag"
    LOCATION = "location"
    USER = "user"
    TOP = "top"


class InteractionType(Enum):
    """互动类型"""
    LIKE = "like"
    UNLIKE = "unlike"
    COMMENT = "comment"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    SAVE = "save"
    SHARE = "share"
    MESSAGE = "message"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class InstagramPost:
    """Instagram帖子数据结构"""
    id: str
    shortcode: str
    url: str
    media_type: MediaType
    caption: str
    likes_count: int
    comments_count: int
    timestamp: datetime
    owner: Dict[str, Any]
    media_urls: List[str]
    hashtags: List[str]
    mentions: List[str]
    location: Optional[Dict[str, Any]] = None
    is_video: bool = False
    video_duration: Optional[float] = None
    platform: str = "instagram"


@dataclass
class InstagramUser:
    """Instagram用户数据结构"""
    user_id: str
    username: str
    full_name: str
    biography: str
    followers_count: int
    following_count: int
    posts_count: int
    profile_pic_url: str
    is_verified: bool
    is_private: bool
    is_business: bool
    external_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    platform: str = "instagram"


@dataclass
class InstagramComment:
    """Instagram评论数据结构"""
    id: str
    text: str
    owner: Dict[str, Any]
    created_at: datetime
    likes_count: int
    post_id: str
    platform: str = "instagram"


@dataclass
class MatcherConfig:
    """内容过滤配置"""
    min_likes: int = 0
    max_likes: Optional[int] = None
    min_comments: int = 0
    max_comments: Optional[int] = None
    min_followers: int = 0
    max_followers: Optional[int] = None
    required_hashtags: List[str] = None
    excluded_hashtags: List[str] = None
    required_locations: List[str] = None
    allowed_media_types: List[MediaType] = None
    verified_only: bool = False
    min_engagement_rate: float = 0.0


# ============================================================================
# Layer 2 - Anti-Crawl Layer (反爬虫层)
# ============================================================================

class InstagramAntiCrawl:
    """
    Instagram反爬虫处理层

    功能:
    - Graph API集成
    - Cookie认证
    - CSRF Token处理
    - 设备指纹伪装
    - 请求签名
    - Rate limit处理
    - 双因素认证
    """

    def __init__(self, logger):
        self.logger = logger
        self._csrf_token: Optional[str] = None
        self._session_id: Optional[str] = None
        self._device_id: str = self._generate_device_id()
        self._app_id: str = "936619743392459"  # Instagram App ID
        self._api_version: str = "v1"
        self._request_count: int = 0
        self._last_request_time: float = 0
        self._rate_limit_per_hour: int = 200
        self._failed_requests: int = 0
        self._proxy_list: List[str] = []
        self._current_proxy_index: int = 0

    def _generate_device_id(self) -> str:
        """生成设备ID"""
        return f"android-{uuid.uuid4().hex[:16]}"

    def _generate_uuid(self) -> str:
        """生成UUID"""
        return str(uuid.uuid4())

    async def extract_csrf_token(self, page: Page) -> Optional[str]:
        """从页面中提取CSRF Token"""
        try:
            # 方法1: 从页面meta标签提取
            csrf_meta = await page.query_selector('meta[name="csrf-token"]')
            if csrf_meta:
                self._csrf_token = await csrf_meta.get_attribute("content")
                self.logger.debug(f"Extracted CSRF token from meta tag: {self._csrf_token[:20]}...")
                return self._csrf_token

            # 方法2: 从JavaScript变量提取
            csrf_js = await page.evaluate("""
                () => {
                    if (window._sharedData && window._sharedData.config) {
                        return window._sharedData.config.csrf_token;
                    }
                    return null;
                }
            """)
            if csrf_js:
                self._csrf_token = csrf_js
                self.logger.debug(f"Extracted CSRF token from JS: {self._csrf_token[:20]}...")
                return self._csrf_token

            # 方法3: 从Cookie提取
            cookies = await page.context.cookies()
            for cookie in cookies:
                if cookie['name'] == 'csrftoken':
                    self._csrf_token = cookie['value']
                    self.logger.debug(f"Extracted CSRF token from cookie: {self._csrf_token[:20]}...")
                    return self._csrf_token

            self.logger.warning("Could not extract CSRF token")
            return None

        except Exception as e:
            self.logger.error(f"Failed to extract CSRF token: {e}")
            return None

    async def get_session_id(self, page: Page) -> Optional[str]:
        """获取Session ID"""
        try:
            cookies = await page.context.cookies()
            for cookie in cookies:
                if cookie['name'] == 'sessionid':
                    self._session_id = cookie['value']
                    self.logger.debug(f"Got session ID: {self._session_id[:20]}...")
                    return self._session_id
            return None
        except Exception as e:
            self.logger.error(f"Failed to get session ID: {e}")
            return None

    def generate_device_fingerprint(self) -> Dict[str, Any]:
        """生成设备指纹"""
        screen_resolutions = [
            (1920, 1080), (1366, 768), (1440, 900),
            (1536, 864), (1280, 720), (2560, 1440)
        ]
        resolution = random.choice(screen_resolutions)

        return {
            "device_id": self._device_id,
            "uuid": self._generate_uuid(),
            "screen_width": resolution[0],
            "screen_height": resolution[1],
            "pixel_ratio": random.choice([1, 1.5, 2, 3]),
            "timezone_offset": random.choice([-480, -420, -360, -300, 0, 60, 120, 480]),
            "language": random.choice(["en-US", "en-GB", "zh-CN", "es-ES"]),
            "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
            "hardware_concurrency": random.choice([2, 4, 8, 12, 16]),
            "device_memory": random.choice([4, 8, 16, 32]),
            "connection_type": random.choice(["4g", "wifi", "ethernet"]),
        }

    def sign_request(self, data: Dict[str, Any]) -> str:
        """签名请求数据 (Instagram API签名)"""
        try:
            # Instagram使用HMAC-SHA256签名
            secret = "fc9297e6c67812b16a6242f6c326c6f3"  # Instagram签名密钥(示例)
            message = json.dumps(data, separators=(',', ':'))
            signature = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            return f"ig_sig_key_version=4&signed_body={signature}.{message}"
        except Exception as e:
            self.logger.error(f"Failed to sign request: {e}")
            return ""

    async def check_rate_limit(self) -> bool:
        """检查是否超过速率限制"""
        current_time = time.time()
        time_diff = current_time - self._last_request_time

        # 计算每小时请求数
        if self._request_count >= self._rate_limit_per_hour:
            if time_diff < 3600:
                wait_time = 3600 - time_diff
                self.logger.warning(f"Rate limit reached. Waiting {wait_time:.0f}s...")
                await asyncio.sleep(wait_time)
                self._request_count = 0

        # 请求间隔随机延迟 (更人性化)
        if time_diff < 2:
            delay = random.uniform(1.5, 3.5)
            await asyncio.sleep(delay)

        self._last_request_time = current_time
        self._request_count += 1
        return True

    async def handle_challenge(self, page: Page) -> bool:
        """处理Instagram验证挑战"""
        try:
            # 检查是否出现验证页面
            challenge_selectors = [
                'input[name="verificationCode"]',
                'button:has-text("Send Security Code")',
                'form[method="POST"]#challenge_form'
            ]

            for selector in challenge_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    self.logger.warning("Challenge detected! Manual verification required.")
                    # 这里可以集成自动化验证服务
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Error checking challenge: {e}")
            return False

    async def handle_two_factor(self, page: Page, code: Optional[str] = None) -> bool:
        """处理双因素认证"""
        try:
            # 检查是否需要2FA
            code_input = await page.query_selector('input[name="verificationCode"]')
            if not code_input:
                return True

            if not code:
                self.logger.error("2FA code required but not provided")
                return False

            # 输入验证码
            await code_input.fill(code)

            # 点击确认
            confirm_btn = await page.query_selector('button[type="submit"]')
            if confirm_btn:
                await confirm_btn.click()
                await asyncio.sleep(3)
                return True

            return False
        except Exception as e:
            self.logger.error(f"2FA handling failed: {e}")
            return False

    def get_api_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        return {
            "X-IG-App-ID": self._app_id,
            "X-IG-WWW-Claim": "0",
            "X-Instagram-AJAX": "1",
            "X-CSRFToken": self._csrf_token or "",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.instagram.com/",
            "User-Agent": self._get_random_user_agent(),
        }

    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        ]
        return random.choice(user_agents)

    async def bypass_bot_detection(self, page: Page) -> bool:
        """绕过机器人检测"""
        try:
            # 注入反检测脚本
            await page.add_init_script("""
                // 移除webdriver标记
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });

                // 覆盖权限查询
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // 伪装Chrome
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // 伪装语言
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

            return True
        except Exception as e:
            self.logger.error(f"Failed to bypass bot detection: {e}")
            return False

    async def rotate_proxy(self) -> Optional[str]:
        """轮换代理"""
        if not self._proxy_list:
            return None

        self._current_proxy_index = (self._current_proxy_index + 1) % len(self._proxy_list)
        return self._proxy_list[self._current_proxy_index]

    def add_proxy(self, proxy: str):
        """添加代理到池"""
        if proxy not in self._proxy_list:
            self._proxy_list.append(proxy)
            self.logger.info(f"Added proxy: {proxy}")


# ============================================================================
# Layer 3 - Matcher Layer (内容过滤层)
# ============================================================================

class InstagramMatcher:
    """
    Instagram内容匹配过滤层

    功能:
    - 点赞数过滤
    - 评论数过滤
    - 粉丝数过滤
    - 标签匹配
    - 位置过滤
    - 媒体类型过滤
    """

    def __init__(self, config: MatcherConfig, logger):
        self.config = config
        self.logger = logger

    def match_post(self, post: InstagramPost) -> bool:
        """匹配帖子是否符合条件"""
        try:
            # 点赞数过滤
            if post.likes_count < self.config.min_likes:
                self.logger.debug(f"Post {post.id} filtered: likes {post.likes_count} < {self.config.min_likes}")
                return False

            if self.config.max_likes and post.likes_count > self.config.max_likes:
                self.logger.debug(f"Post {post.id} filtered: likes {post.likes_count} > {self.config.max_likes}")
                return False

            # 评论数过滤
            if post.comments_count < self.config.min_comments:
                self.logger.debug(f"Post {post.id} filtered: comments {post.comments_count} < {self.config.min_comments}")
                return False

            if self.config.max_comments and post.comments_count > self.config.max_comments:
                self.logger.debug(f"Post {post.id} filtered: comments {post.comments_count} > {self.config.max_comments}")
                return False

            # 标签匹配
            if self.config.required_hashtags:
                if not any(tag in post.hashtags for tag in self.config.required_hashtags):
                    self.logger.debug(f"Post {post.id} filtered: missing required hashtags")
                    return False

            # 排除标签
            if self.config.excluded_hashtags:
                if any(tag in post.hashtags for tag in self.config.excluded_hashtags):
                    self.logger.debug(f"Post {post.id} filtered: contains excluded hashtags")
                    return False

            # 媒体类型过滤
            if self.config.allowed_media_types:
                if post.media_type not in self.config.allowed_media_types:
                    self.logger.debug(f"Post {post.id} filtered: media type {post.media_type}")
                    return False

            # 位置过滤
            if self.config.required_locations and post.location:
                location_name = post.location.get('name', '').lower()
                if not any(loc.lower() in location_name for loc in self.config.required_locations):
                    self.logger.debug(f"Post {post.id} filtered: location mismatch")
                    return False

            self.logger.debug(f"Post {post.id} matched all criteria")
            return True

        except Exception as e:
            self.logger.error(f"Error matching post: {e}")
            return False

    def match_user(self, user: InstagramUser) -> bool:
        """匹配用户是否符合条件"""
        try:
            # 粉丝数过滤
            if user.followers_count < self.config.min_followers:
                self.logger.debug(f"User {user.username} filtered: followers {user.followers_count} < {self.config.min_followers}")
                return False

            if self.config.max_followers and user.followers_count > self.config.max_followers:
                self.logger.debug(f"User {user.username} filtered: followers {user.followers_count} > {self.config.max_followers}")
                return False

            # 认证用户过滤
            if self.config.verified_only and not user.is_verified:
                self.logger.debug(f"User {user.username} filtered: not verified")
                return False

            self.logger.debug(f"User {user.username} matched all criteria")
            return True

        except Exception as e:
            self.logger.error(f"Error matching user: {e}")
            return False

    def calculate_engagement_rate(self, post: InstagramPost) -> float:
        """计算互动率"""
        try:
            if not post.owner or post.owner.get('followers_count', 0) == 0:
                return 0.0

            followers = post.owner.get('followers_count', 0)
            engagements = post.likes_count + post.comments_count

            return (engagements / followers) * 100
        except Exception as e:
            self.logger.error(f"Error calculating engagement rate: {e}")
            return 0.0

    def filter_posts(self, posts: List[InstagramPost]) -> List[InstagramPost]:
        """批量过滤帖子"""
        filtered = []
        for post in posts:
            if self.match_post(post):
                engagement_rate = self.calculate_engagement_rate(post)
                if engagement_rate >= self.config.min_engagement_rate:
                    filtered.append(post)

        self.logger.info(f"Filtered {len(filtered)}/{len(posts)} posts")
        return filtered


# ============================================================================
# Layer 4 - Interaction Layer (互动操作层)
# ============================================================================

class InstagramInteraction:
    """
    Instagram互动操作层

    功能:
    - 点赞/取消点赞
    - 评论发布
    - 关注/取消关注
    - 保存帖子
    - 分享到Story
    - 消息发送
    """

    def __init__(self, page: Page, anti_crawl: InstagramAntiCrawl, logger):
        self.page = page
        self.anti_crawl = anti_crawl
        self.logger = logger
        self._interaction_count: Dict[InteractionType, int] = {}

    async def like_post(self, post_id: str) -> bool:
        """点赞帖子"""
        try:
            self.logger.info(f"Liking post: {post_id}")

            # 导航到帖子页面
            post_url = f"https://www.instagram.com/p/{post_id}/"
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 2))

            # 查找点赞按钮
            like_button_selectors = [
                'svg[aria-label="Like"]',
                'button[aria-label="Like"]',
                'span[aria-label="Like"]',
            ]

            for selector in like_button_selectors:
                like_btn = await self.page.query_selector(selector)
                if like_btn:
                    await like_btn.click()
                    await asyncio.sleep(random.uniform(0.5, 1.5))

                    self._increment_interaction(InteractionType.LIKE)
                    self.logger.info(f"Successfully liked post: {post_id}")
                    return True

            self.logger.warning(f"Could not find like button for post: {post_id}")
            return False

        except Exception as e:
            self.logger.error(f"Failed to like post {post_id}: {e}")
            return False

    async def unlike_post(self, post_id: str) -> bool:
        """取消点赞"""
        try:
            self.logger.info(f"Unliking post: {post_id}")

            post_url = f"https://www.instagram.com/p/{post_id}/"
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 2))

            # 查找取消点赞按钮
            unlike_button_selectors = [
                'svg[aria-label="Unlike"]',
                'button[aria-label="Unlike"]',
            ]

            for selector in unlike_button_selectors:
                unlike_btn = await self.page.query_selector(selector)
                if unlike_btn:
                    await unlike_btn.click()
                    await asyncio.sleep(random.uniform(0.5, 1.5))

                    self._increment_interaction(InteractionType.UNLIKE)
                    self.logger.info(f"Successfully unliked post: {post_id}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to unlike post {post_id}: {e}")
            return False

    async def comment_on_post(self, post_id: str, comment_text: str) -> bool:
        """在帖子上发表评论"""
        try:
            self.logger.info(f"Commenting on post: {post_id}")

            post_url = f"https://www.instagram.com/p/{post_id}/"
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 3))

            # 查找评论输入框
            comment_input = await self.page.query_selector('textarea[aria-label="Add a comment…"]')
            if not comment_input:
                comment_input = await self.page.query_selector('textarea[placeholder="Add a comment…"]')

            if comment_input:
                # 模拟人类输入
                await comment_input.click()
                await asyncio.sleep(random.uniform(0.5, 1))

                for char in comment_text:
                    await comment_input.type(char, delay=random.randint(50, 150))

                await asyncio.sleep(random.uniform(1, 2))

                # 点击发布按钮
                post_button = await self.page.query_selector('button[type="submit"]:has-text("Post")')
                if post_button:
                    await post_button.click()
                    await asyncio.sleep(random.uniform(1, 2))

                    self._increment_interaction(InteractionType.COMMENT)
                    self.logger.info(f"Successfully commented on post: {post_id}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to comment on post {post_id}: {e}")
            return False

    async def follow_user(self, username: str) -> bool:
        """关注用户"""
        try:
            self.logger.info(f"Following user: {username}")

            profile_url = f"https://www.instagram.com/{username}/"
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 3))

            # 查找关注按钮
            follow_button_selectors = [
                'button:has-text("Follow")',
                'button._acan._acap._acas._aj1-',
            ]

            for selector in follow_button_selectors:
                follow_btn = await self.page.query_selector(selector)
                if follow_btn:
                    button_text = await follow_btn.inner_text()
                    if "Follow" in button_text and "Following" not in button_text:
                        await follow_btn.click()
                        await asyncio.sleep(random.uniform(1, 2))

                        self._increment_interaction(InteractionType.FOLLOW)
                        self.logger.info(f"Successfully followed user: {username}")
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to follow user {username}: {e}")
            return False

    async def unfollow_user(self, username: str) -> bool:
        """取消关注用户"""
        try:
            self.logger.info(f"Unfollowing user: {username}")

            profile_url = f"https://www.instagram.com/{username}/"
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 3))

            # 查找Following按钮
            following_btn = await self.page.query_selector('button:has-text("Following")')
            if following_btn:
                await following_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

                # 确认取消关注
                unfollow_confirm = await self.page.query_selector('button:has-text("Unfollow")')
                if unfollow_confirm:
                    await unfollow_confirm.click()
                    await asyncio.sleep(random.uniform(1, 2))

                    self._increment_interaction(InteractionType.UNFOLLOW)
                    self.logger.info(f"Successfully unfollowed user: {username}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to unfollow user {username}: {e}")
            return False

    async def save_post(self, post_id: str) -> bool:
        """保存帖子"""
        try:
            self.logger.info(f"Saving post: {post_id}")

            post_url = f"https://www.instagram.com/p/{post_id}/"
            await self.page.goto(post_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1, 2))

            # 查找保存按钮
            save_btn = await self.page.query_selector('svg[aria-label="Save"]')
            if save_btn:
                await save_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1.5))

                self._increment_interaction(InteractionType.SAVE)
                self.logger.info(f"Successfully saved post: {post_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to save post {post_id}: {e}")
            return False

    async def send_message(self, username: str, message: str) -> bool:
        """发送私信"""
        try:
            self.logger.info(f"Sending message to: {username}")

            # 导航到消息页面
            await self.page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 3))

            # 点击新建消息
            new_message_btn = await self.page.query_selector('svg[aria-label="New message"]')
            if new_message_btn:
                await new_message_btn.click()
                await asyncio.sleep(random.uniform(1, 2))

                # 搜索用户
                search_input = await self.page.query_selector('input[placeholder="Search..."]')
                if search_input:
                    await search_input.type(username, delay=random.randint(50, 150))
                    await asyncio.sleep(random.uniform(1, 2))

                    # 选择用户
                    user_result = await self.page.query_selector(f'div:has-text("{username}")')
                    if user_result:
                        await user_result.click()
                        await asyncio.sleep(random.uniform(0.5, 1))

                        # 点击Next
                        next_btn = await self.page.query_selector('button:has-text("Next")')
                        if next_btn:
                            await next_btn.click()
                            await asyncio.sleep(random.uniform(1, 2))

                            # 输入消息
                            message_input = await self.page.query_selector('textarea[placeholder="Message..."]')
                            if message_input:
                                await message_input.type(message, delay=random.randint(50, 150))
                                await asyncio.sleep(random.uniform(0.5, 1))

                                # 发送
                                send_btn = await self.page.query_selector('button:has-text("Send")')
                                if send_btn:
                                    await send_btn.click()
                                    await asyncio.sleep(random.uniform(1, 2))

                                    self._increment_interaction(InteractionType.MESSAGE)
                                    self.logger.info(f"Successfully sent message to: {username}")
                                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to send message to {username}: {e}")
            return False

    def _increment_interaction(self, interaction_type: InteractionType):
        """增加互动计数"""
        if interaction_type not in self._interaction_count:
            self._interaction_count[interaction_type] = 0
        self._interaction_count[interaction_type] += 1

    def get_interaction_stats(self) -> Dict[str, int]:
        """获取互动统计"""
        return {k.value: v for k, v in self._interaction_count.items()}


# ============================================================================
# Layer 1 - Spider Layer (数据爬取层)
# ============================================================================

class InstagramSpider(BaseSpider):
    """
    Instagram图片/视频社交平台爬虫 - 完整4层架构

    Platform Information:
    - Base URL: https://www.instagram.com
    - Login Required: Yes (for most features)
    - Rate Limit: Strict (200 requests/hour)
    - Special Features: Posts, Stories, Reels, IGTV, Graph API
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        matcher_config: Optional[MatcherConfig] = None
    ):
        super().__init__(platform="instagram", headless=headless, proxy=proxy)
        self.base_url = "https://www.instagram.com"
        self.api_base_url = "https://www.instagram.com/api/v1"
        self.graph_api_url = "https://graph.instagram.com"

        # 初始化各层
        self.anti_crawl = InstagramAntiCrawl(self.logger)
        self.matcher = InstagramMatcher(matcher_config or MatcherConfig(), self.logger)
        self.interaction: Optional[InstagramInteraction] = None

        # Graph API配置
        self._access_token: Optional[str] = None
        self._graph_api_enabled: bool = False

    async def start(self) -> None:
        """启动爬虫并初始化各层"""
        await super().start()

        # 初始化互动层
        self.interaction = InstagramInteraction(self._page, self.anti_crawl, self.logger)

        # 应用反爬虫措施
        await self.anti_crawl.bypass_bot_detection(self._page)

    async def login(
        self,
        username: str,
        password: str,
        two_factor_code: Optional[str] = None
    ) -> bool:
        """
        登录Instagram

        Args:
            username: 用户名或邮箱
            password: 密码
            two_factor_code: 双因素认证码(可选)
        """
        try:
            self.logger.info(f"Logging in to Instagram as {username}...")

            # 检查是否已有有效Cookie
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)

                # 验证登录状态
                if await self._page.query_selector('svg[aria-label="Home"]'):
                    self._is_logged_in = True
                    await self.anti_crawl.extract_csrf_token(self._page)
                    await self.anti_crawl.get_session_id(self._page)
                    self.logger.info("Logged in with saved cookies")
                    return True

            # 执行登录流程
            await self.navigate(f"{self.base_url}/accounts/login/")
            await asyncio.sleep(random.uniform(2, 4))

            # 拒绝Cookie通知(如果有)
            try:
                decline_btn = await self._page.query_selector('button:has-text("Decline")')
                if decline_btn:
                    await decline_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

            # 填写用户名
            username_input = await self._page.wait_for_selector(
                'input[name="username"]',
                timeout=10000
            )
            await username_input.click()
            await asyncio.sleep(random.uniform(0.5, 1))
            await username_input.type(username, delay=random.randint(80, 150))

            # 填写密码
            password_input = await self._page.wait_for_selector(
                'input[name="password"]',
                timeout=10000
            )
            await password_input.click()
            await asyncio.sleep(random.uniform(0.5, 1))
            await password_input.type(password, delay=random.randint(80, 150))

            await asyncio.sleep(random.uniform(1, 2))

            # 点击登录
            login_btn = await self._page.wait_for_selector(
                'button[type="submit"]',
                timeout=10000
            )
            await login_btn.click()
            await asyncio.sleep(random.uniform(4, 6))

            # 处理双因素认证
            if two_factor_code:
                if not await self.anti_crawl.handle_two_factor(self._page, two_factor_code):
                    self.logger.error("2FA verification failed")
                    return False
                await asyncio.sleep(3)

            # 处理"保存登录信息"提示
            try:
                not_now_btn = await self._page.wait_for_selector(
                    'button:has-text("Not Now")',
                    timeout=5000
                )
                if not_now_btn:
                    await not_now_btn.click()
                    await asyncio.sleep(2)
            except:
                pass

            # 处理"开启通知"提示
            try:
                not_now_btn = await self._page.wait_for_selector(
                    'button:has-text("Not Now")',
                    timeout=5000
                )
                if not_now_btn:
                    await not_now_btn.click()
                    await asyncio.sleep(2)
            except:
                pass

            # 验证登录成功
            if await self._page.query_selector('svg[aria-label="Home"]'):
                self._is_logged_in = True
                await self._save_cookies()
                await self.anti_crawl.extract_csrf_token(self._page)
                await self.anti_crawl.get_session_id(self._page)
                self.logger.info("Login successful")
                return True

            # 检查是否遇到验证挑战
            if not await self.anti_crawl.handle_challenge(self._page):
                self.logger.error("Challenge verification required")
                return False

            self.logger.error("Login failed")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(
        self,
        keyword: str,
        search_type: SearchType = SearchType.HASHTAG,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索Instagram内容

        Args:
            keyword: 搜索关键词
            search_type: 搜索类型(标签/位置/用户)
            max_results: 最大结果数
        """
        try:
            self.logger.info(f"Searching Instagram for '{keyword}' ({search_type.value})")

            await self.anti_crawl.check_rate_limit()

            # 根据搜索类型构建URL
            if search_type == SearchType.HASHTAG:
                search_url = f"{self.base_url}/explore/tags/{keyword}/"
            elif search_type == SearchType.LOCATION:
                search_url = f"{self.base_url}/explore/locations/{keyword}/"
            elif search_type == SearchType.USER:
                search_url = f"{self.base_url}/{keyword}/"
            else:
                search_url = f"{self.base_url}/explore/search/?q={keyword}"

            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 4))

            # 滚动加载更多内容
            posts_loaded = 0
            scroll_attempts = 0
            max_scrolls = max_results // 12 + 2

            while posts_loaded < max_results and scroll_attempts < max_scrolls:
                # 向下滚动
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

                # 统计已加载的帖子
                post_elements = await self._page.query_selector_all('article a[href*="/p/"]')
                posts_loaded = len(post_elements)
                scroll_attempts += 1

                self.logger.debug(f"Loaded {posts_loaded} posts after {scroll_attempts} scrolls")

            # 解析搜索结果
            results = []
            post_elements = await self._page.query_selector_all('article a[href*="/p/"]')

            for elem in post_elements[:max_results]:
                try:
                    result = await self._parse_search_result_element(elem)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to parse search result: {e}")
                    continue

            self.logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def _parse_search_result_element(self, elem: ElementHandle) -> Optional[Dict[str, Any]]:
        """解析搜索结果元素"""
        try:
            result = {'platform': self.platform}

            # 获取帖子URL和ID
            href = await elem.get_attribute('href')
            if href:
                result['url'] = f"{self.base_url}{href}" if not href.startswith('http') else href

                # 提取shortcode
                match = re.search(r'/p/([A-Za-z0-9_-]+)', href)
                if match:
                    result['shortcode'] = match.group(1)
                    result['id'] = match.group(1)

            # 获取缩略图
            img = await elem.query_selector('img')
            if img:
                result['thumbnail'] = await img.get_attribute('src')
                alt = await img.get_attribute('alt')
                if alt:
                    result['caption'] = alt

            # 获取互动数据(如果可见)
            engagement_elem = await elem.query_selector('ul li')
            if engagement_elem:
                text = await engagement_elem.inner_text()
                result['engagement_preview'] = text

            return result if result.get('id') else None

        except Exception as e:
            self.logger.error(f"Failed to parse element: {e}")
            return None

    async def get_user_profile(self, username: str) -> Optional[InstagramUser]:
        """
        获取用户资料

        Args:
            username: 用户名
        """
        try:
            self.logger.info(f"Getting profile: {username}")

            await self.anti_crawl.check_rate_limit()

            profile_url = f"{self.base_url}/{username}/"
            await self.navigate(profile_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 检查用户是否存在
            if await self._page.query_selector('span:has-text("Sorry, this page isn\'t available.")'):
                self.logger.warning(f"User not found: {username}")
                return None

            # 提取用户数据
            user_data = await self._page.evaluate("""
                () => {
                    const data = window._sharedData?.entry_data?.ProfilePage?.[0]?.graphql?.user;
                    return data || null;
                }
            """)

            if user_data:
                return self._parse_user_data(user_data)

            # 备用解析方法(从页面元素)
            return await self._parse_user_profile_from_page(username)

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return None

    def _parse_user_data(self, data: Dict[str, Any]) -> InstagramUser:
        """解析用户数据"""
        return InstagramUser(
            user_id=data.get('id', ''),
            username=data.get('username', ''),
            full_name=data.get('full_name', ''),
            biography=data.get('biography', ''),
            followers_count=data.get('edge_followed_by', {}).get('count', 0),
            following_count=data.get('edge_follow', {}).get('count', 0),
            posts_count=data.get('edge_owner_to_timeline_media', {}).get('count', 0),
            profile_pic_url=data.get('profile_pic_url_hd', ''),
            is_verified=data.get('is_verified', False),
            is_private=data.get('is_private', False),
            is_business=data.get('is_business_account', False),
            external_url=data.get('external_url'),
            email=data.get('business_email'),
            phone=data.get('business_phone_number'),
            category=data.get('category_name'),
        )

    async def _parse_user_profile_from_page(self, username: str) -> Optional[InstagramUser]:
        """从页面元素解析用户资料"""
        try:
            # 用户名
            full_name_elem = await self._page.query_selector('header section h1')
            full_name = await full_name_elem.inner_text() if full_name_elem else username

            # 统计数据
            stats = await self._page.query_selector_all('header section ul li span')
            posts_count = 0
            followers_count = 0
            following_count = 0

            if len(stats) >= 3:
                posts_text = await stats[0].inner_text()
                posts_count = self.parser.parse_count(posts_text)

                followers_title = await stats[1].get_attribute('title')
                followers_text = followers_title or await stats[1].inner_text()
                followers_count = self.parser.parse_count(followers_text)

                following_text = await stats[2].inner_text()
                following_count = self.parser.parse_count(following_text)

            # 简介
            bio_elem = await self._page.query_selector('header section div > span')
            bio = await bio_elem.inner_text() if bio_elem else ''

            # 头像
            avatar_elem = await self._page.query_selector('header img')
            avatar = await avatar_elem.get_attribute('src') if avatar_elem else ''

            # 认证状态
            verified_elem = await self._page.query_selector('svg[aria-label="Verified"]')
            is_verified = verified_elem is not None

            # 私密账户
            private_elem = await self._page.query_selector('h2:has-text("This Account is Private")')
            is_private = private_elem is not None

            return InstagramUser(
                user_id='',  # 需要从API获取
                username=username,
                full_name=full_name,
                biography=bio,
                followers_count=followers_count,
                following_count=following_count,
                posts_count=posts_count,
                profile_pic_url=avatar,
                is_verified=is_verified,
                is_private=is_private,
                is_business=False,
            )

        except Exception as e:
            self.logger.error(f"Failed to parse user profile: {e}")
            return None

    async def get_user_posts(
        self,
        username: str,
        max_posts: int = 20,
        apply_filter: bool = True
    ) -> List[InstagramPost]:
        """
        获取用户帖子

        Args:
            username: 用户名
            max_posts: 最大帖子数
            apply_filter: 是否应用过滤器
        """
        try:
            self.logger.info(f"Getting posts from: {username}")

            await self.anti_crawl.check_rate_limit()

            profile_url = f"{self.base_url}/{username}/"
            await self.navigate(profile_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载帖子
            posts_loaded = 0
            scroll_attempts = 0
            max_scrolls = max_posts // 12 + 2

            while posts_loaded < max_posts and scroll_attempts < max_scrolls:
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

                post_elements = await self._page.query_selector_all('article a[href*="/p/"]')
                posts_loaded = len(post_elements)
                scroll_attempts += 1

            # 收集帖子链接
            post_elements = await self._page.query_selector_all('article a[href*="/p/"]')
            post_links = []

            for elem in post_elements[:max_posts]:
                href = await elem.get_attribute('href')
                if href:
                    match = re.search(r'/p/([A-Za-z0-9_-]+)', href)
                    if match:
                        post_links.append(match.group(1))

            # 获取详细信息
            posts = []
            for shortcode in post_links:
                post = await self.get_post_detail(shortcode)
                if post:
                    # 应用过滤器
                    if apply_filter:
                        if self.matcher.match_post(post):
                            posts.append(post)
                    else:
                        posts.append(post)

                # 避免请求过快
                await asyncio.sleep(random.uniform(1, 2))

            self.logger.info(f"Got {len(posts)} posts from {username}")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get user posts: {e}")
            return []

    async def get_post_detail(self, shortcode: str) -> Optional[InstagramPost]:
        """
        获取帖子详情

        Args:
            shortcode: 帖子短代码
        """
        try:
            self.logger.info(f"Getting post detail: {shortcode}")

            await self.anti_crawl.check_rate_limit()

            post_url = f"{self.base_url}/p/{shortcode}/"
            await self.navigate(post_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 从页面数据提取
            post_data = await self._page.evaluate("""
                () => {
                    const data = window._sharedData?.entry_data?.PostPage?.[0]?.graphql?.shortcode_media;
                    return data || null;
                }
            """)

            if post_data:
                return self._parse_post_data(post_data, shortcode)

            # 备用解析方法
            return await self._parse_post_from_page(shortcode)

        except Exception as e:
            self.logger.error(f"Failed to get post detail: {e}")
            return None

    def _parse_post_data(self, data: Dict[str, Any], shortcode: str) -> InstagramPost:
        """解析帖子数据"""
        # 提取媒体URL
        media_urls = []
        if data.get('__typename') == 'GraphSidecar':
            # 轮播帖子
            edges = data.get('edge_sidecar_to_children', {}).get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                if node.get('is_video'):
                    media_urls.append(node.get('video_url', ''))
                else:
                    media_urls.append(node.get('display_url', ''))
        else:
            # 单个媒体
            if data.get('is_video'):
                media_urls.append(data.get('video_url', ''))
            else:
                media_urls.append(data.get('display_url', ''))

        # 提取标题
        caption_edges = data.get('edge_media_to_caption', {}).get('edges', [])
        caption = caption_edges[0].get('node', {}).get('text', '') if caption_edges else ''

        # 提取标签和提及
        hashtags = re.findall(r'#(\w+)', caption)
        mentions = re.findall(r'@(\w+)', caption)

        # 媒体类型
        typename = data.get('__typename', '')
        if typename == 'GraphSidecar':
            media_type = MediaType.CAROUSEL
        elif typename == 'GraphVideo':
            media_type = MediaType.VIDEO
        else:
            media_type = MediaType.IMAGE

        # 位置信息
        location = None
        if data.get('location'):
            location = {
                'id': data['location'].get('id'),
                'name': data['location'].get('name'),
                'slug': data['location'].get('slug'),
            }

        return InstagramPost(
            id=data.get('id', ''),
            shortcode=shortcode,
            url=f"{self.base_url}/p/{shortcode}/",
            media_type=media_type,
            caption=caption,
            likes_count=data.get('edge_media_preview_like', {}).get('count', 0),
            comments_count=data.get('edge_media_to_parent_comment', {}).get('count', 0),
            timestamp=datetime.fromtimestamp(data.get('taken_at_timestamp', 0)),
            owner={
                'id': data.get('owner', {}).get('id'),
                'username': data.get('owner', {}).get('username'),
                'full_name': data.get('owner', {}).get('full_name', ''),
                'profile_pic_url': data.get('owner', {}).get('profile_pic_url', ''),
                'is_verified': data.get('owner', {}).get('is_verified', False),
            },
            media_urls=media_urls,
            hashtags=hashtags,
            mentions=mentions,
            location=location,
            is_video=data.get('is_video', False),
            video_duration=data.get('video_duration'),
        )

    async def _parse_post_from_page(self, shortcode: str) -> Optional[InstagramPost]:
        """从页面元素解析帖子"""
        try:
            # 作者
            author_elem = await self._page.query_selector('header a')
            author_username = await author_elem.inner_text() if author_elem else ''

            # 标题
            caption_elem = await self._page.query_selector('article h1 + span')
            caption = await caption_elem.inner_text() if caption_elem else ''

            # 点赞数
            likes_elem = await self._page.query_selector('section button span')
            likes_text = await likes_elem.inner_text() if likes_elem else '0'
            likes_count = self.parser.parse_count(likes_text)

            # 评论数(需要展开评论)
            comments_count = 0

            # 媒体URL
            media_urls = []
            img_elements = await self._page.query_selector_all('article img[src*="instagram"]')
            video_elements = await self._page.query_selector_all('article video')

            for img in img_elements:
                src = await img.get_attribute('src')
                if src and 'profile_pic' not in src:
                    media_urls.append(src)

            for video in video_elements:
                src = await video.get_attribute('src')
                if src:
                    media_urls.append(src)

            # 时间戳
            time_elem = await self._page.query_selector('time')
            timestamp = datetime.now()
            if time_elem:
                datetime_attr = await time_elem.get_attribute('datetime')
                if datetime_attr:
                    timestamp = self.parser.parse_date(datetime_attr)

            # 提取标签和提及
            hashtags = re.findall(r'#(\w+)', caption)
            mentions = re.findall(r'@(\w+)', caption)

            # 判断媒体类型
            media_type = MediaType.IMAGE
            if video_elements:
                media_type = MediaType.VIDEO
            elif len(media_urls) > 1:
                media_type = MediaType.CAROUSEL

            return InstagramPost(
                id=shortcode,
                shortcode=shortcode,
                url=f"{self.base_url}/p/{shortcode}/",
                media_type=media_type,
                caption=caption,
                likes_count=likes_count,
                comments_count=comments_count,
                timestamp=timestamp,
                owner={'username': author_username},
                media_urls=media_urls,
                hashtags=hashtags,
                mentions=mentions,
            )

        except Exception as e:
            self.logger.error(f"Failed to parse post from page: {e}")
            return None

    async def get_comments(
        self,
        shortcode: str,
        max_comments: int = 100
    ) -> List[InstagramComment]:
        """
        获取帖子评论

        Args:
            shortcode: 帖子短代码
            max_comments: 最大评论数
        """
        try:
            self.logger.info(f"Getting comments for post: {shortcode}")

            await self.anti_crawl.check_rate_limit()

            post_url = f"{self.base_url}/p/{shortcode}/"
            await self.navigate(post_url)
            await asyncio.sleep(random.uniform(2, 3))

            comments = []

            # 点击"查看更多评论"
            for _ in range(max_comments // 20):
                try:
                    load_more = await self._page.query_selector(
                        'button:has-text("Load more comments")',
                        timeout=2000
                    )
                    if load_more:
                        await load_more.click()
                        await asyncio.sleep(random.uniform(1, 2))
                    else:
                        break
                except:
                    break

            # 提取评论
            comment_elements = await self._page.query_selector_all('article ul ul li')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = await self._parse_comment_element(elem, shortcode)
                    if comment:
                        comments.append(comment)
                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []

    async def _parse_comment_element(
        self,
        elem: ElementHandle,
        post_id: str
    ) -> Optional[InstagramComment]:
        """解析评论元素"""
        try:
            # 作者
            author_elem = await elem.query_selector('a')
            author = {}
            if author_elem:
                author['username'] = await author_elem.inner_text()

            # 内容
            content_elem = await elem.query_selector('span')
            content = ''
            if content_elem:
                text = await content_elem.inner_text()
                # 移除用户名
                if author.get('username') and text.startswith(author['username']):
                    text = text[len(author['username']):].strip()
                content = text

            if not content:
                return None

            # 点赞数
            likes_elem = await elem.query_selector('button span')
            likes_count = 0
            if likes_elem:
                likes_text = await likes_elem.inner_text()
                likes_count = self.parser.parse_count(likes_text)

            # 时间
            time_elem = await elem.query_selector('time')
            created_at = datetime.now()
            if time_elem:
                datetime_attr = await time_elem.get_attribute('datetime')
                if datetime_attr:
                    created_at = self.parser.parse_date(datetime_attr)

            # 生成ID
            comment_id = hashlib.md5(
                f"{author.get('username', '')}{content}{post_id}".encode()
            ).hexdigest()[:16]

            return InstagramComment(
                id=comment_id,
                text=content,
                owner=author,
                created_at=created_at,
                likes_count=likes_count,
                post_id=post_id,
            )

        except Exception as e:
            self.logger.error(f"Failed to parse comment element: {e}")
            return None

    async def get_stories(self, username: str) -> List[Dict[str, Any]]:
        """
        获取用户Stories

        Args:
            username: 用户名
        """
        try:
            self.logger.info(f"Getting stories from: {username}")

            await self.anti_crawl.check_rate_limit()

            # 导航到主页
            await self.navigate(self.base_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 查找用户的Story圈
            story_elem = await self._page.query_selector(f'a[href*="/{username}"] canvas')
            if not story_elem:
                self.logger.info(f"No stories available for {username}")
                return []

            # 点击打开Story
            await story_elem.click()
            await asyncio.sleep(random.uniform(2, 3))

            stories = []
            max_stories = 50  # 限制最大数量

            for i in range(max_stories):
                try:
                    # 提取当前Story
                    story = await self._parse_current_story(username)
                    if story:
                        stories.append(story)

                    # 点击下一个
                    next_btn = await self._page.query_selector('button[aria-label="Next"]')
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(random.uniform(1, 2))
                    else:
                        break

                except:
                    break

            self.logger.info(f"Got {len(stories)} stories")
            return stories

        except Exception as e:
            self.logger.error(f"Failed to get stories: {e}")
            return []

    async def _parse_current_story(self, username: str) -> Optional[Dict[str, Any]]:
        """解析当前显示的Story"""
        try:
            story = {
                'platform': self.platform,
                'username': username,
                'type': 'story',
            }

            # 获取媒体
            img_elem = await self._page.query_selector('img[draggable="false"]')
            video_elem = await self._page.query_selector('video')

            if video_elem:
                story['media_type'] = 'video'
                story['media_url'] = await video_elem.get_attribute('src')
            elif img_elem:
                story['media_type'] = 'image'
                story['media_url'] = await img_elem.get_attribute('src')

            # 时间戳
            time_elem = await self._page.query_selector('time')
            if time_elem:
                datetime_attr = await time_elem.get_attribute('datetime')
                if datetime_attr:
                    story['created_at'] = self.parser.parse_date(datetime_attr)

            return story if story.get('media_url') else None

        except Exception as e:
            self.logger.error(f"Failed to parse story: {e}")
            return None

    async def get_reels(self, username: str, max_reels: int = 20) -> List[Dict[str, Any]]:
        """
        获取用户Reels

        Args:
            username: 用户名
            max_reels: 最大数量
        """
        try:
            self.logger.info(f"Getting reels from: {username}")

            await self.anti_crawl.check_rate_limit()

            # Instagram Reels通常在用户主页的Reels标签
            profile_url = f"{self.base_url}/{username}/reels/"
            await self.navigate(profile_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            reels_loaded = 0
            scroll_attempts = 0
            max_scrolls = max_reels // 12 + 2

            while reels_loaded < max_reels and scroll_attempts < max_scrolls:
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

                reel_elements = await self._page.query_selector_all('a[href*="/reel/"]')
                reels_loaded = len(reel_elements)
                scroll_attempts += 1

            # 提取Reels
            reels = []
            reel_elements = await self._page.query_selector_all('a[href*="/reel/"]')

            for elem in reel_elements[:max_reels]:
                try:
                    reel = await self._parse_reel_element(elem)
                    if reel:
                        reels.append(reel)
                except Exception as e:
                    self.logger.warning(f"Failed to parse reel: {e}")
                    continue

            self.logger.info(f"Got {len(reels)} reels")
            return reels

        except Exception as e:
            self.logger.error(f"Failed to get reels: {e}")
            return []

    async def _parse_reel_element(self, elem: ElementHandle) -> Optional[Dict[str, Any]]:
        """解析Reel元素"""
        try:
            reel = {'platform': self.platform, 'type': 'reel'}

            href = await elem.get_attribute('href')
            if href:
                reel['url'] = f"{self.base_url}{href}" if not href.startswith('http') else href
                match = re.search(r'/reel/([A-Za-z0-9_-]+)', href)
                if match:
                    reel['id'] = match.group(1)

            # 缩略图
            img = await elem.query_selector('img')
            if img:
                reel['thumbnail'] = await img.get_attribute('src')

            return reel if reel.get('id') else None

        except Exception as e:
            self.logger.error(f"Failed to parse reel element: {e}")
            return None

    async def download_media(
        self,
        media_urls: List[str],
        save_dir: Optional[Path] = None
    ) -> List[Path]:
        """
        批量下载媒体文件

        Args:
            media_urls: 媒体URL列表
            save_dir: 保存目录
        """
        try:
            save_dir = save_dir or self._download_dir
            downloaded_files = []

            for i, url in enumerate(media_urls):
                self.logger.info(f"Downloading media {i+1}/{len(media_urls)}")

                filepath = await super().download_media(url)
                if filepath:
                    downloaded_files.append(filepath)

                # 避免请求过快
                await asyncio.sleep(random.uniform(0.5, 1.5))

            self.logger.info(f"Downloaded {len(downloaded_files)}/{len(media_urls)} files")
            return downloaded_files

        except Exception as e:
            self.logger.error(f"Failed to download media: {e}")
            return []

    # ========================================================================
    # Graph API Methods
    # ========================================================================

    def set_graph_api_token(self, access_token: str):
        """设置Graph API访问令牌"""
        self._access_token = access_token
        self._graph_api_enabled = True
        self.logger.info("Graph API enabled")

    async def graph_api_get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """使用Graph API获取用户信息"""
        if not self._graph_api_enabled:
            self.logger.error("Graph API not enabled")
            return None

        try:
            url = f"{self.graph_api_url}/{user_id}"
            params = {
                'fields': 'id,username,name,biography,followers_count,follows_count,media_count',
                'access_token': self._access_token
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            self.logger.error(f"Graph API request failed: {e}")
            return None

    async def graph_api_get_media(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """使用Graph API获取用户媒体"""
        if not self._graph_api_enabled:
            self.logger.error("Graph API not enabled")
            return []

        try:
            url = f"{self.graph_api_url}/{user_id}/media"
            params = {
                'fields': 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count',
                'limit': limit,
                'access_token': self._access_token
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get('data', [])

        except Exception as e:
            self.logger.error(f"Graph API request failed: {e}")
            return []

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        stats = {
            'platform': self.platform,
            'logged_in': self._is_logged_in,
            'requests_made': self.anti_crawl._request_count,
            'failed_requests': self.anti_crawl._failed_requests,
            'downloaded_files': len(self._downloaded_urls),
        }

        if self.interaction:
            stats['interactions'] = self.interaction.get_interaction_stats()

        return stats
