from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.a2a.server import mount as mount_a2a
from src.api.routes import chat, debug
from src.core.config.settings import settings
from src.core.llm.keys import key_client
from src.core.observability.errors import register_error_handlers
from src.core.observability.langsmith_tracing import warn_if_global_tracing
from src.core.observability.observability import setup_observability
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)


def cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_if_global_tracing()
    await ensure_user_memory_indexes()
    yield


app = FastAPI(
    title="Solaria Operacional API",
    description="Agente que ajuda a operar o SaaS: acha telas e propõe ações com aprovação do usuário.",
    version="0.1.0",
    lifespan=lifespan,
)
# logo após criar a app -> os spans HTTP já existem quando as rotas e os middlewares entram
setup_observability(app, "ai-operational")
# erros viram ProblemDetail e marcam o span criado acima -> precisa vir depois da observabilidade
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(settings.CORS_ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(chat.router)
app.include_router(debug.router)
mount_a2a(app)


@app.get("/health")
def health() -> dict:
    """Responde 'ok' se o servidor subiu, listando configuração ausente."""
    configured = key_client().providers()
    missing = [
        f"{provider.upper()}_API_KEY"
        for provider in ("gemini", "groq")
        if provider not in configured
    ]

    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
