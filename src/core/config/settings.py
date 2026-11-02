from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    DB_MONGO_AGENTS: str = "dbagents"
    CHECKPOINT_TTL_DIAS: int = 30

    API_MESSENGER_URL: str | None = None
    SERVICE_KEY: str | None = Field(
        None, validation_alias=AliasChoices("SERVICE_KEY", "SERVICE_KEY_AI_OPERATIONAL")
    )

    JWT_JWKS_URL: str | None = None
    JWT_ISSUER: str | None = None

    ENVIRONMENT: str = "LOCAL"

    DOCS_ENABLED: bool = True
    PROPOSAL_SIGNING_KEY: str | None = None
    PROPOSAL_TTL_SECONDS: int = 900
    MAX_WRITES_PER_CONVERSATION: int = 10
    MAX_MESSAGE_CHARS: int = 2000

    SOLARIA_LANGSMITH_ENABLED: bool = False
    SOLARIA_LANGSMITH_API_KEY: str | None = None
    SOLARIA_LANGSMITH_PROJECT: str = "solaria-local"
    SOLARIA_LANGSMITH_ENDPOINT: str | None = None
    SOLARIA_LANGSMITH_SAMPLING_RATE: float = 1.0

    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://localhost:5174,"
        "http://127.0.0.1:5174,https://web-sandbox-7ug0.onrender.com"
    )

    DEBUG_ADMIN_SUBS: str = ""

    # api-core: onde as ações aprovadas pelo usuário são executadas, com o JWT dele.
    API_CORE_URL: str = "http://localhost:8080/api"

    # A2A: URL pública deste serviço, anunciada no Agent Card.
    A2A_PUBLIC_URL: str = "http://localhost:8003"

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
