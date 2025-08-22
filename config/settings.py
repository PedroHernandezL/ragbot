from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # SOLO DATABASE_URL es obligatorio
    database_url: str = Field(..., env="DATABASE_URL")

    # estos no deberían ser requeridos, elimina o hazlos opcionales si los usas en otras partes
    # database_host: str = Field(default=None, env="DATABASE_HOST")
    # database_name: str = Field(default=None, env="DATABASE_NAME")
    # database_user: str = Field(default=None, env="DATABASE_USER")
    # database_password: str = Field(default=None, env="DATABASE_PASSWORD")
    database_port: int = Field(default=5432, env="DATABASE_PORT")

    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")
    max_tokens: int = Field(500, env="MAX_TOKENS")
    temperature: float = Field(0.7, env="TEMPERATURE")
    chat_model: str = Field("gpt-4o-mini", env="CHAT_MODEL")

    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()