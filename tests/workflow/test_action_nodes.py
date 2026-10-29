import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.actions.proposal import make_proposal
from src.core.security.request_context import current_user_token
from src.infra.api_core.client import ApiCoreError, SupplierRef
from src.workflow.nodes import action_proposer_node as proposer
from src.workflow.nodes import proposal_decision_node as decision
from src.workflow.nodes import router_node
from src.workflow.nodes.llm_json import InvalidJsonReply, parse_json_object

ACME = SupplierRef("s1", "c1", "ACME Solar")
MODELO = {"id": "m1", "brand": "Canadian", "model": "CS6R", "powerWp": 550.0}
DADOS = {
    "modelo": "Canadian CS6R",
    "preco_unitario": 900.5,
    "disponibilidade": 40,
    "titulo": None,
    "descricao": None,
    "empresa": None,
}
STATE = {
    "messages": [
        HumanMessage(content="cadastra a Canadian CS6R a 900,50 com 40 unidades")
    ]
}


@pytest.fixture(autouse=True)
def _token():
    valor = current_user_token.set("jwt-do-usuario")
    yield
    current_user_token.reset(valor)


def _core(monkeypatch, suppliers=(ACME,), models=(MODELO,), create=None):
    client = Mock()
    client.my_suppliers = AsyncMock(return_value=list(suppliers))
    client.approved_models = AsyncMock(return_value=list(models))
    client.create_offer = AsyncMock(return_value=create or {"id": "o1"})
    factory = Mock(return_value=client)
    monkeypatch.setattr(proposer, "ApiCoreClient", factory)
    monkeypatch.setattr(decision, "ApiCoreClient", factory)
    return client


def _json(monkeypatch, dados, acao="create_offer"):
    monkeypatch.setattr(
        proposer, "ask_json", AsyncMock(side_effect=[{"acao": acao}, dados])
    )


def _propor(state=STATE):
    return asyncio.run(proposer.action_proposer_node(state))


def test_proposta_completa_guarda_o_pedido_e_nao_grava(monkeypatch):
    client = _core(monkeypatch)
    _json(monkeypatch, DADOS)

    result = _propor()

    texto = result["messages"][0].content
    assert "só depois do seu aceite" in texto
    assert "R$ 900,50" in texto
    pendente = result["pending_proposal"]
    assert pendente["action"] == "create_offer"
    assert pendente["payload"]["modelId"] == "m1"
    assert pendente["payload"]["supplierId"] == "s1"
    client.create_offer.assert_not_awaited()
    assert result["turn_agents"] == ["action_proposer"]


def test_falta_de_dados_pergunta_sem_consultar_o_api_core(monkeypatch):
    client = _core(monkeypatch)
    _json(monkeypatch, {**DADOS, "preco_unitario": None, "disponibilidade": None})

    result = _propor()

    assert "preço" in result["messages"][0].content
    assert "quantidade" in result["messages"][0].content
    assert "pending_proposal" not in result
    client.my_suppliers.assert_not_awaited()


def test_resposta_do_llm_invalida_pede_para_reformular(monkeypatch):
    _core(monkeypatch)
    monkeypatch.setattr(
        proposer, "ask_json", AsyncMock(side_effect=InvalidJsonReply("x"))
    )

    result = _propor()

    assert "Não consegui entender" in result["messages"][0].content


def test_preco_negativo_do_llm_nao_vira_proposta(monkeypatch):
    _core(monkeypatch)
    _json(monkeypatch, {**DADOS, "preco_unitario": -1})

    result = _propor()

    assert "Não consegui entender" in result["messages"][0].content
    assert "pending_proposal" not in result


def test_sem_empresa_fornecedora_orienta_o_cadastro(monkeypatch):
    _core(monkeypatch, suppliers=())
    _json(monkeypatch, DADOS)

    result = _propor()

    assert "empresa fornecedora" in result["messages"][0].content
    assert "pending_proposal" not in result


def test_varias_empresas_perguntam_qual(monkeypatch):
    _core(monkeypatch, suppliers=(ACME, SupplierRef("s2", "c2", "Beta Energia")))
    _json(monkeypatch, DADOS)

    result = _propor()

    assert "Em qual empresa" in result["messages"][0].content
    assert "Beta Energia" in result["messages"][0].content


def test_modelo_inexistente_indica_a_tela_de_modelos(monkeypatch):
    _core(monkeypatch, models=())
    _json(monkeypatch, DADOS)

    result = _propor()

    assert "modelos de placa" in result["messages"][0].content
    assert "pending_proposal" not in result


def test_modelo_ambiguo_lista_as_opcoes(monkeypatch):
    outro = {"id": "m2", "brand": "Canadian", "model": "CS6R", "powerWp": 600.0}
    _core(monkeypatch, models=(MODELO, outro))
    _json(monkeypatch, {**DADOS, "modelo": "Canadian CS6R"})

    result = _propor()

    assert "mais de um modelo" in result["messages"][0].content
    assert "600 Wp" in result["messages"][0].content


def test_falha_do_api_core_vira_mensagem_sem_proposta(monkeypatch):
    client = _core(monkeypatch)
    client.my_suppliers.side_effect = ApiCoreError(
        "O sistema está indisponível no momento."
    )
    _json(monkeypatch, DADOS)

    result = _propor()

    assert "indisponível" in result["messages"][0].content
    assert "pending_proposal" not in result


def test_sem_token_nao_propoe(monkeypatch):
    _core(monkeypatch)
    _json(monkeypatch, DADOS)
    current_user_token.set(None)

    assert "autenticado" in _propor()["messages"][0].content


# ---- decisão sobre a proposta pendente

PENDENTE = make_proposal(
    "create_offer",
    {
        "supplierId": "s1",
        "modelId": "m1",
        "title": "Placa X",
        "unitPrice": 900.5,
        "availability": 40,
    },
    "Posso cadastrar esta oferta...",
    None,
)


def _decidir(texto, pendente=PENDENTE):
    state = {"messages": [HumanMessage(content=texto)], "pending_proposal": pendente}
    return asyncio.run(decision.proposal_decision_node(state))


@pytest.mark.parametrize(
    "texto", ["sim", "Sim!", "pode cadastrar", "ACEITO", "isso mesmo", "confirmo."]
)
def test_aceite_claro_executa_com_o_token_do_usuario(monkeypatch, texto):
    client = _core(monkeypatch)

    result = _decidir(texto)

    client.create_offer.assert_awaited_once_with(PENDENTE["payload"])
    decision.ApiCoreClient.assert_called_with("jwt-do-usuario")
    assert "foi cadastrada" in result["messages"][0].content
    assert result["pending_proposal"] is None


@pytest.mark.parametrize(
    "texto", ["não", "Nao", "cancela", "melhor não", "deixa pra lá"]
)
def test_recusa_descarta_sem_gravar(monkeypatch, texto):
    client = _core(monkeypatch)

    result = _decidir(texto)

    client.create_offer.assert_not_awaited()
    assert "não cadastrei nada" in result["messages"][0].content
    assert result["pending_proposal"] is None


def test_aceite_dito_pelo_llm_nunca_executa(monkeypatch):
    client = _core(monkeypatch)
    monkeypatch.setattr(
        decision, "ask_json", AsyncMock(return_value={"decisao": "aceitar"})
    )
    monkeypatch.setattr(decision, "ask_text", AsyncMock(return_value=""))

    result = _decidir("olha, tá tudo certo, pode seguir com isso")

    client.create_offer.assert_not_awaited()
    assert result["pending_proposal"]["em_duvida"] is True
    assert "continua pendente" in result["messages"][0].content


@pytest.mark.parametrize("retorno", [{"decisao": "talvez"}, {}, {"decisao": None}])
def test_decisao_invalida_do_llm_nunca_executa(monkeypatch, retorno):
    client = _core(monkeypatch)
    monkeypatch.setattr(decision, "ask_json", AsyncMock(return_value=retorno))
    monkeypatch.setattr(
        decision, "ask_text", AsyncMock(return_value="O preço é R$ 900,50.")
    )

    result = _decidir("e o frete, como fica?")

    client.create_offer.assert_not_awaited()
    assert result["pending_proposal"]["em_duvida"] is True
    assert "continua pendente" in result["messages"][0].content


def test_llm_fora_do_ar_na_classificacao_nunca_executa(monkeypatch):
    client = _core(monkeypatch)
    monkeypatch.setattr(
        decision, "ask_json", AsyncMock(side_effect=InvalidJsonReply("x"))
    )
    monkeypatch.setattr(decision, "ask_text", AsyncMock(return_value=""))

    result = _decidir("não sei ainda")

    client.create_offer.assert_not_awaited()
    assert "continua pendente" in result["messages"][0].content


def test_duvida_responde_e_mantem_a_proposta(monkeypatch):
    _core(monkeypatch)
    monkeypatch.setattr(
        decision, "ask_json", AsyncMock(return_value={"decisao": "duvida"})
    )
    monkeypatch.setattr(
        decision, "ask_text", AsyncMock(return_value="São 40 unidades.")
    )

    result = _decidir("quantas unidades mesmo?")

    assert "São 40 unidades." in result["messages"][0].content
    assert result["pending_proposal"]["em_duvida"] is True


def test_erro_do_api_core_ao_executar_descarta_e_explica(monkeypatch):
    client = _core(monkeypatch)
    client.create_offer.side_effect = ApiCoreError(
        "Você não tem permissão para fazer isso nesta empresa.", 403
    )

    result = _decidir("sim")

    assert "Não consegui executar" in result["messages"][0].content
    assert "permissão" in result["messages"][0].content
    assert result["pending_proposal"] is None


def test_aceite_sem_token_descarta_a_proposta(monkeypatch):
    client = _core(monkeypatch)
    current_user_token.set(None)

    result = _decidir("sim")

    client.create_offer.assert_not_awaited()
    assert result["pending_proposal"] is None


def test_proposta_pendente_invalida_e_descartada(monkeypatch):
    _core(monkeypatch)

    result = _decidir("sim", pendente={"action": "outra"})

    assert result["pending_proposal"] is None
    assert "Não consegui validar" in result["messages"][0].content


def test_roteador_devolve_a_resposta_para_a_decisao_sem_chamar_o_llm(monkeypatch):
    llm = Mock()
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    state = {"messages": [HumanMessage(content="sim")], "pending_proposal": PENDENTE}

    result = router_node.router_node(state)

    assert result == {"route": "proposal_decision", "turn_agents": ["router"]}
    llm.invoke.assert_not_called()


def test_resposta_dos_nos_de_acao_leva_os_metadados_do_turno(monkeypatch):
    _core(monkeypatch)

    result = _decidir("não")

    mensagem = result["messages"][0]
    assert isinstance(mensagem, AIMessage)
    assert mensagem.additional_kwargs["specialists_used"] == ["proposal_decision"]


def test_parse_json_extrai_o_objeto_mesmo_com_texto_em_volta():
    assert parse_json_object('Claro:\n```json\n{"a": 1}\n```') == {"a": 1}


@pytest.mark.parametrize("texto", ["sem json", "{quebrado", "[1, 2]", None])
def test_parse_json_rejeita_o_que_nao_e_objeto(texto):
    with pytest.raises(InvalidJsonReply):
        parse_json_object(texto)


def test_resposta_curta_a_uma_proposta_pula_a_classificacao_por_llm(monkeypatch):
    from src.workflow.nodes import input_guardrail_node as guardrail

    llm = Mock()
    monkeypatch.setattr(guardrail, "llm_groq", Mock(return_value=llm))
    state = {"messages": [HumanMessage(content="sim")], "pending_proposal": PENDENTE}

    result = guardrail.input_guardrail_node(state)

    assert result["route"] == "proceed"
    llm.invoke.assert_not_called()


def test_mensagem_longa_com_proposta_pendente_continua_sendo_classificada(monkeypatch):
    from src.workflow.nodes import input_guardrail_node as guardrail

    llm = Mock()
    llm.invoke.return_value = AIMessage(
        content="CATEGORIA: APROVADO\nJUSTIFICATIVA: ok"
    )
    monkeypatch.setattr(guardrail, "llm_groq", Mock(return_value=llm))
    state = {
        "messages": [HumanMessage(content="e o frete como fica?")],
        "pending_proposal": PENDENTE,
    }

    guardrail.input_guardrail_node(state)

    llm.invoke.assert_called_once()
