from pydantic import BaseModel, Field

from src.actions import base
from src.actions.offer import model_label
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    CART_EXTRACTION_PROMPT,
)
from src.infra.api_core.client import ApiCoreClient

ACTION = "update_cart"


class CartDraft(BaseModel):
    oferta: str | None = None
    quantidade: int | None = Field(default=None, ge=0)


def offer_label(offer: dict) -> str:
    return model_label(offer.get("model") or {})


def offer_line(offer: dict) -> str:
    preco = offer.get("unitPrice")
    preco_txt = f" - {base.brl(float(preco))}" if preco is not None else ""
    return f"{base.safe(offer_label(offer))}{preco_txt}"


async def prepare(draft: CartDraft, client: ApiCoreClient) -> base.Ask | base.Ready:
    if not draft.oferta:
        return base.Ask(
            "Qual placa quer no carrinho? Diga marca, modelo e potência, "
            'por exemplo "Canadian CS6R 550".'
        )
    if draft.quantidade is None:
        return base.Ask(
            "Quantas unidades quer no carrinho no total? Diga 0 para tirar o item."
        )

    ofertas = await client.catalog_offers()
    candidatas = [
        o
        for o in ofertas
        if o.get("commercialStatus", "ACTIVE") == "ACTIVE"
        and base.label_matches(draft.oferta, f"{offer_label(o)} {o.get('slug') or ''}")
    ]
    if not candidatas:
        return base.Ask(
            f'Não encontrei uma oferta de "{base.safe(draft.oferta)}" no catálogo. '
            "Procure na tela de placas solares (`/pt-BR/placas-solares`)."
        )
    if len(candidatas) > 1:
        opcoes = base.options_text([offer_line(o) for o in candidatas])
        return base.Ask(f"Encontrei mais de uma oferta. Qual delas?\n{opcoes}")

    oferta = candidatas[0]
    disponivel = oferta.get("availability")
    if isinstance(disponivel, int) and draft.quantidade > disponivel:
        return base.Ask(f"Só há {disponivel} unidades disponíveis dessa oferta.")

    rotulo = base.safe(offer_label(oferta))
    acao = (
        "tirar do carrinho"
        if draft.quantidade == 0
        else f"deixar o carrinho com {draft.quantidade} unidades"
    )
    resumo = (
        "Posso mexer no seu carrinho, mas só depois do seu aceite. Isso não finaliza compra:\n\n"
        f"- Placa: {offer_line(oferta)}\n"
        f"- Ação: {acao}"
    )
    payload = {"offerId": oferta["id"], "quantity": draft.quantidade, "rotulo": rotulo}
    return base.Ready(payload, resumo)


async def execute(client: ApiCoreClient, payload: dict) -> dict:
    if payload["quantity"] == 0:
        return await client.remove_cart_item(payload["offerId"])
    return await client.put_cart_item(payload["offerId"], payload["quantity"])


def success(resultado: dict, payload: dict) -> str:
    if payload["quantity"] == 0:
        return f'Pronto, tirei "{payload["rotulo"]}" do carrinho.'
    total = resultado.get("total") if isinstance(resultado, dict) else None
    total_txt = (
        f" Total do carrinho: {base.brl(float(total))}." if total is not None else ""
    )
    return (
        f"Pronto, o carrinho está com {payload['quantity']} unidades de "
        f'"{payload["rotulo"]}".{total_txt} Para finalizar a compra, use a tela do carrinho.'
    )


SPEC = base.ActionSpec(
    name=ACTION,
    descricao="update_cart: colocar, mudar a quantidade ou tirar uma placa do carrinho de compras (não finaliza compra).",
    prompt=CART_EXTRACTION_PROMPT,
    draft_model=CartDraft,
    prepare=prepare,
    execute=execute,
    success=success,
    recusado="Tudo bem, não mexi no carrinho.",
)
