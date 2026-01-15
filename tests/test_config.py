"""
Tests for configuration management
Tests Config class, sub-configurations, and environment variable loading
"""

import pytest
import os
import tempfile
from pathlib import Path
from pydantic import ValidationError

from omnisense.config import (
    Config,
    DatabaseConfig,
    StorageConfig,
    ProxyConfig,
    AntiCrawlConfig,
    SpiderConfig,
    MatcherConfig,
    AnalysisConfig,
    AgentConfig,
    PlatformConfig,
)


class TestDatabaseConfig:
    """Test DatabaseConfig class"""

    def test_default_values(self):
        """Test default configuration values"""
        config = DatabaseConfig()
        assert config.sqlite_path == "data/omnisense.db"
        assert config.chroma_path == "data/chroma"
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_db == 0
        assert config.redis_password is None

    def test_custom_values(self):
        """Test custom configuration values"""
        config = DatabaseConfig(
            sqlite_path="custom/path.db",
            redis_host="custom-host",
            redis_port=6380,
            redis_password="secret",
        )
        assert config.sqlite_path == "custom/path.db"
        assert config.redis_host == "custom-host"
        assert config.redis_port == 6380
        assert config.redis_password == "secret"

    def test_validation(self):
        """Test configuration validation"""
        with pytest.raises(ValidationError):
            DatabaseConfig(redis_port="invalid")  # Should be int

        with pytest.raises(ValidationError):
            DatabaseConfig(redis_db=-1)  # Should be non-negative


class TestSpiderConfig:
    """Test SpiderConfig class"""

    def test_default_values(self):
        """Test default spider configuration"""
        config = SpiderConfig()
        assert config.concurrent_tasks == 5
        assert config.timeout == 30
        assert config.download_media is True
        assert "jpg" in config.media_formats
        assert "mp4" in config.media_formats

    def test_custom_values(self):
        """Test custom spider configuration"""
        config = SpiderConfig(
            concurrent_tasks=10,
            timeout=60,
            download_media=False,
            media_formats=["png"],
        )
        assert config.concurrent_tasks == 10
        assert config.timeout == 60
        assert config.download_media is False
        assert config.media_formats == ["png"]

    def test_validation(self):
        """Test spider configuration validation"""
        with pytest.raises(ValidationError):
            SpiderConfig(concurrent_tasks=0)  # Should be positive

        with pytest.raises(ValidationError):
            SpiderConfig(timeout=-1)  # Should be positive


class TestAntiCrawlConfig:
    """Test AntiCrawlConfig class"""

    def test_default_values(self):
        """Test default anti-crawl configuration"""
        config = AntiCrawlConfig()
        assert config.user_agent_rotation is True
        assert config.fingerprint_random is True
        assert config.request_delay_min == 1.0
        assert config.request_delay_max == 5.0
        assert config.max_retries == 3

    def test_delay_validation(self):
        """Test delay configuration validation"""
        # Valid configuration
        config = AntiCrawlConfig(request_delay_min=2.0, request_delay_max=5.0)
        assert config.request_delay_min == 2.0
        assert config.request_delay_max == 5.0

    def test_retry_validation(self):
        """Test retry configuration validation"""
        config = AntiCrawlConfig(max_retries=5)
        assert config.max_retries == 5

        with pytest.raises(ValidationError):
            AntiCrawlConfig(max_retries=-1)  # Should be non-negative


class TestProxyConfig:
    """Test ProxyConfig class"""

    def test_default_values(self):
        """Test default proxy configuration"""
        config = ProxyConfig()
        assert config.enabled is False
        assert config.http_proxy is None
        assert config.https_proxy is None
        assert config.proxy_pool_enabled is False

    def test_custom_proxy(self):
        """Test custom proxy configuration"""
        config = ProxyConfig(
            enabled=True,
            http_proxy="http://proxy.example.com:8080",
            https_proxy="https://proxy.example.com:8443",
        )
        assert config.enabled is True
        assert config.http_proxy == "http://proxy.example.com:8080"
        assert config.https_proxy == "https://proxy.example.com:8443"


class TestAgentConfig:
    """Test AgentConfig class"""

    def test_default_values(self):
        """Test default agent configuration"""
        config = AgentConfig()
        assert config.llm_provider == "ollama"
        assert config.llm_model == "qwen2.5:7b"
        assert config.llm_temperature == 0.7
        assert config.llm_max_tokens == 4096
        assert config.ollama_base_url == "http://localhost:11434"

    def test_openai_config(self):
        """Test OpenAI configuration"""
        config = AgentConfig(
            llm_provider="openai",
            llm_model="gpt-4",
            openai_api_key="sk-test-key",
        )
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.openai_api_key == "sk-test-key"

    def test_temperature_validation(self):
        """Test temperature validation"""
        config = AgentConfig(llm_temperature=0.5)
        assert config.llm_temperature == 0.5

        config = AgentConfig(llm_temperature=1.0)
        assert config.llm_temperature == 1.0


class TestPlatformConfig:
    """Test PlatformConfig class"""

    def test_default_platforms(self):
        """Test default enabled platforms"""
        config = PlatformConfig()
        assert "douyin" in config.enabled_platforms
        assert "xiaohongshu" in config.enabled_platforms
        assert "amazon" in config.enabled_platforms
        assert "google_scholar" in config.enabled_platforms

    def test_platform_priority(self):
        """Test platform priority"""
        config = PlatformConfig()
        assert config.platform_priority.get("douyin") == 10
        assert config.platform_priority.get("xiaohongshu") == 10
        assert config.platform_priority.get("amazon") == 10

    def test_custom_platforms(self):
        """Test custom platform configuration"""
        config = PlatformConfig(
            enabled_platforms=["douyin", "weibo"],
            platform_priority={"douyin": 10, "weibo": 5},
        )
        assert len(config.enabled_platforms) == 2
        assert config.platform_priority["douyin"] == 10
        assert config.platform_priority["weibo"] == 5


class TestMainConfig:
    """Test main Config class"""

    def test_default_config(self, temp_dir):
        """Test default configuration"""
        config = Config(data_dir=temp_dir / "data", cache_dir=temp_dir / "cache")
        assert config.debug is False
        assert config.log_level == "INFO"
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.spider, SpiderConfig)
        assert isinstance(config.anti_crawl, AntiCrawlConfig)

    def test_directory_creation(self, temp_dir):
        """Test that directories are created"""
        data_dir = temp_dir / "data"
        cache_dir = temp_dir / "cache"

        config = Config(
            data_dir=data_dir,
            cache_dir=cache_dir,
            log_file=str(temp_dir / "logs" / "test.log"),
        )

        assert data_dir.exists()
        assert cache_dir.exists()
        assert (temp_dir / "logs").exists()

    def test_get_platform_config(self, temp_dir):
        """Test get_platform_config method"""
        config = Config(data_dir=temp_dir / "data", cache_dir=temp_dir / "cache")

        douyin_config = config.get_platform_config("douyin")
        assert douyin_config["enabled"] is True
        assert douyin_config["priority"] == 10

        unknown_config = config.get_platform_config("unknown_platform")
        assert unknown_config["enabled"] is False
        assert unknown_config["priority"] == 5

    def test_nested_configuration(self, temp_dir):
        """Test nested configuration access"""
        config = Config(
            data_dir=temp_dir / "data",
            cache_dir=temp_dir / "cache",
            database=DatabaseConfig(redis_port=6380),
            spider=SpiderConfig(concurrent_tasks=10),
        )

        assert config.database.redis_port == 6380
        assert config.spider.concurrent_tasks == 10

    def test_debug_mode(self, temp_dir):
        """Test debug mode configuration"""
        config = Config(
            debug=True,
            log_level="DEBUG",
            data_dir=temp_dir / "data",
            cache_dir=temp_dir / "cache",
        )

        assert config.debug is True
        assert config.log_level == "DEBUG"

    @pytest.mark.skip(reason="Requires .env file setup")
    def test_env_file_loading(self, temp_dir):
        """Test loading configuration from .env file"""
        # Create .env file
        env_file = temp_dir / ".env"
        env_file.write_text(
            """
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE__REDIS_PORT=6380
"""
        )

        # This would require setting env_file in Config
        # config = Config(_env_file=str(env_file))
        # assert config.debug is True
        # assert config.database.redis_port == 6380

    def test_yaml_loading(self, temp_dir):
        """Test loading configuration from YAML file"""
        import yaml

        yaml_file = temp_dir / "config.yaml"
        yaml_data = {
            "debug": True,
            "log_level": "DEBUG",
            "database": {"redis_port": 6380},
            "spider": {"concurrent_tasks": 10},
        }

        with open(yaml_file, "w") as f:
            yaml.dump(yaml_data, f)

        # Load config from file
        config = Config.from_file(str(yaml_file))
        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.database.redis_port == 6380
        assert config.spider.concurrent_tasks == 10


class TestMatcherConfig:
    """Test MatcherConfig class"""

    def test_default_values(self):
        """Test default matcher configuration"""
        config = MatcherConfig()
        assert config.similarity_threshold == 0.85
        assert "paraphrase-multilingual" in config.bert_model
        assert config.use_gpu is False
        assert config.vector_dim == 384

    def test_custom_values(self):
        """Test custom matcher configuration"""
        config = MatcherConfig(
            similarity_threshold=0.90,
            bert_model="custom-model",
            use_gpu=True,
            vector_dim=512,
        )
        assert config.similarity_threshold == 0.90
        assert config.bert_model == "custom-model"
        assert config.use_gpu is True
        assert config.vector_dim == 512


class TestAnalysisConfig:
    """Test AnalysisConfig class"""

    def test_default_values(self):
        """Test default analysis configuration"""
        config = AnalysisConfig()
        assert "sentiment" in config.sentiment_model
        assert config.language_detection is True
        assert "zh" in config.supported_languages
        assert "en" in config.supported_languages

    def test_custom_languages(self):
        """Test custom language configuration"""
        config = AnalysisConfig(supported_languages=["en", "fr", "de"])
        assert len(config.supported_languages) == 3
        assert "fr" in config.supported_languages


class TestConfigEdgeCases:
    """Test edge cases and error handling"""

    def test_invalid_log_level(self, temp_dir):
        """Test invalid log level"""
        # Should accept any string but ideally validate
        config = Config(
            log_level="INVALID",
            data_dir=temp_dir / "data",
            cache_dir=temp_dir / "cache",
        )
        assert config.log_level == "INVALID"

    def test_path_validation(self, temp_dir):
        """Test path handling"""
        config = Config(
            data_dir=temp_dir / "data",
            cache_dir=temp_dir / "cache",
        )

        assert isinstance(config.data_dir, Path)
        assert isinstance(config.cache_dir, Path)

    def test_empty_platform_list(self):
        """Test empty platform list"""
        config = PlatformConfig(enabled_platforms=[])
        assert len(config.enabled_platforms) == 0

    def test_config_serialization(self, temp_dir):
        """Test configuration serialization"""
        config = Config(
            debug=True,
            data_dir=temp_dir / "data",
            cache_dir=temp_dir / "cache",
        )

        # Convert to dict
        config_dict = config.dict()
        assert "debug" in config_dict
        assert "database" in config_dict
        assert "spider" in config_dict


class TestConfigPerformance:
    """Test configuration performance"""

    def test_config_creation_performance(self, temp_dir, performance_tracker):
        """Test configuration creation performance"""
        performance_tracker.start()

        for _ in range(100):
            Config(data_dir=temp_dir / "data", cache_dir=temp_dir / "cache")

        elapsed = performance_tracker.stop()
        assert elapsed < 1.0, f"Config creation took {elapsed}s for 100 instances"

    def test_config_access_performance(self, temp_dir, performance_tracker):
        """Test configuration access performance"""
        config = Config(data_dir=temp_dir / "data", cache_dir=temp_dir / "cache")

        performance_tracker.start()

        for _ in range(1000):
            _ = config.database.redis_port
            _ = config.spider.concurrent_tasks
            _ = config.anti_crawl.max_retries

        elapsed = performance_tracker.stop()
        assert elapsed < 0.1, f"Config access took {elapsed}s for 1000 accesses"
