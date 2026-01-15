"""
GitHub Spider Implementation
完整的GitHub平台爬虫实现，包含四层架构：
1. Spider Layer: 数据爬取层 - 仓库搜索、用户信息、代码搜索、Trending、Issue/PR
2. Anti-Crawl Layer: 反反爬层 - API速率限制、Token轮换、GraphQL、请求重试
3. Matcher Layer: 智能匹配层 - 语言匹配、Stars过滤、主题标签、许可证、活跃度
4. Interaction Layer: 互动处理层 - Star/Fork/Watch、Issue/PR评论、Code Review
"""

import asyncio
import hashlib
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode, urlparse, parse_qs
from collections import deque
from enum import Enum

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from omnisense.config import config
from omnisense.spider.base import BaseSpider
from omnisense.utils.logger import get_logger

logger = get_logger(__name__)


class APIVersion(Enum):
    """GitHub API版本"""
    REST_V3 = "v3"
    GRAPHQL_V4 = "v4"


class RateLimitError(Exception):
    """速率限制异常"""
    pass


class GitHubAntiCrawl:
    """
    GitHub反反爬处理器
    Layer 2: Anti-Crawl - API速率限制、Token轮换、请求重试、指数退避
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

        # Token池
        self._tokens: deque = deque()
        self._current_token: Optional[str] = None
        self._token_rate_limits: Dict[str, Dict[str, Any]] = {}

        # 速率限制
        self._rate_limit_remaining = 5000
        self._rate_limit_reset = None
        self._requests_count = 0
        self._last_request_time = None

        # 重试配置
        self._max_retries = 3
        self._base_retry_delay = 1.0
        self._max_retry_delay = 60.0

        # User-Agent池
        self._user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]

    def add_token(self, token: str) -> None:
        """添加GitHub Token到池中"""
        if token and token not in self._tokens:
            self._tokens.append(token)
            self._token_rate_limits[token] = {
                'remaining': 5000,
                'reset': None,
                'limit': 5000
            }
            self.logger.info(f"Added token to pool (total: {len(self._tokens)})")

    def add_tokens(self, tokens: List[str]) -> None:
        """批量添加Token"""
        for token in tokens:
            self.add_token(token)

    def get_current_token(self) -> Optional[str]:
        """获取当前可用的Token"""
        if not self._tokens:
            return None

        # 如果当前token可用，继续使用
        if self._current_token and self._is_token_available(self._current_token):
            return self._current_token

        # 轮换到下一个可用token
        for _ in range(len(self._tokens)):
            token = self._tokens[0]
            self._tokens.rotate(-1)  # 轮换

            if self._is_token_available(token):
                self._current_token = token
                self.logger.debug(f"Rotated to token: {token[:8]}...")
                return token

        # 所有token都不可用
        self._current_token = None
        return None

    def _is_token_available(self, token: str) -> bool:
        """检查Token是否可用"""
        if token not in self._token_rate_limits:
            return True

        info = self._token_rate_limits[token]

        # 检查是否还有剩余配额
        if info['remaining'] > 100:  # 保留一些buffer
            return True

        # 检查是否已经重置
        if info['reset']:
            reset_time = datetime.fromtimestamp(info['reset'])
            if datetime.now() > reset_time:
                info['remaining'] = info['limit']
                return True

        return False

    def update_rate_limit(self, token: str, remaining: int, reset_timestamp: int, limit: int = 5000) -> None:
        """更新Token的速率限制信息"""
        if token not in self._token_rate_limits:
            self._token_rate_limits[token] = {}

        self._token_rate_limits[token].update({
            'remaining': remaining,
            'reset': reset_timestamp,
            'limit': limit
        })

        self._rate_limit_remaining = remaining
        self._rate_limit_reset = reset_timestamp

        self.logger.debug(
            f"Rate limit updated - Remaining: {remaining}/{limit}, "
            f"Reset: {datetime.fromtimestamp(reset_timestamp).strftime('%H:%M:%S')}"
        )

    async def wait_for_rate_limit(self) -> None:
        """等待速率限制重置"""
        if self._rate_limit_remaining > 0:
            return

        if self._rate_limit_reset:
            reset_time = datetime.fromtimestamp(self._rate_limit_reset)
            wait_seconds = (reset_time - datetime.now()).total_seconds()

            if wait_seconds > 0:
                self.logger.warning(
                    f"Rate limit exceeded. Waiting {wait_seconds:.0f} seconds until reset..."
                )
                await asyncio.sleep(wait_seconds + 1)

    async def request_with_retry(
        self,
        request_func,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        带重试的请求包装器

        Args:
            request_func: 请求函数
            max_retries: 最大重试次数
            *args, **kwargs: 传递给请求函数的参数

        Returns:
            请求结果
        """
        max_retries = max_retries or self._max_retries
        last_exception = None

        for attempt in range(max_retries):
            try:
                # 速率限制检查
                await self.wait_for_rate_limit()

                # 请求延迟（避免过于频繁）
                await self._apply_request_delay()

                # 执行请求
                result = await request_func(*args, **kwargs)

                self._requests_count += 1
                self._last_request_time = time.time()

                return result

            except RateLimitError as e:
                last_exception = e
                self.logger.warning(f"Rate limit hit on attempt {attempt + 1}")

                # 尝试轮换token
                next_token = self.get_current_token()
                if not next_token:
                    # 没有可用token，等待重置
                    await self.wait_for_rate_limit()

            except Exception as e:
                last_exception = e

                # 计算退避延迟
                delay = self._calculate_backoff_delay(attempt)

                self.logger.warning(
                    f"Request failed on attempt {attempt + 1}/{max_retries}: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                await asyncio.sleep(delay)

        # 所有重试都失败
        raise last_exception or Exception("Request failed after all retries")

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """计算指数退避延迟"""
        delay = self._base_retry_delay * (2 ** attempt)
        # 添加随机抖动
        jitter = random.uniform(0, 0.3 * delay)
        total_delay = min(delay + jitter, self._max_retry_delay)
        return total_delay

    async def _apply_request_delay(self) -> None:
        """应用请求延迟（避免过于频繁）"""
        if self._last_request_time:
            elapsed = time.time() - self._last_request_time
            min_delay = 0.1  # 最小100ms间隔

            if elapsed < min_delay:
                await asyncio.sleep(min_delay - elapsed)

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self._user_agents)

    async def initialize(self, page: Page) -> None:
        """初始化反爬措施"""
        await self._inject_webdriver_evasion(page)

    async def _inject_webdriver_evasion(self, page: Page) -> None:
        """注入反webdriver检测"""
        evasion_script = """
        // Remove webdriver property
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
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'zh-CN']
        });
        """
        await page.add_init_script(evasion_script)


class GitHubMatcher:
    """
    GitHub内容匹配器
    Layer 3: Matcher - 语言匹配、Stars过滤、主题标签、许可证、活跃度
    """

    def __init__(self):
        self.logger = logger

    async def match_repository(
        self,
        repo: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        匹配仓库

        Args:
            repo: 仓库数据
            criteria: 匹配条件

        Returns:
            (is_match, match_score)
        """
        if not criteria:
            return True, 1.0

        score = 0.0
        weights = {
            'language': 0.25,
            'stars': 0.20,
            'topics': 0.20,
            'activity': 0.20,
            'license': 0.15
        }

        # 语言匹配
        if 'languages' in criteria:
            required_langs = criteria['languages']
            if isinstance(required_langs, str):
                required_langs = [required_langs]

            repo_lang = repo.get('language', '').lower()
            if any(lang.lower() == repo_lang for lang in required_langs):
                score += weights['language']

        # Stars过滤和评分
        stars = repo.get('stars', 0)

        if 'min_stars' in criteria:
            if stars < criteria['min_stars']:
                return False, 0.0

        if 'max_stars' in criteria:
            if stars > criteria['max_stars']:
                return False, 0.0

        # Stars评分（对数尺度）
        if 'stars_weight' in criteria and stars > 0:
            import math
            stars_score = min(math.log10(stars + 1) / 5, 1.0)  # 最大10^5
            score += stars_score * weights['stars']

        # Forks过滤
        if 'min_forks' in criteria:
            if repo.get('forks', 0) < criteria['min_forks']:
                return False, 0.0

        # 主题标签匹配
        if 'topics' in criteria:
            required_topics = criteria['topics']
            if isinstance(required_topics, str):
                required_topics = [required_topics]

            repo_topics = [t.lower() for t in repo.get('topics', [])]
            topic_matches = sum(1 for topic in required_topics if topic.lower() in repo_topics)

            if topic_matches > 0:
                score += (topic_matches / len(required_topics)) * weights['topics']

        # 许可证过滤
        if 'licenses' in criteria:
            allowed_licenses = criteria['licenses']
            if isinstance(allowed_licenses, str):
                allowed_licenses = [allowed_licenses]

            repo_license = repo.get('license', '').lower()

            if not any(lic.lower() in repo_license for lic in allowed_licenses):
                return False, 0.0
            else:
                score += weights['license']

        # 活跃度评估
        if criteria.get('check_activity', False):
            activity_score = self._evaluate_activity(repo)
            score += activity_score * weights['activity']

        # 更新时间过滤
        if 'updated_after' in criteria:
            updated_at = repo.get('updated_at')
            if updated_at:
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

                min_date = criteria['updated_after']
                if isinstance(min_date, str):
                    min_date = datetime.fromisoformat(min_date)

                if updated_at < min_date:
                    return False, 0.0

        # 归一化分数
        total_weight = sum(weights.values())
        normalized_score = score / total_weight if total_weight > 0 else 0.0

        # 匹配阈值
        threshold = criteria.get('match_threshold', 0.3)
        is_match = normalized_score >= threshold

        return is_match, normalized_score

    def _evaluate_activity(self, repo: Dict[str, Any]) -> float:
        """评估仓库活跃度"""
        score = 0.0

        # 最近更新时间
        updated_at = repo.get('updated_at')
        if updated_at:
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

            days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days

            if days_since_update < 7:
                score += 0.5
            elif days_since_update < 30:
                score += 0.3
            elif days_since_update < 90:
                score += 0.1

        # Issues和PR数量
        open_issues = repo.get('open_issues', 0)
        if open_issues > 0:
            score += 0.3

        # Commits数量
        commits = repo.get('commits_count', 0)
        if commits > 100:
            score += 0.2
        elif commits > 10:
            score += 0.1

        return min(score, 1.0)


class GitHubInteraction:
    """
    GitHub互动处理器
    Layer 4: Interaction - Star/Fork/Watch、Issue/PR评论、Code Review
    """

    def __init__(self, spider):
        self.spider = spider
        self.logger = logger

    async def star_repository(self, page: Page, owner: str, repo: str) -> bool:
        """
        Star仓库

        Args:
            page: Playwright页面对象
            owner: 仓库所有者
            repo: 仓库名称

        Returns:
            是否成功
        """
        try:
            repo_url = f"https://github.com/{owner}/{repo}"
            await page.goto(repo_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 查找Star按钮
            star_button = await page.query_selector('button[data-ga-click*="star"]')
            if not star_button:
                self.logger.warning(f"Star button not found for {owner}/{repo}")
                return False

            # 检查是否已经starred
            aria_label = await star_button.get_attribute('aria-label')
            if aria_label and 'unstar' in aria_label.lower():
                self.logger.info(f"Repository {owner}/{repo} already starred")
                return True

            # 点击Star
            await star_button.click()
            await asyncio.sleep(random.uniform(0.5, 1))

            self.logger.info(f"Successfully starred {owner}/{repo}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to star repository: {e}")
            return False

    async def unstar_repository(self, page: Page, owner: str, repo: str) -> bool:
        """Unstar仓库"""
        try:
            repo_url = f"https://github.com/{owner}/{repo}"
            await page.goto(repo_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 查找Unstar按钮
            unstar_button = await page.query_selector('button[data-ga-click*="unstar"]')
            if not unstar_button:
                self.logger.warning(f"Repository {owner}/{repo} not starred")
                return False

            await unstar_button.click()
            await asyncio.sleep(random.uniform(0.5, 1))

            self.logger.info(f"Successfully unstarred {owner}/{repo}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to unstar repository: {e}")
            return False

    async def fork_repository(self, page: Page, owner: str, repo: str) -> bool:
        """Fork仓库"""
        try:
            repo_url = f"https://github.com/{owner}/{repo}"
            await page.goto(repo_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 查找Fork按钮
            fork_button = await page.query_selector('button[data-ga-click*="fork"]')
            if not fork_button:
                self.logger.warning(f"Fork button not found for {owner}/{repo}")
                return False

            await fork_button.click()
            await asyncio.sleep(random.uniform(2, 3))

            self.logger.info(f"Successfully forked {owner}/{repo}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to fork repository: {e}")
            return False

    async def watch_repository(self, page: Page, owner: str, repo: str) -> bool:
        """Watch仓库"""
        try:
            repo_url = f"https://github.com/{owner}/{repo}"
            await page.goto(repo_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 查找Watch按钮
            watch_button = await page.query_selector('button[data-ga-click*="watch"]')
            if not watch_button:
                self.logger.warning(f"Watch button not found for {owner}/{repo}")
                return False

            await watch_button.click()
            await asyncio.sleep(random.uniform(0.5, 1))

            self.logger.info(f"Successfully watched {owner}/{repo}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to watch repository: {e}")
            return False

    async def comment_on_issue(
        self,
        page: Page,
        owner: str,
        repo: str,
        issue_number: int,
        comment: str
    ) -> bool:
        """
        在Issue上评论

        Args:
            page: Playwright页面对象
            owner: 仓库所有者
            repo: 仓库名称
            issue_number: Issue编号
            comment: 评论内容

        Returns:
            是否成功
        """
        try:
            issue_url = f"https://github.com/{owner}/{repo}/issues/{issue_number}"
            await page.goto(issue_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 查找评论框
            comment_field = await page.query_selector('textarea[placeholder*="comment"]')
            if not comment_field:
                self.logger.warning(f"Comment field not found for issue #{issue_number}")
                return False

            # 输入评论
            await comment_field.fill(comment)
            await asyncio.sleep(random.uniform(0.5, 1))

            # 提交评论
            submit_button = await page.query_selector('button[type="submit"]:has-text("Comment")')
            if submit_button:
                await submit_button.click()
                await asyncio.sleep(random.uniform(1, 2))

                self.logger.info(f"Successfully commented on issue #{issue_number}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to comment on issue: {e}")
            return False

    async def comment_on_pr(
        self,
        page: Page,
        owner: str,
        repo: str,
        pr_number: int,
        comment: str
    ) -> bool:
        """在Pull Request上评论"""
        try:
            pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
            await page.goto(pr_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 查找评论框
            comment_field = await page.query_selector('textarea[placeholder*="comment"]')
            if not comment_field:
                self.logger.warning(f"Comment field not found for PR #{pr_number}")
                return False

            # 输入评论
            await comment_field.fill(comment)
            await asyncio.sleep(random.uniform(0.5, 1))

            # 提交评论
            submit_button = await page.query_selector('button[type="submit"]:has-text("Comment")')
            if submit_button:
                await submit_button.click()
                await asyncio.sleep(random.uniform(1, 2))

                self.logger.info(f"Successfully commented on PR #{pr_number}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to comment on PR: {e}")
            return False

    async def get_issue_comments(
        self,
        page: Page,
        owner: str,
        repo: str,
        issue_number: int
    ) -> List[Dict[str, Any]]:
        """获取Issue评论"""
        comments = []

        try:
            issue_url = f"https://github.com/{owner}/{repo}/issues/{issue_number}"
            await page.goto(issue_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(1, 2))

            # 解析评论
            comment_elements = await page.query_selector_all('.timeline-comment')

            for elem in comment_elements:
                try:
                    comment_data = {}

                    # 用户名
                    author_elem = await elem.query_selector('.author')
                    if author_elem:
                        comment_data['author'] = await author_elem.inner_text()

                    # 评论内容
                    body_elem = await elem.query_selector('.comment-body')
                    if body_elem:
                        comment_data['body'] = await body_elem.inner_text()

                    # 时间
                    time_elem = await elem.query_selector('relative-time')
                    if time_elem:
                        comment_data['created_at'] = await time_elem.get_attribute('datetime')

                    if comment_data.get('body'):
                        comments.append(comment_data)

                except Exception as e:
                    self.logger.debug(f"Error parsing comment: {e}")
                    continue

            self.logger.info(f"Collected {len(comments)} comments from issue #{issue_number}")

        except Exception as e:
            self.logger.error(f"Failed to get issue comments: {e}")

        return comments


class GitHubSpider(BaseSpider):
    """
    GitHub爬虫主类
    Layer 1: Spider - 完整的爬取功能实现

    功能:
    - 仓库搜索（关键词、语言、stars范围）
    - 用户信息获取（profile、followers、repos）
    - 仓库详情（README、stars、forks、issues、commits）
    - Issue和PR获取
    - 代码搜索
    - Trending仓库
    - 支持API v3和GraphQL v4
    - Cookie和Token双模式
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        tokens: Optional[List[str]] = None,
        use_graphql: bool = False
    ):
        super().__init__(
            platform="github",
            headless=headless,
            proxy=proxy
        )

        # 初始化各层组件
        self.anti_crawl = GitHubAntiCrawl(self)
        self.matcher = GitHubMatcher()
        self.interaction = GitHubInteraction(self)

        # GitHub配置
        self.base_url = "https://github.com"
        self.api_base_url = "https://api.github.com"
        self.graphql_url = "https://api.github.com/graphql"

        # API版本
        self.use_graphql = use_graphql
        self.api_version = APIVersion.GRAPHQL_V4 if use_graphql else APIVersion.REST_V3

        # 添加tokens
        if tokens:
            self.anti_crawl.add_tokens(tokens)

        # 缓存
        self._collected_repo_ids: Set[str] = set()

    async def start(self) -> None:
        """启动爬虫并初始化反爬措施"""
        await super().start()

        # 初始化反爬
        await self.anti_crawl.initialize(self._page)

        self.logger.info("GitHub spider started successfully")

    async def login(self, username: str, password: str) -> bool:
        """
        登录GitHub

        Args:
            username: 用户名或邮箱
            password: 密码

        Returns:
            登录是否成功
        """
        try:
            self.logger.info(f"Logging in to GitHub as {username}...")

            # 检查是否有保存的cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)

                if await self._check_login_status():
                    self._is_logged_in = True
                    self.logger.info("Logged in with saved cookies")
                    return True

            # 访问登录页
            await self.navigate(f"{self.base_url}/login")
            await asyncio.sleep(random.uniform(2, 3))

            # 填写用户名
            username_input = await self._page.wait_for_selector('#login_field', timeout=10000)
            await username_input.fill(username)
            await asyncio.sleep(random.uniform(0.3, 0.5))

            # 填写密码
            password_input = await self._page.wait_for_selector('#password', timeout=10000)
            await password_input.fill(password)
            await asyncio.sleep(random.uniform(0.3, 0.5))

            # 点击登录
            login_btn = await self._page.wait_for_selector('input[type="submit"][value="Sign in"]', timeout=10000)
            await login_btn.click()
            await asyncio.sleep(random.uniform(3, 5))

            # 检查是否需要2FA
            if await self._page.query_selector('input[name="app_otp"]'):
                self.logger.warning("2FA required. Please enter the code manually or use token-based auth.")
                # 等待用户输入2FA
                await asyncio.sleep(60)

            # 检查登录状态
            if await self._check_login_status():
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def _check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 检查是否有用户菜单
            user_menu = await self._page.query_selector('button[aria-label*="View profile"]')
            return user_menu is not None
        except:
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        search_type: str = "repositories",
        language: Optional[str] = None,
        sort: str = "best-match",
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索仓库

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            search_type: 搜索类型 (repositories/code/issues/users)
            language: 编程语言过滤
            sort: 排序方式 (best-match/stars/forks/updated)
            criteria: 匹配条件

        Returns:
            仓库列表
        """
        self.logger.info(
            f"Searching GitHub for '{keyword}', type: {search_type}, "
            f"language: {language}, max: {max_results}"
        )

        results = []

        try:
            # 构建搜索查询
            query = keyword
            if language:
                query += f" language:{language}"

            # 构建搜索URL
            search_params = {
                'q': query,
                'type': search_type,
                's': sort
            }
            search_url = f"{self.base_url}/search?{urlencode(search_params)}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载更多
            await self._scroll_and_load(max_results)

            # 解析搜索结果
            if search_type == "repositories":
                repo_elements = await self._page.query_selector_all('.repo-list-item')

                for elem in repo_elements[:max_results * 2]:
                    try:
                        repo_data = await self._parse_repository_element(elem)

                        if repo_data and repo_data.get('full_name'):
                            # 内容匹配
                            if criteria:
                                is_match, match_score = await self.matcher.match_repository(
                                    repo_data, criteria
                                )
                                if not is_match:
                                    continue
                                repo_data['match_score'] = match_score

                            repo_id = repo_data['full_name']
                            if repo_id not in self._collected_repo_ids:
                                results.append(repo_data)
                                self._collected_repo_ids.add(repo_id)

                            if len(results) >= max_results:
                                break

                    except Exception as e:
                        self.logger.error(f"Error parsing repository: {e}")
                        continue

            self.logger.info(f"Collected {len(results)} repositories for keyword: {keyword}")

        except Exception as e:
            self.logger.error(f"Search failed: {e}")

        return results

    async def _parse_repository_element(self, element) -> Optional[Dict[str, Any]]:
        """解析仓库元素"""
        try:
            repo_data = {
                'platform': 'github',
                'full_name': None,
                'owner': None,
                'repo': None,
                'url': None,
                'description': None,
                'language': None,
                'stars': 0,
                'forks': 0,
                'topics': [],
                'updated_at': None
            }

            # 仓库名称和链接
            title_elem = await element.query_selector('a.v-align-middle')
            if title_elem:
                href = await title_elem.get_attribute('href')
                if href:
                    parts = href.strip('/').split('/')
                    if len(parts) >= 2:
                        repo_data['owner'] = parts[0]
                        repo_data['repo'] = parts[1]
                        repo_data['full_name'] = f"{parts[0]}/{parts[1]}"
                        repo_data['url'] = f"{self.base_url}{href}"

            # 描述
            desc_elem = await element.query_selector('p.mb-1')
            if desc_elem:
                repo_data['description'] = (await desc_elem.inner_text()).strip()

            # 语言
            lang_elem = await element.query_selector('[itemprop="programmingLanguage"]')
            if lang_elem:
                repo_data['language'] = (await lang_elem.inner_text()).strip()

            # Stars
            stars_elem = await element.query_selector('a[href$="/stargazers"]')
            if stars_elem:
                stars_text = await stars_elem.inner_text()
                repo_data['stars'] = self.parser.parse_count(stars_text)

            # Forks
            forks_elem = await element.query_selector('a[href$="/forks"]')
            if forks_elem:
                forks_text = await forks_elem.inner_text()
                repo_data['forks'] = self.parser.parse_count(forks_text)

            # Topics
            topic_elements = await element.query_selector_all('a.topic-tag')
            for topic_elem in topic_elements:
                topic = (await topic_elem.inner_text()).strip()
                if topic:
                    repo_data['topics'].append(topic)

            # 更新时间
            updated_elem = await element.query_selector('relative-time')
            if updated_elem:
                repo_data['updated_at'] = await updated_elem.get_attribute('datetime')

            return repo_data if repo_data['full_name'] else None

        except Exception as e:
            self.logger.error(f"Error parsing repository element: {e}")
            return None

    async def get_user_profile(self, username: str) -> Dict[str, Any]:
        """
        获取用户资料

        Args:
            username: 用户名

        Returns:
            用户资料
        """
        self.logger.info(f"Getting profile for user: {username}")

        profile_data = {
            'platform': 'github',
            'username': username,
            'name': None,
            'bio': None,
            'avatar_url': None,
            'company': None,
            'location': None,
            'email': None,
            'website': None,
            'twitter': None,
            'followers': 0,
            'following': 0,
            'public_repos': 0,
            'public_gists': 0,
            'created_at': None,
            'updated_at': None
        }

        try:
            # 访问用户主页
            user_url = f"{self.base_url}/{username}"
            await self.navigate(user_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 姓名
            name_elem = await self._page.query_selector('.vcard-fullname')
            if name_elem:
                profile_data['name'] = (await name_elem.inner_text()).strip()

            # 简介
            bio_elem = await self._page.query_selector('.user-profile-bio')
            if bio_elem:
                profile_data['bio'] = (await bio_elem.inner_text()).strip()

            # 头像
            avatar_elem = await self._page.query_selector('.avatar-user')
            if avatar_elem:
                profile_data['avatar_url'] = await avatar_elem.get_attribute('src')

            # 公司
            company_elem = await self._page.query_selector('[itemprop="worksFor"]')
            if company_elem:
                profile_data['company'] = (await company_elem.inner_text()).strip()

            # 位置
            location_elem = await self._page.query_selector('[itemprop="homeLocation"]')
            if location_elem:
                profile_data['location'] = (await location_elem.inner_text()).strip()

            # 邮箱
            email_elem = await self._page.query_selector('[itemprop="email"]')
            if email_elem:
                profile_data['email'] = (await email_elem.inner_text()).strip()

            # 网站
            website_elem = await self._page.query_selector('[itemprop="url"]')
            if website_elem:
                profile_data['website'] = await website_elem.get_attribute('href')

            # Twitter
            twitter_elem = await self._page.query_selector('[itemprop="social"][href*="twitter.com"]')
            if twitter_elem:
                twitter_url = await twitter_elem.get_attribute('href')
                if twitter_url:
                    profile_data['twitter'] = twitter_url.split('/')[-1]

            # 统计数据
            followers_elem = await self._page.query_selector('a[href$="?tab=followers"] span')
            if followers_elem:
                followers_text = await followers_elem.inner_text()
                profile_data['followers'] = self.parser.parse_count(followers_text)

            following_elem = await self._page.query_selector('a[href$="?tab=following"] span')
            if following_elem:
                following_text = await following_elem.inner_text()
                profile_data['following'] = self.parser.parse_count(following_text)

            repos_elem = await self._page.query_selector('[data-tab-item="repositories"] span')
            if repos_elem:
                repos_text = await repos_elem.inner_text()
                profile_data['public_repos'] = self.parser.parse_count(repos_text)

            self.logger.info(f"Collected profile for {username}")

        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")

        return profile_data

    async def get_user_posts(
        self,
        username: str,
        max_posts: int = 20,
        criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户的仓库

        Args:
            username: 用户名
            max_posts: 最大仓库数
            criteria: 匹配条件

        Returns:
            仓库列表
        """
        self.logger.info(f"Getting repositories for user: {username}, max: {max_posts}")

        repos = []

        try:
            # 访问用户仓库页
            repos_url = f"{self.base_url}/{username}?tab=repositories"
            await self.navigate(repos_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 滚动加载
            await self._scroll_and_load(max_posts)

            # 解析仓库列表
            repo_elements = await self._page.query_selector_all('#user-repositories-list li')

            for elem in repo_elements[:max_posts * 2]:
                try:
                    # 仓库链接
                    link_elem = await elem.query_selector('a[itemprop="name codeRepository"]')
                    if not link_elem:
                        continue

                    repo_name = (await link_elem.inner_text()).strip()
                    repo_data = {
                        'platform': 'github',
                        'owner': username,
                        'repo': repo_name,
                        'full_name': f"{username}/{repo_name}",
                        'url': f"{self.base_url}/{username}/{repo_name}"
                    }

                    # 描述
                    desc_elem = await elem.query_selector('p[itemprop="description"]')
                    if desc_elem:
                        repo_data['description'] = (await desc_elem.inner_text()).strip()

                    # 语言
                    lang_elem = await elem.query_selector('[itemprop="programmingLanguage"]')
                    if lang_elem:
                        repo_data['language'] = (await lang_elem.inner_text()).strip()

                    # Stars
                    stars_elem = await elem.query_selector('a[href$="/stargazers"]')
                    if stars_elem:
                        stars_text = await stars_elem.inner_text()
                        repo_data['stars'] = self.parser.parse_count(stars_text)

                    # Forks
                    forks_elem = await elem.query_selector('a[href$="/forks"]')
                    if forks_elem:
                        forks_text = await forks_elem.inner_text()
                        repo_data['forks'] = self.parser.parse_count(forks_text)

                    # 内容匹配
                    if criteria:
                        is_match, match_score = await self.matcher.match_repository(
                            repo_data, criteria
                        )
                        if not is_match:
                            continue
                        repo_data['match_score'] = match_score

                    repos.append(repo_data)

                    if len(repos) >= max_posts:
                        break

                except Exception as e:
                    self.logger.error(f"Error parsing repository: {e}")
                    continue

            self.logger.info(f"Collected {len(repos)} repositories for user: {username}")

        except Exception as e:
            self.logger.error(f"Failed to get user repositories: {e}")

        return repos

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        获取仓库详情

        Args:
            post_id: 仓库全名 (owner/repo)

        Returns:
            仓库详细信息
        """
        self.logger.info(f"Getting repository detail: {post_id}")

        repo_data = {
            'platform': 'github',
            'full_name': post_id,
            'owner': None,
            'repo': None,
            'url': None,
            'description': None,
            'homepage': None,
            'language': None,
            'languages': {},
            'stars': 0,
            'forks': 0,
            'watchers': 0,
            'open_issues': 0,
            'topics': [],
            'license': None,
            'readme': None,
            'created_at': None,
            'updated_at': None,
            'pushed_at': None,
            'size': 0,
            'default_branch': 'main',
            'is_fork': False,
            'is_archived': False,
            'commits_count': 0,
            'branches_count': 0,
            'releases_count': 0,
            'contributors_count': 0
        }

        try:
            # 解析owner和repo
            parts = post_id.split('/')
            if len(parts) != 2:
                raise ValueError(f"Invalid repository ID: {post_id}")

            repo_data['owner'] = parts[0]
            repo_data['repo'] = parts[1]

            # 访问仓库页面
            repo_url = f"{self.base_url}/{post_id}"
            repo_data['url'] = repo_url

            await self.navigate(repo_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 仓库名称
            name_elem = await self._page.query_selector('[itemprop="name"]')
            if not name_elem:
                self.logger.warning(f"Repository not found: {post_id}")
                return repo_data

            # 描述
            desc_elem = await self._page.query_selector('[itemprop="about"]')
            if desc_elem:
                repo_data['description'] = (await desc_elem.inner_text()).strip()

            # 主页
            homepage_elem = await self._page.query_selector('[data-pjax="#repo-content-pjax-container"] a[href]:not([href*="github.com"])')
            if homepage_elem:
                repo_data['homepage'] = await homepage_elem.get_attribute('href')

            # Stars
            stars_elem = await self._page.query_selector('#repo-stars-counter-star')
            if stars_elem:
                stars_text = await stars_elem.get_attribute('title')
                if not stars_text:
                    stars_text = await stars_elem.inner_text()
                repo_data['stars'] = self.parser.parse_count(stars_text)

            # Forks
            forks_elem = await self._page.query_selector('#repo-network-counter')
            if forks_elem:
                forks_text = await forks_elem.get_attribute('title')
                if not forks_text:
                    forks_text = await forks_elem.inner_text()
                repo_data['forks'] = self.parser.parse_count(forks_text)

            # Watchers
            watchers_elem = await self._page.query_selector('#repo-notifications-counter')
            if watchers_elem:
                watchers_text = await watchers_elem.get_attribute('title')
                if not watchers_text:
                    watchers_text = await watchers_elem.inner_text()
                repo_data['watchers'] = self.parser.parse_count(watchers_text)

            # 主要语言
            lang_elem = await self._page.query_selector('[itemprop="programmingLanguage"]')
            if lang_elem:
                repo_data['language'] = (await lang_elem.inner_text()).strip()

            # Topics
            topic_elements = await self._page.query_selector_all('a.topic-tag')
            for topic_elem in topic_elements:
                topic = (await topic_elem.inner_text()).strip()
                if topic:
                    repo_data['topics'].append(topic)

            # License
            license_elem = await self._page.query_selector('a[href*="/blob/"][href*="LICENSE"]')
            if license_elem:
                repo_data['license'] = (await license_elem.inner_text()).strip()

            # README
            readme_elem = await self._page.query_selector('#readme article')
            if readme_elem:
                repo_data['readme'] = (await readme_elem.inner_text()).strip()

            # 是否Fork
            fork_elem = await self._page.query_selector('.fork-flag')
            repo_data['is_fork'] = fork_elem is not None

            # 是否归档
            archived_elem = await self._page.query_selector('.label-archived')
            repo_data['is_archived'] = archived_elem is not None

            # Issues数量
            issues_elem = await self._page.query_selector('[data-tab-item="issues-tab"] .Counter')
            if issues_elem:
                issues_text = await issues_elem.inner_text()
                repo_data['open_issues'] = self.parser.parse_count(issues_text)

            # Commits数量
            commits_elem = await self._page.query_selector('.commits .num')
            if commits_elem:
                commits_text = await commits_elem.inner_text()
                repo_data['commits_count'] = self.parser.parse_count(commits_text)

            # Branches数量
            branches_elem = await self._page.query_selector('[href$="/branches"] .num')
            if branches_elem:
                branches_text = await branches_elem.inner_text()
                repo_data['branches_count'] = self.parser.parse_count(branches_text)

            # Releases数量
            releases_elem = await self._page.query_selector('[href$="/releases"] .num')
            if releases_elem:
                releases_text = await releases_elem.inner_text()
                repo_data['releases_count'] = self.parser.parse_count(releases_text)

            self.logger.info(f"Collected repository detail: {post_id}")

        except Exception as e:
            self.logger.error(f"Failed to get repository detail: {e}")

        return repo_data

    async def get_comments(
        self,
        post_id: str,
        max_comments: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取仓库的Issues

        Args:
            post_id: 仓库全名 (owner/repo)
            max_comments: 最大Issue数

        Returns:
            Issue列表
        """
        self.logger.info(f"Getting issues for repository: {post_id}, max: {max_comments}")

        issues = []

        try:
            # 访问Issues页面
            issues_url = f"{self.base_url}/{post_id}/issues"
            await self.navigate(issues_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 解析Issue列表
            issue_elements = await self._page.query_selector_all('.js-issue-row')

            for elem in issue_elements[:max_comments]:
                try:
                    issue_data = {
                        'platform': 'github',
                        'repository': post_id,
                        'number': None,
                        'title': None,
                        'state': 'open',
                        'author': None,
                        'labels': [],
                        'comments_count': 0,
                        'created_at': None,
                        'url': None
                    }

                    # 标题和链接
                    title_elem = await elem.query_selector('.Link--primary')
                    if title_elem:
                        issue_data['title'] = (await title_elem.inner_text()).strip()
                        href = await title_elem.get_attribute('href')
                        if href:
                            issue_data['url'] = f"{self.base_url}{href}"
                            # 提取issue编号
                            if '/issues/' in href:
                                issue_data['number'] = int(href.split('/issues/')[-1].split('/')[0])

                    # 作者
                    author_elem = await elem.query_selector('.opened-by a')
                    if author_elem:
                        issue_data['author'] = (await author_elem.inner_text()).strip()

                    # 标签
                    label_elements = await elem.query_selector_all('.IssueLabel')
                    for label_elem in label_elements:
                        label = (await label_elem.inner_text()).strip()
                        if label:
                            issue_data['labels'].append(label)

                    # 评论数
                    comments_elem = await elem.query_selector('.Link--muted')
                    if comments_elem:
                        comments_text = await comments_elem.inner_text()
                        if comments_text:
                            issue_data['comments_count'] = self.parser.parse_count(comments_text)

                    if issue_data['number']:
                        issues.append(issue_data)

                except Exception as e:
                    self.logger.error(f"Error parsing issue: {e}")
                    continue

            self.logger.info(f"Collected {len(issues)} issues for repository: {post_id}")

        except Exception as e:
            self.logger.error(f"Failed to get issues: {e}")

        return issues

    async def get_trending(
        self,
        language: Optional[str] = None,
        since: str = "daily",
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        获取Trending仓库

        Args:
            language: 编程语言
            since: 时间范围 (daily/weekly/monthly)
            max_results: 最大结果数

        Returns:
            Trending仓库列表
        """
        self.logger.info(f"Getting trending repositories (language: {language}, since: {since})")

        trending_repos = []

        try:
            # 构建URL
            trending_url = f"{self.base_url}/trending"
            if language:
                trending_url += f"/{language}"
            trending_url += f"?since={since}"

            # 访问Trending页面
            await self.navigate(trending_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 解析仓库列表
            repo_elements = await self._page.query_selector_all('article.Box-row')

            for elem in repo_elements[:max_results]:
                try:
                    repo_data = {}

                    # 仓库名称
                    name_elem = await elem.query_selector('h2 a')
                    if name_elem:
                        href = await name_elem.get_attribute('href')
                        if href:
                            full_name = href.strip('/')
                            repo_data['full_name'] = full_name
                            repo_data['url'] = f"{self.base_url}{href}"

                            parts = full_name.split('/')
                            if len(parts) == 2:
                                repo_data['owner'] = parts[0]
                                repo_data['repo'] = parts[1]

                    # 描述
                    desc_elem = await elem.query_selector('p')
                    if desc_elem:
                        repo_data['description'] = (await desc_elem.inner_text()).strip()

                    # 语言
                    lang_elem = await elem.query_selector('[itemprop="programmingLanguage"]')
                    if lang_elem:
                        repo_data['language'] = (await lang_elem.inner_text()).strip()

                    # Stars (总数和今日新增)
                    stars_elem = await elem.query_selector('a[href$="/stargazers"]')
                    if stars_elem:
                        stars_text = await stars_elem.inner_text()
                        repo_data['stars'] = self.parser.parse_count(stars_text)

                    stars_today_elem = await elem.query_selector('.float-sm-right')
                    if stars_today_elem:
                        stars_today_text = await stars_today_elem.inner_text()
                        if 'stars today' in stars_today_text.lower():
                            repo_data['stars_today'] = self.parser.parse_count(stars_today_text)

                    # Forks
                    forks_elem = await elem.query_selector('a[href$="/forks"]')
                    if forks_elem:
                        forks_text = await forks_elem.inner_text()
                        repo_data['forks'] = self.parser.parse_count(forks_text)

                    if repo_data.get('full_name'):
                        trending_repos.append(repo_data)

                except Exception as e:
                    self.logger.error(f"Error parsing trending repository: {e}")
                    continue

            self.logger.info(f"Collected {len(trending_repos)} trending repositories")

        except Exception as e:
            self.logger.error(f"Failed to get trending repositories: {e}")

        return trending_repos

    async def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索代码

        Args:
            query: 搜索查询
            language: 编程语言过滤
            max_results: 最大结果数

        Returns:
            代码搜索结果
        """
        self.logger.info(f"Searching code for: {query}, language: {language}")

        results = []

        try:
            # 构建搜索查询
            search_query = query
            if language:
                search_query += f" language:{language}"

            # 构建URL
            search_params = {
                'q': search_query,
                'type': 'code'
            }
            search_url = f"{self.base_url}/search?{urlencode(search_params)}"

            # 访问搜索页
            await self.navigate(search_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 解析代码结果
            code_elements = await self._page.query_selector_all('.code-list-item')

            for elem in code_elements[:max_results]:
                try:
                    code_data = {}

                    # 文件路径
                    path_elem = await elem.query_selector('.f4 a')
                    if path_elem:
                        code_data['path'] = (await path_elem.inner_text()).strip()
                        href = await path_elem.get_attribute('href')
                        if href:
                            code_data['url'] = f"{self.base_url}{href}"

                            # 提取仓库信息
                            parts = href.strip('/').split('/')
                            if len(parts) >= 4:
                                code_data['repository'] = f"{parts[0]}/{parts[1]}"

                    # 代码片段
                    code_elem = await elem.query_selector('.code-list-item-code')
                    if code_elem:
                        code_data['code_snippet'] = (await code_elem.inner_text()).strip()

                    if code_data.get('path'):
                        results.append(code_data)

                except Exception as e:
                    self.logger.error(f"Error parsing code result: {e}")
                    continue

            self.logger.info(f"Collected {len(results)} code results")

        except Exception as e:
            self.logger.error(f"Code search failed: {e}")

        return results

    async def get_pull_requests(
        self,
        repo_id: str,
        state: str = "open",
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取Pull Requests

        Args:
            repo_id: 仓库全名 (owner/repo)
            state: PR状态 (open/closed/all)
            max_results: 最大结果数

        Returns:
            PR列表
        """
        self.logger.info(f"Getting pull requests for {repo_id}, state: {state}")

        prs = []

        try:
            # 访问PR页面
            pr_url = f"{self.base_url}/{repo_id}/pulls?q=is%3Apr+is%3A{state}"
            await self.navigate(pr_url)
            await asyncio.sleep(random.uniform(2, 3))

            # 解析PR列表
            pr_elements = await self._page.query_selector_all('.js-issue-row')

            for elem in pr_elements[:max_results]:
                try:
                    pr_data = {
                        'platform': 'github',
                        'repository': repo_id,
                        'number': None,
                        'title': None,
                        'state': state,
                        'author': None,
                        'labels': [],
                        'created_at': None,
                        'url': None
                    }

                    # 标题和链接
                    title_elem = await elem.query_selector('.Link--primary')
                    if title_elem:
                        pr_data['title'] = (await title_elem.inner_text()).strip()
                        href = await title_elem.get_attribute('href')
                        if href:
                            pr_data['url'] = f"{self.base_url}{href}"
                            if '/pull/' in href:
                                pr_data['number'] = int(href.split('/pull/')[-1].split('/')[0])

                    # 作者
                    author_elem = await elem.query_selector('.opened-by a')
                    if author_elem:
                        pr_data['author'] = (await author_elem.inner_text()).strip()

                    # 标签
                    label_elements = await elem.query_selector_all('.IssueLabel')
                    for label_elem in label_elements:
                        label = (await label_elem.inner_text()).strip()
                        if label:
                            pr_data['labels'].append(label)

                    if pr_data['number']:
                        prs.append(pr_data)

                except Exception as e:
                    self.logger.error(f"Error parsing PR: {e}")
                    continue

            self.logger.info(f"Collected {len(prs)} pull requests for {repo_id}")

        except Exception as e:
            self.logger.error(f"Failed to get pull requests: {e}")

        return prs

    async def _scroll_and_load(self, target_count: int) -> None:
        """滚动加载更多内容"""
        last_height = 0
        no_change_count = 0
        max_scrolls = min(target_count // 10, 10)

        for _ in range(max_scrolls):
            # 滚动到底部
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(1, 2))

            # 检查页面高度
            current_height = await self._page.evaluate("document.body.scrollHeight")

            if current_height == last_height:
                no_change_count += 1
                if no_change_count >= 2:
                    break
            else:
                no_change_count = 0
                last_height = current_height


# 便捷函数
async def search_github_repositories(
    keyword: str,
    max_results: int = 20,
    language: Optional[str] = None,
    headless: bool = True,
    criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：搜索GitHub仓库

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        language: 编程语言过滤
        headless: 是否无头模式
        criteria: 匹配条件

    Returns:
        仓库列表
    """
    spider = GitHubSpider(headless=headless)

    async with spider.session():
        results = await spider.search(
            keyword,
            max_results,
            language=language,
            criteria=criteria
        )
        return results


async def get_github_trending(
    language: Optional[str] = None,
    since: str = "daily",
    headless: bool = True
) -> List[Dict[str, Any]]:
    """
    便捷函数：获取GitHub Trending

    Args:
        language: 编程语言
        since: 时间范围
        headless: 是否无头模式

    Returns:
        Trending仓库列表
    """
    spider = GitHubSpider(headless=headless)

    async with spider.session():
        results = await spider.get_trending(language=language, since=since)
        return results


if __name__ == "__main__":
    # 测试代码
    async def test_github_spider():
        # 创建爬虫实例
        spider = GitHubSpider(headless=False)

        async with spider.session():
            print("=" * 50)
            print("Testing GitHub Spider")
            print("=" * 50)

            # 测试1: 搜索仓库
            print("\n1. Testing repository search...")
            repos = await spider.search(
                "machine learning",
                max_results=5,
                language="python",
                criteria={
                    'min_stars': 1000,
                    'languages': ['python']
                }
            )

            for repo in repos:
                print(f"\nRepo: {repo.get('full_name')}")
                print(f"Description: {repo.get('description', 'N/A')[:100]}")
                print(f"Stars: {repo.get('stars')}")
                print(f"Language: {repo.get('language')}")
                print(f"Topics: {', '.join(repo.get('topics', [])[:5])}")

            # 测试2: 获取Trending
            print("\n2. Testing trending repositories...")
            trending = await spider.get_trending(language="python", since="daily", max_results=3)

            for repo in trending:
                print(f"\nTrending: {repo.get('full_name')}")
                print(f"Stars: {repo.get('stars')}")
                print(f"Stars today: {repo.get('stars_today', 'N/A')}")

            # 测试3: 获取仓库详情
            if repos:
                print("\n3. Testing repository detail...")
                first_repo = repos[0]
                detail = await spider.get_post_detail(first_repo['full_name'])

                print(f"\nRepository: {detail.get('full_name')}")
                print(f"Description: {detail.get('description', 'N/A')[:100]}")
                print(f"Stars: {detail.get('stars')}")
                print(f"Forks: {detail.get('forks')}")
                print(f"Open Issues: {detail.get('open_issues')}")
                print(f"License: {detail.get('license', 'N/A')}")
                print(f"Topics: {', '.join(detail.get('topics', []))}")

            # 测试4: 获取用户信息
            print("\n4. Testing user profile...")
            profile = await spider.get_user_profile("torvalds")

            print(f"\nUser: {profile.get('username')}")
            print(f"Name: {profile.get('name')}")
            print(f"Bio: {profile.get('bio', 'N/A')[:100]}")
            print(f"Followers: {profile.get('followers')}")
            print(f"Public Repos: {profile.get('public_repos')}")

            print("\n" + "=" * 50)
            print("All tests completed!")
            print("=" * 50)

    # 运行测试
    asyncio.run(test_github_spider())
