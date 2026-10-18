from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.a2a.server import mount as mount_a2a
from src.api.routes import chat
from src.core.llm.keys import key_client
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_user_memory_indexes()
    yield


app = FastAPI(
    title="Solaria Operacional API",
    description="Agente que ajuda a operar o SaaS: acha telas e propõe ações com aprovação do usuário.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat.router)
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
