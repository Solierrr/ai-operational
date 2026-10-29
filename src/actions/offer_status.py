from typing import Literal

from pydantic import BaseModel

from src.actions import base
from src.actions.offer import model_label
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    OFFER_STATUS_EXTRACTION_PROMPT,
)
from src.infra.api_core.client import ApiCoreClient

ACTION = "set_offer_status"

STATUS_PT = {"ACTIVE": "ativa", "PAUSED": "pausada", "CLOSED": "encerrada"}
VERBO_PT = {"ACTIVE": "Reativar", "PAUSED": "Pausar", "CLOSED": "Encerrar"}


class OfferStatusDraft(BaseModel):
    oferta: str | None = None
    situacao: Literal["ACTIVE", "PAUSED", "CLOSED"] | None = None
    empresa: str | None = None


def offer_label(offer: dict) -> str:
    return model_label(offer.get("model") or {})


def offer_line(offer: dict) -> str:
    preco = offer.get("unitPrice")
    preco_txt = f" - {base.brl(float(preco))}" if preco is not None else ""
    situacao = STATUS_PT.get(offer.get("commercialStatus"), "")
    situacao_txt = f" ({situacao})" if situacao else ""
    return f"{base.safe(offer_label(offer))}{preco_txt}{situacao_txt}"


def _search_text(offer: dict) -> str:
    return f"{offer_label(offer)} {offer.get('slug') or ''}"


async def prepare(
    draft: OfferStatusDraft, client: ApiCoreClient
) -> base.Ask | base.Ready:
    ofertas = await client.my_offers()
    if not ofertas:
        return base.Ask("Sua empresa ainda não tem ofertas cadastradas.")
    ofertas = base.filter_by_company(ofertas, draft.empresa)

    if not draft.oferta:
        opcoes = base.options_text([offer_line(o) for o in ofertas])
        return base.Ask(f"Qual oferta devo alterar?\n{opcoes}")
    if not draft.situacao:
        return base.Ask(
            "O que devo fazer com a oferta: pausar, reativar ou encerrar? "
            "Encerrar não tem volta."
        )

    candidatas = [
        o for o in ofertas if base.label_matches(draft.oferta, _search_text(o))
    ]
    if not candidatas:
        opcoes = base.options_text([offer_line(o) for o in ofertas])
        return base.Ask(
            f'Não encontrei uma oferta "{base.safe(draft.oferta)}" na sua empresa. '
            f"Estas são as suas:\n{opcoes}"
        )
    if len(candidatas) > 1:
        opcoes = base.options_text([offer_line(o) for o in candidatas])
        return base.Ask(f"Encontrei mais de uma oferta. Qual delas?\n{opcoes}")

    oferta = candidatas[0]
    atual = oferta.get("commercialStatus")
    if atual == draft.situacao:
        return base.Ask(f"Essa oferta já está {STATUS_PT[atual]}.")
    if atual == "CLOSED":
        return base.Ask("Uma oferta encerrada não pode ser reaberta.")

    destino = draft.situacao
    resumo = (
        f"Posso alterar esta oferta, mas só depois do seu aceite:\n\n"
        f"- Oferta: {base.safe(offer_label(oferta))}\n"
        f"- Empresa: {base.safe(oferta['_empresa'])}\n"
        f"- Situação: {STATUS_PT.get(atual, atual)} -> {STATUS_PT[destino]}\n"
        f"- Ação: {VERBO_PT[destino]}"
    )
    payload = {
        "offerId": oferta["id"],
        "status": destino,
        "rotulo": base.safe(offer_label(oferta)),
    }
    return base.Ready(payload, resumo, irreversible=destino == "CLOSED")


async def execute(client: ApiCoreClient, payload: dict) -> dict:
    return await client.change_offer_status(payload["offerId"], payload["status"])


def success(resultado: dict, payload: dict) -> str:
    return f'Pronto, a oferta "{payload["rotulo"]}" agora está {STATUS_PT[payload["status"]]}.'


SPEC = base.ActionSpec(
    name=ACTION,
    descricao="set_offer_status: pausar, reativar ou encerrar uma oferta já cadastrada da empresa.",
    prompt=OFFER_STATUS_EXTRACTION_PROMPT,
    draft_model=OfferStatusDraft,
    prepare=prepare,
    execute=execute,
    success=success,
    recusado="Tudo bem, não alterei a oferta.",
)
