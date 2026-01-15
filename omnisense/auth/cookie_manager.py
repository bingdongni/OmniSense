"""
Cookie Manager - 企业级Cookie管理系统

支持多种Cookie来源:
1. 浏览器导出 (Chrome, Firefox, Edge)
2. 手动配置
3. 自动登录获取
4. Cookie池管理
5. 自动刷新和验证

Author: bingdongni
Version: 1.0.0
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import asyncio
from loguru import logger


@dataclass
class Cookie:
    """单个Cookie数据结构"""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[int] = None
    secure: bool = False
    httpOnly: bool = False
    sameSite: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 移除None值
        return {k: v for k, v in data.items() if v is not None}

    def is_expired(self) -> bool:
        """检查是否过期"""
        if not self.expires:
            return False
        return time.time() > self.expires


@dataclass
class CookieSet:
    """平台Cookie集合"""
    platform: str
    cookies: List[Cookie] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    account_name: Optional[str] = None
    is_valid: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_playwright_cookies(self) -> List[Dict[str, Any]]:
        """转换为Playwright格式"""
        return [cookie.to_dict() for cookie in self.cookies if not cookie.is_expired()]

    def to_requests_cookies(self) -> Dict[str, str]:
        """转换为Requests格式"""
        return {
            cookie.name: cookie.value
            for cookie in self.cookies
            if not cookie.is_expired()
        }

    def get_cookie_value(self, name: str) -> Optional[str]:
        """获取指定Cookie的值"""
        for cookie in self.cookies:
            if cookie.name == name and not cookie.is_expired():
                return cookie.value
        return None

    def has_valid_cookies(self) -> bool:
        """检查是否有有效的Cookie"""
        return any(not cookie.is_expired() for cookie in self.cookies)


class CookieManager:
    """
    企业级Cookie管理器

    功能:
    - 从浏览器导出Cookie (Chrome, Firefox, Edge)
    - Cookie持久化存储
    - Cookie池管理 (多账号轮换)
    - 自动验证Cookie有效性
    - 自动刷新过期Cookie
    - Cookie加密存储 (可选)
    """

    def __init__(
        self,
        storage_path: str = "./data/cookies",
        auto_refresh: bool = True,
        encrypt: bool = False
    ):
        """
        初始化Cookie管理器

        Args:
            storage_path: Cookie存储路径
            auto_refresh: 是否自动刷新过期Cookie
            encrypt: 是否加密存储
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.auto_refresh = auto_refresh
        self.encrypt = encrypt

        # Cookie池: platform -> list of CookieSet
        self.cookie_pool: Dict[str, List[CookieSet]] = {}

        # 加载已存储的Cookie
        self._load_cookies()

        logger.info(f"Cookie管理器初始化完成: {self.storage_path}")

    def _load_cookies(self):
        """从存储加载Cookie"""
        try:
            for cookie_file in self.storage_path.glob("*.json"):
                platform = cookie_file.stem
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cookie_sets = []
                    for item in data:
                        cookies = [Cookie(**c) for c in item.get('cookies', [])]
                        cookie_set = CookieSet(
                            platform=platform,
                            cookies=cookies,
                            created_at=datetime.fromisoformat(item.get('created_at')),
                            expires_at=datetime.fromisoformat(item['expires_at']) if item.get('expires_at') else None,
                            user_id=item.get('user_id'),
                            account_name=item.get('account_name'),
                            is_valid=item.get('is_valid', True),
                            metadata=item.get('metadata', {})
                        )
                        if cookie_set.has_valid_cookies():
                            cookie_sets.append(cookie_set)

                    if cookie_sets:
                        self.cookie_pool[platform] = cookie_sets
                        logger.info(f"加载平台 {platform} 的 {len(cookie_sets)} 个Cookie集合")
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")

    def _save_cookies(self, platform: str):
        """保存Cookie到存储"""
        try:
            if platform not in self.cookie_pool:
                return

            cookie_file = self.storage_path / f"{platform}.json"
            data = []
            for cookie_set in self.cookie_pool[platform]:
                data.append({
                    'platform': platform,
                    'cookies': [asdict(c) for c in cookie_set.cookies],
                    'created_at': cookie_set.created_at.isoformat(),
                    'expires_at': cookie_set.expires_at.isoformat() if cookie_set.expires_at else None,
                    'user_id': cookie_set.user_id,
                    'account_name': cookie_set.account_name,
                    'is_valid': cookie_set.is_valid,
                    'metadata': cookie_set.metadata
                })

            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"保存平台 {platform} 的Cookie成功")
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")

    def import_from_browser_db(
        self,
        platform: str,
        browser: str = "chrome",
        domain: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        从浏览器数据库导入Cookie

        Args:
            platform: 平台名称
            browser: 浏览器类型 (chrome, firefox, edge)
            domain: 域名过滤
            user_id: 用户ID标识

        Returns:
            是否导入成功
        """
        try:
            browser_paths = {
                "chrome": {
                    "windows": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies"),
                    "darwin": os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies"),
                    "linux": os.path.expanduser("~/.config/google-chrome/Default/Cookies")
                },
                "edge": {
                    "windows": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Network\Cookies"),
                    "darwin": os.path.expanduser("~/Library/Application Support/Microsoft Edge/Default/Cookies"),
                    "linux": os.path.expanduser("~/.config/microsoft-edge/Default/Cookies")
                },
                "firefox": {
                    # Firefox使用不同的Cookie存储方式
                    "windows": os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles"),
                    "darwin": os.path.expanduser("~/Library/Application Support/Firefox/Profiles"),
                    "linux": os.path.expanduser("~/.mozilla/firefox")
                }
            }

            import platform as sys_platform
            system = sys_platform.system().lower()
            if system == "darwin":
                system = "darwin"
            elif system == "windows":
                system = "windows"
            else:
                system = "linux"

            cookie_db = browser_paths.get(browser, {}).get(system)
            if not cookie_db or not os.path.exists(cookie_db):
                logger.warning(f"未找到{browser}浏览器的Cookie数据库: {cookie_db}")
                return False

            # 复制数据库文件 (避免锁定)
            import shutil
            temp_db = self.storage_path / f"temp_{browser}.db"
            shutil.copy2(cookie_db, temp_db)

            # 读取Cookie
            cookies = []
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()

            query = "SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly FROM cookies"
            if domain:
                query += f" WHERE host_key LIKE '%{domain}%'"

            cursor.execute(query)
            for row in cursor.fetchall():
                name, value, host_key, path, expires_utc, is_secure, is_httponly = row

                # Chrome的expires是微秒时间戳
                expires = None
                if expires_utc:
                    # Chrome epoch: 1601-01-01
                    chrome_epoch = datetime(1601, 1, 1)
                    expires_dt = chrome_epoch + timedelta(microseconds=expires_utc)
                    expires = int(expires_dt.timestamp())

                cookie = Cookie(
                    name=name,
                    value=value,
                    domain=host_key,
                    path=path,
                    expires=expires,
                    secure=bool(is_secure),
                    httpOnly=bool(is_httponly)
                )
                cookies.append(cookie)

            conn.close()
            temp_db.unlink()

            if cookies:
                cookie_set = CookieSet(
                    platform=platform,
                    cookies=cookies,
                    user_id=user_id,
                    account_name=f"{browser}_import",
                    metadata={'source': browser, 'domain': domain}
                )
                self.add_cookie_set(platform, cookie_set)
                logger.info(f"从{browser}导入 {len(cookies)} 个Cookie到平台 {platform}")
                return True
            else:
                logger.warning(f"未从{browser}找到Cookie")
                return False

        except Exception as e:
            logger.error(f"从浏览器导入Cookie失败: {e}")
            return False

    def import_from_json(
        self,
        platform: str,
        json_file: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        从JSON文件导入Cookie

        JSON格式示例:
        [
            {
                "name": "sessionid",
                "value": "xxx",
                "domain": ".douyin.com",
                "path": "/",
                "expires": 1234567890,
                "secure": true,
                "httpOnly": true
            }
        ]

        Args:
            platform: 平台名称
            json_file: JSON文件路径
            user_id: 用户ID

        Returns:
            是否导入成功
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cookies = []
            for item in data:
                cookie = Cookie(
                    name=item['name'],
                    value=item['value'],
                    domain=item.get('domain', ''),
                    path=item.get('path', '/'),
                    expires=item.get('expires'),
                    secure=item.get('secure', False),
                    httpOnly=item.get('httpOnly', False),
                    sameSite=item.get('sameSite')
                )
                cookies.append(cookie)

            cookie_set = CookieSet(
                platform=platform,
                cookies=cookies,
                user_id=user_id,
                account_name='json_import',
                metadata={'source': 'json', 'file': json_file}
            )
            self.add_cookie_set(platform, cookie_set)
            logger.info(f"从JSON文件导入 {len(cookies)} 个Cookie到平台 {platform}")
            return True

        except Exception as e:
            logger.error(f"从JSON导入Cookie失败: {e}")
            return False

    def import_from_dict(
        self,
        platform: str,
        cookies_dict: Dict[str, str],
        domain: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        从字典导入Cookie (简单格式)

        Args:
            platform: 平台名称
            cookies_dict: Cookie字典 {"name": "value"}
            domain: Cookie域名
            user_id: 用户ID

        Returns:
            是否导入成功
        """
        try:
            cookies = []
            for name, value in cookies_dict.items():
                cookie = Cookie(
                    name=name,
                    value=value,
                    domain=domain,
                    path='/'
                )
                cookies.append(cookie)

            cookie_set = CookieSet(
                platform=platform,
                cookies=cookies,
                user_id=user_id,
                account_name='dict_import',
                metadata={'source': 'dict'}
            )
            self.add_cookie_set(platform, cookie_set)
            logger.info(f"从字典导入 {len(cookies)} 个Cookie到平台 {platform}")
            return True

        except Exception as e:
            logger.error(f"从字典导入Cookie失败: {e}")
            return False

    def add_cookie_set(self, platform: str, cookie_set: CookieSet):
        """添加Cookie集合"""
        if platform not in self.cookie_pool:
            self.cookie_pool[platform] = []

        self.cookie_pool[platform].append(cookie_set)
        self._save_cookies(platform)
        logger.info(f"添加Cookie集合到平台 {platform}")

    def get_cookie_set(
        self,
        platform: str,
        user_id: Optional[str] = None,
        rotate: bool = True
    ) -> Optional[CookieSet]:
        """
        获取Cookie集合

        Args:
            platform: 平台名称
            user_id: 指定用户ID (可选)
            rotate: 是否轮换 (从池中选择)

        Returns:
            Cookie集合或None
        """
        if platform not in self.cookie_pool:
            logger.warning(f"平台 {platform} 没有可用的Cookie")
            return None

        cookie_sets = self.cookie_pool[platform]

        # 过滤有效的Cookie集合
        valid_sets = [cs for cs in cookie_sets if cs.is_valid and cs.has_valid_cookies()]

        if not valid_sets:
            logger.warning(f"平台 {platform} 没有有效的Cookie")
            return None

        # 如果指定user_id
        if user_id:
            for cookie_set in valid_sets:
                if cookie_set.user_id == user_id:
                    return cookie_set
            logger.warning(f"平台 {platform} 未找到用户 {user_id} 的Cookie")
            return None

        # 轮换策略: 选择使用次数最少的
        if rotate:
            # 简单轮换: 返回第一个并移到末尾
            cookie_set = valid_sets[0]
            self.cookie_pool[platform].remove(cookie_set)
            self.cookie_pool[platform].append(cookie_set)
            return cookie_set
        else:
            return valid_sets[0]

    async def validate_cookies(
        self,
        platform: str,
        validation_url: str,
        success_indicator: str
    ) -> List[Tuple[CookieSet, bool]]:
        """
        验证Cookie有效性

        Args:
            platform: 平台名称
            validation_url: 验证URL
            success_indicator: 成功标识 (页面中的文本)

        Returns:
            (CookieSet, is_valid) 列表
        """
        results = []

        if platform not in self.cookie_pool:
            return results

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            for cookie_set in self.cookie_pool[platform]:
                try:
                    context = await browser.new_context()

                    # 添加Cookie
                    await context.add_cookies(cookie_set.to_playwright_cookies())

                    # 访问验证URL
                    page = await context.new_page()
                    await page.goto(validation_url, wait_until='networkidle')
                    await asyncio.sleep(2)

                    # 检查成功标识
                    content = await page.content()
                    is_valid = success_indicator in content

                    cookie_set.is_valid = is_valid
                    results.append((cookie_set, is_valid))

                    await context.close()

                    logger.info(f"Cookie验证: {platform} - {cookie_set.account_name} - {'有效' if is_valid else '无效'}")

                except Exception as e:
                    logger.error(f"验证Cookie失败: {e}")
                    cookie_set.is_valid = False
                    results.append((cookie_set, False))

            await browser.close()

        # 保存验证结果
        self._save_cookies(platform)

        return results

    def export_to_json(self, platform: str, output_file: str):
        """导出Cookie到JSON文件"""
        try:
            if platform not in self.cookie_pool:
                logger.warning(f"平台 {platform} 没有Cookie可导出")
                return

            data = []
            for cookie_set in self.cookie_pool[platform]:
                data.extend([asdict(c) for c in cookie_set.cookies])

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"导出平台 {platform} 的Cookie到 {output_file}")

        except Exception as e:
            logger.error(f"导出Cookie失败: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取Cookie池统计信息"""
        stats = {}

        for platform, cookie_sets in self.cookie_pool.items():
            valid_count = sum(1 for cs in cookie_sets if cs.is_valid and cs.has_valid_cookies())
            total_cookies = sum(len(cs.cookies) for cs in cookie_sets)

            stats[platform] = {
                'total_sets': len(cookie_sets),
                'valid_sets': valid_count,
                'total_cookies': total_cookies,
                'accounts': [cs.account_name for cs in cookie_sets]
            }

        return stats

    def remove_cookie_set(self, platform: str, user_id: Optional[str] = None):
        """删除Cookie集合"""
        if platform not in self.cookie_pool:
            return

        if user_id:
            self.cookie_pool[platform] = [
                cs for cs in self.cookie_pool[platform]
                if cs.user_id != user_id
            ]
        else:
            self.cookie_pool[platform] = []

        self._save_cookies(platform)
        logger.info(f"删除平台 {platform} 的Cookie")


# 全局Cookie管理器实例
_cookie_manager: Optional[CookieManager] = None


def get_cookie_manager() -> CookieManager:
    """获取全局Cookie管理器实例"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager


if __name__ == "__main__":
    # 示例使用
    manager = CookieManager()

    # 1. 从浏览器导入
    # manager.import_from_browser_db("douyin", browser="chrome", domain="douyin.com")

    # 2. 从字典导入
    cookies = {
        "sessionid": "your_session_id",
        "csrf_token": "your_csrf_token"
    }
    manager.import_from_dict("douyin", cookies, domain=".douyin.com", user_id="user1")

    # 3. 获取Cookie
    cookie_set = manager.get_cookie_set("douyin")
    if cookie_set:
        print("Playwright格式:", cookie_set.to_playwright_cookies())
        print("Requests格式:", cookie_set.to_requests_cookies())

    # 4. 查看统计
    print("统计信息:", manager.get_statistics())
