"""
Application Configuration

从环境变量加载配置，使用 Pydantic Settings 进行验证
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --------------------------------------------
    # Environment 环境
    # --------------------------------------------
    ENV: str = "development"
    DEBUG: bool = True

    # --------------------------------------------
    # Supabase Configuration
    # --------------------------------------------
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str

    # --------------------------------------------
    # AI Model Services
    # --------------------------------------------
    OPENAI_API_KEY: str | None = None
    DASHSCOPE_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    ZHIPU_API_KEY: str | None = None
    VOLCANO_API_KEY: str | None = None

    # --------------------------------------------
    # Tushare Pro Configuration
    # --------------------------------------------
    TUSHARE_TOKEN: str | None = None
    TUSHARE_URL: str | None = None  # 私人链接 URL
    DISABLE_TUSHARE: bool = False  # 完全禁用 Tushare，只使用 AkShare

    # --------------------------------------------
    # Application Settings
    # --------------------------------------------
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --------------------------------------------
    # Redis Configuration (可选)
    # --------------------------------------------
    REDIS_URL: str = "redis://localhost:6379"

    # --------------------------------------------
    # API Configuration
    # --------------------------------------------
    # 请求超时配置（秒）
    API_TIMEOUT_DEFAULT: int = 15
    API_TIMEOUT_FAST: int = 5
    API_TIMEOUT_SLOW: int = 30

    # 重试配置
    API_MAX_RETRIES: int = 3
    API_RETRY_DELAY: int = 2  # 重试延迟（秒）

    # 缓存配置
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 缓存5分钟

    # 数据源配置
    DATA_SOURCE_FALLBACK_TO_AKSHARE: bool = True  # Tushare失败时是否降级到AkShare


# ============================================
# 数据源优先级常量（统一管理）
# ============================================
# 所有数据获取都遵循此优先级顺序，避免硬编码不一致问题
DATA_SOURCE_PRIORITY = {
    "primary": "Tushare",      # 主要数据源
    "secondary": "Baostock",   # 备用数据源
    "fallback": "AkShare",     # 最后备选
}

DATA_SOURCE_PRIORITY_ORDER = ["Tushare", "Baostock", "AkShare"]

# 数据类型与优先级映射
DATA_TYPE_PRIORITY = {
    "stock_info": ["Tushare", "本地数据库", "Baostock", "AkShare"],
    "financial_metrics": ["Tushare", "Baostock", "AkShare"],
    "technical_analysis": ["Tushare", "Baostock", "AkShare"],
    "realtime_price": ["Tushare", "Baostock", "AkShare"],
}

    # --------------------------------------------
    # RSSHub Configuration
    # --------------------------------------------
    RSSHUB_URL: str = "http://localhost:1200"  # 本地RSSHub实例地址
    RSSHUB_USE_PUBLIC: bool = False  # 是否使用公共实例（可能被限流）

    @property
    def cors_origins_list(self) -> list[str]:
        """将 CORS_ORIGINS 字符串转换为列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# 全局配置实例
settings = Settings()
