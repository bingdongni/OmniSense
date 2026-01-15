"""
User Agent Rotation

Manages rotation of user agent strings with realistic browser profiles.
Supports Chrome, Firefox, Safari, Edge, and mobile browsers.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger

try:
    from fake_useragent import UserAgent
    FAKE_UA_AVAILABLE = True
except ImportError:
    FAKE_UA_AVAILABLE = False
    logger.warning("fake-useragent not available, using built-in user agents")


@dataclass
class UserAgentConfig:
    """Configuration for user agent rotation"""
    browser_types: List[str] = field(default_factory=lambda: ["chrome", "firefox", "safari", "edge"])
    include_mobile: bool = False
    os_types: List[str] = field(default_factory=lambda: ["windows", "macos", "linux"])
    use_fake_useragent: bool = True  # Use fake-useragent library if available
    fallback_to_builtin: bool = True


class UserAgentRotator:
    """
    Rotates user agent strings to avoid detection.

    Features:
    - Multiple browser types (Chrome, Firefox, Safari, Edge)
    - Desktop and mobile user agents
    - Multiple operating systems
    - Integration with fake-useragent library
    - Fallback to built-in user agents
    """

    # Built-in user agents by browser and OS
    BUILTIN_USER_AGENTS = {
        "chrome": {
            "windows": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            ],
            "macos": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
            "linux": [
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
        },
        "firefox": {
            "windows": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            ],
            "macos": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:121.0) Gecko/20100101 Firefox/121.0",
            ],
            "linux": [
                "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            ],
        },
        "safari": {
            "macos": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            ],
        },
        "edge": {
            "windows": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
            ],
            "macos": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            ],
        },
    }

    MOBILE_USER_AGENTS = {
        "chrome": [
            "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1",
        ],
        "safari": [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        ],
        "firefox": [
            "Mozilla/5.0 (Android 13; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
            "Mozilla/5.0 (Android 12; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/121.0 Mobile/15E148 Safari/605.1.15",
        ],
    }

    def __init__(self, config: Optional[UserAgentConfig] = None):
        """
        Initialize user agent rotator.

        Args:
            config: User agent configuration
        """
        self.config = config or UserAgentConfig()
        self._fake_ua: Optional[UserAgent] = None
        self.current_user_agent: Optional[str] = None

        # Initialize fake-useragent if available and enabled
        if self.config.use_fake_useragent and FAKE_UA_AVAILABLE:
            try:
                self._fake_ua = UserAgent()
                logger.info("Initialized with fake-useragent library")
            except Exception as e:
                logger.warning(f"Failed to initialize fake-useragent: {str(e)}")
                if not self.config.fallback_to_builtin:
                    raise

        logger.info(f"UserAgentRotator initialized with browsers: {self.config.browser_types}")

    def get_random_user_agent(self) -> str:
        """
        Get a random user agent string.

        Returns:
            User agent string
        """
        # Try fake-useragent first if available
        if self._fake_ua and self.config.use_fake_useragent:
            try:
                browser = random.choice(self.config.browser_types)
                user_agent = self._get_fake_ua_by_browser(browser)
                if user_agent:
                    self.current_user_agent = user_agent
                    return user_agent
            except Exception as e:
                logger.debug(f"Failed to get user agent from fake-useragent: {str(e)}")

        # Fallback to built-in user agents
        user_agent = self._get_builtin_user_agent()
        self.current_user_agent = user_agent
        return user_agent

    def _get_fake_ua_by_browser(self, browser: str) -> Optional[str]:
        """
        Get user agent from fake-useragent library.

        Args:
            browser: Browser type

        Returns:
            User agent string or None
        """
        if not self._fake_ua:
            return None

        try:
            if browser == "chrome":
                return self._fake_ua.chrome
            elif browser == "firefox":
                return self._fake_ua.firefox
            elif browser == "safari":
                return self._fake_ua.safari
            elif browser == "edge":
                return self._fake_ua.edge
            else:
                return self._fake_ua.random
        except Exception:
            return None

    def _get_builtin_user_agent(self) -> str:
        """
        Get user agent from built-in list.

        Returns:
            User agent string
        """
        # Check if should return mobile user agent
        if self.config.include_mobile and random.random() < 0.3:  # 30% mobile
            return self._get_mobile_user_agent()

        # Select browser
        browser = random.choice(self.config.browser_types)

        # Safari only works on macOS
        if browser == "safari":
            os_type = "macos"
        else:
            # Filter available OS for this browser
            available_os = [
                os for os in self.config.os_types
                if os in self.BUILTIN_USER_AGENTS.get(browser, {})
            ]

            if not available_os:
                # Fallback to chrome on windows if no match
                browser = "chrome"
                os_type = "windows"
            else:
                os_type = random.choice(available_os)

        # Get user agents for this browser/os combination
        user_agents = self.BUILTIN_USER_AGENTS.get(browser, {}).get(os_type, [])

        if not user_agents:
            # Final fallback to Chrome on Windows
            user_agents = self.BUILTIN_USER_AGENTS["chrome"]["windows"]

        return random.choice(user_agents)

    def _get_mobile_user_agent(self) -> str:
        """
        Get mobile user agent.

        Returns:
            Mobile user agent string
        """
        # Filter browsers that have mobile variants
        available_browsers = [
            b for b in self.config.browser_types
            if b in self.MOBILE_USER_AGENTS
        ]

        if not available_browsers:
            available_browsers = ["chrome"]

        browser = random.choice(available_browsers)
        user_agents = self.MOBILE_USER_AGENTS[browser]

        return random.choice(user_agents)

    def get_user_agent_by_browser(self, browser: str, mobile: bool = False) -> str:
        """
        Get user agent for specific browser.

        Args:
            browser: Browser type (chrome, firefox, safari, edge)
            mobile: Whether to get mobile user agent

        Returns:
            User agent string
        """
        if mobile:
            user_agents = self.MOBILE_USER_AGENTS.get(browser, self.MOBILE_USER_AGENTS["chrome"])
            user_agent = random.choice(user_agents)
        else:
            # Try fake-useragent first
            if self._fake_ua and self.config.use_fake_useragent:
                try:
                    user_agent = self._get_fake_ua_by_browser(browser)
                    if user_agent:
                        self.current_user_agent = user_agent
                        return user_agent
                except Exception:
                    pass

            # Fallback to built-in
            browser_uas = self.BUILTIN_USER_AGENTS.get(browser)
            if not browser_uas:
                browser_uas = self.BUILTIN_USER_AGENTS["chrome"]

            # Get first available OS
            os_type = list(browser_uas.keys())[0]
            user_agents = browser_uas[os_type]
            user_agent = random.choice(user_agents)

        self.current_user_agent = user_agent
        return user_agent

    def parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """
        Parse user agent string to extract browser and OS info.

        Args:
            user_agent: User agent string

        Returns:
            Dictionary with browser and OS information
        """
        info = {
            "browser": "unknown",
            "browser_version": "unknown",
            "os": "unknown",
            "os_version": "unknown",
            "mobile": False,
        }

        ua_lower = user_agent.lower()

        # Detect browser
        if "edg/" in ua_lower or "edge/" in ua_lower:
            info["browser"] = "edge"
        elif "chrome/" in ua_lower and "safari/" in ua_lower:
            info["browser"] = "chrome"
        elif "firefox/" in ua_lower:
            info["browser"] = "firefox"
        elif "safari/" in ua_lower and "chrome/" not in ua_lower:
            info["browser"] = "safari"

        # Detect OS
        if "windows" in ua_lower:
            info["os"] = "windows"
            if "windows nt 10.0" in ua_lower:
                info["os_version"] = "10/11"
        elif "mac os x" in ua_lower or "macintosh" in ua_lower:
            info["os"] = "macos"
        elif "linux" in ua_lower:
            info["os"] = "linux"
        elif "android" in ua_lower:
            info["os"] = "android"
            info["mobile"] = True
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            info["os"] = "ios"
            info["mobile"] = True

        # Detect mobile
        if "mobile" in ua_lower or "android" in ua_lower:
            info["mobile"] = True

        return info

    def get_stats(self) -> Dict[str, any]:
        """
        Get user agent statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "current_user_agent": self.current_user_agent,
            "using_fake_ua": self._fake_ua is not None,
            "browser_types": self.config.browser_types,
            "include_mobile": self.config.include_mobile,
        }


# Utility functions
def is_mobile_user_agent(user_agent: str) -> bool:
    """
    Check if user agent is mobile.

    Args:
        user_agent: User agent string

    Returns:
        True if mobile, False otherwise
    """
    mobile_keywords = ["mobile", "android", "iphone", "ipad", "ipod", "blackberry", "windows phone"]
    ua_lower = user_agent.lower()
    return any(keyword in ua_lower for keyword in mobile_keywords)


def get_browser_from_user_agent(user_agent: str) -> str:
    """
    Extract browser name from user agent.

    Args:
        user_agent: User agent string

    Returns:
        Browser name (chrome, firefox, safari, edge, or unknown)
    """
    ua_lower = user_agent.lower()

    if "edg/" in ua_lower or "edge/" in ua_lower:
        return "edge"
    elif "chrome/" in ua_lower and "safari/" in ua_lower:
        return "chrome"
    elif "firefox/" in ua_lower:
        return "firefox"
    elif "safari/" in ua_lower and "chrome/" not in ua_lower:
        return "safari"
    else:
        return "unknown"


def get_latest_user_agents() -> Dict[str, str]:
    """
    Get the latest user agents for each major browser.

    Returns:
        Dictionary mapping browser to latest user agent
    """
    return {
        "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    }
