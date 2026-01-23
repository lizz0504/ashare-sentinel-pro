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

    @property
    def cors_origins_list(self) -> list[str]:
        """将 CORS_ORIGINS 字符串转换为列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# 全局配置实例
settings = Settings()
