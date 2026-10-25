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
from fastapi import FastAPI

from src.core.config.settings import settings
from src.version import VERSION

_SEM_TOKEN = "É preciso estar autenticado para executar ações na plataforma."

SKILLS = [
    Skill(
        id="operar-saas",
        name="Operar o SaaS",
        description=(
            "Executa no SaaS o que o usuário pede (por exemplo cadastrar uma placa ou a "
            "empresa) e indica onde ficam as telas. Ações que gravam dados são propostas "
            "antes e só valem depois do aceite do usuário."
        ),
        tags=["operação", "cadastro", "telas"],
        examples=[
            "Cadastra uma placa de 550 Wp da marca X",
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

    # Importado aqui para não compilar o grafo (e abrir o Mongo) ao importar o app.
    from src.workflow.graph.graph import compiled_app
    from src.workflow.runner import execute_turn

    final_state = await execute_turn(
        request.conversation_id,
        request.text,
        compiled_app,
        user_token=request.token,
    )
    # Uma proposta pendente espera a decisão do usuário: estado A2A "input_required".
    return TurnReply(
        text=str(final_state["messages"][-1].content),
        needs_input=bool(final_state.get("pending_proposal")),
    )


def mount(app: FastAPI) -> None:
    mount_a2a(app, build_card(), TurnExecutor(handle_turn))
