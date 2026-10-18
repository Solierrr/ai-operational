import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from ai_lib.a2a import TurnRequest, delegate
from fastapi import FastAPI
from langchain_core.messages import AIMessage

from src.a2a import server


def _fake_graph_modules(monkeypatch, final_text="Vou cadastrar a placa X. Aceita?"):
    execute_turn = AsyncMock(return_value={"messages": [AIMessage(content=final_text)]})
    monkeypatch.setitem(
        sys.modules, "src.workflow.graph.graph", SimpleNamespace(compiled_app="grafo")
    )
    monkeypatch.setitem(
        sys.modules, "src.workflow.runner", SimpleNamespace(execute_turn=execute_turn)
    )
    return execute_turn


def test_card_anuncia_a_habilidade_operacional():
    card = server.build_card()

    assert card.name == "Agente Operacional Solaria"
    assert [skill.id for skill in card.skills] == ["operar-saas"]


def test_sem_token_nao_chama_o_grafo(monkeypatch):
    execute_turn = _fake_graph_modules(monkeypatch)

    reply = asyncio.run(server.handle_turn(TurnRequest("oi", None, "demandante", "c1")))

    assert "autenticado" in reply.text
    execute_turn.assert_not_awaited()


def test_turno_repassa_conversa_e_token(monkeypatch):
    execute_turn = _fake_graph_modules(monkeypatch)

    reply = asyncio.run(
        server.handle_turn(TurnRequest("cadastra a placa X", "jwt", "demandante", "c1"))
    )

    assert reply.text == "Vou cadastrar a placa X. Aceita?"
    execute_turn.assert_awaited_once_with(
        "c1", "cadastra a placa X", "grafo", user_token="jwt"
    )


def test_delegacao_a2a_chega_ao_turno_do_agente(monkeypatch):
    execute_turn = _fake_graph_modules(monkeypatch)
    app = FastAPI()
    server.mount(app)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            headers={"Authorization": "Bearer jwt"},
        ) as http:
            card = await http.get(
                f"{server.settings.A2A_PUBLIC_URL}/.well-known/agent-card.json"
            )
            result = await delegate(
                server.settings.A2A_PUBLIC_URL,
                "cadastra a placa X",
                token="jwt",
                http_client=http,
            )
        return card, result

    card, result = asyncio.run(run())

    assert card.status_code == 200
    assert result.outcome == "completed"
    assert result.text == "Vou cadastrar a placa X. Aceita?"
    assert execute_turn.await_args.args[1] == "cadastra a placa X"
    assert execute_turn.await_args.kwargs == {"user_token": "jwt"}
