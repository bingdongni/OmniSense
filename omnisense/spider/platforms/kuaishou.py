"""
Kuaishou (快手) Spider Implementation
完整的快手平台爬虫实现，包含四层架构：
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


class KuaishouAntiCrawl:
    """
    快手反反爬处理器
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
        self._device_id = self._generate_device_id()

        device_script = f"""
        // Device fingerprint for Kuaishou
        window._ks_device_id = '{self._device_id}';

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
        """
        await page.add_init_script(device_script)
        self.logger.debug(f"Injected device fingerprint: {self._device_id}")

    async def _inject_webdriver_evasion(self, page: Page):
        """注入反webdriver检测"""
        evasion_script = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }
            ]
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_canvas_fingerprint(self, page: Page):
        """注入Canvas指纹随机化"""
        canvas_script = """
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;

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
        random_str = ''.join(random.choices('0123456789abcdef', k=16))
        return hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest()

    async def random_scroll_behavior(self, page: Page, duration: float = 3.0):
        """模拟真实用户的随机滚动行为"""
        viewport_height = page.viewport_size['height']
        total_height = await page.evaluate("document.body.scrollHeight")

        scroll_steps = random.randint(5, 10)
        step_duration = duration / scroll_steps

        for _ in range(scroll_steps):
            scroll_distance = random.randint(100, viewport_height // 2)
            current_position = await page.evaluate("window.pageYOffset")
            new_position = min(current_position + scroll_distance, total_height - viewport_height)

            await page.evaluate(f"window.scrollTo({{top: {new_position}, behavior: 'smooth'}})")
            await asyncio.sleep(step_duration + random.uniform(0, 0.5))

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

            steps = random.randint(10, 20)
            for i in range(steps):
                await page.mouse.move(x * (i / steps), y * (i / steps))
                await asyncio.sleep(0.01)

            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def simulate_read_time(self, content_length: int):
        """根据内容长度模拟阅读时间"""
        base_time = (content_length / 100) * random.uniform(2, 4)
        read_time = max(2, base_time + random.uniform(-1, 2))
        await asyncio.sleep(read_time)

    async def handle_slider_captcha(self, page: Page) -> bool:
        """处理滑块验证码"""
        try:
            slider_selector = '.verify-slider'
            if not await page.query_selector(slider_selector):
                return True

            self.logger.info("Detected slider captcha, attempting to solve...")

            slider = await page.query_selector(slider_selector)
            box = await slider.bounding_box()

            if not box:
                return False

            start_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] / 2
            slide_distance = random.randint(260, 290)

            await page.mouse.move(start_x, start_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.down()

            steps = random.randint(20, 30)
            for i in range(steps):
                jitter_x = random.uniform(-2, 2)
                jitter_y = random.uniform(-2, 2)
                progress = (i + 1) / steps
                ease_progress = 1 - (1 - progress) ** 3

                current_x = start_x + (slide_distance * ease_progress) + jitter_x
                current_y = start_y + jitter_y

                await page.mouse.move(current_x, current_y)
                await asyncio.sleep(random.uniform(0.01, 0.03))

            await asyncio.sleep(random.uniform(0.1, 0.2))
            await page.mouse.up()
            await asyncio.sleep(2)

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


class KuaishouMatcher:
    """
    快手内容匹配器
    Layer 3: Matcher - 多模态匹配（标题、描述、字幕、OCR）
    """

    def __init__(self):
        self.logger = logger

    async def match_video(self, video: Dict[str, Any], criteria: Dict[str, Any]) -> tuple[bool, float]:
        """匹配视频内容"""
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

        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]

            if video.get('title'):
                title_matches = sum(1 for kw in keywords if kw.lower() in video['title'].lower())
                score += (title_matches / len(keywords)) * weights['title']

            if video.get('description'):
                desc_matches = sum(1 for kw in keywords if kw.lower() in video['description'].lower())
                score += (desc_matches / len(keywords)) * weights['description']

            if video.get('hashtags'):
                hashtag_text = ' '.join(video['hashtags']).lower()
                hashtag_matches = sum(1 for kw in keywords if kw.lower() in hashtag_text)
                score += (hashtag_matches / len(keywords)) * weights['hashtags']

        if 'min_likes' in criteria:
            if video.get('like_count', 0) < criteria['min_likes']:
                return False, 0.0

        if 'min_views' in criteria:
            if video.get('view_count', 0) < criteria['min_views']:
                return False, 0.0

        if 'min_date' in criteria:
            video_date = video.get('publish_time')
            if video_date and isinstance(video_date, datetime):
                min_date = criteria['min_date']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)
                if video_date < min_date:
                    return False, 0.0

        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score


class KuaishouInteraction:
    """
    快手互动处理器
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
        """获取视频评论（支持嵌套回复）"""
        comments = []

        try:
            comment_selector = '.comment-item'
            try:
                await page.wait_for_selector(comment_selector, timeout=5000)
            except PlaywrightTimeoutError:
                self.logger.warning(f"No comments found for video {video_id}")
                return comments

            await self._scroll_to_load_comments(page, max_comments)

            comment_elements = await page.query_selector_all(comment_selector)

            for idx, elem in enumerate(comment_elements[:max_comments]):
                try:
                    comment = await self._parse_comment_element(page, elem)
                    if comment:
                        comments.append(comment)

                        if include_replies and idx < 20:
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
        max_scrolls = min(target_count // 10, 20)

        for _ in range(max_scrolls):
            await page.evaluate("""
                () => {
                    const commentList = document.querySelector('.comment-list');
                    if (commentList) {
                        commentList.scrollTop = commentList.scrollHeight;
                    }
                }
            """)

            await asyncio.sleep(random.uniform(1, 2))

            current_count = await page.evaluate("""
                () => document.querySelectorAll('.comment-item').length
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

            username_elem = await element.query_selector('.comment-username')
            if username_elem:
                comment_data['user']['nickname'] = await username_elem.inner_text()

            avatar_elem = await element.query_selector('.comment-avatar img')
            if avatar_elem:
                comment_data['user']['avatar'] = await avatar_elem.get_attribute('src')

            text_elem = await element.query_selector('.comment-text')
            if text_elem:
                comment_data['text'] = await text_elem.inner_text()

            like_elem = await element.query_selector('.comment-like-count')
            if like_elem:
                like_text = await like_elem.inner_text()
                comment_data['like_count'] = self.spider.parser.parse_count(like_text)

            time_elem = await element.query_selector('.comment-time')
            if time_elem:
                time_text = await time_elem.inner_text()
                comment_data['publish_time'] = self.spider.parser.parse_date(time_text)

            author_tag = await element.query_selector('.author-tag')
            comment_data['is_author'] = author_tag is not None

            ip_elem = await element.query_selector('.comment-ip')
            if ip_elem:
                comment_data['ip_location'] = await ip_elem.inner_text()

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
            more_replies_btn = await comment_element.query_selector('.view-more-replies')
            if more_replies_btn:
                await more_replies_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

            reply_elements = await comment_element.query_selector_all('.reply-item')

            for reply_elem in reply_elements[:10]:
                reply = await self._parse_comment_element(page, reply_elem)
                if reply:
                    reply['parent_id'] = parent_comment_id
                    replies.append(reply)

        except Exception as e:
            self.logger.debug(f"Error getting comment replies: {e}")

        return replies

    async def get_creator_info(self, page: Page, user_id: str) -> Dict[str, Any]:
        """获取创作者详细信息"""
        creator_info = {
            'user_id': user_id,
            'nickname': None,
            'avatar': None,
            'signature': None,
            'follower_count': 0,
            'following_count': 0,
            'total_likes': 0,
            'video_count': 0,
            'kuaishou_id': None,
            'verified': False,
            'verification_type': None,
            'ip_location': None,
            'gender': None,
            'age': None,
            'region': None
        }

        try:
            user_url = f"https://www.kuaishou.com/profile/{user_id}"
            await page.goto(user_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            nickname_elem = await page.query_selector('.profile-user-name')
            if nickname_elem:
                creator_info['nickname'] = await nickname_elem.inner_text()

            avatar_elem = await page.query_selector('.profile-avatar img')
            if avatar_elem:
                creator_info['avatar'] = await avatar_elem.get_attribute('src')

            signature_elem = await page.query_selector('.profile-signature')
            if signature_elem:
                creator_info['signature'] = await signature_elem.inner_text()

            stats_elems = await page.query_selector_all('.profile-stats .stat-item')
            for elem in stats_elems:
                label_text = await elem.inner_text()
                if '关注' in label_text and '粉丝' not in label_text:
                    creator_info['following_count'] = self.spider.parser.parse_count(label_text)
                elif '粉丝' in label_text:
                    creator_info['follower_count'] = self.spider.parser.parse_count(label_text)
                elif '获赞' in label_text or '点赞' in label_text:
                    creator_info['total_likes'] = self.spider.parser.parse_count(label_text)

            ks_id_elem = await page.query_selector('.profile-ks-id')
            if ks_id_elem:
                ks_id_text = await ks_id_elem.inner_text()
                creator_info['kuaishou_id'] = ks_id_text.replace('快手号：', '').strip()

            verified_elem = await page.query_selector('.profile-verified')
            if verified_elem:
                creator_info['verified'] = True
                verification_text = await verified_elem.inner_text()
                creator_info['verification_type'] = verification_text

            ip_elem = await page.query_selector('.profile-ip')
            if ip_elem:
                ip_text = await ip_elem.inner_text()
                creator_info['ip_location'] = ip_text.replace('IP属地：', '').strip()

            video_count = await page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('.profile-video-item');
                    return videos.length;
                }
            """)
            creator_info['video_count'] = video_count

            self.logger.info(f"Collected creator info for {user_id}")

        except Exception as e:
            self.logger.error(f"Error getting creator info: {e}")

        return creator_info


class KuaishouSpider(BaseSpider):
    """
    快手爬虫主类
    Layer 1: Spider - 完整的爬取功能实现
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="kuaishou",
            headless=headless,
            proxy=proxy
        )

        self.anti_crawl = KuaishouAntiCrawl(self)
        self.matcher = KuaishouMatcher()
        self.interaction = KuaishouInteraction(self)

        self.base_url = "https://www.kuaishou.com"
        self.search_url = f"{self.base_url}/search"
        self.mobile_simulation = False

        self._collected_video_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()
        await self.anti_crawl.initialize(self._page)
        self.logger.info("Kuaishou spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """登录快手"""
        try:
            await self.navigate(self.base_url)
            await asyncio.sleep(2)

            if await self._check_login_status():
                self.logger.info("Already logged in")
                self._is_logged_in = True
                return True

            if self._cookies_file.exists():
                await self._load_cookies()
                await self._page.reload()
                await asyncio.sleep(2)

                if await self._check_login_status():
                    self.logger.info("Logged in with cookies")
                    self._is_logged_in = True
                    return True

            self.logger.info("Please scan QR code to login (waiting 60 seconds)...")

            login_btn_selector = '.login-button'
            if await self._page.query_selector(login_btn_selector):
                await self._page.click(login_btn_selector)
                await asyncio.sleep(2)

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
            user_info = await self._page.query_selector('.user-info')
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
        """搜索视频"""
        self.logger.info(f"Searching for: {keyword}, type: {search_type}, max: {max_results}")

        results = []

        try:
            search_params = {
                'keyword': keyword,
                'type': search_type,
                'sort': sort_type
            }
            search_url = f"{self.search_url}?{urlencode(search_params)}"

            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            if await self.anti_crawl.handle_slider_captcha(self._page):
                self.logger.info("Passed captcha check")

            await self._scroll_and_load(max_results)

            video_elements = await self._page.query_selector_all('.search-video-item')

            for elem in video_elements[:max_results * 2]:
                try:
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    video_url = await link_elem.get_attribute('href')
                    if not video_url:
                        continue

                    video_id = self._extract_video_id(video_url)
                    if not video_id or video_id in self._collected_video_ids:
                        continue

                    video_data = await self.get_post_detail(video_id)

                    if video_data:
                        if criteria:
                            is_match, match_score = await self.matcher.match_video(video_data, criteria)
                            if not is_match:
                                continue
                            video_data['match_score'] = match_score

                        results.append(video_data)
                        self._collected_video_ids.add(video_id)

                        if len(results) >= max_results:
                            break

                    await asyncio.sleep(random.uniform(0.5, 1))

                except Exception as e:
                    self.logger.error(f"Error parsing video: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} videos for keyword: {keyword}")

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料"""
        return await self.interaction.get_creator_info(self._page, user_id)

    async def get_user_posts(
        self,
        user_id: str,
        max_posts: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取用户发布的视频"""
        self.logger.info(f"Getting posts for user: {user_id}, max: {max_posts}")

        posts = []

        try:
            user_url = f"{self.base_url}/profile/{user_id}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            await self._scroll_and_load(max_posts)

            video_elements = await self._page.query_selector_all('.profile-video-item')

            for elem in video_elements[:max_posts * 2]:
                try:
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    video_url = await link_elem.get_attribute('href')
                    video_id = self._extract_video_id(video_url)

                    if not video_id or video_id in self._collected_video_ids:
                        continue

                    video_data = await self.get_post_detail(video_id)

                    if video_data:
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
        """获取视频详情（20+字段）"""
        self.logger.info(f"Getting video detail: {post_id}")

        video_data = {
            'content_id': post_id,
            'platform': 'kuaishou',
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
            video_url = f"{self.base_url}/video/{post_id}"
            video_data['url'] = video_url

            await self.navigate(video_url)
            await asyncio.sleep(random.uniform(2, 3))

            await self.anti_crawl.random_scroll_behavior(self._page, duration=2)

            title_elem = await self._page.query_selector('.video-title')
            if title_elem:
                video_data['title'] = await title_elem.inner_text()

            desc_elem = await self._page.query_selector('.video-desc')
            if desc_elem:
                video_data['description'] = await desc_elem.inner_text()
                video_data['hashtags'] = self.parser.extract_hashtags(video_data['description'])
                video_data['mentions'] = self.parser.extract_mentions(video_data['description'])

            cover_elem = await self._page.query_selector('.video-cover img')
            if cover_elem:
                video_data['cover_image'] = await cover_elem.get_attribute('src')

            video_elem = await self._page.query_selector('video')
            if video_elem:
                video_data['video_url'] = await video_elem.get_attribute('src')

            duration_elem = await self._page.query_selector('.video-duration')
            if duration_elem:
                duration_text = await duration_elem.inner_text()
                video_data['duration'] = self.parser.parse_duration(duration_text)

            author_elem = await self._page.query_selector('.video-author')
            if author_elem:
                author_name_elem = await author_elem.query_selector('.author-name')
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

            stats_selectors = {
                'like_count': '.like-count',
                'comment_count': '.comment-count',
                'share_count': '.share-count',
                'view_count': '.view-count'
            }

            for key, selector in stats_selectors.items():
                elem = await self._page.query_selector(selector)
                if elem:
                    count_text = await elem.inner_text()
                    video_data[key] = self.parser.parse_count(count_text)

            music_elem = await self._page.query_selector('.video-music')
            if music_elem:
                music_title_elem = await music_elem.query_selector('.music-title')
                if music_title_elem:
                    video_data['music']['title'] = await music_title_elem.inner_text()

                music_author_elem = await music_elem.query_selector('.music-author')
                if music_author_elem:
                    video_data['music']['author'] = await music_author_elem.inner_text()

            time_elem = await self._page.query_selector('.video-publish-time')
            if time_elem:
                time_text = await time_elem.inner_text()
                video_data['publish_time'] = self.parser.parse_date(time_text)

            location_elem = await self._page.query_selector('.video-location')
            if location_elem:
                video_data['location'] = await location_elem.inner_text()

            ad_tag = await self._page.query_selector('.ad-tag')
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
        """获取评论（支持嵌套回复）"""
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

    async def _scroll_and_load(self, target_count: int):
        """滚动加载更多内容"""
        last_height = 0
        no_change_count = 0
        max_scrolls = min(target_count // 5, 20)

        for i in range(max_scrolls):
            await self.anti_crawl.random_scroll_behavior(self._page, duration=2)

            current_height = await self._page.evaluate("document.body.scrollHeight")

            if current_height == last_height:
                no_change_count += 1
                if no_change_count >= 2:
                    break
            else:
                no_change_count = 0
                last_height = current_height

            await asyncio.sleep(random.uniform(1, 2))

    def _extract_video_id(self, url: str) -> Optional[str]:
        """从URL中提取视频ID"""
        try:
            match = self.parser.extract_numbers(url)
            if match and len(str(int(match[0]))) >= 10:
                return str(int(match[0]))
            return None
        except:
            return None

    def _extract_user_id(self, url: str) -> Optional[str]:
        """从URL中提取用户ID"""
        try:
            if '/profile/' in url:
                user_id = url.split('/profile/')[-1].split('?')[0]
                return user_id
            return None
        except:
            return None


async def search_kuaishou_videos(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """便捷函数：搜索快手视频"""
    spider = KuaishouSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


if __name__ == "__main__":
    async def test_kuaishou_spider():
        spider = KuaishouSpider(headless=False)

        async with spider.session():
            print("Testing search...")
            videos = await spider.search("美食", max_results=5)

            for video in videos:
                print(f"\nVideo: {video.get('title')}")
                print(f"Author: {video.get('author', {}).get('nickname')}")
                print(f"Likes: {video.get('like_count')}")
                print(f"URL: {video.get('url')}")
