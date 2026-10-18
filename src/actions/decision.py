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
    if limpo in _ACEITE:
        return "aceitar"
    if limpo in _RECUSA:
        return "recusar"
    return None
