from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import BaseModel

from src.core.security.untrusted import sanitize_field
from src.domain.text import normalize
from src.infra.api_core.client import ApiCoreClient

MAX_OPCOES = 5

RODAPE_NORMAL = (
    '\n\nVocê aceita? Responda "sim" para executar, "não" para cancelar, '
    "ou me diga o que quer ajustar."
)
RODAPE_IRREVERSIVEL = (
    "\n\nEsta ação não pode ser desfeita. Para executar, responda exatamente "
    '"confirmo". Para cancelar, responda "não".'
)


@dataclass(frozen=True)
class Ask:
    text: str


@dataclass(frozen=True)
class Ready:
    payload: dict
    resumo: str
    irreversible: bool = False


@dataclass(frozen=True)
class ActionSpec:
    name: str
    descricao: str
    prompt: str
    draft_model: type[BaseModel]
    prepare: Callable[[BaseModel, ApiCoreClient], Awaitable[Ask | Ready]]
    execute: Callable[[ApiCoreClient, dict], Awaitable[dict]]
    success: Callable[[dict, dict], str]
    recusado: str


def brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def short_id(value: object) -> str:
    return str(value or "")[:8]


def safe(value: object, limit: int = 80) -> str:
    return sanitize_field(value, limit)


def tokens(text: str) -> list[str]:
    return [token for token in normalize(text).split() if token]


def label_matches(query: str, label: str) -> bool:
    wanted = tokens(query)
    if not wanted:
        return False
    haystack = " ".join(tokens(label))
    return all(token.removesuffix("wp") in haystack for token in wanted)


def filter_by_company(items: list[dict], company: str | None) -> list[dict]:
    if not company:
        return items
    da_empresa = [i for i in items if label_matches(company, i.get("_empresa", ""))]
    return da_empresa or items


def render_proposal(ready: Ready) -> str:
    rodape = RODAPE_IRREVERSIVEL if ready.irreversible else RODAPE_NORMAL
    return ready.resumo + rodape


def options_text(labels: list[str]) -> str:
    return "\n".join(f"- {label}" for label in labels[:MAX_OPCOES])
