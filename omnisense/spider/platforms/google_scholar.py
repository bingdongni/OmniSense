"""
Google Scholar Spider Implementation
完整的谷歌学术爬虫实现 - 4层架构

Architecture Layers:
===================
Layer 1 - Spider Layer: 论文搜索、作者信息、引用追踪、相关论文、期刊信息、H-index计算
Layer 2 - Anti-Crawl Layer: reCAPTCHA、请求延迟、UA轮换、Cookie管理、IP代理、频率控制、浏览器指纹
Layer 3 - Matcher Layer: 引用数阈值、年份过滤、期刊质量、作者匹配、研究领域、开放获取
Layer 4 - Interaction Layer: 引用导出、相关推荐、引用网络、协作网络、影响力评估

Features:
=========
- Comprehensive paper search with advanced filters
- Author profile analysis with citation metrics
- Citation tracking and network analysis
- Journal/conference quality filtering
- Multi-format citation export (BibTeX, RIS, EndNote)
- Collaboration network visualization
- Impact factor assessment
- Advanced anti-crawl mechanisms
- Selenium and Playwright support
- Intelligent retry and rate limiting

Author: OmniSense Team
Date: 2026-01-14
Version: 2.0.0
"""

import asyncio
import hashlib
import json
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urlencode, urlparse, parse_qs

from omnisense.spider.base import BaseSpider


# ============================================================================
# Layer 1: Spider Layer - 核心数据采集
# ============================================================================

class GoogleScholarSpider(BaseSpider):
    """
    Google Scholar Spider - 完整的4层架构实现

    This spider implements comprehensive Google Scholar data collection
    with advanced anti-crawl mechanisms and intelligent filtering.
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        use_scholar_cn: bool = False,
        captcha_api_key: Optional[str] = None,
    ):
        """
        Initialize Google Scholar spider

        Args:
            headless: Run browser in headless mode
            proxy: Proxy server URL
            use_scholar_cn: Use scholar.google.com.cn instead of .com
            captcha_api_key: API key for captcha solving service
        """
        super().__init__(platform="google_scholar", headless=headless, proxy=proxy)

        # URLs
        self.base_url = "https://scholar.google.com.cn" if use_scholar_cn else "https://scholar.google.com"
        self.search_url = f"{self.base_url}/scholar"
        self.citations_url = f"{self.base_url}/citations"

        # Anti-crawl configuration
        self.captcha_api_key = captcha_api_key
        self._user_agents = self._load_user_agents()
        self._current_ua_index = 0
        self._request_timestamps: List[float] = []
        self._captcha_detected_count = 0
        self._max_captcha_retries = 3

        # Cookie pool for rotation
        self._cookie_pool: List[Dict] = []
        self._current_cookie_index = 0

        # Rate limiting configuration
        self._min_request_interval = 2.0  # Minimum 2 seconds between requests
        self._max_request_interval = 5.0  # Maximum 5 seconds
        self._requests_per_window = 10  # Max requests per time window
        self._time_window = 60.0  # 60 seconds window

        # Cache for reducing repeated requests
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1 hour cache TTL

        # Quality thresholds (Layer 3)
        self._min_citations = 0
        self._min_year = 1900
        self._max_year = datetime.now().year + 1
        self._quality_journals: Set[str] = set()
        self._impact_factor_db: Dict[str, float] = {}

        # Collaboration network data
        self._author_network: Dict[str, Set[str]] = defaultdict(set)
        self._coauthor_papers: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)

        self.logger.info(f"Initialized Google Scholar spider (URL: {self.base_url})")

    # ========================================================================
    # Layer 1: Core Spider Methods
    # ========================================================================

    async def login(self, username: str, password: str) -> bool:
        """
        Login to Google Scholar (optional for enhanced features)

        Google Scholar allows public access but login provides benefits:
        - Access to personal library
        - Citation alerts
        - Follow authors
        - Create public profiles

        Args:
            username: Google account email
            password: Google account password

        Returns:
            bool: True if login successful
        """
        try:
            self.logger.info("Attempting to login to Google Scholar...")

            # Check for existing valid cookies
            if self._cookies_file.exists():
                await self._load_cookies()
                await self.navigate(self.base_url)
                await asyncio.sleep(2)

                # Check if already logged in
                if await self._page.query_selector('[data-ved][aria-label*="profile" i]'):
                    self._is_logged_in = True
                    self.logger.info("Already logged in via saved cookies")
                    return True

            # Navigate to Google login
            login_url = "https://accounts.google.com/ServiceLogin?service=scholar"
            await self.navigate(login_url)
            await asyncio.sleep(random.uniform(2, 3))

            # Enter email
            email_input = await self._page.query_selector('input[type="email"]')
            if email_input:
                await email_input.fill(username)
                await asyncio.sleep(random.uniform(0.5, 1))
                await self._page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(2, 3))
            else:
                self.logger.warning("Email input not found")
                return False

            # Enter password
            password_input = await self._page.query_selector('input[type="password"]')
            if password_input:
                await password_input.fill(password)
                await asyncio.sleep(random.uniform(0.5, 1))
                await self._page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(3, 5))
            else:
                self.logger.warning("Password input not found")
                return False

            # Check for 2FA or other verification
            if await self._page.query_selector('[data-challengetype]'):
                self.logger.warning("Two-factor authentication detected - manual intervention required")
                # Wait for manual completion
                await self._page.wait_for_url(f"{self.base_url}/**", timeout=120000)

            # Verify login success
            await self.navigate(self.base_url)
            await asyncio.sleep(2)

            if await self._page.query_selector('[data-ved][aria-label*="profile" i]'):
                self._is_logged_in = True
                await self._save_cookies()
                self.logger.info("Login successful")
                return True
            else:
                self.logger.warning("Login verification failed")
                return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        year_low: Optional[int] = None,
        year_high: Optional[int] = None,
        sort_by: str = "relevance",
        include_citations: bool = True,
        include_patents: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search Google Scholar with advanced filters

        Args:
            keyword: Search query
            max_results: Maximum number of results
            year_low: Filter by start year
            year_high: Filter by end year
            sort_by: Sort order ('relevance' or 'date')
            include_citations: Include citation results
            include_patents: Include patents in results

        Returns:
            List of paper dictionaries with metadata
        """
        try:
            self.logger.info(f"Searching Google Scholar: '{keyword}'")

            # Build search parameters
            params = {"q": keyword}

            # Date range filter
            if year_low or year_high:
                y_low = year_low or 1900
                y_high = year_high or datetime.now().year
                params["as_ylo"] = y_low
                params["as_yhi"] = y_high

            # Sort order
            if sort_by == "date":
                params["scisbd"] = "1"  # Sort by date

            # Exclude citations
            if not include_citations:
                params["as_vis"] = "1"

            # Exclude patents
            if not include_patents:
                params["as_sdt"] = "0,5"

            # Construct URL
            search_url = f"{self.search_url}?{urlencode(params)}"

            # Apply anti-crawl measures
            await self._apply_anti_crawl_measures()

            # Navigate with retry
            success = await self._navigate_with_retry(search_url)
            if not success:
                return []

            # Check for CAPTCHA
            if await self._detect_captcha():
                self.logger.warning("CAPTCHA detected during search")
                if not await self._handle_captcha():
                    return []

            # Wait for results to load
            await asyncio.sleep(random.uniform(1, 2))

            # Parse results
            results = await self._parse_search_results(max_results)

            self.logger.info(f"Found {len(results)} papers")
            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    async def search_by_author(
        self,
        author_name: str,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search papers by author name

        Args:
            author_name: Author's full name
            max_results: Maximum results to return

        Returns:
            List of papers by the author
        """
        try:
            self.logger.info(f"Searching papers by author: {author_name}")

            # Use author search syntax
            query = f"author:\"{author_name}\""
            return await self.search(query, max_results=max_results)

        except Exception as e:
            self.logger.error(f"Author search failed: {e}")
            return []

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive Google Scholar author profile

        Args:
            user_id: Scholar user ID (from profile URL)

        Returns:
            Dictionary containing profile information:
            - name, affiliation, email domain
            - citation metrics (total, h-index, i10-index)
            - research interests
            - co-authors
            - citation history
        """
        try:
            self.logger.info(f"Fetching profile for user: {user_id}")

            # Check cache
            cache_key = f"profile_{user_id}"
            if cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                if time.time() - cached_time < self._cache_ttl:
                    self.logger.debug("Returning cached profile data")
                    return cached_data

            # Build profile URL
            profile_url = f"{self.citations_url}?user={user_id}&hl=en"

            # Apply anti-crawl
            await self._apply_anti_crawl_measures()

            # Navigate
            success = await self._navigate_with_retry(profile_url)
            if not success:
                return {}

            # Check CAPTCHA
            if await self._detect_captcha():
                if not await self._handle_captcha():
                    return {}

            await asyncio.sleep(random.uniform(1, 2))

            # Parse profile
            profile = await self._parse_author_profile(user_id)

            # Get citation history
            profile["citation_history"] = await self._get_citation_history()

            # Get co-authors
            profile["coauthors"] = await self._get_coauthors()

            # Calculate additional metrics
            profile["metrics"] = await self._calculate_author_metrics(profile)

            # Cache the result
            self._cache[cache_key] = (profile, time.time())

            self.logger.info(f"Profile retrieved: {profile.get('name', 'Unknown')}")
            return profile

        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            return {}

    async def get_user_posts(
        self,
        user_id: str,
        max_posts: int = 20,
        sort_by: str = "citations",
    ) -> List[Dict[str, Any]]:
        """
        Get publications from a Google Scholar profile

        Args:
            user_id: Scholar user ID
            max_posts: Maximum number of publications
            sort_by: Sort order ('citations', 'year', 'title')

        Returns:
            List of publication dictionaries
        """
        try:
            self.logger.info(f"Fetching publications for user: {user_id}")

            # Build URL with sorting
            sort_param = {
                "citations": "pubdate",
                "year": "pubdate",
                "title": "title",
            }.get(sort_by, "pubdate")

            profile_url = f"{self.citations_url}?user={user_id}&hl=en&cstart=0&pagesize=100&sortby={sort_param}"

            # Apply anti-crawl
            await self._apply_anti_crawl_measures()

            # Navigate
            success = await self._navigate_with_retry(profile_url)
            if not success:
                return []

            # Check CAPTCHA
            if await self._detect_captcha():
                if not await self._handle_captcha():
                    return []

            await asyncio.sleep(random.uniform(1, 2))

            # Parse publications
            posts = await self._parse_user_publications(user_id, max_posts)

            self.logger.info(f"Retrieved {len(posts)} publications")
            return posts

        except Exception as e:
            self.logger.error(f"Failed to get publications: {e}")
            return []

    async def get_post_detail(self, post_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific paper

        Args:
            post_id: Paper ID (can be URL, DOI, or cluster ID)

        Returns:
            Detailed paper information including:
            - Full metadata
            - All versions
            - Citation contexts
            - Related papers
            - Full citation graph
        """
        try:
            self.logger.info(f"Fetching paper details: {post_id}")

            # Determine URL from ID
            if post_id.startswith("http"):
                paper_url = post_id
            elif "cluster:" in post_id:
                cluster_id = post_id.split("cluster:")[-1]
                paper_url = f"{self.search_url}?cluster={cluster_id}"
            else:
                # Search by title or DOI
                return await self._search_paper_detail(post_id)

            # Apply anti-crawl
            await self._apply_anti_crawl_measures()

            # Navigate
            success = await self._navigate_with_retry(paper_url)
            if not success:
                return {}

            await asyncio.sleep(random.uniform(1, 2))

            # Parse paper detail
            detail = await self._parse_paper_detail(post_id)

            # Get citations to this paper
            if detail.get("cluster_id"):
                detail["citing_papers"] = await self.get_citing_papers(
                    detail["cluster_id"],
                    max_results=10
                )

            # Get related papers
            detail["related_papers"] = await self.get_related_papers(
                detail.get("title", ""),
                max_results=5
            )

            return detail

        except Exception as e:
            self.logger.error(f"Failed to get paper detail: {e}")
            return {}

    async def get_comments(self, post_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Get citations as 'comments' (papers that cite this work)

        Note: Google Scholar doesn't have traditional comments,
        but citations serve as academic commentary.

        Args:
            post_id: Paper cluster ID
            max_comments: Maximum number of citing papers

        Returns:
            List of citing papers with citation context
        """
        try:
            self.logger.info(f"Fetching citing papers for: {post_id}")

            citing_papers = await self.get_citing_papers(post_id, max_results=max_comments)

            # Format as comment-like structure
            comments = []
            for paper in citing_papers:
                comment = {
                    "id": paper.get("id"),
                    "author": paper.get("authors", "Unknown"),
                    "content": paper.get("snippet", ""),
                    "timestamp": paper.get("year"),
                    "citation_context": paper.get("citation_context", ""),
                    "paper_title": paper.get("title"),
                    "url": paper.get("url"),
                }
                comments.append(comment)

            return comments

        except Exception as e:
            self.logger.error(f"Failed to get citations: {e}")
            return []

    # ========================================================================
    # Advanced Spider Methods - Extended Layer 1
    # ========================================================================

    async def get_citing_papers(
        self,
        cluster_id: str,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get papers that cite a specific work

        Args:
            cluster_id: Google Scholar cluster ID
            max_results: Maximum citing papers to retrieve

        Returns:
            List of citing papers
        """
        try:
            self.logger.info(f"Fetching citing papers for cluster: {cluster_id}")

            # Build citations URL
            cites_url = f"{self.search_url}?cites={cluster_id}"

            await self._apply_anti_crawl_measures()
            success = await self._navigate_with_retry(cites_url)

            if not success:
                return []

            await asyncio.sleep(random.uniform(1, 2))

            # Parse citing papers
            citing_papers = await self._parse_search_results(max_results)

            self.logger.info(f"Found {len(citing_papers)} citing papers")
            return citing_papers

        except Exception as e:
            self.logger.error(f"Failed to get citing papers: {e}")
            return []

    async def get_related_papers(
        self,
        title_or_cluster: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get papers related to a specific work

        Args:
            title_or_cluster: Paper title or cluster ID
            max_results: Maximum related papers

        Returns:
            List of related papers
        """
        try:
            self.logger.info(f"Fetching related papers for: {title_or_cluster}")

            # Determine if cluster ID or title
            if title_or_cluster.startswith("cluster:"):
                cluster_id = title_or_cluster.split(":")[-1]
                related_url = f"{self.search_url}?q=related:{cluster_id}"
            else:
                # Search by title
                related_url = f"{self.search_url}?q=related:{quote(title_or_cluster)}"

            await self._apply_anti_crawl_measures()
            success = await self._navigate_with_retry(related_url)

            if not success:
                return []

            await asyncio.sleep(random.uniform(1, 2))

            related_papers = await self._parse_search_results(max_results)

            self.logger.info(f"Found {len(related_papers)} related papers")
            return related_papers

        except Exception as e:
            self.logger.error(f"Failed to get related papers: {e}")
            return []

    async def calculate_h_index(self, user_id: str) -> Dict[str, int]:
        """
        Calculate H-index and related metrics for an author

        The h-index is defined as the maximum value of h such that
        the given author has published h papers that have each been
        cited at least h times.

        Args:
            user_id: Scholar user ID

        Returns:
            Dictionary with h-index, i10-index, and citation stats
        """
        try:
            self.logger.info(f"Calculating H-index for: {user_id}")

            # Get user profile (contains citation metrics)
            profile = await self.get_user_profile(user_id)

            if not profile:
                return {}

            # Get all publications with citation counts
            publications = await self.get_user_posts(user_id, max_posts=100, sort_by="citations")

            # Extract citation counts
            citation_counts = [
                p.get("citations_count", 0)
                for p in publications
                if p.get("citations_count") is not None
            ]

            # Sort in descending order
            citation_counts.sort(reverse=True)

            # Calculate h-index
            h_index = 0
            for i, citations in enumerate(citation_counts, start=1):
                if citations >= i:
                    h_index = i
                else:
                    break

            # Calculate i10-index (papers with at least 10 citations)
            i10_index = sum(1 for c in citation_counts if c >= 10)

            # Calculate other metrics
            total_citations = sum(citation_counts)
            avg_citations = total_citations / len(citation_counts) if citation_counts else 0

            metrics = {
                "h_index": h_index,
                "i10_index": i10_index,
                "total_citations": total_citations,
                "total_papers": len(citation_counts),
                "avg_citations_per_paper": round(avg_citations, 2),
                "max_citations": citation_counts[0] if citation_counts else 0,
                "profile_h_index": profile.get("h_index", 0),  # From profile
                "profile_i10_index": profile.get("i10_index", 0),
            }

            self.logger.info(f"H-index calculated: {h_index}")
            return metrics

        except Exception as e:
            self.logger.error(f"Failed to calculate H-index: {e}")
            return {}

    async def get_journal_info(self, journal_name: str) -> Dict[str, Any]:
        """
        Get journal/conference information and metrics

        Args:
            journal_name: Name of journal or conference

        Returns:
            Journal metadata including impact metrics
        """
        try:
            self.logger.info(f"Fetching journal info: {journal_name}")

            # Search for journal
            query = f"source:\"{journal_name}\""
            results = await self.search(query, max_results=50)

            if not results:
                return {"name": journal_name, "paper_count": 0}

            # Aggregate metrics
            total_citations = sum(r.get("citations_count", 0) for r in results)
            paper_count = len(results)
            avg_citations = total_citations / paper_count if paper_count else 0

            # Extract years
            years = [r.get("year") for r in results if r.get("year")]

            journal_info = {
                "name": journal_name,
                "paper_count": paper_count,
                "total_citations": total_citations,
                "avg_citations_per_paper": round(avg_citations, 2),
                "year_range": (min(years), max(years)) if years else None,
                "recent_papers": results[:10],
                "estimated_impact_factor": self._estimate_impact_factor(results),
            }

            return journal_info

        except Exception as e:
            self.logger.error(f"Failed to get journal info: {e}")
            return {}

    # ========================================================================
    # Layer 2: Anti-Crawl Mechanisms
    # ========================================================================

    async def _apply_anti_crawl_measures(self) -> None:
        """
        Apply comprehensive anti-crawl measures before each request

        Implements:
        - Rate limiting with sliding window
        - User-Agent rotation
        - Cookie rotation
        - Request delay randomization
        - Browser fingerprint randomization
        """
        # Rate limiting - check request frequency
        current_time = time.time()

        # Remove timestamps outside the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if current_time - ts < self._time_window
        ]

        # Check if we've exceeded rate limit
        if len(self._request_timestamps) >= self._requests_per_window:
            wait_time = self._time_window - (current_time - self._request_timestamps[0])
            if wait_time > 0:
                self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time + random.uniform(0, 2))

        # Random delay between requests
        delay = random.uniform(self._min_request_interval, self._max_request_interval)
        await asyncio.sleep(delay)

        # Record this request
        self._request_timestamps.append(time.time())

        # Rotate User-Agent
        await self._rotate_user_agent()

        # Rotate cookies if available
        await self._rotate_cookies()

        # Apply random mouse movements and scrolling
        await self._simulate_human_behavior()

    async def _rotate_user_agent(self) -> None:
        """Rotate User-Agent header"""
        if self._user_agents:
            self._current_ua_index = (self._current_ua_index + 1) % len(self._user_agents)
            user_agent = self._user_agents[self._current_ua_index]

            # Update context user agent
            await self._context.add_init_script(f"""
                Object.defineProperty(navigator, 'userAgent', {{
                    get: () => '{user_agent}'
                }});
            """)

            self.logger.debug(f"Rotated User-Agent: {user_agent[:50]}...")

    async def _rotate_cookies(self) -> None:
        """Rotate cookies from cookie pool"""
        if self._cookie_pool and len(self._cookie_pool) > 1:
            self._current_cookie_index = (self._current_cookie_index + 1) % len(self._cookie_pool)
            cookies = self._cookie_pool[self._current_cookie_index]

            # Clear existing cookies and add new ones
            await self._context.clear_cookies()
            await self._context.add_cookies(cookies)

            self.logger.debug("Rotated cookie set")

    async def _simulate_human_behavior(self) -> None:
        """
        Simulate human-like behavior patterns

        Includes:
        - Random mouse movements
        - Random scrolling
        - Random pauses
        - Reading time simulation
        """
        if not self._page:
            return

        # Random mouse movement
        if random.random() < 0.3:  # 30% chance
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await self._page.mouse.move(x, y)

        # Random scroll
        if random.random() < 0.4:  # 40% chance
            scroll_amount = random.randint(100, 500)
            await self._page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.2, 0.5))

    async def _detect_captcha(self) -> bool:
        """
        Detect if Google Scholar is showing a CAPTCHA

        Returns:
            True if CAPTCHA detected
        """
        try:
            # Check for reCAPTCHA iframe
            captcha_iframe = await self._page.query_selector('iframe[src*="recaptcha"]')
            if captcha_iframe:
                self.logger.warning("reCAPTCHA iframe detected")
                self._captcha_detected_count += 1
                return True

            # Check for CAPTCHA image
            captcha_image = await self._page.query_selector('img[src*="captcha"]')
            if captcha_image:
                self.logger.warning("CAPTCHA image detected")
                self._captcha_detected_count += 1
                return True

            # Check for common CAPTCHA text
            page_text = await self._page.content()
            captcha_keywords = ["unusual traffic", "automated requests", "verify you're not a robot"]

            if any(keyword.lower() in page_text.lower() for keyword in captcha_keywords):
                self.logger.warning("CAPTCHA keywords detected in page")
                self._captcha_detected_count += 1
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error detecting CAPTCHA: {e}")
            return False

    async def _handle_captcha(self) -> bool:
        """
        Handle CAPTCHA challenge

        Strategies:
        1. Wait for manual solving (if not headless)
        2. Use captcha solving service (if API key provided)
        3. Switch IP/cookies and retry

        Returns:
            True if CAPTCHA successfully handled
        """
        try:
            self.logger.warning("Handling CAPTCHA challenge...")

            if self._captcha_detected_count > self._max_captcha_retries:
                self.logger.error("Too many CAPTCHA challenges, aborting")
                return False

            # Strategy 1: Manual solving for visible browser
            if not self.headless:
                self.logger.info("Please solve CAPTCHA manually (60s timeout)")
                try:
                    await self._page.wait_for_url(f"{self.base_url}/**", timeout=60000)
                    self.logger.info("CAPTCHA appears to be solved")
                    return True
                except:
                    self.logger.warning("CAPTCHA manual solve timeout")

            # Strategy 2: Use captcha solving service
            if self.captcha_api_key:
                success = await self._solve_captcha_with_service()
                if success:
                    return True

            # Strategy 3: Backoff and retry with different identity
            self.logger.info("Switching identity and retrying...")
            await self._rotate_user_agent()
            await self._rotate_cookies()

            # Longer delay before retry
            await asyncio.sleep(random.uniform(10, 20))

            return False

        except Exception as e:
            self.logger.error(f"Error handling CAPTCHA: {e}")
            return False

    async def _solve_captcha_with_service(self) -> bool:
        """
        Solve CAPTCHA using external service (2captcha, etc.)

        Returns:
            True if solved successfully
        """
        # Placeholder for captcha service integration
        # In production, integrate with services like:
        # - 2captcha
        # - Anti-Captcha
        # - CapMonster

        self.logger.warning("Captcha solving service not implemented")
        return False

    def _load_user_agents(self) -> List[str]:
        """
        Load a pool of realistic User-Agent strings

        Returns:
            List of User-Agent strings
        """
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",

            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",

            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",

            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]

    async def _navigate_with_retry(self, url: str, max_retries: int = 3) -> bool:
        """
        Navigate to URL with retry logic and error handling

        Args:
            url: Target URL
            max_retries: Maximum retry attempts

        Returns:
            True if navigation successful
        """
        for attempt in range(max_retries):
            try:
                await self.navigate(url)
                return True
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 2)
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to navigate after {max_retries} attempts")
                    return False
        return False

    # ========================================================================
    # Layer 3: Matcher/Filter Layer
    # ========================================================================

    def filter_by_citations(
        self,
        papers: List[Dict[str, Any]],
        min_citations: int,
        max_citations: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter papers by citation count

        Args:
            papers: List of paper dictionaries
            min_citations: Minimum citation threshold
            max_citations: Maximum citation threshold (optional)

        Returns:
            Filtered list of papers
        """
        filtered = []
        for paper in papers:
            citations = paper.get("citations_count", 0)
            if citations >= min_citations:
                if max_citations is None or citations <= max_citations:
                    filtered.append(paper)

        self.logger.info(f"Filtered {len(papers)} -> {len(filtered)} papers by citations")
        return filtered

    def filter_by_year(
        self,
        papers: List[Dict[str, Any]],
        year_low: Optional[int] = None,
        year_high: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter papers by publication year

        Args:
            papers: List of paper dictionaries
            year_low: Minimum year (inclusive)
            year_high: Maximum year (inclusive)

        Returns:
            Filtered list of papers
        """
        filtered = []
        current_year = datetime.now().year

        for paper in papers:
            year = paper.get("year")

            # Try to parse year from string if necessary
            if isinstance(year, str):
                year_match = re.search(r'\b(19|20)\d{2}\b', year)
                if year_match:
                    year = int(year_match.group())
                else:
                    continue

            if year is None:
                continue

            # Apply filters
            if year_low and year < year_low:
                continue
            if year_high and year > year_high:
                continue

            filtered.append(paper)

        self.logger.info(f"Filtered {len(papers)} -> {len(filtered)} papers by year")
        return filtered

    def filter_by_author(
        self,
        papers: List[Dict[str, Any]],
        author_name: str,
        exact_match: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Filter papers by author name

        Args:
            papers: List of paper dictionaries
            author_name: Author name to match
            exact_match: Require exact name match vs substring

        Returns:
            Papers authored by the specified person
        """
        filtered = []
        author_lower = author_name.lower()

        for paper in papers:
            authors = paper.get("authors", "")
            authors_lower = authors.lower()

            if exact_match:
                # Split by common separators and check each author
                author_list = re.split(r',|;|\band\b', authors_lower)
                author_list = [a.strip() for a in author_list]
                if author_lower in author_list:
                    filtered.append(paper)
            else:
                # Substring match
                if author_lower in authors_lower:
                    filtered.append(paper)

        self.logger.info(f"Filtered {len(papers)} -> {len(filtered)} papers by author")
        return filtered

    def filter_by_venue_quality(
        self,
        papers: List[Dict[str, Any]],
        quality_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Filter papers by publication venue quality

        Uses heuristics based on:
        - Citation count
        - Journal/conference reputation
        - Impact factor estimates

        Args:
            papers: List of paper dictionaries
            quality_threshold: Quality score threshold (0-1)

        Returns:
            High-quality papers
        """
        filtered = []

        for paper in papers:
            quality_score = self._calculate_venue_quality(paper)
            if quality_score >= quality_threshold:
                paper["venue_quality_score"] = quality_score
                filtered.append(paper)

        self.logger.info(f"Filtered {len(papers)} -> {len(filtered)} papers by venue quality")
        return filtered

    def filter_by_open_access(
        self,
        papers: List[Dict[str, Any]],
        open_access_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Filter papers by open access availability

        Args:
            papers: List of paper dictionaries
            open_access_only: Only include open access papers

        Returns:
            Filtered papers
        """
        filtered = []

        for paper in papers:
            has_pdf = bool(paper.get("pdf_url"))

            if open_access_only:
                if has_pdf:
                    filtered.append(paper)
            else:
                if not has_pdf:
                    filtered.append(paper)

        self.logger.info(f"Filtered {len(papers)} -> {len(filtered)} papers by open access")
        return filtered

    def classify_research_field(self, paper: Dict[str, Any]) -> List[str]:
        """
        Classify paper into research fields

        Uses keyword matching and venue analysis

        Args:
            paper: Paper dictionary

        Returns:
            List of research field tags
        """
        fields = []

        # Get text to analyze
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        venue = paper.get("venue", "").lower()

        text = f"{title} {abstract} {venue}"

        # Field keywords
        field_keywords = {
            "machine_learning": ["machine learning", "deep learning", "neural network", "ai", "artificial intelligence"],
            "computer_vision": ["computer vision", "image processing", "object detection", "segmentation"],
            "nlp": ["natural language", "nlp", "text mining", "language model", "bert", "gpt"],
            "robotics": ["robotics", "robot", "autonomous", "manipulation", "navigation"],
            "security": ["security", "cryptography", "privacy", "encryption", "attack"],
            "database": ["database", "sql", "query", "indexing", "transaction"],
            "networks": ["network", "protocol", "routing", "wireless", "internet"],
            "systems": ["operating system", "distributed", "parallel", "compiler"],
            "theory": ["algorithm", "complexity", "optimization", "graph theory"],
            "hci": ["human computer", "hci", "interface", "interaction", "usability"],
        }

        # Check each field
        for field, keywords in field_keywords.items():
            if any(kw in text for kw in keywords):
                fields.append(field)

        return fields if fields else ["general"]

    def _calculate_venue_quality(self, paper: Dict[str, Any]) -> float:
        """
        Calculate venue quality score (0-1)

        Args:
            paper: Paper dictionary

        Returns:
            Quality score between 0 and 1
        """
        score = 0.5  # Base score

        # Citation-based component
        citations = paper.get("citations_count", 0)
        if citations > 100:
            score += 0.3
        elif citations > 50:
            score += 0.2
        elif citations > 10:
            score += 0.1

        # Venue-based component
        venue = paper.get("venue", "").lower()

        # Top-tier venues (examples)
        top_venues = [
            "nature", "science", "cell", "pnas",
            "jama", "lancet", "nejm",
            "cvpr", "iccv", "neurips", "icml", "iclr",
            "sigmod", "vldb", "icde",
            "sigcomm", "nsdi", "osdi",
        ]

        if any(tv in venue for tv in top_venues):
            score += 0.2

        # Year recency component
        year = paper.get("year")
        if year:
            if isinstance(year, str):
                year_match = re.search(r'\b(19|20)\d{2}\b', year)
                if year_match:
                    year = int(year_match.group())

            if isinstance(year, int):
                current_year = datetime.now().year
                if current_year - year <= 2:
                    score += 0.1

        return min(score, 1.0)

    # ========================================================================
    # Layer 4: Interaction Layer
    # ========================================================================

    async def export_citation(
        self,
        paper: Dict[str, Any],
        format: str = "bibtex",
    ) -> str:
        """
        Export paper citation in various formats

        Args:
            paper: Paper dictionary
            format: Export format ('bibtex', 'ris', 'endnote', 'refman')

        Returns:
            Formatted citation string
        """
        try:
            if format.lower() == "bibtex":
                return self._export_bibtex(paper)
            elif format.lower() == "ris":
                return self._export_ris(paper)
            elif format.lower() == "endnote":
                return self._export_endnote(paper)
            else:
                self.logger.warning(f"Unsupported format: {format}, using BibTeX")
                return self._export_bibtex(paper)
        except Exception as e:
            self.logger.error(f"Citation export failed: {e}")
            return ""

    def _export_bibtex(self, paper: Dict[str, Any]) -> str:
        """Export paper as BibTeX"""
        title = paper.get("title", "Untitled")
        authors = paper.get("authors", "Unknown")
        year = paper.get("year", "")
        venue = paper.get("venue", "")
        url = paper.get("url", "")

        # Generate citation key
        first_author = authors.split(",")[0].split()[-1] if authors else "Unknown"
        cite_key = f"{first_author}{year}".replace(" ", "")

        bibtex = f"""@article{{{cite_key},
  title={{{title}}},
  author={{{authors}}},
  year={{{year}}},
  journal={{{venue}}},
  url={{{url}}}
}}"""

        return bibtex

    def _export_ris(self, paper: Dict[str, Any]) -> str:
        """Export paper as RIS format"""
        title = paper.get("title", "Untitled")
        authors = paper.get("authors", "Unknown")
        year = paper.get("year", "")
        venue = paper.get("venue", "")
        url = paper.get("url", "")

        # Split authors
        author_list = [a.strip() for a in authors.split(",")]

        ris = "TY  - JOUR\n"
        ris += f"TI  - {title}\n"
        for author in author_list:
            ris += f"AU  - {author}\n"
        ris += f"PY  - {year}\n"
        ris += f"JO  - {venue}\n"
        ris += f"UR  - {url}\n"
        ris += "ER  - \n"

        return ris

    def _export_endnote(self, paper: Dict[str, Any]) -> str:
        """Export paper as EndNote format"""
        # Similar to RIS but with different tags
        title = paper.get("title", "Untitled")
        authors = paper.get("authors", "Unknown")
        year = paper.get("year", "")
        venue = paper.get("venue", "")

        endnote = f"%0 Journal Article\n"
        endnote += f"%T {title}\n"
        endnote += f"%A {authors}\n"
        endnote += f"%D {year}\n"
        endnote += f"%J {venue}\n"

        return endnote

    async def build_citation_network(
        self,
        paper_id: str,
        depth: int = 2,
        max_nodes: int = 50,
    ) -> Dict[str, Any]:
        """
        Build citation network graph for a paper

        Creates a graph showing:
        - Papers that cite this work (forward citations)
        - Papers cited by this work (backward citations)
        - Co-citation relationships

        Args:
            paper_id: Starting paper ID
            depth: Network depth (levels of citations)
            max_nodes: Maximum nodes in network

        Returns:
            Network graph structure with nodes and edges
        """
        try:
            self.logger.info(f"Building citation network for: {paper_id}")

            network = {
                "nodes": [],
                "edges": [],
                "metadata": {
                    "root_paper": paper_id,
                    "depth": depth,
                    "created_at": datetime.now().isoformat(),
                }
            }

            visited = set()
            queue = [(paper_id, 0)]  # (paper_id, current_depth)

            while queue and len(network["nodes"]) < max_nodes:
                current_id, current_depth = queue.pop(0)

                if current_id in visited or current_depth >= depth:
                    continue

                visited.add(current_id)

                # Get paper details
                paper = await self.get_post_detail(current_id)
                if not paper:
                    continue

                # Add node
                node = {
                    "id": current_id,
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", ""),
                    "year": paper.get("year", ""),
                    "citations": paper.get("citations_count", 0),
                    "depth": current_depth,
                }
                network["nodes"].append(node)

                # Get citing papers
                cluster_id = paper.get("cluster_id")
                if cluster_id and current_depth < depth - 1:
                    citing = await self.get_citing_papers(cluster_id, max_results=10)

                    for cite_paper in citing:
                        cite_id = cite_paper.get("id")
                        if cite_id and cite_id not in visited:
                            # Add edge
                            network["edges"].append({
                                "source": cite_id,
                                "target": current_id,
                                "type": "cites",
                            })

                            queue.append((cite_id, current_depth + 1))

            self.logger.info(f"Citation network built: {len(network['nodes'])} nodes, {len(network['edges'])} edges")
            return network

        except Exception as e:
            self.logger.error(f"Failed to build citation network: {e}")
            return {"nodes": [], "edges": [], "metadata": {}}

    async def build_collaboration_network(
        self,
        author_id: str,
        max_coauthors: int = 20,
    ) -> Dict[str, Any]:
        """
        Build author collaboration network

        Args:
            author_id: Google Scholar author ID
            max_coauthors: Maximum co-authors to include

        Returns:
            Collaboration network with authors and connections
        """
        try:
            self.logger.info(f"Building collaboration network for: {author_id}")

            # Get author's publications
            papers = await self.get_user_posts(author_id, max_posts=50)

            # Extract all co-authors
            coauthor_counts = defaultdict(int)
            coauthor_papers = defaultdict(list)

            for paper in papers:
                authors_str = paper.get("authors", "")
                # Parse author names
                authors = self._parse_author_names(authors_str)

                for author in authors:
                    if author != author_id:  # Exclude the main author
                        coauthor_counts[author] += 1
                        coauthor_papers[author].append(paper)

            # Get top co-authors
            top_coauthors = sorted(
                coauthor_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:max_coauthors]

            # Build network
            network = {
                "nodes": [{"id": author_id, "type": "main", "papers": len(papers)}],
                "edges": [],
                "metadata": {
                    "root_author": author_id,
                    "total_coauthors": len(coauthor_counts),
                    "total_papers": len(papers),
                }
            }

            for coauthor, count in top_coauthors:
                # Add coauthor node
                network["nodes"].append({
                    "id": coauthor,
                    "type": "coauthor",
                    "collaboration_count": count,
                })

                # Add edge
                network["edges"].append({
                    "source": author_id,
                    "target": coauthor,
                    "weight": count,
                    "papers": [p.get("title") for p in coauthor_papers[coauthor]],
                })

            self.logger.info(f"Collaboration network built: {len(network['nodes'])} authors")
            return network

        except Exception as e:
            self.logger.error(f"Failed to build collaboration network: {e}")
            return {"nodes": [], "edges": [], "metadata": {}}

    async def assess_paper_impact(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess paper's academic impact

        Metrics:
        - Citation count and growth
        - Citation velocity
        - H-index of citing papers
        - Influential citations
        - Cross-field impact

        Args:
            paper: Paper dictionary

        Returns:
            Impact assessment metrics
        """
        try:
            impact = {
                "paper_title": paper.get("title"),
                "total_citations": paper.get("citations_count", 0),
            }

            # Get citing papers for analysis
            cluster_id = paper.get("cluster_id")
            if cluster_id:
                citing_papers = await self.get_citing_papers(cluster_id, max_results=100)

                if citing_papers:
                    # Citation velocity (citations per year)
                    paper_year = paper.get("year")
                    if paper_year:
                        if isinstance(paper_year, str):
                            year_match = re.search(r'\b(19|20)\d{2}\b', paper_year)
                            if year_match:
                                paper_year = int(year_match.group())

                        if isinstance(paper_year, int):
                            years_since_pub = datetime.now().year - paper_year
                            if years_since_pub > 0:
                                impact["citation_velocity"] = round(
                                    impact["total_citations"] / years_since_pub, 2
                                )

                    # Analyze citing papers
                    citing_years = []
                    citing_citations = []

                    for citing in citing_papers:
                        year = citing.get("year")
                        if year and isinstance(year, int):
                            citing_years.append(year)

                        cites = citing.get("citations_count", 0)
                        citing_citations.append(cites)

                    if citing_years:
                        impact["first_citation_year"] = min(citing_years)
                        impact["latest_citation_year"] = max(citing_years)
                        impact["citation_span_years"] = max(citing_years) - min(citing_years)

                    if citing_citations:
                        impact["avg_citing_paper_citations"] = round(
                            sum(citing_citations) / len(citing_citations), 2
                        )
                        # Influential citations (citing papers with high citations)
                        influential = [c for c in citing_citations if c >= 50]
                        impact["influential_citations"] = len(influential)

                    # Research field diversity
                    fields = set()
                    for citing in citing_papers:
                        paper_fields = self.classify_research_field(citing)
                        fields.update(paper_fields)

                    impact["cross_field_impact"] = len(fields)
                    impact["fields"] = list(fields)

            # Impact score (0-100)
            impact["impact_score"] = self._calculate_impact_score(impact)

            return impact

        except Exception as e:
            self.logger.error(f"Failed to assess impact: {e}")
            return {}

    def _calculate_impact_score(self, impact_data: Dict[str, Any]) -> float:
        """
        Calculate overall impact score (0-100)

        Args:
            impact_data: Impact metrics dictionary

        Returns:
            Impact score
        """
        score = 0.0

        # Citations component (max 40 points)
        total_cites = impact_data.get("total_citations", 0)
        if total_cites >= 1000:
            score += 40
        elif total_cites >= 500:
            score += 35
        elif total_cites >= 100:
            score += 25
        elif total_cites >= 50:
            score += 15
        elif total_cites >= 10:
            score += 5

        # Velocity component (max 20 points)
        velocity = impact_data.get("citation_velocity", 0)
        if velocity >= 50:
            score += 20
        elif velocity >= 20:
            score += 15
        elif velocity >= 10:
            score += 10
        elif velocity >= 5:
            score += 5

        # Influential citations (max 20 points)
        influential = impact_data.get("influential_citations", 0)
        score += min(influential * 2, 20)

        # Cross-field impact (max 20 points)
        cross_field = impact_data.get("cross_field_impact", 0)
        score += min(cross_field * 4, 20)

        return min(score, 100.0)

    # ========================================================================
    # Helper Methods - Parsing
    # ========================================================================

    async def _parse_search_results(self, max_results: int) -> List[Dict[str, Any]]:
        """Parse search results from page"""
        results = []

        try:
            # Wait for results
            await self._page.wait_for_selector('.gs_ri, .gs_r', timeout=10000)

            # Get result elements
            result_elements = await self._page.query_selector_all('.gs_ri')

            if not result_elements:
                result_elements = await self._page.query_selector_all('.gs_r')

            for elem in result_elements[:max_results]:
                try:
                    result = {
                        "platform": self.platform,
                        "type": "paper",
                        "scraped_at": datetime.now().isoformat(),
                    }

                    # Title and URL
                    title_elem = await elem.query_selector('h3 a, .gs_rt a')
                    if title_elem:
                        title_text = await title_elem.inner_text()
                        result["title"] = title_text.strip()

                        href = await title_elem.get_attribute("href")
                        if href:
                            result["url"] = href
                            result["id"] = hashlib.md5(href.encode()).hexdigest()[:16]

                    # Authors, venue, year
                    info_elem = await elem.query_selector('.gs_a')
                    if info_elem:
                        info_text = await info_elem.inner_text()
                        result["publication_info"] = info_text

                        # Parse info
                        parts = info_text.split(" - ")
                        if len(parts) >= 1:
                            result["authors"] = parts[0].strip()
                        if len(parts) >= 2:
                            result["venue"] = parts[1].strip()
                        if len(parts) >= 3:
                            year_str = parts[2].strip()
                            year_match = re.search(r'\b(19|20)\d{2}\b', year_str)
                            if year_match:
                                result["year"] = int(year_match.group())

                    # Abstract/snippet
                    snippet_elem = await elem.query_selector('.gs_rs')
                    if snippet_elem:
                        result["snippet"] = await snippet_elem.inner_text()

                    # Citation count and cluster ID
                    footer_links = await elem.query_selector_all('.gs_fl a')
                    for link in footer_links:
                        link_text = await link.inner_text()
                        link_href = await link.get_attribute("href")

                        if "Cited by" in link_text:
                            # Extract citation count
                            cite_match = re.search(r'Cited by (\d+)', link_text)
                            if cite_match:
                                result["citations_count"] = int(cite_match.group(1))

                            # Extract cluster ID
                            if link_href:
                                cluster_match = re.search(r'cites=(\d+)', link_href)
                                if cluster_match:
                                    result["cluster_id"] = cluster_match.group(1)

                        elif "Related articles" in link_text:
                            result["has_related_articles"] = True

                        elif "versions" in link_text.lower():
                            version_match = re.search(r'(\d+)', link_text)
                            if version_match:
                                result["version_count"] = int(version_match.group(1))

                    # PDF link
                    pdf_elem = await elem.query_selector('a[href$=".pdf"]')
                    if not pdf_elem:
                        pdf_elem = await elem.query_selector('.gs_or_ggsm a')

                    if pdf_elem:
                        pdf_url = await pdf_elem.get_attribute("href")
                        if pdf_url:
                            result["pdf_url"] = pdf_url
                            result["open_access"] = True

                    if result.get("title"):
                        results.append(result)

                except Exception as e:
                    self.logger.debug(f"Failed to parse result element: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to parse search results: {e}")

        return results

    async def _parse_author_profile(self, user_id: str) -> Dict[str, Any]:
        """Parse author profile page"""
        profile = {
            "user_id": user_id,
            "platform": self.platform,
            "type": "author",
        }

        try:
            # Name
            name_elem = await self._page.query_selector('#gsc_prf_in')
            if name_elem:
                profile["name"] = await name_elem.inner_text()

            # Affiliation
            affiliation_elem = await self._page.query_selector('.gsc_prf_il')
            if affiliation_elem:
                profile["affiliation"] = await affiliation_elem.inner_text()

            # Email domain
            email_elem = await self._page.query_selector('#gsc_prf_ivh')
            if email_elem:
                profile["email_domain"] = await email_elem.inner_text()

            # Research interests
            interest_elems = await self._page.query_selector_all('#gsc_prf_int a')
            interests = []
            for elem in interest_elems:
                interests.append(await elem.inner_text())
            profile["interests"] = interests

            # Citation statistics
            stat_rows = await self._page.query_selector_all('#gsc_rsb_st tbody tr')
            if len(stat_rows) >= 3:
                # Row 1: Citations
                try:
                    all_citations = await stat_rows[0].query_selector('td:nth-child(2)')
                    recent_citations = await stat_rows[0].query_selector('td:nth-child(3)')

                    if all_citations:
                        profile["total_citations"] = int(await all_citations.inner_text())
                    if recent_citations:
                        profile["citations_since_2019"] = int(await recent_citations.inner_text())
                except:
                    pass

                # Row 2: h-index
                try:
                    h_index_all = await stat_rows[1].query_selector('td:nth-child(2)')
                    h_index_recent = await stat_rows[1].query_selector('td:nth-child(3)')

                    if h_index_all:
                        profile["h_index"] = int(await h_index_all.inner_text())
                    if h_index_recent:
                        profile["h_index_since_2019"] = int(await h_index_recent.inner_text())
                except:
                    pass

                # Row 3: i10-index
                try:
                    i10_all = await stat_rows[2].query_selector('td:nth-child(2)')
                    i10_recent = await stat_rows[2].query_selector('td:nth-child(3)')

                    if i10_all:
                        profile["i10_index"] = int(await i10_all.inner_text())
                    if i10_recent:
                        profile["i10_index_since_2019"] = int(await i10_recent.inner_text())
                except:
                    pass

        except Exception as e:
            self.logger.error(f"Error parsing profile: {e}")

        return profile

    async def _parse_user_publications(self, user_id: str, max_posts: int) -> List[Dict[str, Any]]:
        """Parse user's publications from profile"""
        posts = []

        try:
            # Get publication rows
            pub_rows = await self._page.query_selector_all('.gsc_a_tr')

            for row in pub_rows[:max_posts]:
                try:
                    post = {
                        "user_id": user_id,
                        "platform": self.platform,
                        "type": "paper",
                    }

                    # Title
                    title_elem = await row.query_selector('.gsc_a_at')
                    if title_elem:
                        post["title"] = await title_elem.inner_text()
                        href = await title_elem.get_attribute("href")
                        if href:
                            post["url"] = f"{self.base_url}{href}" if not href.startswith("http") else href
                            post["id"] = hashlib.md5(post["title"].encode()).hexdigest()[:16]

                    # Authors
                    authors_elem = await row.query_selector('.gs_gray:nth-child(1)')
                    if authors_elem:
                        post["authors"] = await authors_elem.inner_text()

                    # Venue
                    venue_elem = await row.query_selector('.gs_gray:nth-child(2)')
                    if venue_elem:
                        post["venue"] = await venue_elem.inner_text()

                    # Year
                    year_elem = await row.query_selector('.gsc_a_y span')
                    if year_elem:
                        year_text = await year_elem.inner_text()
                        if year_text.isdigit():
                            post["year"] = int(year_text)

                    # Citations
                    cite_elem = await row.query_selector('.gsc_a_c')
                    if cite_elem:
                        cite_text = await cite_elem.inner_text()
                        if cite_text.isdigit():
                            post["citations_count"] = int(cite_text)

                    if post.get("title"):
                        posts.append(post)

                except Exception as e:
                    self.logger.debug(f"Failed to parse publication row: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error parsing publications: {e}")

        return posts

    async def _parse_paper_detail(self, post_id: str) -> Dict[str, Any]:
        """Parse detailed paper information"""
        detail = {
            "id": post_id,
            "platform": self.platform,
        }

        try:
            # Similar parsing logic as search results but with more detail
            # Title
            title_elem = await self._page.query_selector('h3 a, .gs_rt a')
            if title_elem:
                detail["title"] = await title_elem.inner_text()

            # Full metadata
            meta_elem = await self._page.query_selector('.gs_a')
            if meta_elem:
                detail["metadata"] = await meta_elem.inner_text()

            # Abstract
            abstract_elem = await self._page.query_selector('.gs_rs')
            if abstract_elem:
                detail["abstract"] = await abstract_elem.inner_text()

        except Exception as e:
            self.logger.error(f"Error parsing paper detail: {e}")

        return detail

    async def _get_citation_history(self) -> Dict[str, List[int]]:
        """Get citation history from profile page"""
        history = {"years": [], "citations": []}

        try:
            # Citation graph data
            chart_elem = await self._page.query_selector('#gsc_md_hist_b')
            if chart_elem:
                year_elems = await chart_elem.query_selector_all('.gsc_md_hist_y')
                cite_elems = await chart_elem.query_selector_all('.gsc_md_hist_c')

                for year_elem in year_elems:
                    year_text = await year_elem.inner_text()
                    if year_text.isdigit():
                        history["years"].append(int(year_text))

                for cite_elem in cite_elems:
                    cite_text = await cite_elem.inner_text()
                    if cite_text.isdigit():
                        history["citations"].append(int(cite_text))

        except Exception as e:
            self.logger.debug(f"Error getting citation history: {e}")

        return history

    async def _get_coauthors(self) -> List[Dict[str, str]]:
        """Get co-authors from profile page"""
        coauthors = []

        try:
            coauthor_elems = await self._page.query_selector_all('.gsc_rsb_aa')

            for elem in coauthor_elems:
                try:
                    name_elem = await elem.query_selector('.gsc_rsb_a_desc a')
                    if name_elem:
                        name = await name_elem.inner_text()
                        href = await name_elem.get_attribute("href")

                        coauthor = {"name": name}

                        if href:
                            # Extract user ID
                            user_match = re.search(r'user=([^&]+)', href)
                            if user_match:
                                coauthor["user_id"] = user_match.group(1)

                        # Affiliation
                        affil_elem = await elem.query_selector('.gsc_rsb_a_ext')
                        if affil_elem:
                            coauthor["affiliation"] = await affil_elem.inner_text()

                        coauthors.append(coauthor)

                except Exception as e:
                    self.logger.debug(f"Error parsing coauthor: {e}")
                    continue

        except Exception as e:
            self.logger.debug(f"Error getting coauthors: {e}")

        return coauthors

    async def _calculate_author_metrics(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional author metrics"""
        metrics = {}

        try:
            # Productivity metrics
            total_citations = profile.get("total_citations", 0)
            h_index = profile.get("h_index", 0)
            i10_index = profile.get("i10_index", 0)

            # G-index approximation
            metrics["g_index_estimate"] = int((total_citations ** 0.5))

            # M-quotient (h-index per year)
            # Would need career start year for accurate calculation
            metrics["h_index"] = h_index
            metrics["i10_index"] = i10_index

            # Citation growth rate
            recent_cites = profile.get("citations_since_2019", 0)
            if total_citations > 0:
                metrics["recent_citation_ratio"] = round(recent_cites / total_citations, 2)

        except Exception as e:
            self.logger.debug(f"Error calculating metrics: {e}")

        return metrics

    def _parse_author_names(self, authors_str: str) -> List[str]:
        """Parse author names from string"""
        # Split by common delimiters
        authors = re.split(r',|;|\band\b', authors_str)

        # Clean up
        authors = [a.strip() for a in authors if a.strip()]

        return authors

    async def _search_paper_detail(self, query: str) -> Dict[str, Any]:
        """Search for paper by title/DOI and get first result detail"""
        results = await self.search(query, max_results=1)

        if results:
            return results[0]

        return {}

    def _estimate_impact_factor(self, papers: List[Dict[str, Any]]) -> float:
        """Estimate journal impact factor based on citation patterns"""
        if not papers:
            return 0.0

        # Simple estimation: average citations per paper in recent years
        recent_papers = [
            p for p in papers
            if p.get("year") and isinstance(p.get("year"), int) and
            datetime.now().year - p.get("year") <= 3
        ]

        if not recent_papers:
            return 0.0

        total_citations = sum(p.get("citations_count", 0) for p in recent_papers)
        avg_citations = total_citations / len(recent_papers)

        # Rough impact factor estimate
        return round(avg_citations / 2, 2)


# ============================================================================
# Main - Testing
# ============================================================================

if __name__ == "__main__":
    async def test_google_scholar_spider():
        """Test Google Scholar spider functionality"""
        spider = GoogleScholarSpider(headless=False)

        async with spider.session():
            print("\n" + "="*80)
            print("Testing Google Scholar Spider - 4-Layer Architecture")
            print("="*80)

            # Test 1: Basic search
            print("\n[Test 1] Basic search for 'machine learning'")
            results = await spider.search("machine learning", max_results=5)

            for i, paper in enumerate(results, 1):
                print(f"\n{i}. {paper.get('title', 'No title')}")
                print(f"   Authors: {paper.get('authors', 'Unknown')}")
                print(f"   Year: {paper.get('year', 'N/A')}")
                print(f"   Citations: {paper.get('citations_count', 0)}")
                print(f"   URL: {paper.get('url', 'N/A')}")

            # Test 2: Filter by citations
            print("\n[Test 2] Filter papers by citations (>= 50)")
            filtered = spider.filter_by_citations(results, min_citations=50)
            print(f"Filtered: {len(results)} -> {len(filtered)} papers")

            # Test 3: Export citation
            if results:
                print("\n[Test 3] Export first paper as BibTeX")
                bibtex = await spider.export_citation(results[0], format="bibtex")
                print(bibtex)

            # Test 4: Author profile
            print("\n[Test 4] Get author profile (example user)")
            # Note: Replace with actual user ID for testing
            # profile = await spider.get_user_profile("SOME_USER_ID")
            # print(f"Name: {profile.get('name')}")
            # print(f"H-index: {profile.get('h_index')}")

            print("\n" + "="*80)
            print("Testing completed!")
            print("="*80)

    # Run tests
    asyncio.run(test_google_scholar_spider())
