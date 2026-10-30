import logging
import re

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from src.actions.base import Ask, render_proposal
from src.actions.proposal import make_proposal
from src.actions.registry import (
    ACAO_PROIBIDA,
    describe_actions,
    get_action,
)
from src.agents.specialist.action_proposer.action_proposer_prompt import (
    ACTION_SELECTION_PROMPT,
)
from src.core.config.settings import settings
from src.core.security.request_context import current_user_token
from src.core.security.untrusted import wrap_untrusted
from src.domain.screens import find_screens
from src.domain.text import normalize
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
    "Não consegui entender qual ação você quer fazer. Eu posso cadastrar ofertas de placas, "
    "pausar, reativar ou encerrar uma oferta, ajustar o estoque, cancelar um pedido seu e "
    "mexer no seu carrinho; para outras coisas, posso indicar a tela certa."
)
_LIMITE = (
    "Já fiz muitas alterações nesta conversa. Por segurança, comece uma nova conversa "
    "para continuar, ou faça o restante direto nas telas da plataforma."
)
_PROIBIDO = (
    "Por segurança, eu não faço compras, pagamentos, exclusões, transferências nem "
    "mudanças de senha, cargo ou permissão por você. Isso você faz direto na plataforma"
)

_PEDIDO_PROIBIDO = re.compile(
    r"\b(?:finaliz\w+|conclu\w+|fech\w+|efetu\w+|realiz\w+)\s+(?:a\s+|minha\s+|o\s+|meu\s+|um\s+)*(?:compra|pedido|pagamento|checkout|carrinho)"
    r"|\b(?:pagar|pague|paga|comprar|compre|transferir|transfira|excluir|exclua|apagar|apague|deletar|delete|remover\s+(?:a\s+)?(?:conta|empresa))\b"
    r"|\b(?:alter\w+|tro[cq]\w+|mud\w+|redefin\w+)\s+(?:a\s+|minha\s+)*senha"
    r"|\b(?:dar|conced\w+|alter\w+|tro[cq]\w+|mud\w+)\s+(?:o\s+|um\s+)?(?:cargo|permiss\w+)"
    r"|\b(?:de|da)\s+(?:o\s+|um\s+)?(?:cargo|permiss\w+)\b"
)


def _conversa(state: GraphState) -> str:
    linhas = []
    for mensagem in state["messages"][-_MENSAGENS_NO_CONTEXTO:]:
        autor = "Usuário" if isinstance(mensagem, HumanMessage) else "Assistente"
        linhas.append(f"{autor}: {mensagem.content}")
    return wrap_untrusted("conversa", "\n".join(linhas))


def _ultima_do_usuario(state: GraphState) -> str:
    for mensagem in reversed(state["messages"]):
        if isinstance(mensagem, HumanMessage):
            return str(mensagem.content)
    return ""


_FINALIZA_COMPRA = re.compile(r"\b(?:finaliz\w+|pagar|pague|paga|pagamento|checkout)\b")


def _pedido_proibido(texto: str) -> bool:
    limpo = normalize(texto)
    if "carrinho" in limpo and not _FINALIZA_COMPRA.search(limpo):
        return False
    return bool(_PEDIDO_PROIBIDO.search(limpo))


def _resposta_proibida(texto: str) -> str:
    telas = find_screens(texto, limit=1)
    if telas:
        return f"{_PROIBIDO}: {telas[0]['tela']} (`{telas[0]['caminho']}`)."
    return f"{_PROIBIDO}."


async def action_proposer_node(state: GraphState, config=None) -> dict:
    token = current_user_token.get()
    if not token:
        return reply(state, AGENT, _SEM_TOKEN)

    if state.get("writes_done", 0) >= settings.MAX_WRITES_PER_CONVERSATION:
        logger.warning("Limite de ações por conversa atingido")
        return reply(state, AGENT, _LIMITE)

    ultima = _ultima_do_usuario(state)
    if _pedido_proibido(ultima):
        logger.info("Pedido de ação proibida recusado")
        return reply(state, AGENT, _resposta_proibida(ultima))

    conversa = _conversa(state)
    try:
        escolha = await ask_json(
            ACTION_SELECTION_PROMPT.format(acoes=describe_actions(), conversa=conversa),
            config,
        )
    except InvalidJsonReply:
        logger.warning("Não foi possível escolher a ação", exc_info=True)
        return reply(state, AGENT, _NAO_ENTENDI)

    nome = escolha.get("acao")
    if nome == ACAO_PROIBIDA:
        logger.info("Ação proibida recusada pelo seletor")
        return reply(state, AGENT, _resposta_proibida(ultima))
    spec = get_action(nome)
    if spec is None:
        return reply(state, AGENT, _NAO_ENTENDI)

    try:
        dados = await ask_json(spec.prompt.format(conversa=conversa), config)
        rascunho = spec.draft_model.model_validate(dados)
    except (InvalidJsonReply, ValidationError):
        logger.warning(
            "Não foi possível extrair o rascunho de %s", spec.name, exc_info=True
        )
        return reply(state, AGENT, _NAO_ENTENDI)

    try:
        resultado = await spec.prepare(rascunho, ApiCoreClient(token))
    except ApiCoreError as erro:
        return reply(
            state,
            AGENT,
            erro.message,
            outcome=(Outcome.TOOL_FAILED, Reason.ACTION_FAILED),
        )

    if isinstance(resultado, Ask):
        return reply(state, AGENT, resultado.text)

    proposta = render_proposal(resultado)
    pendente = make_proposal(
        spec.name,
        resultado.payload,
        proposta,
        state.get("user_id"),
        resultado.irreversible,
    )
    logger.info("Proposta %s criada para %s", pendente["id"], spec.name)
    return reply(state, AGENT, proposta, pending_proposal=pendente)
