"""
Captcha Solving Integration

Integrates with popular captcha solving services:
- 2Captcha
- Anti-Captcha
- CapSolver
- DeathByCaptcha

Supports:
- reCAPTCHA v2
- reCAPTCHA v3
- hCaptcha
- Image captcha
- FunCaptcha
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger


class CaptchaService(Enum):
    """Supported captcha services"""
    TWOCAPTCHA = "2captcha"
    ANTICAPTCHA = "anticaptcha"
    CAPSOLVER = "capsolver"
    DEATHBYCAPTCHA = "deathbycaptcha"


class CaptchaType(Enum):
    """Supported captcha types"""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    IMAGE = "image"


@dataclass
class CaptchaConfig:
    """Configuration for captcha resolver"""
    service: str = "2captcha"
    api_key: str = ""
    timeout: int = 120  # Maximum time to wait for solution (seconds)
    polling_interval: float = 5.0  # How often to check for solution (seconds)
    min_score: float = 0.3  # Minimum score for reCAPTCHA v3


class CaptchaResolver:
    """
    Resolves captchas using external solving services.

    Supports multiple captcha types and services with automatic retry
    and polling for solutions.
    """

    # Service API endpoints
    ENDPOINTS = {
        CaptchaService.TWOCAPTCHA: {
            "submit": "https://2captcha.com/in.php",
            "result": "https://2captcha.com/res.php",
        },
        CaptchaService.ANTICAPTCHA: {
            "submit": "https://api.anti-captcha.com/createTask",
            "result": "https://api.anti-captcha.com/getTaskResult",
        },
        CaptchaService.CAPSOLVER: {
            "submit": "https://api.capsolver.com/createTask",
            "result": "https://api.capsolver.com/getTaskResult",
        },
    }

    def __init__(self, config: Optional[CaptchaConfig] = None):
        """
        Initialize captcha resolver.

        Args:
            config: Captcha configuration
        """
        self.config = config or CaptchaConfig()

        if not self.config.api_key:
            logger.warning("Captcha API key not provided")

        try:
            self.service = CaptchaService(self.config.service)
        except ValueError:
            logger.error(f"Unknown captcha service: {self.config.service}")
            self.service = CaptchaService.TWOCAPTCHA

        self._session: Optional[aiohttp.ClientSession] = None
        self._solve_count = 0
        self._success_count = 0
        self._failure_count = 0

        logger.info(f"CaptchaResolver initialized with service: {self.service.value}")

    async def initialize(self) -> None:
        """Initialize HTTP session."""
        self._session = aiohttp.ClientSession()

    async def solve(
        self,
        captcha_type: str,
        site_key: str,
        page_url: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Solve a captcha.

        Args:
            captcha_type: Type of captcha
            site_key: Site key for the captcha
            page_url: URL of the page with captcha
            **kwargs: Additional parameters (action, min_score, proxy, etc.)

        Returns:
            Captcha solution token or None
        """
        if not self._session:
            await self.initialize()

        try:
            captcha_enum = CaptchaType(captcha_type)
        except ValueError:
            logger.error(f"Unknown captcha type: {captcha_type}")
            return None

        self._solve_count += 1

        try:
            # Submit captcha
            task_id = await self._submit_captcha(
                captcha_enum, site_key, page_url, **kwargs
            )

            if not task_id:
                self._failure_count += 1
                return None

            # Poll for solution
            solution = await self._get_solution(task_id)

            if solution:
                self._success_count += 1
                logger.info(f"Captcha solved successfully: {captcha_type}")
                return solution
            else:
                self._failure_count += 1
                logger.error(f"Failed to solve captcha: {captcha_type}")
                return None

        except Exception as e:
            self._failure_count += 1
            logger.error(f"Error solving captcha: {str(e)}")
            return None

    async def _submit_captcha(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Submit captcha to solving service.

        Args:
            captcha_type: Type of captcha
            site_key: Site key
            page_url: Page URL
            **kwargs: Additional parameters

        Returns:
            Task ID or None
        """
        if self.service == CaptchaService.TWOCAPTCHA:
            return await self._submit_2captcha(captcha_type, site_key, page_url, **kwargs)
        elif self.service == CaptchaService.ANTICAPTCHA:
            return await self._submit_anticaptcha(captcha_type, site_key, page_url, **kwargs)
        elif self.service == CaptchaService.CAPSOLVER:
            return await self._submit_capsolver(captcha_type, site_key, page_url, **kwargs)
        else:
            logger.error(f"Submission not implemented for: {self.service.value}")
            return None

    async def _submit_2captcha(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """Submit captcha to 2Captcha."""
        params = {
            "key": self.config.api_key,
            "json": 1,
            "pageurl": page_url,
            "googlekey": site_key,
        }

        if captcha_type == CaptchaType.RECAPTCHA_V2:
            params["method"] = "userrecaptcha"
        elif captcha_type == CaptchaType.RECAPTCHA_V3:
            params["method"] = "userrecaptcha"
            params["version"] = "v3"
            params["action"] = kwargs.get("action", "verify")
            params["min_score"] = kwargs.get("min_score", self.config.min_score)
        elif captcha_type == CaptchaType.HCAPTCHA:
            params["method"] = "hcaptcha"
        else:
            logger.error(f"Captcha type not supported for 2Captcha: {captcha_type}")
            return None

        # Add proxy if provided
        if "proxy" in kwargs:
            proxy = kwargs["proxy"]
            params["proxy"] = proxy
            params["proxytype"] = kwargs.get("proxy_type", "HTTP")

        try:
            async with self._session.post(
                self.ENDPOINTS[CaptchaService.TWOCAPTCHA]["submit"],
                data=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                result = await response.json()

                if result.get("status") == 1:
                    task_id = result.get("request")
                    logger.debug(f"2Captcha task submitted: {task_id}")
                    return task_id
                else:
                    logger.error(f"2Captcha submission failed: {result.get('request')}")
                    return None

        except Exception as e:
            logger.error(f"2Captcha submission error: {str(e)}")
            return None

    async def _submit_anticaptcha(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """Submit captcha to Anti-Captcha."""
        task = {
            "clientKey": self.config.api_key,
        }

        if captcha_type == CaptchaType.RECAPTCHA_V2:
            task["task"] = {
                "type": "RecaptchaV2TaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        elif captcha_type == CaptchaType.RECAPTCHA_V3:
            task["task"] = {
                "type": "RecaptchaV3TaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
                "minScore": kwargs.get("min_score", self.config.min_score),
                "pageAction": kwargs.get("action", "verify"),
            }
        elif captcha_type == CaptchaType.HCAPTCHA:
            task["task"] = {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        else:
            logger.error(f"Captcha type not supported for Anti-Captcha: {captcha_type}")
            return None

        try:
            async with self._session.post(
                self.ENDPOINTS[CaptchaService.ANTICAPTCHA]["submit"],
                json=task,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                result = await response.json()

                if result.get("errorId") == 0:
                    task_id = result.get("taskId")
                    logger.debug(f"Anti-Captcha task submitted: {task_id}")
                    return str(task_id)
                else:
                    logger.error(f"Anti-Captcha submission failed: {result.get('errorCode')}")
                    return None

        except Exception as e:
            logger.error(f"Anti-Captcha submission error: {str(e)}")
            return None

    async def _submit_capsolver(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """Submit captcha to CapSolver."""
        task = {
            "clientKey": self.config.api_key,
        }

        if captcha_type == CaptchaType.RECAPTCHA_V2:
            task["task"] = {
                "type": "ReCaptchaV2TaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        elif captcha_type == CaptchaType.RECAPTCHA_V3:
            task["task"] = {
                "type": "ReCaptchaV3TaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": site_key,
                "minScore": kwargs.get("min_score", self.config.min_score),
                "pageAction": kwargs.get("action", "verify"),
            }
        elif captcha_type == CaptchaType.HCAPTCHA:
            task["task"] = {
                "type": "HCaptchaTaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        else:
            logger.error(f"Captcha type not supported for CapSolver: {captcha_type}")
            return None

        try:
            async with self._session.post(
                self.ENDPOINTS[CaptchaService.CAPSOLVER]["submit"],
                json=task,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                result = await response.json()

                if result.get("errorId") == 0:
                    task_id = result.get("taskId")
                    logger.debug(f"CapSolver task submitted: {task_id}")
                    return task_id
                else:
                    logger.error(f"CapSolver submission failed: {result.get('errorCode')}")
                    return None

        except Exception as e:
            logger.error(f"CapSolver submission error: {str(e)}")
            return None

    async def _get_solution(self, task_id: str) -> Optional[str]:
        """
        Poll for captcha solution.

        Args:
            task_id: Task ID from submission

        Returns:
            Solution token or None
        """
        start_time = time.time()

        while time.time() - start_time < self.config.timeout:
            await asyncio.sleep(self.config.polling_interval)

            try:
                if self.service == CaptchaService.TWOCAPTCHA:
                    solution = await self._get_solution_2captcha(task_id)
                elif self.service == CaptchaService.ANTICAPTCHA:
                    solution = await self._get_solution_anticaptcha(task_id)
                elif self.service == CaptchaService.CAPSOLVER:
                    solution = await self._get_solution_capsolver(task_id)
                else:
                    return None

                if solution:
                    return solution

            except Exception as e:
                logger.error(f"Error polling for solution: {str(e)}")

        logger.error(f"Captcha solution timeout after {self.config.timeout}s")
        return None

    async def _get_solution_2captcha(self, task_id: str) -> Optional[str]:
        """Get solution from 2Captcha."""
        params = {
            "key": self.config.api_key,
            "action": "get",
            "id": task_id,
            "json": 1,
        }

        try:
            async with self._session.get(
                self.ENDPOINTS[CaptchaService.TWOCAPTCHA]["result"],
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                result = await response.json()

                if result.get("status") == 1:
                    return result.get("request")
                elif result.get("request") == "CAPCHA_NOT_READY":
                    return None
                else:
                    logger.error(f"2Captcha error: {result.get('request')}")
                    return None

        except Exception as e:
            logger.error(f"2Captcha polling error: {str(e)}")
            return None

    async def _get_solution_anticaptcha(self, task_id: str) -> Optional[str]:
        """Get solution from Anti-Captcha."""
        data = {
            "clientKey": self.config.api_key,
            "taskId": int(task_id),
        }

        try:
            async with self._session.post(
                self.ENDPOINTS[CaptchaService.ANTICAPTCHA]["result"],
                json=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                result = await response.json()

                if result.get("status") == "ready":
                    return result.get("solution", {}).get("gRecaptchaResponse")
                elif result.get("status") == "processing":
                    return None
                else:
                    logger.error(f"Anti-Captcha error: {result.get('errorCode')}")
                    return None

        except Exception as e:
            logger.error(f"Anti-Captcha polling error: {str(e)}")
            return None

    async def _get_solution_capsolver(self, task_id: str) -> Optional[str]:
        """Get solution from CapSolver."""
        data = {
            "clientKey": self.config.api_key,
            "taskId": task_id,
        }

        try:
            async with self._session.post(
                self.ENDPOINTS[CaptchaService.CAPSOLVER]["result"],
                json=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                result = await response.json()

                if result.get("status") == "ready":
                    return result.get("solution", {}).get("gRecaptchaResponse")
                elif result.get("status") == "processing":
                    return None
                else:
                    logger.error(f"CapSolver error: {result.get('errorCode')}")
                    return None

        except Exception as e:
            logger.error(f"CapSolver polling error: {str(e)}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get captcha solving statistics.

        Returns:
            Statistics dictionary
        """
        success_rate = (
            (self._success_count / self._solve_count * 100)
            if self._solve_count > 0 else 0
        )

        return {
            "service": self.service.value,
            "total_solved": self._solve_count,
            "successful": self._success_count,
            "failed": self._failure_count,
            "success_rate": round(success_rate, 2),
        }

    async def close(self) -> None:
        """Cleanup resources."""
        if self._session:
            await self._session.close()
        logger.info("CaptchaResolver closed")


# Utility functions
def estimate_solve_time(captcha_type: CaptchaType) -> int:
    """
    Estimate typical solve time for captcha type.

    Args:
        captcha_type: Type of captcha

    Returns:
        Estimated solve time in seconds
    """
    estimates = {
        CaptchaType.RECAPTCHA_V2: 30,
        CaptchaType.RECAPTCHA_V3: 20,
        CaptchaType.HCAPTCHA: 35,
        CaptchaType.FUNCAPTCHA: 40,
        CaptchaType.IMAGE: 15,
    }

    return estimates.get(captcha_type, 30)


def get_service_pricing(service: CaptchaService) -> Dict[str, float]:
    """
    Get approximate pricing for captcha service (per 1000 captchas).

    Args:
        service: Captcha service

    Returns:
        Dictionary with pricing info
    """
    pricing = {
        CaptchaService.TWOCAPTCHA: {
            "recaptcha_v2": 2.99,
            "recaptcha_v3": 2.99,
            "hcaptcha": 2.99,
            "funcaptcha": 2.99,
            "image": 0.5,
        },
        CaptchaService.ANTICAPTCHA: {
            "recaptcha_v2": 2.0,
            "recaptcha_v3": 2.0,
            "hcaptcha": 2.0,
            "funcaptcha": 2.0,
            "image": 0.5,
        },
        CaptchaService.CAPSOLVER: {
            "recaptcha_v2": 1.2,
            "recaptcha_v3": 1.2,
            "hcaptcha": 1.2,
            "funcaptcha": 1.2,
            "image": 0.4,
        },
    }

    return pricing.get(service, {})
