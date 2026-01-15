"""
Twitter (X) Spider Implementation
完整的Twitter/X平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 关键词搜索、用户主页、话题页、推文详情
2. Anti-Crawl Layer: 反反爬层 - 设备指纹、IP轮换、滑动行为模拟
3. Matcher Layer: 智能匹配层 - 多模态匹配（文本、图片、链接、话题）
4. Interaction Layer: 互动处理层 - 回复（嵌套）、转推、引用、用户信息
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


class TwitterAntiCrawl:
    """
    Twitter反反爬处理器
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
                }
            ]
        });

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'zh-CN', 'zh']
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_canvas_fingerprint(self, page: Page):
        """注入Canvas指纹随机化"""
        canvas_script = """
        // Canvas fingerprint noise
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
                await page.mouse.move(
                    x * (i / steps),
                    y * (i / steps)
                )
                await asyncio.sleep(0.01)

            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def simulate_read_time(self, content_length: int):
        """根据内容长度模拟阅读时间"""
        base_time = (content_length / 100) * random.uniform(2, 4)
        read_time = max(2, base_time + random.uniform(-1, 2))
        await asyncio.sleep(read_time)


class TwitterMatcher:
    """
    Twitter内容匹配器
    Layer 3: Matcher - 多模态匹配（文本、图片、链接、话题）
    """

    def __init__(self):
        self.logger = logger

    async def match_tweet(self, tweet: Dict[str, Any], criteria: Dict[str, Any]) -> tuple[bool, float]:
        """
        匹配推文内容

        Args:
            tweet: 推文数据
            criteria: 匹配条件 (keywords, hashtags, etc.)

        Returns:
            (is_match, match_score)
        """
        if not criteria:
            return True, 1.0

        score = 0.0
        weights = {
            'text': 0.4,
            'hashtags': 0.25,
            'mentions': 0.15,
            'links': 0.1,
            'media': 0.1
        }

        # 关键词匹配
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]

            if tweet.get('text'):
                text_matches = sum(1 for kw in keywords if kw.lower() in tweet['text'].lower())
                score += (text_matches / len(keywords)) * weights['text']

            if tweet.get('hashtags'):
                hashtag_text = ' '.join(tweet['hashtags']).lower()
                hashtag_matches = sum(1 for kw in keywords if kw.lower() in hashtag_text)
                score += (hashtag_matches / len(keywords)) * weights['hashtags']

        # 互动量过滤
        if 'min_likes' in criteria:
            if tweet.get('like_count', 0) < criteria['min_likes']:
                return False, 0.0

        if 'min_retweets' in criteria:
            if tweet.get('retweet_count', 0) < criteria['min_retweets']:
                return False, 0.0

        # 时间过滤
        if 'min_date' in criteria:
            tweet_date = tweet.get('publish_time')
            if tweet_date and isinstance(tweet_date, datetime):
                min_date = criteria['min_date']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)
                if tweet_date < min_date:
                    return False, 0.0

        # 归一化分数
        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0

        # 匹配阈值
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score


class TwitterInteraction:
    """
    Twitter互动处理器
    Layer 4: Interaction - 回复、转推、引用、用户信息
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def get_tweet_replies(
        self,
        page: Page,
        tweet_id: str,
        max_replies: int = 100,
        include_nested: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取推文回复（支持嵌套）

        Args:
            page: Playwright页面对象
            tweet_id: 推文ID
            max_replies: 最大回复数
            include_nested: 是否包含嵌套回复

        Returns:
            回复列表
        """
        replies = []

        try:
            # 等待回复区加载
            reply_selector = '[data-testid="tweet"]'
            try:
                await page.wait_for_selector(reply_selector, timeout=5000)
            except PlaywrightTimeoutError:
                self.logger.warning(f"No replies found for tweet {tweet_id}")
                return replies

            # 滚动加载更多回复
            await self._scroll_to_load_replies(page, max_replies)

            # 解析回复
            reply_elements = await page.query_selector_all(reply_selector)

            for idx, elem in enumerate(reply_elements[:max_replies]):
                try:
                    reply = await self._parse_tweet_element(page, elem)
                    if reply:
                        replies.append(reply)

                        # 获取嵌套回复
                        if include_nested and idx < 20:
                            nested = await self._get_nested_replies(page, elem, reply['tweet_id'])
                            reply['replies'] = nested
                            reply['reply_count'] = len(nested)

                except Exception as e:
                    self.logger.error(f"Error parsing reply: {e}")
                    continue

            self.logger.info(f"Collected {len(replies)} replies for tweet {tweet_id}")

        except Exception as e:
            self.logger.error(f"Error getting replies: {e}")

        return replies

    async def _scroll_to_load_replies(self, page: Page, target_count: int):
        """滚动加载更多回复"""
        last_count = 0
        no_change_count = 0
        max_scrolls = min(target_count // 10, 20)

        for _ in range(max_scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(1, 2))

            current_count = await page.evaluate(
                '() => document.querySelectorAll(\'[data-testid="tweet"]\').length'
            )

            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 2:
                    break
            else:
                no_change_count = 0
                last_count = current_count

            if current_count >= target_count:
                break

    async def _parse_tweet_element(self, page: Page, element) -> Optional[Dict[str, Any]]:
        """解析单条推文元素"""
        try:
            tweet_data = {
                'tweet_id': None,
                'user': {},
                'text': None,
                'like_count': 0,
                'retweet_count': 0,
                'reply_count': 0,
                'view_count': 0,
                'publish_time': None,
                'replies': [],
                'is_verified': False,
                'hashtags': [],
                'mentions': [],
                'links': [],
                'media': []
            }

            # 用户信息
            username_elem = await element.query_selector('[data-testid="User-Name"]')
            if username_elem:
                tweet_data['user']['nickname'] = await username_elem.inner_text()

            avatar_elem = await element.query_selector('[data-testid="Tweet-User-Avatar"] img')
            if avatar_elem:
                tweet_data['user']['avatar'] = await avatar_elem.get_attribute('src')

            # 推文内容
            text_elem = await element.query_selector('[data-testid="tweetText"]')
            if text_elem:
                tweet_data['text'] = await text_elem.inner_text()
                # 提取话题标签
                tweet_data['hashtags'] = self.spider.parser.extract_hashtags(tweet_data['text'])
                # 提取@用户
                tweet_data['mentions'] = self.spider.parser.extract_mentions(tweet_data['text'])

            # 点赞数
            like_elem = await element.query_selector('[data-testid="like"]')
            if like_elem:
                like_text = await like_elem.get_attribute('aria-label')
                tweet_data['like_count'] = self.spider.parser.parse_count(like_text)

            # 转推数
            retweet_elem = await element.query_selector('[data-testid="retweet"]')
            if retweet_elem:
                retweet_text = await retweet_elem.get_attribute('aria-label')
                tweet_data['retweet_count'] = self.spider.parser.parse_count(retweet_text)

            # 回复数
            reply_elem = await element.query_selector('[data-testid="reply"]')
            if reply_elem:
                reply_text = await reply_elem.get_attribute('aria-label')
                tweet_data['reply_count'] = self.spider.parser.parse_count(reply_text)

            # 发布时间
            time_elem = await element.query_selector('time')
            if time_elem:
                time_str = await time_elem.get_attribute('datetime')
                tweet_data['publish_time'] = datetime.fromisoformat(time_str.replace('Z', '+00:00'))

            # 验证标识
            verified_elem = await element.query_selector('[data-testid="icon-verified"]')
            tweet_data['is_verified'] = verified_elem is not None

            # 媒体
            media_elems = await element.query_selector_all('[data-testid="tweetPhoto"]')
            for media_elem in media_elems:
                img = await media_elem.query_selector('img')
                if img:
                    tweet_data['media'].append({
                        'type': 'image',
                        'url': await img.get_attribute('src')
                    })

            # 生成推文ID
            if tweet_data['text']:
                tweet_data['tweet_id'] = hashlib.md5(
                    f"{tweet_data['user'].get('nickname', '')}{tweet_data['text']}{tweet_data['publish_time']}".encode()
                ).hexdigest()[:16]

            return tweet_data if tweet_data['text'] else None

        except Exception as e:
            self.logger.error(f"Error parsing tweet element: {e}")
            return None

    async def _get_nested_replies(
        self,
        page: Page,
        tweet_element,
        parent_tweet_id: str
    ) -> List[Dict[str, Any]]:
        """获取嵌套回复"""
        nested = []

        try:
            # 查找"显示更多回复"按钮
            more_btn = await tweet_element.query_selector('[data-testid="show-more-replies"]')
            if more_btn:
                await more_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

            # 解析嵌套回复
            nested_elems = await tweet_element.query_selector_all('[data-testid="tweet-reply"]')

            for nested_elem in nested_elems[:10]:
                reply = await self._parse_tweet_element(page, nested_elem)
                if reply:
                    reply['parent_id'] = parent_tweet_id
                    nested.append(reply)

        except Exception as e:
            self.logger.debug(f"Error getting nested replies: {e}")

        return nested

    async def get_user_info(self, page: Page, username: str) -> Dict[str, Any]:
        """
        获取用户详细信息

        Args:
            page: Playwright页面对象
            username: 用户名（不含@）

        Returns:
            用户信息
        """
        user_info = {
            'username': username,
            'display_name': None,
            'avatar': None,
            'banner': None,
            'bio': None,
            'location': None,
            'website': None,
            'follower_count': 0,
            'following_count': 0,
            'tweet_count': 0,
            'verified': False,
            'created_at': None,
            'blue_subscriber': False
        }

        try:
            # 访问用户主页
            user_url = f"https://twitter.com/{username}"
            await page.goto(user_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 显示名称
            display_name_elem = await page.query_selector('[data-testid="UserName"]')
            if display_name_elem:
                user_info['display_name'] = await display_name_elem.inner_text()

            # 头像
            avatar_elem = await page.query_selector('[data-testid="UserAvatar-Container-*"] img')
            if avatar_elem:
                user_info['avatar'] = await avatar_elem.get_attribute('src')

            # 横幅
            banner_elem = await page.query_selector('[data-testid="UserProfileHeader_Banners"] img')
            if banner_elem:
                user_info['banner'] = await banner_elem.get_attribute('src')

            # 简介
            bio_elem = await page.query_selector('[data-testid="UserDescription"]')
            if bio_elem:
                user_info['bio'] = await bio_elem.inner_text()

            # 位置
            location_elem = await page.query_selector('[data-testid="UserLocation"]')
            if location_elem:
                user_info['location'] = await location_elem.inner_text()

            # 网站
            website_elem = await page.query_selector('[data-testid="UserUrl"]')
            if website_elem:
                link = await website_elem.query_selector('a')
                if link:
                    user_info['website'] = await link.get_attribute('href')

            # 统计数据
            following_elem = await page.query_selector('[href$="/following"]')
            if following_elem:
                following_text = await following_elem.inner_text()
                user_info['following_count'] = self.spider.parser.parse_count(following_text)

            followers_elem = await page.query_selector('[href$="/followers"]')
            if followers_elem:
                followers_text = await followers_elem.inner_text()
                user_info['follower_count'] = self.spider.parser.parse_count(followers_text)

            # 验证标识
            verified_elem = await page.query_selector('[data-testid="icon-verified"]')
            user_info['verified'] = verified_elem is not None

            # Blue订阅者
            blue_elem = await page.query_selector('[data-testid="icon-blue-verified"]')
            user_info['blue_subscriber'] = blue_elem is not None

            self.logger.info(f"Collected user info for @{username}")

        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")

        return user_info


class TwitterSpider(BaseSpider):
    """
    Twitter爬虫主类
    Layer 1: Spider - 完整的爬取功能实现

    功能:
    - 关键词搜索推文
    - 用户主页爬取
    - 话题标签爬取
    - 推文详情获取（20+字段）
    - 回复采集（嵌套）
    - 转推和引用
    - 图片/视频下载
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="twitter",
            headless=headless,
            proxy=proxy
        )

        # 初始化各层组件
        self.anti_crawl = TwitterAntiCrawl(self)
        self.matcher = TwitterMatcher()
        self.interaction = TwitterInteraction(self)

        # Twitter特定配置
        self.base_url = "https://twitter.com"
        self.search_url = f"{self.base_url}/search"

        # 缓存
        self._collected_tweet_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()
        await self.anti_crawl.initialize(self._page)
        self.logger.info("Twitter spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """
        登录Twitter

        Args:
            username: 用户名或邮箱
            password: 密码

        Returns:
            登录是否成功
        """
        try:
            await self.navigate(f"{self.base_url}/login")
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

            # 手动登录
            if username and password:
                # 输入用户名
                username_input = await self._page.query_selector('input[autocomplete="username"]')
                if username_input:
                    await username_input.fill(username)
                    await asyncio.sleep(random.uniform(0.5, 1))
                    await self._page.keyboard.press('Enter')
                    await asyncio.sleep(2)

                # 输入密码
                password_input = await self._page.query_selector('input[type="password"]')
                if password_input:
                    await password_input.fill(password)
                    await asyncio.sleep(random.uniform(0.5, 1))
                    await self._page.keyboard.press('Enter')
                    await asyncio.sleep(3)

                # 检查登录状态
                if await self._check_login_status():
                    self.logger.info("Login successful")
                    self._is_logged_in = True
                    await self._save_cookies()
                    return True

            self.logger.warning("Login failed, continuing without login")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def _check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            home_nav = await self._page.query_selector('[data-testid="AppTabBar_Home_Link"]')
            return home_nav is not None
        except:
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "latest",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索推文

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型 (latest/top/people/photos/videos)
            criteria: 匹配条件

        Returns:
            推文列表
        """
        self.logger.info(f"Searching for: {keyword}, type: {search_type}, max: {max_results}")

        results = []

        try:
            # 构建搜索URL
            search_params = {
                'q': keyword,
                'f': search_type
            }
            search_url = f"{self.search_url}?{urlencode(search_params)}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载更多内容
            await self._scroll_and_load(max_results)

            # 解析推文列表
            tweet_elements = await self._page.query_selector_all('[data-testid="tweet"]')

            for elem in tweet_elements[:max_results * 2]:
                try:
                    # 获取推文数据
                    tweet_data = await self.interaction._parse_tweet_element(self._page, elem)

                    if not tweet_data or tweet_data['tweet_id'] in self._collected_tweet_ids:
                        continue

                    # 获取推文链接
                    link_elem = await elem.query_selector('a[href*="/status/"]')
                    if link_elem:
                        tweet_url = await link_elem.get_attribute('href')
                        tweet_data['url'] = f"https://twitter.com{tweet_url}"
                        tweet_data['tweet_id'] = tweet_url.split('/status/')[-1].split('?')[0]

                    # 内容匹配
                    if criteria:
                        is_match, match_score = await self.matcher.match_tweet(tweet_data, criteria)
                        if not is_match:
                            continue
                        tweet_data['match_score'] = match_score

                    results.append(tweet_data)
                    self._collected_tweet_ids.add(tweet_data['tweet_id'])

                    if len(results) >= max_results:
                        break

                    await asyncio.sleep(random.uniform(0.3, 0.7))

                except Exception as e:
                    self.logger.error(f"Error parsing tweet: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} tweets for keyword: {keyword}")

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def get_user_profile(self, username: str) -> Dict[str, Any]:
        """获取用户资料"""
        return await self.interaction.get_user_info(self._page, username)

    async def get_user_posts(
        self,
        username: str,
        max_posts: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取用户推文"""
        self.logger.info(f"Getting posts for user: @{username}, max: {max_posts}")

        posts = []

        try:
            user_url = f"{self.base_url}/{username}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            await self._scroll_and_load(max_posts)

            tweet_elements = await self._page.query_selector_all('[data-testid="tweet"]')

            for elem in tweet_elements[:max_posts * 2]:
                try:
                    tweet_data = await self.interaction._parse_tweet_element(self._page, elem)

                    if not tweet_data or tweet_data['tweet_id'] in self._collected_tweet_ids:
                        continue

                    if criteria:
                        is_match, match_score = await self.matcher.match_tweet(tweet_data, criteria)
                        if not is_match:
                            continue
                        tweet_data['match_score'] = match_score

                    posts.append(tweet_data)
                    self._collected_tweet_ids.add(tweet_data['tweet_id'])

                    if len(posts) >= max_posts:
                        break

                except Exception as e:
                    self.logger.error(f"Error parsing user tweet: {e}")
                    continue

            self.logger.info(f"Collected {len(posts)} posts for user: @{username}")

        except Exception as e:
            self.logger.error(f"Get user posts failed: {e}")

        return posts

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """获取推文详情"""
        self.logger.info(f"Getting tweet detail: {post_id}")

        tweet_data = {
            'content_id': post_id,
            'platform': 'twitter',
            'content_type': 'tweet',
            'url': None,
            'text': None,
            'user': {},
            'hashtags': [],
            'mentions': [],
            'links': [],
            'media': [],
            'like_count': 0,
            'retweet_count': 0,
            'reply_count': 0,
            'view_count': 0,
            'quote_count': 0,
            'publish_time': None,
            'is_verified': False,
            'is_reply': False,
            'reply_to': None,
            'collected_at': datetime.now()
        }

        try:
            tweet_url = f"{self.base_url}/i/web/status/{post_id}"
            tweet_data['url'] = tweet_url

            await self.navigate(tweet_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 查找主推文
            main_tweet = await self._page.query_selector('[data-testid="tweet"]')
            if main_tweet:
                parsed = await self.interaction._parse_tweet_element(self._page, main_tweet)
                if parsed:
                    tweet_data.update(parsed)

            self.logger.info(f"Collected tweet detail: {post_id}")

        except Exception as e:
            self.logger.error(f"Error getting tweet detail: {e}")

        return tweet_data

    async def get_comments(
        self,
        post_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """获取推文回复"""
        tweet_url = f"{self.base_url}/i/web/status/{post_id}"
        current_url = self._page.url

        if post_id not in current_url:
            await self.navigate(tweet_url)
            await asyncio.sleep(2)

        return await self.interaction.get_tweet_replies(
            self._page,
            post_id,
            max_comments,
            include_replies
        )

    async def get_hashtag_tweets(
        self,
        hashtag: str,
        max_tweets: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取话题标签推文"""
        hashtag_clean = hashtag.lstrip('#')
        return await self.search(f"#{hashtag_clean}", max_tweets, criteria=criteria)

    async def _scroll_and_load(self, target_count: int):
        """滚动加载更多内容"""
        last_height = 0
        no_change_count = 0
        max_scrolls = min(target_count // 5, 20)

        for _ in range(max_scrolls):
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


# 便捷函数
async def search_twitter_tweets(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """便捷函数：搜索Twitter推文"""
    spider = TwitterSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


if __name__ == "__main__":
    async def test_twitter_spider():
        spider = TwitterSpider(headless=False)

        async with spider.session():
            print("Testing search...")
            tweets = await spider.search("AI", max_results=5)

            for tweet in tweets:
                print(f"\nTweet: {tweet.get('text')}")
                print(f"User: @{tweet.get('user', {}).get('nickname')}")
                print(f"Likes: {tweet.get('like_count')}")
                print(f"URL: {tweet.get('url')}")
