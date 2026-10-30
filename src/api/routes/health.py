import asyncio
import logging
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.infra.database.mongo.async_client import get_async_mongodb_client
from src.version import VERSION

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Saúde"])

READY_TIMEOUT_SECONDS = 2
DATABASE = "assessor_inteligente"


class HealthResponse(BaseModel):
    status: Literal["UP"] = Field(..., examples=["UP"])
    version: str = Field(..., examples=["0.1.1"])


class ReadyResponse(BaseModel):
    status: Literal["UP", "DOWN"] = Field(..., examples=["UP"])


async def ping_database() -> None:
    await asyncio.wait_for(
        get_async_mongodb_client()[DATABASE].command("ping"),
        timeout=READY_TIMEOUT_SECONDS,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Indica se o processo está vivo",
    description="Só o processo, sem consultar dependências; traz a versão do release.",
    operation_id="getHealth",
    openapi_extra={"security": [], "x-error-codes": ["INTERNAL_ERROR"]},
)
async def health() -> HealthResponse:
    return HealthResponse(status="UP", version=VERSION)


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Indica se o serviço está pronto para atender",
    description=(
        "Consulta só o MongoDB (checkpointer e memória do agente), com timeout de 2 "
        "segundos. Provedores de LLM ficam de fora porque há fallback entre eles. "
        'Responde 503 com {"status":"DOWN"} quando o banco não responde.'
    ),
    operation_id="getReady",
    responses={503: {"model": ReadyResponse, "description": "Serviço não pronto"}},
    openapi_extra={"security": [], "x-error-codes": ["INTERNAL_ERROR"]},
)
async def ready() -> JSONResponse:
    try:
        await ping_database()
    except Exception:
        logger.warning("MongoDB indisponível no /ready", exc_info=True)
        return JSONResponse({"status": "DOWN"}, status_code=503)
    return JSONResponse({"status": "UP"})
