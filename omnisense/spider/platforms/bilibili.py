"""
Bilibili (B站) Spider Implementation
完整的B站平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 视频搜索、UP主信息、视频详情、弹幕、评论、动态、直播
2. Anti-Crawl Layer: 反反爬层 - WBI签名、设备指纹、频率控制、风控检测
3. Matcher Layer: 智能匹配层 - 播放数、弹幕数、投币数、分区、UP主粉丝数、时长范围
4. Interaction Layer: 互动处理层 - 三连操作、评论发布、弹幕发送、关注UP主、分享
"""

import asyncio
import hashlib
import hmac
import json
import random
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from omnisense.config import config
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class BilibiliWbiSigner:
    """
    Bilibili WBI签名算法实现
    用于API请求的参数签名，防止爬虫
    """

    def __init__(self):
        self.logger = logger
        self._mixin_key_enc_tab = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
            27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
            37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
            22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
        ]
        self._img_key = None
        self._sub_key = None
        self._last_update = 0
        self._update_interval = 3600  # 1小时更新一次

    def get_mixin_key(self, orig: str) -> str:
        """
        获取混合密钥

        Args:
            orig: 原始密钥字符串

        Returns:
            混合后的密钥
        """
        return ''.join([orig[i] for i in self._mixin_key_enc_tab])[:32]

    async def update_wbi_keys(self, page: Page = None) -> Tuple[str, str]:
        """
        更新WBI密钥对

        Args:
            page: Playwright页面对象（用于获取最新密钥）

        Returns:
            (img_key, sub_key)
        """
        current_time = time.time()

        # 如果密钥还在有效期内，直接返回
        if self._img_key and self._sub_key and (current_time - self._last_update) < self._update_interval:
            return self._img_key, self._sub_key

        try:
            if page:
                # 从页面获取nav信息
                nav_data = await page.evaluate("""
                    async () => {
                        const response = await fetch('https://api.bilibili.com/x/web-interface/nav');
                        return await response.json();
                    }
                """)

                if nav_data and nav_data.get('code') == 0:
                    wbi_img = nav_data.get('data', {}).get('wbi_img', {})
                    img_url = wbi_img.get('img_url', '')
                    sub_url = wbi_img.get('sub_url', '')

                    # 从URL中提取密钥
                    self._img_key = img_url.split('/')[-1].split('.')[0] if img_url else None
                    self._sub_key = sub_url.split('/')[-1].split('.')[0] if sub_url else None
                    self._last_update = current_time

                    self.logger.debug(f"Updated WBI keys: img={self._img_key[:8]}..., sub={self._sub_key[:8]}...")

        except Exception as e:
            self.logger.warning(f"Failed to update WBI keys: {e}")

        # 如果获取失败，使用默认值
        if not self._img_key or not self._sub_key:
            self._img_key = "7cd084941338484aae1ad9425b84077c"
            self._sub_key = "4932caff0ff746eab6f01bf08b70ac45"
            self.logger.debug("Using default WBI keys")

        return self._img_key, self._sub_key

    def sign_params(self, params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
        """
        对参数进行WBI签名

        Args:
            params: 原始参数字典
            img_key: 图片密钥
            sub_key: 副密钥

        Returns:
            签名后的参数字典
        """
        # 获取混合密钥
        mixin_key = self.get_mixin_key(img_key + sub_key)

        # 添加当前时间戳
        params['wts'] = int(time.time())

        # 按键名排序
        sorted_params = sorted(params.items())

        # 构建查询字符串
        query_string = urllib.parse.urlencode(sorted_params)

        # 计算签名
        sign = hashlib.md5((query_string + mixin_key).encode()).hexdigest()

        # 添加签名到参数
        params['w_rid'] = sign

        return params

    async def sign_url(self, url: str, page: Page = None) -> str:
        """
        对URL进行WBI签名

        Args:
            url: 原始URL
            page: Playwright页面对象

        Returns:
            签名后的URL
        """
        # 解析URL
        parsed = urlparse(url)
        params = dict(parse_qs(parsed.query))

        # 展平参数（parse_qs返回的是列表）
        flat_params = {k: v[0] if isinstance(v, list) else v for k, v in params.items()}

        # 更新密钥
        img_key, sub_key = await self.update_wbi_keys(page)

        # 签名参数
        signed_params = self.sign_params(flat_params, img_key, sub_key)

        # 重建URL
        signed_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(signed_params)}"

        return signed_url


class BilibiliAntiCrawl:
    """
    Bilibili反反爬处理器
    Layer 2: Anti-Crawl - 设备指纹、WBI签名、频率控制、风控检测
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger
        self._device_id = None
        self._fp_cache = {}
        self._wbi_signer = BilibiliWbiSigner()
        self._request_history = []
        self._rate_limit = 30  # 每分钟最大请求数

    async def initialize(self, page: Page):
        """初始化反爬措施"""
        await self._inject_device_fingerprint(page)
        await self._inject_webdriver_evasion(page)
        await self._inject_bili_jct(page)
        await self._inject_api_interceptor(page)

    async def _inject_device_fingerprint(self, page: Page):
        """注入设备指纹"""
        # 生成随机设备ID
        self._device_id = self._generate_device_id()

        device_script = f"""
        // Bilibili device fingerprint
        window._device_id = '{self._device_id}';
        window._buvid = '{self._generate_buvid()}';

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
            get: () => 'Win32'
        }});

        // Override vendor
        Object.defineProperty(navigator, 'vendor', {{
            get: () => 'Google Inc.'
        }});

        // Override language
        Object.defineProperty(navigator, 'language', {{
            get: () => 'zh-CN'
        }});

        // Override languages
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        }});
        """
        await page.add_init_script(device_script)
        self.logger.debug(f"Injected Bilibili device fingerprint: {self._device_id}")

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

        // Plugins - Bilibili检测
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf", description: ""},
                    description: "Portable Document Format",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                },
                {
                    0: {type: "application/x-shockwave-flash", suffixes: "swf", description: "Shockwave Flash"},
                    description: "Shockwave Flash",
                    filename: "pepflashplayer.dll",
                    length: 1,
                    name: "Shockwave Flash"
                }
            ]
        });

        // MimeTypes
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => [
                {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                {type: "application/x-shockwave-flash", suffixes: "swf", description: "Shockwave Flash"}
            ]
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_bili_jct(self, page: Page):
        """注入Bilibili CSRF token (bili_jct)"""
        bili_jct_script = """
        // Bilibili CSRF token generator
        window._generateBiliJct = function() {
            const chars = '0123456789abcdef';
            let token = '';
            for (let i = 0; i < 32; i++) {
                token += chars[Math.floor(Math.random() * chars.length)];
            }
            return token;
        };

        // 自动设置到cookie
        if (!document.cookie.includes('bili_jct=')) {
            const jct = window._generateBiliJct();
            document.cookie = `bili_jct=${jct}; path=/; domain=.bilibili.com`;
        }
        """
        await page.add_init_script(bili_jct_script)

    async def _inject_api_interceptor(self, page: Page):
        """注入API拦截器，自动添加必要的headers"""
        interceptor_script = """
        // Intercept fetch requests
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            let [url, options] = args;

            // 如果是Bilibili API请求
            if (url.includes('api.bilibili.com')) {
                options = options || {};
                options.headers = options.headers || {};

                // 添加必要的headers
                options.headers['Referer'] = 'https://www.bilibili.com';
                options.headers['Origin'] = 'https://www.bilibili.com';

                // 从cookie中获取bili_jct
                const biliJct = document.cookie.match(/bili_jct=([^;]+)/)?.[1];
                if (biliJct) {
                    options.headers['X-CSRF-Token'] = biliJct;
                }
            }

            return originalFetch.apply(this, [url, options]);
        };

        // Intercept XHR requests
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url) {
            this._url = url;
            return originalOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function(data) {
            if (this._url && this._url.includes('api.bilibili.com')) {
                this.setRequestHeader('Referer', 'https://www.bilibili.com');
                this.setRequestHeader('Origin', 'https://www.bilibili.com');

                const biliJct = document.cookie.match(/bili_jct=([^;]+)/)?.[1];
                if (biliJct) {
                    this.setRequestHeader('X-CSRF-Token', biliJct);
                }
            }
            return originalSend.apply(this, arguments);
        };
        """
        await page.add_init_script(interceptor_script)

    def _generate_device_id(self) -> str:
        """生成随机设备ID"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789ABCDEF', k=16))
        return hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest().upper()

    def _generate_buvid(self) -> str:
        """生成Bilibili唯一设备标识符 (buvid)"""
        timestamp = int(time.time() * 1000)
        random_str = ''.join(random.choices('0123456789ABCDEF', k=8))
        buvid = f"XY{timestamp}{random_str}"
        return hashlib.md5(buvid.encode()).hexdigest().upper()[:16]

    async def check_rate_limit(self):
        """检查请求频率限制"""
        current_time = time.time()

        # 清理1分钟前的历史记录
        self._request_history = [t for t in self._request_history if current_time - t < 60]

        # 检查是否超过限制
        if len(self._request_history) >= self._rate_limit:
            wait_time = 60 - (current_time - self._request_history[0])
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time + random.uniform(1, 3))
                self._request_history = []

        # 记录本次请求
        self._request_history.append(current_time)

    async def random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """随机延迟"""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    async def sign_api_request(self, url: str, page: Page = None) -> str:
        """
        对API请求URL进行WBI签名

        Args:
            url: 原始API URL
            page: Playwright页面对象

        Returns:
            签名后的URL
        """
        return await self._wbi_signer.sign_url(url, page)

    async def detect_risk_control(self, page: Page) -> bool:
        """
        检测是否触发风控

        Returns:
            True表示需要处理风控，False表示正常
        """
        try:
            # 检查是否有验证码
            captcha_selectors = [
                '.geetest_radar_tip',
                '.geetest_panel',
                '[class*="captcha"]',
                '[class*="verify"]'
            ]

            for selector in captcha_selectors:
                if await page.query_selector(selector):
                    self.logger.warning("Risk control detected: CAPTCHA found")
                    return True

            # 检查是否有封禁提示
            ban_text = await page.evaluate("""
                () => {
                    const body = document.body.innerText;
                    return body.includes('访问被拒绝') ||
                           body.includes('操作频繁') ||
                           body.includes('请稍后再试');
                }
            """)

            if ban_text:
                self.logger.warning("Risk control detected: Rate limit or ban")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error detecting risk control: {e}")
            return False

    async def handle_risk_control(self, page: Page) -> bool:
        """
        处理风控

        Returns:
            True表示处理成功，False表示处理失败
        """
        try:
            self.logger.info("Attempting to handle risk control...")

            # 等待一段时间
            await asyncio.sleep(random.uniform(5, 10))

            # 尝试刷新页面
            await page.reload()
            await asyncio.sleep(random.uniform(2, 4))

            # 重新检测
            if not await self.detect_risk_control(page):
                self.logger.info("Risk control handled successfully")
                return True

            # 如果还有风控，需要更长的等待时间
            self.logger.warning("Risk control still present, need manual intervention or longer wait")
            return False

        except Exception as e:
            self.logger.error(f"Error handling risk control: {e}")
            return False


class BilibiliMatcher:
    """
    Bilibili内容匹配器
    Layer 3: Matcher - 播放数、弹幕数、投币数、分区、UP主、时长
    """

    def __init__(self):
        self.logger = logger

    async def match_video(self, video: Dict[str, Any], criteria: Dict[str, Any]) -> Tuple[bool, float]:
        """
        匹配视频内容

        Args:
            video: 视频数据
            criteria: 匹配条件

        Returns:
            (is_match, match_score)
        """
        if not criteria:
            return True, 1.0

        score = 0.0
        weights = {
            'keyword': 0.25,
            'stats': 0.30,
            'partition': 0.15,
            'uploader': 0.15,
            'duration': 0.10,
            'date': 0.05
        }

        # 关键词匹配
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]

            title_match = 0
            desc_match = 0

            if video.get('title'):
                title_match = sum(1 for kw in keywords if kw.lower() in video['title'].lower())

            if video.get('description'):
                desc_match = sum(1 for kw in keywords if kw.lower() in video['description'].lower())

            keyword_score = (title_match * 0.7 + desc_match * 0.3) / len(keywords)
            score += keyword_score * weights['keyword']

        # 播放数过滤
        if 'min_views' in criteria:
            if video.get('view_count', 0) < criteria['min_views']:
                return False, 0.0

        if 'max_views' in criteria:
            if video.get('view_count', 0) > criteria['max_views']:
                return False, 0.0

        # 弹幕数过滤
        if 'min_danmaku' in criteria:
            if video.get('danmaku_count', 0) < criteria['min_danmaku']:
                return False, 0.0

        # 投币数过滤
        if 'min_coins' in criteria:
            if video.get('coin_count', 0) < criteria['min_coins']:
                return False, 0.0

        # 收藏数过滤
        if 'min_favorites' in criteria:
            if video.get('favorite_count', 0) < criteria['min_favorites']:
                return False, 0.0

        # 点赞数过滤
        if 'min_likes' in criteria:
            if video.get('like_count', 0) < criteria['min_likes']:
                return False, 0.0

        # 统计数据评分
        stats_score = self._evaluate_video_stats(video, criteria)
        score += stats_score * weights['stats']

        # 分区过滤
        if 'partitions' in criteria:
            partitions = criteria['partitions']
            if isinstance(partitions, str):
                partitions = [partitions]

            video_partition = video.get('partition', '')
            if video_partition and any(p.lower() in video_partition.lower() for p in partitions):
                score += 1.0 * weights['partition']
            elif video_partition:
                return False, 0.0

        # UP主粉丝数过滤
        if 'min_uploader_followers' in criteria:
            uploader_followers = video.get('uploader', {}).get('follower_count', 0)
            if uploader_followers < criteria['min_uploader_followers']:
                return False, 0.0

        # UP主匹配
        if 'uploader_keywords' in criteria:
            uploader_keywords = criteria['uploader_keywords']
            if isinstance(uploader_keywords, str):
                uploader_keywords = [uploader_keywords]

            uploader_name = video.get('uploader', {}).get('name', '')
            if uploader_name:
                uploader_match = sum(1 for kw in uploader_keywords if kw.lower() in uploader_name.lower())
                score += (uploader_match / len(uploader_keywords)) * weights['uploader']

        # 视频时长范围
        if 'min_duration' in criteria:
            if video.get('duration', 0) < criteria['min_duration']:
                return False, 0.0

        if 'max_duration' in criteria:
            if video.get('duration', 0) > criteria['max_duration']:
                return False, 0.0

        duration_score = self._evaluate_duration(video, criteria)
        score += duration_score * weights['duration']

        # 发布时间范围
        if 'min_date' in criteria:
            video_date = video.get('publish_time')
            if video_date and isinstance(video_date, datetime):
                min_date = criteria['min_date']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)
                if video_date < min_date:
                    return False, 0.0

        if 'max_date' in criteria:
            video_date = video.get('publish_time')
            if video_date and isinstance(video_date, datetime):
                max_date = criteria['max_date']
                if isinstance(max_date, str):
                    max_date = datetime.fromisoformat(max_date)
                if video_date > max_date:
                    return False, 0.0

        # 归一化分数
        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0

        # 匹配阈值
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score

    def _evaluate_video_stats(self, video: Dict[str, Any], criteria: Dict[str, Any]) -> float:
        """评估视频统计数据质量"""
        view_count = video.get('view_count', 0)
        like_count = video.get('like_count', 0)
        coin_count = video.get('coin_count', 0)
        favorite_count = video.get('favorite_count', 0)
        danmaku_count = video.get('danmaku_count', 0)

        if view_count == 0:
            return 0.0

        # 计算互动率
        engagement_rate = (like_count + coin_count * 2 + favorite_count + danmaku_count * 0.5) / view_count

        # 归一化（通常优质视频的互动率在0.05-0.3之间）
        normalized_engagement = min(engagement_rate / 0.3, 1.0)

        return normalized_engagement

    def _evaluate_duration(self, video: Dict[str, Any], criteria: Dict[str, Any]) -> float:
        """评估视频时长"""
        duration = video.get('duration', 0)

        if duration == 0:
            return 0.5

        # 根据时长评分（通常3-15分钟的视频更受欢迎）
        if 180 <= duration <= 900:  # 3-15分钟
            return 1.0
        elif 60 <= duration <= 1800:  # 1-30分钟
            return 0.8
        elif duration < 60:  # 小于1分钟
            return 0.4
        else:  # 超过30分钟
            return 0.6


class BilibiliInteraction:
    """
    Bilibili互动处理器
    Layer 4: Interaction - 三连操作、评论发布、弹幕发送、关注UP主
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def get_video_comments(
        self,
        page: Page,
        video_id: str,
        oid: str = None,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取视频评论（支持楼中楼）

        Args:
            page: Playwright页面对象
            video_id: 视频ID (BV号或AV号)
            oid: 视频的oid（aid），如果为None则从页面提取
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        comments = []

        try:
            # 如果没有提供oid，需要先获取
            if not oid:
                oid = await self._get_video_oid(page, video_id)

            if not oid:
                self.logger.warning(f"Failed to get oid for video {video_id}")
                return comments

            # 使用API获取评论
            comment_api = f"https://api.bilibili.com/x/v2/reply/main?type=1&oid={oid}&mode=3&next=0"

            # 对URL进行签名
            signed_url = await self.spider.anti_crawl.sign_api_request(comment_api, page)

            # 发送API请求
            response_data = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{signed_url}', {{
                        headers: {{
                            'Referer': 'https://www.bilibili.com',
                            'User-Agent': navigator.userAgent
                        }}
                    }});
                    return await response.json();
                }}
            """)

            if response_data and response_data.get('code') == 0:
                replies = response_data.get('data', {}).get('replies', [])

                for reply in replies[:max_comments]:
                    comment = self._parse_comment_data(reply)
                    if comment:
                        comments.append(comment)

                        # 获取楼中楼回复
                        if include_replies and reply.get('replies'):
                            for sub_reply in reply['replies'][:10]:
                                sub_comment = self._parse_comment_data(sub_reply)
                                if sub_comment:
                                    sub_comment['parent_id'] = comment['comment_id']
                                    comment.setdefault('replies', []).append(sub_comment)

            self.logger.info(f"Collected {len(comments)} comments for video {video_id}")

        except Exception as e:
            self.logger.error(f"Error getting comments: {e}")

        return comments

    async def _get_video_oid(self, page: Page, video_id: str) -> Optional[str]:
        """获取视频的oid (aid)"""
        try:
            # 从页面的__INITIAL_STATE__获取
            oid = await page.evaluate("""
                () => {
                    if (window.__INITIAL_STATE__) {
                        return window.__INITIAL_STATE__.aid ||
                               window.__INITIAL_STATE__.videoData?.aid;
                    }
                    return null;
                }
            """)

            return str(oid) if oid else None

        except Exception as e:
            self.logger.error(f"Error getting video oid: {e}")
            return None

    def _parse_comment_data(self, reply_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析评论数据"""
        try:
            comment = {
                'comment_id': str(reply_data.get('rpid', '')),
                'user': {
                    'mid': str(reply_data.get('mid', '')),
                    'nickname': reply_data.get('member', {}).get('uname', ''),
                    'avatar': reply_data.get('member', {}).get('avatar', ''),
                    'level': reply_data.get('member', {}).get('level_info', {}).get('current_level', 0),
                    'vip_type': reply_data.get('member', {}).get('vip', {}).get('vipType', 0)
                },
                'text': reply_data.get('content', {}).get('message', ''),
                'like_count': reply_data.get('like', 0),
                'reply_count': reply_data.get('rcount', 0),
                'publish_time': datetime.fromtimestamp(reply_data.get('ctime', 0)),
                'ip_location': reply_data.get('reply_control', {}).get('location', ''),
                'replies': []
            }

            return comment if comment['text'] else None

        except Exception as e:
            self.logger.error(f"Error parsing comment data: {e}")
            return None

    async def get_video_danmaku(
        self,
        page: Page,
        video_id: str,
        cid: str = None,
        max_danmaku: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        获取视频弹幕

        Args:
            page: Playwright页面对象
            video_id: 视频ID
            cid: 视频分P的cid，如果为None则获取第一P
            max_danmaku: 最大弹幕数

        Returns:
            弹幕列表
        """
        danmaku_list = []

        try:
            # 如果没有提供cid，需要先获取
            if not cid:
                cid = await self._get_video_cid(page, video_id)

            if not cid:
                self.logger.warning(f"Failed to get cid for video {video_id}")
                return danmaku_list

            # 使用API获取弹幕
            danmaku_api = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"

            # 发送API请求（弹幕API返回的是XML格式）
            response_text = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{danmaku_api}', {{
                        headers: {{
                            'Referer': 'https://www.bilibili.com',
                            'User-Agent': navigator.userAgent
                        }}
                    }});
                    return await response.text();
                }}
            """)

            # 解析XML弹幕数据（简化版）
            if response_text and '<d p=' in response_text:
                import re

                danmaku_pattern = r'<d p="([^"]+)">([^<]+)</d>'
                matches = re.findall(danmaku_pattern, response_text)

                for idx, (params, text) in enumerate(matches[:max_danmaku]):
                    try:
                        param_list = params.split(',')
                        danmaku = {
                            'danmaku_id': f"{cid}_{idx}",
                            'text': text,
                            'time': float(param_list[0]) if len(param_list) > 0 else 0,  # 出现时间（秒）
                            'mode': int(param_list[1]) if len(param_list) > 1 else 1,  # 弹幕模式
                            'font_size': int(param_list[2]) if len(param_list) > 2 else 25,
                            'color': int(param_list[3]) if len(param_list) > 3 else 16777215,  # 颜色
                            'timestamp': int(param_list[4]) if len(param_list) > 4 else 0,  # 发送时间戳
                            'pool': int(param_list[5]) if len(param_list) > 5 else 0,
                            'user_hash': param_list[6] if len(param_list) > 6 else '',
                            'rowid': int(param_list[7]) if len(param_list) > 7 else 0
                        }
                        danmaku_list.append(danmaku)

                    except Exception as e:
                        self.logger.warning(f"Error parsing danmaku: {e}")
                        continue

            self.logger.info(f"Collected {len(danmaku_list)} danmaku for video {video_id}")

        except Exception as e:
            self.logger.error(f"Error getting danmaku: {e}")

        return danmaku_list

    async def _get_video_cid(self, page: Page, video_id: str) -> Optional[str]:
        """获取视频的cid"""
        try:
            # 从页面的__INITIAL_STATE__获取
            cid = await page.evaluate("""
                () => {
                    if (window.__INITIAL_STATE__) {
                        return window.__INITIAL_STATE__.cid ||
                               window.__INITIAL_STATE__.videoData?.cid ||
                               window.__INITIAL_STATE__.videoData?.pages?.[0]?.cid;
                    }
                    return null;
                }
            """)

            return str(cid) if cid else None

        except Exception as e:
            self.logger.error(f"Error getting video cid: {e}")
            return None

    async def get_uploader_info(self, page: Page, mid: str) -> Dict[str, Any]:
        """
        获取UP主详细信息

        Args:
            page: Playwright页面对象
            mid: UP主的mid

        Returns:
            UP主信息
        """
        uploader_info = {
            'mid': mid,
            'name': None,
            'avatar': None,
            'sign': None,
            'level': 0,
            'follower_count': 0,
            'following_count': 0,
            'video_count': 0,
            'total_views': 0,
            'total_likes': 0,
            'vip_type': 0,
            'official_verify': {},
            'is_followed': False,
            'live_room': {}
        }

        try:
            # 访问UP主空间
            space_url = f"https://space.bilibili.com/{mid}"
            await page.goto(space_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 使用API获取UP主信息
            user_api = f"https://api.bilibili.com/x/space/acc/info?mid={mid}"
            signed_url = await self.spider.anti_crawl.sign_api_request(user_api, page)

            user_data = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{signed_url}', {{
                        headers: {{
                            'Referer': 'https://www.bilibili.com',
                            'User-Agent': navigator.userAgent
                        }}
                    }});
                    return await response.json();
                }}
            """)

            if user_data and user_data.get('code') == 0:
                data = user_data.get('data', {})

                uploader_info['name'] = data.get('name')
                uploader_info['avatar'] = data.get('face')
                uploader_info['sign'] = data.get('sign')
                uploader_info['level'] = data.get('level', 0)
                uploader_info['vip_type'] = data.get('vip', {}).get('type', 0)

                # 认证信息
                official = data.get('official', {})
                uploader_info['official_verify'] = {
                    'type': official.get('type', -1),
                    'desc': official.get('desc', '')
                }

            # 获取统计数据
            stat_api = f"https://api.bilibili.com/x/relation/stat?vmid={mid}"
            signed_stat_url = await self.spider.anti_crawl.sign_api_request(stat_api, page)

            stat_data = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{signed_stat_url}', {{
                        headers: {{
                            'Referer': 'https://www.bilibili.com',
                            'User-Agent': navigator.userAgent
                        }}
                    }});
                    return await response.json();
                }}
            """)

            if stat_data and stat_data.get('code') == 0:
                data = stat_data.get('data', {})
                uploader_info['follower_count'] = data.get('follower', 0)
                uploader_info['following_count'] = data.get('following', 0)

            # 获取视频数据统计
            upstat_api = f"https://api.bilibili.com/x/space/upstat?mid={mid}"
            signed_upstat_url = await self.spider.anti_crawl.sign_api_request(upstat_api, page)

            upstat_data = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{signed_upstat_url}', {{
                        headers: {{
                            'Referer': 'https://www.bilibili.com',
                            'User-Agent': navigator.userAgent
                        }}
                    }});
                    return await response.json();
                }}
            """)

            if upstat_data and upstat_data.get('code') == 0:
                data = upstat_data.get('data', {})
                uploader_info['total_views'] = data.get('archive', {}).get('view', 0)
                uploader_info['video_count'] = data.get('archive', {}).get('vv', 0)
                uploader_info['total_likes'] = data.get('likes', 0)

            self.logger.info(f"Collected uploader info for mid={mid}")

        except Exception as e:
            self.logger.error(f"Error getting uploader info: {e}")

        return uploader_info

    async def triple_action(
        self,
        page: Page,
        video_id: str,
        like: bool = True,
        coin: bool = True,
        favorite: bool = True
    ) -> Dict[str, bool]:
        """
        执行三连操作（点赞、投币、收藏）

        Args:
            page: Playwright页面对象
            video_id: 视频ID
            like: 是否点赞
            coin: 是否投币
            favorite: 是否收藏

        Returns:
            操作结果字典
        """
        results = {
            'like': False,
            'coin': False,
            'favorite': False
        }

        try:
            # 确保在视频页面
            if video_id not in page.url:
                video_url = f"https://www.bilibili.com/video/{video_id}"
                await page.goto(video_url)
                await asyncio.sleep(2)

            # 点赞
            if like:
                try:
                    like_btn = await page.query_selector('.video-like, [class*="like"]')
                    if like_btn:
                        await like_btn.click()
                        await asyncio.sleep(random.uniform(0.5, 1))
                        results['like'] = True
                        self.logger.info(f"Liked video {video_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to like: {e}")

            # 投币
            if coin:
                try:
                    coin_btn = await page.query_selector('.video-coin, [class*="coin"]')
                    if coin_btn:
                        await coin_btn.click()
                        await asyncio.sleep(random.uniform(0.5, 1))

                        # 选择投币数量（默认1个）
                        coin_one_btn = await page.query_selector('.bi-coin-1, [data-coin="1"]')
                        if coin_one_btn:
                            await coin_one_btn.click()
                            await asyncio.sleep(random.uniform(0.5, 1))

                        # 确认投币
                        confirm_btn = await page.query_selector('.confirm, [class*="confirm"]')
                        if confirm_btn:
                            await confirm_btn.click()
                            await asyncio.sleep(random.uniform(0.5, 1))
                            results['coin'] = True
                            self.logger.info(f"Coined video {video_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to coin: {e}")

            # 收藏
            if favorite:
                try:
                    fav_btn = await page.query_selector('.video-fav, [class*="collect"]')
                    if fav_btn:
                        await fav_btn.click()
                        await asyncio.sleep(random.uniform(0.5, 1))

                        # 选择默认收藏夹
                        default_fav = await page.query_selector('.fav-item:first-child, [class*="fav-item"]:first-child')
                        if default_fav:
                            await default_fav.click()
                            await asyncio.sleep(random.uniform(0.5, 1))
                            results['favorite'] = True
                            self.logger.info(f"Favorited video {video_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to favorite: {e}")

        except Exception as e:
            self.logger.error(f"Error performing triple action: {e}")

        return results

    async def post_comment(
        self,
        page: Page,
        video_id: str,
        content: str,
        reply_to: str = None
    ) -> bool:
        """
        发布评论

        Args:
            page: Playwright页面对象
            video_id: 视频ID
            content: 评论内容
            reply_to: 回复的评论ID（可选）

        Returns:
            是否成功发布
        """
        try:
            # 确保在视频页面
            if video_id not in page.url:
                video_url = f"https://www.bilibili.com/video/{video_id}"
                await page.goto(video_url)
                await asyncio.sleep(2)

            # 找到评论输入框
            comment_input = await page.query_selector('.comment-input, [class*="comment"] textarea')
            if not comment_input:
                self.logger.warning("Comment input not found")
                return False

            # 输入评论内容
            await comment_input.click()
            await asyncio.sleep(random.uniform(0.5, 1))
            await comment_input.type(content, delay=random.randint(50, 150))
            await asyncio.sleep(random.uniform(1, 2))

            # 点击发布按钮
            submit_btn = await page.query_selector('.comment-submit, [class*="submit"]')
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(random.uniform(1, 2))

                self.logger.info(f"Posted comment on video {video_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error posting comment: {e}")
            return False

    async def send_danmaku(
        self,
        page: Page,
        video_id: str,
        content: str,
        time_point: float = None
    ) -> bool:
        """
        发送弹幕

        Args:
            page: Playwright页面对象
            video_id: 视频ID
            content: 弹幕内容
            time_point: 发送弹幕的时间点（秒），None表示当前播放位置

        Returns:
            是否成功发送
        """
        try:
            # 确保在视频页面
            if video_id not in page.url:
                video_url = f"https://www.bilibili.com/video/{video_id}"
                await page.goto(video_url)
                await asyncio.sleep(2)

            # 如果指定了时间点，跳转到该位置
            if time_point is not None:
                await page.evaluate(f"""
                    () => {{
                        const video = document.querySelector('video');
                        if (video) {{
                            video.currentTime = {time_point};
                        }}
                    }}
                """)
                await asyncio.sleep(1)

            # 找到弹幕输入框
            danmaku_input = await page.query_selector('.bilibili-player-video-danmaku-input')
            if not danmaku_input:
                self.logger.warning("Danmaku input not found")
                return False

            # 输入弹幕内容
            await danmaku_input.click()
            await asyncio.sleep(random.uniform(0.3, 0.7))
            await danmaku_input.type(content, delay=random.randint(50, 100))
            await asyncio.sleep(random.uniform(0.5, 1))

            # 按Enter发送
            await danmaku_input.press('Enter')
            await asyncio.sleep(random.uniform(0.5, 1))

            self.logger.info(f"Sent danmaku on video {video_id}: {content}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending danmaku: {e}")
            return False

    async def follow_uploader(self, page: Page, mid: str) -> bool:
        """
        关注UP主

        Args:
            page: Playwright页面对象
            mid: UP主的mid

        Returns:
            是否成功关注
        """
        try:
            # 访问UP主空间
            space_url = f"https://space.bilibili.com/{mid}"
            await page.goto(space_url)
            await asyncio.sleep(random.uniform(1, 2))

            # 找到关注按钮
            follow_btn = await page.query_selector('.follow-btn, [class*="follow"]')
            if not follow_btn:
                self.logger.warning("Follow button not found")
                return False

            # 检查是否已关注
            is_followed = await follow_btn.evaluate("""
                (btn) => {
                    const text = btn.innerText || btn.textContent;
                    return text.includes('已关注') || text.includes('取消关注');
                }
            """)

            if is_followed:
                self.logger.info(f"Already followed uploader {mid}")
                return True

            # 点击关注
            await follow_btn.click()
            await asyncio.sleep(random.uniform(1, 2))

            self.logger.info(f"Followed uploader {mid}")
            return True

        except Exception as e:
            self.logger.error(f"Error following uploader: {e}")
            return False


class BilibiliSpider(BaseSpider):
    """
    Bilibili爬虫主类
    Layer 1: Spider - 完整的爬取功能实现

    功能:
    - 视频搜索（关键词、分区、排序）
    - UP主信息获取
    - 视频详情（20+字段）
    - 评论采集（楼中楼）
    - 弹幕抓取
    - 动态获取
    - 直播信息
    - 支持API和网页双模式
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="bilibili",
            headless=headless,
            proxy=proxy
        )

        # 初始化各层组件
        self.anti_crawl = BilibiliAntiCrawl(self)
        self.matcher = BilibiliMatcher()
        self.interaction = BilibiliInteraction(self)

        # Bilibili特定配置
        self.base_url = "https://www.bilibili.com"
        self.api_base_url = "https://api.bilibili.com"
        self.search_url = f"{self.base_url}/search"

        # 缓存
        self._collected_video_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()

        # 初始化反爬
        await self.anti_crawl.initialize(self._page)

        self.logger.info("Bilibili spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """
        登录Bilibili（支持扫码或Cookie登录）

        Args:
            username: 用户名（可选）
            password: 密码（可选）

        Returns:
            登录是否成功
        """
        try:
            # 访问B站首页
            await self.navigate(self.base_url)
            await asyncio.sleep(2)

            # 检查是否已登录
            if await self._check_login_status():
                self.logger.info("Already logged in")
                self._is_logged_in = True
                return True

            # 如果有保存的Cookie，尝试加载
            if self._cookies_file.exists():
                await self._load_cookies()
                await self._page.reload()
                await asyncio.sleep(2)

                if await self._check_login_status():
                    self.logger.info("Logged in with cookies")
                    self._is_logged_in = True
                    return True

            # 等待用户扫码登录
            self.logger.info("Please scan QR code to login (waiting 60 seconds)...")

            # 点击登录按钮
            login_btn_selector = '.header-login-entry'
            if await self._page.query_selector(login_btn_selector):
                await self._page.click(login_btn_selector)
                await asyncio.sleep(2)

            # 等待登录完成
            for _ in range(60):
                if await self._check_login_status():
                    self.logger.info("Login successful")
                    self._is_logged_in = True
                    await self._save_cookies()
                    return True
                await asyncio.sleep(1)

            self.logger.warning("Login timeout, continuing without login")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def _check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 检查页面中是否存在用户信息元素
            user_info = await self._page.query_selector('.header-avatar-wrap, .user-con')
            return user_info is not None
        except:
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "video",
        order: str = "totalrank",
        duration: int = 0,
        partition: str = None,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索视频

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型 (video/bangumi/pgc/live/article/topic/user)
            order: 排序方式 (totalrank综合/click播放/pubdate发布时间/dm弹幕/stow收藏)
            duration: 时长过滤 (0全部/1-10分钟以下/2-10-30分钟/3-30-60分钟/4-60分钟以上)
            partition: 分区ID
            criteria: 匹配条件

        Returns:
            视频列表
        """
        self.logger.info(f"Searching for: {keyword}, type: {search_type}, max: {max_results}")

        results = []

        try:
            # 构建搜索URL
            search_params = {
                'keyword': keyword,
                'search_type': search_type,
                'order': order
            }

            if duration > 0:
                search_params['duration'] = duration

            if partition:
                search_params['tids'] = partition

            search_url = f"{self.search_url}?{urlencode(search_params)}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 检查频率限制
            await self.anti_crawl.check_rate_limit()

            # 检查风控
            if await self.anti_crawl.detect_risk_control(self._page):
                await self.anti_crawl.handle_risk_control(self._page)

            # 滚动加载更多内容
            await self._scroll_and_load(max_results)

            # 解析视频列表
            video_elements = await self._page.query_selector_all('.video-item, .bili-video-card')

            for elem in video_elements[:max_results * 2]:
                try:
                    # 提取视频链接
                    link_elem = await elem.query_selector('a[href*="/video/"]')
                    if not link_elem:
                        continue

                    video_url = await link_elem.get_attribute('href')
                    if not video_url:
                        continue

                    # 补全URL
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url

                    video_id = self._extract_video_id(video_url)
                    if not video_id or video_id in self._collected_video_ids:
                        continue

                    # 获取视频详情
                    video_data = await self.get_post_detail(video_id)

                    if video_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_video(video_data, criteria)
                            if not is_match:
                                continue
                            video_data['match_score'] = match_score

                        results.append(video_data)
                        self._collected_video_ids.add(video_id)

                        if len(results) >= max_results:
                            break

                    # 随机延迟
                    await self.anti_crawl.random_delay(0.5, 1.5)

                except Exception as e:
                    self.logger.error(f"Error parsing video: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} videos for keyword: {keyword}")

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def search_by_partition(
        self,
        partition: str,
        max_results: int = 20,
        order: str = "click",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        按分区搜索视频

        Args:
            partition: 分区名称或ID
            max_results: 最大结果数
            order: 排序方式
            criteria: 匹配条件

        Returns:
            视频列表
        """
        self.logger.info(f"Searching partition: {partition}, max: {max_results}")

        # 分区ID映射
        partition_map = {
            '动画': 1, '番剧': 13, '国创': 167, '音乐': 3, '舞蹈': 129,
            '游戏': 4, '知识': 36, '科技': 188, '运动': 234, '汽车': 223,
            '生活': 160, '美食': 211, '动物': 217, '鬼畜': 119, '时尚': 155,
            '娱乐': 5, '影视': 181, '纪录片': 177, '电影': 23, '电视剧': 11
        }

        # 获取分区ID
        tid = partition_map.get(partition, partition)

        # 使用分区搜索
        return await self.search('', max_results=max_results, order=order, partition=str(tid), criteria=criteria)

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户资料（UP主信息）

        Args:
            user_id: 用户ID (mid)

        Returns:
            用户资料
        """
        return await self.interaction.get_uploader_info(self._page, user_id)

    async def get_user_posts(
        self,
        user_id: str,
        max_posts: int = 20,
        order: str = "pubdate",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户发布的视频

        Args:
            user_id: 用户ID (mid)
            max_posts: 最大视频数
            order: 排序方式 (pubdate发布时间/click播放量)
            criteria: 匹配条件

        Returns:
            视频列表
        """
        self.logger.info(f"Getting posts for user: {user_id}, max: {max_posts}")

        posts = []

        try:
            # 访问用户空间
            space_url = f"https://space.bilibili.com/{user_id}/video?order={order}"
            await self.navigate(space_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            await self._scroll_and_load(max_posts)

            # 解析视频列表
            video_elements = await self._page.query_selector_all('.small-item, .list-item')

            for elem in video_elements[:max_posts * 2]:
                try:
                    # 获取视频链接
                    link_elem = await elem.query_selector('a[href*="/video/"]')
                    if not link_elem:
                        continue

                    video_url = await link_elem.get_attribute('href')
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url

                    video_id = self._extract_video_id(video_url)

                    if not video_id or video_id in self._collected_video_ids:
                        continue

                    # 获取视频详情
                    video_data = await self.get_post_detail(video_id)

                    if video_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_video(video_data, criteria)
                            if not is_match:
                                continue
                            video_data['match_score'] = match_score

                        posts.append(video_data)
                        self._collected_video_ids.add(video_id)

                        if len(posts) >= max_posts:
                            break

                    await self.anti_crawl.random_delay(0.5, 1)

                except Exception as e:
                    self.logger.error(f"Error parsing user video: {e}")
                    continue

            self.logger.info(f"Collected {len(posts)} posts for user: {user_id}")

        except Exception as e:
            self.logger.error(f"Get user posts failed: {e}")

        return posts

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        获取视频详情（20+字段）

        Args:
            post_id: 视频ID (BV号或AV号)

        Returns:
            视频详细信息
        """
        self.logger.info(f"Getting video detail: {post_id}")

        video_data = {
            'content_id': post_id,
            'platform': 'bilibili',
            'content_type': 'video',
            'url': None,
            'title': None,
            'description': None,
            'cover': None,
            'duration': 0,
            'partition': None,
            'tags': [],
            'uploader': {},
            'view_count': 0,
            'danmaku_count': 0,
            'like_count': 0,
            'coin_count': 0,
            'favorite_count': 0,
            'share_count': 0,
            'reply_count': 0,
            'publish_time': None,
            'cid': None,
            'aid': None,
            'bvid': None,
            'pages': [],
            'staff': [],
            'stat': {},
            'collected_at': datetime.now()
        }

        try:
            # 访问视频页面
            video_url = f"{self.base_url}/video/{post_id}"
            video_data['url'] = video_url

            await self.navigate(video_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 检查风控
            if await self.anti_crawl.detect_risk_control(self._page):
                await self.anti_crawl.handle_risk_control(self._page)

            # 从页面的__INITIAL_STATE__获取数据
            initial_state = await self._page.evaluate("""
                () => {
                    return window.__INITIAL_STATE__ || {};
                }
            """)

            if initial_state:
                # 视频数据
                video_info = initial_state.get('videoData', {})

                video_data['title'] = video_info.get('title')
                video_data['description'] = video_info.get('desc')
                video_data['cover'] = video_info.get('pic')
                video_data['duration'] = video_info.get('duration', 0)
                video_data['cid'] = video_info.get('cid')
                video_data['aid'] = video_info.get('aid')
                video_data['bvid'] = video_info.get('bvid')

                # 分区信息
                video_data['partition'] = video_info.get('tname')

                # 标签
                tags = video_info.get('tag', '').split(',')
                video_data['tags'] = [tag.strip() for tag in tags if tag.strip()]

                # UP主信息
                owner = video_info.get('owner', {})
                video_data['uploader'] = {
                    'mid': str(owner.get('mid', '')),
                    'name': owner.get('name'),
                    'avatar': owner.get('face')
                }

                # 统计数据
                stat = video_info.get('stat', {})
                video_data['view_count'] = stat.get('view', 0)
                video_data['danmaku_count'] = stat.get('danmaku', 0)
                video_data['like_count'] = stat.get('like', 0)
                video_data['coin_count'] = stat.get('coin', 0)
                video_data['favorite_count'] = stat.get('favorite', 0)
                video_data['share_count'] = stat.get('share', 0)
                video_data['reply_count'] = stat.get('reply', 0)
                video_data['stat'] = stat

                # 发布时间
                pubdate = video_info.get('pubdate')
                if pubdate:
                    video_data['publish_time'] = datetime.fromtimestamp(pubdate)

                # 分P信息
                pages = video_info.get('pages', [])
                video_data['pages'] = pages

                # 联合投稿
                staff = video_info.get('staff', [])
                video_data['staff'] = staff

            self.logger.info(f"Collected video detail: {post_id}")

        except Exception as e:
            self.logger.error(f"Error getting video detail: {e}")

        return video_data

    async def get_comments(
        self,
        post_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取评论（支持楼中楼）

        Args:
            post_id: 视频ID
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        # 确保在视频页面
        video_url = f"{self.base_url}/video/{post_id}"
        current_url = self._page.url

        if post_id not in current_url:
            await self.navigate(video_url)
            await asyncio.sleep(2)

        return await self.interaction.get_video_comments(
            self._page,
            post_id,
            max_comments=max_comments,
            include_replies=include_replies
        )

    async def get_danmaku(
        self,
        post_id: str,
        max_danmaku: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        获取弹幕

        Args:
            post_id: 视频ID
            max_danmaku: 最大弹幕数

        Returns:
            弹幕列表
        """
        # 确保在视频页面
        video_url = f"{self.base_url}/video/{post_id}"
        current_url = self._page.url

        if post_id not in current_url:
            await self.navigate(video_url)
            await asyncio.sleep(2)

        return await self.interaction.get_video_danmaku(
            self._page,
            post_id,
            max_danmaku=max_danmaku
        )

    async def get_user_dynamics(
        self,
        user_id: str,
        max_dynamics: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户动态

        Args:
            user_id: 用户ID (mid)
            max_dynamics: 最大动态数

        Returns:
            动态列表
        """
        dynamics = []

        try:
            # 访问用户动态页
            dynamic_url = f"https://space.bilibili.com/{user_id}/dynamic"
            await self.navigate(dynamic_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            for _ in range(max_dynamics // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            # 解析动态列表
            dynamic_elements = await self._page.query_selector_all('.card, .bili-dyn-item')

            for elem in dynamic_elements[:max_dynamics]:
                try:
                    dynamic = {
                        'user_id': user_id,
                        'platform': 'bilibili'
                    }

                    # 动态内容
                    content_elem = await elem.query_selector('.content, .bili-dyn-content')
                    if content_elem:
                        dynamic['content'] = await content_elem.inner_text()

                    # 发布时间
                    time_elem = await elem.query_selector('.time, .bili-dyn-time')
                    if time_elem:
                        time_text = await time_elem.inner_text()
                        dynamic['publish_time'] = self.parser.parse_date(time_text)

                    # 互动数据
                    like_elem = await elem.query_selector('[class*="like"]')
                    if like_elem:
                        like_text = await like_elem.inner_text()
                        dynamic['like_count'] = self.parser.parse_count(like_text)

                    if dynamic.get('content'):
                        dynamics.append(dynamic)

                except Exception as e:
                    self.logger.warning(f"Error parsing dynamic: {e}")
                    continue

            self.logger.info(f"Collected {len(dynamics)} dynamics for user {user_id}")

        except Exception as e:
            self.logger.error(f"Error getting dynamics: {e}")

        return dynamics

    async def get_live_room_info(self, room_id: str) -> Dict[str, Any]:
        """
        获取直播间信息

        Args:
            room_id: 直播间ID

        Returns:
            直播间信息
        """
        live_info = {
            'room_id': room_id,
            'platform': 'bilibili',
            'title': None,
            'cover': None,
            'status': 0,  # 0未开播 1直播中
            'online': 0,
            'area': None,
            'uploader': {}
        }

        try:
            # 访问直播间
            live_url = f"https://live.bilibili.com/{room_id}"
            await self.navigate(live_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 从页面提取信息
            initial_state = await self._page.evaluate("""
                () => {
                    return window.__NEPTUNE_IS_MY_WAIFU__?.roomInfoRes?.data || {};
                }
            """)

            if initial_state:
                room_info = initial_state.get('room_info', {})
                anchor_info = initial_state.get('anchor_info', {})

                live_info['title'] = room_info.get('title')
                live_info['cover'] = room_info.get('cover')
                live_info['status'] = room_info.get('live_status', 0)
                live_info['online'] = room_info.get('online', 0)
                live_info['area'] = room_info.get('area_name')

                # UP主信息
                base_info = anchor_info.get('base_info', {})
                live_info['uploader'] = {
                    'mid': str(base_info.get('uid', '')),
                    'name': base_info.get('uname'),
                    'avatar': base_info.get('face')
                }

            self.logger.info(f"Collected live room info: {room_id}")

        except Exception as e:
            self.logger.error(f"Error getting live room info: {e}")

        return live_info

    async def _scroll_and_load(self, target_count: int):
        """滚动加载更多内容"""
        last_height = 0
        no_change_count = 0
        max_scrolls = min(target_count // 5, 20)

        for i in range(max_scrolls):
            # 滚动
            await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(random.uniform(1, 2))

            # 检查页面高度
            current_height = await self._page.evaluate("document.body.scrollHeight")

            if current_height == last_height:
                no_change_count += 1
                if no_change_count >= 2:
                    break
            else:
                no_change_count = 0
                last_height = current_height

    def _extract_video_id(self, url: str) -> Optional[str]:
        """从URL中提取视频ID"""
        try:
            # Bilibili视频URL格式: /video/BV1xx411c7mD 或 /video/av123456
            if '/video/' in url:
                video_id = url.split('/video/')[-1].split('?')[0].split('/')[0]
                return video_id
            return None
        except:
            return None


# 便捷函数
async def search_bilibili_videos(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：搜索B站视频

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        视频列表
    """
    spider = BilibiliSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


async def get_bilibili_user_videos(
    user_id: str,
    max_videos: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：获取B站UP主视频

    Args:
        user_id: 用户ID (mid)
        max_videos: 最大视频数
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        视频列表
    """
    spider = BilibiliSpider(headless=headless)

    async with spider.session():
        results = await spider.get_user_posts(user_id, max_videos, criteria=criteria)
        return results


if __name__ == "__main__":
    # 测试代码
    async def test_bilibili_spider():
        spider = BilibiliSpider(headless=False)

        async with spider.session():
            # 测试搜索
            print("Testing search...")
            videos = await spider.search("编程", max_results=5)

            for video in videos:
                print(f"\nVideo: {video.get('title')}")
                print(f"UP主: {video.get('uploader', {}).get('name')}")
                print(f"播放: {video.get('view_count')}")
                print(f"弹幕: {video.get('danmaku_count')}")
                print(f"点赞: {video.get('like_count')}")
                print(f"投币: {video.get('coin_count')}")
                print(f"URL: {video.get('url')}")

                # 测试获取评论
                if video.get('content_id'):
                    print(f"\nGetting comments for {video['content_id']}...")
                    comments = await spider.get_comments(video['content_id'], max_comments=10)
                    print(f"Total comments: {len(comments)}")

                    for comment in comments[:3]:
                        print(f"  - {comment.get('user', {}).get('nickname')}: {comment.get('text')}")

                # 测试获取弹幕
                if video.get('content_id'):
                    print(f"\nGetting danmaku for {video['content_id']}...")
                    danmaku = await spider.get_danmaku(video['content_id'], max_danmaku=20)
                    print(f"Total danmaku: {len(danmaku)}")

                    for dm in danmaku[:5]:
                        print(f"  - [{dm.get('time')}s] {dm.get('text')}")

    # 运行测试
    # asyncio.run(test_bilibili_spider())
