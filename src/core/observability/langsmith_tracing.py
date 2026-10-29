import logging
import os

from langchain_core.tracers.langchain import LangChainTracer
from langsmith import Client
from langsmith.anonymizer import create_anonymizer

from src.core.config.settings import settings
from src.core.guardrails.anonymize import PII_PATTERNS
from src.core.security.untrusted import SEGREDO_REMOVIDO, SEGREDOS_PATTERN

logger = logging.getLogger(__name__)

_client: Client | None = None


def build_anonymizer():
    """Mascara CPF, CNPJ, telefone, e-mail, JWT e chaves antes de qualquer dado sair
    para o LangSmith (entradas e saídas de todas as execuções)."""
    return create_anonymizer(
        [
            *[
                {"pattern": padrao, "replace": f"[{tipo}]"}
                for tipo, padrao in PII_PATTERNS
            ],
            {"pattern": SEGREDOS_PATTERN, "replace": SEGREDO_REMOVIDO},
        ]
    )


def langsmith_enabled() -> bool:
    return bool(
        settings.SOLARIA_LANGSMITH_ENABLED and settings.SOLARIA_LANGSMITH_API_KEY
    )


def _get_client() -> Client:
    """Um Client só, reaproveitado entre turnos (guarda a fila de envio)."""
    global _client
    if _client is None:
        _client = Client(
            api_key=settings.SOLARIA_LANGSMITH_API_KEY,
            api_url=settings.SOLARIA_LANGSMITH_ENDPOINT,
            anonymizer=build_anonymizer(),
            tracing_sampling_rate=settings.SOLARIA_LANGSMITH_SAMPLING_RATE,
        )
    return _client


def build_tracer() -> LangChainTracer | None:
    """Um tracer novo por turno (ele guarda estado das execuções em andamento),
    sobre o Client compartilhado. None se o LangSmith estiver desligado."""
    if not langsmith_enabled():
        return None
    return LangChainTracer(
        client=_get_client(), project_name=settings.SOLARIA_LANGSMITH_PROJECT
    )


def warn_if_global_tracing() -> None:
    """Avisa na subida se o tracing global do LangChain estiver ligado por
    variável de ambiente: ele ignora o anonymizer e envia PII crua."""
    for nome in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        if os.environ.get(nome, "").lower() == "true":
            logger.warning(
                "%s=true: tracing global do LangSmith ligado, sem anonymizer.", nome
            )
    if langsmith_enabled():
        logger.info(
            "LangSmith ligado (projeto=%s).", settings.SOLARIA_LANGSMITH_PROJECT
        )
