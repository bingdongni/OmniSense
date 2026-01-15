"""
Pytest configuration and fixtures for OmniSense test suite
Provides shared fixtures, mocks, and test utilities
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
import sqlite3
import json

# Mock Playwright to avoid browser dependencies in tests
import sys
from unittest.mock import MagicMock

# Mock playwright before imports
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()

from omnisense.config import Config, DatabaseConfig, SpiderConfig, AntiCrawlConfig
from omnisense.storage.database import DatabaseManager
from omnisense.utils.logger import get_logger


# ==================== Pytest Configuration ====================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_llm: Tests requiring LLM")
    config.addinivalue_line("markers", "requires_browser: Tests requiring browser")
    config.addinivalue_line("markers", "requires_network: Tests requiring network")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Configuration Fixtures ====================

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_config(temp_dir):
    """Create test configuration"""
    config = Config(
        debug=True,
        log_level="DEBUG",
        data_dir=temp_dir / "data",
        cache_dir=temp_dir / "cache",
        log_file=str(temp_dir / "logs" / "test.log"),
        database=DatabaseConfig(
            sqlite_path=str(temp_dir / "data" / "test.db"),
            chroma_path=str(temp_dir / "data" / "chroma"),
        ),
        spider=SpiderConfig(
            concurrent_tasks=2,
            timeout=5,
            download_media=False,
        ),
        anti_crawl=AntiCrawlConfig(
            max_retries=2,
            request_delay_min=0.1,
            request_delay_max=0.2,
        ),
    )
    return config


@pytest.fixture
def mock_config(temp_dir):
    """Create mock configuration with minimal dependencies"""
    return {
        "data_dir": temp_dir / "data",
        "cache_dir": temp_dir / "cache",
        "log_file": str(temp_dir / "logs" / "test.log"),
        "debug": True,
        "log_level": "DEBUG",
    }


# ==================== Database Fixtures ====================

@pytest.fixture
async def test_db(temp_dir):
    """Create test database instance"""
    db_path = temp_dir / "test.db"

    # Create database with schema
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        # Collections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                collection_id TEXT UNIQUE NOT NULL,
                keyword TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Content table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                content_id TEXT NOT NULL,
                title TEXT,
                description TEXT,
                author_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, content_id)
            )
        """)

        conn.commit()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_content_data():
    """Sample content data for testing"""
    return [
        {
            "content_id": "test_001",
            "platform": "douyin",
            "content_type": "video",
            "title": "Test Video 1",
            "description": "This is a test video",
            "author": {"user_id": "user_001", "name": "Test User 1"},
            "publish_time": "2024-01-01 12:00:00",
            "stats": {
                "views": 1000,
                "likes": 100,
                "comments": 10,
                "shares": 5,
            },
            "tags": ["test", "video"],
            "media_urls": ["https://example.com/video1.mp4"],
        },
        {
            "content_id": "test_002",
            "platform": "douyin",
            "content_type": "video",
            "title": "Test Video 2",
            "description": "Another test video",
            "author": {"user_id": "user_002", "name": "Test User 2"},
            "publish_time": "2024-01-02 12:00:00",
            "stats": {
                "views": 2000,
                "likes": 200,
                "comments": 20,
                "shares": 10,
            },
            "tags": ["test", "sample"],
            "media_urls": ["https://example.com/video2.mp4"],
        },
    ]


# ==================== Spider Fixtures ====================

@pytest.fixture
def mock_browser():
    """Mock Playwright browser"""
    browser = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()

    # Setup page mock methods
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()
    page.evaluate = AsyncMock(return_value=1000)
    page.text_content = AsyncMock(return_value="Test content")
    page.get_attribute = AsyncMock(return_value="test-attr")
    page.screenshot = AsyncMock()
    page.close = AsyncMock()

    # Setup context mock
    context.new_page = AsyncMock(return_value=page)
    context.cookies = AsyncMock(return_value=[])
    context.add_cookies = AsyncMock()
    context.close = AsyncMock()

    # Setup browser mock
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()

    return {"browser": browser, "context": context, "page": page}


@pytest.fixture
def mock_playwright(mock_browser):
    """Mock Playwright instance"""
    playwright = AsyncMock()
    playwright.chromium.launch = AsyncMock(return_value=mock_browser["browser"])
    playwright.stop = AsyncMock()

    return playwright


# ==================== Anti-Crawl Fixtures ====================

@pytest.fixture
def mock_proxy_pool():
    """Mock proxy pool"""
    return {
        "proxies": [
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
            "http://proxy3.example.com:8080",
        ],
        "current_index": 0,
        "failed": set(),
    }


@pytest.fixture
def mock_user_agents():
    """Mock user agent list"""
    return [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
    ]


@pytest.fixture
def mock_fingerprint():
    """Mock browser fingerprint"""
    return {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "platform": "Win32",
        "vendor": "Google Inc.",
        "webgl_vendor": "Intel Inc.",
        "webgl_renderer": "Intel Iris OpenGL Engine",
        "languages": ["en-US", "en"],
        "screen": {"width": 1920, "height": 1080, "color_depth": 24},
        "timezone": "America/New_York",
    }


# ==================== Matcher Fixtures ====================

@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model"""
    mock_model = Mock()
    mock_model.encode = Mock(return_value=[[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]])
    return mock_model


@pytest.fixture
def sample_matching_criteria():
    """Sample matching criteria for tests"""
    return {
        "keywords": ["test", "sample", "demo"],
        "semantic_query": "This is a test query",
        "similarity_threshold": 0.85,
    }


# ==================== Analysis Fixtures ====================

@pytest.fixture
def mock_sentiment_model():
    """Mock sentiment analysis model"""
    mock_pipeline = Mock()
    mock_pipeline.return_value = [{"label": "POSITIVE", "score": 0.95}]
    return mock_pipeline


@pytest.fixture
def sample_analysis_data():
    """Sample data for analysis"""
    return [
        {
            "title": "Great product! Highly recommended",
            "description": "I love this product. It works perfectly.",
            "stats": {"likes": 100, "views": 1000},
            "publish_time": "2024-01-01T10:00:00",
        },
        {
            "title": "Terrible experience, very disappointed",
            "description": "This product is awful. Don't buy it.",
            "stats": {"likes": 5, "views": 200},
            "publish_time": "2024-01-02T10:00:00",
        },
        {
            "title": "It's okay, nothing special",
            "description": "Average product. Could be better.",
            "stats": {"likes": 50, "views": 500},
            "publish_time": "2024-01-03T10:00:00",
        },
    ]


# ==================== Agent Fixtures ====================

@pytest.fixture
def mock_llm():
    """Mock LLM for agent testing"""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value="This is a test response from the LLM.")
    mock.invoke = Mock(return_value="This is a test response from the LLM.")
    return mock


@pytest.fixture
def mock_agent_config():
    """Mock agent configuration"""
    from omnisense.agents.base import AgentConfig, AgentRole

    return AgentConfig(
        name="test_agent",
        role=AgentRole.ANALYST,
        llm_provider="ollama",
        llm_model="qwen2.5:7b",
        temperature=0.7,
        max_tokens=1024,
        max_retries=2,
        timeout=30,
        enable_memory=False,
        enable_cot=False,
    )


# ==================== API Fixtures ====================

@pytest.fixture
def mock_omnisense_instance():
    """Mock OmniSense instance for API testing"""
    mock = Mock()
    mock.collect = AsyncMock(return_value={
        "platform": "douyin",
        "count": 10,
        "data": [],
    })
    mock.analyze = AsyncMock(return_value={
        "sentiment": {"positive": 0.6, "neutral": 0.3, "negative": 0.1},
        "clusters": {"n_clusters": 3, "topics": ["topic1", "topic2", "topic3"]},
    })
    mock.db = Mock()
    mock.db.get_statistics = AsyncMock(return_value={
        "total_content": 100,
        "total_interactions": 500,
        "total_collections": 10,
    })
    return mock


# ==================== Interaction Fixtures ====================

@pytest.fixture
def sample_interactions():
    """Sample interaction data"""
    return [
        {
            "interaction_id": "comment_001",
            "type": "comment",
            "user": {"user_id": "user_001", "name": "Commenter 1"},
            "text": "Great content!",
            "timestamp": "2024-01-01 13:00:00",
            "like_count": 10,
            "reply_count": 2,
        },
        {
            "interaction_id": "comment_002",
            "type": "comment",
            "user": {"user_id": "user_002", "name": "Commenter 2"},
            "text": "Thanks for sharing",
            "timestamp": "2024-01-01 14:00:00",
            "like_count": 5,
            "reply_count": 0,
        },
    ]


# ==================== Utility Fixtures ====================

@pytest.fixture
def sample_json_file(temp_dir):
    """Create sample JSON file for testing"""
    json_path = temp_dir / "sample.json"
    data = {"test": "data", "items": [1, 2, 3]}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return json_path


@pytest.fixture
def mock_logger():
    """Mock logger instance"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


# ==================== Performance Testing Fixtures ====================

@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests"""
    import time

    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.metrics = {}

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()
            return self.end_time - self.start_time

        def record_metric(self, name: str, value: float):
            self.metrics[name] = value

        def get_metrics(self) -> Dict[str, float]:
            return self.metrics

    return PerformanceTracker()


# ==================== Cleanup Fixtures ====================

@pytest.fixture(autouse=True)
def cleanup_after_test(temp_dir):
    """Cleanup after each test"""
    yield
    # Cleanup is handled by temp_dir fixture


# ==================== Parametrize Helpers ====================

def pytest_generate_tests(metafunc):
    """Generate parametrized tests"""
    if "platform_name" in metafunc.fixturenames:
        platforms = ["douyin", "xiaohongshu", "weibo", "bilibili"]
        metafunc.parametrize("platform_name", platforms)


# ==================== Mock Data Generators ====================

def generate_mock_content(count: int, platform: str = "douyin") -> List[Dict[str, Any]]:
    """Generate mock content data"""
    return [
        {
            "content_id": f"test_{i:03d}",
            "platform": platform,
            "title": f"Test Content {i}",
            "description": f"Description for test content {i}",
            "author": {"user_id": f"user_{i}", "name": f"User {i}"},
            "stats": {
                "views": i * 100,
                "likes": i * 10,
                "comments": i,
                "shares": i // 2,
            },
        }
        for i in range(1, count + 1)
    ]


def generate_mock_interactions(count: int) -> List[Dict[str, Any]]:
    """Generate mock interaction data"""
    return [
        {
            "interaction_id": f"interaction_{i:03d}",
            "type": "comment",
            "user": {"user_id": f"user_{i}", "name": f"User {i}"},
            "text": f"Comment text {i}",
            "like_count": i,
        }
        for i in range(1, count + 1)
    ]


# Export test data generators
__all__ = [
    "generate_mock_content",
    "generate_mock_interactions",
]
