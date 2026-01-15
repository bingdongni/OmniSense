"""
API Client Manager - 企业级官方API集成框架

支持多平台官方API:
- 自动认证和Token管理
- 速率限制和配额管理
- 请求重试和错误处理
- API响应缓存
- 多账号API密钥池

Author: bingdongni
Version: 1.0.0
"""

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import aiohttp
from loguru import logger


class AuthType(Enum):
    """API认证类型"""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    CUSTOM = "custom"


@dataclass
class APICredential:
    """API凭证"""
    platform: str
    auth_type: AuthType
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    account_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查Token是否过期"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def is_valid(self) -> bool:
        """检查凭证是否有效"""
        if self.is_expired():
            return False

        if self.auth_type == AuthType.API_KEY:
            return bool(self.api_key)
        elif self.auth_type == AuthType.OAUTH2:
            return bool(self.access_token)
        elif self.auth_type == AuthType.JWT:
            return bool(self.access_token)
        elif self.auth_type == AuthType.BEARER_TOKEN:
            return bool(self.access_token)
        elif self.auth_type == AuthType.BASIC_AUTH:
            return bool(self.api_key and self.api_secret)

        return False


@dataclass
class RateLimitInfo:
    """速率限制信息"""
    max_requests: int  # 最大请求数
    time_window: int  # 时间窗口(秒)
    remaining: int  # 剩余请求数
    reset_at: datetime  # 重置时间
    used_requests: int = 0  # 已使用请求数

    def can_request(self) -> bool:
        """是否可以发起请求"""
        # 检查是否需要重置
        if datetime.now() >= self.reset_at:
            self.remaining = self.max_requests
            self.used_requests = 0
            self.reset_at = datetime.now() + timedelta(seconds=self.time_window)
            return True

        return self.remaining > 0

    def consume(self):
        """消耗一次请求配额"""
        self.remaining = max(0, self.remaining - 1)
        self.used_requests += 1

    def wait_time(self) -> float:
        """需要等待的时间(秒)"""
        if self.can_request():
            return 0.0
        return (self.reset_at - datetime.now()).total_seconds()


class BaseAPIClient(ABC):
    """
    API客户端基类

    所有平台API客户端都继承此类
    """

    def __init__(
        self,
        credential: APICredential,
        base_url: str,
        rate_limit: Optional[RateLimitInfo] = None
    ):
        """
        初始化API客户端

        Args:
            credential: API凭证
            base_url: API基础URL
            rate_limit: 速率限制信息
        """
        self.credential = credential
        self.base_url = base_url.rstrip('/')
        self.rate_limit = rate_limit
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"初始化API客户端: {credential.platform}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def initialize(self):
        """初始化会话"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """
        获取认证请求头

        Returns:
            认证请求头字典
        """
        pass

    @abstractmethod
    async def refresh_token(self) -> bool:
        """
        刷新访问Token

        Returns:
            是否刷新成功
        """
        pass

    async def _wait_for_rate_limit(self):
        """等待速率限制"""
        if not self.rate_limit:
            return

        if not self.rate_limit.can_request():
            wait_time = self.rate_limit.wait_time()
            logger.warning(f"速率限制，等待 {wait_time:.1f} 秒")
            await asyncio.sleep(wait_time)

        self.rate_limit.consume()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retry: int = 3
    ) -> Dict[str, Any]:
        """
        发起API请求

        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            data: Form数据
            json: JSON数据
            headers: 额外请求头
            retry: 重试次数

        Returns:
            响应数据

        Raises:
            Exception: 请求失败
        """
        if not self.session:
            await self.initialize()

        # 检查凭证有效性
        if not self.credential.is_valid():
            logger.warning("API凭证无效或已过期，尝试刷新")
            if not await self.refresh_token():
                raise Exception("API凭证无效且刷新失败")

        # 等待速率限制
        await self._wait_for_rate_limit()

        # 构建URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # 合并请求头
        req_headers = self.get_auth_headers()
        if headers:
            req_headers.update(headers)

        # 请求重试
        last_error = None
        for attempt in range(retry):
            try:
                logger.debug(f"API请求: {method} {url}")

                async with self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=req_headers
                ) as response:
                    # 检查响应状态
                    if response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"API速率限制，等待 {retry_after} 秒")
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status == 401:  # Unauthorized
                        logger.warning("API认证失败，尝试刷新Token")
                        if await self.refresh_token():
                            continue
                        else:
                            raise Exception("API认证失败且刷新Token失败")

                    response.raise_for_status()

                    # 解析响应
                    result = await response.json()
                    logger.debug(f"API响应成功: {endpoint}")
                    return result

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"API请求失败 (尝试 {attempt + 1}/{retry}): {e}")
                if attempt < retry - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避

        raise Exception(f"API请求失败: {last_error}")

    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict:
        """GET请求"""
        return await self.request("GET", endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> Dict:
        """POST请求"""
        return await self.request("POST", endpoint, data=data, json=json, **kwargs)

    async def put(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None, **kwargs) -> Dict:
        """PUT请求"""
        return await self.request("PUT", endpoint, data=data, json=json, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> Dict:
        """DELETE请求"""
        return await self.request("DELETE", endpoint, **kwargs)

    @abstractmethod
    async def search(self, keyword: str, **kwargs) -> List[Dict[str, Any]]:
        """
        搜索内容 (平台特定实现)

        Args:
            keyword: 搜索关键词
            **kwargs: 其他参数

        Returns:
            搜索结果列表
        """
        pass

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户信息 (平台特定实现)

        Args:
            user_id: 用户ID

        Returns:
            用户信息
        """
        pass

    @abstractmethod
    async def get_user_posts(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取用户发布内容 (平台特定实现)

        Args:
            user_id: 用户ID
            limit: 数量限制

        Returns:
            内容列表
        """
        pass


class APIClientManager:
    """
    API客户端管理器

    功能:
    - 管理多平台API客户端
    - API凭证池管理
    - 自动选择可用凭证
    - 统计API使用情况
    """

    def __init__(self, config_path: str = "./data/api_config.json"):
        """
        初始化API客户端管理器

        Args:
            config_path: API配置文件路径
        """
        self.config_path = config_path
        self.clients: Dict[str, List[BaseAPIClient]] = {}
        self.credentials: Dict[str, List[APICredential]] = {}

        logger.info("API客户端管理器初始化完成")

    def add_credential(self, credential: APICredential):
        """
        添加API凭证

        Args:
            credential: API凭证
        """
        platform = credential.platform
        if platform not in self.credentials:
            self.credentials[platform] = []

        self.credentials[platform].append(credential)
        logger.info(f"添加API凭证: {platform} - {credential.account_name}")

    def get_credential(
        self,
        platform: str,
        user_id: Optional[str] = None
    ) -> Optional[APICredential]:
        """
        获取API凭证

        Args:
            platform: 平台名称
            user_id: 指定用户ID

        Returns:
            API凭证或None
        """
        if platform not in self.credentials:
            logger.warning(f"平台 {platform} 没有可用的API凭证")
            return None

        creds = self.credentials[platform]

        # 过滤有效凭证
        valid_creds = [c for c in creds if c.is_valid()]

        if not valid_creds:
            logger.warning(f"平台 {platform} 没有有效的API凭证")
            return None

        # 如果指定user_id
        if user_id:
            for cred in valid_creds:
                if cred.user_id == user_id:
                    return cred

        # 轮换策略: 返回第一个
        return valid_creds[0]

    def get_client(
        self,
        platform: str,
        client_class: type,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Optional[BaseAPIClient]:
        """
        获取API客户端

        Args:
            platform: 平台名称
            client_class: 客户端类
            user_id: 指定用户ID
            **kwargs: 其他参数

        Returns:
            API客户端或None
        """
        credential = self.get_credential(platform, user_id)
        if not credential:
            return None

        try:
            client = client_class(credential=credential, **kwargs)
            return client
        except Exception as e:
            logger.error(f"创建API客户端失败: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取API使用统计"""
        stats = {}

        for platform, creds in self.credentials.items():
            valid_count = sum(1 for c in creds if c.is_valid())

            stats[platform] = {
                'total_credentials': len(creds),
                'valid_credentials': valid_count,
                'accounts': [c.account_name for c in creds]
            }

        return stats


# 全局API管理器实例
_api_manager: Optional[APIClientManager] = None


def get_api_manager() -> APIClientManager:
    """获取全局API管理器实例"""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIClientManager()
    return _api_manager
