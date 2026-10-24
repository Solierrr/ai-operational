from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    CHECKPOINT_TTL_DIAS: int = 30

    UPSTASH_REDIS_HOST: str | None = None
    UPSTASH_REDIS_PORT: int = 6379
    UPSTASH_REDIS_USERNAME: str = "default"
    UPSTASH_REDIS_PASSWORD: str | None = None

    API_MESSENGER_URL: str | None = None
    SERVICE_KEY: str | None = Field(
        None, validation_alias=AliasChoices("SERVICE_KEY", "SERVICE_KEY_AI_OPERATIONAL")
    )

    JWT_JWKS_URL: str | None = None
    JWT_ISSUER: str | None = None

    ENVIRONMENT: str = "LOCAL"

    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://localhost:5174,"
        "http://127.0.0.1:5174,https://web-sandbox-7ug0.onrender.com"
    )

    DEBUG_ADMIN_SUBS: str = ""

    # api-core: onde as ações aprovadas pelo usuário são executadas, com o JWT dele.
    API_CORE_URL: str = "http://localhost:8080/api"

    # A2A: URL pública deste serviço, anunciada no Agent Card.
    A2A_PUBLIC_URL: str = "http://localhost:8003"

    TEST_USER_TOKEN: str | None = (
        None  # só pra uso local via main.py, nunca em produção
    )

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
