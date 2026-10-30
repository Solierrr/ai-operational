"""Fluxo completo no grafo real, com LLMs e api-core simulados: a proposta de uma
oferta nasce em um turno, fica pendente no estado e só é executada no turno seguinte."""

import asyncio
import importlib
import sys
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from src.core.security.request_context import current_user_token, debug_dry_run
from src.infra.api_core.client import SupplierRef

DADOS = {
    "modelo": "Canadian CS6R",
    "preco_unitario": 900.5,
    "disponibilidade": 40,
    "titulo": None,
    "descricao": None,
    "empresa": None,
}
MODELO = {"id": "m1", "brand": "Canadian", "model": "CS6R", "powerWp": 550.0}


def _llm(texto: str) -> Mock:
    llm = Mock()
    llm.invoke.return_value = AIMessage(content=texto)
    return llm


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        "src.memory.session.mongo_checkpointer.create_mongo_checkpointer",
        lambda: InMemorySaver(),
    )
    sys.modules.pop("src.workflow.graph.graph", None)
    graph = importlib.import_module("src.workflow.graph.graph")

    client = Mock()
    client.my_suppliers = AsyncMock(
        return_value=[SupplierRef("s1", "c1", "ACME Solar")]
    )
    client.approved_models = AsyncMock(return_value=[MODELO])
    client.create_offer = AsyncMock(return_value={"id": "o1"})
    factory = Mock(return_value=client)

    guardrail = importlib.import_module("src.workflow.nodes.input_guardrail_node")
    router = importlib.import_module("src.workflow.nodes.router_node")
    proposer = importlib.import_module("src.workflow.nodes.action_proposer_node")
    decision = importlib.import_module("src.workflow.nodes.proposal_decision_node")
    monkeypatch.setattr(
        guardrail, "llm_groq", lambda: _llm("CATEGORIA: APROVADO\nJUSTIFICATIVA: ok")
    )
    monkeypatch.setattr(
        router, "llm_groq", lambda: _llm("ROTA: action_proposer\nRESPOSTA_DIRETA:")
    )

    async def ask_json(prompt, config=None):
        if "Ações disponíveis" in prompt:
            return {"acao": "create_offer"}
        return DADOS

    monkeypatch.setattr(proposer, "ask_json", ask_json)
    monkeypatch.setattr(proposer, "ApiCoreClient", factory)
    monkeypatch.setattr(decision, "ApiCoreClient", factory)

    token = current_user_token.set("jwt-do-usuario")
    yield graph.compiled_app, client
    current_user_token.reset(token)
    sys.modules.pop("src.workflow.graph.graph", None)


def _turno(compiled, texto: str) -> dict:
    estado = {
        "messages": [HumanMessage(content=texto)],
        "route": "",
        "pii_map": {},
        "turn_agents": [],
        "judge_retries": 0,
        "user_id": None,
        "user_memory": "",
    }
    return asyncio.run(
        compiled.ainvoke(estado, config={"configurable": {"thread_id": "conversa-1"}})
    )


def test_proposta_num_turno_e_execucao_so_depois_do_aceite(app):
    compiled, client = app

    primeiro = _turno(compiled, "cadastra a Canadian CS6R a 900,50 com 40 unidades")

    assert "só depois do seu aceite" in primeiro["messages"][-1].content
    assert primeiro["pending_proposal"]["payload"]["modelId"] == "m1"
    client.create_offer.assert_not_awaited()

    segundo = _turno(compiled, "sim")

    client.create_offer.assert_awaited_once()
    assert "foi cadastrada" in segundo["messages"][-1].content
    assert segundo["pending_proposal"] is None


def test_recusa_depois_da_proposta_nao_grava_e_limpa_o_estado(app):
    compiled, client = app

    _turno(compiled, "cadastra a Canadian CS6R a 900,50 com 40 unidades")
    segundo = _turno(compiled, "não")

    client.create_offer.assert_not_awaited()
    assert "não cadastrei nada" in segundo["messages"][-1].content
    assert segundo["pending_proposal"] is None


def test_aceite_repetido_depois_de_executar_nao_grava_duas_vezes(app, monkeypatch):
    compiled, client = app
    router = importlib.import_module("src.workflow.nodes.router_node")
    output = importlib.import_module("src.workflow.nodes.output_guardrail_node")
    _turno(compiled, "cadastra a Canadian CS6R a 900,50 com 40 unidades")
    _turno(compiled, "sim")

    # Sem proposta pendente, o roteador volta a decidir pelo LLM e responde direto.
    monkeypatch.setattr(
        router,
        "llm_groq",
        lambda: _llm("ROTA: None\nRESPOSTA_DIRETA: Não há nada pendente."),
    )
    monkeypatch.setattr(
        output,
        "llm_groq",
        lambda: _llm("STATUS: APROVADO\nRESPOSTA: Não há nada pendente."),
    )
    terceiro = _turno(compiled, "sim")

    client.create_offer.assert_awaited_once()
    assert terceiro["pending_proposal"] is None


def test_aceite_em_modo_debug_simula_e_nao_grava_no_api_core(app):
    compiled, client = app
    token = debug_dry_run.set(True)
    try:
        _turno(compiled, "cadastra a Canadian CS6R a 900,50 com 40 unidades")
        segundo = _turno(compiled, "sim")
    finally:
        debug_dry_run.reset(token)

    client.create_offer.assert_not_awaited()
    assert "[Modo debug] Simulação" in segundo["messages"][-1].content
    assert segundo["pending_proposal"] is None


def test_ajuste_descarta_a_proposta_e_gera_outra_com_o_valor_novo(app, monkeypatch):
    compiled, client = app
    decision = importlib.import_module("src.workflow.nodes.proposal_decision_node")
    proposer = importlib.import_module("src.workflow.nodes.action_proposer_node")
    primeiro = _turno(compiled, "cadastra a Canadian CS6R a 900,50 com 40 unidades")
    id_antigo = primeiro["pending_proposal"]["id"]

    async def ask_json(prompt, config=None):
        if "Ações disponíveis" in prompt:
            return {"acao": "create_offer"}
        return {**DADOS, "preco_unitario": 800}

    monkeypatch.setattr(
        decision, "ask_json", AsyncMock(return_value={"decisao": "ajustar"})
    )
    monkeypatch.setattr(proposer, "ask_json", ask_json)

    segundo = _turno(compiled, "muda o preço para 800")

    client.create_offer.assert_not_awaited()
    assert "R$ 800,00" in segundo["messages"][-1].content
    assert segundo["pending_proposal"]["id"] != id_antigo
    assert segundo["pending_proposal"]["payload"]["unitPrice"] == 800.0


def test_aceite_so_executa_a_proposta_vigente_com_o_payload_assinado(app):
    compiled, client = app
    primeiro = _turno(compiled, "cadastra a Canadian CS6R a 900,50 com 40 unidades")

    _turno(compiled, "sim")

    client.create_offer.assert_awaited_once_with(
        primeiro["pending_proposal"]["payload"]
    )
