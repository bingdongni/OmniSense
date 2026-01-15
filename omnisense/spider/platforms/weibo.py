"""
Weibo (微博) Spider Implementation
完整的微博平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 热搜监控、用户时间线、关键词搜索、话题追踪
2. Anti-Crawl Layer: 反反爬层 - Cookie轮换、请求节流、User-Agent管理
3. Matcher Layer: 智能匹配层 - 话题匹配、实体抽取、热度评估
4. Interaction Layer: 互动处理层 - 转发链、评论链、点赞、KOL分析
"""

import asyncio
import hashlib
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlencode, urlparse, parse_qs

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from omnisense.config import config
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class WeiboAntiCrawl:
    """
    微博反反爬处理器
    Layer 2: Anti-Crawl - Cookie轮换、请求节流、滑块验证
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger
        self._cookie_pool = []
        self._current_cookie_index = 0
        self._request_timestamps = []

    async def initialize(self, page: Page):
        """初始化反爬措施"""
        await self._inject_webdriver_evasion(page)
        await self._inject_font_anticrack(page)
        await self._setup_request_throttle()

    async def _inject_webdriver_evasion(self, page: Page):
        """注入反webdriver检测"""
        evasion_script = """
        // Remove webdriver
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
            get: () => [1, 2, 3, 4, 5]
        });

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });

        // Device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });

        // Hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_font_anticrack(self, page: Page):
        """注入微博字体反爬破解"""
        # 微博使用自定义字体来隐藏数字
        font_script = """
        // Weibo font anticrack
        window._weiboFontMap = {
            // 映射微博自定义字体的字符到实际数字
            // 这个映射需要根据实际情况动态更新
        };

        // 拦截字体加载
        const originalAddEventListener = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(type, listener, options) {
            if (type === 'DOMContentLoaded') {
                const newListener = function(event) {
                    // 处理字体映射
                    const elements = document.querySelectorAll('[class*="woo-font"]');
                    elements.forEach(el => {
                        const text = el.innerText;
                        // 解码字体
                        if (window._weiboFontMap[text]) {
                            el.innerText = window._weiboFontMap[text];
                        }
                    });
                    listener(event);
                };
                return originalAddEventListener.call(this, type, newListener, options);
            }
            return originalAddEventListener.call(this, type, listener, options);
        };
        """
        await page.add_init_script(font_script)

    async def _setup_request_throttle(self):
        """设置请求节流"""
        self._request_timestamps = []

    async def throttle_request(self):
        """请求节流控制"""
        current_time = time.time()

        # 移除1分钟前的时间戳
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if current_time - ts < 60
        ]

        # 检查请求频率
        if len(self._request_timestamps) >= 30:  # 每分钟最多30个请求
            oldest_timestamp = self._request_timestamps[0]
            wait_time = 60 - (current_time - oldest_timestamp)
            if wait_time > 0:
                self.logger.info(f"Request throttling: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        # 添加当前时间戳
        self._request_timestamps.append(current_time)

        # 随机延迟
        await asyncio.sleep(random.uniform(1, 3))

    async def rotate_cookie(self, page: Page):
        """轮换Cookie"""
        if not self._cookie_pool:
            return

        self._current_cookie_index = (self._current_cookie_index + 1) % len(self._cookie_pool)
        cookie = self._cookie_pool[self._current_cookie_index]

        await page.context.clear_cookies()
        await page.context.add_cookies(cookie)

        self.logger.debug(f"Rotated to cookie {self._current_cookie_index}")

    async def handle_slider_captcha(self, page: Page) -> bool:
        """处理滑块验证码"""
        try:
            # 检测滑块
            slider_selector = '.geetest_slider_button'
            if not await page.query_selector(slider_selector):
                return True

            self.logger.info("Detected slider captcha, attempting to solve...")

            slider = await page.query_selector(slider_selector)
            box = await slider.bounding_box()

            if not box:
                return False

            # 计算滑动距离
            start_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] / 2
            slide_distance = random.randint(260, 300)

            # 模拟人类滑动
            await page.mouse.move(start_x, start_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.down()

            # 分段滑动
            steps = random.randint(25, 35)
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

            # 检查验证结果
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


class WeiboMatcher:
    """
    微博内容匹配器
    Layer 3: Matcher - 话题匹配、实体抽取、热度评估
    """

    def __init__(self):
        self.logger = logger

    async def match_weibo(self, weibo: Dict[str, Any], criteria: Dict[str, Any]) -> tuple[bool, float]:
        """
        匹配微博内容

        Args:
            weibo: 微博数据
            criteria: 匹配条件 (keywords, topics, entity_types, etc.)

        Returns:
            (is_match, match_score)
        """
        if not criteria:
            return True, 1.0

        score = 0.0
        weights = {
            'text': 0.3,
            'topics': 0.25,
            'entities': 0.2,
            'heat': 0.15,
            'source': 0.1
        }

        # 关键词匹配
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]

            text = weibo.get('text', '')
            keyword_matches = sum(1 for kw in keywords if kw.lower() in text.lower())
            score += (keyword_matches / len(keywords)) * weights['text']

        # 话题匹配
        if 'topics' in criteria:
            required_topics = criteria['topics']
            if isinstance(required_topics, str):
                required_topics = [required_topics]

            weibo_topics = [t.lower() for t in weibo.get('topics', [])]
            topic_matches = sum(1 for topic in required_topics if topic.lower() in weibo_topics)
            score += (topic_matches / len(required_topics)) * weights['topics']

        # 实体匹配
        if 'entity_types' in criteria:
            entity_types = criteria['entity_types']
            entities = self._extract_entities(weibo)

            entity_score = 0.0
            for entity_type in entity_types:
                if entity_type in entities and entities[entity_type]:
                    entity_score += 1.0 / len(entity_types)

            score += entity_score * weights['entities']

        # 热度过滤
        if 'min_heat' in criteria:
            heat = self._calculate_heat(weibo)
            if heat < criteria['min_heat']:
                return False, 0.0
            score += min(heat / criteria['min_heat'], 1.0) * weights['heat']

        # 来源过滤
        if 'sources' in criteria:
            source = weibo.get('source', '')
            if any(s in source for s in criteria['sources']):
                score += weights['source']

        # 互动量过滤
        if 'min_reposts' in criteria:
            if weibo.get('repost_count', 0) < criteria['min_reposts']:
                return False, 0.0

        if 'min_comments' in criteria:
            if weibo.get('comment_count', 0) < criteria['min_comments']:
                return False, 0.0

        # 时间过滤
        if 'min_date' in criteria:
            weibo_date = weibo.get('publish_time')
            if weibo_date and isinstance(weibo_date, datetime):
                min_date = criteria['min_date']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)
                if weibo_date < min_date:
                    return False, 0.0

        # 归一化分数
        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0

        # 匹配阈值
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score

    def _extract_entities(self, weibo: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取实体"""
        text = weibo.get('text', '')

        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'urls': [],
            'emails': [],
            'phones': []
        }

        # 提取@用户（可能是人名或组织）
        mentions = weibo.get('mentions', [])
        entities['persons'].extend(mentions)

        # 提取URL
        from omnisense.spider.utils.parser import ContentParser
        parser = ContentParser(self.logger)
        entities['urls'] = parser.extract_urls(text)
        entities['emails'] = parser.extract_emails(text)
        entities['phones'] = parser.extract_phone_numbers(text)

        return entities

    def _calculate_heat(self, weibo: Dict[str, Any]) -> float:
        """计算热度"""
        # 热度 = 转发 * 2 + 评论 * 1.5 + 点赞 * 1
        repost_count = weibo.get('repost_count', 0)
        comment_count = weibo.get('comment_count', 0)
        like_count = weibo.get('like_count', 0)

        heat = repost_count * 2 + comment_count * 1.5 + like_count * 1

        return heat


class WeiboInteraction:
    """
    微博互动处理器
    Layer 4: Interaction - 转发链、评论链、点赞、KOL分析
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def get_weibo_comments(
        self,
        page: Page,
        weibo_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取微博评论

        Args:
            page: Playwright页面对象
            weibo_id: 微博ID
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        comments = []

        try:
            # 等待评论区加载
            comment_selector = '.card-comment, [class*="comment"]'
            try:
                await page.wait_for_selector(comment_selector, timeout=5000)
            except PlaywrightTimeoutError:
                self.logger.warning(f"No comments found for weibo {weibo_id}")
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
                        if include_replies and idx < 20:
                            replies = await self._get_comment_replies(page, elem, comment['comment_id'])
                            comment['replies'] = replies
                            comment['reply_count'] = len(replies)

                except Exception as e:
                    self.logger.error(f"Error parsing comment: {e}")
                    continue

            self.logger.info(f"Collected {len(comments)} comments for weibo {weibo_id}")

        except Exception as e:
            self.logger.error(f"Error getting comments: {e}")

        return comments

    async def _scroll_to_load_comments(self, page: Page, target_count: int):
        """滚动加载更多评论"""
        last_count = 0
        no_change_count = 0
        max_scrolls = min(target_count // 10, 20)

        for _ in range(max_scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(1, 2))

            current_count = await page.evaluate(
                """() => document.querySelectorAll('.card-comment, [class*="comment"]').length"""
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
                'source': None,
                'ip_location': None
            }

            # 用户信息
            username_elem = await element.query_selector('.name, [class*="name"]')
            if username_elem:
                comment_data['user']['nickname'] = await username_elem.inner_text()

            avatar_elem = await element.query_selector('.avatar img')
            if avatar_elem:
                comment_data['user']['avatar'] = await avatar_elem.get_attribute('src')

            # 评论内容
            text_elem = await element.query_selector('.txt, [class*="text"], [class*="content"]')
            if text_elem:
                comment_data['text'] = await text_elem.inner_text()

            # 点赞数
            like_elem = await element.query_selector('.like em, [class*="like"]')
            if like_elem:
                like_text = await like_elem.inner_text()
                comment_data['like_count'] = self.spider.parser.parse_count(like_text)

            # 发布时间
            time_elem = await element.query_selector('.time, [class*="time"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                comment_data['publish_time'] = self.spider.parser.parse_date(time_text)

            # 来源
            source_elem = await element.query_selector('.source, [class*="from"]')
            if source_elem:
                comment_data['source'] = await source_elem.inner_text()

            # IP属地
            ip_elem = await element.query_selector('.from, [class*="location"]')
            if ip_elem:
                ip_text = await ip_elem.inner_text()
                if 'IP属地' in ip_text:
                    comment_data['ip_location'] = ip_text.replace('IP属地：', '').strip()

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
            more_replies_btn = await comment_element.query_selector('.more, [class*="more-reply"]')
            if more_replies_btn:
                await more_replies_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

            # 解析回复
            reply_elements = await comment_element.query_selector_all('.reply, [class*="reply"]')

            for reply_elem in reply_elements[:10]:
                reply = await self._parse_comment_element(page, reply_elem)
                if reply:
                    reply['parent_id'] = parent_comment_id
                    replies.append(reply)

        except Exception as e:
            self.logger.debug(f"Error getting comment replies: {e}")

        return replies

    async def get_repost_chain(
        self,
        page: Page,
        weibo_id: str,
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        获取转发链

        Args:
            page: Playwright页面对象
            weibo_id: 微博ID
            max_depth: 最大追踪深度

        Returns:
            转发链列表
        """
        repost_chain = []

        try:
            current_id = weibo_id
            current_depth = 0

            while current_depth < max_depth:
                # 访问微博页面
                weibo_url = f"https://weibo.com/{current_id}"
                await page.goto(weibo_url, wait_until='networkidle')
                await asyncio.sleep(random.uniform(1, 2))

                # 检查是否有转发源
                repost_elem = await page.query_selector('.retweeted, [class*="retweeted"]')
                if not repost_elem:
                    break

                # 解析转发信息
                repost_info = {
                    'depth': current_depth,
                    'weibo_id': None,
                    'user': {},
                    'text': None,
                    'publish_time': None
                }

                # 用户信息
                user_elem = await repost_elem.query_selector('.name, [class*="name"]')
                if user_elem:
                    repost_info['user']['nickname'] = await user_elem.inner_text()

                # 文本
                text_elem = await repost_elem.query_selector('.txt, [class*="text"]')
                if text_elem:
                    repost_info['text'] = await text_elem.inner_text()

                # 时间
                time_elem = await repost_elem.query_selector('.time, [class*="time"]')
                if time_elem:
                    time_text = await time_elem.inner_text()
                    repost_info['publish_time'] = self.spider.parser.parse_date(time_text)

                # 提取转发源ID
                link_elem = await repost_elem.query_selector('a')
                if link_elem:
                    link_url = await link_elem.get_attribute('href')
                    if link_url:
                        repost_info['weibo_id'] = self._extract_weibo_id(link_url)
                        current_id = repost_info['weibo_id']

                repost_chain.append(repost_info)
                current_depth += 1

                if not repost_info['weibo_id']:
                    break

            self.logger.info(f"Collected repost chain of depth {len(repost_chain)}")

        except Exception as e:
            self.logger.error(f"Error getting repost chain: {e}")

        return repost_chain

    def _extract_weibo_id(self, url: str) -> Optional[str]:
        """从URL中提取微博ID"""
        try:
            if '/status/' in url:
                weibo_id = url.split('/status/')[-1].split('?')[0]
                return weibo_id
            return None
        except:
            return None

    async def get_kol_analysis(self, page: Page, user_id: str) -> Dict[str, Any]:
        """
        KOL分析

        Args:
            page: Playwright页面对象
            user_id: 用户ID

        Returns:
            KOL分析数据
        """
        analysis = {
            'user_id': user_id,
            'nickname': None,
            'follower_count': 0,
            'following_count': 0,
            'weibo_count': 0,
            'verified': False,
            'verification_type': None,
            'influence_score': 0.0,
            'activity_score': 0.0,
            'engagement_rate': 0.0,
            'avg_repost': 0,
            'avg_comment': 0,
            'avg_like': 0,
            'topics': [],
            'posting_frequency': 0.0
        }

        try:
            # 访问用户主页
            user_url = f"https://weibo.com/u/{user_id}"
            await page.goto(user_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 用户信息
            nickname_elem = await page.query_selector('.name, [class*="name"]')
            if nickname_elem:
                analysis['nickname'] = await nickname_elem.inner_text()

            # 统计数据
            stats_script = """
            () => {
                const stats = {};
                const items = document.querySelectorAll('.info, [class*="count"]');
                items.forEach(item => {
                    const text = item.innerText || item.textContent;
                    if (text.includes('关注')) {
                        stats.following = text;
                    } else if (text.includes('粉丝')) {
                        stats.followers = text;
                    } else if (text.includes('微博')) {
                        stats.weibo = text;
                    }
                });
                return stats;
            }
            """
            stats = await page.evaluate(stats_script)

            if stats:
                if 'following' in stats:
                    analysis['following_count'] = self.spider.parser.parse_count(stats['following'])
                if 'followers' in stats:
                    analysis['follower_count'] = self.spider.parser.parse_count(stats['followers'])
                if 'weibo' in stats:
                    analysis['weibo_count'] = self.spider.parser.parse_count(stats['weibo'])

            # 认证信息
            verified_elem = await page.query_selector('.verify, [class*="verify"]')
            if verified_elem:
                analysis['verified'] = True
                verification_text = await verified_elem.inner_text()
                analysis['verification_type'] = verification_text

            # 分析最近微博
            weibo_elements = await page.query_selector_all('.card-wrap')
            total_reposts = 0
            total_comments = 0
            total_likes = 0
            weibo_count = 0

            for weibo_elem in weibo_elements[:20]:
                try:
                    # 转发数
                    repost_elem = await weibo_elem.query_selector('[class*="repost"]')
                    if repost_elem:
                        repost_text = await repost_elem.inner_text()
                        total_reposts += self.spider.parser.parse_count(repost_text)

                    # 评论数
                    comment_elem = await weibo_elem.query_selector('[class*="comment"]')
                    if comment_elem:
                        comment_text = await comment_elem.inner_text()
                        total_comments += self.spider.parser.parse_count(comment_text)

                    # 点赞数
                    like_elem = await weibo_elem.query_selector('[class*="like"]')
                    if like_elem:
                        like_text = await like_elem.inner_text()
                        total_likes += self.spider.parser.parse_count(like_text)

                    weibo_count += 1

                except Exception as e:
                    continue

            # 计算平均互动
            if weibo_count > 0:
                analysis['avg_repost'] = total_reposts // weibo_count
                analysis['avg_comment'] = total_comments // weibo_count
                analysis['avg_like'] = total_likes // weibo_count

            # 计算影响力分数
            if analysis['follower_count'] > 0:
                avg_engagement = analysis['avg_repost'] + analysis['avg_comment'] + analysis['avg_like']
                analysis['engagement_rate'] = (avg_engagement / analysis['follower_count']) * 100

                # 影响力分数 = log(粉丝数) * 互动率 * 10
                import math
                analysis['influence_score'] = math.log10(max(analysis['follower_count'], 1)) * analysis['engagement_rate'] * 10

            # 活跃度分数
            if analysis['weibo_count'] > 0:
                # 假设账号创建1年，计算发帖频率
                analysis['posting_frequency'] = analysis['weibo_count'] / 365
                analysis['activity_score'] = min(analysis['posting_frequency'] * 10, 100)

            self.logger.info(f"Completed KOL analysis for {user_id}")

        except Exception as e:
            self.logger.error(f"Error in KOL analysis: {e}")

        return analysis


class WeiboSpider(BaseSpider):
    """
    微博爬虫主类
    Layer 1: Spider - 完整的爬取功能实现

    功能:
    - 热搜监控
    - 关键词搜索
    - 用户时间线爬取
    - 话题追踪
    - 微博详情获取（20+字段）
    - 评论采集（嵌套回复）
    - 转发链追踪
    - KOL分析
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="weibo",
            headless=headless,
            proxy=proxy
        )

        # 初始化各层组件
        self.anti_crawl = WeiboAntiCrawl(self)
        self.matcher = WeiboMatcher()
        self.interaction = WeiboInteraction(self)

        # 微博特定配置
        self.base_url = "https://weibo.com"
        self.search_url = f"{self.base_url}/search"
        self.hot_search_url = f"{self.base_url}/top/summary"

        # 缓存
        self._collected_weibo_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()

        # 初始化反爬
        await self.anti_crawl.initialize(self._page)

        self.logger.info("Weibo spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """
        登录微博

        Args:
            username: 用户名
            password: 密码

        Returns:
            登录是否成功
        """
        try:
            # 访问微博首页
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

            # 等待用户扫码或输入密码登录
            self.logger.info("Please login manually (waiting 60 seconds)...")

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
            user_info = await self._page.query_selector('.gn_nav_list, [class*="user"]')
            return user_info is not None
        except:
            return False

    async def get_hot_search(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        获取热搜榜

        Args:
            max_results: 最大结果数

        Returns:
            热搜列表
        """
        self.logger.info(f"Getting hot search, max: {max_results}")

        hot_search = []

        try:
            # 访问热搜页
            await self.navigate(self.hot_search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 解析热搜列表
            hot_elements = await self._page.query_selector_all('tbody tr')

            for idx, elem in enumerate(hot_elements[:max_results]):
                try:
                    hot_item = {
                        'rank': idx + 1,
                        'keyword': None,
                        'heat': 0,
                        'icon': None,
                        'category': None,
                        'url': None
                    }

                    # 关键词
                    keyword_elem = await elem.query_selector('td:nth-child(2) a')
                    if keyword_elem:
                        hot_item['keyword'] = await keyword_elem.inner_text()
                        hot_item['url'] = await keyword_elem.get_attribute('href')

                    # 热度
                    heat_elem = await elem.query_selector('td:nth-child(3)')
                    if heat_elem:
                        heat_text = await heat_elem.inner_text()
                        hot_item['heat'] = self.parser.parse_count(heat_text)

                    # 图标（新、热、爆等）
                    icon_elem = await elem.query_selector('td:nth-child(2) img')
                    if icon_elem:
                        icon_alt = await icon_elem.get_attribute('alt')
                        hot_item['icon'] = icon_alt

                    hot_search.append(hot_item)

                except Exception as e:
                    self.logger.error(f"Error parsing hot search item: {e}")
                    continue

            self.logger.info(f"Collected {len(hot_search)} hot search items")

        except Exception as e:
            self.logger.error(f"Get hot search failed: {e}")

        return hot_search

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "综合",
        sort_type: str = "默认",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索微博

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型 (综合/实时/热门/用户)
            sort_type: 排序方式 (默认/时间/热度)
            criteria: 匹配条件

        Returns:
            微博列表
        """
        self.logger.info(f"Searching for: {keyword}, type: {search_type}, max: {max_results}")

        results = []

        try:
            # 构建搜索URL
            search_params = {
                'q': keyword,
                'type': search_type,
                'sort': sort_type
            }
            search_url = f"{self.search_url}?{urlencode(search_params)}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 请求节流
            await self.anti_crawl.throttle_request()

            # 滚动加载更多内容
            await self._scroll_and_load(max_results)

            # 解析微博列表
            weibo_elements = await self._page.query_selector_all('.card-wrap')

            for elem in weibo_elements[:max_results * 2]:
                try:
                    # 提取微博ID和URL
                    link_elem = await elem.query_selector('.from a')
                    if not link_elem:
                        continue

                    weibo_url = await link_elem.get_attribute('href')
                    if not weibo_url:
                        continue

                    weibo_id = self._extract_weibo_id(weibo_url)
                    if not weibo_id or weibo_id in self._collected_weibo_ids:
                        continue

                    # 获取微博详情
                    weibo_data = await self.get_post_detail(weibo_id)

                    if weibo_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_weibo(weibo_data, criteria)
                            if not is_match:
                                continue
                            weibo_data['match_score'] = match_score

                        results.append(weibo_data)
                        self._collected_weibo_ids.add(weibo_id)

                        if len(results) >= max_results:
                            break

                    # 随机延迟
                    await asyncio.sleep(random.uniform(0.5, 1))

                except Exception as e:
                    self.logger.error(f"Error parsing weibo: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} weibos for keyword: {keyword}")

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
        return await self.interaction.get_kol_analysis(self._page, user_id)

    async def get_user_posts(
        self,
        user_id: str,
        max_posts: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户时间线（微博列表）

        Args:
            user_id: 用户ID
            max_posts: 最大微博数
            criteria: 匹配条件

        Returns:
            微博列表
        """
        self.logger.info(f"Getting posts for user: {user_id}, max: {max_posts}")

        posts = []

        try:
            # 访问用户主页
            user_url = f"{self.base_url}/u/{user_id}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 请求节流
            await self.anti_crawl.throttle_request()

            # 滚动加载
            await self._scroll_and_load(max_posts)

            # 解析微博列表
            weibo_elements = await self._page.query_selector_all('.card-wrap')

            for elem in weibo_elements[:max_posts * 2]:
                try:
                    # 获取微博链接
                    link_elem = await elem.query_selector('.from a')
                    if not link_elem:
                        continue

                    weibo_url = await link_elem.get_attribute('href')
                    weibo_id = self._extract_weibo_id(weibo_url)

                    if not weibo_id or weibo_id in self._collected_weibo_ids:
                        continue

                    # 获取微博详情
                    weibo_data = await self.get_post_detail(weibo_id)

                    if weibo_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_weibo(weibo_data, criteria)
                            if not is_match:
                                continue
                            weibo_data['match_score'] = match_score

                        posts.append(weibo_data)
                        self._collected_weibo_ids.add(weibo_id)

                        if len(posts) >= max_posts:
                            break

                except Exception as e:
                    self.logger.error(f"Error parsing user weibo: {e}")
                    continue

            self.logger.info(f"Collected {len(posts)} posts for user: {user_id}")

        except Exception as e:
            self.logger.error(f"Get user posts failed: {e}")

        return posts

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        获取微博详情（20+字段）

        Args:
            post_id: 微博ID

        Returns:
            微博详细信息
        """
        self.logger.info(f"Getting weibo detail: {post_id}")

        weibo_data = {
            'content_id': post_id,
            'platform': 'weibo',
            'content_type': 'weibo',
            'url': None,
            'text': None,
            'images': [],
            'video_url': None,
            'topics': [],
            'mentions': [],
            'urls': [],
            'author': {},
            'repost_count': 0,
            'comment_count': 0,
            'like_count': 0,
            'publish_time': None,
            'source': None,
            'location': None,
            'ip_location': None,
            'is_repost': False,
            'repost_source': None,
            'heat': 0,
            'collected_at': datetime.now()
        }

        try:
            # 访问微博页面
            weibo_url = f"{self.base_url}/{post_id}"
            weibo_data['url'] = weibo_url

            await self.navigate(weibo_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 请求节流
            await self.anti_crawl.throttle_request()

            # 解析微博信息
            # 文本内容
            text_elem = await self._page.query_selector('.txt, [class*="text"]')
            if text_elem:
                weibo_data['text'] = await text_elem.inner_text()
                # 提取话题
                weibo_data['topics'] = self.parser.extract_hashtags(weibo_data['text'])
                # 提取@用户
                weibo_data['mentions'] = self.parser.extract_mentions(weibo_data['text'])
                # 提取URL
                weibo_data['urls'] = self.parser.extract_urls(weibo_data['text'])

            # 图片
            image_elements = await self._page.query_selector_all('img[src*="//wx"]')
            for img_elem in image_elements:
                img_src = await img_elem.get_attribute('src')
                if img_src:
                    weibo_data['images'].append(img_src)

            # 视频
            video_elem = await self._page.query_selector('video')
            if video_elem:
                weibo_data['video_url'] = await video_elem.get_attribute('src')

            # 作者信息
            author_elem = await self._page.query_selector('.name, [class*="name"]')
            if author_elem:
                weibo_data['author']['nickname'] = await author_elem.inner_text()

            avatar_elem = await self._page.query_selector('.avator img, [class*="avatar"] img')
            if avatar_elem:
                weibo_data['author']['avatar'] = await avatar_elem.get_attribute('src')

            # 互动数据
            stats_script = """
            () => {
                const stats = {};
                const items = document.querySelectorAll('.toolbar, [class*="toolbar"] a');
                items.forEach(item => {
                    const text = item.innerText || item.textContent;
                    if (text.includes('转发')) {
                        stats.repost = text;
                    } else if (text.includes('评论')) {
                        stats.comment = text;
                    } else if (text.includes('赞')) {
                        stats.like = text;
                    }
                });
                return stats;
            }
            """
            stats = await self._page.evaluate(stats_script)

            if stats:
                if 'repost' in stats:
                    weibo_data['repost_count'] = self.parser.parse_count(stats['repost'])
                if 'comment' in stats:
                    weibo_data['comment_count'] = self.parser.parse_count(stats['comment'])
                if 'like' in stats:
                    weibo_data['like_count'] = self.parser.parse_count(stats['like'])

            # 发布时间
            time_elem = await self._page.query_selector('.from, [class*="time"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                weibo_data['publish_time'] = self.parser.parse_date(time_text)

            # 来源
            source_elem = await self._page.query_selector('.from a')
            if source_elem:
                weibo_data['source'] = await source_elem.inner_text()

            # IP属地
            ip_elem = await self._page.query_selector('.from, [class*="location"]')
            if ip_elem:
                ip_text = await ip_elem.inner_text()
                if 'IP属地' in ip_text:
                    weibo_data['ip_location'] = ip_text.split('IP属地：')[-1].strip()

            # 是否转发
            repost_elem = await self._page.query_selector('.retweeted, [class*="retweeted"]')
            if repost_elem:
                weibo_data['is_repost'] = True
                # 获取转发源文本
                repost_text_elem = await repost_elem.query_selector('.txt')
                if repost_text_elem:
                    weibo_data['repost_source'] = await repost_text_elem.inner_text()

            # 计算热度
            weibo_data['heat'] = self.matcher._calculate_heat(weibo_data)

            self.logger.info(f"Collected weibo detail: {post_id}")

        except Exception as e:
            self.logger.error(f"Error getting weibo detail: {e}")

        return weibo_data

    async def get_comments(
        self,
        post_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取评论（支持嵌套回复）

        Args:
            post_id: 微博ID
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        # 确保在微博页面
        weibo_url = f"{self.base_url}/{post_id}"
        current_url = self._page.url

        if post_id not in current_url:
            await self.navigate(weibo_url)
            await asyncio.sleep(2)

        return await self.interaction.get_weibo_comments(
            self._page,
            post_id,
            max_comments,
            include_replies
        )

    async def get_topic_weibos(
        self,
        topic: str,
        max_weibos: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取话题下的微博

        Args:
            topic: 话题名称（不含#）
            max_weibos: 最大微博数
            criteria: 匹配条件

        Returns:
            微博列表
        """
        self.logger.info(f"Getting weibos for topic: #{topic}, max: {max_weibos}")

        weibos = []

        try:
            # 访问话题页
            topic_url = f"{self.base_url}/p/{topic}/super_index"
            await self.navigate(topic_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 请求节流
            await self.anti_crawl.throttle_request()

            # 滚动加载
            await self._scroll_and_load(max_weibos)

            # 解析微博列表
            weibo_elements = await self._page.query_selector_all('.card-wrap')

            for elem in weibo_elements[:max_weibos * 2]:
                try:
                    link_elem = await elem.query_selector('.from a')
                    if not link_elem:
                        continue

                    weibo_url = await link_elem.get_attribute('href')
                    weibo_id = self._extract_weibo_id(weibo_url)

                    if not weibo_id or weibo_id in self._collected_weibo_ids:
                        continue

                    # 获取微博详情
                    weibo_data = await self.get_post_detail(weibo_id)

                    if weibo_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_weibo(weibo_data, criteria)
                            if not is_match:
                                continue
                            weibo_data['match_score'] = match_score

                        weibos.append(weibo_data)
                        self._collected_weibo_ids.add(weibo_id)

                        if len(weibos) >= max_weibos:
                            break

                except Exception as e:
                    self.logger.error(f"Error parsing topic weibo: {e}")
                    continue

            self.logger.info(f"Collected {len(weibos)} weibos for topic: #{topic}")

        except Exception as e:
            self.logger.error(f"Get topic weibos failed: {e}")

        return weibos

    async def _scroll_and_load(self, target_count: int):
        """滚动加载更多内容"""
        last_height = 0
        no_change_count = 0
        max_scrolls = min(target_count // 5, 20)

        for i in range(max_scrolls):
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(2, 3))

            current_height = await self._page.evaluate("document.body.scrollHeight")

            if current_height == last_height:
                no_change_count += 1
                if no_change_count >= 2:
                    break
            else:
                no_change_count = 0
                last_height = current_height

    def _extract_weibo_id(self, url: str) -> Optional[str]:
        """从URL中提取微博ID"""
        try:
            # 微博URL格式: /123456789/ABC123DEF
            if '/status/' in url:
                weibo_id = url.split('/status/')[-1].split('?')[0]
                return weibo_id
            # 短链接格式
            parts = url.strip('/').split('/')
            if len(parts) >= 2:
                return parts[-1]
            return None
        except:
            return None


# 便捷函数
async def search_weibo(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：搜索微博

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        微博列表
    """
    spider = WeiboSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


async def get_weibo_hot_search(
    max_results: int = 50,
    headless: bool = True
) -> List[Dict[str, Any]]:
    """
    便捷函数：获取微博热搜

    Args:
        max_results: 最大结果数
        headless: 是否无头模式

    Returns:
        热搜列表
    """
    spider = WeiboSpider(headless=headless)

    async with spider.session():
        results = await spider.get_hot_search(max_results)
        return results


if __name__ == "__main__":
    # 测试代码
    async def test_weibo_spider():
        spider = WeiboSpider(headless=False)

        async with spider.session():
            # 测试热搜
            print("Testing hot search...")
            hot_search = await spider.get_hot_search(max_results=10)

            for item in hot_search:
                print(f"\n{item['rank']}. {item['keyword']} - Heat: {item['heat']}")

            # 测试搜索
            if hot_search:
                keyword = hot_search[0]['keyword']
                print(f"\nSearching for: {keyword}")
                weibos = await spider.search(keyword, max_results=5)

                for weibo in weibos:
                    print(f"\nWeibo: {weibo.get('text', '')[:50]}...")
                    print(f"Author: {weibo.get('author', {}).get('nickname')}")
                    print(f"Reposts: {weibo.get('repost_count')}")
                    print(f"Comments: {weibo.get('comment_count')}")

    # 运行测试
    # asyncio.run(test_weibo_spider())
