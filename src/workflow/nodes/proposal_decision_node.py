import logging

from pydantic import ValidationError

from src.actions import proposal as proposals
from src.actions.decision import EXIGE_CONFIRMO, strict_decision
from src.actions.registry import get_action
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    DECISION_PROMPT,
    QUESTION_PROMPT,
)
from src.core.config.settings import settings
from src.core.security.request_context import current_user_token, debug_dry_run
from src.core.security.untrusted import wrap_untrusted
from src.infra.api_core.client import ApiCoreClient, ApiCoreError
from src.workflow.nodes.llm_json import InvalidJsonReply, ask_json, ask_text
from src.workflow.nodes.replies import reply
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

logger = logging.getLogger(__name__)

AGENT = "proposal_decision"

_SEM_TOKEN = (
    "Para executar a ação é preciso estar autenticado. A proposta foi descartada."
)
_SIMULADO = "[Modo debug] Simulação: a ação seria executada agora, mas nada foi gravado no api-core."
_REFAZER = "Não consegui validar essa proposta. Pode me pedir de novo o que quer fazer?"
_EXPIROU = (
    "Essa proposta expirou por segurança e nada foi feito. Pode me pedir de novo?"
)
_LIMITE = (
    "Já fiz muitas alterações nesta conversa. Por segurança, nada foi executado; "
    "comece uma nova conversa para continuar."
)
_PEDE_CONFIRMO = (
    'Essa ação não pode ser desfeita, então preciso que você responda exatamente "confirmo" '
    'para executar. Se não quiser, responda "não". A proposta continua pendente.'
)
_INCERTO = (
    "Não consegui confirmar se a ação foi executada, porque o sistema não respondeu. "
    "Confira nas telas da plataforma antes de pedir de novo, para não repetir."
)
_RESPOSTAS_LLM = {"recusar", "duvida", "ajustar", "outro"}


def _ultima_mensagem(state: GraphState) -> str:
    return str(state["messages"][-1].content)


async def classify(
    proposta: str,
    resposta: str,
    config=None,
    irreversible: bool = False,
    after_doubt: bool = False,
) -> str:
    rapida = strict_decision(resposta, irreversible, after_doubt)
    if rapida:
        return rapida
    try:
        dados = await ask_json(
            DECISION_PROMPT.format(
                proposta=proposta, resposta=wrap_untrusted("resposta", resposta)
            ),
            config,
        )
        decisao = dados.get("decisao")
    except InvalidJsonReply:
        return "duvida"
    return decisao if decisao in _RESPOSTAS_LLM else "duvida"


def _pendente_texto(irreversivel: bool) -> str:
    if irreversivel:
        return 'A proposta continua pendente. Responda "confirmo" para executar ou "não" para cancelar.'
    return 'A proposta continua pendente. Responda "sim" para executar ou "não" para cancelar.'


async def _executar(state: GraphState, spec, pendente: dict) -> dict:
    token = current_user_token.get()
    if not token:
        return reply(state, AGENT, _SEM_TOKEN, pending_proposal=None)
    if state.get("writes_done", 0) >= settings.MAX_WRITES_PER_CONVERSATION:
        logger.warning("Limite de ações por conversa atingido na execução")
        return reply(state, AGENT, _LIMITE, pending_proposal=None)
    if debug_dry_run.get():
        return reply(state, AGENT, _SIMULADO, pending_proposal=None)

    payload = pendente["payload"]
    try:
        resultado = await spec.execute(ApiCoreClient(token), payload)
    except ApiCoreError as erro:
        logger.info(
            "Ação %s recusada pelo api-core (status=%s)", spec.name, erro.status
        )
        texto = (
            _INCERTO
            if erro.status is None
            else f"Não consegui executar. {erro.message}"
        )
        return reply(state, AGENT, texto, pending_proposal=None)
    logger.info("Ação %s executada (proposta %s)", spec.name, pendente.get("id"))
    return reply(
        state,
        AGENT,
        spec.success(resultado, payload),
        pending_proposal=None,
        writes_done=state.get("writes_done", 0) + 1,
    )


async def proposal_decision_node(state: GraphState, config=None) -> dict:
    pendente = state.get("pending_proposal") or {}
    spec = get_action(pendente.get("action"))
    verificacao = proposals.verify_proposal(pendente, state.get("user_id"))
    if spec is None or "payload" not in pendente:
        return reply(state, AGENT, _REFAZER, pending_proposal=None)
    if verificacao == proposals.EXPIRADA:
        if strict_decision(_ultima_mensagem(state), False):
            return reply(state, AGENT, _EXPIROU, pending_proposal=None)
        return {
            "pending_proposal": None,
            "route": "reroute",
            "turn_agents": append_turn_agent(state, AGENT),
        }
    if verificacao != proposals.OK:
        logger.warning("Proposta rejeitada na verificação (%s)", verificacao)
        return reply(state, AGENT, _REFAZER, pending_proposal=None)

    irreversivel = bool(pendente.get("irreversivel"))
    resposta = _ultima_mensagem(state)
    decisao = await classify(
        pendente.get("resumo", ""),
        resposta,
        config,
        irreversivel,
        bool(pendente.get("em_duvida")),
    )

    if decisao == "recusar":
        return reply(state, AGENT, spec.recusado, pending_proposal=None)

    if decisao == "aceitar":
        return await _executar(state, spec, pendente)

    if decisao == EXIGE_CONFIRMO:
        return reply(state, AGENT, _PEDE_CONFIRMO)

    if decisao in {"ajustar", "outro"}:
        return {
            "pending_proposal": None,
            "route": "reroute",
            "turn_agents": append_turn_agent(state, AGENT),
        }

    try:
        explicacao = await ask_text(
            QUESTION_PROMPT.format(
                proposta=pendente.get("resumo", ""),
                mensagem=wrap_untrusted("mensagem", resposta),
            ),
            config,
        )
    except (ValidationError, ValueError):
        logger.warning("Falha ao responder a dúvida sobre a proposta", exc_info=True)
        explicacao = ""
    texto = (explicacao + "\n\n" if explicacao else "") + _pendente_texto(irreversivel)
    return reply(state, AGENT, texto, pending_proposal={**pendente, "em_duvida": True})
