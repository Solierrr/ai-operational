import asyncio
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage, HumanMessage

from src.workflow import config as workflow_config
from src.workflow.nodes import data_reader_node, how_to_guide_node


def _agente(texto):
    agente = Mock()
    agente.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content=texto)]})
    return agente


def test_guia_usa_so_ferramentas_de_consulta_de_conteudo(monkeypatch):
    construtor = Mock(return_value=_agente("1. Abra a tela"))
    monkeypatch.setattr(how_to_guide_node, "build_agent", construtor)

    result = asyncio.run(
        how_to_guide_node.how_to_guide_node(
            {"messages": [HumanMessage(content="como cadastro uma oferta?")]}
        )
    )

    nomes = {t.name for t in construtor.call_args.kwargs["tools"]}
    assert nomes == {"buscar_guia", "buscar_tela"}
    assert result["messages"][0].content == "1. Abra a tela"
    assert result["turn_agents"] == ["how_to_guide"]


def test_consulta_so_recebe_as_ferramentas_de_leitura(monkeypatch):
    construtor = Mock(return_value=_agente("Você tem 2 ofertas"))
    monkeypatch.setattr(data_reader_node, "build_agent", construtor)

    result = asyncio.run(
        data_reader_node.data_reader_node(
            {
                "messages": [HumanMessage(content="quais minhas ofertas?")],
                "turn_agents": ["router"],
            }
        )
    )

    nomes = {t.name for t in construtor.call_args.kwargs["tools"]}
    assert "minhas_ofertas" in nomes
    assert not nomes & {"criar_oferta", "cancelar_pedido", "alterar_estoque"}
    assert result["turn_agents"] == ["router", "data_reader"]


def test_rotas_registradas_no_config():
    assert {"how_to_guide", "data_reader", "screen_finder", "action_proposer"} == set(
        workflow_config.SPECIALIST_ROUTES
    )
