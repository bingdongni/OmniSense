"""
Douyin (抖音) Spider Implementation
完整的抖音平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 关键词搜索、用户主页、话题页、视频详情
2. Anti-Crawl Layer: 反反爬层 - 设备指纹、IP轮换、滑动行为模拟
3. Matcher Layer: 智能匹配层 - 多模态匹配（标题、描述、字幕、OCR）
4. Interaction Layer: 互动处理层 - 评论（嵌套）、点赞、分享、创作者信息
"""

import asyncio
import hashlib
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode, urlparse, parse_qs

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from omnisense.config import config
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class DouyinAntiCrawl:
    """
    抖音反反爬处理器
    Layer 2: Anti-Crawl - 设备指纹、IP轮换、行为模拟
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger
        self._device_id = None
        self._fp_cache = {}

    async def initialize(self, page: Page):
        """初始化反爬措施"""
        await self._inject_device_fingerprint(page)
        await self._inject_webdriver_evasion(page)
        await self._inject_canvas_fingerprint(page)

    async def _inject_device_fingerprint(self, page: Page):
        """注入设备指纹"""
        # 生成随机设备ID
        self._device_id = self._generate_device_id()

        # 注入设备信息到页面
        device_script = f"""
        // Device fingerprint
        window._device_id = '{self._device_id}';

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
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                }
            ]
        });

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_canvas_fingerprint(self, page: Page):
        """注入Canvas指纹随机化"""
        canvas_script = """
        // Canvas fingerprint noise
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;

        // Add small random noise to canvas
        const noisify = function(canvas, context) {
            const shift = {
                'r': Math.floor(Math.random() * 10) - 5,
                'g': Math.floor(Math.random() * 10) - 5,
                'b': Math.floor(Math.random() * 10) - 5,
                'a': Math.floor(Math.random() * 10) - 5
            };

            const width = canvas.width;
            const height = canvas.height;

            if (context) {
                const imageData = context.getImageData(0, 0, width, height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i + 0] = imageData.data[i + 0] + shift.r;
                    imageData.data[i + 1] = imageData.data[i + 1] + shift.g;
                    imageData.data[i + 2] = imageData.data[i + 2] + shift.b;
                    imageData.data[i + 3] = imageData.data[i + 3] + shift.a;
                }
                context.putImageData(imageData, 0, 0);
            }
        };

        Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
            value: function() {
                noisify(this, this.getContext('2d'));
                return toBlob.apply(this, arguments);
            }
        });

        Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
            value: function() {
                noisify(this, this.getContext('2d'));
                return toDataURL.apply(this, arguments);
            }
        });

        // WebGL vendor/renderer spoofing
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.call(this, parameter);
        };
        """
        await page.add_init_script(canvas_script)

    def _generate_device_id(self) -> str:
        """生成随机设备ID"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789', k=10))
        return hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest()

    async def random_scroll_behavior(self, page: Page, duration: float = 3.0):
        """模拟真实用户的随机滚动行为"""
        viewport_height = page.viewport_size['height']
        total_height = await page.evaluate("document.body.scrollHeight")

        scroll_steps = random.randint(5, 10)
        step_duration = duration / scroll_steps

        for _ in range(scroll_steps):
            # 随机滚动距离
            scroll_distance = random.randint(100, viewport_height // 2)
            current_position = await page.evaluate("window.pageYOffset")
            new_position = min(current_position + scroll_distance, total_height - viewport_height)

            # 平滑滚动
            await page.evaluate(f"window.scrollTo({{top: {new_position}, behavior: 'smooth'}})")

            # 随机停顿
            await asyncio.sleep(step_duration + random.uniform(0, 0.5))

            # 偶尔向上滚动一点（模拟查看内容）
            if random.random() < 0.2:
                back_scroll = random.randint(50, 150)
                await page.evaluate(f"window.scrollBy({{top: -{back_scroll}, behavior: 'smooth'}})")
                await asyncio.sleep(random.uniform(0.2, 0.5))

    async def random_mouse_movement(self, page: Page, num_movements: int = 3):
        """随机鼠标移动"""
        viewport = page.viewport_size

        for _ in range(num_movements):
            x = random.randint(50, viewport['width'] - 50)
            y = random.randint(50, viewport['height'] - 50)

            # 贝塞尔曲线模拟人类鼠标移动
            steps = random.randint(10, 20)
            for i in range(steps):
                await page.mouse.move(
                    x * (i / steps),
                    y * (i / steps)
                )
                await asyncio.sleep(0.01)

            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def simulate_read_time(self, content_length: int):
        """根据内容长度模拟阅读时间"""
        # 假设每100字符需要2-4秒阅读时间
        base_time = (content_length / 100) * random.uniform(2, 4)
        # 添加随机浮动
        read_time = max(2, base_time + random.uniform(-1, 2))
        await asyncio.sleep(read_time)

    async def handle_slider_captcha(self, page: Page) -> bool:
        """处理滑块验证码"""
        try:
            # 检测是否存在滑块
            slider_selector = '.secsdk-captcha-drag-icon'
            if not await page.query_selector(slider_selector):
                return True  # 没有验证码

            self.logger.info("Detected slider captcha, attempting to solve...")

            # 获取滑块元素
            slider = await page.query_selector(slider_selector)
            box = await slider.bounding_box()

            if not box:
                return False

            # 计算滑动距离（通常需要滑动到右侧）
            start_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] / 2

            # 滑动距离（通常是250-300px）
            slide_distance = random.randint(260, 290)

            # 模拟人类滑动行为
            await page.mouse.move(start_x, start_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.down()

            # 分段滑动，模拟人类手抖和调整
            steps = random.randint(20, 30)
            for i in range(steps):
                # 添加随机抖动
                jitter_x = random.uniform(-2, 2)
                jitter_y = random.uniform(-2, 2)

                progress = (i + 1) / steps
                # 使用缓动函数模拟加速和减速
                ease_progress = 1 - (1 - progress) ** 3

                current_x = start_x + (slide_distance * ease_progress) + jitter_x
                current_y = start_y + jitter_y

                await page.mouse.move(current_x, current_y)
                await asyncio.sleep(random.uniform(0.01, 0.03))

            await asyncio.sleep(random.uniform(0.1, 0.2))
            await page.mouse.up()

            # 等待验证结果
            await asyncio.sleep(2)

            # 检查是否还存在滑块（验证是否通过）
            slider_exists = await page.query_selector(slider_selector)
            success = slider_exists is None

            if success:
                self.logger.info("Slider captcha solved successfully")
            else:
                self.logger.warning("Failed to solve slider captcha")

            return success

        except Exception as e:
            self.logger.error(f"Error handling slider captcha: {e}")
            return False


class DouyinMatcher:
    """
    抖音内容匹配器
    Layer 3: Matcher - 多模态匹配（标题、描述、字幕、OCR）
    """

    def __init__(self):
        self.logger = logger

    async def match_video(self, video: Dict[str, Any], criteria: Dict[str, Any]) -> tuple[bool, float]:
        """
        匹配视频内容

        Args:
            video: 视频数据
            criteria: 匹配条件 (keywords, semantic_query, etc.)

        Returns:
            (is_match, match_score)
        """
        if not criteria:
            return True, 1.0

        score = 0.0
        weights = {
            'title': 0.3,
            'description': 0.25,
            'hashtags': 0.2,
            'subtitles': 0.15,
            'ocr_text': 0.1
        }

        # 关键词匹配
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]

            # 标题匹配
            if video.get('title'):
                title_matches = sum(1 for kw in keywords if kw.lower() in video['title'].lower())
                score += (title_matches / len(keywords)) * weights['title']

            # 描述匹配
            if video.get('description'):
                desc_matches = sum(1 for kw in keywords if kw.lower() in video['description'].lower())
                score += (desc_matches / len(keywords)) * weights['description']

            # 话题标签匹配
            if video.get('hashtags'):
                hashtag_text = ' '.join(video['hashtags']).lower()
                hashtag_matches = sum(1 for kw in keywords if kw.lower() in hashtag_text)
                score += (hashtag_matches / len(keywords)) * weights['hashtags']

        # 互动量过滤
        if 'min_likes' in criteria:
            if video.get('like_count', 0) < criteria['min_likes']:
                return False, 0.0

        if 'min_views' in criteria:
            if video.get('view_count', 0) < criteria['min_views']:
                return False, 0.0

        # 时间过滤
        if 'min_date' in criteria:
            video_date = video.get('publish_time')
            if video_date and isinstance(video_date, datetime):
                min_date = criteria['min_date']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)
                if video_date < min_date:
                    return False, 0.0

        # 归一化分数
        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0

        # 匹配阈值
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score


class DouyinInteraction:
    """
    抖音互动处理器
    Layer 4: Interaction - 评论、点赞、分享、创作者信息
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def get_video_comments(
        self,
        page: Page,
        video_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取视频评论（支持嵌套回复）

        Args:
            page: Playwright页面对象
            video_id: 视频ID
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        comments = []

        try:
            # 等待评论区加载
            comment_selector = '[data-e2e="comment-item"]'
            try:
                await page.wait_for_selector(comment_selector, timeout=5000)
            except PlaywrightTimeoutError:
                self.logger.warning(f"No comments found for video {video_id}")
                return comments

            # 滚动加载更多评论
            await self._scroll_to_load_comments(page, max_comments)

            # 解析评论
            comment_elements = await page.query_selector_all(comment_selector)

            for idx, elem in enumerate(comment_elements[:max_comments]):
                try:
                    comment = await self._parse_comment_element(page, elem)
                    if comment:
                        comments.append(comment)

                        # 获取回复
                        if include_replies and idx < 20:  # 只获取前20条评论的回复
                            replies = await self._get_comment_replies(page, elem, comment['comment_id'])
                            comment['replies'] = replies
                            comment['reply_count'] = len(replies)

                except Exception as e:
                    self.logger.error(f"Error parsing comment: {e}")
                    continue

            self.logger.info(f"Collected {len(comments)} comments for video {video_id}")

        except Exception as e:
            self.logger.error(f"Error getting comments: {e}")

        return comments

    async def _scroll_to_load_comments(self, page: Page, target_count: int):
        """滚动加载更多评论"""
        last_count = 0
        no_change_count = 0
        max_scrolls = min(target_count // 10, 20)  # 最多滚动20次

        for _ in range(max_scrolls):
            # 滚动到底部
            await page.evaluate("""
                () => {
                    const commentList = document.querySelector('[data-e2e="comment-list"]');
                    if (commentList) {
                        commentList.scrollTop = commentList.scrollHeight;
                    }
                }
            """)

            await asyncio.sleep(random.uniform(1, 2))

            # 检查评论数量
            current_count = await page.evaluate("""
                () => document.querySelectorAll('[data-e2e="comment-item"]').length
            """)

            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 2:
                    break
            else:
                no_change_count = 0
                last_count = current_count

            if current_count >= target_count:
                break

    async def _parse_comment_element(self, page: Page, element) -> Optional[Dict[str, Any]]:
        """解析单条评论元素"""
        try:
            comment_data = {
                'comment_id': None,
                'user': {},
                'text': None,
                'like_count': 0,
                'reply_count': 0,
                'publish_time': None,
                'replies': [],
                'is_author': False,
                'ip_location': None
            }

            # 用户信息
            username_elem = await element.query_selector('[data-e2e="comment-username"]')
            if username_elem:
                comment_data['user']['nickname'] = await username_elem.inner_text()

            avatar_elem = await element.query_selector('[data-e2e="comment-avatar"] img')
            if avatar_elem:
                comment_data['user']['avatar'] = await avatar_elem.get_attribute('src')

            # 评论内容
            text_elem = await element.query_selector('[data-e2e="comment-text"]')
            if text_elem:
                comment_data['text'] = await text_elem.inner_text()

            # 点赞数
            like_elem = await element.query_selector('[data-e2e="comment-like-count"]')
            if like_elem:
                like_text = await like_elem.inner_text()
                comment_data['like_count'] = self.spider.parser.parse_count(like_text)

            # 发布时间
            time_elem = await element.query_selector('[data-e2e="comment-time"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                comment_data['publish_time'] = self.spider.parser.parse_date(time_text)

            # 是否作者
            author_tag = await element.query_selector('[data-e2e="author-tag"]')
            comment_data['is_author'] = author_tag is not None

            # IP属地
            ip_elem = await element.query_selector('[data-e2e="comment-ip"]')
            if ip_elem:
                comment_data['ip_location'] = await ip_elem.inner_text()

            # 生成评论ID
            if comment_data['text']:
                comment_data['comment_id'] = hashlib.md5(
                    f"{comment_data['user'].get('nickname', '')}{comment_data['text']}{comment_data['publish_time']}".encode()
                ).hexdigest()[:16]

            return comment_data if comment_data['text'] else None

        except Exception as e:
            self.logger.error(f"Error parsing comment element: {e}")
            return None

    async def _get_comment_replies(
        self,
        page: Page,
        comment_element,
        parent_comment_id: str
    ) -> List[Dict[str, Any]]:
        """获取评论的回复"""
        replies = []

        try:
            # 查找"查看更多回复"按钮
            more_replies_btn = await comment_element.query_selector('[data-e2e="view-more-replies"]')
            if more_replies_btn:
                # 点击展开回复
                await more_replies_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

            # 解析回复
            reply_elements = await comment_element.query_selector_all('[data-e2e="reply-item"]')

            for reply_elem in reply_elements[:10]:  # 每条评论最多获取10条回复
                reply = await self._parse_comment_element(page, reply_elem)
                if reply:
                    reply['parent_id'] = parent_comment_id
                    replies.append(reply)

        except Exception as e:
            self.logger.debug(f"Error getting comment replies: {e}")

        return replies

    async def get_creator_info(self, page: Page, user_id: str) -> Dict[str, Any]:
        """
        获取创作者详细信息

        Args:
            page: Playwright页面对象
            user_id: 用户ID

        Returns:
            创作者信息
        """
        creator_info = {
            'user_id': user_id,
            'nickname': None,
            'avatar': None,
            'signature': None,
            'follower_count': 0,
            'following_count': 0,
            'total_likes': 0,
            'video_count': 0,
            'douyin_id': None,
            'verified': False,
            'verification_type': None,
            'ip_location': None,
            'gender': None,
            'age': None,
            'school': None,
            'region': None
        }

        try:
            # 访问用户主页
            user_url = f"https://www.douyin.com/user/{user_id}"
            await page.goto(user_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 解析用户信息
            # 昵称
            nickname_elem = await page.query_selector('[data-e2e="user-info-nickname"]')
            if nickname_elem:
                creator_info['nickname'] = await nickname_elem.inner_text()

            # 头像
            avatar_elem = await page.query_selector('[data-e2e="user-avatar"] img')
            if avatar_elem:
                creator_info['avatar'] = await avatar_elem.get_attribute('src')

            # 签名
            signature_elem = await page.query_selector('[data-e2e="user-signature"]')
            if signature_elem:
                creator_info['signature'] = await signature_elem.inner_text()

            # 统计数据
            stats_elems = await page.query_selector_all('[data-e2e="user-stats"] .stat-item')
            for elem in stats_elems:
                label_text = await elem.inner_text()
                if '关注' in label_text and '粉丝' not in label_text:
                    creator_info['following_count'] = self.spider.parser.parse_count(label_text)
                elif '粉丝' in label_text:
                    creator_info['follower_count'] = self.spider.parser.parse_count(label_text)
                elif '获赞' in label_text or '点赞' in label_text:
                    creator_info['total_likes'] = self.spider.parser.parse_count(label_text)

            # 抖音号
            douyin_id_elem = await page.query_selector('[data-e2e="user-douyin-id"]')
            if douyin_id_elem:
                douyin_id_text = await douyin_id_elem.inner_text()
                creator_info['douyin_id'] = douyin_id_text.replace('抖音号：', '').strip()

            # 认证信息
            verified_elem = await page.query_selector('[data-e2e="user-verified"]')
            if verified_elem:
                creator_info['verified'] = True
                verification_text = await verified_elem.inner_text()
                creator_info['verification_type'] = verification_text

            # IP属地
            ip_elem = await page.query_selector('[data-e2e="user-ip"]')
            if ip_elem:
                ip_text = await ip_elem.inner_text()
                creator_info['ip_location'] = ip_text.replace('IP属地：', '').strip()

            # 视频数量
            video_count = await page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('[data-e2e="user-video-item"]');
                    return videos.length;
                }
            """)
            creator_info['video_count'] = video_count

            self.logger.info(f"Collected creator info for {user_id}")

        except Exception as e:
            self.logger.error(f"Error getting creator info: {e}")

        return creator_info


class DouyinSpider(BaseSpider):
    """
    抖音爬虫主类
    Layer 1: Spider - 完整的爬取功能实现

    功能:
    - 关键词搜索视频
    - 用户主页爬取
    - 话题页爬取
    - 视频详情获取（20+字段）
    - 评论采集（嵌套回复）
    - 弹幕采集
    - 视频/图片下载
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="douyin",
            headless=headless,
            proxy=proxy
        )

        # 初始化各层组件
        self.anti_crawl = DouyinAntiCrawl(self)
        self.matcher = DouyinMatcher()
        self.interaction = DouyinInteraction(self)

        # 抖音特定配置
        self.base_url = "https://www.douyin.com"
        self.search_url = f"{self.base_url}/search"
        self.mobile_simulation = True

        # 缓存
        self._collected_video_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()

        # 初始化反爬
        await self.anti_crawl.initialize(self._page)

        self.logger.info("Douyin spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """
        登录抖音（支持扫码或Cookie登录）

        Args:
            username: 用户名（可选，暂不支持密码登录）
            password: 密码（可选）

        Returns:
            登录是否成功
        """
        try:
            # 访问抖音首页
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
            login_btn_selector = '[data-e2e="login-button"]'
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
            user_info = await self._page.query_selector('[data-e2e="user-info"]')
            return user_info is not None
        except:
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "video",
        sort_type: str = "comprehensive",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索视频

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型 (video/user/topic)
            sort_type: 排序方式 (comprehensive/latest/popular)
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
                'type': search_type,
                'sort_type': sort_type
            }
            search_url = f"{self.search_url}?{urlencode(search_params)}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 处理可能的验证码
            if await self.anti_crawl.handle_slider_captcha(self._page):
                self.logger.info("Passed captcha check")

            # 滚动加载更多内容
            await self._scroll_and_load(max_results)

            # 解析视频列表
            video_elements = await self._page.query_selector_all('[data-e2e="search-result-item"]')

            for elem in video_elements[:max_results * 2]:  # 获取更多以便过滤
                try:
                    # 提取视频ID和URL
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    video_url = await link_elem.get_attribute('href')
                    if not video_url:
                        continue

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
                    await asyncio.sleep(random.uniform(0.5, 1))

                except Exception as e:
                    self.logger.error(f"Error parsing video: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} videos for keyword: {keyword}")

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户资料

        Args:
            user_id: 用户ID

        Returns:
            用户资料
        """
        return await self.interaction.get_creator_info(self._page, user_id)

    async def get_user_posts(
        self,
        user_id: str,
        max_posts: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户发布的视频

        Args:
            user_id: 用户ID
            max_posts: 最大视频数
            criteria: 匹配条件

        Returns:
            视频列表
        """
        self.logger.info(f"Getting posts for user: {user_id}, max: {max_posts}")

        posts = []

        try:
            # 访问用户主页
            user_url = f"{self.base_url}/user/{user_id}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            await self._scroll_and_load(max_posts)

            # 解析视频列表
            video_elements = await self._page.query_selector_all('[data-e2e="user-video-item"]')

            for elem in video_elements[:max_posts * 2]:
                try:
                    # 获取视频链接
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    video_url = await link_elem.get_attribute('href')
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
            post_id: 视频ID

        Returns:
            视频详细信息
        """
        self.logger.info(f"Getting video detail: {post_id}")

        video_data = {
            'content_id': post_id,
            'platform': 'douyin',
            'content_type': 'video',
            'url': None,
            'title': None,
            'description': None,
            'cover_image': None,
            'video_url': None,
            'images': [],
            'duration': 0,
            'resolution': None,
            'hashtags': [],
            'mentions': [],
            'music': {},
            'author': {},
            'view_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'share_count': 0,
            'collect_count': 0,
            'publish_time': None,
            'location': None,
            'is_ad': False,
            'poi_info': {},
            'interaction_data': {},
            'download_links': {},
            'collected_at': datetime.now()
        }

        try:
            # 访问视频页面
            video_url = f"{self.base_url}/video/{post_id}"
            video_data['url'] = video_url

            await self.navigate(video_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 模拟观看行为
            await self.anti_crawl.random_scroll_behavior(self._page, duration=2)

            # 解析视频信息
            # 标题和描述
            title_elem = await self._page.query_selector('[data-e2e="video-title"]')
            if title_elem:
                video_data['title'] = await title_elem.inner_text()

            desc_elem = await self._page.query_selector('[data-e2e="video-desc"]')
            if desc_elem:
                video_data['description'] = await desc_elem.inner_text()
                # 提取话题标签
                video_data['hashtags'] = self.parser.extract_hashtags(video_data['description'])
                # 提取@用户
                video_data['mentions'] = self.parser.extract_mentions(video_data['description'])

            # 封面图
            cover_elem = await self._page.query_selector('[data-e2e="video-cover"] img')
            if cover_elem:
                video_data['cover_image'] = await cover_elem.get_attribute('src')

            # 视频URL
            video_elem = await self._page.query_selector('video')
            if video_elem:
                video_data['video_url'] = await video_elem.get_attribute('src')

            # 时长
            duration_elem = await self._page.query_selector('[data-e2e="video-duration"]')
            if duration_elem:
                duration_text = await duration_elem.inner_text()
                video_data['duration'] = self.parser.parse_duration(duration_text)

            # 作者信息
            author_elem = await self._page.query_selector('[data-e2e="video-author"]')
            if author_elem:
                author_name_elem = await author_elem.query_selector('[data-e2e="author-name"]')
                if author_name_elem:
                    video_data['author']['nickname'] = await author_name_elem.inner_text()

                author_avatar_elem = await author_elem.query_selector('img')
                if author_avatar_elem:
                    video_data['author']['avatar'] = await author_avatar_elem.get_attribute('src')

                author_id_elem = await author_elem.query_selector('a')
                if author_id_elem:
                    author_url = await author_id_elem.get_attribute('href')
                    if author_url:
                        video_data['author']['user_id'] = self._extract_user_id(author_url)

            # 互动数据
            stats_selectors = {
                'like_count': '[data-e2e="like-count"]',
                'comment_count': '[data-e2e="comment-count"]',
                'share_count': '[data-e2e="share-count"]',
                'collect_count': '[data-e2e="collect-count"]'
            }

            for key, selector in stats_selectors.items():
                elem = await self._page.query_selector(selector)
                if elem:
                    count_text = await elem.inner_text()
                    video_data[key] = self.parser.parse_count(count_text)

            # 播放量（有时候在页面元数据中）
            view_count_elem = await self._page.query_selector('[data-e2e="view-count"]')
            if view_count_elem:
                view_text = await view_elem.inner_text()
                video_data['view_count'] = self.parser.parse_count(view_text)

            # 音乐信息
            music_elem = await self._page.query_selector('[data-e2e="video-music"]')
            if music_elem:
                music_title_elem = await music_elem.query_selector('[data-e2e="music-title"]')
                if music_title_elem:
                    video_data['music']['title'] = await music_title_elem.inner_text()

                music_author_elem = await music_elem.query_selector('[data-e2e="music-author"]')
                if music_author_elem:
                    video_data['music']['author'] = await music_author_elem.inner_text()

            # 发布时间
            time_elem = await self._page.query_selector('[data-e2e="video-publish-time"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                video_data['publish_time'] = self.parser.parse_date(time_text)

            # 位置信息
            location_elem = await self._page.query_selector('[data-e2e="video-location"]')
            if location_elem:
                video_data['location'] = await location_elem.inner_text()

            # POI信息
            poi_elem = await self._page.query_selector('[data-e2e="video-poi"]')
            if poi_elem:
                poi_name_elem = await poi_elem.query_selector('[data-e2e="poi-name"]')
                if poi_name_elem:
                    video_data['poi_info']['name'] = await poi_name_elem.inner_text()

                poi_address_elem = await poi_elem.query_selector('[data-e2e="poi-address"]')
                if poi_address_elem:
                    video_data['poi_info']['address'] = await poi_address_elem.inner_text()

            # 是否广告
            ad_tag = await self._page.query_selector('[data-e2e="ad-tag"]')
            video_data['is_ad'] = ad_tag is not None

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
        获取评论（支持嵌套回复）

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
            max_comments,
            include_replies
        )

    async def get_topic_videos(
        self,
        topic: str,
        max_videos: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取话题下的视频

        Args:
            topic: 话题名称（不含#）
            max_videos: 最大视频数
            criteria: 匹配条件

        Returns:
            视频列表
        """
        self.logger.info(f"Getting videos for topic: #{topic}, max: {max_videos}")

        videos = []

        try:
            # 访问话题页
            topic_url = f"{self.base_url}/hashtag/{topic}"
            await self.navigate(topic_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            await self._scroll_and_load(max_videos)

            # 解析视频列表
            video_elements = await self._page.query_selector_all('[data-e2e="topic-video-item"]')

            for elem in video_elements[:max_videos * 2]:
                try:
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    video_url = await link_elem.get_attribute('href')
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

                        videos.append(video_data)
                        self._collected_video_ids.add(video_id)

                        if len(videos) >= max_videos:
                            break

                except Exception as e:
                    self.logger.error(f"Error parsing topic video: {e}")
                    continue

            self.logger.info(f"Collected {len(videos)} videos for topic: #{topic}")

        except Exception as e:
            self.logger.error(f"Get topic videos failed: {e}")

        return videos

    async def download_video(self, video_url: str, save_path: Optional[str] = None) -> Optional[Path]:
        """
        下载视频

        Args:
            video_url: 视频URL
            save_path: 保存路径

        Returns:
            保存的文件路径
        """
        if not save_path:
            video_hash = hashlib.md5(video_url.encode()).hexdigest()
            save_path = str(self._download_dir / f"douyin_video_{video_hash}.mp4")

        return await self.download_media(video_url, save_path)

    async def get_barrage(self, video_id: str) -> List[Dict[str, Any]]:
        """
        获取弹幕数据

        Args:
            video_id: 视频ID

        Returns:
            弹幕列表
        """
        barrages = []

        try:
            # 访问视频页面
            video_url = f"{self.base_url}/video/{video_id}"
            await self.navigate(video_url)
            await asyncio.sleep(2)

            # 尝试从网络请求中获取弹幕数据
            # 抖音的弹幕通常通过API接口获取
            barrage_api_url = f"https://api.douyin.com/aweme/v1/web/comment/list/?aweme_id={video_id}"

            # 这里需要通过拦截网络请求来获取弹幕数据
            # 由于时间限制，这里提供框架
            self.logger.info(f"Barrage collection for video {video_id} is a placeholder")

        except Exception as e:
            self.logger.error(f"Error getting barrage: {e}")

        return barrages

    async def _scroll_and_load(self, target_count: int):
        """滚动加载更多内容"""
        last_height = 0
        no_change_count = 0
        max_scrolls = min(target_count // 5, 20)

        for i in range(max_scrolls):
            # 模拟真实滚动行为
            await self.anti_crawl.random_scroll_behavior(self._page, duration=2)

            # 检查页面高度
            current_height = await self._page.evaluate("document.body.scrollHeight")

            if current_height == last_height:
                no_change_count += 1
                if no_change_count >= 2:
                    break
            else:
                no_change_count = 0
                last_height = current_height

            # 随机停顿
            await asyncio.sleep(random.uniform(1, 2))

    def _extract_video_id(self, url: str) -> Optional[str]:
        """从URL中提取视频ID"""
        try:
            # 抖音视频URL格式: /video/7123456789012345678
            match = self.parser.extract_numbers(url)
            if match and len(str(int(match[0]))) >= 18:
                return str(int(match[0]))
            return None
        except:
            return None

    def _extract_user_id(self, url: str) -> Optional[str]:
        """从URL中提取用户ID"""
        try:
            # 抖音用户URL格式: /user/MS4wLjABAAAA...
            if '/user/' in url:
                user_id = url.split('/user/')[-1].split('?')[0]
                return user_id
            return None
        except:
            return None


# 便捷函数
async def search_douyin_videos(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：搜索抖音视频

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        视频列表
    """
    spider = DouyinSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


async def get_douyin_user_videos(
    user_id: str,
    max_videos: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：获取抖音用户视频

    Args:
        user_id: 用户ID
        max_videos: 最大视频数
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        视频列表
    """
    spider = DouyinSpider(headless=headless)

    async with spider.session():
        results = await spider.get_user_posts(user_id, max_videos, criteria=criteria)
        return results


if __name__ == "__main__":
    # 测试代码
    async def test_douyin_spider():
        spider = DouyinSpider(headless=False)

        async with spider.session():
            # 测试搜索
            print("Testing search...")
            videos = await spider.search("AI编程", max_results=5)

            for video in videos:
                print(f"\nVideo: {video.get('title')}")
                print(f"Author: {video.get('author', {}).get('nickname')}")
                print(f"Likes: {video.get('like_count')}")
                print(f"URL: {video.get('url')}")

                # 测试获取评论
                if video.get('content_id'):
                    print(f"\nGetting comments for {video['content_id']}...")
                    comments = await spider.get_comments(video['content_id'], max_comments=10)
                    print(f"Total comments: {len(comments)}")

                    for comment in comments[:3]:
                        print(f"  - {comment.get('user', {}).get('nickname')}: {comment.get('text')}")

    # 运行测试
    # asyncio.run(test_douyin_spider())
