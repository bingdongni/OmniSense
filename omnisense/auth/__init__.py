"""
Authentication Module

企业级认证和授权管理模块:
- Cookie管理
- API客户端管理
- OAuth2集成
- Token管理

Author: bingdongni
Version: 1.0.0
"""

from omnisense.auth.cookie_manager import (
    Cookie,
    CookieSet,
    CookieManager,
    get_cookie_manager
)

from omnisense.auth.api_client import (
    AuthType,
    APICredential,
    RateLimitInfo,
    BaseAPIClient,
    APIClientManager,
    get_api_manager
)

__all__ = [
    # Cookie相关
    'Cookie',
    'CookieSet',
    'CookieManager',
    'get_cookie_manager',

    # API相关
    'AuthType',
    'APICredential',
    'RateLimitInfo',
    'BaseAPIClient',
    'APIClientManager',
    'get_api_manager',
]
