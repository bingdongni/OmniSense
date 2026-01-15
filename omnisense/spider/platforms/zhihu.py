"""
Zhihu (知乎) Spider Implementation
完整的知乎平台爬虫实现 - 企业级4层架构

架构说明:
- Layer 1: Spider Layer - 核心爬虫功能
- Layer 2: Anti-Crawl Layer - 反爬虫机制和安全防护
- Layer 3: Matcher Layer - 智能匹配和数据过滤
- Layer 4: Interaction Layer - 用户交互操作
"""

import asyncio
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, parse_qs

from omnisense.spider.base import BaseSpider


# ============================================================================
# 数据模型定义
# ============================================================================

class ZhihuContentType(Enum):
    """知乎内容类型"""
    QUESTION = "question"
    ANSWER = "answer"
    ARTICLE = "article"
    PIN = "pin"  # 想法
    COLUMN = "column"  # 专栏


class ZhihuSortType(Enum):
    """知乎排序类型"""
    DEFAULT = "default"  # 默认排序
    TIME = "created"  # 按时间
    HEAT = "score"  # 按热度


@dataclass
class ZhihuQuestion:
    """知乎问题信息"""
    question_id: str
    title: str
    url: str

    # 统计信息
    answer_count: int = 0
    follower_count: int = 0
    view_count: int = 0

    # 内容信息
    detail: str = ""
    topics: List[str] = field(default_factory=list)

    # 时间信息
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None


@dataclass
class ZhihuAnswer:
    """知乎回答信息"""
    answer_id: str
    question_id: str
    url: str

    # 作者信息
    author_name: str = ""
    author_id: str = ""
    author_headline: str = ""

    # 内容信息
    content: str = ""
    excerpt: str = ""

    # 统计信息
    voteup_count: int = 0
    comment_count: int = 0
    thanks_count: int = 0

    # 时间信息
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None

    # 是否精选
    is_featured: bool = False


@dataclass
class ZhihuArticle:
    """知乎文章信息"""
    article_id: str
    title: str
    url: str

    # 作者信息
    author_name: str = ""
    author_id: str = ""

    # 内容信息
    content: str = ""
    excerpt: str = ""

    # 统计信息
    voteup_count: int = 0
    comment_count: int = 0

    # 专栏信息
    column_id: Optional[str] = None
    column_title: Optional[str] = None

    # 时间信息
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None


@dataclass
class ZhihuUser:
    """知乎用户信息"""
    user_id: str
    url_token: str
    name: str

    # 个人信息
    headline: str = ""
    description: str = ""
    avatar_url: Optional[str] = None

    # 统计信息
    follower_count: int = 0
    following_count: int = 0
    answer_count: int = 0
    question_count: int = 0
    article_count: int = 0
    voteup_count: int = 0

    # 认证信息
    badge: Optional[str] = None
    is_org: bool = False

    # 专业领域
    business: Optional[str] = None
    employment: Optional[str] = None
    education: Optional[str] = None
    locations: List[str] = field(default_factory=list)


# ============================================================================
# Layer 2: Anti-Crawl Layer - 反爬虫机制
# ============================================================================

class ZhihuAntiCrawl:
    """知乎反爬虫处理层"""

    # 30+ User-Agent池
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Mobile Chrome
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        # Mobile Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Additional variants
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    ]

    def __init__(self, logger):
        self.logger = logger
        self.request_count = 0
        self.last_request_time = 0
        self.session_id = self._generate_session_id()
        self.d_c0 = self._generate_d_c0()
        self.captcha_count = 0
        self.blocked_count = 0

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = int(time.time() * 1000)
        random_part = ''.join(random.choices('0123456789abcdef', k=16))
        return f"{timestamp}-{random_part}"

    def _generate_d_c0(self) -> str:
        """生成知乎d_c0 cookie"""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
        return ''.join(random.choices(chars, k=108))

    def generate_x_zse_86(self, url: str, params: Dict[str, Any]) -> str:
        """生成知乎x-zse-86签名

        知乎的反爬虫签名机制，用于验证请求合法性
        """
        # 简化版签名算法（实际需要逆向JS）
        timestamp = str(int(time.time() * 1000))
        param_str = json.dumps(params, separators=(',', ':'))
        sign_str = f"{url}{param_str}{timestamp}{self.d_c0}"

        # MD5签名
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

        # 知乎格式: 2.0_<sign>
        return f"2.0_{sign}"

    def generate_x_zse_96(self, data: str) -> str:
        """生成知乎x-zse-96加密参数

        用于POST请求的数据加密
        """
        # 简化版加密算法
        timestamp = str(int(time.time()))
        encrypt_str = f"{data}{timestamp}{self.d_c0}"
        encrypted = hashlib.sha256(encrypt_str.encode('utf-8')).hexdigest()
        return f"2.0_{encrypted}"

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.USER_AGENTS)

    def get_request_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """获取完整的请求头"""
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }

        if referer:
            headers['Referer'] = referer
            headers['Sec-Fetch-Site'] = 'same-origin'

        return headers

    def get_api_headers(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """获取API请求头（包含签名）"""
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.zhihu.com/',
            'x-api-version': '3.0.91',
            'x-app-za': 'OS=Web',
        }

        # 添加签名
        if params:
            headers['x-zse-86'] = self.generate_x_zse_86(url, params)

        return headers

    async def smart_delay(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """智能延迟 - 模拟人类行为"""
        self.request_count += 1

        # 基础延迟
        base_delay = random.uniform(min_delay, max_delay)

        # 根据请求频率调整
        if self.request_count % 10 == 0:
            base_delay += random.uniform(3, 8)
            self.logger.debug(f"添加额外延迟，已完成 {self.request_count} 个请求")

        # 随机波动
        jitter = random.uniform(-0.5, 0.5)
        final_delay = max(0.5, base_delay + jitter)

        await asyncio.sleep(final_delay)
        self.last_request_time = time.time()

    async def exponential_backoff(self, attempt: int, base_delay: float = 2.0) -> float:
        """指数退避算法"""
        delay = min(base_delay * (2 ** attempt), 60)
        jitter = random.uniform(0, delay * 0.1)
        total_delay = delay + jitter

        self.logger.info(f"指数退避: 尝试 {attempt}, 等待 {total_delay:.2f}秒")
        await asyncio.sleep(total_delay)
        return total_delay

    def detect_captcha(self, page_content: str) -> bool:
        """检测验证码"""
        captcha_indicators = [
            '请完成安全验证',
            '验证码',
            '滑动验证',
            'captcha',
            'zhihu-captcha',
        ]

        content_lower = page_content.lower()
        for indicator in captcha_indicators:
            if indicator.lower() in content_lower:
                self.logger.warning(f"检测到验证码: {indicator}")
                return True
        return False

    def detect_blocked(self, page_content: str) -> bool:
        """检测是否被封禁"""
        block_indicators = [
            '访问异常',
            '请求过于频繁',
            '系统检测到异常访问',
            'blocked',
            '403 Forbidden',
        ]

        content_lower = page_content.lower()
        for indicator in block_indicators:
            if indicator.lower() in content_lower:
                self.logger.error(f"访问被阻止: {indicator}")
                self.blocked_count += 1
                return True
        return False

    async def handle_captcha(self, page) -> bool:
        """处理验证码"""
        self.captcha_count += 1
        self.logger.warning(f"遇到验证码 (次数: {self.captcha_count})")

        # 等待更长时间
        await asyncio.sleep(random.uniform(10, 20))

        # 刷新页面重试
        try:
            await page.reload()
            await asyncio.sleep(3)

            content = await page.content()
            if not self.detect_captcha(content):
                self.logger.info("验证码已绕过")
                return True
        except Exception as e:
            self.logger.error(f"处理验证码失败: {e}")

        return False

    def should_rotate_session(self) -> bool:
        """判断是否需要轮换会话"""
        if self.request_count >= 50 or self.captcha_count >= 3:
            return True
        return False

    def reset_session(self):
        """重置会话"""
        self.logger.info("重置会话...")
        self.session_id = self._generate_session_id()
        self.d_c0 = self._generate_d_c0()
        self.request_count = 0
        self.captcha_count = 0


# ============================================================================
# Layer 3: Matcher Layer - 智能匹配和过滤
# ============================================================================

class ZhihuMatcher:
    """知乎内容匹配和过滤层"""

    def __init__(self, logger):
        self.logger = logger

    def filter_by_voteup(
        self,
        items: List[Dict[str, Any]],
        min_voteup: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """按点赞数过滤"""
        if min_voteup is None:
            return items

        filtered = [
            item for item in items
            if item.get('voteup_count', 0) >= min_voteup
        ]

        self.logger.info(f"点赞数过滤: {len(items)} -> {len(filtered)} 条内容")
        return filtered

    def filter_by_follower(
        self,
        items: List[Dict[str, Any]],
        min_followers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """按关注数过滤"""
        if min_followers is None:
            return items

        filtered = [
            item for item in items
            if item.get('follower_count', 0) >= min_followers
        ]

        self.logger.info(f"关注数过滤: {len(items)} -> {len(filtered)} 条内容")
        return filtered

    def filter_by_topics(
        self,
        items: List[Dict[str, Any]],
        topics: List[str]
    ) -> List[Dict[str, Any]]:
        """按话题过滤"""
        if not topics:
            return items

        topics_lower = [t.lower() for t in topics]
        filtered = []

        for item in items:
            item_topics = item.get('topics', [])
            if any(
                any(topic_filter in topic.lower() for topic_filter in topics_lower)
                for topic in item_topics
            ):
                filtered.append(item)

        self.logger.info(f"话题过滤: {len(items)} -> {len(filtered)} 条内容")
        return filtered

    def filter_by_keywords(
        self,
        items: List[Dict[str, Any]],
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """按关键词过滤标题和内容"""
        filtered = items.copy()

        # 包含关键词过滤
        if include_keywords:
            include_lower = [kw.lower() for kw in include_keywords]
            filtered = [
                item for item in filtered
                if any(
                    kw in item.get('title', '').lower() or
                    kw in item.get('content', '').lower() or
                    kw in item.get('excerpt', '').lower()
                    for kw in include_lower
                )
            ]
            self.logger.info(f"包含关键词过滤: {len(items)} -> {len(filtered)} 条内容")

        # 排除关键词过滤
        if exclude_keywords:
            exclude_lower = [kw.lower() for kw in exclude_keywords]
            filtered = [
                item for item in filtered
                if not any(
                    kw in item.get('title', '').lower() or
                    kw in item.get('content', '').lower() or
                    kw in item.get('excerpt', '').lower()
                    for kw in exclude_lower
                )
            ]
            self.logger.info(f"排除关键词过滤后: {len(filtered)} 条内容")

        return filtered

    def filter_by_professional_field(
        self,
        users: List[Dict[str, Any]],
        fields: List[str]
    ) -> List[Dict[str, Any]]:
        """按专业领域过滤用户"""
        if not fields:
            return users

        fields_lower = [f.lower() for f in fields]
        filtered = []

        for user in users:
            user_fields = [
                user.get('business', ''),
                user.get('employment', ''),
                user.get('education', ''),
                user.get('headline', '')
            ]

            if any(
                any(field_filter in field.lower() for field_filter in fields_lower)
                for field in user_fields if field
            ):
                filtered.append(user)

        self.logger.info(f"专业领域过滤: {len(users)} -> {len(filtered)} 个用户")
        return filtered

    def calculate_content_quality_score(self, item: Dict[str, Any]) -> float:
        """计算内容质量评分 (0-100)"""
        score = 0.0

        # 点赞数权重 40%
        voteup_count = item.get('voteup_count', 0)
        if voteup_count > 0:
            voteup_score = min(40, (voteup_count / 1000) * 40)
            score += voteup_score

        # 评论数权重 20%
        comment_count = item.get('comment_count', 0)
        if comment_count > 0:
            comment_score = min(20, (comment_count / 100) * 20)
            score += comment_score

        # 内容长度权重 20%
        content = item.get('content', '') or item.get('excerpt', '')
        if len(content) > 100:
            score += 20
        elif len(content) > 50:
            score += 15
        elif len(content) > 20:
            score += 10

        # 作者认证权重 10%
        if item.get('badge'):
            score += 10

        # 是否精选权重 10%
        if item.get('is_featured'):
            score += 10

        return round(score, 2)

    def calculate_user_influence_score(self, user: Dict[str, Any]) -> float:
        """计算用户影响力评分 (0-100)"""
        score = 0.0

        # 粉丝数权重 30%
        follower_count = user.get('follower_count', 0)
        if follower_count > 0:
            follower_score = min(30, (follower_count / 10000) * 30)
            score += follower_score

        # 获赞数权重 25%
        voteup_count = user.get('voteup_count', 0)
        if voteup_count > 0:
            voteup_score = min(25, (voteup_count / 50000) * 25)
            score += voteup_score

        # 回答数权重 15%
        answer_count = user.get('answer_count', 0)
        if answer_count > 0:
            answer_score = min(15, (answer_count / 500) * 15)
            score += answer_score

        # 文章数权重 10%
        article_count = user.get('article_count', 0)
        if article_count > 0:
            article_score = min(10, (article_count / 100) * 10)
            score += article_score

        # 认证权重 10%
        if user.get('badge'):
            score += 10

        # 机构账号权重 10%
        if user.get('is_org'):
            score += 10

        return round(score, 2)

    def sort_items(
        self,
        items: List[Dict[str, Any]],
        sort_by: str = "default"
    ) -> List[Dict[str, Any]]:
        """排序内容

        Args:
            sort_by: default, voteup, time, quality, comments
        """
        if sort_by == "default":
            return items

        try:
            if sort_by == "voteup":
                items.sort(key=lambda x: x.get('voteup_count', 0), reverse=True)
            elif sort_by == "time":
                items.sort(
                    key=lambda x: x.get('created_time') or datetime.min,
                    reverse=True
                )
            elif sort_by == "quality":
                items.sort(
                    key=lambda x: self.calculate_content_quality_score(x),
                    reverse=True
                )
            elif sort_by == "comments":
                items.sort(key=lambda x: x.get('comment_count', 0), reverse=True)

            self.logger.info(f"已按 {sort_by} 排序 {len(items)} 条内容")
        except Exception as e:
            self.logger.error(f"排序失败: {e}")

        return items


# ============================================================================
# Layer 4: Interaction Layer - 用户交互操作
# ============================================================================

class ZhihuInteraction:
    """知乎用户交互层"""

    def __init__(self, page, logger):
        self.page = page
        self.logger = logger

    async def follow_question(self, question_id: str) -> bool:
        """关注问题"""
        try:
            self.logger.info(f"关注问题: {question_id}")

            # 查找关注按钮
            follow_button = await self.page.query_selector('.QuestionHeader-follow button')
            if not follow_button:
                follow_button = await self.page.query_selector('button:has-text("关注问题")')

            if follow_button:
                await follow_button.click()
                await asyncio.sleep(1)
                self.logger.info("成功关注问题")
                return True

            return False

        except Exception as e:
            self.logger.error(f"关注问题失败: {e}")
            return False

    async def follow_user(self, user_id: str) -> bool:
        """关注用户"""
        try:
            self.logger.info(f"关注用户: {user_id}")

            # 查找关注按钮
            follow_button = await self.page.query_selector('.Button--blue:has-text("关注")')
            if not follow_button:
                follow_button = await self.page.query_selector('button:has-text("关注他")')

            if follow_button:
                await follow_button.click()
                await asyncio.sleep(1)
                self.logger.info("成功关注用户")
                return True

            return False

        except Exception as e:
            self.logger.error(f"关注用户失败: {e}")
            return False

    async def voteup_answer(self, answer_id: str) -> bool:
        """点赞回答"""
        try:
            self.logger.info(f"点赞回答: {answer_id}")

            # 查找点赞按钮
            voteup_button = await self.page.query_selector('.VoteButton--up')
            if voteup_button:
                await voteup_button.click()
                await asyncio.sleep(0.5)
                self.logger.info("成功点赞回答")
                return True

            return False

        except Exception as e:
            self.logger.error(f"点赞回答失败: {e}")
            return False

    async def thank_answer(self, answer_id: str) -> bool:
        """感谢回答"""
        try:
            self.logger.info(f"感谢回答: {answer_id}")

            # 查找感谢按钮
            thank_button = await self.page.query_selector('button:has-text("感谢")')
            if thank_button:
                await thank_button.click()
                await asyncio.sleep(1)
                self.logger.info("成功感谢回答")
                return True

            return False

        except Exception as e:
            self.logger.error(f"感谢回答失败: {e}")
            return False

    async def collect_answer(self, answer_id: str, collection_id: Optional[str] = None) -> bool:
        """收藏回答"""
        try:
            self.logger.info(f"收藏回答: {answer_id}")

            # 查找收藏按钮
            collect_button = await self.page.query_selector('button:has-text("收藏")')
            if collect_button:
                await collect_button.click()
                await asyncio.sleep(1)

                # 如果指定了收藏夹，选择收藏夹
                if collection_id:
                    collection_elem = await self.page.query_selector(f'[data-id="{collection_id}"]')
                    if collection_elem:
                        await collection_elem.click()
                        await asyncio.sleep(0.5)

                # 确认收藏
                confirm_button = await self.page.query_selector('button:has-text("完成")')
                if confirm_button:
                    await confirm_button.click()
                    await asyncio.sleep(0.5)

                self.logger.info("成功收藏回答")
                return True

            return False

        except Exception as e:
            self.logger.error(f"收藏回答失败: {e}")
            return False

    async def post_comment(self, target_id: str, content: str, target_type: str = "answer") -> bool:
        """发表评论

        Args:
            target_id: 目标ID（回答ID、文章ID等）
            content: 评论内容
            target_type: 目标类型 (answer, article, pin)
        """
        try:
            self.logger.info(f"发表评论到 {target_type}: {target_id}")

            # 查找评论输入框
            comment_input = await self.page.query_selector('.CommentEditor-input textarea')
            if not comment_input:
                comment_input = await self.page.query_selector('textarea[placeholder*="评论"]')

            if comment_input:
                await comment_input.fill(content)
                await asyncio.sleep(1)

                # 查找发送按钮
                submit_button = await self.page.query_selector('button:has-text("发布")')
                if submit_button:
                    await submit_button.click()
                    await asyncio.sleep(2)
                    self.logger.info("成功发表评论")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"发表评论失败: {e}")
            return False


# ============================================================================
# Layer 1: Spider Layer - 核心爬虫功能
# ============================================================================

class ZhihuSpider(BaseSpider):
    """知乎问答社区爬虫 - 完整4层架构实现"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="zhihu", headless=headless, proxy=proxy)
        self.base_url = "https://www.zhihu.com"
        self.api_base_url = "https://www.zhihu.com/api/v4"

        # 初始化各层
        self.anti_crawl = ZhihuAntiCrawl(self.logger)
        self.matcher = ZhihuMatcher(self.logger)
        self.interaction = None  # 在session启动后初始化

    async def _safe_navigate(self, url: str, max_retries: int = 3) -> bool:
        """安全导航 - 带反爬虫处理"""
        for attempt in range(max_retries):
            try:
                # 智能延迟
                await self.anti_crawl.smart_delay()

                # 导航到页面
                await self.navigate(url)
                await asyncio.sleep(2)

                # 获取页面内容
                content = await self._page.content()

                # 检测验证码
                if self.anti_crawl.detect_captcha(content):
                    if await self.anti_crawl.handle_captcha(self._page):
                        return True
                    else:
                        continue

                # 检测封禁
                if self.anti_crawl.detect_blocked(content):
                    await self.anti_crawl.exponential_backoff(attempt)
                    continue

                # 检查是否需要轮换会话
                if self.anti_crawl.should_rotate_session():
                    self.anti_crawl.reset_session()

                return True

            except Exception as e:
                self.logger.error(f"导航失败 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await self.anti_crawl.exponential_backoff(attempt)

        return False

    async def login(self, username: str, password: str) -> bool:
        """登录知乎账户"""
        try:
            self.logger.info("登录知乎...")

            # 尝试使用已保存的cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                if await self._safe_navigate(self.base_url):
                    if await self._page.query_selector('.AppHeader-profile'):
                        self._is_logged_in = True
                        self.interaction = ZhihuInteraction(self._page, self.logger)
                        self.logger.info("使用已保存的cookies登录成功")
                        return True

            # 导航到登录页面
            if not await self._safe_navigate(f"{self.base_url}/signin"):
                self.logger.error("无法导航到登录页面")
                return False

            # 切换到密码登录
            password_tab = await self._page.query_selector('.SignFlow-tab:has-text("密码登录")')
            if password_tab:
                await password_tab.click()
                await asyncio.sleep(1)

            # 填写手机号/邮箱
            username_input = await self._page.wait_for_selector('input[name="username"]', timeout=10000)
            await username_input.fill(username)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # 填写密码
            password_input = await self._page.wait_for_selector('input[name="password"]', timeout=10000)
            await password_input.fill(password)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # 点击登录
            login_btn = await self._page.wait_for_selector('button[type="submit"]', timeout=10000)
            await login_btn.click()
            await asyncio.sleep(5)

            # 检查登录是否成功
            if await self._page.query_selector('.AppHeader-profile'):
                self._is_logged_in = True
                self.interaction = ZhihuInteraction(self._page, self.logger)
                await self._save_cookies()
                self.logger.info("登录成功")
                return True

            self.logger.error("登录失败")
            return False

        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        content_type: str = "all",
        sort_by: str = "default"
    ) -> List[Dict[str, Any]]:
        """搜索知乎内容 - 支持高级过滤

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            content_type: 内容类型 (all, question, answer, article, user)
            sort_by: 排序方式 (default, time, heat)

        Returns:
            搜索结果列表
        """
        try:
            self.logger.info(f"搜索知乎内容: '{keyword}'")

            # 构建搜索URL
            search_params = {'q': keyword, 'type': 'content'}

            if content_type != "all":
                search_params['type'] = content_type

            search_url = f"{self.base_url}/search?{urlencode(search_params)}"

            if not await self._safe_navigate(search_url):
                self.logger.error("无法导航到搜索页面")
                return []

            # 滚动加载更多
            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            item_elements = await self._page.query_selector_all('.List-item')

            for elem in item_elements[:max_results]:
                try:
                    result = {'platform': self.platform}

                    # 标题和链接
                    title_elem = await elem.query_selector('.ContentItem-title a')
                    if title_elem:
                        result['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        result['url'] = href if href.startswith('http') else f"{self.base_url}{href}"

                        # 提取ID
                        if '/question/' in href:
                            result['id'] = href.split('/question/')[-1].split('/')[0]
                            result['type'] = 'question'
                        elif '/answer/' in href:
                            result['id'] = href.split('/answer/')[-1].split('/')[0]
                            result['type'] = 'answer'
                        elif '/p/' in href:
                            result['id'] = href.split('/p/')[-1].split('/')[0]
                            result['type'] = 'article'

                    # 内容预览
                    content = await elem.query_selector('.RichText')
                    if content:
                        result['excerpt'] = await content.inner_text()

                    # 作者
                    author = await elem.query_selector('.AuthorInfo-name')
                    if author:
                        result['author'] = await author.inner_text()

                    # 统计数据
                    vote_count = await elem.query_selector('.Button--plain:has-text("赞同")')
                    if vote_count:
                        vote_text = await vote_count.inner_text()
                        result['voteup_count'] = self.parser.parse_count(vote_text)

                    comment_count = await elem.query_selector('.Button--plain:has-text("条评论")')
                    if comment_count:
                        comment_text = await comment_count.inner_text()
                        result['comment_count'] = self.parser.parse_count(comment_text)

                    if result.get('id'):
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"解析结果失败: {e}")
                    continue

            self.logger.info(f"找到 {len(results)} 个结果")
            return results

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取知乎用户资料"""
        try:
            self.logger.info(f"获取用户资料: {user_id}")

            profile_url = f"{self.base_url}/people/{user_id}"
            if not await self._safe_navigate(profile_url):
                self.logger.error("无法导航到用户页面")
                return {}

            profile = {'user_id': user_id, 'platform': self.platform, 'type': 'user'}

            # 用户名
            name = await self._page.query_selector('.ProfileHeader-name')
            if name:
                profile['username'] = await name.inner_text()

            # 一句话介绍
            headline = await self._page.query_selector('.ProfileHeader-headline')
            if headline:
                profile['headline'] = await headline.inner_text()

            # 个人简介
            bio = await self._page.query_selector('.ProfileHeader-detail')
            if bio:
                profile['description'] = await bio.inner_text()

            # 头像
            avatar = await self._page.query_selector('.Avatar img')
            if avatar:
                profile['avatar_url'] = await avatar.get_attribute('src')

            # 统计数据
            stats = await self._page.query_selector_all('.Profile-lightItem')
            for stat in stats:
                text = await stat.inner_text()
                if '关注者' in text:
                    profile['follower_count'] = self.parser.parse_count(text)
                elif '关注了' in text:
                    profile['following_count'] = self.parser.parse_count(text)

            # 获赞和感谢
            side_stats = await self._page.query_selector_all('.Profile-sideColumnItem')
            for stat in side_stats:
                text = await stat.inner_text()
                if '获得' in text and '赞同' in text:
                    profile['voteup_count'] = self.parser.parse_count(text)
                elif '获得' in text and '感谢' in text:
                    profile['thanks_count'] = self.parser.parse_count(text)

            # 认证信息
            badge = await self._page.query_selector('.ProfileHeader-badge')
            if badge:
                profile['badge'] = await badge.inner_text()

            # 专业领域
            business = await self._page.query_selector('.ProfileHeader-infoItem:has-text("行业")')
            if business:
                profile['business'] = await business.inner_text()

            employment = await self._page.query_selector('.ProfileHeader-infoItem:has-text("公司")')
            if employment:
                profile['employment'] = await employment.inner_text()

            education = await self._page.query_selector('.ProfileHeader-infoItem:has-text("学校")')
            if education:
                profile['education'] = await education.inner_text()

            self.logger.info(f"成功获取用户资料: {profile.get('username', user_id)}")
            return profile

        except Exception as e:
            self.logger.error(f"获取用户资料失败: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """获取用户的回答列表"""
        try:
            self.logger.info(f"获取用户回答: {user_id}")

            answers_url = f"{self.base_url}/people/{user_id}/answers"
            if not await self._safe_navigate(answers_url):
                self.logger.error("无法导航到用户回答页面")
                return []

            # 滚动加载更多
            for _ in range(max_posts // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            posts = []
            item_elements = await self._page.query_selector_all('.List-item')

            for elem in item_elements[:max_posts]:
                try:
                    post = {'user_id': user_id, 'platform': self.platform, 'type': 'answer'}

                    # 问题标题
                    question = await elem.query_selector('.ContentItem-title a')
                    if question:
                        post['question'] = await question.inner_text()
                        href = await question.get_attribute('href')
                        post['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if '/answer/' in href:
                            post['id'] = href.split('/answer/')[-1].split('/')[0]

                    # 回答内容
                    content = await elem.query_selector('.RichText')
                    if content:
                        post['content'] = await content.inner_text()

                    # 统计数据
                    vote = await elem.query_selector('.Button--plain:has-text("赞同")')
                    if vote:
                        post['voteup_count'] = self.parser.parse_count(await vote.inner_text())

                    comment = await elem.query_selector('.Button--plain:has-text("条评论")')
                    if comment:
                        post['comment_count'] = self.parser.parse_count(await comment.inner_text())

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"解析回答失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(posts)} 个回答")
            return posts

        except Exception as e:
            self.logger.error(f"获取用户回答失败: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """获取知乎回答详细信息"""
        try:
            self.logger.info(f"获取回答详情: {post_id}")

            post_url = f"{self.base_url}/answer/{post_id}"
            if not await self._safe_navigate(post_url):
                self.logger.error("无法导航到回答页面")
                return {}

            post = {'id': post_id, 'url': post_url, 'platform': self.platform, 'type': 'answer'}

            # 问题标题
            question = await self._page.query_selector('.QuestionHeader-title')
            if question:
                post['question'] = await question.inner_text()

            # 回答作者
            author = await self._page.query_selector('.AuthorInfo-name')
            if author:
                post['author'] = await author.inner_text()

            # 作者简介
            headline = await self._page.query_selector('.AuthorInfo-detail')
            if headline:
                post['author_headline'] = await headline.inner_text()

            # 回答内容
            content = await self._page.query_selector('.RichContent-inner')
            if content:
                post['content'] = await content.inner_text()

            # 统计数据
            vote = await self._page.query_selector('.Button--plain:has-text("赞同")')
            if vote:
                post['voteup_count'] = self.parser.parse_count(await vote.inner_text())

            comment = await self._page.query_selector('.Button--plain:has-text("条评论")')
            if comment:
                post['comment_count'] = self.parser.parse_count(await comment.inner_text())

            # 时间戳
            time_elem = await self._page.query_selector('.ContentItem-time')
            if time_elem:
                post['created_at'] = self.parser.parse_date(await time_elem.inner_text())

            self.logger.info(f"成功获取回答详情: {post_id}")
            return post

        except Exception as e:
            self.logger.error(f"获取回答详情失败: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Get comments for a Zhihu answer"""
        try:
            self.logger.info(f"Getting comments for post: {post_id}")

            post_url = f"{self.base_url}/answer/{post_id}"
            if post_id not in self._page.url:
                await self.navigate(post_url)
                await asyncio.sleep(3)

            # Click to load comments
            comment_btn = await self._page.query_selector('.Button--plain:has-text("条评论")')
            if comment_btn:
                await comment_btn.click()
                await asyncio.sleep(2)

            # Load more comments
            for _ in range(max_comments // 20):
                load_more = await self._page.query_selector('button:has-text("查看更多评论")')
                if load_more:
                    await load_more.click()
                    await asyncio.sleep(random.uniform(1, 2))

            comments = []
            comment_elements = await self._page.query_selector_all('.CommentItem')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {'post_id': post_id, 'platform': self.platform}

                    # Author
                    author = await elem.query_selector('.CommentItem-author')
                    if author:
                        comment['username'] = await author.inner_text()

                    # Content
                    content = await elem.query_selector('.CommentItem-content')
                    if content:
                        comment['content'] = await content.inner_text()

                    # Likes
                    like = await elem.query_selector('.Button--plain')
                    if like:
                        like_text = await like.inner_text()
                        comment['likes'] = self.parser.parse_count(like_text) if like_text else 0

                    # Time
                    time_elem = await elem.query_selector('.CommentItem-time')
                    if time_elem:
                        comment['created_at'] = self.parser.parse_date(await time_elem.inner_text())

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(f"{comment.get('username', '')}{comment['content']}".encode()).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"Failed to parse comment: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} comments")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get comments: {e}")
            return []

    # ========================================================================
    # 扩展功能方法
    # ========================================================================

    async def get_question_detail(self, question_id: str) -> Dict[str, Any]:
        """获取问题详情"""
        try:
            self.logger.info(f"获取问题详情: {question_id}")

            question_url = f"{self.base_url}/question/{question_id}"
            if not await self._safe_navigate(question_url):
                return {}

            question = {
                'id': question_id,
                'url': question_url,
                'platform': self.platform,
                'type': 'question'
            }

            # 问题标题
            title = await self._page.query_selector('.QuestionHeader-title')
            if title:
                question['title'] = await title.inner_text()

            # 问题描述
            detail = await self._page.query_selector('.QuestionRichText')
            if detail:
                question['detail'] = await detail.inner_text()

            # 统计数据
            stats = await self._page.query_selector_all('.NumberBoard-itemValue')
            stat_labels = await self._page.query_selector_all('.NumberBoard-itemName')

            for i, stat in enumerate(stats):
                if i < len(stat_labels):
                    label = await stat_labels[i].inner_text()
                    value = await stat.inner_text()

                    if '关注者' in label:
                        question['follower_count'] = self.parser.parse_count(value)
                    elif '被浏览' in label:
                        question['view_count'] = self.parser.parse_count(value)
                    elif '回答' in label:
                        question['answer_count'] = self.parser.parse_count(value)

            # 话题标签
            topics = []
            topic_elements = await self._page.query_selector_all('.QuestionHeader-topics .Tag')
            for topic in topic_elements:
                topics.append(await topic.inner_text())
            question['topics'] = topics

            self.logger.info(f"成功获取问题详情: {question.get('title', question_id)[:50]}")
            return question

        except Exception as e:
            self.logger.error(f"获取问题详情失败: {e}")
            return {}

    async def get_question_answers(
        self,
        question_id: str,
        max_answers: int = 20,
        sort_by: str = "default"
    ) -> List[Dict[str, Any]]:
        """获取问题的所有回答

        Args:
            question_id: 问题ID
            max_answers: 最大回答数
            sort_by: 排序方式 (default, time)
        """
        try:
            self.logger.info(f"获取问题回答: {question_id}")

            question_url = f"{self.base_url}/question/{question_id}"
            if sort_by == "time":
                question_url += "?sort=created"

            if not await self._safe_navigate(question_url):
                return []

            # 滚动加载更多
            for _ in range(max_answers // 5):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            answers = []
            answer_elements = await self._page.query_selector_all('.List-item')

            for elem in answer_elements[:max_answers]:
                try:
                    answer = {
                        'question_id': question_id,
                        'platform': self.platform,
                        'type': 'answer'
                    }

                    # 回答链接和ID
                    link = await elem.query_selector('.ContentItem-title a')
                    if link:
                        href = await link.get_attribute('href')
                        if href and '/answer/' in href:
                            answer['id'] = href.split('/answer/')[-1].split('/')[0]
                            answer['url'] = href if href.startswith('http') else f"{self.base_url}{href}"

                    # 作者
                    author = await elem.query_selector('.AuthorInfo-name')
                    if author:
                        answer['author'] = await author.inner_text()

                    # 内容
                    content = await elem.query_selector('.RichText')
                    if content:
                        answer['content'] = await content.inner_text()

                    # 统计数据
                    vote = await elem.query_selector('.Button--plain:has-text("赞同")')
                    if vote:
                        answer['voteup_count'] = self.parser.parse_count(await vote.inner_text())

                    comment = await elem.query_selector('.Button--plain:has-text("条评论")')
                    if comment:
                        answer['comment_count'] = self.parser.parse_count(await comment.inner_text())

                    if answer.get('id'):
                        answers.append(answer)

                except Exception as e:
                    self.logger.warning(f"解析回答失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(answers)} 个回答")
            return answers

        except Exception as e:
            self.logger.error(f"获取问题回答失败: {e}")
            return []

    async def get_hot_list(self, max_items: int = 50) -> List[Dict[str, Any]]:
        """获取知乎热榜"""
        try:
            self.logger.info("获取知乎热榜")

            hot_url = f"{self.base_url}/hot"
            if not await self._safe_navigate(hot_url):
                return []

            hot_items = []
            item_elements = await self._page.query_selector_all('.HotItem')

            for i, elem in enumerate(item_elements[:max_items], 1):
                try:
                    item = {'platform': self.platform, 'rank': i, 'type': 'hot_item'}

                    # 标题和链接
                    title_elem = await elem.query_selector('.HotItem-title')
                    if title_elem:
                        item['title'] = await title_elem.inner_text()

                    link = await elem.query_selector('a')
                    if link:
                        href = await link.get_attribute('href')
                        item['url'] = href if href.startswith('http') else f"{self.base_url}{href}"

                        # 提取ID
                        if '/question/' in href:
                            item['id'] = href.split('/question/')[-1].split('/')[0]
                            item['content_type'] = 'question'

                    # 热度
                    metrics = await elem.query_selector('.HotItem-metrics')
                    if metrics:
                        item['heat'] = await metrics.inner_text()

                    # 摘要
                    excerpt = await elem.query_selector('.HotItem-excerpt')
                    if excerpt:
                        item['excerpt'] = await excerpt.inner_text()

                    if item.get('title'):
                        hot_items.append(item)

                except Exception as e:
                    self.logger.warning(f"解析热榜项失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(hot_items)} 个热榜项")
            return hot_items

        except Exception as e:
            self.logger.error(f"获取热榜失败: {e}")
            return []

    async def get_article_detail(self, article_id: str) -> Dict[str, Any]:
        """获取文章详情"""
        try:
            self.logger.info(f"获取文章详情: {article_id}")

            article_url = f"{self.base_url}/p/{article_id}"
            if not await self._safe_navigate(article_url):
                return {}

            article = {
                'id': article_id,
                'url': article_url,
                'platform': self.platform,
                'type': 'article'
            }

            # 文章标题
            title = await self._page.query_selector('.Post-Title')
            if title:
                article['title'] = await title.inner_text()

            # 作者
            author = await self._page.query_selector('.AuthorInfo-name')
            if author:
                article['author'] = await author.inner_text()

            # 文章内容
            content = await self._page.query_selector('.RichText')
            if content:
                article['content'] = await content.inner_text()

            # 统计数据
            vote = await self._page.query_selector('.Button--plain:has-text("赞同")')
            if vote:
                article['voteup_count'] = self.parser.parse_count(await vote.inner_text())

            comment = await self._page.query_selector('.Button--plain:has-text("条评论")')
            if comment:
                article['comment_count'] = self.parser.parse_count(await comment.inner_text())

            # 专栏信息
            column = await self._page.query_selector('.Post-Header-ColumnLink')
            if column:
                article['column_title'] = await column.inner_text()
                column_href = await column.get_attribute('href')
                if column_href and '/column/' in column_href:
                    article['column_id'] = column_href.split('/column/')[-1].split('/')[0]

            # 时间
            time_elem = await self._page.query_selector('.ContentItem-time')
            if time_elem:
                article['created_at'] = self.parser.parse_date(await time_elem.inner_text())

            self.logger.info(f"成功获取文章详情: {article.get('title', article_id)[:50]}")
            return article

        except Exception as e:
            self.logger.error(f"获取文章详情失败: {e}")
            return {}

    async def get_user_articles(self, user_id: str, max_articles: int = 20) -> List[Dict[str, Any]]:
        """获取用户的文章列表"""
        try:
            self.logger.info(f"获取用户文章: {user_id}")

            articles_url = f"{self.base_url}/people/{user_id}/posts"
            if not await self._safe_navigate(articles_url):
                return []

            # 滚动加载更多
            for _ in range(max_articles // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            articles = []
            item_elements = await self._page.query_selector_all('.List-item')

            for elem in item_elements[:max_articles]:
                try:
                    article = {'user_id': user_id, 'platform': self.platform, 'type': 'article'}

                    # 标题和链接
                    title_elem = await elem.query_selector('.ContentItem-title a')
                    if title_elem:
                        article['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        article['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if '/p/' in href:
                            article['id'] = href.split('/p/')[-1].split('/')[0]

                    # 摘要
                    excerpt = await elem.query_selector('.RichText')
                    if excerpt:
                        article['excerpt'] = await excerpt.inner_text()

                    # 统计数据
                    vote = await elem.query_selector('.Button--plain:has-text("赞同")')
                    if vote:
                        article['voteup_count'] = self.parser.parse_count(await vote.inner_text())

                    comment = await elem.query_selector('.Button--plain:has-text("条评论")')
                    if comment:
                        article['comment_count'] = self.parser.parse_count(await comment.inner_text())

                    if article.get('id'):
                        articles.append(article)

                except Exception as e:
                    self.logger.warning(f"解析文章失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(articles)} 篇文章")
            return articles

        except Exception as e:
            self.logger.error(f"获取用户文章失败: {e}")
            return []

    async def get_topic_questions(
        self,
        topic_id: str,
        max_questions: int = 20
    ) -> List[Dict[str, Any]]:
        """获取话题下的问题列表"""
        try:
            self.logger.info(f"获取话题问题: {topic_id}")

            topic_url = f"{self.base_url}/topic/{topic_id}/hot"
            if not await self._safe_navigate(topic_url):
                return []

            # 滚动加载更多
            for _ in range(max_questions // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            questions = []
            item_elements = await self._page.query_selector_all('.List-item')

            for elem in item_elements[:max_questions]:
                try:
                    question = {'topic_id': topic_id, 'platform': self.platform, 'type': 'question'}

                    # 问题标题和链接
                    title_elem = await elem.query_selector('.ContentItem-title a')
                    if title_elem:
                        question['title'] = await title_elem.inner_text()
                        href = await title_elem.get_attribute('href')
                        question['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        if '/question/' in href:
                            question['id'] = href.split('/question/')[-1].split('/')[0]

                    # 问题摘要
                    excerpt = await elem.query_selector('.RichText')
                    if excerpt:
                        question['excerpt'] = await excerpt.inner_text()

                    # 统计数据
                    answer_count = await elem.query_selector('.ContentItem-meta:has-text("个回答")')
                    if answer_count:
                        question['answer_count'] = self.parser.parse_count(await answer_count.inner_text())

                    if question.get('id'):
                        questions.append(question)

                except Exception as e:
                    self.logger.warning(f"解析问题失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(questions)} 个问题")
            return questions

        except Exception as e:
            self.logger.error(f"获取话题问题失败: {e}")
            return []

    async def get_user_followers(
        self,
        user_id: str,
        max_followers: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户的粉丝列表"""
        try:
            self.logger.info(f"获取用户粉丝: {user_id}")

            followers_url = f"{self.base_url}/people/{user_id}/followers"
            if not await self._safe_navigate(followers_url):
                return []

            # 滚动加载更多
            for _ in range(max_followers // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            followers = []
            user_elements = await self._page.query_selector_all('.List-item')

            for elem in user_elements[:max_followers]:
                try:
                    follower = {'platform': self.platform, 'type': 'user'}

                    # 用户名和链接
                    name_elem = await elem.query_selector('.ContentItem-title a')
                    if name_elem:
                        follower['username'] = await name_elem.inner_text()
                        href = await name_elem.get_attribute('href')
                        if href and '/people/' in href:
                            follower['user_id'] = href.split('/people/')[-1].split('/')[0]
                            follower['url'] = href if href.startswith('http') else f"{self.base_url}{href}"

                    # 用户简介
                    headline = await elem.query_selector('.ContentItem-meta')
                    if headline:
                        follower['headline'] = await headline.inner_text()

                    if follower.get('user_id'):
                        followers.append(follower)

                except Exception as e:
                    self.logger.warning(f"解析粉丝失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(followers)} 个粉丝")
            return followers

        except Exception as e:
            self.logger.error(f"获取用户粉丝失败: {e}")
            return []

    async def get_user_following(
        self,
        user_id: str,
        max_following: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户关注的人"""
        try:
            self.logger.info(f"获取用户关注: {user_id}")

            following_url = f"{self.base_url}/people/{user_id}/following"
            if not await self._safe_navigate(following_url):
                return []

            # 滚动加载更多
            for _ in range(max_following // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            following = []
            user_elements = await self._page.query_selector_all('.List-item')

            for elem in user_elements[:max_following]:
                try:
                    user = {'platform': self.platform, 'type': 'user'}

                    # 用户名和链接
                    name_elem = await elem.query_selector('.ContentItem-title a')
                    if name_elem:
                        user['username'] = await name_elem.inner_text()
                        href = await name_elem.get_attribute('href')
                        if href and '/people/' in href:
                            user['user_id'] = href.split('/people/')[-1].split('/')[0]
                            user['url'] = href if href.startswith('http') else f"{self.base_url}{href}"

                    # 用户简介
                    headline = await elem.query_selector('.ContentItem-meta')
                    if headline:
                        user['headline'] = await headline.inner_text()

                    if user.get('user_id'):
                        following.append(user)

                except Exception as e:
                    self.logger.warning(f"解析关注失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(following)} 个关注")
            return following

        except Exception as e:
            self.logger.error(f"获取用户关注失败: {e}")
            return []

    async def search_users(
        self,
        keyword: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索用户"""
        try:
            self.logger.info(f"搜索用户: '{keyword}'")

            search_url = f"{self.base_url}/search?q={keyword}&type=people"
            if not await self._safe_navigate(search_url):
                return []

            # 滚动加载更多
            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            users = []
            user_elements = await self._page.query_selector_all('.List-item')

            for elem in user_elements[:max_results]:
                try:
                    user = {'platform': self.platform, 'type': 'user'}

                    # 用户名和链接
                    name_elem = await elem.query_selector('.ContentItem-title a')
                    if name_elem:
                        user['username'] = await name_elem.inner_text()
                        href = await name_elem.get_attribute('href')
                        if href and '/people/' in href:
                            user['user_id'] = href.split('/people/')[-1].split('/')[0]
                            user['url'] = href if href.startswith('http') else f"{self.base_url}{href}"

                    # 用户简介
                    headline = await elem.query_selector('.RichText')
                    if headline:
                        user['headline'] = await headline.inner_text()

                    # 统计数据
                    stats = await elem.query_selector_all('.ContentItem-meta span')
                    for stat in stats:
                        text = await stat.inner_text()
                        if '回答' in text:
                            user['answer_count'] = self.parser.parse_count(text)
                        elif '文章' in text:
                            user['article_count'] = self.parser.parse_count(text)
                        elif '关注者' in text:
                            user['follower_count'] = self.parser.parse_count(text)

                    if user.get('user_id'):
                        users.append(user)

                except Exception as e:
                    self.logger.warning(f"解析用户失败: {e}")
                    continue

            self.logger.info(f"找到 {len(users)} 个用户")
            return users

        except Exception as e:
            self.logger.error(f"搜索用户失败: {e}")
            return []


if __name__ == "__main__":
    async def test_zhihu_spider():
        """测试知乎爬虫功能"""
        spider = ZhihuSpider(headless=False)

        async with spider.session():
            print("=" * 80)
            print("知乎爬虫 - 完整功能测试")
            print("=" * 80)

            # 测试1: 搜索内容
            print("\n[测试1] 搜索知乎内容")
            results = await spider.search("人工智能", max_results=5, content_type="all")

            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.get('title', 'N/A')[:60]}")
                print(f"   类型: {result.get('type')}")
                print(f"   作者: {result.get('author', 'N/A')}")
                print(f"   点赞: {result.get('voteup_count', 0)}")
                print(f"   评论: {result.get('comment_count', 0)}")

            # 测试2: 使用Matcher过滤
            if results:
                print("\n[测试2] 使用Matcher过滤内容")
                filtered = spider.matcher.filter_by_voteup(results, min_voteup=100)
                print(f"点赞数过滤: {len(results)} -> {len(filtered)} 条内容")

                # 计算质量评分
                for result in filtered[:3]:
                    quality_score = spider.matcher.calculate_content_quality_score(result)
                    print(f"\n{result.get('title', 'N/A')[:50]}")
                    print(f"  质量评分: {quality_score}/100")

            # 测试3: 获取热榜
            print("\n[测试3] 获取知乎热榜")
            hot_list = await spider.get_hot_list(max_items=5)
            for i, item in enumerate(hot_list, 1):
                print(f"\n{i}. {item.get('title', 'N/A')[:60]}")
                print(f"   排名: {item.get('rank')}")
                print(f"   热度: {item.get('heat', 'N/A')}")

            # 测试4: 搜索用户
            print("\n[测试4] 搜索用户")
            users = await spider.search_users("人工智能", max_results=3)
            for i, user in enumerate(users, 1):
                print(f"\n{i}. {user.get('username', 'N/A')}")
                print(f"   简介: {user.get('headline', 'N/A')[:50]}")
                print(f"   回答数: {user.get('answer_count', 0)}")
                print(f"   粉丝数: {user.get('follower_count', 0)}")

                # 计算用户影响力评分
                if i == 1:
                    influence_score = spider.matcher.calculate_user_influence_score(user)
                    print(f"   影响力评分: {influence_score}/100")

            print("\n" + "=" * 80)
            print("测试完成!")
            print("=" * 80)

    asyncio.run(test_zhihu_spider())
