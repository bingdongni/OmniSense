"""
TikTok (国际版抖音) Spider Implementation
完整的TikTok平台爬虫实现，包含四层架构：
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


class TikTokAntiCrawl:
    """TikTok反反爬处理器"""

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
        await self._inject_tiktok_specific(page)

    async def _inject_device_fingerprint(self, page: Page):
        """注入设备指纹"""
        self._device_id = self._generate_device_id()

        device_script = f"""
        window._tt_device_id = '{self._device_id}';
        window.byted_acrawler = {{
            init: function() {{}},
            sign: function(data) {{ return data; }}
        }};

        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {random.choice([4, 8, 16])}
        }});

        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.choice([4, 8, 12, 16])}
        }});

        Object.defineProperty(navigator, 'platform', {{
            get: () => 'Win32'
        }});
        """
        await page.add_init_script(device_script)
        self.logger.debug(f"Injected TikTok device fingerprint: {self._device_id}")

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
            get: () => [1, 2, 3, 4, 5]
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'zh-CN', 'zh']
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_canvas_fingerprint(self, page: Page):
        """注入Canvas指纹随机化"""
        canvas_script = """
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

        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {
            const ctx = this.getContext('2d');
            if (ctx) {
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] += Math.floor(Math.random() * 5) - 2;
                }
                ctx.putImageData(imageData, 0, 0);
            }
            return toDataURL.apply(this, arguments);
        };
        """
        await page.add_init_script(canvas_script)

    async def _inject_tiktok_specific(self, page: Page):
        """注入TikTok特定脚本"""
        tiktok_script = """
        // TikTok specific overrides
        window.__NEXT_DATA__ = window.__NEXT_DATA__ || {};
        window.TikTokAppContext = window.TikTokAppContext || {};
        """
        await page.add_init_script(tiktok_script)

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
            scroll_distance = random.randint(100, viewport_height // 2)
            current_position = await page.evaluate("window.pageYOffset")
            new_position = min(current_position + scroll_distance, total_height - viewport_height)

            await page.evaluate(f"window.scrollTo({{top: {new_position}, behavior: 'smooth'}})")
            await asyncio.sleep(step_duration + random.uniform(0, 0.5))

            if random.random() < 0.2:
                back_scroll = random.randint(50, 150)
                await page.evaluate(f"window.scrollBy({{top: -{back_scroll}, behavior: 'smooth'}})")
                await asyncio.sleep(random.uniform(0.2, 0.5))

    async def handle_slider_captcha(self, page: Page) -> bool:
        """处理滑块验证码"""
        try:
            slider_selector = '.secsdk-captcha-drag-icon'
            if not await page.query_selector(slider_selector):
                return True

            self.logger.info("Detected TikTok slider captcha, attempting to solve...")

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
            return slider_exists is None

        except Exception as e:
            self.logger.error(f"Error handling slider captcha: {e}")
            return False


class TikTokMatcher:
    """TikTok内容匹配器"""

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

        if 'min_likes' in criteria and video.get('like_count', 0) < criteria['min_likes']:
            return False, 0.0

        if 'min_views' in criteria and video.get('view_count', 0) < criteria['min_views']:
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


class TikTokInteraction:
    """TikTok互动处理器"""

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
        """获取视频评论"""
        comments = []

        try:
            comment_selector = '[data-e2e="comment-item"]'
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
                    const commentList = document.querySelector('[data-e2e="comment-list"]');
                    if (commentList) {
                        commentList.scrollTop = commentList.scrollHeight;
                    }
                }
            """)

            await asyncio.sleep(random.uniform(1, 2))

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
                'is_author': False
            }

            username_elem = await element.query_selector('[data-e2e="comment-username"]')
            if username_elem:
                comment_data['user']['nickname'] = await username_elem.inner_text()

            avatar_elem = await element.query_selector('[data-e2e="comment-avatar"] img')
            if avatar_elem:
                comment_data['user']['avatar'] = await avatar_elem.get_attribute('src')

            text_elem = await element.query_selector('[data-e2e="comment-text"]')
            if text_elem:
                comment_data['text'] = await text_elem.inner_text()

            like_elem = await element.query_selector('[data-e2e="comment-like-count"]')
            if like_elem:
                like_text = await like_elem.inner_text()
                comment_data['like_count'] = self.spider.parser.parse_count(like_text)

            time_elem = await element.query_selector('[data-e2e="comment-time"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                comment_data['publish_time'] = self.spider.parser.parse_date(time_text)

            author_tag = await element.query_selector('[data-e2e="author-tag"]')
            comment_data['is_author'] = author_tag is not None

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
            more_replies_btn = await comment_element.query_selector('[data-e2e="view-more-replies"]')
            if more_replies_btn:
                await more_replies_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

            reply_elements = await comment_element.query_selector_all('[data-e2e="reply-item"]')

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
            'username': None,
            'avatar': None,
            'signature': None,
            'follower_count': 0,
            'following_count': 0,
            'total_likes': 0,
            'video_count': 0,
            'verified': False,
            'verification_type': None,
            'region': None
        }

        try:
            user_url = f"https://www.tiktok.com/@{user_id}"
            await page.goto(user_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            nickname_elem = await page.query_selector('[data-e2e="user-title"]')
            if nickname_elem:
                creator_info['nickname'] = await nickname_elem.inner_text()

            username_elem = await page.query_selector('[data-e2e="user-subtitle"]')
            if username_elem:
                creator_info['username'] = await username_elem.inner_text()

            avatar_elem = await page.query_selector('[data-e2e="user-avatar"] img')
            if avatar_elem:
                creator_info['avatar'] = await avatar_elem.get_attribute('src')

            signature_elem = await page.query_selector('[data-e2e="user-bio"]')
            if signature_elem:
                creator_info['signature'] = await signature_elem.inner_text()

            stats_elems = await page.query_selector_all('[data-e2e="user-post-stats"] strong')
            for idx, elem in enumerate(stats_elems):
                count_text = await elem.inner_text()
                count = self.spider.parser.parse_count(count_text)

                if idx == 0:
                    creator_info['following_count'] = count
                elif idx == 1:
                    creator_info['follower_count'] = count
                elif idx == 2:
                    creator_info['total_likes'] = count

            verified_elem = await page.query_selector('[data-e2e="user-verified"]')
            creator_info['verified'] = verified_elem is not None

            self.logger.info(f"Collected creator info for {user_id}")

        except Exception as e:
            self.logger.error(f"Error getting creator info: {e}")

        return creator_info


class TikTokSpider(BaseSpider):
    """TikTok爬虫主类"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="tiktok",
            headless=headless,
            proxy=proxy
        )

        self.anti_crawl = TikTokAntiCrawl(self)
        self.matcher = TikTokMatcher()
        self.interaction = TikTokInteraction(self)

        self.base_url = "https://www.tiktok.com"
        self.search_url = f"{self.base_url}/search"

        self._collected_video_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()
        await self.anti_crawl.initialize(self._page)
        self.logger.info("TikTok spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """登录TikTok"""
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

            self.logger.info("Please login manually (waiting 60 seconds)...")

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
            user_info = await self._page.query_selector('[data-e2e="user-avatar"]')
            return user_info is not None
        except:
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "video",
        sort_type: str = "relevance",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索视频"""
        self.logger.info(f"Searching TikTok for: {keyword}, max: {max_results}")

        results = []

        try:
            search_params = {
                'q': keyword,
                'type': search_type
            }
            search_url = f"{self.search_url}?{urlencode(search_params)}"

            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            if await self.anti_crawl.handle_slider_captcha(self._page):
                self.logger.info("Passed captcha check")

            await self._scroll_and_load(max_results)

            video_elements = await self._page.query_selector_all('[data-e2e="search-video-item"]')

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
            user_url = f"{self.base_url}/@{user_id}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            await self._scroll_and_load(max_posts)

            video_elements = await self._page.query_selector_all('[data-e2e="user-post-item"]')

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
        """获取视频详情"""
        self.logger.info(f"Getting video detail: {post_id}")

        video_data = {
            'content_id': post_id,
            'platform': 'tiktok',
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
            'collected_at': datetime.now()
        }

        try:
            video_url = f"{self.base_url}/@unknown/video/{post_id}"
            video_data['url'] = video_url

            await self.navigate(video_url)
            await asyncio.sleep(random.uniform(2, 3))

            await self.anti_crawl.random_scroll_behavior(self._page, duration=2)

            desc_elem = await self._page.query_selector('[data-e2e="browse-video-desc"]')
            if desc_elem:
                video_data['description'] = await desc_elem.inner_text()
                video_data['title'] = video_data['description'][:100]
                video_data['hashtags'] = self.parser.extract_hashtags(video_data['description'])
                video_data['mentions'] = self.parser.extract_mentions(video_data['description'])

            video_elem = await self._page.query_selector('video')
            if video_elem:
                video_data['video_url'] = await video_elem.get_attribute('src')
                poster = await video_elem.get_attribute('poster')
                if poster:
                    video_data['cover_image'] = poster

            author_elem = await self._page.query_selector('[data-e2e="browse-username"]')
            if author_elem:
                video_data['author']['nickname'] = await author_elem.inner_text()

            author_link_elem = await self._page.query_selector('[data-e2e="browse-username-link"]')
            if author_link_elem:
                author_url = await author_link_elem.get_attribute('href')
                if author_url:
                    video_data['author']['user_id'] = self._extract_user_id(author_url)

            stats_selectors = {
                'like_count': '[data-e2e="like-count"]',
                'comment_count': '[data-e2e="comment-count"]',
                'share_count': '[data-e2e="share-count"]'
            }

            for key, selector in stats_selectors.items():
                elem = await self._page.query_selector(selector)
                if elem:
                    count_text = await elem.inner_text()
                    video_data[key] = self.parser.parse_count(count_text)

            music_elem = await self._page.query_selector('[data-e2e="browse-music"]')
            if music_elem:
                music_title = await music_elem.inner_text()
                video_data['music']['title'] = music_title

            time_elem = await self._page.query_selector('[data-e2e="browser-nickname"] + span')
            if time_elem:
                time_text = await time_elem.inner_text()
                video_data['publish_time'] = self.spider.parser.parse_date(time_text)

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
        """获取评论"""
        video_url = f"{self.base_url}/@unknown/video/{post_id}"
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
            if '/video/' in url:
                video_id = url.split('/video/')[-1].split('?')[0]
                return video_id
            return None
        except:
            return None

    def _extract_user_id(self, url: str) -> Optional[str]:
        """从URL中提取用户ID"""
        try:
            if '/@' in url:
                user_id = url.split('/@')[-1].split('/')[0].split('?')[0]
                return user_id
            return None
        except:
            return None


async def search_tiktok_videos(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """便捷函数：搜索TikTok视频"""
    spider = TikTokSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


if __name__ == "__main__":
    async def test_tiktok_spider():
        spider = TikTokSpider(headless=False)

        async with spider.session():
            print("Testing TikTok search...")
            videos = await spider.search("cooking", max_results=5)

            for video in videos:
                print(f"\nVideo: {video.get('title')}")
                print(f"Author: {video.get('author', {}).get('nickname')}")
                print(f"Likes: {video.get('like_count')}")
