"""Ação "criar oferta de placa": rascunho, resolução de modelo e fornecedor, texto da
proposta e payload do api-core. Nada aqui grava: quem grava é o nó de decisão, depois
do aceite do usuário."""

from decimal import Decimal

from pydantic import BaseModel, Field

from src.actions import base
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    OFFER_EXTRACTION_PROMPT,
)
from src.core.security.untrusted import REMOVIDO
from src.domain.text import normalize
from src.infra.api_core.client import ApiCoreClient, SupplierRef

ACTION = "create_offer"
MAX_OPCOES = base.MAX_OPCOES
TITULO_MAX = 80
DESCRICAO_MAX = 200

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


def _texto_gravavel(value: str | None, padrao: str, limite: int) -> str:
    texto = base.safe(value, limite) if value else ""
    if not texto or texto == REMOVIDO:
        return base.safe(padrao, limite)
    return texto


def build_payload(draft: OfferDraft, model: dict, supplier: SupplierRef) -> dict:
    return {
        "supplierId": supplier.supplier_id,
        "modelId": model["id"],
        "title": _texto_gravavel(draft.titulo, default_title(model), TITULO_MAX),
        "description": _texto_gravavel(
            draft.descricao, default_description(model), DESCRICAO_MAX
        ),
        "unitPrice": float(draft.preco_unitario),
        "availability": draft.disponibilidade,
    }


def _brl(value: float) -> str:
    return base.brl(value)


def render_proposal(payload: dict, model: dict, supplier: SupplierRef) -> str:
    return (
        "Posso cadastrar esta oferta, mas só depois do seu aceite:\n\n"
        f"- Empresa: {base.safe(supplier.company_name)}\n"
        f"- Placa: {base.safe(model_label(model))}\n"
        f"- Título: {base.safe(payload['title'], TITULO_MAX)}\n"
        f"- Descrição: {base.safe(payload['description'], DESCRICAO_MAX)}\n"
        f"- Preço unitário: {_brl(payload['unitPrice'])}\n"
        f"- Disponibilidade: {payload['availability']} unidades"
    )


def render_success(offer: dict, payload: dict) -> str:
    return (
        f'Pronto, a oferta "{base.safe(payload["title"])}" foi cadastrada '
        f"por {_brl(payload['unitPrice'])} com {payload['availability']} unidades."
    )


SEM_FORNECEDOR = (
    "Sua conta não está ligada a uma empresa fornecedora, então não posso cadastrar ofertas. "
    "Cadastre a empresa pela tela de cadastro de empresa (`/pt-BR/cadastro/empresa`) e peça de novo."
)


async def prepare(draft: OfferDraft, client: ApiCoreClient) -> base.Ask | base.Ready:
    faltando = missing_fields(draft)
    if faltando:
        itens = "\n".join(f"- {item}" for item in faltando)
        return base.Ask(f"Para cadastrar a oferta ainda preciso saber:\n{itens}")

    fornecedores = await client.my_suppliers()
    if not fornecedores:
        return base.Ask(SEM_FORNECEDOR)
    escolhido = pick_supplier(draft, fornecedores)
    if isinstance(escolhido, list):
        nomes = "\n".join(f"- {base.safe(s.company_name)}" for s in escolhido)
        return base.Ask(f"Em qual empresa devo cadastrar a oferta?\n{nomes}")

    modelos = await client.approved_models()
    candidatos = match_models(draft.modelo, modelos)
    if not candidatos:
        return base.Ask(
            f'Não encontrei "{base.safe(draft.modelo)}" entre os modelos aprovados do catálogo. '
            "Se o modelo ainda não existe, cadastre-o na tela de modelos de placa "
            "(`/pt-BR/admin/modelos-de-placa-solar`) e peça de novo."
        )
    if len(candidatos) > 1:
        opcoes = base.options_text([base.safe(model_label(m)) for m in candidatos])
        return base.Ask(f"Encontrei mais de um modelo. Qual deles?\n{opcoes}")

    modelo = candidatos[0]
    payload = build_payload(draft, modelo, escolhido)
    return base.Ready(payload, render_proposal(payload, modelo, escolhido))


async def execute(client: ApiCoreClient, payload: dict) -> dict:
    return await client.create_offer(payload)


SPEC = base.ActionSpec(
    name=ACTION,
    descricao="create_offer: cadastrar uma oferta de placa solar da empresa (modelo, preço e quantidade).",
    prompt=OFFER_EXTRACTION_PROMPT,
    draft_model=OfferDraft,
    prepare=prepare,
    execute=execute,
    success=render_success,
    recusado="Tudo bem, não cadastrei nada.",
)
