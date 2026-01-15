"""
Configuration management for OmniSense
支持环境变量、配置文件、运行时配置的统一管理
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    sqlite_path: str = Field(default="data/omnisense.db", description="SQLite database path")
    chroma_path: str = Field(default="data/chroma", description="ChromaDB vector database path")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")


class StorageConfig(BaseSettings):
    """Storage configuration"""
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO endpoint")
    minio_access_key: str = Field(default="minioadmin", description="MinIO access key")
    minio_secret_key: str = Field(default="minioadmin", description="MinIO secret key")
    minio_bucket: str = Field(default="omnisense", description="MinIO bucket name")
    minio_secure: bool = Field(default=False, description="Use HTTPS for MinIO")


class ProxyConfig(BaseSettings):
    """Proxy configuration"""
    enabled: bool = Field(default=False, description="Enable proxy")
    http_proxy: Optional[str] = Field(default=None, description="HTTP proxy URL")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS proxy URL")
    proxy_pool_enabled: bool = Field(default=False, description="Enable proxy pool")
    proxy_pool_url: Optional[str] = Field(default=None, description="Proxy pool API URL")


class AntiCrawlConfig(BaseSettings):
    """Anti-crawl configuration"""
    user_agent_rotation: bool = Field(default=True, description="Enable user agent rotation")
    fingerprint_random: bool = Field(default=True, description="Enable fingerprint randomization")
    captcha_service: Optional[str] = Field(default=None, description="Captcha solving service (2captcha, etc)")
    captcha_api_key: Optional[str] = Field(default=None, description="Captcha service API key")
    request_delay_min: float = Field(default=1.0, description="Minimum request delay (seconds)")
    request_delay_max: float = Field(default=5.0, description="Maximum request delay (seconds)")
    max_retries: int = Field(default=3, description="Maximum retries for failed requests")


class SpiderConfig(BaseSettings):
    """Spider configuration"""
    concurrent_tasks: int = Field(default=5, description="Number of concurrent tasks")
    timeout: int = Field(default=30, description="Request timeout (seconds)")
    download_media: bool = Field(default=True, description="Download media files")
    media_formats: List[str] = Field(default=["jpg", "png", "mp4", "mp3"], description="Allowed media formats")
    max_media_size: int = Field(default=100 * 1024 * 1024, description="Maximum media file size (bytes)")
    cookie_persist: bool = Field(default=True, description="Persist cookies between sessions")


class MatcherConfig(BaseSettings):
    """Matcher configuration"""
    similarity_threshold: float = Field(default=0.85, description="Content similarity threshold")
    bert_model: str = Field(default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                           description="BERT model for semantic analysis")
    use_gpu: bool = Field(default=False, description="Use GPU for model inference")
    vector_dim: int = Field(default=384, description="Vector dimension")


class AnalysisConfig(BaseSettings):
    """Analysis configuration"""
    sentiment_model: str = Field(default="cardiffnlp/twitter-roberta-base-sentiment",
                                description="Sentiment analysis model")
    language_detection: bool = Field(default=True, description="Enable language detection")
    supported_languages: List[str] = Field(default=["zh", "en", "ja", "ko"],
                                          description="Supported languages")


class AgentConfig(BaseSettings):
    """Agent configuration"""
    llm_provider: str = Field(default="ollama", description="LLM provider (ollama, openai, anthropic)")
    llm_model: str = Field(default="qwen2.5:7b", description="LLM model name")
    llm_temperature: float = Field(default=0.7, description="LLM temperature")
    llm_max_tokens: int = Field(default=4096, description="Maximum tokens for LLM")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")


class CookieConfig(BaseSettings):
    """Cookie management configuration"""
    storage_path: str = Field(default="data/cookies", description="Cookie storage path")
    auto_refresh: bool = Field(default=True, description="Auto refresh expired cookies")
    encrypt: bool = Field(default=False, description="Encrypt cookie storage")
    validation_enabled: bool = Field(default=True, description="Validate cookies before use")
    pool_enabled: bool = Field(default=True, description="Enable cookie pool for rotation")


class APIConfig(BaseSettings):
    """API configuration"""
    # API凭证存储路径
    credentials_path: str = Field(default="data/api_credentials.json", description="API credentials storage path")

    # GitHub API
    github_token: Optional[str] = Field(default=None, description="GitHub Personal Access Token")
    github_rate_limit: int = Field(default=5000, description="GitHub API rate limit per hour")

    # Twitter API
    twitter_bearer_token: Optional[str] = Field(default=None, description="Twitter API Bearer Token")
    twitter_api_key: Optional[str] = Field(default=None, description="Twitter API Key")
    twitter_api_secret: Optional[str] = Field(default=None, description="Twitter API Secret")
    twitter_access_token: Optional[str] = Field(default=None, description="Twitter Access Token")
    twitter_access_secret: Optional[str] = Field(default=None, description="Twitter Access Token Secret")

    # Reddit API
    reddit_client_id: Optional[str] = Field(default=None, description="Reddit Client ID")
    reddit_client_secret: Optional[str] = Field(default=None, description="Reddit Client Secret")
    reddit_user_agent: str = Field(default="OmniSense/1.0", description="Reddit User Agent")

    # YouTube API
    youtube_api_key: Optional[str] = Field(default=None, description="YouTube Data API Key")
    youtube_quota_limit: int = Field(default=10000, description="YouTube API quota per day")

    # Google Scholar (需要API key或使用SerpAPI)
    serpapi_key: Optional[str] = Field(default=None, description="SerpAPI Key for Google Scholar")

    # 微信公众号 API
    wechat_app_id: Optional[str] = Field(default=None, description="WeChat App ID")
    wechat_app_secret: Optional[str] = Field(default=None, description="WeChat App Secret")

    # 抖音开放平台
    douyin_client_key: Optional[str] = Field(default=None, description="Douyin Client Key")
    douyin_client_secret: Optional[str] = Field(default=None, description="Douyin Client Secret")

    # 小红书 (非官方)
    xiaohongshu_api_key: Optional[str] = Field(default=None, description="Xiaohongshu API Key (third-party)")

    # 京东 API
    jd_app_key: Optional[str] = Field(default=None, description="JD App Key")
    jd_app_secret: Optional[str] = Field(default=None, description="JD App Secret")

    # 淘宝/天猫 API
    taobao_app_key: Optional[str] = Field(default=None, description="Taobao App Key")
    taobao_app_secret: Optional[str] = Field(default=None, description="Taobao App Secret")

    # API使用偏好
    prefer_api: bool = Field(default=True, description="Prefer official API over scraping when available")
    fallback_to_scraping: bool = Field(default=True, description="Fallback to scraping if API fails")

    # 速率限制
    enable_rate_limit: bool = Field(default=True, description="Enable API rate limiting")
    default_rate_limit: int = Field(default=60, description="Default requests per minute")


class PlatformConfig(BaseSettings):
    """Platform-specific configuration"""
    enabled_platforms: List[str] = Field(
        default=[
            "douyin", "xiaohongshu", "weibo", "bilibili", "kuaishou",
            "tiktok", "youtube", "twitter", "instagram", "facebook",
            "wechat_mp", "zhihu", "douban", "baidu_tieba", "toutiao",
            "amazon", "taobao", "tmall", "jd", "pinduoduo",
            "meituan", "dianping", "baidu", "google",
            "google_scholar", "cnki", "github", "csdn", "stackoverflow"
        ],
        description="Enabled platforms"
    )
    platform_priority: Dict[str, int] = Field(
        default={
            "douyin": 10, "xiaohongshu": 10, "weibo": 9, "bilibili": 9,
            "amazon": 10, "taobao": 9, "google_scholar": 8
        },
        description="Platform priority (higher = more important)"
    )

    # 数据采集模式配置
    collection_mode: Dict[str, str] = Field(
        default={
            "github": "api",  # api, scraping, hybrid
            "twitter": "hybrid",
            "reddit": "api",
            "youtube": "api",
            "arxiv": "api",
            "douyin": "hybrid",
            "xiaohongshu": "scraping",
            "weibo": "hybrid"
        },
        description="Data collection mode per platform (api/scraping/hybrid)"
    )


class Config(BaseSettings):
    """Main configuration for OmniSense"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False
    )

    # Basic settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    log_file: str = Field(default="logs/omnisense.log", description="Log file path")
    data_dir: Path = Field(default=Path("data"), description="Data directory")
    cache_dir: Path = Field(default=Path("cache"), description="Cache directory")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    anti_crawl: AntiCrawlConfig = Field(default_factory=AntiCrawlConfig)
    spider: SpiderConfig = Field(default_factory=SpiderConfig)
    matcher: MatcherConfig = Field(default_factory=MatcherConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    platform: PlatformConfig = Field(default_factory=PlatformConfig)
    cookie: CookieConfig = Field(default_factory=CookieConfig)
    api: APIConfig = Field(default_factory=APIConfig)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.data_dir,
            self.cache_dir,
            Path(self.log_file).parent,
            Path(self.database.sqlite_path).parent,
            Path(self.database.chroma_path).parent,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific configuration"""
        return {
            "enabled": platform in self.platform.enabled_platforms,
            "priority": self.platform.platform_priority.get(platform, 5),
        }

    @classmethod
    def from_file(cls, config_file: str) -> "Config":
        """Load configuration from file"""
        import yaml
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)


class ReportConfig(BaseSettings):
    """Report Engine configuration"""
    default_template: str = Field(default="default", description="Default report template")
    target_words: int = Field(default=5000, description="Default target word count")
    max_word_limit: int = Field(default=20000, description="Maximum word limit for reports")
    enable_charts: bool = Field(default=True, description="Enable chart generation")
    enable_toc: bool = Field(default=True, description="Enable table of contents")
    default_format: str = Field(default="html", description="Default output format (html/pdf/markdown)")
    pdf_engine: str = Field(default="weasyprint", description="PDF generation engine")
    concurrent_chapters: int = Field(default=5, description="Maximum concurrent chapter generation")
    enable_llm_selection: bool = Field(default=True, description="Enable LLM-based template selection")


class ForumConfig(BaseSettings):
    """Forum Engine configuration"""
    max_rounds: int = Field(default=10, description="Maximum discussion rounds")
    timeout_seconds: int = Field(default=300, description="Forum session timeout")
    enable_moderator: bool = Field(default=True, description="Enable LLM moderator")
    enable_monitoring: bool = Field(default=True, description="Enable forum monitoring")
    disagreement_threshold: int = Field(default=2, description="Threshold for disagreement detection")
    consensus_threshold: float = Field(default=0.5, description="Consensus threshold (0.0-1.0)")
    message_history_limit: int = Field(default=100, description="Message history limit")
    moderator_guidance_frequency: int = Field(default=3, description="Moderator guidance frequency (rounds)")


class GraphRAGConfig(BaseSettings):
    """GraphRAG configuration"""
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password", description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")
    ner_model: str = Field(default="dslim/bert-base-NER", description="NER model for entity extraction")
    use_gpu: bool = Field(default=False, description="Use GPU for NER model")
    entity_confidence_threshold: float = Field(default=0.5, description="Minimum entity confidence")
    relation_confidence_threshold: float = Field(default=0.5, description="Minimum relation confidence")
    enable_llm_relation_extraction: bool = Field(default=True, description="Enable LLM-based relation extraction")
    enable_pattern_extraction: bool = Field(default=True, description="Enable pattern-based extraction")
    max_entity_distance: int = Field(default=100, description="Maximum distance between entities for relation")
    batch_size: int = Field(default=10, description="Batch size for document processing")
    enable_auto_indexing: bool = Field(default=True, description="Enable automatic index creation")
    enable_graph_enrichment: bool = Field(default=False, description="Enable graph enrichment (slower)")


# Global configuration instance
config = Config()
