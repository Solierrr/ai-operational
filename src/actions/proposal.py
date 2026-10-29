import hashlib
import hmac
import json
import secrets
import time
from uuid import uuid4

from src.core.config.settings import settings

_PROCESS_KEY = secrets.token_bytes(32)

OK = "ok"
INVALIDA = "invalida"
EXPIRADA = "expirada"
OUTRO_USUARIO = "outro_usuario"


def _signing_key() -> bytes:
    chave = settings.PROPOSAL_SIGNING_KEY or settings.SERVICE_KEY
    return chave.encode() if chave else _PROCESS_KEY


def _seal(body: dict) -> str:
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, default=str)
    return hmac.new(_signing_key(), canonical.encode(), hashlib.sha256).hexdigest()


def _body(proposal: dict) -> dict:
    return {
        "id": proposal.get("id"),
        "action": proposal.get("action"),
        "payload": proposal.get("payload"),
        "resumo": proposal.get("resumo"),
        "user_id": proposal.get("user_id"),
        "criada_em": proposal.get("criada_em"),
        "irreversivel": proposal.get("irreversivel"),
    }


def make_proposal(
    action: str,
    payload: dict,
    resumo: str,
    user_id: str | None,
    irreversible: bool = False,
    now: float | None = None,
) -> dict:
    proposal = {
        "id": uuid4().hex,
        "action": action,
        "payload": payload,
        "resumo": resumo,
        "user_id": user_id,
        "criada_em": time.time() if now is None else now,
        "irreversivel": irreversible,
    }
    return {**proposal, "selo": _seal(_body(proposal))}


def verify_proposal(
    proposal: dict | None, user_id: str | None, now: float | None = None
) -> str:
    if not proposal or not isinstance(proposal.get("selo"), str):
        return INVALIDA
    if not user_id and settings.ENVIRONMENT.upper() != "LOCAL":
        return INVALIDA
    if not hmac.compare_digest(proposal["selo"], _seal(_body(proposal))):
        return INVALIDA
    if proposal.get("user_id") != user_id:
        return OUTRO_USUARIO
    criada = proposal.get("criada_em")
    if not isinstance(criada, int | float):
        return INVALIDA
    atual = time.time() if now is None else now
    if atual - criada > settings.PROPOSAL_TTL_SECONDS:
        return EXPIRADA
    return OK
