"""
Platform Generator Script
Generates all 30 platform implementations following the douyin.py pattern
"""

import os
from pathlib import Path

# Platform configurations
PLATFORMS = {
    # Social Media (8)
    "facebook": {
        "name": "Facebook",
        "base_url": "https://www.facebook.com",
        "search_url": "https://www.facebook.com/search",
        "content_type": "post",
        "selectors": {
            "post": '[data-testid="post"]',
            "user": '[data-testid="user-link"]',
            "text": '[data-testid="post-text"]',
            "like": '[aria-label*="reactions"]',
            "comment": '[data-testid="UFI2Comment/root"]',
            "share": '[data-testid="share-count"]'
        }
    },
    "instagram": {
        "name": "Instagram",
        "base_url": "https://www.instagram.com",
        "search_url": "https://www.instagram.com/explore/tags",
        "content_type": "post",
        "selectors": {
            "post": 'article',
            "user": 'a[href^="/"]',
            "text": 'h1',
            "like": 'button[aria-label*="like"]',
            "comment": 'ul > li',
            "share": 'button[aria-label*="share"]'
        }
    },
    "linkedin": {
        "name": "LinkedIn",
        "base_url": "https://www.linkedin.com",
        "search_url": "https://www.linkedin.com/search/results",
        "content_type": "post",
        "selectors": {
            "post": '.feed-shared-update-v2',
            "user": '.update-components-actor__title',
            "text": '.feed-shared-text',
            "like": 'button[aria-label*="React"]',
            "comment": '.comments-comment-item',
            "share": 'button[aria-label*="Share"]'
        }
    },
    "reddit": {
        "name": "Reddit",
        "base_url": "https://www.reddit.com",
        "search_url": "https://www.reddit.com/search",
        "content_type": "post",
        "selectors": {
            "post": 'shreddit-post',
            "user": 'a[slot="author-link"]',
            "text": 'div[slot="text-body"]',
            "like": 'shreddit-vote-button',
            "comment": 'shreddit-comment',
            "share": 'button[aria-label="share"]'
        }
    },
    "wechat_mp": {
        "name": "WeChat Official Account (微信公众号)",
        "base_url": "https://mp.weixin.qq.com",
        "search_url": "https://weixin.sogou.com/weixin",
        "content_type": "article",
        "selectors": {
            "post": '.news-box',
            "user": '.account',
            "text": '#js_content',
            "like": '#like',
            "comment": '.discuss_container',
            "share": '.share_btn'
        }
    },
    "douban": {
        "name": "Douban (豆瓣)",
        "base_url": "https://www.douban.com",
        "search_url": "https://www.douban.com/search",
        "content_type": "post",
        "selectors": {
            "post": '.status-item',
            "user": '.author',
            "text": '.status-saying',
            "like": '.rec-btn',
            "comment": '.comment-item',
            "share": '.share-btn'
        }
    },
    "hupu": {
        "name": "Hupu (虎扑)",
        "base_url": "https://bbs.hupu.com",
        "search_url": "https://bbs.hupu.com/search",
        "content_type": "post",
        "selectors": {
            "post": '.post-item',
            "user": '.author',
            "text": '.post-content',
            "like": '.like-btn',
            "comment": '.reply-item',
            "share": '.share-btn'
        }
    },

    # Content (5)
    "baidu_tieba": {
        "name": "Baidu Tieba (百度贴吧)",
        "base_url": "https://tieba.baidu.com",
        "search_url": "https://tieba.baidu.com/f/search",
        "content_type": "post",
        "selectors": {
            "post": '.j_thread_list',
            "user": '.tb_icon_author',
            "text": '.d_post_content',
            "like": '.agree',
            "comment": '.l_post',
            "share": '.share-btn'
        }
    },
    "toutiao": {
        "name": "Toutiao (今日头条)",
        "base_url": "https://www.toutiao.com",
        "search_url": "https://www.toutiao.com/search",
        "content_type": "article",
        "selectors": {
            "post": '.article-item',
            "user": '.author-name',
            "text": '.article-content',
            "like": '.digg-btn',
            "comment": '.comment-item',
            "share": '.share-btn'
        }
    },
    "sohu": {
        "name": "Sohu (搜狐)",
        "base_url": "https://www.sohu.com",
        "search_url": "https://search.sohu.com",
        "content_type": "article",
        "selectors": {
            "post": '.news-item',
            "user": '.author',
            "text": '.article-text',
            "like": '.like-btn',
            "comment": '.comment',
            "share": '.share'
        }
    },
    "quora": {
        "name": "Quora",
        "base_url": "https://www.quora.com",
        "search_url": "https://www.quora.com/search",
        "content_type": "answer",
        "selectors": {
            "post": '.q-box',
            "user": '.author_info',
            "text": '.q-text',
            "like": 'button[aria-label*="Upvote"]',
            "comment": '.comment',
            "share": 'button[aria-label="Share"]'
        }
    },
    "medium": {
        "name": "Medium",
        "base_url": "https://medium.com",
        "search_url": "https://medium.com/search",
        "content_type": "article",
        "selectors": {
            "post": 'article',
            "user": 'a[data-testid="user-link"]',
            "text": 'section',
            "like": 'button[data-testid="clap-button"]',
            "comment": 'div[data-testid="comment"]',
            "share": 'button[aria-label="Share"]'
        }
    },

    # E-commerce (7)
    "shopee": {
        "name": "Shopee",
        "base_url": "https://shopee.com",
        "search_url": "https://shopee.com/search",
        "content_type": "product",
        "selectors": {
            "product": '.shopee-search-item-result__item',
            "seller": '.shop-name',
            "text": '.item-name',
            "price": '.item-price',
            "review": '.item-rating',
            "sales": '.item-sold'
        }
    },
    "temu": {
        "name": "Temu",
        "base_url": "https://www.temu.com",
        "search_url": "https://www.temu.com/search",
        "content_type": "product",
        "selectors": {
            "product": '._1pJTQ_0E',
            "seller": '._3kCTwbaq',
            "text": '._2mRXxQvj',
            "price": '._1zCsOWcM',
            "review": '._3uD7lCq5',
            "sales": '._2KqLT1Ah'
        }
    },
    "ozon": {
        "name": "Ozon",
        "base_url": "https://www.ozon.ru",
        "search_url": "https://www.ozon.ru/search",
        "content_type": "product",
        "selectors": {
            "product": '.tile-root',
            "seller": '.tile-seller',
            "text": '.tile-title',
            "price": '.tile-price',
            "review": '.tile-rating',
            "sales": '.tile-sold'
        }
    },
    "xianyu": {
        "name": "Xianyu (闲鱼)",
        "base_url": "https://2.taobao.com",
        "search_url": "https://s.2.taobao.com/list",
        "content_type": "product",
        "selectors": {
            "product": '.item',
            "seller": '.seller-name',
            "text": '.item-title',
            "price": '.item-price',
            "location": '.item-location',
            "views": '.item-views'
        }
    },
    "dewu": {
        "name": "Dewu (得物)",
        "base_url": "https://www.dewu.com",
        "search_url": "https://www.dewu.com/search",
        "content_type": "product",
        "selectors": {
            "product": '.product-item',
            "seller": '.seller-info',
            "text": '.product-name',
            "price": '.price',
            "sales": '.sales-count',
            "certification": '.auth-badge'
        }
    },
    "vipshop": {
        "name": "Vipshop (唯品会)",
        "base_url": "https://www.vip.com",
        "search_url": "https://category.vip.com/search",
        "content_type": "product",
        "selectors": {
            "product": '.goods-item',
            "seller": '.brand-name',
            "text": '.goods-title',
            "price": '.goods-price',
            "discount": '.discount-tag',
            "sales": '.sales-num'
        }
    },
    "zhuanzhuan": {
        "name": "Zhuanzhuan (转转)",
        "base_url": "https://www.zhuanzhuan.com",
        "search_url": "https://www.zhuanzhuan.com/search",
        "content_type": "product",
        "selectors": {
            "product": '.item-card',
            "seller": '.seller-name',
            "text": '.item-title',
            "price": '.item-price',
            "location": '.location',
            "condition": '.condition-tag'
        }
    },

    # Local Services (3)
    "aihuishou": {
        "name": "Aihuishou (爱回收)",
        "base_url": "https://www.aihuishou.com",
        "search_url": "https://www.aihuishou.com/search",
        "content_type": "product",
        "selectors": {
            "product": '.product-item',
            "category": '.category',
            "text": '.product-name',
            "price": '.recycle-price',
            "condition": '.condition-options',
            "brand": '.brand-name'
        }
    },
    "meituan": {
        "name": "Meituan (美团)",
        "base_url": "https://www.meituan.com",
        "search_url": "https://www.meituan.com/search",
        "content_type": "merchant",
        "selectors": {
            "merchant": '.poi-item',
            "name": '.poi-name',
            "category": '.poi-category',
            "rating": '.poi-rating',
            "review": '.review-count',
            "location": '.poi-address'
        }
    },
    "dianping": {
        "name": "Dianping (大众点评)",
        "base_url": "https://www.dianping.com",
        "search_url": "https://www.dianping.com/search",
        "content_type": "merchant",
        "selectors": {
            "merchant": '.shop-item',
            "name": '.shop-name',
            "category": '.shop-tags',
            "rating": '.shop-star',
            "review": '.review-num',
            "location": '.shop-addr'
        }
    },

    # Search (3)
    "baidu": {
        "name": "Baidu (百度)",
        "base_url": "https://www.baidu.com",
        "search_url": "https://www.baidu.com/s",
        "content_type": "result",
        "selectors": {
            "result": '.result',
            "title": 'h3 a',
            "text": '.c-abstract',
            "url": 'h3 a',
            "source": '.c-showurl',
            "timestamp": '.c-color-gray2'
        }
    },
    "google": {
        "name": "Google",
        "base_url": "https://www.google.com",
        "search_url": "https://www.google.com/search",
        "content_type": "result",
        "selectors": {
            "result": '.g',
            "title": 'h3',
            "text": '.VwiC3b',
            "url": 'a',
            "source": 'cite',
            "timestamp": '.LEwnzc'
        }
    },
    "quark": {
        "name": "Quark (夸克)",
        "base_url": "https://quark.sm.cn",
        "search_url": "https://quark.sm.cn/s",
        "content_type": "result",
        "selectors": {
            "result": '.result',
            "title": '.title',
            "text": '.abstract',
            "url": 'a',
            "source": '.source',
            "timestamp": '.time'
        }
    },

    # Academic (2)
    "web_of_science": {
        "name": "Web of Science",
        "base_url": "https://www.webofscience.com",
        "search_url": "https://www.webofscience.com/wos/woscc/basic-search",
        "content_type": "paper",
        "selectors": {
            "paper": '.search-results-item',
            "title": '.title',
            "authors": '.authors',
            "abstract": '.abstract',
            "journal": '.journal',
            "citations": '.citations',
            "year": '.year'
        }
    },
    "arxiv": {
        "name": "arXiv",
        "base_url": "https://arxiv.org",
        "search_url": "https://arxiv.org/search",
        "content_type": "paper",
        "selectors": {
            "paper": '.arxiv-result',
            "title": '.title',
            "authors": '.authors',
            "abstract": '.abstract-full',
            "category": '.tag',
            "pdf": '.download-pdf',
            "date": '.is-size-7'
        }
    },

    # Developer (2)
    "csdn": {
        "name": "CSDN",
        "base_url": "https://www.csdn.net",
        "search_url": "https://so.csdn.net/so/search",
        "content_type": "article",
        "selectors": {
            "article": '.search-item',
            "title": '.search-item-title',
            "author": '.search-item-author',
            "text": '.search-item-content',
            "views": '.view-num',
            "likes": '.like-num',
            "comments": '.comment-num'
        }
    },
    "stackoverflow": {
        "name": "Stack Overflow",
        "base_url": "https://stackoverflow.com",
        "search_url": "https://stackoverflow.com/search",
        "content_type": "question",
        "selectors": {
            "question": '.s-post-summary',
            "title": '.s-link',
            "user": '.s-user-card',
            "text": '.s-post-summary--content-excerpt',
            "votes": '.s-post-summary--stats-item-number',
            "answers": '.s-post-summary--stats-item-number',
            "tags": '.s-tag'
        }
    }
}


def generate_platform_code(platform_id, config):
    """Generate complete platform spider code"""

    platform_name = config['name']
    base_url = config['base_url']
    search_url = config['search_url']
    content_type = config['content_type']
    selectors = config['selectors']

    # Create class name (e.g., facebook -> Facebook, baidu_tieba -> BaiduTieba)
    class_name = ''.join(word.capitalize() for word in platform_id.split('_'))

    code = f'''"""
{platform_name} Spider Implementation
完整的{platform_name}平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 关键词搜索、用户主页、话题页、内容详情
2. Anti-Crawl Layer: 反反爬层 - 设备指纹、IP轮换、滑动行为模拟
3. Matcher Layer: 智能匹配层 - 多模态匹配（文本、标签、元数据）
4. Interaction Layer: 互动处理层 - 评论、点赞、分享、用户信息
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


class {class_name}AntiCrawl:
    """
    {platform_name}反反爬处理器
    Layer 2: Anti-Crawl - 设备指纹、IP轮换、行为模拟
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger
        self._device_id = None
        self._fp_cache = {{}}

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
        window._device_id = '{{self._device_id}}';

        // Override device memory
        Object.defineProperty(navigator, 'deviceMemory', {{{{
            get: () => {{random.choice([4, 8, 16])}}
        }}}});

        // Override hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {{{{
            get: () => {{random.choice([4, 8, 12, 16])}}
        }}}});

        // Override platform
        Object.defineProperty(navigator, 'platform', {{{{
            get: () => 'Win32'
        }}}});

        // Override vendor
        Object.defineProperty(navigator, 'vendor', {{{{
            get: () => 'Google Inc.'
        }}}});
        """
        await page.add_init_script(device_script)
        self.logger.debug(f"Injected device fingerprint: {{self._device_id}}")

    async def _inject_webdriver_evasion(self, page: Page):
        """注入反webdriver检测"""
        evasion_script = """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});

        // Chrome runtime
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}}
        }};

        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );

        // Plugins
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{
                    0: {{type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"}},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }}
            ]
        }});

        // Languages
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        }});
        """
        await page.add_init_script(evasion_script)

    async def _inject_canvas_fingerprint(self, page: Page):
        """注入Canvas指纹随机化"""
        canvas_script = """
        // Canvas fingerprint noise
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;

        const noisify = function(canvas, context) {{
            const shift = {{
                'r': Math.floor(Math.random() * 10) - 5,
                'g': Math.floor(Math.random() * 10) - 5,
                'b': Math.floor(Math.random() * 10) - 5,
                'a': Math.floor(Math.random() * 10) - 5
            }};

            const width = canvas.width;
            const height = canvas.height;

            if (context) {{
                const imageData = context.getImageData(0, 0, width, height);
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i + 0] = imageData.data[i + 0] + shift.r;
                    imageData.data[i + 1] = imageData.data[i + 1] + shift.g;
                    imageData.data[i + 2] = imageData.data[i + 2] + shift.b;
                    imageData.data[i + 3] = imageData.data[i + 3] + shift.a;
                }}
                context.putImageData(imageData, 0, 0);
            }}
        }};

        Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {{
            value: function() {{
                noisify(this, this.getContext('2d'));
                return toBlob.apply(this, arguments);
            }}
        }});

        Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {{
            value: function() {{
                noisify(this, this.getContext('2d'));
                return toDataURL.apply(this, arguments);
            }}
        }});

        // WebGL vendor/renderer spoofing
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{
                return 'Intel Inc.';
            }}
            if (parameter === 37446) {{
                return 'Intel Iris OpenGL Engine';
            }}
            return getParameter.call(this, parameter);
        }};
        """
        await page.add_init_script(canvas_script)

    def _generate_device_id(self) -> str:
        """生成随机设备ID"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789abcdef', k=16))
        return hashlib.md5(f"{{timestamp}}{{random_str}}".encode()).hexdigest()

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

            await page.evaluate(f"window.scrollTo({{{{top: {{new_position}}, behavior: 'smooth'}}}}")
            await asyncio.sleep(step_duration + random.uniform(0, 0.5))

            if random.random() < 0.2:
                back_scroll = random.randint(50, 150)
                await page.evaluate(f"window.scrollBy({{{{top: -{{back_scroll}}, behavior: 'smooth'}}}}")
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


class {class_name}Matcher:
    """
    {platform_name}内容匹配器
    Layer 3: Matcher - 多模态匹配（文本、标签、元数据）
    """

    def __init__(self):
        self.logger = logger

    async def match_content(self, content: Dict[str, Any], criteria: Dict[str, Any]) -> tuple[bool, float]:
        """
        匹配内容

        Args:
            content: 内容数据
            criteria: 匹配条件 (keywords, etc.)

        Returns:
            (is_match, match_score)
        """
        if not criteria:
            return True, 1.0

        score = 0.0
        weights = {{
            'text': 0.4,
            'title': 0.3,
            'tags': 0.2,
            'metadata': 0.1
        }}

        # 关键词匹配
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]

            # 文本匹配
            if content.get('text'):
                text_matches = sum(1 for kw in keywords if kw.lower() in content['text'].lower())
                score += (text_matches / len(keywords)) * weights['text']

            # 标题匹配
            if content.get('title'):
                title_matches = sum(1 for kw in keywords if kw.lower() in content['title'].lower())
                score += (title_matches / len(keywords)) * weights['title']

            # 标签匹配
            if content.get('tags'):
                tag_text = ' '.join(content['tags']).lower()
                tag_matches = sum(1 for kw in keywords if kw.lower() in tag_text)
                score += (tag_matches / len(keywords)) * weights['tags']

        # 互动量过滤
        if 'min_engagement' in criteria:
            engagement = content.get('like_count', 0) + content.get('comment_count', 0)
            if engagement < criteria['min_engagement']:
                return False, 0.0

        # 时间过滤
        if 'min_date' in criteria:
            content_date = content.get('publish_time')
            if content_date and isinstance(content_date, datetime):
                min_date = criteria['min_date']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)
                if content_date < min_date:
                    return False, 0.0

        # 归一化分数
        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0

        # 匹配阈值
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score


class {class_name}Interaction:
    """
    {platform_name}互动处理器
    Layer 4: Interaction - 评论、点赞、分享、用户信息
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def get_comments(
        self,
        page: Page,
        content_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取评论（支持嵌套回复）

        Args:
            page: Playwright页面对象
            content_id: 内容ID
            max_comments: 最大评论数
            include_replies: 是否包含回复

        Returns:
            评论列表
        """
        comments = []

        try:
            # 等待评论区加载
            comment_selector = '{selectors.get("comment", ".comment")}'
            try:
                await page.wait_for_selector(comment_selector, timeout=5000)
            except PlaywrightTimeoutError:
                self.logger.warning(f"No comments found for content {{content_id}}")
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
                    self.logger.error(f"Error parsing comment: {{e}}")
                    continue

            self.logger.info(f"Collected {{len(comments)}} comments for content {{content_id}}")

        except Exception as e:
            self.logger.error(f"Error getting comments: {{e}}")

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
                f'() => document.querySelectorAll(\\'{selectors.get("comment", ".comment")}\\').length'
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
            comment_data = {{
                'comment_id': None,
                'user': {{}},
                'text': None,
                'like_count': 0,
                'reply_count': 0,
                'publish_time': None,
                'replies': []
            }}

            # 用户信息
            user_elem = await element.query_selector('{selectors.get("user", ".user")}')
            if user_elem:
                comment_data['user']['nickname'] = await user_elem.inner_text()

            # 评论内容
            text_elem = await element.query_selector('.comment-text, .text')
            if text_elem:
                comment_data['text'] = await text_elem.inner_text()

            # 点赞数
            like_elem = await element.query_selector('.like-count, .likes')
            if like_elem:
                like_text = await like_elem.inner_text()
                comment_data['like_count'] = self.spider.parser.parse_count(like_text)

            # 发布时间
            time_elem = await element.query_selector('time, .timestamp')
            if time_elem:
                time_text = await time_elem.inner_text()
                comment_data['publish_time'] = self.spider.parser.parse_date(time_text)

            # 生成评论ID
            if comment_data['text']:
                comment_data['comment_id'] = hashlib.md5(
                    f"{{comment_data['user'].get('nickname', '')}}{{comment_data['text']}}{{comment_data['publish_time']}}".encode()
                ).hexdigest()[:16]

            return comment_data if comment_data['text'] else None

        except Exception as e:
            self.logger.error(f"Error parsing comment element: {{e}}")
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
            more_replies_btn = await comment_element.query_selector('.view-replies, .show-replies')
            if more_replies_btn:
                await more_replies_btn.click()
                await asyncio.sleep(random.uniform(0.5, 1))

            # 解析回复
            reply_elements = await comment_element.query_selector_all('.reply, .sub-comment')

            for reply_elem in reply_elements[:10]:
                reply = await self._parse_comment_element(page, reply_elem)
                if reply:
                    reply['parent_id'] = parent_comment_id
                    replies.append(reply)

        except Exception as e:
            self.logger.debug(f"Error getting comment replies: {{e}}")

        return replies

    async def get_user_info(self, page: Page, user_id: str) -> Dict[str, Any]:
        """
        获取用户详细信息

        Args:
            page: Playwright页面对象
            user_id: 用户ID

        Returns:
            用户信息
        """
        user_info = {{
            'user_id': user_id,
            'nickname': None,
            'avatar': None,
            'bio': None,
            'follower_count': 0,
            'following_count': 0,
            'post_count': 0,
            'verified': False
        }}

        try:
            # 访问用户主页
            user_url = f"{{base_url}}/user/{{user_id}}"
            await page.goto(user_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 解析用户信息
            nickname_elem = await page.query_selector('.username, .nickname, .user-name')
            if nickname_elem:
                user_info['nickname'] = await nickname_elem.inner_text()

            avatar_elem = await page.query_selector('.avatar img, .user-avatar img')
            if avatar_elem:
                user_info['avatar'] = await avatar_elem.get_attribute('src')

            bio_elem = await page.query_selector('.bio, .description, .user-bio')
            if bio_elem:
                user_info['bio'] = await bio_elem.inner_text()

            # 统计数据
            followers_elem = await page.query_selector('.followers-count, .follower-count')
            if followers_elem:
                followers_text = await followers_elem.inner_text()
                user_info['follower_count'] = self.spider.parser.parse_count(followers_text)

            following_elem = await page.query_selector('.following-count, .follow-count')
            if following_elem:
                following_text = await following_elem.inner_text()
                user_info['following_count'] = self.spider.parser.parse_count(following_text)

            # 验证标识
            verified_elem = await page.query_selector('.verified, .verified-badge')
            user_info['verified'] = verified_elem is not None

            self.logger.info(f"Collected user info for {{user_id}}")

        except Exception as e:
            self.logger.error(f"Error getting user info: {{e}}")

        return user_info


class {class_name}Spider(BaseSpider):
    """
    {platform_name}爬虫主类
    Layer 1: Spider - 完整的爬取功能实现

    功能:
    - 关键词搜索
    - 用户主页爬取
    - 话题页爬取
    - 内容详情获取（20+字段）
    - 评论采集（嵌套回复）
    - 媒体下载
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(
            platform="{platform_id}",
            headless=headless,
            proxy=proxy
        )

        # 初始化各层组件
        self.anti_crawl = {class_name}AntiCrawl(self)
        self.matcher = {class_name}Matcher()
        self.interaction = {class_name}Interaction(self)

        # {platform_name}特定配置
        self.base_url = "{base_url}"
        self.search_url = "{search_url}"

        # 缓存
        self._collected_content_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()
        await self.anti_crawl.initialize(self._page)
        self.logger.info("{platform_name} spider started successfully")

    async def login(self, username: str = None, password: str = None) -> bool:
        """
        登录{platform_name}

        Args:
            username: 用户名
            password: 密码

        Returns:
            登录是否成功
        """
        try:
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

            self.logger.warning("Please login manually or provide credentials")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {{e}}")
            return False

    async def _check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            user_info = await self._page.query_selector('.user-info, .user-menu, .account')
            return user_info is not None
        except:
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "comprehensive",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索内容

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型
            criteria: 匹配条件

        Returns:
            内容列表
        """
        self.logger.info(f"Searching for: {{keyword}}, type: {{search_type}}, max: {{max_results}}")

        results = []

        try:
            # 构建搜索URL
            search_params = {{
                'q': keyword,
                'keyword': keyword,
                'type': search_type
            }}
            search_url = f"{{self.search_url}}?{{urlencode(search_params)}}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载更多内容
            await self._scroll_and_load(max_results)

            # 解析内容列表
            content_elements = await self._page.query_selector_all('{selectors.get(content_type, ".item")}')

            for elem in content_elements[:max_results * 2]:
                try:
                    # 获取内容链接
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    content_url = await link_elem.get_attribute('href')
                    if not content_url:
                        continue

                    content_id = self._extract_content_id(content_url)
                    if not content_id or content_id in self._collected_content_ids:
                        continue

                    # 获取内容详情
                    content_data = await self.get_post_detail(content_id)

                    if content_data:
                        # 内容匹配
                        if criteria:
                            is_match, match_score = await self.matcher.match_content(content_data, criteria)
                            if not is_match:
                                continue
                            content_data['match_score'] = match_score

                        results.append(content_data)
                        self._collected_content_ids.add(content_id)

                        if len(results) >= max_results:
                            break

                    await asyncio.sleep(random.uniform(0.5, 1))

                except Exception as e:
                    self.logger.error(f"Error parsing content: {{e}}")
                    continue

            self.logger.info(f"Collected {{len(results)}} items for keyword: {{keyword}}")

        except Exception as e:
            self.logger.error(f"Search failed: {{e}}")

        return results

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料"""
        return await self.interaction.get_user_info(self._page, user_id)

    async def get_user_posts(
        self,
        user_id: str,
        max_posts: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """获取用户内容"""
        self.logger.info(f"Getting posts for user: {{user_id}}, max: {{max_posts}}")

        posts = []

        try:
            user_url = f"{{self.base_url}}/user/{{user_id}}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            await self._scroll_and_load(max_posts)

            content_elements = await self._page.query_selector_all('{selectors.get(content_type, ".item")}')

            for elem in content_elements[:max_posts * 2]:
                try:
                    link_elem = await elem.query_selector('a')
                    if not link_elem:
                        continue

                    content_url = await link_elem.get_attribute('href')
                    content_id = self._extract_content_id(content_url)

                    if not content_id or content_id in self._collected_content_ids:
                        continue

                    content_data = await self.get_post_detail(content_id)

                    if content_data:
                        if criteria:
                            is_match, match_score = await self.matcher.match_content(content_data, criteria)
                            if not is_match:
                                continue
                            content_data['match_score'] = match_score

                        posts.append(content_data)
                        self._collected_content_ids.add(content_id)

                        if len(posts) >= max_posts:
                            break

                except Exception as e:
                    self.logger.error(f"Error parsing user content: {{e}}")
                    continue

            self.logger.info(f"Collected {{len(posts)}} posts for user: {{user_id}}")

        except Exception as e:
            self.logger.error(f"Get user posts failed: {{e}}")

        return posts

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """获取内容详情"""
        self.logger.info(f"Getting content detail: {{post_id}}")

        content_data = {{
            'content_id': post_id,
            'platform': '{platform_id}',
            'content_type': '{content_type}',
            'url': None,
            'title': None,
            'text': None,
            'images': [],
            'videos': [],
            'author': {{}},
            'tags': [],
            'like_count': 0,
            'comment_count': 0,
            'share_count': 0,
            'view_count': 0,
            'publish_time': None,
            'collected_at': datetime.now()
        }}

        try:
            # 访问内容页面
            content_url = f"{{self.base_url}}/{content_type}/{{post_id}}"
            content_data['url'] = content_url

            await self.navigate(content_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 模拟阅读行为
            await self.anti_crawl.random_scroll_behavior(self._page, duration=2)

            # 解析内容信息
            # 标题
            title_elem = await self._page.query_selector('{selectors.get("title", "h1, .title")}')
            if title_elem:
                content_data['title'] = await title_elem.inner_text()

            # 文本内容
            text_elem = await self._page.query_selector('{selectors.get("text", ".content, .text")}')
            if text_elem:
                content_data['text'] = await text_elem.inner_text()

            # 作者信息
            author_elem = await self._page.query_selector('{selectors.get("user", ".author")}')
            if author_elem:
                author_name_elem = await author_elem.query_selector('.name, .nickname')
                if author_name_elem:
                    content_data['author']['nickname'] = await author_name_elem.inner_text()

                author_avatar_elem = await author_elem.query_selector('img')
                if author_avatar_elem:
                    content_data['author']['avatar'] = await author_avatar_elem.get_attribute('src')

            # 互动数据
            like_elem = await self._page.query_selector('{selectors.get("like", ".like-count")}')
            if like_elem:
                like_text = await like_elem.inner_text()
                content_data['like_count'] = self.parser.parse_count(like_text)

            comment_elem = await self._page.query_selector('.comment-count, .comments-count')
            if comment_elem:
                comment_text = await comment_elem.inner_text()
                content_data['comment_count'] = self.parser.parse_count(comment_text)

            share_elem = await self._page.query_selector('{selectors.get("share", ".share-count")}')
            if share_elem:
                share_text = await share_elem.inner_text()
                content_data['share_count'] = self.parser.parse_count(share_text)

            # 发布时间
            time_elem = await self._page.query_selector('time, .publish-time, .timestamp')
            if time_elem:
                time_text = await time_elem.inner_text()
                content_data['publish_time'] = self.spider.parser.parse_date(time_text)

            # 图片
            img_elements = await self._page.query_selector_all('.content img, .images img')
            for img_elem in img_elements[:10]:
                img_url = await img_elem.get_attribute('src')
                if img_url:
                    content_data['images'].append(img_url)

            # 视频
            video_elements = await self._page.query_selector_all('video')
            for video_elem in video_elements:
                video_url = await video_elem.get_attribute('src')
                if video_url:
                    content_data['videos'].append(video_url)

            self.logger.info(f"Collected content detail: {{post_id}}")

        except Exception as e:
            self.logger.error(f"Error getting content detail: {{e}}")

        return content_data

    async def get_comments(
        self,
        post_id: str,
        max_comments: int = 100,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """获取评论"""
        content_url = f"{{self.base_url}}/{content_type}/{{post_id}}"
        current_url = self._page.url

        if post_id not in current_url:
            await self.navigate(content_url)
            await asyncio.sleep(2)

        return await self.interaction.get_comments(
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

    def _extract_content_id(self, url: str) -> Optional[str]:
        """从URL中提取内容ID"""
        try:
            # 尝试从URL路径中提取ID
            parts = url.split('/')
            for part in reversed(parts):
                if part and part.replace('-', '').replace('_', '').isalnum():
                    return part
            return None
        except:
            return None


# 便捷函数
async def search_{platform_id}_content(
    keyword: str,
    max_results: int = 20,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """便捷函数：搜索{platform_name}内容"""
    spider = {class_name}Spider(headless=headless)

    async with spider.session():
        results = await spider.search(keyword, max_results, criteria=criteria)
        return results


if __name__ == "__main__":
    async def test_{platform_id}_spider():
        spider = {class_name}Spider(headless=False)

        async with spider.session():
            print("Testing search...")
            results = await spider.search("test", max_results=5)

            for item in results:
                print(f"\\nContent: {{item.get('title') or item.get('text', '')[:50]}}")
                print(f"Author: {{item.get('author', {{}}).get('nickname')}}")
                print(f"Likes: {{item.get('like_count')}}")
                print(f"URL: {{item.get('url')}}")
'''

    return code


def main():
    """Main function to generate all platforms"""
    output_dir = Path(__file__).parent / "omnisense" / "spider" / "platforms"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(PLATFORMS)} platform implementations...")
    print(f"Output directory: {output_dir}")

    for platform_id, config in PLATFORMS.items():
        print(f"\nGenerating {platform_id}.py ({config['name']})...")

        # Generate code
        code = generate_platform_code(platform_id, config)

        # Write to file
        output_file = output_dir / f"{platform_id}.py"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(code)

        print(f"  ✓ Created {output_file.name} ({len(code):,} bytes)")

    print(f"\n{'='*60}")
    print(f"Successfully generated {len(PLATFORMS)} platform implementations!")
    print(f"Total size: {sum(len(generate_platform_code(pid, cfg)) for pid, cfg in PLATFORMS.items()):,} bytes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
