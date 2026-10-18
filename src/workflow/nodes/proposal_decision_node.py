import logging

from pydantic import ValidationError

from src.actions import offer
from src.actions.decision import quick_decision
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    DECISION_PROMPT,
    QUESTION_PROMPT,
)
from src.core.security.request_context import current_user_token
from src.infra.api_core.client import ApiCoreClient, ApiCoreError
from src.workflow.nodes.llm_json import InvalidJsonReply, ask_json, ask_text
from src.workflow.nodes.replies import reply
from src.workflow.state import GraphState

logger = logging.getLogger(__name__)

AGENT = "proposal_decision"

_SEM_TOKEN = (
    "Para executar a ação é preciso estar autenticado. A proposta foi descartada."
)
_RECUSADO = "Tudo bem, não cadastrei nada."
_REFAZER = (
    "Não consegui validar essa proposta. Pode me pedir de novo o que quer cadastrar?"
)


def _ultima_mensagem(state: GraphState) -> str:
    return str(state["messages"][-1].content)


async def classify(proposta: str, resposta: str, config=None) -> str:
    rapida = quick_decision(resposta)
    if rapida:
        return rapida
    try:
        dados = await ask_json(
            DECISION_PROMPT.format(proposta=proposta, resposta=resposta), config
        )
        decisao = dados.get("decisao")
    except InvalidJsonReply:
        return "duvida"
    return decisao if decisao in {"aceitar", "recusar", "duvida"} else "duvida"


async def proposal_decision_node(state: GraphState, config=None) -> dict:
    """Trata a resposta do usuário a uma proposta pendente: aceitar executa no
    api-core com o JWT dele, recusar descarta e dúvida responde e mantém a proposta."""
    pendente = state.get("pending_proposal") or {}
    if pendente.get("action") != offer.ACTION or "payload" not in pendente:
        return reply(state, AGENT, _REFAZER, pending_proposal=None)

    resposta = _ultima_mensagem(state)
    decisao = await classify(pendente.get("resumo", ""), resposta, config)

    if decisao == "recusar":
        return reply(state, AGENT, _RECUSADO, pending_proposal=None)

    if decisao == "aceitar":
        token = current_user_token.get()
        if not token:
            return reply(state, AGENT, _SEM_TOKEN, pending_proposal=None)
        payload = pendente["payload"]
        try:
            criada = await ApiCoreClient(token).create_offer(payload)
        except ApiCoreError as erro:
            return reply(
                state,
                AGENT,
                f"Não consegui cadastrar a oferta. {erro.message}",
                pending_proposal=None,
            )
        return reply(
            state, AGENT, offer.render_success(criada, payload), pending_proposal=None
        )

    try:
        explicacao = await ask_text(
            QUESTION_PROMPT.format(
                proposta=pendente.get("resumo", ""), mensagem=resposta
            ),
            config,
        )
    except (ValidationError, ValueError):
        logger.warning("Falha ao responder a dúvida sobre a proposta", exc_info=True)
        explicacao = ""
    texto = (
        (explicacao + "\n\n" if explicacao else "")
        + 'A proposta continua pendente. Responda "sim" para cadastrar ou "não" para cancelar.'
    )
    return reply(state, AGENT, texto)
