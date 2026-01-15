"""
Xianyu (闲鱼) Spider Implementation
完整的闲鱼二手交易平台爬虫实现 - 企业级4层架构

架构说明:
- Layer 1: Spider Layer - 核心爬虫功能
- Layer 2: Anti-Crawl Layer - 反爬虫机制和安全防护
- Layer 3: Matcher Layer - 智能匹配和数据过滤
- Layer 4: Interaction Layer - 用户交互操作

闲鱼特色:
- 二手商品交易
- 同城优先推荐
- 芝麻信用评分
- 鱼塘社区功能
- 新旧程度评估
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

class XianyuCondition(Enum):
    """闲鱼商品新旧程度"""
    BRAND_NEW = "brand_new"  # 全新
    ALMOST_NEW = "almost_new"  # 几乎全新
    LIGHTLY_USED = "lightly_used"  # 轻微使用痕迹
    OBVIOUSLY_USED = "obviously_used"  # 明显使用痕迹
    HEAVILY_USED = "heavily_used"  # 重度使用


class XianyuSortType(Enum):
    """闲鱼排序类型"""
    DEFAULT = "default"  # 综合排序
    PRICE_ASC = "price_asc"  # 价格从低到高
    PRICE_DESC = "price_desc"  # 价格从高到低
    DISTANCE = "distance"  # 距离优先
    TIME_DESC = "time_desc"  # 最新发布


class XianyuTradeType(Enum):
    """交易方式"""
    FACE_TO_FACE = "face_to_face"  # 同城面交
    EXPRESS = "express"  # 快递邮寄
    BOTH = "both"  # 两者皆可


@dataclass
class XianyuLocation:
    """地理位置信息"""
    city: str
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance: Optional[float] = None  # 距离（公里）

    def get_display_text(self) -> str:
        """获取显示文本"""
        if self.district:
            return f"{self.city} {self.district}"
        return self.city


@dataclass
class XianyuPrice:
    """价格信息"""
    amount: Decimal
    currency: str = "CNY"
    display_text: str = ""
    original_price: Optional[Decimal] = None  # 原价（新品价格）
    discount_percentage: Optional[int] = None
    negotiable: bool = True  # 是否可议价

    def get_discount_rate(self) -> Optional[float]:
        """计算折扣率"""
        if self.original_price and self.amount:
            return float((self.original_price - self.amount) / self.original_price * 100)
        return None


@dataclass
class XianyuUser:
    """闲鱼用户信息"""
    user_id: str
    username: str
    avatar: Optional[str] = None

    # 信用信息
    sesame_credit: Optional[int] = None  # 芝麻信用分
    real_name_verified: bool = False  # 实名认证

    # 交易统计
    sold_count: int = 0  # 已卖出
    selling_count: int = 0  # 在售中
    want_count: int = 0  # 想要

    # 评价信息
    positive_rate: Optional[float] = None  # 好评率
    review_count: int = 0

    # 活跃度
    response_rate: Optional[float] = None  # 回复率
    response_time: Optional[str] = None  # 平均回复时间
    last_active: Optional[datetime] = None


@dataclass
class XianyuProduct:
    """闲鱼商品完整信息"""
    item_id: str
    title: str
    url: str

    # 价格信息
    price: Optional[XianyuPrice] = None

    # 商品状态
    condition: Optional[XianyuCondition] = None
    condition_description: str = ""  # 成色描述

    # 位置信息
    location: Optional[XianyuLocation] = None

    # 交易方式
    trade_type: XianyuTradeType = XianyuTradeType.BOTH
    free_shipping: bool = False

    # 商品详情
    description: str = ""
    category: Optional[str] = None
    brand: Optional[str] = None

    # 图片和视频
    main_image: Optional[str] = None
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)

    # 卖家信息
    seller: Optional[XianyuUser] = None

    # 互动数据
    view_count: int = 0
    want_count: int = 0  # 想要人数
    comment_count: int = 0

    # 时间信息
    published_at: Optional[datetime] = None
    scraped_at: datetime = field(default_factory=datetime.now)

    # 鱼塘信息
    fish_pond: Optional[str] = None  # 所属鱼塘


@dataclass
class XianyuFishPond:
    """鱼塘（社区）信息"""
    pond_id: str
    pond_name: str
    description: str = ""

    # 统计信息
    member_count: int = 0
    post_count: int = 0

    # 分类
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # 位置
    location: Optional[str] = None


# ============================================================================
# Layer 2: Anti-Crawl Layer - 反爬虫机制
# ============================================================================

class XianyuAntiCrawl:
    """闲鱼反爬虫处理层 - 基于淘宝系Token机制"""

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
        # Xianyu App User-Agents
        "Mozilla/5.0 (Linux; U; Android 13; zh-CN; Pixel 7 Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/100.0.4896.127 Mobile Safari/537.36 AliApp(IDLE/2.8.0)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 AliApp(IDLE/2.8.0)",
        "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36 AliApp(IDLE/2.7.5)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 AliApp(IDLE/2.7.5)",
        "Mozilla/5.0 (Linux; U; Android 11; zh-CN; Mi 11 Build/RKQ1.200826.002) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/100.0.4896.127 Mobile Safari/537.36 AliApp(IDLE/2.8.0)",
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
        """生成淘宝系UMID Token（闲鱼使用淘宝账号体系）"""
        timestamp = str(int(time.time() * 1000))
        random_str = ''.join(random.choices('0123456789ABCDEF', k=16))
        return f"{timestamp}_{random_str}"

    def generate_token(self) -> str:
        """生成闲鱼Token"""
        timestamp = int(time.time() * 1000)
        random_num = random.randint(10000000, 99999999)
        token_str = f"{timestamp}_{random_num}_{self.device_id}"
        return hashlib.md5(token_str.encode()).hexdigest()

    def generate_sign(self, params: Dict[str, Any]) -> str:
        """生成闲鱼Sign签名算法

        闲鱼使用淘宝系签名机制
        """
        # 按key排序参数
        sorted_params = sorted(params.items(), key=lambda x: x[0])

        # 拼接参数字符串
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params if v is not None])

        # 添加密钥
        secret_key = "xianyu_secret_key_placeholder"
        sign_str = f"{secret_key}{param_str}{secret_key}"

        # MD5签名
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

        return sign

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

    def detect_captcha(self, page_content: str) -> bool:
        """检测验证码"""
        captcha_indicators = [
            '请输入验证码',
            '滑动验证',
            '点击完成验证',
            'nc_1_n1z',
            'sufei-captcha',
            'baxia-dialog',
            '安全验证',
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
            '页面不存在',
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

class XianyuMatcher:
    """闲鱼商品匹配和过滤层 - 二手商品特色过滤"""

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

    def filter_by_location(
        self,
        products: List[Dict[str, Any]],
        city: Optional[str] = None,
        max_distance: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """按地理位置过滤 - 闲鱼特色同城功能"""
        if not city and max_distance is None:
            return products

        filtered = []
        for product in products:
            location = product.get('location', '')

            # 城市匹配
            if city:
                if city.lower() in location.lower():
                    filtered.append(product)
                    continue

            # 距离过滤
            if max_distance is not None:
                distance = product.get('distance')
                if distance is not None and distance <= max_distance:
                    filtered.append(product)

        self.logger.info(f"位置过滤: {len(products)} -> {len(filtered)} 个商品")
        return filtered

    def filter_by_condition(
        self,
        products: List[Dict[str, Any]],
        conditions: List[str]
    ) -> List[Dict[str, Any]]:
        """按商品成色过滤 - 闲鱼特色"""
        if not conditions:
            return products

        conditions_lower = [c.lower() for c in conditions]
        filtered = []

        for product in products:
            condition = product.get('condition', '').lower()
            condition_desc = product.get('condition_description', '').lower()

            # 检查成色是否匹配
            if any(cond in condition or cond in condition_desc for cond in conditions_lower):
                filtered.append(product)

        self.logger.info(f"成色过滤: {len(products)} -> {len(filtered)} 个商品")
        return filtered

    def filter_by_sesame_credit(
        self,
        products: List[Dict[str, Any]],
        min_credit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """按芝麻信用分过滤 - 闲鱼特色"""
        if min_credit is None:
            return products

        filtered = []
        for product in products:
            seller = product.get('seller', {})
            if isinstance(seller, dict):
                credit = seller.get('sesame_credit')
                if credit is not None and credit >= min_credit:
                    filtered.append(product)

        self.logger.info(f"芝麻信用过滤 (>={min_credit}): {len(products)} -> {len(filtered)} 个商品")
        return filtered

    def filter_by_trade_type(
        self,
        products: List[Dict[str, Any]],
        trade_type: str
    ) -> List[Dict[str, Any]]:
        """按交易方式过滤"""
        if not trade_type:
            return products

        filtered = []
        for product in products:
            product_trade_type = product.get('trade_type', '')

            if trade_type == 'face_to_face':
                if 'face' in product_trade_type.lower() or '同城' in product_trade_type or '面交' in product_trade_type:
                    filtered.append(product)
            elif trade_type == 'express':
                if 'express' in product_trade_type.lower() or '快递' in product_trade_type or '邮寄' in product_trade_type:
                    filtered.append(product)

        self.logger.info(f"交易方式过滤 ({trade_type}): {len(products)} -> {len(filtered)} 个商品")
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

    def calculate_value_score(self, product: Dict[str, Any]) -> float:
        """计算二手商品性价比评分 (0-100)"""
        score = 0.0

        # 价格合理性 30%
        price_str = product.get('price', '')
        if price_str:
            price_value = self._extract_price_value(price_str)
            if price_value:
                # 二手商品价格越低越好
                if price_value < 100:
                    score += 30
                elif price_value < 500:
                    score += 25
                elif price_value < 1000:
                    score += 20
                else:
                    score += 10

        # 成色评分 25%
        condition = product.get('condition', '').lower()
        if '全新' in condition or 'brand_new' in condition:
            score += 25
        elif '几乎全新' in condition or 'almost_new' in condition:
            score += 22
        elif '轻微' in condition or 'lightly' in condition:
            score += 18
        else:
            score += 10

        # 卖家信用 25%
        seller = product.get('seller', {})
        if isinstance(seller, dict):
            credit = seller.get('sesame_credit')
            if credit:
                if credit >= 750:
                    score += 25
                elif credit >= 700:
                    score += 20
                elif credit >= 650:
                    score += 15
                else:
                    score += 10

            # 实名认证加分
            if seller.get('real_name_verified'):
                score += 5

        # 距离评分 15%（同城优先）
        distance = product.get('distance')
        if distance is not None:
            if distance < 5:
                score += 15
            elif distance < 20:
                score += 12
            elif distance < 50:
                score += 8
            else:
                score += 5

        # 想要人数 5%
        want_count = product.get('want_count', 0)
        if want_count > 50:
            score += 5
        elif want_count > 20:
            score += 4
        elif want_count > 5:
            score += 3

        return round(score, 2)

    def calculate_seller_trust_score(self, seller: Dict[str, Any]) -> float:
        """计算卖家信任度评分 (0-100)"""
        score = 0.0

        # 芝麻信用 40%
        credit = seller.get('sesame_credit')
        if credit:
            if credit >= 750:
                score += 40
            elif credit >= 700:
                score += 35
            elif credit >= 650:
                score += 28
            elif credit >= 600:
                score += 20
            else:
                score += 10

        # 实名认证 20%
        if seller.get('real_name_verified'):
            score += 20

        # 好评率 20%
        positive_rate = seller.get('positive_rate')
        if positive_rate:
            score += (positive_rate / 100) * 20

        # 交易量 10%
        sold_count = seller.get('sold_count', 0)
        if sold_count > 100:
            score += 10
        elif sold_count > 50:
            score += 8
        elif sold_count > 20:
            score += 6
        elif sold_count > 5:
            score += 4

        # 回复率 10%
        response_rate = seller.get('response_rate')
        if response_rate:
            score += (response_rate / 100) * 10

        return round(score, 2)

    def sort_products(
        self,
        products: List[Dict[str, Any]],
        sort_by: str = "default"
    ) -> List[Dict[str, Any]]:
        """排序商品

        Args:
            sort_by: default, price_asc, price_desc, distance, time, value, trust
        """
        if sort_by == "default":
            return products

        try:
            if sort_by == "price_asc":
                products.sort(
                    key=lambda p: self._extract_price_value(p.get('price', '')) or float('inf')
                )
            elif sort_by == "price_desc":
                products.sort(
                    key=lambda p: self._extract_price_value(p.get('price', '')) or 0,
                    reverse=True
                )
            elif sort_by == "distance":
                products.sort(
                    key=lambda p: p.get('distance') or float('inf')
                )
            elif sort_by == "time":
                products.sort(
                    key=lambda p: p.get('published_at') or datetime.min,
                    reverse=True
                )
            elif sort_by == "value":
                products.sort(
                    key=lambda p: self.calculate_value_score(p),
                    reverse=True
                )
            elif sort_by == "trust":
                products.sort(
                    key=lambda p: self.calculate_seller_trust_score(p.get('seller', {})),
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


# ============================================================================
# Layer 4: Interaction Layer - 用户交互操作
# ============================================================================

class XianyuInteraction:
    """闲鱼用户交互层 - 二手交易特色功能"""

    def __init__(self, page, logger):
        self.page = page
        self.logger = logger

    async def click_want(self, item_id: str) -> bool:
        """点击"我想要" - 闲鱼特色功能"""
        try:
            self.logger.info(f"点击商品 {item_id} 的'我想要'")

            # 查找"我想要"按钮
            want_button_selectors = [
                'button:has-text("我想要")',
                '.want-btn',
                '[class*="want"]',
                'a:has-text("我想要")',
            ]

            for selector in want_button_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    await button.click()
                    await asyncio.sleep(1)
                    self.logger.info("成功点击'我想要'")
                    return True

            self.logger.warning("未找到'我想要'按钮")
            return False

        except Exception as e:
            self.logger.error(f"点击'我想要'失败: {e}")
            return False

    async def add_to_favorites(self, item_id: str) -> bool:
        """添加到收藏"""
        try:
            self.logger.info(f"收藏商品 {item_id}")

            # 查找收藏按钮
            favorite_button = await self.page.query_selector('.favorite-btn, button:has-text("收藏")')
            if favorite_button:
                await favorite_button.click()
                await asyncio.sleep(1)
                self.logger.info("成功添加到收藏")
                return True

            return False

        except Exception as e:
            self.logger.error(f"添加到收藏失败: {e}")
            return False

    async def send_message(self, item_id: str, message: str) -> bool:
        """发送私聊消息给卖家"""
        try:
            self.logger.info(f"向商品 {item_id} 的卖家发送消息")

            # 查找聊天按钮
            chat_button = await self.page.query_selector('button:has-text("私聊"), .chat-btn')
            if not chat_button:
                self.logger.warning("未找到私聊按钮")
                return False

            await chat_button.click()
            await asyncio.sleep(2)

            # 查找消息输入框
            message_input = await self.page.query_selector('textarea, input[type="text"]')
            if message_input:
                await message_input.fill(message)
                await asyncio.sleep(0.5)

                # 查找发送按钮
                send_button = await self.page.query_selector('button:has-text("发送")')
                if send_button:
                    await send_button.click()
                    await asyncio.sleep(1)
                    self.logger.info("成功发送消息")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False

    async def follow_seller(self, user_id: str) -> bool:
        """关注卖家"""
        try:
            self.logger.info(f"关注卖家 {user_id}")

            # 查找关注按钮
            follow_button = await self.page.query_selector('button:has-text("关注"), .follow-btn')
            if follow_button:
                await follow_button.click()
                await asyncio.sleep(1)
                self.logger.info("成功关注卖家")
                return True

            return False

        except Exception as e:
            self.logger.error(f"关注卖家失败: {e}")
            return False

    async def join_fish_pond(self, pond_id: str) -> bool:
        """加入鱼塘 - 闲鱼特色社区功能"""
        try:
            self.logger.info(f"加入鱼塘 {pond_id}")

            # 查找加入按钮
            join_button = await self.page.query_selector('button:has-text("加入鱼塘"), .join-pond-btn')
            if join_button:
                await join_button.click()
                await asyncio.sleep(1)
                self.logger.info("成功加入鱼塘")
                return True

            return False

        except Exception as e:
            self.logger.error(f"加入鱼塘失败: {e}")
            return False


# ============================================================================
# Layer 1: Spider Layer - 核心爬虫功能
# ============================================================================

class XianyuSpider(BaseSpider):
    """闲鱼二手交易平台爬虫 - 完整4层架构实现"""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        super().__init__(platform="xianyu", headless=headless, proxy=proxy)
        self.base_url = "https://www.goofish.com"
        self.api_base_url = "https://h5api.m.goofish.com"

        # 初始化各层
        self.anti_crawl = XianyuAntiCrawl(self.logger)
        self.matcher = XianyuMatcher(self.logger)
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
        """登录闲鱼账户（使用淘宝账号体系）

        Args:
            username: 用户名（闲鱼使用淘宝账号）
            password: 密码

        Returns:
            bool: 登录是否成功
        """
        try:
            self.logger.info("登录闲鱼...")

            # 尝试使用已保存的cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                if await self._safe_navigate(self.base_url):
                    # 检查登录状态
                    user_elem = await self._page.query_selector('.user-info, [class*="user"]')
                    if user_elem:
                        self._is_logged_in = True
                        self.interaction = XianyuInteraction(self._page, self.logger)
                        self.logger.info("使用已保存的cookies登录成功")
                        return True

            # 导航到登录页面（使用淘宝登录）
            if not await self._safe_navigate("https://login.taobao.com"):
                self.logger.error("无法导航到登录页面")
                return False

            self.logger.info("请扫描二维码登录 (等待60秒)...")

            # 等待用户扫码登录
            for _ in range(60):
                user_elem = await self._page.query_selector('.site-nav-user, [class*="user"]')
                if user_elem:
                    self._is_logged_in = True
                    self.interaction = XianyuInteraction(self._page, self.logger)
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
        city: Optional[str] = None,
        condition: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索闲鱼商品 - 支持高级过滤

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            sort_by: 排序方式 (default, price_asc, price_desc, distance, time)
            min_price: 最低价格
            max_price: 最高价格
            city: 城市（同城搜索）
            condition: 商品成色

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"搜索闲鱼商品: '{keyword}'")

            # 构建搜索URL
            search_params = {'q': keyword}

            # 添加排序
            sort_map = {
                'price_asc': 'price_asc',
                'price_desc': 'price_desc',
                'distance': 'distance',
                'time': 'time_desc',
            }
            if sort_by in sort_map:
                search_params['sort'] = sort_map[sort_by]

            # 添加价格范围
            if min_price is not None:
                search_params['start_price'] = str(min_price)
            if max_price is not None:
                search_params['end_price'] = str(max_price)

            # 同城搜索
            if city:
                search_params['city'] = city

            search_url = f"{self.base_url}/s?{urlencode(search_params)}"

            if not await self._safe_navigate(search_url):
                self.logger.error("无法导航到搜索页面")
                return []

            # 滚动加载更多
            for _ in range(max_results // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            results = []
            # 使用多个选择器
            item_elements = await self._page.query_selector_all(
                '.item, [class*="item"], [class*="product"], [class*="card"]'
            )

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
            if condition:
                results = self.matcher.filter_by_condition(results, [condition])

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
        title_elem = await elem.query_selector('[class*="title"], .title, h3, h4')
        link_elem = await elem.query_selector('a[href]')

        if title_elem:
            result['title'] = (await title_elem.inner_text()).strip()

        if link_elem:
            href = await link_elem.get_attribute('href')
            if href:
                if not href.startswith('http'):
                    href = 'https:' + href if href.startswith('//') else self.base_url + href
                result['url'] = href
                # 提取商品ID
                if 'id=' in href:
                    result['id'] = href.split('id=')[-1].split('&')[0]
                elif '/item/' in href:
                    result['id'] = href.split('/item/')[-1].split('?')[0]

        # 价格
        price_elem = await elem.query_selector('[class*="price"], .price')
        if price_elem:
            price_text = await price_elem.inner_text()
            result['price'] = price_text.strip()

        # 位置信息
        location_elem = await elem.query_selector('[class*="location"], [class*="city"], .location')
        if location_elem:
            result['location'] = (await location_elem.inner_text()).strip()

        # 距离
        distance_elem = await elem.query_selector('[class*="distance"]')
        if distance_elem:
            distance_text = await distance_elem.inner_text()
            result['distance_text'] = distance_text.strip()

        # 成色
        condition_elem = await elem.query_selector('[class*="condition"], [class*="quality"]')
        if condition_elem:
            result['condition'] = (await condition_elem.inner_text()).strip()

        # 卖家信息
        seller_elem = await elem.query_selector('[class*="seller"], [class*="user"]')
        if seller_elem:
            result['seller_name'] = (await seller_elem.inner_text()).strip()

        # 想要人数
        want_elem = await elem.query_selector('[class*="want"]')
        if want_elem:
            want_text = await want_elem.inner_text()
            result['want_count_text'] = want_text.strip()

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

        return result

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取闲鱼用户资料

        Args:
            user_id: 用户ID

        Returns:
            用户资料信息
        """
        try:
            self.logger.info(f"获取用户资料: {user_id}")

            # 闲鱼用户页面
            user_url = f"{self.base_url}/user/{user_id}"
            if not await self._safe_navigate(user_url):
                self.logger.error("无法导航到用户页面")
                return {}

            profile = {
                'user_id': user_id,
                'platform': self.platform,
                'type': 'user',
                'user_url': user_url
            }

            # 用户名
            name_elem = await self._page.query_selector('[class*="username"], [class*="nickname"], .username')
            if name_elem:
                profile['username'] = (await name_elem.inner_text()).strip()

            # 头像
            avatar_elem = await self._page.query_selector('[class*="avatar"] img, .avatar img')
            if avatar_elem:
                avatar_src = await avatar_elem.get_attribute('src')
                if avatar_src:
                    if not avatar_src.startswith('http'):
                        avatar_src = 'https:' + avatar_src
                    profile['avatar'] = avatar_src

            # 芝麻信用分
            credit_elem = await self._page.query_selector('[class*="credit"], [class*="sesame"]')
            if credit_elem:
                credit_text = await credit_elem.inner_text()
                # 提取数字
                credit_match = re.search(r'(\d+)', credit_text)
                if credit_match:
                    profile['sesame_credit'] = int(credit_match.group(1))

            # 实名认证
            verified_elem = await self._page.query_selector('[class*="verified"], [class*="realname"]')
            if verified_elem:
                profile['real_name_verified'] = True

            # 交易统计
            stats = await self._page.query_selector_all('[class*="stat"], .stat-item')
            for stat in stats:
                text = await stat.inner_text()
                if '已卖出' in text or '卖出' in text:
                    profile['sold_count'] = self.parser.parse_count(text)
                elif '在售' in text:
                    profile['selling_count'] = self.parser.parse_count(text)
                elif '想要' in text:
                    profile['want_count'] = self.parser.parse_count(text)

            # 好评率
            rate_elem = await self._page.query_selector('[class*="rate"], [class*="positive"]')
            if rate_elem:
                rate_text = await rate_elem.inner_text()
                rate_match = re.search(r'(\d+(?:\.\d+)?)%', rate_text)
                if rate_match:
                    profile['positive_rate'] = float(rate_match.group(1))

            # 回复率
            response_elem = await self._page.query_selector('[class*="response"]')
            if response_elem:
                response_text = await response_elem.inner_text()
                response_match = re.search(r'(\d+(?:\.\d+)?)%', response_text)
                if response_match:
                    profile['response_rate'] = float(response_match.group(1))

            self.logger.info(f"成功获取用户资料: {profile.get('username', user_id)}")
            return profile

        except Exception as e:
            self.logger.error(f"获取用户资料失败: {e}")
            return {}

    async def get_user_posts(self, user_id: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """获取用户发布的商品列表

        Args:
            user_id: 用户ID
            max_posts: 最大商品数

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"获取用户商品: {user_id}")

            user_url = f"{self.base_url}/user/{user_id}"
            if not await self._safe_navigate(user_url):
                self.logger.error("无法导航到用户页面")
                return []

            # 滚动加载商品
            for _ in range(max_posts // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            posts = []
            item_elements = await self._page.query_selector_all('.item, [class*="item"], [class*="product"]')

            for elem in item_elements[:max_posts]:
                try:
                    post = await self._parse_search_result(elem)
                    if post and post.get('id'):
                        post['user_id'] = user_id
                        posts.append(post)

                except Exception as e:
                    self.logger.warning(f"解析商品失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(posts)} 个商品")
            return posts

        except Exception as e:
            self.logger.error(f"获取用户商品失败: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """获取闲鱼商品详细信息

        Args:
            post_id: 商品ID

        Returns:
            商品详细信息
        """
        try:
            self.logger.info(f"获取商品详情: {post_id}")

            # 构建商品详情URL
            product_url = f"{self.base_url}/item/{post_id}"

            if not await self._safe_navigate(product_url):
                self.logger.error("无法导航到商品页面")
                return {}

            post = {
                'id': post_id,
                'url': product_url,
                'platform': self.platform,
                'type': 'product'
            }

            # 商品标题
            title_elem = await self._page.query_selector('[class*="title"], .title, h1')
            if title_elem:
                post['title'] = (await title_elem.inner_text()).strip()

            # 价格信息
            price_elem = await self._page.query_selector('[class*="price"], .price')
            if price_elem:
                post['price'] = (await price_elem.inner_text()).strip()

            # 原价（新品价格）
            original_price_elem = await self._page.query_selector('[class*="original"], [class*="new-price"]')
            if original_price_elem:
                post['original_price'] = (await original_price_elem.inner_text()).strip()

            # 商品成色
            condition_elem = await self._page.query_selector('[class*="condition"], [class*="quality"]')
            if condition_elem:
                post['condition'] = (await condition_elem.inner_text()).strip()

            # 成色描述
            condition_desc_elem = await self._page.query_selector('[class*="condition-desc"]')
            if condition_desc_elem:
                post['condition_description'] = (await condition_desc_elem.inner_text()).strip()

            # 位置信息
            location_elem = await self._page.query_selector('[class*="location"], [class*="city"]')
            if location_elem:
                post['location'] = (await location_elem.inner_text()).strip()

            # 距离
            distance_elem = await self._page.query_selector('[class*="distance"]')
            if distance_elem:
                post['distance_text'] = (await distance_elem.inner_text()).strip()

            # 交易方式
            trade_elem = await self._page.query_selector('[class*="trade-type"]')
            if trade_elem:
                trade_text = await trade_elem.inner_text()
                post['trade_type'] = trade_text.strip()
                if '同城' in trade_text or '面交' in trade_text:
                    post['face_to_face'] = True
                if '快递' in trade_text or '邮寄' in trade_text:
                    post['express'] = True

            # 包邮
            shipping_elem = await self._page.query_selector('[class*="shipping"]')
            if shipping_elem:
                shipping_text = await shipping_elem.inner_text()
                post['free_shipping'] = '包邮' in shipping_text or '免运费' in shipping_text

            # 商品描述
            desc_elem = await self._page.query_selector('[class*="description"], .description, [class*="detail"]')
            if desc_elem:
                post['description'] = (await desc_elem.inner_text()).strip()

            # 分类
            category_elem = await self._page.query_selector('[class*="category"]')
            if category_elem:
                post['category'] = (await category_elem.inner_text()).strip()

            # 品牌
            brand_elem = await self._page.query_selector('[class*="brand"]')
            if brand_elem:
                post['brand'] = (await brand_elem.inner_text()).strip()

            # 商品图片
            images = []
            main_image = await self._page.query_selector('[class*="main-image"] img, .main-img img')
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
            image_thumbs = await self._page.query_selector_all('[class*="thumb"] img, .thumbnail img')
            for img in image_thumbs[:20]:
                src = await img.get_attribute('src')
                if not src:
                    src = await img.get_attribute('data-src')
                if src and src not in images:
                    if not src.startswith('http'):
                        src = 'https:' + src
                    # 替换为高清图
                    src = src.replace('_50x50', '_800x800').replace('_60x60', '_800x800')
                    images.append(src)
            post['images'] = images

            # 卖家信息
            seller_info = await self._parse_seller_info()
            if seller_info:
                post['seller'] = seller_info

            # 互动数据
            view_elem = await self._page.query_selector('[class*="view"]')
            if view_elem:
                view_text = await view_elem.inner_text()
                post['view_count'] = self.parser.parse_count(view_text)

            want_elem = await self._page.query_selector('[class*="want"]')
            if want_elem:
                want_text = await want_elem.inner_text()
                post['want_count'] = self.parser.parse_count(want_text)

            # 发布时间
            time_elem = await self._page.query_selector('[class*="time"], [class*="publish"]')
            if time_elem:
                time_text = await time_elem.inner_text()
                post['published_at'] = self.parser.parse_date(time_text)

            # 鱼塘信息
            pond_elem = await self._page.query_selector('[class*="pond"], [class*="community"]')
            if pond_elem:
                post['fish_pond'] = (await pond_elem.inner_text()).strip()

            self.logger.info(f"成功获取商品详情: {post.get('title', post_id)[:50]}")
            return post

        except Exception as e:
            self.logger.error(f"获取商品详情失败: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """获取闲鱼商品评论/留言

        Args:
            post_id: 商品ID
            max_comments: 最大评论数

        Returns:
            评论列表
        """
        try:
            self.logger.info(f"获取商品评论: {post_id}")

            product_url = f"{self.base_url}/item/{post_id}"
            if post_id not in self._page.url:
                if not await self._safe_navigate(product_url):
                    return []

            # 点击评论标签
            comments_tab = await self._page.query_selector('[class*="comment"], a:has-text("留言")')
            if comments_tab:
                await comments_tab.click()
                await asyncio.sleep(2)

            # 滚动加载更多评论
            for _ in range(max_comments // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            comments = []
            comment_elements = await self._page.query_selector_all('[class*="comment-item"], .comment')

            for elem in comment_elements[:max_comments]:
                try:
                    comment = {
                        'post_id': post_id,
                        'platform': self.platform,
                        'type': 'comment'
                    }

                    # 评论者名称
                    user_elem = await elem.query_selector('[class*="username"], [class*="user"]')
                    if user_elem:
                        comment['username'] = (await user_elem.inner_text()).strip()

                    # 评论内容
                    text_elem = await elem.query_selector('[class*="content"], [class*="text"]')
                    if text_elem:
                        comment['content'] = (await text_elem.inner_text()).strip()

                    # 评论时间
                    time_elem = await elem.query_selector('[class*="time"], [class*="date"]')
                    if time_elem:
                        time_text = await time_elem.inner_text()
                        comment['created_at'] = self.parser.parse_date(time_text)

                    if comment.get('content'):
                        comment['id'] = hashlib.md5(
                            f"{comment.get('username', '')}{comment['content']}".encode()
                        ).hexdigest()[:16]
                        comments.append(comment)

                except Exception as e:
                    self.logger.warning(f"解析评论失败: {e}")
                    continue

            self.logger.info(f"获取到 {len(comments)} 条评论")
            return comments

        except Exception as e:
            self.logger.error(f"获取评论失败: {e}")
            return []

    # ========================================================================
    # 辅助解析方法
    # ========================================================================

    async def _parse_seller_info(self) -> Optional[Dict[str, Any]]:
        """解析卖家信息"""
        try:
            seller_info = {}

            # 卖家名称
            seller_elem = await self._page.query_selector('[class*="seller"], [class*="user-name"]')
            if seller_elem:
                seller_info['username'] = (await seller_elem.inner_text()).strip()

            # 卖家ID
            seller_link = await self._page.query_selector('[class*="seller"] a[href*="user"]')
            if seller_link:
                href = await seller_link.get_attribute('href')
                if href and '/user/' in href:
                    seller_info['user_id'] = href.split('/user/')[-1].split('?')[0]

            # 芝麻信用
            credit_elem = await self._page.query_selector('[class*="credit"], [class*="sesame"]')
            if credit_elem:
                credit_text = await credit_elem.inner_text()
                credit_match = re.search(r'(\d+)', credit_text)
                if credit_match:
                    seller_info['sesame_credit'] = int(credit_match.group(1))

            # 实名认证
            verified_elem = await self._page.query_selector('[class*="verified"]')
            if verified_elem:
                seller_info['real_name_verified'] = True

            # 好评率
            rate_elem = await self._page.query_selector('[class*="positive-rate"]')
            if rate_elem:
                rate_text = await rate_elem.inner_text()
                rate_match = re.search(r'(\d+(?:\.\d+)?)%', rate_text)
                if rate_match:
                    seller_info['positive_rate'] = float(rate_match.group(1))

            return seller_info if seller_info else None

        except Exception as e:
            self.logger.debug(f"解析卖家信息失败: {e}")
            return None

    # ========================================================================
    # 扩展功能方法 - 闲鱼特色
    # ========================================================================

    async def search_nearby(
        self,
        keyword: str,
        city: str,
        max_distance: float = 10.0,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """同城搜索 - 闲鱼特色功能

        Args:
            keyword: 搜索关键词
            city: 城市
            max_distance: 最大距离（公里）
            max_results: 最大结果数

        Returns:
            附近商品列表
        """
        try:
            self.logger.info(f"同城搜索: '{keyword}' 在 {city}")

            # 搜索商品
            results = await self.search(
                keyword=keyword,
                max_results=max_results,
                city=city,
                sort_by="distance"
            )

            # 按距离过滤
            filtered = self.matcher.filter_by_location(
                results,
                city=city,
                max_distance=max_distance
            )

            self.logger.info(f"找到 {len(filtered)} 个同城商品")
            return filtered

        except Exception as e:
            self.logger.error(f"同城搜索失败: {e}")
            return []

    async def get_fish_pond(self, pond_id: str) -> Dict[str, Any]:
        """获取鱼塘信息 - 闲鱼特色社区功能

        Args:
            pond_id: 鱼塘ID

        Returns:
            鱼塘信息
        """
        try:
            self.logger.info(f"获取鱼塘信息: {pond_id}")

            pond_url = f"{self.base_url}/pond/{pond_id}"
            if not await self._safe_navigate(pond_url):
                self.logger.error("无法导航到鱼塘页面")
                return {}

            pond = {
                'pond_id': pond_id,
                'platform': self.platform,
                'type': 'fish_pond',
                'pond_url': pond_url
            }

            # 鱼塘名称
            name_elem = await self._page.query_selector('[class*="pond-name"], .pond-title, h1')
            if name_elem:
                pond['pond_name'] = (await name_elem.inner_text()).strip()

            # 鱼塘描述
            desc_elem = await self._page.query_selector('[class*="pond-desc"], .description')
            if desc_elem:
                pond['description'] = (await desc_elem.inner_text()).strip()

            # 成员数
            member_elem = await self._page.query_selector('[class*="member"]')
            if member_elem:
                member_text = await member_elem.inner_text()
                pond['member_count'] = self.parser.parse_count(member_text)

            # 帖子数
            post_elem = await self._page.query_selector('[class*="post-count"]')
            if post_elem:
                post_text = await post_elem.inner_text()
                pond['post_count'] = self.parser.parse_count(post_text)

            # 分类
            category_elem = await self._page.query_selector('[class*="category"]')
            if category_elem:
                pond['category'] = (await category_elem.inner_text()).strip()

            # 位置
            location_elem = await self._page.query_selector('[class*="location"]')
            if location_elem:
                pond['location'] = (await location_elem.inner_text()).strip()

            self.logger.info(f"成功获取鱼塘信息: {pond.get('pond_name', pond_id)}")
            return pond

        except Exception as e:
            self.logger.error(f"获取鱼塘信息失败: {e}")
            return {}

    async def get_fish_pond_posts(
        self,
        pond_id: str,
        max_posts: int = 20
    ) -> List[Dict[str, Any]]:
        """获取鱼塘内的商品

        Args:
            pond_id: 鱼塘ID
            max_posts: 最大商品数

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"获取鱼塘商品: {pond_id}")

            pond_url = f"{self.base_url}/pond/{pond_id}"
            if not await self._safe_navigate(pond_url):
                return []

            # 滚动加载
            for _ in range(max_posts // 20):
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(2, 3))

            posts = []
            item_elements = await self._page.query_selector_all('.item, [class*="item"], [class*="product"]')

            for elem in item_elements[:max_posts]:
                try:
                    post = await self._parse_search_result(elem)
                    if post and post.get('id'):
                        post['fish_pond'] = pond_id
                        posts.append(post)
                except:
                    continue

            self.logger.info(f"获取到 {len(posts)} 个鱼塘商品")
            return posts

        except Exception as e:
            self.logger.error(f"获取鱼塘商品失败: {e}")
            return []

    async def search_by_condition(
        self,
        keyword: str,
        condition: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """按成色搜索 - 闲鱼特色

        Args:
            keyword: 搜索关键词
            condition: 成色 (全新/几乎全新/轻微使用/明显使用)
            max_results: 最大结果数

        Returns:
            商品列表
        """
        try:
            self.logger.info(f"按成色搜索: '{keyword}' - {condition}")

            # 搜索商品
            results = await self.search(
                keyword=keyword,
                max_results=max_results,
                condition=condition
            )

            # 按成色过滤
            filtered = self.matcher.filter_by_condition(results, [condition])

            self.logger.info(f"找到 {len(filtered)} 个符合成色的商品")
            return filtered

        except Exception as e:
            self.logger.error(f"按成色搜索失败: {e}")
            return []

    async def get_trusted_sellers(
        self,
        keyword: str,
        min_credit: int = 700,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索高信用卖家的商品

        Args:
            keyword: 搜索关键词
            min_credit: 最低芝麻信用分
            max_results: 最大结果数

        Returns:
            高信用卖家的商品列表
        """
        try:
            self.logger.info(f"搜索高信用卖家商品: '{keyword}' (信用>={min_credit})")

            # 搜索商品
            results = await self.search(keyword=keyword, max_results=max_results * 2)

            # 按芝麻信用过滤
            filtered = self.matcher.filter_by_sesame_credit(results, min_credit=min_credit)

            # 按信任度排序
            sorted_results = self.matcher.sort_products(filtered, sort_by="trust")

            return sorted_results[:max_results]

        except Exception as e:
            self.logger.error(f"搜索高信用卖家商品失败: {e}")
            return []

    async def compare_second_hand_products(
        self,
        item_ids: List[str]
    ) -> Dict[str, Any]:
        """比较多个二手商品

        Args:
            item_ids: 商品ID列表

        Returns:
            比较结果
        """
        try:
            self.logger.info(f"比较 {len(item_ids)} 个二手商品")

            comparison = {
                'products': [],
                'comparison_time': datetime.now().isoformat()
            }

            for item_id in item_ids:
                detail = await self.get_post_detail(item_id)
                if detail:
                    # 计算评分
                    detail['value_score'] = self.matcher.calculate_value_score(detail)
                    if detail.get('seller'):
                        detail['seller_trust_score'] = self.matcher.calculate_seller_trust_score(detail['seller'])
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

                # 最佳性价比
                comparison['products'].sort(
                    key=lambda p: p.get('value_score', 0),
                    reverse=True
                )
                comparison['best_value'] = comparison['products'][0].get('id')

                # 最可信卖家
                comparison['products'].sort(
                    key=lambda p: p.get('seller_trust_score', 0),
                    reverse=True
                )
                comparison['most_trusted_seller'] = comparison['products'][0].get('id')

            self.logger.info("商品比较完成")
            return comparison

        except Exception as e:
            self.logger.error(f"商品比较失败: {e}")
            return {}

    async def get_bargain_recommendations(
        self,
        keyword: str,
        max_price: float,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """获取性价比推荐 - 二手好货

        Args:
            keyword: 搜索关键词
            max_price: 最高价格
            max_results: 最大结果数

        Returns:
            性价比商品列表
        """
        try:
            self.logger.info(f"获取性价比推荐: '{keyword}' (价格<={max_price})")

            # 搜索商品
            results = await self.search(
                keyword=keyword,
                max_results=max_results * 3,
                max_price=max_price
            )

            # 计算性价比评分
            for product in results:
                product['value_score'] = self.matcher.calculate_value_score(product)

            # 按性价比排序
            sorted_results = self.matcher.sort_products(results, sort_by="value")

            return sorted_results[:max_results]

        except Exception as e:
            self.logger.error(f"获取性价比推荐失败: {e}")
            return []


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    async def test_xianyu_spider():
        """测试闲鱼爬虫功能"""
        spider = XianyuSpider(headless=False)

        async with spider.session():
            print("=" * 80)
            print("闲鱼爬虫 - 完整功能测试")
            print("=" * 80)

            # 测试1: 搜索二手商品
            print("\n[测试1] 搜索二手商品 - 同城优先")
            products = await spider.search(
                "iPhone",
                max_results=5,
                sort_by="distance",
                min_price=1000,
                max_price=5000,
                city="杭州"
            )

            for i, product in enumerate(products, 1):
                print(f"\n{i}. {product.get('title', 'N/A')[:60]}")
                print(f"   ID: {product.get('id')}")
                print(f"   价格: {product.get('price')}")
                print(f"   位置: {product.get('location')}")
                print(f"   成色: {product.get('condition')}")
                print(f"   卖家: {product.get('seller_name')}")

            # 测试2: 使用Matcher过滤
            if products:
                print("\n[测试2] 使用Matcher过滤商品")

                # 按成色过滤
                filtered = spider.matcher.filter_by_condition(products, ['全新', '几乎全新'])
                print(f"成色过滤: {len(products)} -> {len(filtered)} 个商品")

                # 计算性价比评分
                for product in filtered[:3]:
                    value_score = spider.matcher.calculate_value_score(product)
                    print(f"\n{product.get('title', 'N/A')[:50]}")
                    print(f"  性价比评分: {value_score}/100")

            # 测试3: 获取商品详情
            if products:
                print("\n[测试3] 获取商品详情")
                first_id = products[0].get('id')
                if first_id:
                    detail = await spider.get_post_detail(first_id)
                    print(f"\n商品: {detail.get('title', 'N/A')[:60]}")
                    print(f"价格: {detail.get('price')}")
                    print(f"原价: {detail.get('original_price')}")
                    print(f"成色: {detail.get('condition')}")
                    print(f"成色描述: {detail.get('condition_description', 'N/A')[:50]}")
                    print(f"位置: {detail.get('location')}")
                    print(f"交易方式: {detail.get('trade_type')}")
                    print(f"包邮: {'是' if detail.get('free_shipping') else '否'}")
                    print(f"图片数量: {len(detail.get('images', []))}")
                    print(f"想要人数: {detail.get('want_count')}")
                    print(f"鱼塘: {detail.get('fish_pond', 'N/A')}")

                    # 卖家信息
                    seller = detail.get('seller', {})
                    if seller:
                        print(f"\n卖家信息:")
                        print(f"  用户名: {seller.get('username')}")
                        print(f"  芝麻信用: {seller.get('sesame_credit')}")
                        print(f"  实名认证: {'是' if seller.get('real_name_verified') else '否'}")
                        print(f"  好评率: {seller.get('positive_rate')}%")

            # 测试4: 同城搜索
            print("\n[测试4] 同城搜索")
            nearby = await spider.search_nearby(
                keyword="笔记本",
                city="杭州",
                max_distance=10.0,
                max_results=3
            )
            for i, item in enumerate(nearby, 1):
                print(f"\n{i}. {item.get('title', 'N/A')[:50]}")
                print(f"   价格: {item.get('price')}")
                print(f"   位置: {item.get('location')}")
                print(f"   距离: {item.get('distance_text', 'N/A')}")

            # 测试5: 性价比推荐
            print("\n[测试5] 性价比推荐")
            bargains = await spider.get_bargain_recommendations(
                keyword="iPad",
                max_price=3000,
                max_results=3
            )
            for i, item in enumerate(bargains, 1):
                print(f"\n{i}. {item.get('title', 'N/A')[:50]}")
                print(f"   价格: {item.get('price')}")
                print(f"   性价比评分: {item.get('value_score', 0)}/100")
                print(f"   成色: {item.get('condition', 'N/A')}")

            print("\n" + "=" * 80)
            print("测试完成!")
            print("=" * 80)

    asyncio.run(test_xianyu_spider())

