"""Servidor A2A do agente operacional: outros agentes (como o ai-assistant) delegam
aqui as ações no SaaS que o usuário pede."""

from ai_lib.a2a import (
    Skill,
    TurnExecutor,
    TurnReply,
    TurnRequest,
    build_agent_card,
    mount_a2a,
)
from fastapi import FastAPI, HTTPException

from src.api.auth import require_valid_token
from src.core.config.settings import settings
from src.core.security.conversation_access import ConversationAccessDenied
from src.version import VERSION

_SEM_TOKEN = "É preciso estar autenticado para executar ações na plataforma."
_TOKEN_INVALIDO = "Sua sessão expirou ou é inválida. Entre de novo para continuar."
_OUTRO_USUARIO = "Esta conversa não pertence a você."

SKILLS = [
    Skill(
        id="operar-saas",
        name="Operar o SaaS",
        description=(
            "Explica como fazer cada tarefa na plataforma, indica onde ficam as telas, "
            "mostra os dados do usuário (ofertas, estoque, pedidos, carrinho, vendas, "
            "assinatura) e executa no SaaS o que ele pede: cadastrar, pausar, reativar "
            "ou encerrar ofertas, ajustar estoque, cancelar pedidos e mexer no carrinho. "
            "Ações que gravam dados são propostas antes e só valem depois do aceite "
            "explícito do usuário."
        ),
        tags=["operação", "cadastro", "telas"],
        examples=[
            "Cadastra uma placa de 550 Wp da marca X",
            "Como eu pauso uma oferta?",
            "Quais são as minhas ofertas?",
            "Onde fica a tela de ofertas?",
        ],
    )
]


def build_card():
    return build_agent_card(
        name="Agente Operacional Solaria",
        description="Executa ações no SaaS em nome do usuário, com aprovação antes de gravar.",
        version=VERSION,
        base_url=settings.A2A_PUBLIC_URL,
        skills=SKILLS,
    )


async def handle_turn(request: TurnRequest) -> TurnReply:
    if not request.token:
        return TurnReply(text=_SEM_TOKEN)
    try:
        await require_valid_token(request.token)
    except HTTPException:
        return TurnReply(text=_TOKEN_INVALIDO)

    # Importado aqui para não compilar o grafo (e abrir o Mongo) ao importar o app.
    from src.workflow.graph.graph import compiled_app
    from src.workflow.runner import execute_turn

    try:
        final_state = await execute_turn(
            request.conversation_id,
            request.text,
            compiled_app,
            user_token=request.token,
        )
    except ConversationAccessDenied:
        return TurnReply(text=_OUTRO_USUARIO)
    # Uma proposta pendente espera a decisão do usuário: estado A2A "input_required".
    return TurnReply(
        text=str(final_state["messages"][-1].content),
        needs_input=bool(final_state.get("pending_proposal")),
    )


def mount(app: FastAPI) -> None:
    mount_a2a(app, build_card(), TurnExecutor(handle_turn))
