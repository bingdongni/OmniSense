"""
Taobao (淘宝) Spider Implementation
完整的淘宝电商平台爬虫实现 - 企业级4层架构

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
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, parse_qs

from omnisense.spider.base import BaseSpider


# ============================================================================
# 数据模型定义
# ============================================================================

class TaobaoSortType(Enum):
    """淘宝排序类型"""
    DEFAULT = "default"  # 综合排序
    SALES = "sale-desc"  # 销量从高到低
    PRICE_ASC = "price-asc"  # 价格从低到高
    PRICE_DESC = "price-desc"  # 价格从高到低
    CREDIT = "credit-desc"  # 信用从高到低
    NEW = "new-desc"  # 新品优先


class ShopType(Enum):
    """店铺类型"""
    TAOBAO = "taobao"  # 淘宝店铺
    TMALL = "tmall"  # 天猫店铺
    GLOBAL = "global"  # 全球购
    UNKNOWN = "unknown"


@dataclass
class TaobaoPrice:
    """价格信息"""
    amount: Decimal
    currency: str = "CNY"
    display_text: str = ""
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[int] = None
    promotion_price: Optional[Decimal] = None

    def get_savings(self) -> Optional[Decimal]:
        """计算节省金额"""
        if self.original_price and self.amount:
            return self.original_price - self.amount
        return None


@dataclass
class TaobaoSKU:
    """商品SKU信息"""
    sku_id: str
    properties: Dict[str, str]  # 属性键值对，如 {"颜色": "红色", "尺码": "M"}
    price: Optional[TaobaoPrice] = None
    stock: int = 0
    image_url: Optional[str] = None

    # SKU属性
    color: Optional[str] = None
    size: Optional[str] = None
    style: Optional[str] = None


@dataclass
class TaobaoShop:
    """店铺信息"""
    shop_id: str
    shop_name: str
    shop_type: ShopType = ShopType.UNKNOWN

    # 店铺评分
    description_score: Optional[float] = None  # 描述相符
    service_score: Optional[float] = None  # 服务态度
    logistics_score: Optional[float] = None  # 物流服务

    # 店铺统计
    product_count: int = 0
    followers: int = 0
    sales_count: int = 0

    # 店铺详情
    location: Optional[str] = None
    established_date: Optional[datetime] = None
    credit_level: Optional[str] = None
    shop_url: Optional[str] = None


@dataclass
class TaobaoProduct:
    """淘宝商品完整信息"""
    item_id: str
    title: str
    url: str

    # 价格信息
    price: Optional[TaobaoPrice] = None

    # 销售信息
    sales_count: int = 0
    monthly_sales: int = 0

    # 评价信息
    rating: Optional[float] = None
    review_count: int = 0
    positive_rate: Optional[float] = None  # 好评率

    # 商品详情
    description: str = ""
    features: List[str] = field(default_factory=list)

    # 图片和视频
    main_image: Optional[str] = None
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)

    # 分类信息
    category: Optional[str] = None
    categories_path: List[str] = field(default_factory=list)

    # 商品属性
    brand: Optional[str] = None
    location: Optional[str] = None  # 发货地
    in_stock: bool = False

    # 配送信息
    free_shipping: bool = False
    delivery_time: Optional[str] = None

    # 店铺信息
    shop: Optional[TaobaoShop] = None

    # SKU信息
    skus: List[TaobaoSKU] = field(default_factory=list)

    # 商品规格
    specifications: Dict[str, str] = field(default_factory=dict)

    # 时间戳
    scraped_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# Layer 2: Anti-Crawl Layer - 反爬虫机制
# ============================================================================

class TaobaoAntiCrawl:
    """淘宝反爬虫处理层"""

    # 30+ User-Agent池
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Mobile Chrome
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        # Mobile Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Additional variants
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    ]

    def __init__(self, logger):
        self.logger = logger
        self.request_count = 0
        self.last_request_time = 0
        self.session_id = self._generate_session_id()
        self.device_id = self._generate_device_id()
        self.umid_token = self._generate_umid_token()
        self.captcha_count = 0
        self.blocked_count = 0

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = int(time.time() * 1000)
        random_part = ''.join(random.choices('0123456789abcdef', k=16))
        return f"{timestamp}-{random_part}"

    def _generate_device_id(self) -> str:
        """生成设备ID"""
        return ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=32))

    def _generate_umid_token(self) -> str:
        """生成淘宝UMID Token"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789ABCDEF', k=16))
        return f"{timestamp}_{random_str}"

    def generate_token(self) -> str:
        """生成淘宝Token"""
        timestamp = int(time.time() * 1000)
        random_num = random.randint(10000000, 99999999)
        token_str = f"{timestamp}_{random_num}_{self.device_id}"
        return hashlib.md5(token_str.encode()).hexdigest()

    def generate_sign(self, params: Dict[str, Any]) -> str:
        """生成淘宝Sign签名算法

        淘宝的签名机制用于验证请求合法性
        """
        # 按key排序参数
        sorted_params = sorted(params.items(), key=lambda x: x[0])

        # 拼接参数字符串
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params if v is not None])

        # 添加密钥（实际应用中需要从淘宝获取）
        secret_key = "taobao_secret_key_placeholder"
        sign_str = f"{secret_key}{param_str}{secret_key}"

        # MD5签名
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

        return sign

    def get_user_agents(self) -> List[str]:
        """获取所有User-Agent"""
        return self.USER_AGENTS.copy()

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

    async def smart_delay(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """智能延迟 - 模拟人类行为"""
        self.request_count += 1

        # 基础延迟
        base_delay = random.uniform(min_delay, max_delay)

        # 根据请求频率调整
        if self.request_count % 10 == 0:
            # 每10个请求增加额外延迟
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

    def handle_rate_limit(self, response_code: int) -> bool:
        """处理限流"""
        rate_limit_codes = [429, 503]

        if response_code in rate_limit_codes:
            self.logger.warning(f"检测到限流，响应码: {response_code}")
            return True

        return False

    def detect_captcha(self, page_content: str) -> bool:
        """检测验证码"""
        captcha_indicators = [
            '请输入验证码',
            '滑动验证',
            '点击完成验证',
            'nc_1_n1z',
            'sufei-captcha',
            'baxia-dialog',
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
            '访问被拒绝',
            '请求异常',
            '系统繁忙',
            '访问过于频繁',
            'blocked',
        ]

        content_lower = page_content.lower()
        for indicator in block_indicators:
            if indicator.lower() in content_lower:
                self.logger.error(f"访问被阻止: {indicator}")
                self.blocked_count += 1
                return True
        return False

    async def handle_captcha(self, page) -> bool:
        """处理验证码 - 简单重试机制"""
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
        # 每50个请求或遇到3次验证码后轮换
        if self.request_count >= 50 or self.captcha_count >= 3:
            return True
        return False

    def reset_session(self):
        """重置会话"""
        self.logger.info("重置会话...")
        self.session_id = self._generate_session_id()
        self.device_id = self._generate_device_id()
        self.umid_token = self._generate_umid_token()
        self.request_count = 0
        self.captcha_count = 0


# ============================================================================
# Layer 3: Matcher Layer - 智能匹配和过滤
# ============================================================================

class TaobaoMatcher:
    """淘宝商品匹配和过滤层"""

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
                self.logger.debug(f"解析价格失败 {price_str}: {e}")
                continue

        self.logger.info(f"价格过滤: {len(products)} -> {len(filtered)} 个商品")
        return filtered

    def filter_by_sales(
        self,
        products: List[Dict[str, Any]],
        min_sales: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """按销量过滤商品"""
        if min_sales is None:
            return products

        filtered = []
        for product in products:
            sales_str = product.get('sales', '')
            if not sales_str:
                continue

            try:
                sales_count = self._extract_sales_count(sales_str)
                if sales_count is not None and sales_count >= min_sales:
                    filtered.append(product)
            except Exception as e:
                self.logger.debug(f"解析销量失败 {sales_str}: {e}")
                continue

        self.logger.info(f"销量过滤: {len(products)} -> {len(filtered)} 个商品")
        return filtered

    def filter_by_shop_type(
        self,
        products: List[Dict[str, Any]],
        shop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """按店铺类型过滤

        Args:
            shop_type: 'tmall' 只要天猫, 'taobao' 只要淘宝
        """
        if not shop_type:
            return products

        filtered = []
        for product in products:
            url = product.get('url', '')

            if shop_type == 'tmall':
                if 'tmall.com' in url or 'detail.tmall.com' in url:
                    filtered.append(product)
            elif shop_type == 'taobao':
                if 'item.taobao.com' in url and 'tmall.com' not in url:
                    filtered.append(product)

        self.logger.info(f"店铺类型过滤 ({shop_type}): {len(products)} -> {len(filtered)} 个商品")
        return filtered

    def filter_by_location(
        self,
        products: List[Dict[str, Any]],
        locations: List[str]
    ) -> List[Dict[str, Any]]:
        """按发货地过滤"""
        if not locations:
            return products

        locations_lower = [loc.lower() for loc in locations]
        filtered = []

        for product in products:
            location = product.get('location', '').lower()
            if any(loc in location for loc in locations_lower):
                filtered.append(product)

        self.logger.info(f"发货地过滤: {len(products)} -> {len(filtered)} 个商品")
        return filtered

    def filter_by_keywords(
        self,
        products: List[Dict[str, Any]],
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """按关键词过滤标题"""
        filtered = products.copy()

        # 包含关键词过滤
        if include_keywords:
            include_lower = [kw.lower() for kw in include_keywords]
            filtered = [
                p for p in filtered
                if any(kw in p.get('title', '').lower() for kw in include_lower)
            ]
            self.logger.info(f"包含关键词过滤: {len(products)} -> {len(filtered)} 个商品")

        # 排除关键词过滤
        if exclude_keywords:
            exclude_lower = [kw.lower() for kw in exclude_keywords]
            filtered = [
                p for p in filtered
                if not any(kw in p.get('title', '').lower() for kw in exclude_lower)
            ]
            self.logger.info(f"排除关键词过滤后: {len(filtered)} 个商品")

        return filtered

    def calculate_quality_score(self, product: Dict[str, Any]) -> float:
        """计算商品质量评分 (0-100)"""
        score = 0.0

        # 销量权重 30%
        sales_str = product.get('sales', '')
        if sales_str:
            sales_count = self._extract_sales_count(sales_str)
            if sales_count:
                # 对数缩放，10000+销量得满分
                sales_score = min(30, (sales_count / 10000) * 30)
                score += sales_score

        # 价格合理性权重 20%
        price_str = product.get('price', '')
        if price_str:
            price_value = self._extract_price_value(price_str)
            if price_value:
                # 价格在合理区间得分更高
                if 50 <= price_value <= 500:
                    score += 20
                elif 20 <= price_value <= 1000:
                    score += 15
                else:
                    score += 10

        # 店铺类型权重 25%
        url = product.get('url', '')
        if 'tmall.com' in url:
            score += 25  # 天猫店铺
        elif 'taobao.com' in url:
            score += 15  # 淘宝店铺

        # 标题完整性权重 15%
        title = product.get('title', '')
        if len(title) > 20:
            score += 15
        elif len(title) > 10:
            score += 10
        else:
            score += 5

        # 图片存在权重 10%
        if product.get('thumbnail'):
            score += 10

        return round(score, 2)

    def calculate_value_score(self, product: Dict[str, Any]) -> Optional[float]:
        """计算性价比评分"""
        price_str = product.get('price', '')
        sales_str = product.get('sales', '')

        if not price_str or not sales_str:
            return None

        try:
            price = self._extract_price_value(price_str)
            sales = self._extract_sales_count(sales_str)

            if price is None or price <= 0 or sales is None:
                return None

            # 性价比 = 销量 / 价格
            # 销量越高、价格越低，性价比越好
            import math
            value_score = sales / math.log10(max(price, 1) + 10)
            return round(value_score, 2)
        except Exception:
            return None

    def sort_products(
        self,
        products: List[Dict[str, Any]],
        sort_by: str = "default"
    ) -> List[Dict[str, Any]]:
        """排序商品

        Args:
            sort_by: default, sales, price_asc, price_desc, quality, value
        """
        if sort_by == "default":
            return products

        try:
            if sort_by == "sales":
                products.sort(
                    key=lambda p: self._extract_sales_count(p.get('sales', '')) or 0,
                    reverse=True
                )
            elif sort_by == "price_asc":
                products.sort(
                    key=lambda p: self._extract_price_value(p.get('price', '')) or float('inf')
                )
            elif sort_by == "price_desc":
                products.sort(
                    key=lambda p: self._extract_price_value(p.get('price', '')) or 0,
                    reverse=True
                )
            elif sort_by == "quality":
                products.sort(
                    key=lambda p: self.calculate_quality_score(p),
                    reverse=True
                )
            elif sort_by == "value":
                products.sort(
                    key=lambda p: self.calculate_value_score(p) or 0,
                    reverse=True
                )

            self.logger.info(f"已按 {sort_by} 排序 {len(products)} 个商品")
        except Exception as e:
            self.logger.error(f"排序失败: {e}")

        return products

    def _extract_price_value(self, price_str: str) -> Optional[float]:
        """从价格字符串提取数值"""
        if not price_str:
            return None

        try:
            # 移除货币符号和其他字符
            price_clean = re.sub(r'[^\d.]', '', price_str)
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
            # 处理"1000+人付款"、"2.5万"等格式
            sales_clean = sales_str.lower()

            # 提取数字
            match = re.search(r'([\d.]+)([万千百]?)', sales_clean)
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

class TaobaoInteraction:
    """淘宝用户交互层"""

    def __init__(self, page, logger):
        self.page = page
        self.logger = logger

    async def add_to_cart(self, item_id: str, quantity: int = 1) -> bool:
        """添加商品到购物车"""
        try:
            self.logger.info(f"添加商品 {item_id} 到购物车 (数量: {quantity})")

            # 查找加入购物车按钮
            cart_button_selectors = [
                '.J_LinkAdd',
                '.tb-btn-buy',
                'a:has-text("加入购物车")',
                'button:has-text("加入购物车")',
            ]

            for selector in cart_button_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    # 设置数量
                    qty_input = await self.page.query_selector('.tb-amount-input')
                    if qty_input and quantity > 1:
                        await qty_input.fill(str(quantity))
                        await asyncio.sleep(0.5)

                    # 点击加入购物车
                    await button.click()
                    await asyncio.sleep(2)

                    # 检查是否成功
                    success_indicator = await self.page.query_selector('.tb-cart-success')
                    if success_indicator:
                        self.logger.info("成功添加到购物车")
                        return True

            self.logger.warning("未找到加入购物车按钮")
            return False

        except Exception as e:
            self.logger.error(f"添加到购物车失败: {e}")
            return False

    async def add_to_favorites(self, item_id: str) -> bool:
        """添加到收藏夹"""
        try:
            self.logger.info(f"收藏商品 {item_id}")

            # 查找收藏按钮
            favorite_button = await self.page.query_selector('.tb-fav-btn')
            if not favorite_button:
                favorite_button = await self.page.query_selector('a:has-text("收藏")')

            if favorite_button:
                await favorite_button.click()
                await asyncio.sleep(2)
                self.logger.info("成功添加到收藏夹")
                return True

            self.logger.warning("未找到收藏按钮")
            return False

        except Exception as e:
            self.logger.error(f"添加到收藏夹失败: {e}")
            return False

    async def follow_shop(self, shop_id: str) -> bool:
        """关注店铺"""
        try:
            self.logger.info(f"关注店铺 {shop_id}")

            # 查找关注按钮
            follow_button = await self.page.query_selector('.tb-follow-btn')
            if not follow_button:
                follow_button = await self.page.query_selector('a:has-text("关注店铺")')

            if follow_button:
                await follow_button.click()
                await asyncio.sleep(1)
                self.logger.info("成功关注店铺")
                return True

            return False

        except Exception as e:
            self.logger.error(f"关注店铺失败: {e}")
            return False

    async def submit_review(
        self,
        item_id: str,
        rating: int,
        content: str,
        images: Optional[List[str]] = None
    ) -> bool:
        """提交商品评价

        Args:
            item_id: 商品ID
            rating: 评分 (1-5)
            content: 评价内容
            images: 评价图片路径列表
        """
        try:
            self.logger.info(f"提交商品 {item_id} 的评价")

            # 选择评分
            star_selector = f'.rate-star-{rating}'
            star_elem = await self.page.query_selector(star_selector)
            if star_elem:
                await star_elem.click()
                await asyncio.sleep(0.5)

            # 填写评价内容
            content_input = await self.page.query_selector('.rate-content textarea')
            if content_input:
                await content_input.fill(content)
                await asyncio.sleep(1)

            # 上传图片（如果有）
            if images:
                upload_input = await self.page.query_selector('input[type="file"]')
                if upload_input:
                    for image_path in images[:9]:  # 最多9张
                        await upload_input.set_input_files(image_path)
                        await asyncio.sleep(1)

            # 提交评价
            submit_button = await self.page.query_selector('.rate-submit-btn')
            if submit_button:
                await submit_button.click()
                await asyncio.sleep(2)
                self.logger.info("成功提交评价")
                return True

            return False

        except Exception as e:
            self.logger.error(f"提交评价失败: {e}")
            return False


# ============================================================================
# Layer 1: Spider Layer - 核心爬虫功能
# ============================================================================

class TaobaoSpider(BaseSpider):
    """淘宝电商平台爬虫 - 完整4层架构实现"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="taobao", headless=headless, proxy=proxy)
        self.base_url = "https://www.taobao.com"
        self.api_base_url = "https://h5api.m.taobao.com"

        # 初始化各层
        self.anti_crawl = TaobaoAntiCrawl(self.logger)
        self.matcher = TaobaoMatcher(self.logger)
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
        """登录淘宝账户

        Args:
            username: 用户名（淘宝主要使用扫码登录）
            password: 密码

        Returns:
            bool: 登录是否成功
        """
        try:
            self.logger.info("登录淘宝...")

            # 尝试使用已保存的cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                if await self._safe_navigate(self.base_url):
                    # 检查登录状态
                    user_elem = await self._page.query_selector('.site-nav-user')
                    if user_elem:
                        self._is_logged_in = True
                        self.interaction = TaobaoInteraction(self._page, self.logger)
                        self.logger.info("使用已保存的cookies登录成功")
                        return True

            # 导航到登录页面
            if not await self._safe_navigate("https://login.taobao.com"):
                self.logger.error("无法导航到登录页面")
                return False

            self.logger.info("请扫描二维码登录 (等待60秒)...")

            # 等待用户扫码登录
            for _ in range(60):
                user_elem = await self._page.query_selector('.site-nav-user')
                if user_elem:
                    self._is_logged_in = True
                    self.interaction = TaobaoInteraction(self._page, self.logger)
                    await self._save_cookies()
                    self.logger.info("登录成功")
                    return True
                await asyncio.sleep(1)

            self.logger.error("登录超时")
            return False

        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        sort_by: str = "default",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        shop_type: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索淘宝商品 - 支持高级过滤

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            sort_by: 排序方式 (default, sales, price_asc, price_desc, credit)
            min_price: 最低价格
            max_price: 最高价格
            shop_type: 店铺类型 ('tmall' 或 'taobao')
            location: 发货地

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"搜索淘宝商品: '{keyword}'")

            # 构建搜索URL
            search_params = {'q': keyword}

            # 添加排序
            sort_map = {
                'sales': 'sale-desc',
                'price_asc': 'price-asc',
                'price_desc': 'price-desc',
                'credit': 'credit-desc',
            }
            if sort_by in sort_map:
                search_params['sort'] = sort_map[sort_by]

            # 添加价格范围
            if min_price is not None:
                search_params['start_price'] = str(min_price)
            if max_price is not None:
                search_params['end_price'] = str(max_price)

            # 天猫筛选
            if shop_type == 'tmall':
                search_params['filter'] = 'tmall'

            search_url = f"https://s.taobao.com/search?{urlencode(search_params)}"

            if not await self._safe_navigate(search_url):
                self.logger.error("无法导航到搜索页面")
                return []

            # 滚动加载更多
            for _ in range(max_results // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            # 使用多个选择器，因为淘宝结构会变化
            item_elements = await self._page.query_selector_all('.item, .Card--doubleCardWrapper--L2XFE73')

            self.logger.info(f"找到 {len(item_elements)} 个商品元素")

            for elem in item_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and (result.get('id') or result.get('url')):
                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"解析商品失败: {e}")
                    continue

            # 应用额外过滤
            if location:
                results = self.matcher.filter_by_location(results, [location])

            self.logger.info(f"成功解析 {len(results)} 个商品")
            return results

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []

    async def _parse_search_result(self, elem) -> Dict[str, Any]:
        """解析搜索结果中的单个商品"""
        result = {
            'platform': self.platform,
            'type': 'product'
        }

        # 标题和链接
        title_elem = await elem.query_selector('.title, .Title--title--jCOPvpf')
        link_elem = await elem.query_selector('a[href*="item.taobao.com"], a[href*="detail.tmall.com"]')

        if title_elem:
            result['title'] = (await title_elem.inner_text()).strip()

        if link_elem:
            href = await link_elem.get_attribute('href')
            if href:
                if not href.startswith('http'):
                    href = 'https:' + href
                result['url'] = href
                # 提取商品ID
                if 'id=' in href:
                    result['id'] = href.split('id=')[-1].split('&')[0]

        # 价格
        price_elem = await elem.query_selector('.price, .Price--priceInt--ZlsSi_M')
        if price_elem:
            price_text = await price_elem.inner_text()
            result['price'] = price_text.strip()

        # 销量
        sales_elem = await elem.query_selector('.deal-cnt, .RealSales--realSales--FhTZc7U')
        if sales_elem:
            sales_text = await sales_elem.inner_text()
            result['sales'] = sales_text.strip()

        # 店铺名称
        shop_elem = await elem.query_selector('.shop, .ShopInfo--shopName--rg6mGmy')
        if shop_elem:
            result['shop'] = (await shop_elem.inner_text()).strip()

        # 发货地
        location_elem = await elem.query_selector('.location, .Locaddress--address--ievZpAT')
        if location_elem:
            result['location'] = (await location_elem.inner_text()).strip()

        # 商品图片
        img = await elem.query_selector('img')
        if img:
            src = await img.get_attribute('src')
            if src:
                if not src.startswith('http'):
                    src = 'https:' + src
                result['thumbnail'] = src

        return result

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取淘宝店铺资料

        Args:
            user_id: 店铺ID

        Returns:
            店铺资料信息
        """
        try:
            self.logger.info(f"获取店铺资料: {user_id}")

            # 淘宝店铺页面
            shop_url = f"https://shop{user_id}.taobao.com"
            if not await self._safe_navigate(shop_url):
                self.logger.error("无法导航到店铺页面")
                return {}

            profile = {
                'user_id': user_id,
                'platform': self.platform,
                'type': 'shop',
                'shop_url': shop_url
            }

            # 店铺名称
            name_selectors = ['.shop-name', '.slogo-shopname', '.shop-header-title']
            for selector in name_selectors:
                name = await self._page.query_selector(selector)
                if name:
                    profile['shop_name'] = (await name.inner_text()).strip()
                    break

            # 店铺描述
            desc = await self._page.query_selector('.shop-description')
            if desc:
                profile['description'] = (await desc.inner_text()).strip()

            # 店铺统计
            stats = await self._page.query_selector_all('.shop-rank li, .shop-info li')
            for stat in stats:
                text = await stat.inner_text()
                if '宝贝' in text or '商品' in text:
                    profile['product_count'] = self.parser.parse_count(text)
                elif '粉丝' in text or '关注' in text:
                    profile['followers'] = self.parser.parse_count(text)
                elif '信用' in text:
                    profile['credit'] = text.strip()

            # 店铺评分（描述相符、服务态度、物流服务）
            score_elems = await self._page.query_selector_all('.shop-score-item')
            for elem in score_elems:
                try:
                    label = await elem.query_selector('.score-label')
                    value = await elem.query_selector('.score-value')
                    if label and value:
                        label_text = (await label.inner_text()).strip()
                        value_text = (await value.inner_text()).strip()

                        if '描述' in label_text:
                            profile['description_score'] = float(value_text)
                        elif '服务' in label_text:
                            profile['service_score'] = float(value_text)
                        elif '物流' in label_text:
                            profile['logistics_score'] = float(value_text)
                except:
                    continue

            # 店铺类型判断
            if 'tmall.com' in shop_url or await self._page.query_selector('.tmall-logo'):
                profile['shop_type'] = 'tmall'
            else:
                profile['shop_type'] = 'taobao'

            self.logger.info(f"成功获取店铺资料: {profile.get('shop_name', user_id)}")
            return profile

        except Exception as e:
            self.logger.error(f"获取店铺资料失败: {e}")
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
            self.logger.info(f"获取店铺商品: {user_id}")

            shop_url = f"https://shop{user_id}.taobao.com"
            if not await self._safe_navigate(shop_url):
                self.logger.error("无法导航到店铺页面")
                return []

            # 滚动加载商品
            for _ in range(max_posts // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            posts = []
            item_elements = await self._page.query_selector_all('.item, .J_TItems .item, .shop-item')

            for elem in item_elements[:max_posts]:
                try:
                    post = {
                        'user_id': user_id,
                        'platform': self.platform,
                        'type': 'product'
                    }

                    # 商品链接和ID
                    link = await elem.query_selector('a[href*="item.taobao.com"], a[href*="detail.tmall.com"]')
                    if link:
                        href = await link.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = 'https:' + href
                            post['url'] = href
                            if 'id=' in href:
                                post['id'] = href.split('id=')[-1].split('&')[0]

                    # 标题
                    title = await elem.query_selector('.title, .item-name, .item-title')
                    if title:
                        post['title'] = (await title.inner_text()).strip()

                    # 价格
                    price = await elem.query_selector('.price, .item-price')
                    if price:
                        post['price'] = (await price.inner_text()).strip()

                    # 销量
                    sales = await elem.query_selector('.sales, .item-sales')
                    if sales:
                        post['sales'] = (await sales.inner_text()).strip()

                    if post.get('id'):
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"解析商品失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(posts)} 个商品")
            return posts

        except Exception as e:
            self.logger.error(f"获取店铺商品失败: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """获取淘宝商品详细信息

        Args:
            post_id: 商品ID

        Returns:
            商品详细信息
        """
        try:
            self.logger.info(f"获取商品详情: {post_id}")

            # 尝试淘宝和天猫两种URL
            product_urls = [
                f"https://item.taobao.com/item.htm?id={post_id}",
                f"https://detail.tmall.com/item.htm?id={post_id}"
            ]

            product_url = None
            for url in product_urls:
                if await self._safe_navigate(url):
                    product_url = url
                    break

            if not product_url:
                self.logger.error("无法导航到商品页面")
                return {}

            post = {
                'id': post_id,
                'url': product_url,
                'platform': self.platform,
                'type': 'product'
            }

            # 商品标题
            title_selectors = ['.tb-main-title', '[data-spm="1000983"]', '.ItemTitle--mainTitle--']
            for selector in title_selectors:
                title = await self._page.query_selector(selector)
                if title:
                    post['title'] = (await title.inner_text()).strip()
                    break

            # 价格信息
            price_elem = await self._page.query_selector('.tb-rmb-num, .Price--priceText--, .tm-price')
            if price_elem:
                post['price'] = (await price_elem.inner_text()).strip()

            # 原价
            original_price_elem = await self._page.query_selector('.tb-original-price, .Price--originalText--')
            if original_price_elem:
                post['original_price'] = (await original_price_elem.inner_text()).strip()

            # 销量
            sales_selectors = ['.tb-sell-counter', '[class*="SalesCount"]', '.tm-count']
            for selector in sales_selectors:
                sales = await self._page.query_selector(selector)
                if sales:
                    post['sales'] = (await sales.inner_text()).strip()
                    break

            # 店铺信息
            shop_info = await self._parse_shop_info()
            if shop_info:
                post['shop'] = shop_info.get('shop_name')
                post['shop_id'] = shop_info.get('shop_id')
                post['shop_type'] = shop_info.get('shop_type')

            # 商品描述
            desc = await self._page.query_selector('#J_DivItemDesc, .tb-detail-hd')
            if desc:
                post['description'] = (await desc.inner_text()).strip()

            # 商品属性/规格
            specifications = await self._parse_product_specifications()
            if specifications:
                post['specifications'] = specifications

            # 商品图片
            images = []
            main_image = await self._page.query_selector('#J_ImgBooth, .ItemGallery--mainPic--')
            if main_image:
                main_src = await main_image.get_attribute('src')
                if main_src:
                    if not main_src.startswith('http'):
                        main_src = 'https:' + main_src
                    post['main_image'] = main_src
                    images.append(main_src)

            # 其他图片
            image_thumbs = await self._page.query_selector_all('#J_UlThumb img, .ItemGallery--thumbnail--')
            for img in image_thumbs[:10]:
                src = await img.get_attribute('src')
                if src and src not in images:
                    if not src.startswith('http'):
                        src = 'https:' + src
                    # 替换为高清图
                    src = src.replace('_50x50.jpg', '_430x430.jpg').replace('_60x60.jpg', '_430x430.jpg')
                    images.append(src)
            post['images'] = images

            # SKU信息
            skus = await self._parse_skus()
            if skus:
                post['skus'] = skus

            # 发货地
            location_elem = await self._page.query_selector('.tb-location, .ItemHeader--location--')
            if location_elem:
                post['location'] = (await location_elem.inner_text()).strip()

            # 配送信息
            delivery_elem = await self._page.query_selector('.tb-delivery, .Delivery--root--')
            if delivery_elem:
                delivery_text = await delivery_elem.inner_text()
                post['delivery_info'] = delivery_text.strip()
                post['free_shipping'] = '包邮' in delivery_text or '免运费' in delivery_text

            # 品牌
            brand_elem = await self._page.query_selector('.tb-brand, [class*="Brand"]')
            if brand_elem:
                post['brand'] = (await brand_elem.inner_text()).strip()

            # 库存状态
            stock_elem = await self._page.query_selector('.tb-stock, .Stock--root--')
            if stock_elem:
                stock_text = await stock_elem.inner_text()
                post['in_stock'] = '有货' in stock_text or '现货' in stock_text

            self.logger.info(f"成功获取商品详情: {post.get('title', post_id)[:50]}")
            return post

        except Exception as e:
            self.logger.error(f"获取商品详情失败: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """获取淘宝商品评价

        Args:
            post_id: 商品ID
            max_comments: 最大评价数

        Returns:
            评价列表
        """
        try:
            self.logger.info(f"获取商品评价: {post_id}")

            product_url = f"https://item.taobao.com/item.htm?id={post_id}"
            if post_id not in self._page.url:
                if not await self._safe_navigate(product_url):
                    return []

            # 点击评价标签
            reviews_tab = await self._page.query_selector('[data-spm="1000983.1000983.0.0"] a:has-text("累计评价")')
            if reviews_tab:
                await reviews_tab.click()
                await asyncio.sleep(2)

            # 加载更多评价
            for _ in range(max_comments // 20):
                load_more = await self._page.query_selector('.rate-page-next')
                if load_more:
                    try:
                        await load_more.click()
                        await asyncio.sleep(random.uniform(1, 2))
                    except:
                        break

            comments = []
            review_elements = await self._page.query_selector_all('.rate-item, [class*="Comment--item--"]')

            for elem in review_elements[:max_comments]:
                try:
                    comment = {
                        'post_id': post_id,
                        'platform': self.platform,
                        'type': 'review'
                    }

                    # 评论者名称
                    reviewer = await elem.query_selector('.rate-user-name, [class*="Comment--userName--"]')
                    if reviewer:
                        comment['username'] = (await reviewer.inner_text()).strip()

                    # 评价内容
                    text = await elem.query_selector('.rate-text, [class*="Comment--content--"]')
                    if text:
                        comment['content'] = (await text.inner_text()).strip()

                    # 评分
                    rating = await elem.query_selector('.rate-star, [class*="Comment--star--"]')
                    if rating:
                        rating_class = await rating.get_attribute('class')
                        if 'star' in rating_class:
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
                    date = await elem.query_selector('.rate-date, [class*="Comment--date--"]')
                    if date:
                        date_text = await date.inner_text()
                        comment['created_at'] = self.parser.parse_date(date_text)

                    # 购买规格
                    specs = await elem.query_selector('.rate-sku, [class*="Comment--sku--"]')
                    if specs:
                        comment['purchased_specs'] = (await specs.inner_text()).strip()

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(
                            f"{comment.get('username', '')}{comment['content']}".encode()
                        ).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"解析评价失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(comments)} 条评价")
            return comments

        except Exception as e:
            self.logger.error(f"获取评价失败: {e}")
            return []

    # ========================================================================
    # 辅助解析方法
    # ========================================================================

    async def _parse_shop_info(self) -> Optional[Dict[str, Any]]:
        """解析店铺信息"""
        try:
            shop_info = {}

            # 店铺名称
            shop_elem = await self._page.query_selector('.tb-shop-name a, .ShopHeader--name--')
            if shop_elem:
                shop_info['shop_name'] = (await shop_elem.inner_text()).strip()
                shop_href = await shop_elem.get_attribute('href')
                if shop_href and 'shop' in shop_href:
                    shop_info['shop_id'] = shop_href.split('shop')[-1].split('.')[0]

            # 判断店铺类型
            if await self._page.query_selector('.tmall-logo, .tm-logo'):
                shop_info['shop_type'] = 'tmall'
            else:
                shop_info['shop_type'] = 'taobao'

            return shop_info if shop_info else None

        except Exception as e:
            self.logger.debug(f"解析店铺信息失败: {e}")
            return None

    async def _parse_product_specifications(self) -> Dict[str, str]:
        """解析商品规格"""
        specifications = {}

        try:
            # 商品属性列表
            prop_elements = await self._page.query_selector_all('.tb-property-type li, [class*="Property--item--"]')
            for prop in prop_elements:
                try:
                    prop_text = await prop.inner_text()
                    if ':' in prop_text or '：' in prop_text:
                        parts = re.split('[：:]', prop_text, 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            specifications[key] = value
                except:
                    continue

        except Exception as e:
            self.logger.debug(f"解析商品规格失败: {e}")

        return specifications

    async def _parse_skus(self) -> List[Dict[str, Any]]:
        """解析SKU信息"""
        skus = []

        try:
            # 颜色/款式选项
            color_items = await self._page.query_selector_all('.tb-sku-item[data-value]')
            for item in color_items[:20]:
                try:
                    sku = {}
                    sku['sku_id'] = await item.get_attribute('data-value')

                    # SKU名称
                    title = await item.get_attribute('title')
                    if title:
                        sku['name'] = title.strip()

                    # SKU图片
                    img = await item.query_selector('img')
                    if img:
                        img_src = await img.get_attribute('src')
                        if img_src:
                            if not img_src.startswith('http'):
                                img_src = 'https:' + img_src
                            sku['image_url'] = img_src

                    if sku.get('sku_id'):
                        skus.append(sku)

                except:
                    continue

        except Exception as e:
            self.logger.debug(f"解析SKU失败: {e}")

        return skus

    # ========================================================================
    # 扩展功能方法
    # ========================================================================

    async def get_shop_products(
        self,
        shop_id: str,
        max_results: int = 50,
        sort_by: str = "default"
    ) -> List[Dict[str, Any]]:
        """获取店铺所有商品

        Args:
            shop_id: 店铺ID
            max_results: 最大结果数
            sort_by: 排序方式

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"获取店铺 {shop_id} 的商品列表")

            # 构建店铺商品列表URL
            shop_url = f"https://shop{shop_id}.taobao.com/search.htm"

            # 添加排序参数
            if sort_by != "default":
                sort_map = {
                    'sales': 'sale-desc',
                    'price_asc': 'price-asc',
                    'price_desc': 'price-desc',
                }
                if sort_by in sort_map:
                    shop_url += f"?orderType={sort_map[sort_by]}"

            if not await self._safe_navigate(shop_url):
                self.logger.error("无法导航到店铺商品页面")
                return []

            # 滚动加载
            for _ in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            item_elements = await self._page.query_selector_all('.item, .shop-item')

            for elem in item_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        result['shop_id'] = shop_id
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"解析商品失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(results)} 个店铺商品")
            return results

        except Exception as e:
            self.logger.error(f"获取店铺商品失败: {e}")
            return []

    async def get_hot_products(
        self,
        category: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """获取热销商品

        Args:
            category: 分类（可选）
            max_results: 最大结果数

        Returns:
            热销商品列表
        """
        try:
            self.logger.info(f"获取热销商品")

            # 构建热销榜URL
            if category:
                hot_url = f"https://s.taobao.com/search?q={category}&sort=sale-desc"
            else:
                hot_url = "https://ai.taobao.com/search/index.htm"

            if not await self._safe_navigate(hot_url):
                self.logger.error("无法导航到热销页面")
                return []

            # 滚动加载
            for _ in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            item_elements = await self._page.query_selector_all('.item, .Card--doubleCardWrapper--L2XFE73')

            for elem in item_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        result['is_hot'] = True
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"解析商品失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(results)} 个热销商品")
            return results

        except Exception as e:
            self.logger.error(f"获取热销商品失败: {e}")
            return []

    async def search_shops(
        self,
        keyword: str,
        max_results: int = 20,
        shop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索店铺

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            shop_type: 店铺类型 ('tmall' 或 'taobao')

        Returns:
            店铺列表
        """
        try:
            self.logger.info(f"搜索店铺: '{keyword}'")

            # 构建店铺搜索URL
            search_url = f"https://s.taobao.com/search?q={keyword}&search_type=shop"

            if shop_type == 'tmall':
                search_url += "&filter=tmall"

            if not await self._safe_navigate(search_url):
                self.logger.error("无法导航到店铺搜索页面")
                return []

            # 滚动加载
            for _ in range(max_results // 10):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            shops = []
            shop_elements = await self._page.query_selector_all('.shop-item, .ShopCard--root--')

            for elem in shop_elements[:max_results]:
                try:
                    shop = {
                        'platform': self.platform,
                        'type': 'shop'
                    }

                    # 店铺名称和链接
                    name_elem = await elem.query_selector('.shop-name, .ShopCard--name--')
                    if name_elem:
                        shop['shop_name'] = (await name_elem.inner_text()).strip()

                    link_elem = await elem.query_selector('a[href*="shop"]')
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = 'https:' + href
                            shop['shop_url'] = href
                            # 提取店铺ID
                            if 'shop' in href:
                                match = re.search(r'shop(\d+)', href)
                                if match:
                                    shop['shop_id'] = match.group(1)

                    # 店铺评分
                    score_elem = await elem.query_selector('.shop-score')
                    if score_elem:
                        shop['score'] = (await score_elem.inner_text()).strip()

                    # 商品数量
                    product_count_elem = await elem.query_selector('.shop-product-count')
                    if product_count_elem:
                        count_text = await product_count_elem.inner_text()
                        shop['product_count'] = self.parser.parse_count(count_text)

                    if shop.get('shop_id'):
                        shops.append(shop)

                except Exception as e:
                    self.logger.warning(f"解析店铺失败: {e}")
                    continue

            self.logger.info(f"找到 {len(shops)} 个店铺")
            return shops

        except Exception as e:
            self.logger.error(f"搜索店铺失败: {e}")
            return []

    async def get_category_products(
        self,
        category_id: str,
        max_results: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """按分类浏览商品

        Args:
            category_id: 分类ID
            max_results: 最大结果数
            filters: 额外过滤条件

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"浏览分类: {category_id}")

            # 构建分类URL
            category_url = f"https://s.taobao.com/list?cat={category_id}"

            # 添加过滤条件
            if filters:
                params = []
                if filters.get('min_price'):
                    params.append(f"start_price={filters['min_price']}")
                if filters.get('max_price'):
                    params.append(f"end_price={filters['max_price']}")
                if filters.get('location'):
                    params.append(f"loc={filters['location']}")

                if params:
                    category_url += "&" + "&".join(params)

            if not await self._safe_navigate(category_url):
                self.logger.error("无法导航到分类页面")
                return []

            # 滚动加载
            for _ in range(min((max_results // 20) + 1, 3)):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            item_elements = await self._page.query_selector_all('.item, .Card--doubleCardWrapper--L2XFE73')

            for elem in item_elements[:max_results]:
                try:
                    result = await self._parse_search_result(elem)
                    if result and result.get('id'):
                        result['category_id'] = category_id
                        results.append(result)
                except Exception as e:
                    self.logger.warning(f"解析商品失败: {e}")
                    continue

            self.logger.info(f"找到 {len(results)} 个分类商品")
            return results

        except Exception as e:
            self.logger.error(f"浏览分类失败: {e}")
            return []

    async def get_product_recommendations(
        self,
        item_id: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """获取商品推荐（相关商品）

        Args:
            item_id: 商品ID
            max_results: 最大结果数

        Returns:
            推荐商品列表
        """
        try:
            self.logger.info(f"获取商品 {item_id} 的推荐")

            # 导航到商品页面
            product_url = f"https://item.taobao.com/item.htm?id={item_id}"
            if not await self._safe_navigate(product_url):
                return []

            recommendations = []

            # 查找"看了又看"推荐
            recommend_elements = await self._page.query_selector_all('.recommend-item, .related-item')

            for elem in recommend_elements[:max_results]:
                try:
                    rec = await self._parse_search_result(elem)
                    if rec and rec.get('id'):
                        rec['recommendation_type'] = 'related'
                        recommendations.append(rec)
                except:
                    continue

            self.logger.info(f"获取到 {len(recommendations)} 个推荐商品")
            return recommendations

        except Exception as e:
            self.logger.error(f"获取推荐商品失败: {e}")
            return []

    async def compare_products(
        self,
        item_ids: List[str]
    ) -> Dict[str, Any]:
        """比较多个商品

        Args:
            item_ids: 商品ID列表

        Returns:
            比较结果
        """
        try:
            self.logger.info(f"比较 {len(item_ids)} 个商品")

            comparison = {
                'products': [],
                'comparison_time': datetime.now().isoformat()
            }

            for item_id in item_ids:
                detail = await self.get_post_detail(item_id)
                if detail:
                    comparison['products'].append(detail)

            # 计算比较指标
            if comparison['products']:
                prices = [
                    self.matcher._extract_price_value(p.get('price', ''))
                    for p in comparison['products']
                ]
                prices = [p for p in prices if p is not None]

                if prices:
                    comparison['price_range'] = {
                        'min': min(prices),
                        'max': max(prices),
                        'avg': sum(prices) / len(prices)
                    }

                # 质量评分比较
                for product in comparison['products']:
                    product['quality_score'] = self.matcher.calculate_quality_score(product)
                    product['value_score'] = self.matcher.calculate_value_score(product)

                # 排序推荐
                comparison['products'].sort(
                    key=lambda p: p.get('quality_score', 0),
                    reverse=True
                )
                comparison['best_quality'] = comparison['products'][0].get('id')

                comparison['products'].sort(
                    key=lambda p: p.get('value_score', 0),
                    reverse=True
                )
                comparison['best_value'] = comparison['products'][0].get('id')

            self.logger.info(f"商品比较完成")
            return comparison

        except Exception as e:
            self.logger.error(f"商品比较失败: {e}")
            return {}

    async def track_price_changes(
        self,
        item_id: str,
        check_interval: int = 3600
    ) -> Dict[str, Any]:
        """追踪商品价格变化

        Args:
            item_id: 商品ID
            check_interval: 检查间隔（秒）

        Returns:
            价格变化信息
        """
        try:
            self.logger.info(f"追踪商品 {item_id} 的价格变化")

            detail = await self.get_post_detail(item_id)
            if not detail:
                return {}

            price_info = {
                'item_id': item_id,
                'title': detail.get('title'),
                'current_price': detail.get('price'),
                'original_price': detail.get('original_price'),
                'check_time': datetime.now().isoformat(),
                'check_interval': check_interval
            }

            # 计算价格变化
            current = self.matcher._extract_price_value(detail.get('price', ''))
            original = self.matcher._extract_price_value(detail.get('original_price', ''))

            if current and original:
                price_info['discount_amount'] = original - current
                price_info['discount_percentage'] = round(
                    ((original - current) / original) * 100, 2
                )

            return price_info

        except Exception as e:
            self.logger.error(f"追踪价格失败: {e}")
            return {}


if __name__ == "__main__":
    async def test_taobao_spider():
        """测试淘宝爬虫功能"""
        spider = TaobaoSpider(headless=False)

        async with spider.session():
            print("=" * 80)
            print("淘宝爬虫 - 完整功能测试")
            print("=" * 80)

            # 测试1: 搜索商品
            print("\n[测试1] 搜索商品 - 高级过滤")
            products = await spider.search(
                "手机",
                max_results=5,
                sort_by="sales",
                min_price=1000,
                max_price=5000,
                shop_type="tmall"
            )

            for i, product in enumerate(products, 1):
                print(f"\n{i}. {product.get('title', 'N/A')[:60]}")
                print(f"   ID: {product.get('id')}")
                print(f"   价格: {product.get('price')}")
                print(f"   销量: {product.get('sales')}")
                print(f"   店铺: {product.get('shop')}")
                print(f"   发货地: {product.get('location')}")

            # 测试2: 使用Matcher过滤
            if products:
                print("\n[测试2] 使用Matcher过滤商品")
                filtered = spider.matcher.filter_by_price(products, min_price=2000, max_price=4000)
                print(f"价格过滤: {len(products)} -> {len(filtered)} 个商品")

                # 计算质量评分
                for product in filtered[:3]:
                    quality_score = spider.matcher.calculate_quality_score(product)
                    value_score = spider.matcher.calculate_value_score(product)
                    print(f"\n{product.get('title', 'N/A')[:50]}")
                    print(f"  质量评分: {quality_score}/100")
                    print(f"  性价比评分: {value_score}")

            # 测试3: 获取商品详情
            if products:
                print("\n[测试3] 获取商品详情")
                first_id = products[0].get('id')
                if first_id:
                    detail = await spider.get_post_detail(first_id)
                    print(f"\n商品: {detail.get('title', 'N/A')[:60]}")
                    print(f"价格: {detail.get('price')}")
                    print(f"原价: {detail.get('original_price')}")
                    print(f"销量: {detail.get('sales')}")
                    print(f"店铺: {detail.get('shop')}")
                    print(f"店铺类型: {detail.get('shop_type')}")
                    print(f"发货地: {detail.get('location')}")
                    print(f"包邮: {'是' if detail.get('free_shipping') else '否'}")
                    print(f"图片数量: {len(detail.get('images', []))}")
                    print(f"SKU数量: {len(detail.get('skus', []))}")
                    print(f"规格数量: {len(detail.get('specifications', {}))}")

                    # 测试4: 获取评价
                    print("\n[测试4] 获取商品评价")
                    reviews = await spider.get_comments(first_id, max_comments=3)
                    for i, review in enumerate(reviews, 1):
                        print(f"\n评价 {i}:")
                        print(f"  用户: {review.get('username', 'N/A')}")
                        print(f"  评分: {review.get('rating', 'N/A')} 星")
                        print(f"  内容: {review.get('content', 'N/A')[:80]}...")
                        print(f"  规格: {review.get('purchased_specs', 'N/A')}")

            # 测试5: 搜索店铺
            print("\n[测试5] 搜索店铺")
            shops = await spider.search_shops("数码", max_results=3, shop_type="tmall")
            for i, shop in enumerate(shops, 1):
                print(f"\n{i}. {shop.get('shop_name', 'N/A')}")
                print(f"   店铺ID: {shop.get('shop_id')}")
                print(f"   评分: {shop.get('score')}")
                print(f"   商品数: {shop.get('product_count')}")

            print("\n" + "=" * 80)
            print("测试完成!")
            print("=" * 80)

    asyncio.run(test_taobao_spider())
