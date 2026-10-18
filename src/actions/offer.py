"""Ação "criar oferta de placa": rascunho, resolução de modelo e fornecedor, texto da
proposta e payload do api-core. Nada aqui grava: quem grava é o nó de decisão, depois
do aceite do usuário."""

from decimal import Decimal

from pydantic import BaseModel, Field

from src.domain.text import normalize
from src.infra.api_core.client import SupplierRef

ACTION = "create_offer"
MAX_OPCOES = 5

CAMPOS_OBRIGATORIOS = {
    "modelo": 'o modelo da placa (marca e modelo, por exemplo "Canadian CS6R 550")',
    "preco_unitario": "o preço unitário em reais",
    "disponibilidade": "a quantidade disponível em estoque",
}


class OfferDraft(BaseModel):
    """O que o LLM entendeu do pedido. Tudo opcional: o que faltar é perguntado."""

    modelo: str | None = None
    titulo: str | None = None
    descricao: str | None = None
    preco_unitario: Decimal | None = Field(default=None, gt=0)
    disponibilidade: int | None = Field(default=None, ge=0)
    empresa: str | None = None


def missing_fields(draft: OfferDraft) -> list[str]:
    """Descrição de cada campo obrigatório que ainda não foi informado."""
    return [
        texto
        for campo, texto in CAMPOS_OBRIGATORIOS.items()
        if getattr(draft, campo) in (None, "")
    ]


def pick_supplier(
    draft: OfferDraft, suppliers: list[SupplierRef]
) -> SupplierRef | list[SupplierRef]:
    """O fornecedor da oferta, ou a lista de candidatos quando for ambíguo."""
    if len(suppliers) == 1:
        return suppliers[0]
    if draft.empresa:
        alvo = normalize(draft.empresa).strip()
        achados = [s for s in suppliers if alvo and alvo in normalize(s.company_name)]
        if len(achados) == 1:
            return achados[0]
    return suppliers


def _tokens(text: str) -> list[str]:
    return [token for token in normalize(text).split() if token]


def match_models(query: str, models: list[dict]) -> list[dict]:
    """Modelos do catálogo em que todas as palavras da consulta aparecem em
    "marca modelo potência". Números casam com a potência (550 ou 550wp)."""
    wanted = _tokens(query)
    if not wanted:
        return []
    achados = []
    for model in models:
        power = model.get("powerWp")
        power_text = (
            f"{power:g}" if isinstance(power, (int, float)) else str(power or "")
        )
        haystack = " ".join(
            _tokens(f"{model.get('brand', '')} {model.get('model', '')} {power_text}")
        )
        if all(token.removesuffix("wp") in haystack for token in wanted):
            achados.append(model)
    return achados


def model_label(model: dict) -> str:
    power = model.get("powerWp")
    power_text = f" {power:g} Wp" if isinstance(power, (int, float)) else ""
    return f"{model.get('brand', '')} {model.get('model', '')}{power_text}".strip()


def default_title(model: dict) -> str:
    return f"Placa solar {model_label(model)}"


def default_description(model: dict) -> str:
    return f"Placa solar {model_label(model)} disponível para venda."


def build_payload(draft: OfferDraft, model: dict, supplier: SupplierRef) -> dict:
    return {
        "supplierId": supplier.supplier_id,
        "modelId": model["id"],
        "title": draft.titulo or default_title(model),
        "description": draft.descricao or default_description(model),
        "unitPrice": float(draft.preco_unitario),
        "availability": draft.disponibilidade,
    }


def _brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_proposal(payload: dict, model: dict, supplier: SupplierRef) -> str:
    return (
        "Posso cadastrar esta oferta, mas só depois do seu aceite:\n\n"
        f"- Empresa: {supplier.company_name}\n"
        f"- Placa: {model_label(model)}\n"
        f"- Título: {payload['title']}\n"
        f"- Descrição: {payload['description']}\n"
        f"- Preço unitário: {_brl(payload['unitPrice'])}\n"
        f"- Disponibilidade: {payload['availability']} unidades\n\n"
        'Você aceita? Responda "sim" para cadastrar, "não" para cancelar, ou me diga o que quer ajustar.'
    )


def render_success(offer: dict, payload: dict) -> str:
    return (
        f'Pronto, a oferta "{payload["title"]}" foi cadastrada '
        f"por {_brl(payload['unitPrice'])} com {payload['availability']} unidades."
    )
