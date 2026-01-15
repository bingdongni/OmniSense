"""
Xiaohongshu (小红书/Little Red Book) Spider Implementation
完整的小红书平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 关键词搜索、用户主页、标签搜索、笔记详情
2. Anti-Crawl Layer: 反反爬层 - 移动端模拟、设备指纹、签名算法
3. Matcher Layer: 智能匹配层 - 标签匹配、种草内容识别、互动质量评估
4. Interaction Layer: 互动处理层 - 评论、点赞、收藏、创作者档案、互动分析
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


class XiaohongshuAntiCrawl:
    """
    小红书反反爬处理器
    Layer 2: Anti-Crawl - 移动端模拟、设备指纹、签名生成
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger
        self._device_id = None
        self._fp_cache = {}
        self._signature_cache = {}

    async def initialize(self, page: Page):
        """初始化反爬措施"""
        await self._inject_mobile_fingerprint(page)
        await self._inject_webdriver_evasion(page)
        await self._inject_shield_bypass(page)
        await self._inject_api_signature(page)

    async def _inject_mobile_fingerprint(self, page: Page):
        """注入移动端设备指纹"""
        # 生成随机设备ID
        self._device_id = self._generate_device_id()

        # 小红书主要是移动端，需要模拟移动设备
        mobile_script = f"""
        // Mobile device fingerprint
        window._device_id = '{self._device_id}';
        window._platform = 'iOS';

        // Override user agent
        Object.defineProperty(navigator, 'userAgent', {{
            get: () => 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1 Edg/120.0.0.0 XiaoHongShu/8.1.0'
        }});

        // Mobile-specific properties
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: () => 5
        }});

        Object.defineProperty(screen, 'orientation', {{
            get: () => ({{
                type: 'portrait-primary',
                angle: 0
            }})
        }});

        // Device memory
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {random.choice([4, 6, 8])}
        }});

        // Hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.choice([6, 8])}
        }});

        // Platform
        Object.defineProperty(navigator, 'platform', {{
            get: () => 'iPhone'
        }});

        // Connection
        Object.defineProperty(navigator, 'connection', {{
            get: () => ({{
                effectiveType: '4g',
                downlink: 10,
                rtt: 50
            }})
        }});
        """
        await page.add_init_script(mobile_script)
        self.logger.debug(f"Injected mobile fingerprint: {self._device_id}")

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
                Promise.resolve({ state: 'default' }) :
                originalQuery(parameters)
        );

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en']
        });

        // Battery API (mobile)
        navigator.getBattery = () => Promise.resolve({
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 0.85
        });
        """
        await page.add_init_script(evasion_script)

    async def _inject_shield_bypass(self, page: Page):
        """注入小红书Shield反爬绕过"""
        shield_script = """
        // Bypass Xiaohongshu Shield detection
        window._webmsxyw = function(e) {
            // Mock shield encryption
            return btoa(e);
        };

        // Mock shield token generator
        window._shield = {
            run: function(data) {
                const timestamp = Date.now();
                const random = Math.random().toString(36).substring(2);
                return btoa(JSON.stringify({
                    timestamp: timestamp,
                    data: data,
                    token: random
                }));
            }
        };

        // Mock XHR interceptor for signature injection
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url) {
            this._url = url;
            return originalOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function(data) {
            // Add shield headers
            if (this._url && this._url.includes('/api/')) {
                const timestamp = Date.now().toString();
                this.setRequestHeader('X-S', timestamp);
                this.setRequestHeader('X-T', timestamp);
                this.setRequestHeader('X-S-Common', btoa('{"platform":"web"}'));
            }
            return originalSend.apply(this, arguments);
        };
        """
        await page.add_init_script(shield_script)

    async def _inject_api_signature(self, page: Page):
        """注入API签名生成"""
        signature_script = """
        // XHS API signature generator
        window._xhsSignature = function(url, data) {
            // Simplified signature algorithm
            const timestamp = Date.now();
            const nonce = Math.random().toString(36).substring(2, 15);
            const str = url + JSON.stringify(data) + timestamp + nonce;

            // Simple hash function
            let hash = 0;
            for (let i = 0; i < str.length; i++) {
                const char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }

            return {
                'X-Sign': Math.abs(hash).toString(16),
                'X-T': timestamp.toString(),
                'X-S': btoa(nonce)
            };
        };
        """
        await page.add_init_script(signature_script)

    def _generate_device_id(self) -> str:
        """生成随机设备ID"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789abcdef', k=16))
        return hashlib.md5(f"{timestamp}{random_str}".encode()).hexdigest()

    async def random_scroll_behavior(self, page: Page, duration: float = 3.0):
        """模拟移动端滑动行为"""
        viewport_height = page.viewport_size['height']
        total_height = await page.evaluate("document.body.scrollHeight")

        scroll_steps = random.randint(5, 10)
        step_duration = duration / scroll_steps

        for _ in range(scroll_steps):
            # 随机滑动距离（移动端滑动更小）
            scroll_distance = random.randint(80, viewport_height // 3)
            current_position = await page.evaluate("window.pageYOffset")
            new_position = min(current_position + scroll_distance, total_height - viewport_height)

            # 平滑滚动
            await page.evaluate(f"window.scrollTo({{top: {new_position}, behavior: 'smooth'}})")

            # 随机停顿
            await asyncio.sleep(step_duration + random.uniform(0, 0.5))

            # 偶尔向上滑动（移动端特征）
            if random.random() < 0.25:
                back_scroll = random.randint(30, 100)
                await page.evaluate(f"window.scrollBy({{top: -{back_scroll}, behavior: 'smooth'}})")
                await asyncio.sleep(random.uniform(0.2, 0.4))

    async def simulate_tap(self, page: Page, x: int, y: int):
        """模拟移动端点击"""
        # 移动端点击持续时间更短
        await page.mouse.move(x, y)
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.up()

    async def simulate_swipe(self, page: Page, start_y: int, end_y: int, duration: float = 0.3):
        """模拟移动端滑动"""
        viewport = page.viewport_size
        x = viewport['width'] // 2

        steps = 20
        for i in range(steps):
            progress = i / steps
            y = start_y + (end_y - start_y) * progress
            await page.mouse.move(x, y)
            await asyncio.sleep(duration / steps)


class XiaohongshuMatcher:
    """
    小红书内容匹配器
    Layer 3: Matcher - 标签匹配、种草内容识别、互动质量评估
    """

    def __init__(self):
        self.logger = logger

    async def match_note(self, note: Dict[str, Any], criteria: Dict[str, Any]) -> tuple[bool, float]:
        """
        匹配笔记内容

        Args:
            note: 笔记数据
            criteria: 匹配条件 (keywords, tags, seed_content_detection, etc.)

        Returns:
            (is_match, match_score)
        """
        if not criteria:
            return True, 1.0

        score = 0.0
        weights = {
            'title': 0.25,
            'description': 0.25,
            'tags': 0.25,
            'seed_content': 0.15,
            'engagement_quality': 0.10
        }

        # 关键词匹配
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]

            # 标题匹配
            if note.get('title'):
                title_matches = sum(1 for kw in keywords if kw.lower() in note['title'].lower())
                score += (title_matches / len(keywords)) * weights['title']

            # 描述匹配
            if note.get('description'):
                desc_matches = sum(1 for kw in keywords if kw.lower() in note['description'].lower())
                score += (desc_matches / len(keywords)) * weights['description']

        # 标签匹配
        if 'tags' in criteria:
            required_tags = criteria['tags']
            if isinstance(required_tags, str):
                required_tags = [required_tags]

            if note.get('tags'):
                note_tags = [tag.lower() for tag in note['tags']]
                tag_matches = sum(1 for tag in required_tags if tag.lower() in note_tags)
                score += (tag_matches / len(required_tags)) * weights['tags']

        # 种草内容识别
        if criteria.get('detect_seed_content', False):
            seed_score = self._detect_seed_content(note)
            score += seed_score * weights['seed_content']

        # 互动质量评估
        if criteria.get('engagement_quality', False):
            engagement_score = self._evaluate_engagement_quality(note)
            score += engagement_score * weights['engagement_quality']

        # 互动量过滤
        if 'min_likes' in criteria:
            if note.get('like_count', 0) < criteria['min_likes']:
                return False, 0.0

        if 'min_collects' in criteria:
            if note.get('collect_count', 0) < criteria['min_collects']:
                return False, 0.0

        # 时间过滤
        if 'min_date' in criteria:
            note_date = note.get('publish_time')
            if note_date and isinstance(note_date, datetime):
                min_date = criteria['min_date']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)
                if note_date < min_date:
                    return False, 0.0

        # 归一化分数
        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0

        # 匹配阈值
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score

    def _detect_seed_content(self, note: Dict[str, Any]) -> float:
        """检测种草内容特征"""
        score = 0.0

        # 种草关键词
        seed_keywords = [
            '推荐', '安利', '种草', '好用', '测评',
            '分享', '必买', '回购', '值得', '建议',
            'recommend', 'review', 'must-have'
        ]

        text = (note.get('title', '') + ' ' + note.get('description', '')).lower()

        # 检查种草关键词
        keyword_matches = sum(1 for kw in seed_keywords if kw in text)
        score += min(keyword_matches / 5, 1.0) * 0.4

        # 检查是否有产品链接
        if note.get('product_links') or note.get('poi_info'):
            score += 0.3

        # 检查图片数量（种草内容通常多图）
        image_count = len(note.get('images', []))
        if image_count >= 4:
            score += 0.3
        elif image_count >= 2:
            score += 0.15

        return min(score, 1.0)

    def _evaluate_engagement_quality(self, note: Dict[str, Any]) -> float:
        """评估互动质量"""
        like_count = note.get('like_count', 0)
        collect_count = note.get('collect_count', 0)
        comment_count = note.get('comment_count', 0)
        share_count = note.get('share_count', 0)

        if like_count == 0:
            return 0.0

        # 收藏率（高质量内容收藏率高）
        collect_rate = collect_count / like_count if like_count > 0 else 0

        # 评论率
        comment_rate = comment_count / like_count if like_count > 0 else 0

        # 分享率
        share_rate = share_count / like_count if like_count > 0 else 0

        # 综合质量分
        quality_score = (
            min(collect_rate * 2, 1.0) * 0.4 +
            min(comment_rate * 5, 1.0) * 0.3 +
            min(share_rate * 10, 1.0) * 0.3
        )

        return quality_score


class XiaohongshuInteraction:
    """
    小红书互动处理器
    Layer 4: Interaction - 评论、点赞、收藏、创作者档案
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def get_note_comments(
        self,
        page: Page,
        note_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取笔记评论

        Args:
            page: Playwright页面对象
            note_id: 笔记ID
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        comments = []

        try:
            # 等待评论区加载
            comment_selector = '.comment-item, [class*="comment"]'
            try:
                await page.wait_for_selector(comment_selector, timeout=5000)
            except PlaywrightTimeoutError:
                self.logger.warning(f"No comments found for note {note_id}")
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

            self.logger.info(f"Collected {len(comments)} comments for note {note_id}")

        except Exception as e:
            self.logger.error(f"Error getting comments: {e}")

        return comments

    async def _scroll_to_load_comments(self, page: Page, target_count: int):
        """滚动加载更多评论"""
        last_count = 0
        no_change_count = 0
        max_scrolls = min(target_count // 10, 20)

        for _ in range(max_scrolls):
            # 滚动到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(1, 2))

            # 检查评论数量
            current_count = await page.evaluate(
                """() => document.querySelectorAll('.comment-item, [class*="comment"]').length"""
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
                'ip_location': None
            }

            # 用户信息
            username_elem = await element.query_selector('.username, [class*="username"], [class*="nickname"]')
            if username_elem:
                comment_data['user']['nickname'] = await username_elem.inner_text()

            avatar_elem = await element.query_selector('.avatar img, [class*="avatar"] img')
            if avatar_elem:
                comment_data['user']['avatar'] = await avatar_elem.get_attribute('src')

            # 评论内容
            text_elem = await element.query_selector('.content, [class*="content"], [class*="text"]')
            if text_elem:
                comment_data['text'] = await text_elem.inner_text()

            # 点赞数
            like_elem = await element.query_selector('.like-count, [class*="like"]')
            if like_elem:
                like_text = await like_elem.inner_text()
                comment_data['like_count'] = self.spider.parser.parse_count(like_text)

            # 发布时间
            time_elem = await element.query_selector('.time, [class*="time"], [class*="date"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                comment_data['publish_time'] = self.spider.parser.parse_date(time_text)

            # IP属地
            ip_elem = await element.query_selector('.ip-location, [class*="location"]')
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
            more_replies_btn = await comment_element.query_selector('.view-more-reply, [class*="more-reply"]')
            if more_replies_btn:
                await more_replies_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

            # 解析回复
            reply_elements = await comment_element.query_selector_all('.reply-item, [class*="reply"]')

            for reply_elem in reply_elements[:10]:
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
            'note_count': 0,
            'like_count': 0,
            'collect_count': 0,
            'xiaohongshu_id': None,
            'verified': False,
            'verification_type': None,
            'ip_location': None,
            'gender': None,
            'age': None,
            'tags': [],
            'engagement_rate': 0.0
        }

        try:
            # 访问用户主页
            user_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            await page.goto(user_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 解析用户信息
            # 昵称
            nickname_elem = await page.query_selector('.username, [class*="username"], [class*="nickname"]')
            if nickname_elem:
                creator_info['nickname'] = await nickname_elem.inner_text()

            # 头像
            avatar_elem = await page.query_selector('.avatar img, [class*="avatar"] img')
            if avatar_elem:
                creator_info['avatar'] = await avatar_elem.get_attribute('src')

            # 签名
            signature_elem = await page.query_selector('.signature, [class*="signature"], [class*="desc"]')
            if signature_elem:
                creator_info['signature'] = await signature_elem.inner_text()

            # 统计数据
            stats_script = """
            () => {
                const stats = {};
                const items = document.querySelectorAll('.user-info .count, [class*="count"]');
                items.forEach(item => {
                    const text = item.innerText || item.textContent;
                    if (text.includes('关注')) {
                        stats.following = text;
                    } else if (text.includes('粉丝')) {
                        stats.followers = text;
                    } else if (text.includes('获赞')) {
                        stats.likes = text;
                    } else if (text.includes('收藏')) {
                        stats.collects = text;
                    }
                });
                return stats;
            }
            """
            stats = await page.evaluate(stats_script)

            if stats:
                if 'following' in stats:
                    creator_info['following_count'] = self.spider.parser.parse_count(stats['following'])
                if 'followers' in stats:
                    creator_info['follower_count'] = self.spider.parser.parse_count(stats['followers'])
                if 'likes' in stats:
                    creator_info['like_count'] = self.spider.parser.parse_count(stats['likes'])
                if 'collects' in stats:
                    creator_info['collect_count'] = self.spider.parser.parse_count(stats['collects'])

            # 小红书号
            xhs_id_elem = await page.query_selector('.xhs-id, [class*="redId"]')
            if xhs_id_elem:
                xhs_id_text = await xhs_id_elem.inner_text()
                creator_info['xiaohongshu_id'] = xhs_id_text.replace('小红书号：', '').strip()

            # 认证信息
            verified_elem = await page.query_selector('.verified, [class*="verified"]')
            if verified_elem:
                creator_info['verified'] = True
                verification_text = await verified_elem.inner_text()
                creator_info['verification_type'] = verification_text

            # IP属地
            ip_elem = await page.query_selector('.ip-location, [class*="location"]')
            if ip_elem:
                ip_text = await ip_elem.inner_text()
                creator_info['ip_location'] = ip_text.replace('IP属地：', '').strip()

            # 标签
            tag_elements = await page.query_selector_all('.user-tag, [class*="tag"]')
            for tag_elem in tag_elements:
                tag_text = await tag_elem.inner_text()
                if tag_text:
                    creator_info['tags'].append(tag_text.strip())

            # 笔记数量
            note_count = await page.evaluate(
                """() => document.querySelectorAll('.note-item, [class*="note"]').length"""
            )
            creator_info['note_count'] = note_count

            # 计算互动率
            if creator_info['follower_count'] > 0 and creator_info['note_count'] > 0:
                avg_engagement = (creator_info['like_count'] + creator_info['collect_count']) / creator_info['note_count']
                creator_info['engagement_rate'] = (avg_engagement / creator_info['follower_count']) * 100

            self.logger.info(f"Collected creator info for {user_id}")

        except Exception as e:
            self.logger.error(f"Error getting creator info: {e}")

        return creator_info

    async def analyze_engagement(self, note: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析笔记互动数据

        Args:
            note: 笔记数据

        Returns:
            互动分析结果
        """
        analysis = {
            'total_engagement': 0,
            'engagement_rate': 0.0,
            'like_rate': 0.0,
            'collect_rate': 0.0,
            'comment_rate': 0.0,
            'share_rate': 0.0,
            'quality_score': 0.0,
            'virality_score': 0.0
        }

        try:
            like_count = note.get('like_count', 0)
            collect_count = note.get('collect_count', 0)
            comment_count = note.get('comment_count', 0)
            share_count = note.get('share_count', 0)
            view_count = note.get('view_count', 1)  # 避免除零

            # 总互动量
            analysis['total_engagement'] = like_count + collect_count + comment_count + share_count

            # 互动率
            if view_count > 0:
                analysis['engagement_rate'] = (analysis['total_engagement'] / view_count) * 100
                analysis['like_rate'] = (like_count / view_count) * 100
                analysis['collect_rate'] = (collect_count / view_count) * 100
                analysis['comment_rate'] = (comment_count / view_count) * 100
                analysis['share_rate'] = (share_count / view_count) * 100

            # 质量分（收藏和评论占比高说明质量好）
            if analysis['total_engagement'] > 0:
                quality_weight = (collect_count * 2 + comment_count * 1.5) / analysis['total_engagement']
                analysis['quality_score'] = min(quality_weight * 100, 100)

            # 传播力（分享占比高说明传播力强）
            if analysis['total_engagement'] > 0:
                virality_weight = (share_count * 3 + like_count) / analysis['total_engagement']
                analysis['virality_score'] = min(virality_weight * 100, 100)

        except Exception as e:
            self.logger.error(f"Error analyzing engagement: {e}")

        return analysis


class XiaohongshuSpider(BaseSpider):
    """
    小红书爬虫主类
    Layer 1: Spider - 完整的爬取功能实现

    功能:
    - 关键词搜索笔记
    - 用户主页爬取
    - 标签页爬取
    - 笔记详情获取（20+字段）
    - 评论采集（嵌套回复）
    - 图片/视频下载
    - 种草内容识别
    - 互动分析
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="xiaohongshu",
            headless=headless,
            proxy=proxy
        )

        # 初始化各层组件
        self.anti_crawl = XiaohongshuAntiCrawl(self)
        self.matcher = XiaohongshuMatcher()
        self.interaction = XiaohongshuInteraction(self)

        # 小红书特定配置
        self.base_url = "https://www.xiaohongshu.com"
        self.search_url = f"{self.base_url}/search_result"
        self.mobile_simulation = True

        # 缓存
        self._collected_note_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()

        # 初始化反爬
        await self.anti_crawl.initialize(self._page)

        self.logger.info("Xiaohongshu spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """
        登录小红书（支持扫码或Cookie登录）

        Args:
            username: 用户名（可选）
            password: 密码（可选）

        Returns:
            登录是否成功
        """
        try:
            # 访问小红书首页
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
            login_btn_selector = '.login-btn, [class*="login"]'
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
            user_info = await self._page.query_selector('.user-info, [class*="user"]')
            return user_info is not None
        except:
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "note",
        sort_type: str = "general",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索笔记

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型 (note/user/topic)
            sort_type: 排序方式 (general/time/popular)
            criteria: 匹配条件

        Returns:
            笔记列表
        """
        self.logger.info(f"Searching for: {keyword}, type: {search_type}, max: {max_results}")

        results = []

        try:
            # 构建搜索URL
            search_params = {
                'keyword': keyword,
                'type': search_type,
                'sort': sort_type
            }
            search_url = f"{self.search_url}?{urlencode(search_params)}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载更多内容
            await self._scroll_and_load(max_results)

            # 解析笔记列表
            note_elements = await self._page.query_selector_all('.note-item, [class*="note"]')

            for elem in note_elements[:max_results * 2]:
                try:
                    # 提取笔记ID和URL
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    note_url = await link_elem.get_attribute('href')
                    if not note_url:
                        continue

                    note_id = self._extract_note_id(note_url)
                    if not note_id or note_id in self._collected_note_ids:
                        continue

                    # 获取笔记详情
                    note_data = await self.get_post_detail(note_id)

                    if note_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_note(note_data, criteria)
                            if not is_match:
                                continue
                            note_data['match_score'] = match_score

                        results.append(note_data)
                        self._collected_note_ids.add(note_id)

                        if len(results) >= max_results:
                            break

                    # 随机延迟
                    await asyncio.sleep(random.uniform(0.5, 1))

                except Exception as e:
                    self.logger.error(f"Error parsing note: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} notes for keyword: {keyword}")

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def search_by_tag(
        self,
        tag: str,
        max_results: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        按标签搜索笔记

        Args:
            tag: 标签名称
            max_results: 最大结果数
            criteria: 匹配条件

        Returns:
            笔记列表
        """
        self.logger.info(f"Searching by tag: #{tag}, max: {max_results}")

        results = []

        try:
            # 访问标签页
            tag_url = f"{self.base_url}/page/topics/{tag}"
            await self.navigate(tag_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            await self._scroll_and_load(max_results)

            # 解析笔记列表
            note_elements = await self._page.query_selector_all('.note-item, [class*="note"]')

            for elem in note_elements[:max_results * 2]:
                try:
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    note_url = await link_elem.get_attribute('href')
                    note_id = self._extract_note_id(note_url)

                    if not note_id or note_id in self._collected_note_ids:
                        continue

                    # 获取笔记详情
                    note_data = await self.get_post_detail(note_id)

                    if note_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_note(note_data, criteria)
                            if not is_match:
                                continue
                            note_data['match_score'] = match_score

                        results.append(note_data)
                        self._collected_note_ids.add(note_id)

                        if len(results) >= max_results:
                            break

                except Exception as e:
                    self.logger.error(f"Error parsing note: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} notes for tag: #{tag}")

        except Exception as e:
            self.logger.error(f"Search by tag failed: {e}")

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
        获取用户发布的笔记

        Args:
            user_id: 用户ID
            max_posts: 最大笔记数
            criteria: 匹配条件

        Returns:
            笔记列表
        """
        self.logger.info(f"Getting posts for user: {user_id}, max: {max_posts}")

        posts = []

        try:
            # 访问用户主页
            user_url = f"{self.base_url}/user/profile/{user_id}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            await self._scroll_and_load(max_posts)

            # 解析笔记列表
            note_elements = await self._page.query_selector_all('.note-item, [class*="note"]')

            for elem in note_elements[:max_posts * 2]:
                try:
                    # 获取笔记链接
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    note_url = await link_elem.get_attribute('href')
                    note_id = self._extract_note_id(note_url)

                    if not note_id or note_id in self._collected_note_ids:
                        continue

                    # 获取笔记详情
                    note_data = await self.get_post_detail(note_id)

                    if note_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_note(note_data, criteria)
                            if not is_match:
                                continue
                            note_data['match_score'] = match_score

                        posts.append(note_data)
                        self._collected_note_ids.add(note_id)

                        if len(posts) >= max_posts:
                            break

                except Exception as e:
                    self.logger.error(f"Error parsing user note: {e}")
                    continue

            self.logger.info(f"Collected {len(posts)} posts for user: {user_id}")

        except Exception as e:
            self.logger.error(f"Get user posts failed: {e}")

        return posts

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        获取笔记详情（20+字段）

        Args:
            post_id: 笔记ID

        Returns:
            笔记详细信息
        """
        self.logger.info(f"Getting note detail: {post_id}")

        note_data = {
            'content_id': post_id,
            'platform': 'xiaohongshu',
            'content_type': None,  # 'image' or 'video'
            'url': None,
            'title': None,
            'description': None,
            'cover_image': None,
            'images': [],
            'video_url': None,
            'duration': 0,
            'tags': [],
            'topics': [],
            'mentions': [],
            'author': {},
            'view_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'share_count': 0,
            'collect_count': 0,
            'publish_time': None,
            'location': None,
            'poi_info': {},
            'product_links': [],
            'is_ad': False,
            'is_seed_content': False,
            'engagement_analysis': {},
            'collected_at': datetime.now()
        }

        try:
            # 访问笔记页面
            note_url = f"{self.base_url}/explore/{post_id}"
            note_data['url'] = note_url

            await self.navigate(note_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 模拟阅读行为
            await self.anti_crawl.random_scroll_behavior(self._page, duration=2)

            # 解析笔记信息
            # 标题
            title_elem = await self._page.query_selector('.title, [class*="title"]')
            if title_elem:
                note_data['title'] = await title_elem.inner_text()

            # 描述
            desc_elem = await self._page.query_selector('.desc, [class*="desc"], [class*="content"]')
            if desc_elem:
                note_data['description'] = await desc_elem.inner_text()
                # 提取标签
                note_data['tags'] = self.parser.extract_hashtags(note_data['description'])
                # 提取@用户
                note_data['mentions'] = self.parser.extract_mentions(note_data['description'])

            # 封面图
            cover_elem = await self._page.query_selector('.cover img, [class*="cover"] img')
            if cover_elem:
                note_data['cover_image'] = await cover_elem.get_attribute('src')

            # 判断内容类型（图片或视频）
            video_elem = await self._page.query_selector('video')
            if video_elem:
                note_data['content_type'] = 'video'
                note_data['video_url'] = await video_elem.get_attribute('src')

                # 视频时长
                duration_elem = await self._page.query_selector('.duration, [class*="duration"]')
                if duration_elem:
                    duration_text = await duration_elem.inner_text()
                    note_data['duration'] = self.parser.parse_duration(duration_text)
            else:
                note_data['content_type'] = 'image'

                # 图片列表
                image_elements = await self._page.query_selector_all('.image-item img, [class*="image"] img')
                for img_elem in image_elements:
                    img_src = await img_elem.get_attribute('src')
                    if img_src:
                        note_data['images'].append(img_src)

            # 作者信息
            author_elem = await self._page.query_selector('.author, [class*="author"]')
            if author_elem:
                author_name_elem = await author_elem.query_selector('.username, [class*="username"]')
                if author_name_elem:
                    note_data['author']['nickname'] = await author_name_elem.inner_text()

                author_avatar_elem = await author_elem.query_selector('img')
                if author_avatar_elem:
                    note_data['author']['avatar'] = await author_avatar_elem.get_attribute('src')

                author_id_elem = await author_elem.query_selector('a')
                if author_id_elem:
                    author_url = await author_id_elem.get_attribute('href')
                    if author_url:
                        note_data['author']['user_id'] = self._extract_user_id(author_url)

            # 互动数据
            stats_script = """
            () => {
                const stats = {};
                const items = document.querySelectorAll('.interaction-item, [class*="count"]');
                items.forEach(item => {
                    const text = item.innerText || item.textContent;
                    if (text.includes('点赞') || text.includes('like')) {
                        stats.likes = text.match(/\\d+/)?.[0] || '0';
                    } else if (text.includes('收藏') || text.includes('collect')) {
                        stats.collects = text.match(/\\d+/)?.[0] || '0';
                    } else if (text.includes('评论') || text.includes('comment')) {
                        stats.comments = text.match(/\\d+/)?.[0] || '0';
                    } else if (text.includes('分享') || text.includes('share')) {
                        stats.shares = text.match(/\\d+/)?.[0] || '0';
                    }
                });
                return stats;
            }
            """
            stats = await self._page.evaluate(stats_script)

            if stats:
                if 'likes' in stats:
                    note_data['like_count'] = self.parser.parse_count(stats['likes'])
                if 'collects' in stats:
                    note_data['collect_count'] = self.parser.parse_count(stats['collects'])
                if 'comments' in stats:
                    note_data['comment_count'] = self.parser.parse_count(stats['comments'])
                if 'shares' in stats:
                    note_data['share_count'] = self.parser.parse_count(stats['shares'])

            # 发布时间
            time_elem = await self._page.query_selector('.time, [class*="time"], [class*="date"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                note_data['publish_time'] = self.parser.parse_date(time_text)

            # 位置信息
            location_elem = await self._page.query_selector('.location, [class*="location"]')
            if location_elem:
                note_data['location'] = await location_elem.inner_text()

            # POI信息
            poi_elem = await self._page.query_selector('.poi, [class*="poi"]')
            if poi_elem:
                poi_name_elem = await poi_elem.query_selector('.name')
                if poi_name_elem:
                    note_data['poi_info']['name'] = await poi_name_elem.inner_text()

            # 话题标签
            topic_elements = await self._page.query_selector_all('.topic, [class*="topic"]')
            for topic_elem in topic_elements:
                topic_text = await topic_elem.inner_text()
                if topic_text:
                    note_data['topics'].append(topic_text.strip())

            # 产品链接
            product_elements = await self._page.query_selector_all('.product-link, [class*="product"]')
            for product_elem in product_elements:
                product_url = await product_elem.get_attribute('href')
                if product_url:
                    note_data['product_links'].append(product_url)

            # 是否广告
            ad_tag = await self._page.query_selector('.ad-tag, [class*="ad"]')
            note_data['is_ad'] = ad_tag is not None

            # 检测是否种草内容
            note_data['is_seed_content'] = self.matcher._detect_seed_content(note_data) > 0.5

            # 互动分析
            note_data['engagement_analysis'] = await self.interaction.analyze_engagement(note_data)

            self.logger.info(f"Collected note detail: {post_id}")

        except Exception as e:
            self.logger.error(f"Error getting note detail: {e}")

        return note_data

    async def get_comments(
        self,
        post_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取评论（支持嵌套回复）

        Args:
            post_id: 笔记ID
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        # 确保在笔记页面
        note_url = f"{self.base_url}/explore/{post_id}"
        current_url = self._page.url

        if post_id not in current_url:
            await self.navigate(note_url)
            await asyncio.sleep(2)

        return await self.interaction.get_note_comments(
            self._page,
            post_id,
            max_comments,
            include_replies
        )

    async def download_images(self, note_id: str) -> List[Path]:
        """
        下载笔记的所有图片

        Args:
            note_id: 笔记ID

        Returns:
            下载的文件路径列表
        """
        downloaded_files = []

        try:
            # 获取笔记详情
            note_data = await self.get_post_detail(note_id)

            if note_data and note_data.get('images'):
                for idx, img_url in enumerate(note_data['images']):
                    filename = f"xhs_{note_id}_{idx}.jpg"
                    filepath = await self.download_media(img_url, filename)
                    if filepath:
                        downloaded_files.append(filepath)

            self.logger.info(f"Downloaded {len(downloaded_files)} images for note {note_id}")

        except Exception as e:
            self.logger.error(f"Error downloading images: {e}")

        return downloaded_files

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

    def _extract_note_id(self, url: str) -> Optional[str]:
        """从URL中提取笔记ID"""
        try:
            # 小红书笔记URL格式: /explore/63abc123def456789
            if '/explore/' in url:
                note_id = url.split('/explore/')[-1].split('?')[0]
                return note_id
            return None
        except:
            return None

    def _extract_user_id(self, url: str) -> Optional[str]:
        """从URL中提取用户ID"""
        try:
            # 小红书用户URL格式: /user/profile/5abc123def456
            if '/user/profile/' in url:
                user_id = url.split('/user/profile/')[-1].split('?')[0]
                return user_id
            return None
        except:
            return None


# 便捷函数
async def search_xiaohongshu_notes(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：搜索小红书笔记

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        笔记列表
    """
    spider = XiaohongshuSpider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


async def get_xiaohongshu_user_notes(
    user_id: str,
    max_notes: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：获取小红书用户笔记

    Args:
        user_id: 用户ID
        max_notes: 最大笔记数
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        笔记列表
    """
    spider = XiaohongshuSpider(headless=headless)

    async with spider.session():
        results = await spider.get_user_posts(user_id, max_notes, criteria=criteria)
        return results


if __name__ == "__main__":
    # 测试代码
    async def test_xiaohongshu_spider():
        spider = XiaohongshuSpider(headless=False)

        async with spider.session():
            # 测试搜索
            print("Testing search...")
            notes = await spider.search("护肤", max_results=5)

            for note in notes:
                print(f"\nNote: {note.get('title')}")
                print(f"Author: {note.get('author', {}).get('nickname')}")
                print(f"Likes: {note.get('like_count')}")
                print(f"Collects: {note.get('collect_count')}")
                print(f"Is seed content: {note.get('is_seed_content')}")
                print(f"URL: {note.get('url')}")

                # 测试获取评论
                if note.get('content_id'):
                    print(f"\nGetting comments for {note['content_id']}...")
                    comments = await spider.get_comments(note['content_id'], max_comments=10)
                    print(f"Total comments: {len(comments)}")

                    for comment in comments[:3]:
                        print(f"  - {comment.get('user', {}).get('nickname')}: {comment.get('text')}")

    # 运行测试
    # asyncio.run(test_xiaohongshu_spider())
