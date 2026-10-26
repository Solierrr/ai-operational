import logging

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from src.actions import offer
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    OFFER_EXTRACTION_PROMPT,
)
from src.core.security.request_context import current_user_token
from src.infra.api_core.client import ApiCoreClient, ApiCoreError
from src.workflow.nodes.llm_json import InvalidJsonReply, ask_json
from src.workflow.nodes.replies import reply
from src.workflow.outcome import Outcome, Reason
from src.workflow.state import GraphState

logger = logging.getLogger(__name__)

AGENT = "action_proposer"
_MENSAGENS_NO_CONTEXTO = 8

_SEM_TOKEN = "Para propor uma ação na plataforma é preciso estar autenticado."
_NAO_ENTENDI = (
    "Não consegui entender qual ação você quer fazer. Hoje eu cadastro ofertas de placas; "
    "para outras coisas, posso indicar a tela certa."
)
_SEM_FORNECEDOR = (
    "Sua conta não está ligada a uma empresa fornecedora, então não posso cadastrar ofertas. "
    "Cadastre a empresa pela tela de cadastro de empresa (`/pt-BR/cadastro/empresa`) e peça de novo."
)


def _conversa(state: GraphState) -> str:
    linhas = []
    for mensagem in state["messages"][-_MENSAGENS_NO_CONTEXTO:]:
        autor = "Usuário" if isinstance(mensagem, HumanMessage) else "Assistente"
        linhas.append(f"{autor}: {mensagem.content}")
    return "\n".join(linhas)


async def action_proposer_node(state: GraphState, config=None) -> dict:
    """Entende o pedido de cadastrar uma oferta, completa o que falta e devolve a
    proposta. Não grava nada: a proposta fica em `pending_proposal` até o aceite."""
    token = current_user_token.get()
    if not token:
        return reply(state, AGENT, _SEM_TOKEN)

    try:
        dados = await ask_json(
            OFFER_EXTRACTION_PROMPT.format(conversa=_conversa(state)), config
        )
        rascunho = offer.OfferDraft.model_validate(dados)
    except (InvalidJsonReply, ValidationError):
        logger.warning("Não foi possível extrair o rascunho da oferta", exc_info=True)
        return reply(state, AGENT, _NAO_ENTENDI)

    faltando = offer.missing_fields(rascunho)
    if faltando:
        itens = "\n".join(f"- {item}" for item in faltando)
        return reply(
            state, AGENT, f"Para cadastrar a oferta ainda preciso saber:\n{itens}"
        )

    client = ApiCoreClient(token)
    try:
        fornecedores = await client.my_suppliers()
        if not fornecedores:
            return reply(state, AGENT, _SEM_FORNECEDOR)
        escolhido = offer.pick_supplier(rascunho, fornecedores)
        if isinstance(escolhido, list):
            nomes = "\n".join(f"- {s.company_name}" for s in escolhido)
            return reply(
                state, AGENT, f"Em qual empresa devo cadastrar a oferta?\n{nomes}"
            )

        modelos = await client.approved_models()
    except ApiCoreError as erro:
        return reply(
            state,
            AGENT,
            erro.message,
            outcome=(Outcome.TOOL_FAILED, Reason.ACTION_FAILED),
        )

    candidatos = offer.match_models(rascunho.modelo, modelos)
    if not candidatos:
        return reply(
            state,
            AGENT,
            f'Não encontrei "{rascunho.modelo}" entre os modelos aprovados do catálogo. '
            "Se o modelo ainda não existe, cadastre-o na tela de modelos de placa "
            "(`/pt-BR/admin/modelos-de-placa-solar`) e peça de novo.",
        )
    if len(candidatos) > 1:
        opcoes = "\n".join(
            f"- {offer.model_label(m)}" for m in candidatos[: offer.MAX_OPCOES]
        )
        return reply(
            state, AGENT, f"Encontrei mais de um modelo. Qual deles?\n{opcoes}"
        )

    modelo = candidatos[0]
    payload = offer.build_payload(rascunho, modelo, escolhido)
    proposta = offer.render_proposal(payload, modelo, escolhido)
    return reply(
        state,
        AGENT,
        proposta,
        pending_proposal={
            "action": offer.ACTION,
            "payload": payload,
            "resumo": proposta,
        },
    )
