import re

from src.domain.text import normalize

_ACEITE = frozenset(
    {
        "sim",
        "aceito",
        "aceitar",
        "confirmo",
        "confirmar",
        "ok",
        "pode",
        "pode sim",
        "pode criar",
        "pode cadastrar",
        "isso",
        "isso mesmo",
        "claro",
        "com certeza",
        "manda ver",
        "vai",
        "fechado",
        "de acordo",
        "sim pode",
        "sim por favor",
        "pode executar",
        "pode fazer",
        "pode alterar",
        "pode ajustar",
        "pode pausar",
        "pode reativar",
        "pode encerrar",
        "pode colocar",
        "pode tirar",
        "pode confirmar",
        "sim pode cadastrar",
        "sim pode criar",
    }
)
_CONFIRMO = frozenset(
    {
        "confirmo",
        "sim confirmo",
        "confirmo sim",
        "eu confirmo",
        "sim eu confirmo",
        "confirmo a acao",
        "confirmo o cancelamento",
        "confirmo o encerramento",
    }
)
_RECUSA = frozenset(
    {
        "nao",
        "recuso",
        "recusar",
        "cancela",
        "cancelar",
        "cancele",
        "nao quero",
        "deixa",
        "deixa pra la",
        "esquece",
        "para",
        "pare",
        "desisto",
        "melhor nao",
    }
)


def quick_decision(text: str) -> str | None:
    """Aceite ou recusa inequívocos, sem LLM. Só vale para respostas curtas e
    exatamente iguais a uma das fórmulas conhecidas."""
    limpo = re.sub(r"\s+", " ", normalize(text)).strip()
    if "?" not in text and (limpo in _ACEITE or limpo in _CONFIRMO):
        return "aceitar"
    if limpo in _RECUSA:
        return "recusar"
    return None


EXIGE_CONFIRMO = "exigir_confirmo"

# Depois de uma dúvida sobre a proposta, "ok" pode ser só "entendi": só vale o aceite
# explícito.
_FRACOS = frozenset(
    {"ok", "pode", "isso", "isso mesmo", "claro", "com certeza", "manda ver", "vai"}
)


def strict_decision(
    text: str, irreversible: bool, after_doubt: bool = False
) -> str | None:
    limpo = re.sub(r"\s+", " ", normalize(text)).strip()
    if limpo in _RECUSA:
        return "recusar"
    if "?" in text or (after_doubt and limpo in _FRACOS):
        return None
    if irreversible:
        if limpo in _CONFIRMO:
            return "aceitar"
        if limpo in _ACEITE:
            return EXIGE_CONFIRMO
        return None
    if limpo in _ACEITE or limpo in _CONFIRMO:
        return "aceitar"
    return None
