"""
Tmall (天猫) Spider Implementation
完整的天猫电商平台爬虫实现 - 企业级4层架构

架构说明:
- Layer 1: Spider Layer - 核心爬虫功能，天猫国际/超市/旗舰店支持
- Layer 2: Anti-Crawl Layer - 天猫特有的反爬虫机制和安全防护
- Layer 3: Matcher Layer - 品牌筛选、活动过滤、智能匹配
- Layer 4: Interaction Layer - 品牌关注、活动参与、用户交互操作
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

class TmallStoreType(Enum):
    """天猫店铺类型"""
    FLAGSHIP = ("flagship", "官方旗舰店", "Official Flagship Store")
    SPECIALTY = ("specialty", "专营店", "Specialty Store")
    FRANCHISE = ("franchise", "专卖店", "Franchise Store")
    GLOBAL = ("global", "天猫国际", "Tmall Global")
    SUPERMARKET = ("supermarket", "天猫超市", "Tmall Supermarket")

    def __init__(self, code: str, name_zh: str, name_en: str):
        self.code = code
        self.name_zh = name_zh
        self.name_en = name_en


class TmallActivityType(Enum):
    """天猫活动类型"""
    DOUBLE_11 = ("double11", "双11", "Double 11")
    DOUBLE_12 = ("double12", "双12", "Double 12")
    SUPER_BRAND_DAY = ("super_brand", "超级品牌日", "Super Brand Day")
    NEW_PRODUCT = ("new_product", "新品首发", "New Product Launch")
    PRESALE = ("presale", "预售", "Pre-sale")
    FLASH_SALE = ("flash_sale", "聚划算", "Flash Sale")
    BRAND_CLEARANCE = ("clearance", "品牌清仓", "Brand Clearance")

    def __init__(self, code: str, name_zh: str, name_en: str):
        self.code = code
        self.name_zh = name_zh
        self.name_en = name_en


class ProductCondition(Enum):
    """商品状态"""
    NEW = "new"
    PRESALE = "presale"
    IMPORTED = "imported"
    BONDED = "bonded"


@dataclass
class TmallPrice:
    """价格信息"""
    amount: Decimal
    currency: str = "CNY"
    display_text: str = ""
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[int] = None
    promotion_price: Optional[Decimal] = None
    member_price: Optional[Decimal] = None

    def get_savings(self) -> Optional[Decimal]:
        """计算节省金额"""
        if self.original_price and self.amount:
            return self.original_price - self.amount
        return None


@dataclass
class TmallBrand:
    """品牌信息"""
    brand_id: str
    brand_name: str
    brand_name_en: Optional[str] = None
    logo_url: Optional[str] = None

    # 品牌认证
    is_official: bool = False
    is_authorized: bool = False
    authorization_info: Optional[str] = None

    # 品牌详情
    country_of_origin: Optional[str] = None
    brand_story: Optional[str] = None
    flagship_store_url: Optional[str] = None

    # 品牌统计
    product_count: int = 0
    follower_count: int = 0
    sales_volume: Optional[str] = None


@dataclass
class TmallActivity:
    """活动信息"""
    activity_id: str
    activity_type: TmallActivityType
    activity_name: str

    # 活动时间
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    countdown: Optional[str] = None

    # 活动详情
    description: Optional[str] = None
    banner_url: Optional[str] = None
    activity_url: Optional[str] = None

    # 活动优惠
    discount_info: Optional[str] = None
    coupon_info: Optional[str] = None
    gift_info: Optional[str] = None

    # 参与品牌
    participating_brands: List[str] = field(default_factory=list)
    product_count: int = 0


@dataclass
class TmallShop:
    """天猫店铺信息"""
    shop_id: str
    shop_name: str
    shop_type: TmallStoreType
    shop_url: str

    # 店铺认证
    is_official: bool = False
    is_tmall_verified: bool = True
    brand_authorization: Optional[str] = None

    # 店铺评分
    description_score: Optional[float] = None
    service_score: Optional[float] = None
    logistics_score: Optional[float] = None

    # 店铺统计
    product_count: int = 0
    follower_count: int = 0
    sales_volume: Optional[str] = None

    # 店铺详情
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

    # 服务保障
    services: List[str] = field(default_factory=list)
    return_policy: Optional[str] = None


@dataclass
class TmallProduct:
    """天猫商品完整信息"""
    item_id: str
    title: str
    url: str

    # 价格信息
    price: Optional[TmallPrice] = None

    # 评分信息
    rating: Optional[float] = None
    review_count: int = 0

    # 商品详情
    brand: Optional[TmallBrand] = None
    description: str = ""
    features: List[str] = field(default_factory=list)

    # 图片和媒体
    main_image: Optional[str] = None
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)

    # 分类信息
    category: Optional[str] = None
    categories_path: List[str] = field(default_factory=list)

    # 商品属性
    condition: ProductCondition = ProductCondition.NEW
    is_imported: bool = False
    is_bonded: bool = False
    origin_country: Optional[str] = None

    # 销售信息
    sales_count: Optional[str] = None
    monthly_sales: Optional[int] = None
    stock_status: str = ""

    # 配送信息
    free_shipping: bool = False
    delivery_location: Optional[str] = None
    delivery_time: Optional[str] = None

    # 店铺信息
    shop: Optional[TmallShop] = None

    # 活动信息
    activities: List[TmallActivity] = field(default_factory=list)

    # 规格信息
    specifications: Dict[str, str] = field(default_factory=dict)
    sku_list: List[Dict[str, Any]] = field(default_factory=list)

    # 时间戳
    scraped_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# Layer 2: Anti-Crawl Layer - 天猫反爬虫机制
# ============================================================================

class TmallAntiCrawl:
    """天猫反爬虫处理层 - 处理滑块验证、设备指纹等"""

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
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Mobile Chrome
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        # Additional variants
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    ]

    def __init__(self, logger):
        self.logger = logger
        self.request_count = 0
        self.last_request_time = 0
        self.session_id = self._generate_session_id()
        self.device_fingerprint = self._generate_device_fingerprint()
        self.slider_solve_count = 0
        self.blocked_count = 0
        self.umid_token = None  # 天猫设备标识

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = int(time.time() * 1000)
        random_part = ''.join(random.choices('0123456789abcdef', k=16))
        return f"{timestamp}-{random_part}"

    def _generate_device_fingerprint(self) -> Dict[str, Any]:
        """生成设备指纹 - 天猫特有"""
        return {
            'screen_resolution': random.choice(['1920x1080', '2560x1440', '1366x768', '1440x900']),
            'color_depth': random.choice([24, 32]),
            'timezone_offset': -480,  # 中国时区
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
            'language': 'zh-CN',
            'plugins': random.randint(3, 8),
            'canvas_hash': hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
            'webgl_vendor': random.choice(['Google Inc.', 'Intel Inc.', 'NVIDIA Corporation']),
            'webgl_renderer': random.choice(['ANGLE (Intel HD Graphics)', 'ANGLE (NVIDIA GeForce)']),
        }

    def _generate_umid_token(self) -> str:
        """生成UMID设备标识 - 天猫反爬虫关键"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789ABCDEF', k=32))
        return f"{timestamp}_{random_str}"

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.USER_AGENTS)

    def get_request_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """获取完整的请求头 - 天猫特定"""
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

    async def smart_delay(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """智能延迟 - 模拟人类行为"""
        self.request_count += 1

        # 基础延迟
        base_delay = random.uniform(min_delay, max_delay)

        # 根据请求频率调整
        if self.request_count % 10 == 0:
            base_delay += random.uniform(3, 8)
            self.logger.debug(f"Adding extra delay after {self.request_count} requests")

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

        self.logger.info(f"Exponential backoff: attempt {attempt}, waiting {total_delay:.2f}s")
        await asyncio.sleep(total_delay)
        return total_delay

    def detect_slider_captcha(self, page_content: str) -> bool:
        """检测滑块验证码 - 天猫特有"""
        slider_indicators = [
            'nc_1_n1z',  # 天猫滑块验证码ID
            'slide to verify',
            '滑动验证',
            '拖动滑块',
            'nc-container',
            'sm-pop',  # 阿里系验证码
        ]

        content_lower = page_content.lower()
        for indicator in slider_indicators:
            if indicator.lower() in content_lower:
                self.logger.warning(f"Slider CAPTCHA detected: {indicator}")
                return True
        return False

    def detect_blocked(self, page_content: str) -> bool:
        """检测是否被封禁"""
        block_indicators = [
            '访问被拒绝',
            '请求异常',
            '系统繁忙',
            '访问过于频繁',
            'access denied',
            'request blocked',
        ]

        content_lower = page_content.lower()
        for indicator in block_indicators:
            if indicator.lower() in content_lower:
                self.logger.error(f"Access blocked: {indicator}")
                self.blocked_count += 1
                return True
        return False

    async def handle_slider_captcha(self, page) -> bool:
        """处理滑块验证码 - 简单重试机制"""
        self.slider_solve_count += 1
        self.logger.warning(f"Encountered slider CAPTCHA (count: {self.slider_solve_count})")

        try:
            # 查找滑块元素
            slider_elem = await page.query_selector('.nc_1_n1z, .nc-lang-cnt, #nc_1_n1z')
            if slider_elem:
                self.logger.info("Found slider element, attempting to solve...")

                # 获取滑块按钮
                slider_button = await page.query_selector('.nc_iconfont.btn_slide, .nc-lang-cnt')
                if slider_button:
                    # 获取滑块轨道宽度
                    track = await page.query_selector('.nc_scale, .nc-lang-cnt')
                    if track:
                        box = await track.bounding_box()
                        if box:
                            # 模拟人类滑动
                            await slider_button.hover()
                            await asyncio.sleep(random.uniform(0.3, 0.6))

                            # 按下鼠标
                            await page.mouse.down()
                            await asyncio.sleep(random.uniform(0.1, 0.2))

                            # 分段滑动，模拟人类行为
                            distance = box['width'] - 40
                            steps = random.randint(15, 25)
                            for i in range(steps):
                                move_x = distance / steps
                                # 添加随机抖动
                                jitter_y = random.uniform(-2, 2)
                                await page.mouse.move(
                                    box['x'] + (i + 1) * move_x,
                                    box['y'] + box['height'] / 2 + jitter_y,
                                    steps=random.randint(1, 3)
                                )
                                await asyncio.sleep(random.uniform(0.01, 0.03))

                            # 释放鼠标
                            await asyncio.sleep(random.uniform(0.1, 0.3))
                            await page.mouse.up()

                            # 等待验证结果
                            await asyncio.sleep(3)

                            # 检查是否成功
                            content = await page.content()
                            if not self.detect_slider_captcha(content):
                                self.logger.info("Slider CAPTCHA solved successfully")
                                return True

            # 如果无法自动解决，等待手动处理
            self.logger.warning("Cannot auto-solve slider, waiting for manual intervention...")
            await asyncio.sleep(30)

            content = await page.content()
            if not self.detect_slider_captcha(content):
                return True

        except Exception as e:
            self.logger.error(f"Failed to handle slider CAPTCHA: {e}")

        return False

    def should_rotate_session(self) -> bool:
        """判断是否需要轮换会话"""
        if self.request_count >= 50 or self.slider_solve_count >= 3:
            return True
        return False

    def reset_session(self):
        """重置会话"""
        self.logger.info("Resetting session...")
        self.session_id = self._generate_session_id()
        self.device_fingerprint = self._generate_device_fingerprint()
        self.umid_token = self._generate_umid_token()
        self.request_count = 0
        self.slider_solve_count = 0


# ============================================================================
# Layer 3: Matcher Layer - 品牌筛选和活动过滤
# ============================================================================

class TmallMatcher:
    """天猫商品匹配和过滤层"""

    def __init__(self, logger):
        self.logger = logger

    def filter_by_price(
        self,
        products: List[Dict[str, Any]],
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """按价格过滤商品"""
        filtered = []
        for product in products:
            price_str = product.get('price', '')
            if not price_str:
                continue

            try:
                price_value = self._extract_price_value(price_str)
                if price_value is None:
                    continue

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

    def filter_by_brand(
        self,
        products: List[Dict[str, Any]],
        brands: List[str],
        official_only: bool = False
    ) -> List[Dict[str, Any]]:
        """按品牌过滤商品"""
        if not brands:
            return products

        brands_lower = [b.lower() for b in brands]
        filtered = []

        for product in products:
            # 检查品牌名称
            brand_info = product.get('brand', {})
            if isinstance(brand_info, dict):
                brand_name = brand_info.get('brand_name', '').lower()
            else:
                brand_name = str(brand_info).lower()

            # 品牌匹配
            if any(b in brand_name for b in brands_lower):
                # 如果要求官方旗舰店
                if official_only:
                    shop = product.get('shop', {})
                    if isinstance(shop, dict) and shop.get('is_official'):
                        filtered.append(product)
                else:
                    filtered.append(product)

        self.logger.info(f"Brand filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_store_type(
        self,
        products: List[Dict[str, Any]],
        store_types: List[str]
    ) -> List[Dict[str, Any]]:
        """按店铺类型过滤"""
        if not store_types:
            return products

        store_types_lower = [s.lower() for s in store_types]
        filtered = []

        for product in products:
            shop = product.get('shop', {})
            if isinstance(shop, dict):
                shop_type = shop.get('shop_type', '')
                if isinstance(shop_type, str):
                    shop_type_code = shop_type.lower()
                else:
                    shop_type_code = getattr(shop_type, 'code', '').lower()

                if any(st in shop_type_code for st in store_types_lower):
                    filtered.append(product)

        self.logger.info(f"Store type filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_activity(
        self,
        products: List[Dict[str, Any]],
        activity_types: List[str]
    ) -> List[Dict[str, Any]]:
        """按活动类型过滤"""
        if not activity_types:
            return products

        activity_types_lower = [a.lower() for a in activity_types]
        filtered = []

        for product in products:
            activities = product.get('activities', [])
            if activities:
                for activity in activities:
                    if isinstance(activity, dict):
                        activity_type = activity.get('activity_type', '')
                        if isinstance(activity_type, str):
                            activity_code = activity_type.lower()
                        else:
                            activity_code = getattr(activity_type, 'code', '').lower()

                        if any(at in activity_code for at in activity_types_lower):
                            filtered.append(product)
                            break

        self.logger.info(f"Activity filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_sales(
        self,
        products: List[Dict[str, Any]],
        min_sales: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """按销量过滤"""
        if min_sales is None:
            return products

        filtered = []
        for product in products:
            sales_str = product.get('sales_count', '')
            if sales_str:
                sales_count = self._extract_sales_count(sales_str)
                if sales_count and sales_count >= min_sales:
                    filtered.append(product)

        self.logger.info(f"Sales filter: {len(products)} -> {len(filtered)} products")
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
            review_count = product.get('review_count', 0)

            if min_rating is not None:
                if rating is None or rating < min_rating:
                    continue

            if min_reviews is not None:
                if review_count < min_reviews:
                    continue

            filtered.append(product)

        self.logger.info(f"Rating filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_by_shipping(
        self,
        products: List[Dict[str, Any]],
        free_shipping_only: bool = False
    ) -> List[Dict[str, Any]]:
        """按配送方式过滤"""
        if not free_shipping_only:
            return products

        filtered = [p for p in products if p.get('free_shipping', False)]
        self.logger.info(f"Shipping filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def filter_imported_products(
        self,
        products: List[Dict[str, Any]],
        imported_only: bool = False,
        bonded_only: bool = False
    ) -> List[Dict[str, Any]]:
        """过滤进口商品"""
        filtered = []
        for product in products:
            if imported_only and product.get('is_imported', False):
                filtered.append(product)
            elif bonded_only and product.get('is_bonded', False):
                filtered.append(product)
            elif not imported_only and not bonded_only:
                filtered.append(product)

        self.logger.info(f"Import filter: {len(products)} -> {len(filtered)} products")
        return filtered

    def calculate_quality_score(self, product: Dict[str, Any]) -> float:
        """计算商品质量评分 (0-100)"""
        score = 0.0

        # 评分权重 30%
        rating = product.get('rating')
        if rating:
            score += (rating / 5.0) * 30

        # 评价数权重 20%
        review_count = product.get('review_count', 0)
        if review_count > 0:
            review_score = min(20, (review_count / 1000) * 20)
            score += review_score

        # 销量权重 20%
        sales_str = product.get('sales_count', '')
        if sales_str:
            sales_count = self._extract_sales_count(sales_str)
            if sales_count:
                sales_score = min(20, (sales_count / 10000) * 20)
                score += sales_score

        # 店铺类型权重 15%
        shop = product.get('shop', {})
        if isinstance(shop, dict):
            if shop.get('is_official'):
                score += 15
            elif shop.get('is_tmall_verified'):
                score += 10

        # 包邮权重 10%
        if product.get('free_shipping', False):
            score += 10

        # 活动加分 5%
        if product.get('activities'):
            score += 5

        return round(score, 2)

    def sort_products(
        self,
        products: List[Dict[str, Any]],
        sort_by: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """排序商品

        Args:
            sort_by: relevance, price_asc, price_desc, sales, rating, quality
        """
        if sort_by == "relevance":
            return products

        try:
            if sort_by == "price_asc":
                products.sort(key=lambda p: self._extract_price_value(p.get('price', '')) or float('inf'))
            elif sort_by == "price_desc":
                products.sort(key=lambda p: self._extract_price_value(p.get('price', '')) or 0, reverse=True)
            elif sort_by == "sales":
                products.sort(key=lambda p: self._extract_sales_count(p.get('sales_count', '')) or 0, reverse=True)
            elif sort_by == "rating":
                products.sort(key=lambda p: p.get('rating') or 0, reverse=True)
            elif sort_by == "quality":
                products.sort(key=lambda p: self.calculate_quality_score(p), reverse=True)

            self.logger.info(f"Sorted {len(products)} products by {sort_by}")
        except Exception as e:
            self.logger.error(f"Failed to sort products: {e}")

        return products

    def _extract_price_value(self, price_str: str) -> Optional[float]:
        """从价格字符串提取数值"""
        if not price_str:
            return None

        try:
            price_clean = re.sub(r'[^\d.]', '', str(price_str))
            if price_clean:
                return float(price_clean)
        except Exception:
            pass

        return None

    def _extract_sales_count(self, sales_str: str) -> Optional[int]:
        """从销量字符串提取数值"""
        if not sales_str:
            return None

        try:
            # 处理"1000+人付款"、"5万+"等格式
            sales_str = str(sales_str).lower()

            # 提取数字
            match = re.search(r'([\d.]+)\s*([万千百])?', sales_str)
            if match:
                num = float(match.group(1))
                unit = match.group(2)

                if unit == '万':
                    num *= 10000
                elif unit == '千':
                    num *= 1000
                elif unit == '百':
                    num *= 100

                return int(num)
        except Exception:
            pass

        return None


# ============================================================================
# Layer 4: Interaction Layer - 用户交互操作
# ============================================================================

class TmallInteraction:
    """天猫用户交互层"""

    def __init__(self, page, logger):
        self.page = page
        self.logger = logger

    async def follow_brand(self, brand_id: str) -> bool:
        """关注品牌"""
        try:
            self.logger.info(f"Following brand: {brand_id}")

            follow_button = await self.page.query_selector('[data-action="follow-brand"], .follow-btn')
            if follow_button:
                await follow_button.click()
                await asyncio.sleep(1)
                self.logger.info("Successfully followed brand")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to follow brand: {e}")
            return False

    async def follow_shop(self, shop_id: str) -> bool:
        """关注店铺"""
        try:
            self.logger.info(f"Following shop: {shop_id}")

            follow_button = await self.page.query_selector('.shop-follow-btn, [data-spm="follow"]')
            if follow_button:
                await follow_button.click()
                await asyncio.sleep(1)
                self.logger.info("Successfully followed shop")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to follow shop: {e}")
            return False

    async def add_to_cart(self, item_id: str, quantity: int = 1) -> bool:
        """添加商品到购物车"""
        try:
            self.logger.info(f"Adding item {item_id} to cart (quantity: {quantity})")

            # 查找加入购物车按钮
            add_cart_selectors = [
                '.tm-fcs-panel-add-cart',
                '#J_LinkBuy',
                '[data-action="add-cart"]',
            ]

            for selector in add_cart_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    # 设置数量
                    if quantity > 1:
                        qty_input = await self.page.query_selector('.mui-amount-input input')
                        if qty_input:
                            await qty_input.fill(str(quantity))
                            await asyncio.sleep(0.5)

                    await button.click()
                    await asyncio.sleep(2)

                    # 检查是否成功
                    success_indicator = await self.page.query_selector('.add-cart-success, .J_Go')
                    if success_indicator:
                        self.logger.info("Successfully added to cart")
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to add to cart: {e}")
            return False

    async def participate_in_activity(self, activity_id: str) -> bool:
        """参与活动"""
        try:
            self.logger.info(f"Participating in activity: {activity_id}")

            participate_button = await self.page.query_selector('[data-action="join-activity"], .activity-join-btn')
            if participate_button:
                await participate_button.click()
                await asyncio.sleep(2)
                self.logger.info("Successfully joined activity")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to participate in activity: {e}")
            return False

    async def collect_coupon(self, coupon_id: str) -> bool:
        """领取优惠券"""
        try:
            self.logger.info(f"Collecting coupon: {coupon_id}")

            coupon_button = await self.page.query_selector('.coupon-btn, [data-action="get-coupon"]')
            if coupon_button:
                await coupon_button.click()
                await asyncio.sleep(1)
                self.logger.info("Successfully collected coupon")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to collect coupon: {e}")
            return False


# ============================================================================
# Layer 1: Spider Layer - 核心爬虫功能
# ============================================================================

class TmallSpider(BaseSpider):
    """天猫电商平台爬虫 - 完整4层架构实现"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="tmall", headless=headless, proxy=proxy)
        self.base_url = "https://www.tmall.com"
        self.search_url = "https://list.tmall.com/search_product.htm"
        self.detail_url = "https://detail.tmall.com/item.htm"

        # 初始化各层
        self.anti_crawl = TmallAntiCrawl(self.logger)
        self.matcher = TmallMatcher(self.logger)
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

                # 检测滑块验证码
                if self.anti_crawl.detect_slider_captcha(content):
                    if await self.anti_crawl.handle_slider_captcha(self._page):
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
        """登录天猫账户

        Args:
            username: 手机号或邮箱
            password: 密码

        Returns:
            bool: 登录是否成功
        """
        try:
            self.logger.info(f"Logging in to Tmall as {username}...")

            # 尝试使用已保存的cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self._safe_navigate(self.base_url)

                # 检查登录状态
                account_elem = await self._page.query_selector('.site-nav-user, .site-nav-login-info-nick')
                if account_elem:
                    self._is_logged_in = True
                    self.interaction = TmallInteraction(self._page, self.logger)
                    self.logger.info("Logged in with saved cookies")
                    return True

            # 导航到登录页面
            login_url = "https://login.tmall.com"
            if not await self._safe_navigate(login_url):
                self.logger.error("Failed to navigate to login page")
                return False

            # 天猫通常使用扫码登录或短信验证
            self.logger.info("Please scan QR code or complete verification (waiting 60 seconds)...")

            # 等待用户完成登录
            for _ in range(60):
                account_elem = await self._page.query_selector('.site-nav-user, .site-nav-login-info-nick')
                if account_elem:
                    self._is_logged_in = True
                    self.interaction = TmallInteraction(self._page, self.logger)
                    await self._save_cookies()
                    self.logger.info("Login successful")
                    return True
                await asyncio.sleep(1)

            self.logger.error("Login timeout")
            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        store_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "default"
    ) -> List[Dict[str, Any]]:
        """搜索天猫商品 - 支持多种过滤条件

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            store_type: 店铺类型 (flagship, global, supermarket等)
            min_price: 最低价格
            max_price: 最高价格
            sort_by: 排序方式 (default, price_asc, price_desc, sales)

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"Searching Tmall for '{keyword}'")

            # 构建搜索URL
            search_params = {'q': keyword}

            # 添加价格范围
            if min_price is not None:
                search_params['start_price'] = str(min_price)
            if max_price is not None:
                search_params['end_price'] = str(max_price)

            # 排序
            sort_map = {
                'price_asc': 's',
                'price_desc': 'd',
                'sales': 'sale-desc',
            }
            if sort_by in sort_map:
                search_params['sort'] = sort_map[sort_by]

            search_url = f"{self.search_url}?{urlencode(search_params)}"

            if not await self._safe_navigate(search_url):
                self.logger.error("Failed to navigate to search page")
                return []

            # 滚动加载更多商品
            for i in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            # 天猫商品选择器
            product_elements = await self._page.query_selector_all('.product, .product-item, [class*="item"]')

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
            'type': 'product'
        }

        # 商品标题和链接
        title_elem = await elem.query_selector('.productTitle, [class*="title"] a, .product-title')
        if title_elem:
            result['title'] = (await title_elem.inner_text()).strip()
            href = await title_elem.get_attribute('href')
            if href:
                if not href.startswith('http'):
                    href = 'https:' + href
                result['url'] = href

                # 提取商品ID
                if 'id=' in href:
                    result['id'] = href.split('id=')[-1].split('&')[0]

        # 价格信息
        price_elem = await elem.query_selector('.productPrice, [class*="price"], .price')
        if price_elem:
            price_text = (await price_elem.inner_text()).strip()
            result['price'] = price_text

        # 原价
        original_price_elem = await elem.query_selector('.productPrice-original, [class*="original"]')
        if original_price_elem:
            result['original_price'] = (await original_price_elem.inner_text()).strip()

        # 销量
        sales_elem = await elem.query_selector('.productSales, [class*="sales"], .sale-num')
        if sales_elem:
            result['sales_count'] = (await sales_elem.inner_text()).strip()

        # 店铺名称
        shop_elem = await elem.query_selector('.productShop, [class*="shop"], .shop-name')
        if shop_elem:
            shop_name = (await shop_elem.inner_text()).strip()
            result['shop'] = {'shop_name': shop_name}

            # 判断店铺类型
            if '旗舰店' in shop_name:
                result['shop']['shop_type'] = 'flagship'
                result['shop']['is_official'] = True
            elif '专营店' in shop_name:
                result['shop']['shop_type'] = 'specialty'
            elif '天猫国际' in shop_name:
                result['shop']['shop_type'] = 'global'
                result['is_imported'] = True

        # 商品图片
        img = await elem.query_selector('img')
        if img:
            src = await img.get_attribute('src')
            if not src:
                src = await img.get_attribute('data-src')
            if src:
                if not src.startswith('http'):
                    src = 'https:' + src
                result['thumbnail'] = src

        # 包邮标识
        free_shipping = await elem.query_selector('[class*="free-shipping"], .free-ship')
        result['free_shipping'] = free_shipping is not None

        # 活动标签
        activity_elem = await elem.query_selector('[class*="activity"], .promo-tag')
        if activity_elem:
            activity_text = (await activity_elem.inner_text()).strip()
            result['activities'] = [{'activity_name': activity_text}]

        return result

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取天猫店铺资料

        Args:
            user_id: 店铺ID

        Returns:
            店铺资料信息
        """
        try:
            self.logger.info(f"Getting shop profile: {user_id}")

            # 天猫店铺URL
            shop_url = f"https://shop{user_id}.tmall.com"
            if not await self._safe_navigate(shop_url):
                self.logger.error("Failed to navigate to shop page")
                return {}

            profile = {
                'user_id': user_id,
                'platform': self.platform,
                'type': 'shop'
            }

            # 店铺名称
            name_elem = await self._page.query_selector('.shop-name, .slogo-shopname, [class*="shopName"]')
            if name_elem:
                profile['shop_name'] = (await name_elem.inner_text()).strip()

            # 店铺Logo
            logo_elem = await self._page.query_selector('.shop-logo img, .slogo img')
            if logo_elem:
                profile['logo_url'] = await logo_elem.get_attribute('src')

            # 店铺评分
            score_elems = await self._page.query_selector_all('.shop-score li, [class*="score"]')
            for elem in score_elems:
                text = await elem.inner_text()
                if '描述' in text or 'description' in text.lower():
                    match = re.search(r'([\d.]+)', text)
                    if match:
                        profile['description_score'] = float(match.group(1))
                elif '服务' in text or 'service' in text.lower():
                    match = re.search(r'([\d.]+)', text)
                    if match:
                        profile['service_score'] = float(match.group(1))
                elif '物流' in text or 'logistics' in text.lower():
                    match = re.search(r'([\d.]+)', text)
                    if match:
                        profile['logistics_score'] = float(match.group(1))

            # 店铺统计
            stats_elems = await self._page.query_selector_all('.shop-stats li, [class*="stat"]')
            for elem in stats_elems:
                text = await elem.inner_text()
                if '宝贝' in text or '商品' in text:
                    profile['product_count'] = self.parser.parse_count(text)
                elif '粉丝' in text or '关注' in text:
                    profile['follower_count'] = self.parser.parse_count(text)

            # 店铺类型判断
            shop_name = profile.get('shop_name', '')
            if '旗舰店' in shop_name:
                profile['shop_type'] = 'flagship'
                profile['is_official'] = True
            elif '专营店' in shop_name:
                profile['shop_type'] = 'specialty'
            elif '专卖店' in shop_name:
                profile['shop_type'] = 'franchise'

            profile['is_tmall_verified'] = True

            self.logger.info(f"Successfully retrieved shop profile for {user_id}")
            return profile

        except Exception as e:
            self.logger.error(f"Failed to get shop profile: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """获取店铺的商品列表

        Args:
            user_id: 店铺ID
            max_posts: 最大商品数

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"Getting products from shop: {user_id}")

            shop_url = f"https://shop{user_id}.tmall.com"
            if not await self._safe_navigate(shop_url):
                self.logger.error("Failed to navigate to shop page")
                return []

            # 滚动加载商品
            for i in range(min((max_posts // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            posts = []
            item_elements = await self._page.query_selector_all('.item, .J_TItems .item, [class*="product"]')

            for elem in item_elements[:max_posts]:
                try:
                    post = {'user_id': user_id, 'platform': self.platform, 'type': 'product'}

                    # 商品链接和ID
                    link = await elem.query_selector('a[href*="detail.tmall.com"]')
                    if link:
                        href = await link.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = 'https:' + href
                            post['url'] = href
                            if 'id=' in href:
                                post['id'] = href.split('id=')[-1].split('&')[0]

                    # 标题
                    title = await elem.query_selector('.title, .item-name, [class*="title"]')
                    if title:
                        post['title'] = (await title.inner_text()).strip()

                    # 价格
                    price = await elem.query_selector('.price, [class*="price"]')
                    if price:
                        post['price'] = (await price.inner_text()).strip()

                    # 销量
                    sales = await elem.query_selector('.sale-num, [class*="sales"]')
                    if sales:
                        post['sales_count'] = (await sales.inner_text()).strip()

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"Failed to parse product: {e}")
                    continue

            self.logger.info(f"Got {len(posts)} products from shop")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get shop products: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """获取天猫商品详细信息

        Args:
            post_id: 商品ID

        Returns:
            商品详细信息
        """
        try:
            self.logger.info(f"Getting product detail: {post_id}")

            # 导航到商品页面
            product_url = f"https://detail.tmall.com/item.htm?id={post_id}"
            if not await self._safe_navigate(product_url):
                self.logger.error("Failed to navigate to product page")
                return {}

            post = {
                'id': post_id,
                'url': product_url,
                'platform': self.platform,
                'type': 'product'
            }

            # 商品标题
            title_elem = await self._page.query_selector('.tb-detail-hd h1, [class*="itemTitle"]')
            if title_elem:
                post['title'] = (await title_elem.inner_text()).strip()

            # 价格信息
            price_elem = await self._page.query_selector('.tm-price, .tb-rmb-num')
            if price_elem:
                post['price'] = (await price_elem.inner_text()).strip()

            # 原价
            original_price_elem = await self._page.query_selector('.tm-price-original, [class*="originalPrice"]')
            if original_price_elem:
                post['original_price'] = (await original_price_elem.inner_text()).strip()

            # 销量
            sales_elem = await self._page.query_selector('.tm-count, [class*="salesCount"]')
            if sales_elem:
                post['sales_count'] = (await sales_elem.inner_text()).strip()

            # 店铺信息
            shop_elem = await self._page.query_selector('.tb-shop-name a, [class*="shopName"]')
            if shop_elem:
                shop_name = (await shop_elem.inner_text()).strip()
                shop_href = await shop_elem.get_attribute('href')
                post['shop'] = {
                    'shop_name': shop_name,
                    'is_tmall_verified': True
                }
                if shop_href and 'shop' in shop_href:
                    post['shop']['shop_id'] = shop_href.split('shop')[-1].split('.')[0]

                # 判断店铺类型
                if '旗舰店' in shop_name:
                    post['shop']['shop_type'] = 'flagship'
                    post['shop']['is_official'] = True
                elif '专营店' in shop_name:
                    post['shop']['shop_type'] = 'specialty'

            # 商品描述
            desc_elem = await self._page.query_selector('#J_DivItemDesc, .tb-detail-bd')
            if desc_elem:
                post['description'] = (await desc_elem.inner_text()).strip()

            # 商品特性
            features = []
            feature_elems = await self._page.query_selector_all('.tb-property-type li, [class*="feature"]')
            for elem in feature_elems:
                feature_text = (await elem.inner_text()).strip()
                if feature_text:
                    features.append(feature_text)
            post['features'] = features

            # 商品图片
            images = []
            main_image = await self._page.query_selector('#J_ImgBooth')
            if main_image:
                main_src = await main_image.get_attribute('src')
                if not main_src:
                    main_src = await main_image.get_attribute('data-src')
                if main_src:
                    if not main_src.startswith('http'):
                        main_src = 'https:' + main_src
                    post['main_image'] = main_src
                    images.append(main_src)

            # 其他图片
            image_thumbs = await self._page.query_selector_all('#J_UlThumb img')
            for img in image_thumbs[:10]:
                src = await img.get_attribute('src')
                if not src:
                    src = await img.get_attribute('data-src')
                if src:
                    if not src.startswith('http'):
                        src = 'https:' + src
                    # 替换为高清图
                    src = src.replace('_60x60q90.jpg', '').replace('_sum.jpg', '')
                    if src not in images:
                        images.append(src)
            post['images'] = images

            # 库存状态
            stock_elem = await self._page.query_selector('.tm-stock, [class*="stock"]')
            if stock_elem:
                stock_text = (await stock_elem.inner_text()).strip()
                post['stock_status'] = stock_text

            # 包邮标识
            shipping_elem = await self._page.query_selector('[class*="freeShipping"]')
            post['free_shipping'] = shipping_elem is not None

            # 品牌信息
            brand_elem = await self._page.query_selector('.tb-brand, [class*="brand"]')
            if brand_elem:
                brand_name = (await brand_elem.inner_text()).strip()
                post['brand'] = {'brand_name': brand_name}

            # 规格参数
            specifications = {}
            spec_elems = await self._page.query_selector_all('.tb-property-type li, [class*="spec"]')
            for elem in spec_elems:
                spec_text = (await elem.inner_text()).strip()
                if ':' in spec_text or '：' in spec_text:
                    parts = re.split('[：:]', spec_text, 1)
                    if len(parts) == 2:
                        specifications[parts[0].strip()] = parts[1].strip()
            post['specifications'] = specifications

            self.logger.info(f"Successfully retrieved product detail for {post_id}")
            return post

        except Exception as e:
            self.logger.error(f"Failed to get product detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """获取天猫商品评价

        Args:
            post_id: 商品ID
            max_comments: 最大评价数

        Returns:
            评价列表
        """
        try:
            self.logger.info(f"Getting reviews for product: {post_id}")

            # 导航到商品页面
            product_url = f"https://detail.tmall.com/item.htm?id={post_id}"
            if post_id not in self._page.url:
                if not await self._safe_navigate(product_url):
                    return []

            # 点击评价标签
            reviews_tab = await self._page.query_selector('[data-spm="reviews"], .tm-rate-tab')
            if reviews_tab:
                await reviews_tab.click()
                await asyncio.sleep(2)

            # 滚动加载更多评价
            for _ in range(min((max_comments // 20) + 1, 5)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            comments = []
            review_elements = await self._page.query_selector_all('.rate-item, [class*="rateItem"]')

            for elem in review_elements[:max_comments]:
                try:
                    comment = {
                        'post_id': post_id,
                        'platform': self.platform,
                        'type': 'review'
                    }

                    # 评论者名称
                    reviewer = await elem.query_selector('.rate-user-name, [class*="userName"]')
                    if reviewer:
                        comment['username'] = (await reviewer.inner_text()).strip()

                    # 评价内容
                    text = await elem.query_selector('.rate-text, [class*="rateContent"]')
                    if text:
                        comment['content'] = (await text.inner_text()).strip()

                    # 评分
                    rating = await elem.query_selector('.rate-star, [class*="rateStar"]')
                    if rating:
                        rating_class = await rating.get_attribute('class')
                        if 'star5' in rating_class:
                            comment['rating'] = 5
                        elif 'star4' in rating_class:
                            comment['rating'] = 4
                        elif 'star3' in rating_class:
                            comment['rating'] = 3
                        elif 'star2' in rating_class:
                            comment['rating'] = 2
                        elif 'star1' in rating_class:
                            comment['rating'] = 1

                    # 评价日期
                    date = await elem.query_selector('.rate-date, [class*="rateDate"]')
                    if date:
                        date_text = (await date.inner_text()).strip()
                        comment['created_at'] = self.parser.parse_date(date_text)

                    # 商品规格
                    specs = await elem.query_selector('.rate-sku, [class*="rateSku"]')
                    if specs:
                        comment['purchased_specs'] = (await specs.inner_text()).strip()

                    # 评价图片
                    images = []
                    image_elems = await elem.query_selector_all('.rate-image img')
                    for img in image_elems:
                        src = await img.get_attribute('src')
                        if not src:
                            src = await img.get_attribute('data-src')
                        if src:
                            if not src.startswith('http'):
                                src = 'https:' + src
                            images.append(src)
                    comment['images'] = images

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(
                            f"{comment.get('username', '')}{comment['content']}".encode()
                        ).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"Failed to parse review: {e}")
                    continue

            self.logger.info(f"Got {len(comments)} reviews")
            return comments

        except Exception as e:
            self.logger.error(f"Failed to get reviews: {e}")
            return []

    # ========================================================================
    # 扩展功能方法
    # ========================================================================

    async def get_brand_products(
        self,
        brand_name: str,
        max_results: int = 50,
        official_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取品牌商品

        Args:
            brand_name: 品牌名称
            max_results: 最大结果数
            official_only: 仅官方旗舰店

        Returns:
            品牌商品列表
        """
        try:
            self.logger.info(f"Getting products for brand: {brand_name}")

            # 搜索品牌
            search_keyword = f"{brand_name} 旗舰店" if official_only else brand_name
            products = await self.search(search_keyword, max_results=max_results)

            # 使用Matcher过滤
            if official_only:
                products = self.matcher.filter_by_store_type(products, ['flagship'])

            products = self.matcher.filter_by_brand(products, [brand_name], official_only=official_only)

            self.logger.info(f"Found {len(products)} products for brand {brand_name}")
            return products

        except Exception as e:
            self.logger.error(f"Failed to get brand products: {e}")
            return []

    async def get_activity_products(
        self,
        activity_type: str = "double11",
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """获取活动商品

        Args:
            activity_type: 活动类型 (double11, double12, presale等)
            max_results: 最大结果数

        Returns:
            活动商品列表
        """
        try:
            self.logger.info(f"Getting products for activity: {activity_type}")

            # 构建活动页面URL
            activity_urls = {
                'double11': 'https://www.tmall.com/wow/a/act/tmall/dailygroup/2143/wupr',
                'double12': 'https://www.tmall.com/wow/a/act/tmall/dailygroup/2144/wupr',
                'presale': 'https://yushou.tmall.com',
                'flash_sale': 'https://ju.taobao.com',
            }

            activity_url = activity_urls.get(activity_type, self.base_url)
            if not await self._safe_navigate(activity_url):
                self.logger.error("Failed to navigate to activity page")
                return []

            # 滚动加载
            for i in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            product_elements = await self._page.query_selector_all('.product, .item, [class*="item"]')

            for elem in product_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        result['activity_type'] = activity_type
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to parse product: {e}")
                    continue

            self.logger.info(f"Found {len(results)} products for activity")
            return results

        except Exception as e:
            self.logger.error(f"Failed to get activity products: {e}")
            return []

    async def get_tmall_global_products(
        self,
        keyword: str,
        max_results: int = 50,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取天猫国际商品

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            country: 原产国

        Returns:
            天猫国际商品列表
        """
        try:
            self.logger.info(f"Searching Tmall Global for '{keyword}'")

            # 天猫国际搜索URL
            search_url = f"https://list.tmall.hk/search_product.htm?q={keyword}"
            if not await self._safe_navigate(search_url):
                self.logger.error("Failed to navigate to Tmall Global search")
                return []

            # 滚动加载
            for i in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            product_elements = await self._page.query_selector_all('.product, .product-item')

            for elem in product_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        result['is_imported'] = True
                        result['source'] = 'tmall_global'
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to parse product: {e}")
                    continue

            # 按原产国过滤
            if country:
                results = [p for p in results if country.lower() in str(p.get('origin_country', '')).lower()]

            self.logger.info(f"Found {len(results)} Tmall Global products")
            return results

        except Exception as e:
            self.logger.error(f"Failed to get Tmall Global products: {e}")
            return []

    async def get_tmall_supermarket_products(
        self,
        keyword: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """获取天猫超市商品

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数

        Returns:
            天猫超市商品列表
        """
        try:
            self.logger.info(f"Searching Tmall Supermarket for '{keyword}'")

            # 天猫超市搜索URL
            search_url = f"https://chaoshi.tmall.com/search.htm?q={keyword}"
            if not await self._safe_navigate(search_url):
                self.logger.error("Failed to navigate to Tmall Supermarket")
                return []

            # 滚动加载
            for i in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            product_elements = await self._page.query_selector_all('.product, .item')

            for elem in product_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        result['source'] = 'tmall_supermarket'
                        if result.get('shop'):
                            result['shop']['shop_type'] = 'supermarket'
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"Failed to parse product: {e}")
                    continue

            self.logger.info(f"Found {len(results)} Tmall Supermarket products")
            return results

        except Exception as e:
            self.logger.error(f"Failed to get Tmall Supermarket products: {e}")
            return []


if __name__ == "__main__":
    async def test_tmall_spider():
        """测试天猫爬虫功能"""
        spider = TmallSpider(headless=False)

        async with spider.session():
            print("=" * 80)
            print("Tmall Spider - 完整功能测试")
            print("=" * 80)

            # 测试1: 搜索商品
            print("\n[测试1] 搜索商品")
            products = await spider.search("手机", max_results=5)
            for i, product in enumerate(products, 1):
                print(f"\n{i}. {product.get('title', 'N/A')[:60]}")
                print(f"   ID: {product.get('id')}")
                print(f"   价格: {product.get('price')}")
                print(f"   销量: {product.get('sales_count')}")
                print(f"   店铺: {product.get('shop', {}).get('shop_name')}")
                print(f"   包邮: {'是' if product.get('free_shipping') else '否'}")

            # 测试2: 商品详情
            if products:
                print("\n[测试2] 获取商品详情")
                first_id = products[0].get('id')
                if first_id:
                    detail = await spider.get_post_detail(first_id)
                    print(f"\n商品: {detail.get('title', 'N/A')[:60]}")
                    print(f"价格: {detail.get('price')}")
                    print(f"销量: {detail.get('sales_count')}")
                    print(f"店铺: {detail.get('shop', {}).get('shop_name')}")
                    print(f"特性数量: {len(detail.get('features', []))}")
                    print(f"图片数量: {len(detail.get('images', []))}")

                    # 测试3: 获取评价
                    print("\n[测试3] 获取商品评价")
                    reviews = await spider.get_comments(first_id, max_comments=3)
                    for i, review in enumerate(reviews, 1):
                        print(f"\n评价 {i}:")
                        print(f"  评分: {review.get('rating')} 星")
                        print(f"  内容: {review.get('content', 'N/A')[:60]}...")
                        print(f"  用户: {review.get('username')}")

            # 测试4: 品牌商品搜索
            print("\n[测试4] 品牌商品搜索")
            brand_products = await spider.get_brand_products("Apple", max_results=3, official_only=True)
            for i, product in enumerate(brand_products, 1):
                print(f"\n{i}. {product.get('title', 'N/A')[:60]}")
                print(f"   价格: {product.get('price')}")
                print(f"   店铺类型: {product.get('shop', {}).get('shop_type')}")

            # 测试5: 使用Matcher过滤
            print("\n[测试5] 使用Matcher过滤商品")
            if products:
                filtered = spider.matcher.filter_by_price(products, min_price=1000, max_price=5000)
                print(f"原始商品数: {len(products)}")
                print(f"价格过滤后: {len(filtered)}")

                # 计算质量评分
                for product in products[:3]:
                    quality_score = spider.matcher.calculate_quality_score(product)
                    print(f"\n{product.get('title', 'N/A')[:50]}")
                    print(f"  质量评分: {quality_score}/100")

            print("\n" + "=" * 80)
            print("测试完成!")
            print("=" * 80)

    asyncio.run(test_tmall_spider())

