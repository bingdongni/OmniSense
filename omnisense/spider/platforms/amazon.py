"""
Amazon Spider Implementation
完整的Amazon电商平台爬虫实现 - 企业级4层架构

架构说明:
- Layer 1: Spider Layer - 核心爬虫功能，多站点支持
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
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, parse_qs

from omnisense.spider.base import BaseSpider


# ============================================================================
# 数据模型定义
# ============================================================================

class AmazonSite(Enum):
    """Amazon站点枚举"""
    US = ("com", "https://www.amazon.com", "USD", "en_US")
    UK = ("co.uk", "https://www.amazon.co.uk", "GBP", "en_GB")
    DE = ("de", "https://www.amazon.de", "EUR", "de_DE")
    JP = ("co.jp", "https://www.amazon.co.jp", "JPY", "ja_JP")
    CN = ("cn", "https://www.amazon.cn", "CNY", "zh_CN")
    CA = ("ca", "https://www.amazon.ca", "CAD", "en_CA")
    FR = ("fr", "https://www.amazon.fr", "EUR", "fr_FR")
    IT = ("it", "https://www.amazon.it", "EUR", "it_IT")
    ES = ("es", "https://www.amazon.es", "EUR", "es_ES")
    IN = ("in", "https://www.amazon.in", "INR", "en_IN")

    def __init__(self, domain: str, base_url: str, currency: str, locale: str):
        self.domain = domain
        self.base_url = base_url
        self.currency = currency
        self.locale = locale


class FulfillmentType(Enum):
    """配送类型"""
    FBA = "FBA"  # Fulfilled by Amazon
    FBM = "FBM"  # Fulfilled by Merchant
    UNKNOWN = "UNKNOWN"


class ProductCondition(Enum):
    """商品状态"""
    NEW = "new"
    USED_LIKE_NEW = "used_like_new"
    USED_VERY_GOOD = "used_very_good"
    USED_GOOD = "used_good"
    USED_ACCEPTABLE = "used_acceptable"
    REFURBISHED = "refurbished"


@dataclass
class AmazonPrice:
    """价格信息"""
    amount: Decimal
    currency: str
    display_text: str
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[int] = None
    deal_price: Optional[Decimal] = None
    prime_exclusive: bool = False

    def get_savings(self) -> Optional[Decimal]:
        """计算节省金额"""
        if self.original_price and self.amount:
            return self.original_price - self.amount
        return None


@dataclass
class AmazonVariation:
    """商品变体"""
    asin: str
    name: str
    value: str
    price: Optional[AmazonPrice] = None
    available: bool = True
    image_url: Optional[str] = None

    # 变体属性
    color: Optional[str] = None
    size: Optional[str] = None
    style: Optional[str] = None


@dataclass
class AmazonSeller:
    """卖家信息"""
    seller_id: str
    seller_name: str
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    fulfillment_type: FulfillmentType = FulfillmentType.UNKNOWN

    # 卖家详细信息
    positive_feedback_percentage: Optional[int] = None
    ship_from_country: Optional[str] = None
    business_name: Optional[str] = None
    business_address: Optional[str] = None
    return_policy: Optional[str] = None


@dataclass
class AmazonReview:
    """商品评价"""
    review_id: str
    asin: str
    reviewer_name: str
    reviewer_id: Optional[str] = None

    # 评价内容
    rating: float = 0.0
    title: str = ""
    content: str = ""

    # 评价属性
    verified_purchase: bool = False
    helpful_votes: int = 0
    total_votes: int = 0

    # 时间和媒体
    review_date: Optional[datetime] = None
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)

    # 额外信息
    variant_info: Optional[str] = None
    vine_voice: bool = False
    early_reviewer: bool = False


@dataclass
class AmazonQA:
    """问答信息"""
    question_id: str
    asin: str
    question: str
    asker_name: str
    ask_date: Optional[datetime] = None

    # 答案列表
    answers: List[Dict[str, Any]] = field(default_factory=list)
    answer_count: int = 0
    votes: int = 0


@dataclass
class AmazonPriceHistory:
    """价格历史"""
    asin: str
    timestamp: datetime
    price: Decimal
    currency: str
    availability: str

    # 价格统计
    lowest_price: Optional[Decimal] = None
    highest_price: Optional[Decimal] = None
    average_price: Optional[Decimal] = None


@dataclass
class AmazonProduct:
    """Amazon商品完整信息"""
    asin: str
    title: str
    url: str
    site: str

    # 价格信息
    price: Optional[AmazonPrice] = None

    # 评分信息
    rating: Optional[float] = None
    review_count: int = 0
    answered_questions: int = 0

    # 商品详情
    brand: Optional[str] = None
    description: str = ""
    features: List[str] = field(default_factory=list)

    # 图片和媒体
    main_image: Optional[str] = None
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)

    # 分类和排名
    category: Optional[str] = None
    categories_path: List[str] = field(default_factory=list)
    best_seller_rank: Optional[Dict[str, int]] = None

    # 商品属性
    condition: ProductCondition = ProductCondition.NEW
    availability: str = ""
    in_stock: bool = False

    # 配送信息
    prime_eligible: bool = False
    free_shipping: bool = False
    delivery_date: Optional[str] = None

    # 卖家信息
    seller: Optional[AmazonSeller] = None

    # 变体信息
    variations: List[AmazonVariation] = field(default_factory=list)
    parent_asin: Optional[str] = None

    # 技术规格
    specifications: Dict[str, str] = field(default_factory=dict)
    dimensions: Optional[str] = None
    weight: Optional[str] = None

    # 时间戳
    scraped_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# Layer 2: Anti-Crawl Layer - 反爬虫机制
# ============================================================================

class AmazonAntiCrawl:
    """Amazon反爬虫处理层"""

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
        self.device_fingerprint = self._generate_device_fingerprint()
        self.captcha_solve_count = 0
        self.blocked_count = 0

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = int(time.time() * 1000)
        random_part = ''.join(random.choices('0123456789abcdef', k=16))
        return f"{timestamp}-{random_part}"

    def _generate_device_fingerprint(self) -> Dict[str, Any]:
        """生成设备指纹"""
        return {
            'screen_resolution': random.choice(['1920x1080', '2560x1440', '1366x768', '1440x900']),
            'color_depth': random.choice([24, 32]),
            'timezone_offset': random.choice([-480, -420, -360, -300, -240, 0, 60, 120]),
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
            'language': random.choice(['en-US', 'en-GB', 'de-DE', 'ja-JP', 'zh-CN']),
            'plugins': random.randint(3, 8),
            'canvas_hash': hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
        }

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.USER_AGENTS)

    def get_request_headers(self, site: AmazonSite, referer: Optional[str] = None) -> Dict[str, str]:
        """获取完整的请求头"""
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }

        if referer:
            headers['Referer'] = referer
            headers['Sec-Fetch-Site'] = 'same-origin'

        return headers

    async def smart_delay(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """智能延迟 - 模拟人类行为"""
        self.request_count += 1

        # 基础延迟
        base_delay = random.uniform(min_delay, max_delay)

        # 根据请求频率调整
        if self.request_count % 10 == 0:
            # 每10个请求增加额外延迟
            base_delay += random.uniform(3, 8)
            self.logger.debug(f"Adding extra delay after {self.request_count} requests")

        # 随机添加微小波动
        jitter = random.uniform(-0.5, 0.5)
        final_delay = max(0.5, base_delay + jitter)

        await asyncio.sleep(final_delay)
        self.last_request_time = time.time()

    async def exponential_backoff(self, attempt: int, base_delay: float = 2.0) -> float:
        """指数退避算法"""
        delay = min(base_delay * (2 ** attempt), 60)  # 最大60秒
        jitter = random.uniform(0, delay * 0.1)
        total_delay = delay + jitter

        self.logger.info(f"Exponential backoff: attempt {attempt}, waiting {total_delay:.2f}s")
        await asyncio.sleep(total_delay)
        return total_delay

    def detect_captcha(self, page_content: str) -> bool:
        """检测CAPTCHA"""
        captcha_indicators = [
            'captcha',
            'robot check',
            'Type the characters you see',
            'Enter the characters you see below',
            'api-services-support@amazon',
        ]

        content_lower = page_content.lower()
        for indicator in captcha_indicators:
            if indicator.lower() in content_lower:
                self.logger.warning(f"CAPTCHA detected: {indicator}")
                return True
        return False

    def detect_blocked(self, page_content: str) -> bool:
        """检测是否被封禁"""
        block_indicators = [
            'sorry, we just need to make sure',
            'unusual traffic',
            'automated access',
            'temporarily blocked',
        ]

        content_lower = page_content.lower()
        for indicator in block_indicators:
            if indicator.lower() in content_lower:
                self.logger.error(f"Access blocked: {indicator}")
                self.blocked_count += 1
                return True
        return False

    async def handle_captcha(self, page) -> bool:
        """处理CAPTCHA - 简单重试机制"""
        self.captcha_solve_count += 1
        self.logger.warning(f"Encountered CAPTCHA (count: {self.captcha_solve_count})")

        # 等待更长时间
        await asyncio.sleep(random.uniform(10, 20))

        # 刷新页面重试
        try:
            await page.reload()
            await asyncio.sleep(3)

            content = await page.content()
            if not self.detect_captcha(content):
                self.logger.info("CAPTCHA bypassed after reload")
                return True
        except Exception as e:
            self.logger.error(f"Failed to handle CAPTCHA: {e}")

        return False

    def should_rotate_session(self) -> bool:
        """判断是否需要轮换会话"""
        # 每50个请求或遇到3次CAPTCHA后轮换
        if self.request_count >= 50 or self.captcha_solve_count >= 3:
            return True
        return False

    def reset_session(self):
        """重置会话"""
        self.logger.info("Resetting session...")
        self.session_id = self._generate_session_id()
        self.device_fingerprint = self._generate_device_fingerprint()
        self.request_count = 0
        self.captcha_solve_count = 0


# ============================================================================
# Layer 3: Matcher Layer - 智能匹配和过滤
# ============================================================================

class AmazonMatcher:
    """Amazon商品匹配和过滤层"""

    def __init__(self, logger):
        self.logger = logger

    def filter_by_price(
        self,
        products: List[Dict[str, Any]],
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """按价格过滤商品"""
        filtered = []
        for product in products:
            price_str = product.get('price', '')
            if not price_str:
                continue

            try:
                # 提取数字价格
                price_value = self._extract_price_value(price_str)
                if price_value is None:
                    continue

                # 价格区间过滤
                if min_price is not None and price_value < min_price:
                    continue
                if max_price is not None and price_value > max_price:
                    continue

                filtered.append(product)
            except Exception as e:
                self.logger.debug(f"Failed to parse price {price_str}: {e}")
                continue

        self.logger.info(f"Price filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_rating(
        self,
        products: List[Dict[str, Any]],
        min_rating: Optional[float] = None,
        min_reviews: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """按评分和评价数过滤"""
        filtered = []
        for product in products:
            rating = product.get('rating')
            review_count = product.get('reviews_count', 0)

            # 评分过滤
            if min_rating is not None:
                if rating is None or rating < min_rating:
                    continue

            # 评价数过滤
            if min_reviews is not None:
                if review_count < min_reviews:
                    continue

            filtered.append(product)

        self.logger.info(f"Rating filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_prime(
        self,
        products: List[Dict[str, Any]],
        prime_only: bool = True
    ) -> List[Dict[str, Any]]:
        """过滤Prime商品"""
        if not prime_only:
            return products

        filtered = [p for p in products if p.get('prime', False)]
        self.logger.info(f"Prime filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_seller_type(
        self,
        products: List[Dict[str, Any]],
        amazon_only: bool = False,
        fba_only: bool = False
    ) -> List[Dict[str, Any]]:
        """按卖家类型过滤"""
        filtered = []
        for product in products:
            seller_info = product.get('seller', {})
            fulfillment = seller_info.get('fulfillment_type', 'UNKNOWN')

            if amazon_only:
                # 只要Amazon自营
                if seller_info.get('seller_name', '').lower() != 'amazon':
                    continue
            elif fba_only:
                # 只要FBA配送
                if fulfillment != 'FBA':
                    continue

            filtered.append(product)

        self.logger.info(f"Seller filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_availability(
        self,
        products: List[Dict[str, Any]],
        in_stock_only: bool = True
    ) -> List[Dict[str, Any]]:
        """按库存状态过滤"""
        if not in_stock_only:
            return products

        filtered = [p for p in products if p.get('in_stock', False)]
        self.logger.info(f"Stock filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_brand(
        self,
        products: List[Dict[str, Any]],
        brands: List[str]
    ) -> List[Dict[str, Any]]:
        """按品牌过滤"""
        if not brands:
            return products

        brands_lower = [b.lower() for b in brands]
        filtered = []

        for product in products:
            brand = product.get('brand', '').lower()
            if any(b in brand for b in brands_lower):
                filtered.append(product)

        self.logger.info(f"Brand filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def calculate_quality_score(self, product: Dict[str, Any]) -> float:
        """计算商品质量评分 (0-100)"""
        score = 0.0

        # 评分权重 40%
        rating = product.get('rating')
        if rating:
            score += (rating / 5.0) * 40

        # 评价数权重 20%
        review_count = product.get('reviews_count', 0)
        if review_count > 0:
            # 对数缩放，1000+评价得满分
            review_score = min(20, (review_count / 1000) * 20)
            score += review_score

        # Prime会员权重 15%
        if product.get('prime', False):
            score += 15

        # 卖家类型权重 15%
        seller = product.get('seller', {})
        if seller.get('seller_name', '').lower() == 'amazon':
            score += 15
        elif seller.get('fulfillment_type') == 'FBA':
            score += 10

        # 库存状态权重 10%
        if product.get('in_stock', False):
            score += 10

        return round(score, 2)

    def calculate_value_score(self, product: Dict[str, Any]) -> Optional[float]:
        """计算性价比评分"""
        rating = product.get('rating')
        price_str = product.get('price', '')

        if not rating or not price_str:
            return None

        try:
            price = self._extract_price_value(price_str)
            if price is None or price <= 0:
                return None

            # 性价比 = 评分 / log(价格)
            # 价格越低、评分越高，性价比越好
            import math
            value_score = rating / math.log10(max(price, 1))
            return round(value_score, 2)
        except Exception:
            return None

    def sort_products(
        self,
        products: List[Dict[str, Any]],
        sort_by: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """排序商品

        Args:
            sort_by: relevance, price_asc, price_desc, rating, reviews, quality, value
        """
        if sort_by == "relevance":
            return products

        try:
            if sort_by == "price_asc":
                products.sort(key=lambda p: self._extract_price_value(p.get('price', '')) or float('inf'))
            elif sort_by == "price_desc":
                products.sort(key=lambda p: self._extract_price_value(p.get('price', '')) or 0, reverse=True)
            elif sort_by == "rating":
                products.sort(key=lambda p: p.get('rating') or 0, reverse=True)
            elif sort_by == "reviews":
                products.sort(key=lambda p: p.get('reviews_count', 0), reverse=True)
            elif sort_by == "quality":
                products.sort(key=lambda p: self.calculate_quality_score(p), reverse=True)
            elif sort_by == "value":
                products.sort(key=lambda p: self.calculate_value_score(p) or 0, reverse=True)

            self.logger.info(f"Sorted {len(products)} products by {sort_by}")
        except Exception as e:
            self.logger.error(f"Failed to sort products: {e}")

        return products

    def _extract_price_value(self, price_str: str) -> Optional[float]:
        """从价格字符串提取数值"""
        if not price_str:
            return None

        try:
            # 移除货币符号和逗号
            price_clean = re.sub(r'[^\d.]', '', price_str)
            if price_clean:
                return float(price_clean)
        except Exception:
            pass

        return None


# ============================================================================
# Layer 4: Interaction Layer - 用户交互操作
# ============================================================================

class AmazonInteraction:
    """Amazon用户交互层"""

    def __init__(self, page, logger):
        self.page = page
        self.logger = logger

    async def add_to_cart(self, asin: str, quantity: int = 1) -> bool:
        """添加商品到购物车"""
        try:
            self.logger.info(f"Adding {asin} to cart (quantity: {quantity})")

            # 查找添加到购物车按钮
            add_to_cart_selectors = [
                '#add-to-cart-button',
                '#buy-now-button',
                'input[name="submit.add-to-cart"]',
            ]

            for selector in add_to_cart_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    # 设置数量
                    qty_selector = await self.page.query_selector('#quantity')
                    if qty_selector and quantity > 1:
                        await qty_selector.select_option(str(quantity))
                        await asyncio.sleep(0.5)

                    # 点击添加
                    await button.click()
                    await asyncio.sleep(2)

                    # 检查是否成功
                    success_indicator = await self.page.query_selector('[data-csa-c-content-id="sw-atc-confirmation"]')
                    if success_indicator:
                        self.logger.info("Successfully added to cart")
                        return True

            self.logger.warning("Could not find add to cart button")
            return False

        except Exception as e:
            self.logger.error(f"Failed to add to cart: {e}")
            return False

    async def add_to_wishlist(self, asin: str) -> bool:
        """添加到心愿单"""
        try:
            self.logger.info(f"Adding {asin} to wishlist")

            # 查找心愿单按钮
            wishlist_button = await self.page.query_selector('#add-to-wishlist-button-submit')
            if not wishlist_button:
                wishlist_button = await self.page.query_selector('[data-action="add-to-wishlist"]')

            if wishlist_button:
                await wishlist_button.click()
                await asyncio.sleep(2)
                self.logger.info("Successfully added to wishlist")
                return True

            self.logger.warning("Could not find wishlist button")
            return False

        except Exception as e:
            self.logger.error(f"Failed to add to wishlist: {e}")
            return False

    async def mark_review_helpful(self, review_id: str) -> bool:
        """标记评价有用"""
        try:
            self.logger.info(f"Marking review {review_id} as helpful")

            # 查找有用按钮
            helpful_button = await self.page.query_selector(f'[data-hook="helpful-button-{review_id}"]')
            if not helpful_button:
                helpful_button = await self.page.query_selector('.cr-vote-buttons button[data-hook="helpful-button"]')

            if helpful_button:
                await helpful_button.click()
                await asyncio.sleep(1)
                self.logger.info("Successfully marked as helpful")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to mark review helpful: {e}")
            return False

    async def follow_seller(self, seller_id: str) -> bool:
        """关注卖家"""
        try:
            self.logger.info(f"Following seller {seller_id}")

            follow_button = await self.page.query_selector('[data-action="follow-seller"]')
            if follow_button:
                await follow_button.click()
                await asyncio.sleep(1)
                self.logger.info("Successfully followed seller")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to follow seller: {e}")
            return False


# ============================================================================
# Layer 1: Spider Layer - 核心爬虫功能
# ============================================================================

class AmazonSpider(BaseSpider):
    """Amazon电商平台爬虫 - 完整4层架构实现"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="amazon", headless=headless, proxy=proxy)
        self.base_url = "https://www.amazon.com"
        self.api_base_url = "https://www.amazon.com"
        self.current_site = AmazonSite.US

        # 初始化各层
        self.anti_crawl = AmazonAntiCrawl(self.logger)
        self.matcher = AmazonMatcher(self.logger)
        self.interaction = None  # 在session启动后初始化

        # 价格历史缓存
        self.price_history_cache: Dict[str, List[AmazonPriceHistory]] = {}

    def _get_site_config(self, site: str) -> AmazonSite:
        """获取站点配置"""
        site_map = {
            'com': AmazonSite.US,
            'us': AmazonSite.US,
            'uk': AmazonSite.UK,
            'de': AmazonSite.DE,
            'jp': AmazonSite.JP,
            'cn': AmazonSite.CN,
            'ca': AmazonSite.CA,
            'fr': AmazonSite.FR,
            'it': AmazonSite.IT,
            'es': AmazonSite.ES,
            'in': AmazonSite.IN,
        }
        return site_map.get(site.lower(), AmazonSite.US)

    def switch_site(self, site: str):
        """切换Amazon站点"""
        self.current_site = self._get_site_config(site)
        self.base_url = self.current_site.base_url
        self.api_base_url = self.current_site.base_url
        self.logger.info(f"Switched to Amazon {self.current_site.domain} ({self.current_site.currency})")

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

                # 检测CAPTCHA
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
                self.logger.error(f"Navigation failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await self.anti_crawl.exponential_backoff(attempt)

        return False

    async def login(self, username: str, password: str) -> bool:
        """登录Amazon账户

        Args:
            username: 邮箱或手机号
            password: 密码

        Returns:
            bool: 登录是否成功
        """
        try:
            self.logger.info(f"Logging in to Amazon {self.current_site.domain} as {username}...")

            # 尝试使用已保存的cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self._safe_navigate(self.base_url)

                # 检查登录状态
                account_elem = await self._page.query_selector('#nav-link-accountList')
                if account_elem:
                    account_text = await account_elem.inner_text()
                    if 'Hello' in account_text or 'Hi,' in account_text:
                        self._is_logged_in = True
                        self.interaction = AmazonInteraction(self._page, self.logger)
                        self.logger.info("Logged in with saved cookies")
                        return True

            # 导航到登录页面
            signin_url = f"{self.base_url}/ap/signin"
            if not await self._safe_navigate(signin_url):
                self.logger.error("Failed to navigate to signin page")
                return False

            # 填写邮箱/手机号
            email_input = await self._page.wait_for_selector('#ap_email', timeout=10000)
            await email_input.fill(username)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # 点击继续按钮
            continue_btn = await self._page.query_selector('#continue')
            if continue_btn:
                await continue_btn.click()
                await asyncio.sleep(random.uniform(2, 3))

            # 填写密码
            password_input = await self._page.wait_for_selector('#ap_password', timeout=10000)
            await password_input.fill(password)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # 勾选"保持登录"
            remember_me = await self._page.query_selector('#rememberMeBox')
            if remember_me:
                is_checked = await remember_me.is_checked()
                if not is_checked:
                    await remember_me.click()
                    await asyncio.sleep(0.3)

            # 点击登录按钮
            signin_btn = await self._page.wait_for_selector('#signInSubmit', timeout=10000)
            await signin_btn.click()
            await asyncio.sleep(random.uniform(4, 6))

            # 处理可能的验证码或二次验证
            page_content = await self._page.content()
            if 'Two-Step Verification' in page_content or 'Enter OTP' in page_content:
                self.logger.warning("Two-factor authentication required - manual intervention needed")
                await asyncio.sleep(30)  # 等待用户手动输入验证码

            # 检查登录是否成功
            account_elem = await self._page.query_selector('#nav-link-accountList')
            if account_elem:
                self._is_logged_in = True
                self.interaction = AmazonInteraction(self._page, self.logger)
                await self._save_cookies()
                self.logger.info("Login successful")
                return True

            self.logger.error("Login failed - could not verify login status")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(
        self,
        keyword: str,
        site: str = 'com',
        max_results: int = 20,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        prime_only: bool = False,
        sort_by: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """搜索Amazon商品 - 支持多站点和高级过滤

        Args:
            keyword: 搜索关键词
            site: 站点代码 (com, uk, de, jp, cn等)
            max_results: 最大结果数
            category: 分类筛选
            min_price: 最低价格
            max_price: 最高价格
            prime_only: 仅Prime商品
            sort_by: 排序方式 (relevance, price_asc, price_desc, rating, reviews)

        Returns:
            商品列表
        """
        try:
            # 切换站点
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Searching Amazon {self.current_site.domain} for '{keyword}'")

            # 构建搜索URL
            search_params = {'k': keyword}

            # 添加分类
            if category:
                search_params['i'] = category

            # 添加价格范围
            if min_price is not None:
                search_params['low-price'] = str(min_price)
            if max_price is not None:
                search_params['high-price'] = str(max_price)

            # Prime筛选
            if prime_only:
                search_params['prime'] = 'true'

            # 排序
            sort_map = {
                'price_asc': 'price-asc-rank',
                'price_desc': 'price-desc-rank',
                'rating': 'review-rank',
                'reviews': 'review-count-rank',
            }
            if sort_by in sort_map:
                search_params['s'] = sort_map[sort_by]

            search_url = f"{self.base_url}/s?{urlencode(search_params)}"

            if not await self._safe_navigate(search_url):
                self.logger.error("Failed to navigate to search page")
                return []

            # 滚动加载更多商品
            pages_to_load = (max_results // 16) + 1
            for i in range(min(pages_to_load, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1.5, 2.5))

            results = []
            product_elements = await self._page.query_selector_all('[data-component-type="s-search-result"]')

            self.logger.info(f"Found {len(product_elements)} product elements on page")

            for elem in product_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"Failed to parse product: {e}")
                    continue

            self.logger.info(f"Successfully parsed {len(results)} products")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def _parse_search_result(self, elem) -> Dict[str, Any]:
        """解析搜索结果中的单个商品"""
        result = {
            'platform': self.platform,
            'type': 'product',
            'site': self.current_site.domain
        }

        # 商品标题和链接
        title_elem = await elem.query_selector('h2 a')
        if title_elem:
            result['title'] = (await title_elem.inner_text()).strip()
            href = await title_elem.get_attribute('href')
            result['url'] = f"{self.base_url}{href}" if not href.startswith('http') else href

            # 提取ASIN
            if '/dp/' in href:
                result['id'] = href.split('/dp/')[-1].split('/')[0].split('?')[0]
            elif '/gp/product/' in href:
                result['id'] = href.split('/gp/product/')[-1].split('/')[0].split('?')[0]
            elif 'asin=' in href:
                result['id'] = href.split('asin=')[-1].split('&')[0]

        # 价格信息
        price_elem = await elem.query_selector('.a-price .a-offscreen')
        if price_elem:
            result['price'] = (await price_elem.inner_text()).strip()

        # 原价（如果有折扣）
        original_price_elem = await elem.query_selector('.a-price[data-a-strike="true"] .a-offscreen')
        if original_price_elem:
            result['original_price'] = (await original_price_elem.inner_text()).strip()

        # 评分
        rating_elem = await elem.query_selector('.a-icon-star-small .a-icon-alt')
        if rating_elem:
            rating_text = await rating_elem.inner_text()
            try:
                result['rating'] = float(rating_text.split()[0])
            except:
                pass

        # 评价数量
        reviews_elem = await elem.query_selector('[aria-label*="stars"]')
        if reviews_elem:
            reviews_text = await reviews_elem.get_attribute('aria-label')
            result['reviews_count'] = self.parser.parse_count(reviews_text)
        else:
            # 备用选择器
            reviews_elem2 = await elem.query_selector('.a-size-base.s-underline-text')
            if reviews_elem2:
                reviews_text = await reviews_elem2.inner_text()
                result['reviews_count'] = self.parser.parse_count(reviews_text)

        # 商品图片
        img = await elem.query_selector('img.s-image')
        if img:
            result['thumbnail'] = await img.get_attribute('src')

        # Prime标识
        prime = await elem.query_selector('[aria-label="Amazon Prime"]')
        result['prime'] = prime is not None

        # 配送信息
        delivery_elem = await elem.query_selector('[data-cy="delivery-recipe"]')
        if delivery_elem:
            result['delivery_info'] = (await delivery_elem.inner_text()).strip()

        # 库存状态
        availability_elem = await elem.query_selector('.a-size-base.a-color-price')
        if availability_elem:
            availability_text = await availability_elem.inner_text()
            result['in_stock'] = 'in stock' in availability_text.lower()
        else:
            result['in_stock'] = True  # 默认有货

        # 品牌信息
        brand_elem = await elem.query_selector('.a-size-base-plus')
        if brand_elem:
            result['brand'] = (await brand_elem.inner_text()).strip()

        return result

    async def get_user_profile(self, user_id: str, site: str = 'com') -> Dict[str, Any]:
        """获取Amazon卖家资料

        Args:
            user_id: 卖家ID
            site: 站点代码

        Returns:
            卖家资料信息
        """
        try:
            # 切换站点
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting seller profile: {user_id}")

            # 尝试卖家店铺页面
            profile_url = f"{self.base_url}/sp?seller={user_id}"
            if not await self._safe_navigate(profile_url):
                self.logger.error("Failed to navigate to seller profile")
                return {}

            profile = {
                'user_id': user_id,
                'platform': self.platform,
                'site': self.current_site.domain,
                'type': 'seller'
            }

            # 卖家名称
            name_selectors = ['#sellerName', '.a-spacing-medium h1', '[data-hook="seller-name"]']
            for selector in name_selectors:
                name_elem = await self._page.query_selector(selector)
                if name_elem:
                    profile['seller_name'] = (await name_elem.inner_text()).strip()
                    break

            # 卖家评分
            rating_elem = await self._page.query_selector('#seller-feedback-summary')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                profile['rating_summary'] = rating_text.strip()

                # 解析评分百分比
                match = re.search(r'(\d+)%', rating_text)
                if match:
                    profile['positive_feedback_percentage'] = int(match.group(1))

            # 评分数量
            rating_count_elem = await self._page.query_selector('[data-hook="seller-rating-count"]')
            if rating_count_elem:
                count_text = await rating_count_elem.inner_text()
                profile['rating_count'] = self.parser.parse_count(count_text)

            # 商家地址
            address_elem = await self._page.query_selector('[data-hook="seller-business-address"]')
            if address_elem:
                profile['business_address'] = (await address_elem.inner_text()).strip()

            # 退货政策
            return_policy_elem = await self._page.query_selector('[data-hook="return-policy"]')
            if return_policy_elem:
                profile['return_policy'] = (await return_policy_elem.inner_text()).strip()

            self.logger.info(f"Successfully retrieved seller profile for {user_id}")
            return profile

        except Exception as e:
            self.logger.error(f"Failed to get seller profile: {e}")
            return {}

    async def get_user_posts(self, seller_id: str, site: str = 'com', max_posts: int = 20) -> List[Dict[str, Any]]:
        """获取卖家的商品列表

        Args:
            seller_id: 卖家ID
            site: 站点代码
            max_posts: 最大商品数

        Returns:
            商品列表
        """
        try:
            # 切换站点
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting products from seller: {seller_id}")

            # 导航到卖家店铺
            seller_url = f"{self.base_url}/s?me={seller_id}"
            if not await self._safe_navigate(seller_url):
                self.logger.error("Failed to navigate to seller storefront")
                return []

            # 滚动加载
            for i in range(min((max_posts // 16) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1.5, 2.5))

            posts = []
            product_elements = await self._page.query_selector_all('[data-component-type="s-search-result"]')

            for elem in product_elements[:max_posts]:
                try:
                    post = await self._parse_search_result(elem)
                    if post and post.get('id'):
                        post['seller_id'] = seller_id
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse product: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} products from seller")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get seller products: {e}")
            return []

    async def get_post_detail(self, asin: str, site: str = 'com') -> Dict[str, Any]:
        """获取Amazon商品详细信息

        Args:
            asin: 商品ASIN
            site: 站点代码

        Returns:
            商品详细信息
        """
        try:
            # 切换站点
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting product detail: {asin}")

            # 导航到商品页面
            product_url = f"{self.base_url}/dp/{asin}"
            if not await self._safe_navigate(product_url):
                self.logger.error("Failed to navigate to product page")
                return {}

            post = {
                'id': asin,
                'url': product_url,
                'platform': self.platform,
                'site': self.current_site.domain,
                'type': 'product'
            }

            # 商品标题
            title_elem = await self._page.query_selector('#productTitle')
            if title_elem:
                post['title'] = (await title_elem.inner_text()).strip()

            # 价格信息
            price_elem = await self._page.query_selector('.a-price .a-offscreen')
            if price_elem:
                post['price'] = (await price_elem.inner_text()).strip()

            # 原价
            original_price_elem = await self._page.query_selector('.a-price.a-text-price .a-offscreen')
            if original_price_elem:
                post['original_price'] = (await original_price_elem.inner_text()).strip()

            # 折扣百分比
            discount_elem = await self._page.query_selector('.savingsPercentage')
            if discount_elem:
                discount_text = await discount_elem.inner_text()
                match = re.search(r'(\d+)%', discount_text)
                if match:
                    post['discount_percentage'] = int(match.group(1))

            # 评分
            rating_elem = await self._page.query_selector('#acrPopover .a-icon-alt')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                try:
                    post['rating'] = float(rating_text.split()[0])
                except:
                    pass

            # 评价数量
            review_count_elem = await self._page.query_selector('#acrCustomerReviewText')
            if review_count_elem:
                post['reviews_count'] = self.parser.parse_count(await review_count_elem.inner_text())

            # 问答数量
            qa_count_elem = await self._page.query_selector('#askATFLink')
            if qa_count_elem:
                qa_text = await qa_count_elem.inner_text()
                post['answered_questions'] = self.parser.parse_count(qa_text)

            # 品牌
            brand_elem = await self._page.query_selector('#bylineInfo')
            if brand_elem:
                brand_text = await brand_elem.inner_text()
                post['brand'] = brand_text.replace('Visit the', '').replace('Store', '').replace('Brand:', '').strip()

            # 商品描述（特性列表）
            features = []
            feature_bullets = await self._page.query_selector_all('#feature-bullets li')
            for bullet in feature_bullets:
                text = (await bullet.inner_text()).strip()
                if text and len(text) > 5:
                    features.append(text)
            post['features'] = features

            # 商品描述
            desc_elem = await self._page.query_selector('#productDescription')
            if desc_elem:
                post['description'] = (await desc_elem.inner_text()).strip()

            # 商品图片
            images = []
            main_image = await self._page.query_selector('#landingImage')
            if main_image:
                main_src = await main_image.get_attribute('src')
                if main_src:
                    post['main_image'] = main_src
                    images.append(main_src)

            # 其他图片
            image_thumbs = await self._page.query_selector_all('#altImages img')
            for img in image_thumbs[:10]:
                src = await img.get_attribute('src')
                if src and src not in images:
                    # 替换为高清图
                    src_hd = src.replace('_SS40_', '_SL1500_').replace('_AC_US40_', '_AC_SL1500_')
                    images.append(src_hd)
            post['images'] = images

            # 库存状态
            availability_elem = await self._page.query_selector('#availability')
            if availability_elem:
                availability_text = (await availability_elem.inner_text()).strip()
                post['availability'] = availability_text
                post['in_stock'] = 'in stock' in availability_text.lower()

            # Prime标识
            prime_elem = await self._page.query_selector('#priceBadging_feature_div i.a-icon-prime')
            post['prime'] = prime_elem is not None

            # 配送信息
            delivery_elem = await self._page.query_selector('#mir-layout-DELIVERY_BLOCK')
            if delivery_elem:
                post['delivery_info'] = (await delivery_elem.inner_text()).strip()

            # 卖家信息
            seller_info = await self._parse_seller_info()
            if seller_info:
                post['seller'] = seller_info

            # 商品规格
            specifications = await self._parse_specifications()
            if specifications:
                post['specifications'] = specifications

            # Best Seller排名
            bsr = await self._parse_best_seller_rank()
            if bsr:
                post['best_seller_rank'] = bsr

            # 分类路径
            categories = await self._parse_categories()
            if categories:
                post['categories_path'] = categories

            # 变体信息
            variations = await self._parse_variations(asin)
            if variations:
                post['variations'] = variations

            self.logger.info(f"Successfully retrieved product detail for {asin}")
            return post

        except Exception as e:
            self.logger.error(f"Failed to get product detail: {e}")
            return {}

    async def get_comments(self, asin: str, site: str = 'com', max_comments: int = 100) -> List[Dict[str, Any]]:
        """获取Amazon商品评价

        Args:
            asin: 商品ASIN
            site: 站点代码
            max_comments: 最大评价数

        Returns:
            评价列表
        """
        try:
            # 切换站点
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting reviews for product: {asin}")

            # 导航到评价页面
            reviews_url = f"{self.base_url}/product-reviews/{asin}"
            if not await self._safe_navigate(reviews_url):
                self.logger.error("Failed to navigate to reviews page")
                return []

            comments = []
            pages_loaded = 0
            max_pages = (max_comments // 10) + 1

            while len(comments) < max_comments and pages_loaded < max_pages:
                # 解析当前页面的评价
                review_elements = await self._page.query_selector_all('[data-hook="review"]')

                for elem in review_elements:
                    if len(comments) >= max_comments:
                        break

                    try:
                        comment = await self._parse_review(elem, asin)
                        if comment and comment.get('content'):
                            comments.append(comment)

                    except Exception as e:
                        self.logger.warning(f"Failed to parse review: {e}")
                        continue

                pages_loaded += 1

                # 检查是否有下一页
                if len(comments) < max_comments and pages_loaded < max_pages:
                    next_btn = await self._page.query_selector('.a-pagination .a-last:not(.a-disabled) a')
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(random.uniform(2, 4))
                    else:
                        break

            self.logger.info(f"Got {len(comments)} reviews")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get reviews: {e}")
            return []

    async def _parse_review(self, elem, asin: str) -> Dict[str, Any]:
        """解析单个评价"""
        comment = {
            'post_id': asin,
            'platform': self.platform,
            'site': self.current_site.domain,
            'type': 'review'
        }

        # 评价ID
        review_id_attr = await elem.get_attribute('id')
        if review_id_attr:
            comment['id'] = review_id_attr

        # 评论者名称
        reviewer_elem = await elem.query_selector('.a-profile-name')
        if reviewer_elem:
            comment['username'] = (await reviewer_elem.inner_text()).strip()

        # 评分
        rating_elem = await elem.query_selector('[data-hook="review-star-rating"] .a-icon-alt')
        if rating_elem:
            rating_text = await rating_elem.inner_text()
            try:
                comment['rating'] = float(rating_text.split()[0])
            except:
                pass

        # 评价标题
        title_elem = await elem.query_selector('[data-hook="review-title"]')
        if title_elem:
            title_text = (await title_elem.inner_text()).strip()
            # 移除评分前缀
            comment['title'] = re.sub(r'^\d+\.\d+\s+out of \d+ stars\s*', '', title_text)

        # 评价内容
        text_elem = await elem.query_selector('[data-hook="review-body"]')
        if text_elem:
            comment['content'] = (await text_elem.inner_text()).strip()

        # 评价日期
        date_elem = await elem.query_selector('[data-hook="review-date"]')
        if date_elem:
            date_text = await date_elem.inner_text()
            comment['created_at'] = self.parser.parse_date(date_text)

        # 有用投票数
        helpful_elem = await elem.query_selector('[data-hook="helpful-vote-statement"]')
        if helpful_elem:
            helpful_text = await helpful_elem.inner_text()
            comment['helpful_votes'] = self.parser.parse_count(helpful_text)
        else:
            comment['helpful_votes'] = 0

        # Verified Purchase标识
        verified_elem = await elem.query_selector('[data-hook="avp-badge"]')
        comment['verified_purchase'] = verified_elem is not None

        # Vine Voice标识
        vine_elem = await elem.query_selector('[data-hook="vine-badge"]')
        comment['vine_voice'] = vine_elem is not None

        # 评价图片
        images = []
        image_elems = await elem.query_selector_all('[data-hook="review-image-tile"] img')
        for img in image_elems:
            src = await img.get_attribute('src')
            if src:
                images.append(src)
        comment['images'] = images

        # 变体信息
        variant_elem = await elem.query_selector('[data-hook="format-strip"]')
        if variant_elem:
            comment['variant_info'] = (await variant_elem.inner_text()).strip()

        return comment

    # ========================================================================
    # 辅助解析方法
    # ========================================================================

    async def _parse_seller_info(self) -> Optional[Dict[str, Any]]:
        """解析卖家信息"""
        try:
            seller_info = {}

            # 卖家名称
            seller_elem = await self._page.query_selector('#sellerProfileTriggerId')
            if seller_elem:
                seller_info['seller_name'] = (await seller_elem.inner_text()).strip()

            # 配送方式
            fulfillment_elem = await self._page.query_selector('#merchant-info')
            if fulfillment_elem:
                fulfillment_text = await fulfillment_elem.inner_text()
                if 'Fulfilled by Amazon' in fulfillment_text or 'Ships from Amazon' in fulfillment_text:
                    seller_info['fulfillment_type'] = 'FBA'
                else:
                    seller_info['fulfillment_type'] = 'FBM'

            return seller_info if seller_info else None

        except Exception as e:
            self.logger.debug(f"Failed to parse seller info: {e}")
            return None

    async def _parse_specifications(self) -> Dict[str, str]:
        """解析商品规格"""
        specifications = {}

        try:
            # 技术规格表格
            spec_tables = await self._page.query_selector_all('#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr')
            for row in spec_tables:
                try:
                    th = await row.query_selector('th')
                    td = await row.query_selector('td')
                    if th and td:
                        key = (await th.inner_text()).strip()
                        value = (await td.inner_text()).strip()
                        specifications[key] = value
                except:
                    continue

            # 详细信息列表
            detail_bullets = await self._page.query_selector_all('#detailBullets_feature_div li')
            for bullet in detail_bullets:
                try:
                    text = await bullet.inner_text()
                    if ':' in text:
                        parts = text.split(':', 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        specifications[key] = value
                except:
                    continue

        except Exception as e:
            self.logger.debug(f"Failed to parse specifications: {e}")

        return specifications

    async def _parse_best_seller_rank(self) -> Optional[Dict[str, int]]:
        """解析Best Seller排名"""
        try:
            bsr = {}

            # 查找BSR信息
            bsr_elem = await self._page.query_selector('#detailBulletsWrapper_feature_div, #productDetails_detailBullets_sections1')
            if bsr_elem:
                bsr_text = await bsr_elem.inner_text()

                # 提取排名信息
                matches = re.findall(r'#([\d,]+)\s+in\s+([^()\n]+)', bsr_text)
                for rank_str, category in matches:
                    rank = int(rank_str.replace(',', ''))
                    category = category.strip()
                    bsr[category] = rank

            return bsr if bsr else None

        except Exception as e:
            self.logger.debug(f"Failed to parse BSR: {e}")
            return None

    async def _parse_categories(self) -> List[str]:
        """解析分类路径"""
        categories = []

        try:
            # 面包屑导航
            breadcrumb_elems = await self._page.query_selector_all('#wayfinding-breadcrumbs_feature_div a')
            for elem in breadcrumb_elems:
                category = (await elem.inner_text()).strip()
                if category:
                    categories.append(category)

        except Exception as e:
            self.logger.debug(f"Failed to parse categories: {e}")

        return categories

    async def _parse_variations(self, asin: str) -> List[Dict[str, Any]]:
        """解析商品变体"""
        variations = []

        try:
            # 颜色变体
            color_swatches = await self._page.query_selector_all('#variation_color_name li')
            for swatch in color_swatches[:20]:
                try:
                    variation = {}

                    # 变体ASIN
                    asin_attr = await swatch.get_attribute('data-defaultasin')
                    if asin_attr:
                        variation['asin'] = asin_attr

                    # 颜色名称
                    title_attr = await swatch.get_attribute('title')
                    if title_attr:
                        variation['color'] = title_attr.strip()

                    # 图片
                    img = await swatch.query_selector('img')
                    if img:
                        variation['image_url'] = await img.get_attribute('src')

                    if variation.get('asin'):
                        variations.append(variation)

                except:
                    continue

            # 尺寸变体
            size_options = await self._page.query_selector_all('#variation_size_name option')
            for option in size_options[:20]:
                try:
                    variation = {}

                    # 尺寸名称
                    size_text = await option.inner_text()
                    if size_text:
                        variation['size'] = size_text.strip()

                    # 变体ASIN
                    asin_attr = await option.get_attribute('data-a-html-content')
                    if asin_attr:
                        variation['asin'] = asin_attr

                    if variation.get('size'):
                        variations.append(variation)

                except:
                    continue

        except Exception as e:
            self.logger.debug(f"Failed to parse variations: {e}")

        return variations

    # ========================================================================
    # 扩展功能方法
    # ========================================================================

    async def get_best_sellers(
        self,
        category: str = "electronics",
        site: str = 'com',
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """获取Best Seller榜单

        Args:
            category: 分类名称
            site: 站点代码
            max_results: 最大结果数

        Returns:
            畅销商品列表
        """
        try:
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting best sellers in {category}")

            # 构建Best Sellers URL
            bestsellers_url = f"{self.base_url}/Best-Sellers-{category}/zgbs/{category}"
            if not await self._safe_navigate(bestsellers_url):
                self.logger.error("Failed to navigate to best sellers page")
                return []

            results = []
            product_elements = await self._page.query_selector_all('.zg-item-immersion')

            for elem in product_elements[:max_results]:
                try:
                    product = {'platform': self.platform, 'site': self.current_site.domain, 'type': 'bestseller'}

                    # 排名
                    rank_elem = await elem.query_selector('.zg-badge-text')
                    if rank_elem:
                        rank_text = await rank_elem.inner_text()
                        match = re.search(r'#(\d+)', rank_text)
                        if match:
                            product['rank'] = int(match.group(1))

                    # 商品链接和ASIN
                    link_elem = await elem.query_selector('a.a-link-normal')
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        if href:
                            product['url'] = f"{self.base_url}{href}" if not href.startswith('http') else href
                            if '/dp/' in href:
                                product['id'] = href.split('/dp/')[-1].split('/')[0].split('?')[0]

                    # 商品标题
                    title_elem = await elem.query_selector('.p13n-sc-truncate')
                    if title_elem:
                        product['title'] = (await title_elem.inner_text()).strip()

                    # 评分
                    rating_elem = await elem.query_selector('.a-icon-star-small .a-icon-alt')
                    if rating_elem:
                        rating_text = await rating_elem.inner_text()
                        try:
                            product['rating'] = float(rating_text.split()[0])
                        except:
                            pass

                    # 评价数
                    reviews_elem = await elem.query_selector('.a-size-small.a-link-normal')
                    if reviews_elem:
                        reviews_text = await reviews_elem.inner_text()
                        product['reviews_count'] = self.parser.parse_count(reviews_text)

                    # 价格
                    price_elem = await elem.query_selector('.p13n-sc-price')
                    if price_elem:
                        product['price'] = (await price_elem.inner_text()).strip()

                    if product.get('id'):
                        results.append(product)

                except Exception as e:
                    self.logger.warning(f"Failed to parse bestseller: {e}")
                    continue

            self.logger.info(f"Got {len(results)} best sellers")
            return results

        except Exception as e:
            self.logger.error(f"Failed to get best sellers: {e}")
            return []

    async def get_deals(
        self,
        site: str = 'com',
        deal_type: str = "today",
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """获取促销商品

        Args:
            site: 站点代码
            deal_type: 促销类型 (today, lightning, upcoming)
            max_results: 最大结果数

        Returns:
            促销商品列表
        """
        try:
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting {deal_type} deals")

            # 构建促销页面URL
            deals_url = f"{self.base_url}/gp/goldbox"
            if not await self._safe_navigate(deals_url):
                self.logger.error("Failed to navigate to deals page")
                return []

            # 滚动加载
            for i in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1.5, 2.5))

            results = []
            deal_elements = await self._page.query_selector_all('[data-deal-id]')

            for elem in deal_elements[:max_results]:
                try:
                    deal = {'platform': self.platform, 'site': self.current_site.domain, 'type': 'deal'}

                    # Deal ID
                    deal_id = await elem.get_attribute('data-deal-id')
                    if deal_id:
                        deal['deal_id'] = deal_id

                    # 商品标题
                    title_elem = await elem.query_selector('[data-testid="deal-title"]')
                    if title_elem:
                        deal['title'] = (await title_elem.inner_text()).strip()

                    # 商品链接和ASIN
                    link_elem = await elem.query_selector('a[href*="/dp/"]')
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        if href:
                            deal['url'] = f"{self.base_url}{href}" if not href.startswith('http') else href
                            if '/dp/' in href:
                                deal['id'] = href.split('/dp/')[-1].split('/')[0].split('?')[0]

                    # 折扣价格
                    price_elem = await elem.query_selector('[data-testid="deal-price"]')
                    if price_elem:
                        deal['price'] = (await price_elem.inner_text()).strip()

                    # 原价
                    original_price_elem = await elem.query_selector('[data-testid="list-price"]')
                    if original_price_elem:
                        deal['original_price'] = (await original_price_elem.inner_text()).strip()

                    # 折扣百分比
                    discount_elem = await elem.query_selector('[data-testid="deal-badge-price"]')
                    if discount_elem:
                        discount_text = await discount_elem.inner_text()
                        match = re.search(r'(\d+)%', discount_text)
                        if match:
                            deal['discount_percentage'] = int(match.group(1))

                    # 结束时间
                    timer_elem = await elem.query_selector('[data-testid="deal-timer"]')
                    if timer_elem:
                        deal['ends_in'] = (await timer_elem.inner_text()).strip()

                    if deal.get('id'):
                        results.append(deal)

                except Exception as e:
                    self.logger.warning(f"Failed to parse deal: {e}")
                    continue

            self.logger.info(f"Got {len(results)} deals")
            return results

        except Exception as e:
            self.logger.error(f"Failed to get deals: {e}")
            return []

    async def get_questions_and_answers(
        self,
        asin: str,
        site: str = 'com',
        max_qa: int = 50
    ) -> List[Dict[str, Any]]:
        """获取商品问答

        Args:
            asin: 商品ASIN
            site: 站点代码
            max_qa: 最大问答数

        Returns:
            问答列表
        """
        try:
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting Q&A for product: {asin}")

            # 导航到问答页面
            qa_url = f"{self.base_url}/ask/questions/asin/{asin}"
            if not await self._safe_navigate(qa_url):
                self.logger.error("Failed to navigate to Q&A page")
                return []

            qa_list = []
            question_elements = await self._page.query_selector_all('.a-spacing-base.askTeaserQuestions')

            for elem in question_elements[:max_qa]:
                try:
                    qa = {'asin': asin, 'platform': self.platform, 'site': self.current_site.domain, 'type': 'qa'}

                    # 问题
                    question_elem = await elem.query_selector('.a-text-bold')
                    if question_elem:
                        qa['question'] = (await question_elem.inner_text()).strip()

                    # 提问者
                    asker_elem = await elem.query_selector('.a-color-tertiary')
                    if asker_elem:
                        asker_text = await asker_elem.inner_text()
                        qa['asker'] = asker_text.strip()

                    # 答案
                    answers = []
                    answer_elements = await elem.query_selector_all('.askAnswerText')
                    for ans_elem in answer_elements[:5]:
                        answer_text = (await ans_elem.inner_text()).strip()
                        if answer_text:
                            answers.append(answer_text)
                    qa['answers'] = answers
                    qa['answer_count'] = len(answers)

                    # 投票数
                    votes_elem = await elem.query_selector('.count')
                    if votes_elem:
                        votes_text = await votes_elem.inner_text()
                        qa['votes'] = self.parser.parse_count(votes_text)

                    if qa.get('question'):
                        qa['id'] = hashlib.md5(qa['question'].encode()).hexdigest()[:16]
                        qa_list.append(qa)

                except Exception as e:
                    self.logger.warning(f"Failed to parse Q&A: {e}")
                    continue

            self.logger.info(f"Got {len(qa_list)} Q&A items")
            return qa_list

        except Exception as e:
            self.logger.error(f"Failed to get Q&A: {e}")
            return []

    async def track_price_history(
        self,
        asin: str,
        site: str = 'com',
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """追踪商品价格历史

        Args:
            asin: 商品ASIN
            site: 站点代码
            days: 追踪天数

        Returns:
            价格历史记录
        """
        try:
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Tracking price history for {asin}")

            # 检查缓存
            cache_key = f"{asin}_{site}"
            if cache_key in self.price_history_cache:
                cached_history = self.price_history_cache[cache_key]
                recent_history = [
                    h for h in cached_history
                    if (datetime.now() - h['timestamp']).days <= days
                ]
                if recent_history:
                    self.logger.info(f"Returning {len(recent_history)} cached price records")
                    return [self._price_history_to_dict(h) for h in recent_history]

            # 获取当前价格
            product_detail = await self.get_post_detail(asin, site)
            if not product_detail:
                return []

            # 创建价格记录
            price_record = {
                'asin': asin,
                'site': site,
                'timestamp': datetime.now().isoformat(),
                'price': product_detail.get('price'),
                'availability': product_detail.get('availability', ''),
                'in_stock': product_detail.get('in_stock', False)
            }

            # 保存到缓存
            if cache_key not in self.price_history_cache:
                self.price_history_cache[cache_key] = []
            self.price_history_cache[cache_key].append(price_record)

            self.logger.info(f"Tracked price: {price_record['price']}")
            return [price_record]

        except Exception as e:
            self.logger.error(f"Failed to track price history: {e}")
            return []

    def _price_history_to_dict(self, history) -> Dict[str, Any]:
        """将价格历史对象转换为字典"""
        if isinstance(history, dict):
            return history
        return {
            'asin': history.get('asin'),
            'timestamp': history.get('timestamp'),
            'price': history.get('price'),
            'availability': history.get('availability'),
        }

    async def search_by_category(
        self,
        category: str,
        site: str = 'com',
        max_results: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """按分类浏览商品

        Args:
            category: 分类名称或ID
            site: 站点代码
            max_results: 最大结果数
            filters: 额外过滤条件

        Returns:
            商品列表
        """
        try:
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Browsing category: {category}")

            # 构建分类URL
            category_url = f"{self.base_url}/s?i={category}"

            # 添加过滤条件
            if filters:
                params = []
                if filters.get('min_price'):
                    params.append(f"low-price={filters['min_price']}")
                if filters.get('max_price'):
                    params.append(f"high-price={filters['max_price']}")
                if filters.get('prime_only'):
                    params.append("prime=true")
                if filters.get('min_rating'):
                    params.append(f"rh=p_72:{int(filters['min_rating'])*20}")

                if params:
                    category_url += "&" + "&".join(params)

            if not await self._safe_navigate(category_url):
                self.logger.error("Failed to navigate to category page")
                return []

            # 滚动加载
            for i in range(min((max_results // 16) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1.5, 2.5))

            results = []
            product_elements = await self._page.query_selector_all('[data-component-type="s-search-result"]')

            for elem in product_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        result['category'] = category
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to parse product: {e}")
                    continue

            self.logger.info(f"Found {len(results)} products in category")
            return results

        except Exception as e:
            self.logger.error(f"Failed to browse category: {e}")
            return []

    async def get_product_recommendations(
        self,
        asin: str,
        site: str = 'com',
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """获取商品推荐（相关商品）

        Args:
            asin: 商品ASIN
            site: 站点代码
            max_results: 最大结果数

        Returns:
            推荐商品列表
        """
        try:
            if site != self.current_site.domain.split('.')[0]:
                self.switch_site(site)

            self.logger.info(f"Getting recommendations for {asin}")

            # 导航到商品页面
            product_url = f"{self.base_url}/dp/{asin}"
            if not await self._safe_navigate(product_url):
                return []

            recommendations = []

            # 查找"经常一起购买"
            frequently_bought = await self._page.query_selector_all('#sims-fbt .a-carousel-card')
            for elem in frequently_bought[:max_results]:
                try:
                    rec = await self._parse_recommendation(elem)
                    if rec:
                        rec['recommendation_type'] = 'frequently_bought_together'
                        recommendations.append(rec)
                except:
                    continue

            # 查找"浏览此商品的顾客也浏览"
            also_viewed = await self._page.query_selector_all('#similarities_feature_div .a-carousel-card')
            for elem in also_viewed[:max_results]:
                try:
                    rec = await self._parse_recommendation(elem)
                    if rec:
                        rec['recommendation_type'] = 'customers_also_viewed'
                        recommendations.append(rec)
                except:
                    continue

            self.logger.info(f"Got {len(recommendations)} recommendations")
            return recommendations[:max_results]

        except Exception as e:
            self.logger.error(f"Failed to get recommendations: {e}")
            return []

    async def _parse_recommendation(self, elem) -> Optional[Dict[str, Any]]:
        """解析推荐商品"""
        try:
            rec = {'platform': self.platform, 'site': self.current_site.domain}

            # 商品链接
            link_elem = await elem.query_selector('a')
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href and '/dp/' in href:
                    rec['id'] = href.split('/dp/')[-1].split('/')[0].split('?')[0]
                    rec['url'] = f"{self.base_url}{href}" if not href.startswith('http') else href

            # 商品标题
            title_elem = await elem.query_selector('.a-truncate-full')
            if title_elem:
                rec['title'] = (await title_elem.inner_text()).strip()

            # 价格
            price_elem = await elem.query_selector('.a-price .a-offscreen')
            if price_elem:
                rec['price'] = (await price_elem.inner_text()).strip()

            # 评分
            rating_elem = await elem.query_selector('.a-icon-star-small .a-icon-alt')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                try:
                    rec['rating'] = float(rating_text.split()[0])
                except:
                    pass

            return rec if rec.get('id') else None

        except Exception as e:
            self.logger.debug(f"Failed to parse recommendation: {e}")
            return None


if __name__ == "__main__":
    async def test_amazon_spider():
        """测试Amazon爬虫功能"""
        spider = AmazonSpider(headless=False)

        async with spider.session():
            print("=" * 80)
            print("Amazon Spider - 完整功能测试")
            print("=" * 80)

            # 测试1: 多站点搜索
            print("\n[测试1] 搜索商品 - 美国站点")
            products = await spider.search("laptop", site='com', max_results=5, prime_only=True)
            for i, product in enumerate(products, 1):
                print(f"\n{i}. {product.get('title', 'N/A')[:60]}")
                print(f"   ASIN: {product.get('id')}")
                print(f"   价格: {product.get('price')}")
                print(f"   评分: {product.get('rating')} ({product.get('reviews_count', 0)} 评价)")
                print(f"   Prime: {'是' if product.get('prime') else '否'}")

            # 测试2: 商品详情
            if products:
                print("\n[测试2] 获取商品详情")
                first_asin = products[0].get('id')
                if first_asin:
                    detail = await spider.get_post_detail(first_asin, site='com')
                    print(f"\n商品: {detail.get('title', 'N/A')[:60]}")
                    print(f"品牌: {detail.get('brand')}")
                    print(f"价格: {detail.get('price')}")
                    print(f"评分: {detail.get('rating')} ({detail.get('reviews_count', 0)} 评价)")
                    print(f"库存: {detail.get('availability')}")
                    print(f"特性数量: {len(detail.get('features', []))}")
                    print(f"图片数量: {len(detail.get('images', []))}")
                    print(f"变体数量: {len(detail.get('variations', []))}")

                    # 测试3: 获取评价
                    print("\n[测试3] 获取商品评价")
                    reviews = await spider.get_comments(first_asin, site='com', max_comments=5)
                    for i, review in enumerate(reviews, 1):
                        print(f"\n评价 {i}:")
                        print(f"  评分: {review.get('rating')} 星")
                        print(f"  标题: {review.get('title', 'N/A')[:50]}")
                        print(f"  内容: {review.get('content', 'N/A')[:80]}...")
                        print(f"  认证购买: {'是' if review.get('verified_purchase') else '否'}")
                        print(f"  有用投票: {review.get('helpful_votes', 0)}")

            # 测试4: Best Sellers
            print("\n[测试4] 获取Best Sellers榜单")
            bestsellers = await spider.get_best_sellers(category="electronics", site='com', max_results=3)
            for i, item in enumerate(bestsellers, 1):
                print(f"\n排名 #{item.get('rank', 'N/A')}: {item.get('title', 'N/A')[:60]}")
                print(f"  价格: {item.get('price')}")
                print(f"  评分: {item.get('rating')}")

            # 测试5: 使用Matcher过滤
            print("\n[测试5] 使用Matcher过滤商品")
            if products:
                filtered = spider.matcher.filter_by_rating(products, min_rating=4.0, min_reviews=100)
                print(f"原始商品数: {len(products)}")
                print(f"过滤后商品数: {len(filtered)}")

                # 计算质量评分
                for product in filtered[:3]:
                    quality_score = spider.matcher.calculate_quality_score(product)
                    print(f"\n{product.get('title', 'N/A')[:50]}")
                    print(f"  质量评分: {quality_score}/100")

            print("\n" + "=" * 80)
            print("测试完成!")
            print("=" * 80)

    asyncio.run(test_amazon_spider())
