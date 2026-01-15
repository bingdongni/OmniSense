"""
API utilities and helper functions
"""

from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import hashlib
import json


def generate_task_id(prefix: str = "task") -> str:
    """Generate unique task ID"""
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_hash(password: str, hashed: str) -> bool:
    """Verify password hash"""
    return hash_password(password) == hashed


def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO string"""
    return dt.isoformat()


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string"""
    return datetime.fromisoformat(dt_str)


def calculate_expiry(hours: int = 24) -> datetime:
    """Calculate expiry datetime"""
    return datetime.utcnow() + timedelta(hours=hours)


def mask_sensitive(data: str, show_chars: int = 4) -> str:
    """Mask sensitive data (API keys, tokens)"""
    if len(data) <= show_chars:
        return "*" * len(data)
    return data[:show_chars] + "*" * (len(data) - show_chars)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    import re
    # Remove path separators and special characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    return sanitized


def validate_platform(platform: str, supported_platforms: list) -> bool:
    """Validate if platform is supported"""
    return platform.lower() in [p.lower() for p in supported_platforms]


def format_error_response(error: Exception, include_trace: bool = False) -> Dict[str, Any]:
    """Format error response"""
    response = {
        "error": str(error),
        "type": type(error).__name__
    }

    if include_trace:
        import traceback
        response["traceback"] = traceback.format_exc()

    return response


def paginate_results(items: list, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Paginate list of items"""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": items[start:end],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": end < total,
            "has_prev": page > 1
        }
    }


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple configuration dictionaries"""
    result = {}
    for config in configs:
        result.update(config)
    return result


def compress_response(data: Any) -> bytes:
    """Compress response data"""
    import gzip
    json_str = json.dumps(data)
    return gzip.compress(json_str.encode())


def decompress_response(data: bytes) -> Any:
    """Decompress response data"""
    import gzip
    json_str = gzip.decompress(data).decode()
    return json.loads(json_str)


class RateLimitExceededError(Exception):
    """Rate limit exceeded exception"""
    pass


class TaskNotFoundError(Exception):
    """Task not found exception"""
    pass


class PlatformNotSupportedError(Exception):
    """Platform not supported exception"""
    pass


class InvalidAuthenticationError(Exception):
    """Invalid authentication exception"""
    pass
