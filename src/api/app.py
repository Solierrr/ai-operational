from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.a2a.server import mount as mount_a2a
from src.api.errors import apply_problem_details, register_error_handlers
from src.api.routes import chat, debug, health
from src.core.config.settings import settings
from src.core.llm.keys import key_client
from src.core.observability.langsmith_tracing import warn_if_global_tracing
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)
from src.otel_setup import configure_otel
from src.version import VERSION

A2A_PATHS = ("/a2a", "/.well-known/")

TAGS = [
    {
        "name": "Conversa",
        "description": "Turnos da conversa com o agente operacional",
    },
    {
        "name": "Saúde",
        "description": "Vivo e pronto, para a plataforma e o monitoramento",
    },
]


def cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_if_global_tracing()
    await ensure_user_memory_indexes()
    yield


app = FastAPI(
    title="Solaria — ai-operational",
    description=(
        "Agente que ajuda o usuário a operar o SaaS da Solaria: indica a tela certa do "
        "web-app e propõe ações (hoje, cadastrar uma oferta de placa) que só são "
        "executadas no api-core depois do aceite do usuário. Autentique com o JWT do "
        "api-auth (bearerAuth). O A2A, usado pelo ai-assistant, não faz parte deste "
        "contrato: o Agent Card fica em /.well-known/agent-card.json."
    ),
    version=VERSION,
    contact={"name": "Solaria", "url": "https://github.com/Solierrr"},
    license_info={
        "name": "CC0-1.0",
        "url": "https://creativecommons.org/publicdomain/zero/1.0/",
    },
    servers=[
        {"url": "https://ai-operational.onrender.com", "description": "QA"},
        {"url": "http://localhost:8000", "description": "Local"},
    ],
    openapi_tags=TAGS,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
    redoc_url=None,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(settings.CORS_ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

register_error_handlers(app)
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(debug.router)
mount_a2a(app)


def build_openapi(include_internal: bool) -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=[
            route
            for route in app.routes
            if not getattr(route, "path", "").startswith(A2A_PATHS)
        ],
        tags=app.openapi_tags,
        servers=app.servers,
        contact=app.contact,
        license_info=app.license_info,
    )
    schema["security"] = [{"bearerAuth": []}]
    apply_problem_details(schema)
    if not include_internal:
        schema["paths"] = {
            path: item
            for path, item in schema["paths"].items()
            if not path.startswith("/internal/")
        }
        used = {
            tag
            for item in schema["paths"].values()
            for operation in item.values()
            for tag in operation.get("tags", [])
        }
        schema["tags"] = [tag for tag in schema.get("tags", []) if tag["name"] in used]
    return schema


def public_openapi() -> dict:
    if app.openapi_schema is None:
        app.openapi_schema = build_openapi(include_internal=False)
    return app.openapi_schema


app.openapi = public_openapi

configure_otel(app, "ai-operational")
