import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage

import src.workflow.runner as runner


def test_execute_turn_persists_anonymized_request_and_audited_response(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="Resposta final",
                    additional_kwargs={
                        "specialists_used": ["faq_reader"],
                        "workflow_steps": [
                            "router",
                            "faq_reader",
                            "orchestrator",
                            "output_guardrail",
                        ],
                    },
                )
            ],
            "turn_agents": ["router", "faq_reader", "orchestrator"],
        }
    )
    enviar_mensagem_usuario = AsyncMock()
    enviar_mensagem_chatbot = AsyncMock()
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", enviar_mensagem_usuario)
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)
    monkeypatch.setattr(runner, "_conversations_por_thread", {})
    monkeypatch.setattr(
        runner,
        "criar_conversa_chatbot",
        AsyncMock(return_value="api-conv-1"),
    )
    monkeypatch.setattr(
        runner,
        "anonymize_text",
        Mock(side_effect=[("texto anonimo", {}), ("resposta anonima", {})]),
    )
    monkeypatch.setattr(runner, "uuid4", Mock(return_value="turn-123"))

    asyncio.run(
        runner.execute_turn(
            "conversation-1", "texto original", workflow, user_token="token-abc"
        )
    )

    assert runner.criar_conversa_chatbot.await_args.kwargs["user_token"] == "token-abc"
    assert enviar_mensagem_usuario.await_args.args == (
        "api-conv-1",
        "texto anonimo",
        "token-abc",
    )
    config_usado = workflow.ainvoke.await_args.kwargs["config"]
    assert config_usado["configurable"] == {"thread_id": "operational:conversation-1"}
    assert len(config_usado["callbacks"]) == 1
    assert config_usado["callbacks"][0].conversation_id == "api-conv-1"
    assert enviar_mensagem_chatbot.await_args.args[:2] == (
        "api-conv-1",
        "resposta anonima",
    )
    assert enviar_mensagem_chatbot.await_args.args[2] == {
        "turnId": "turn-123",
        "contentAnonymized": True,
        "specialistsUsed": ["faq_reader"],
        "workflowSteps": [
            "router",
            "faq_reader",
            "orchestrator",
            "output_guardrail",
        ],
    }


def test_execute_turn_reaproveita_conversa_ja_criada_para_a_mesma_thread(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    criar_conversa_chatbot = AsyncMock()
    monkeypatch.setattr(runner, "criar_conversa_chatbot", criar_conversa_chatbot)
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )

    asyncio.run(
        runner.execute_turn("conversation-1", "texto", workflow, user_token="token-abc")
    )

    criar_conversa_chatbot.assert_not_awaited()


def test_execute_turn_injeta_memoria_existente_no_estado_inicial(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    monkeypatch.setattr(
        runner,
        "get_user_memory",
        AsyncMock(return_value=["mora em SP", "é instalador"]),
    )

    asyncio.run(
        runner.execute_turn("conversation-1", "texto", workflow, user_token="token-abc")
    )

    estado_inicial = workflow.ainvoke.await_args.args[0]
    assert estado_inicial["user_id"] == "user-1"
    assert estado_inicial["user_memory"] == "- mora em SP\n- é instalador"


def test_execute_turn_nao_agenda_atualizacao_de_memoria_sem_user_id(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))
    get_user_memory = AsyncMock()
    monkeypatch.setattr(runner, "get_user_memory", get_user_memory)
    agendar = Mock()
    monkeypatch.setattr(runner, "_agendar_atualizacao_memoria", agendar)

    asyncio.run(
        runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-invalido"
        )
    )

    get_user_memory.assert_not_awaited()
    agendar.assert_not_called()


def test_execute_turn_agenda_atualizacao_de_memoria_em_background(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="resposta", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    monkeypatch.setattr(runner, "get_user_memory", AsyncMock(return_value=[]))
    extrair_fatos_atualizados = AsyncMock(return_value=["novo fato"])
    upsert_user_memory = AsyncMock()
    monkeypatch.setattr(runner, "extrair_fatos_atualizados", extrair_fatos_atualizados)
    monkeypatch.setattr(runner, "upsert_user_memory", upsert_user_memory)

    async def _run():
        await runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-abc"
        )
        await asyncio.gather(*runner._background_tasks)

    asyncio.run(_run())

    extrair_fatos_atualizados.assert_awaited_once_with(
        [], "Usuário: texto\nAssistente: resposta"
    )
    upsert_user_memory.assert_awaited_once_with("user-1", ["novo fato"])


def test_execute_turn_nao_propaga_falha_da_atualizacao_de_memoria(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="resposta", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    monkeypatch.setattr(runner, "get_user_memory", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        runner,
        "extrair_fatos_atualizados",
        AsyncMock(side_effect=RuntimeError("groq e gemini fora do ar")),
    )
    monkeypatch.setattr(runner, "upsert_user_memory", AsyncMock())

    async def _run():
        resultado = await runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-abc"
        )
        await asyncio.gather(*runner._background_tasks)
        return resultado

    resultado = asyncio.run(_run())

    assert resultado["messages"][0].content == "resposta"


def _executar_debug_com_historico(monkeypatch, count_turns_mock=None):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    mocks = SimpleNamespace(
        criar_conversa_chatbot=AsyncMock(return_value="api-conv-1"),
        enviar_mensagem_usuario=AsyncMock(),
        enviar_mensagem_chatbot=AsyncMock(),
        get_user_memory=AsyncMock(),
        agendar=Mock(),
        workflow=workflow,
    )
    monkeypatch.setattr(runner, "_conversations_por_thread", {})
    monkeypatch.setattr(runner, "criar_conversa_chatbot", mocks.criar_conversa_chatbot)
    monkeypatch.setattr(
        runner, "enviar_mensagem_usuario", mocks.enviar_mensagem_usuario
    )
    monkeypatch.setattr(
        runner, "enviar_mensagem_chatbot", mocks.enviar_mensagem_chatbot
    )
    monkeypatch.setattr(runner, "get_user_memory", mocks.get_user_memory)
    monkeypatch.setattr(runner, "_agendar_atualizacao_memoria", mocks.agendar)
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    monkeypatch.setattr(
        runner,
        "anonymize_text",
        Mock(side_effect=[("texto anonimo", {}), ("resposta anonima", {})]),
    )
    if count_turns_mock is not None:
        monkeypatch.setattr(runner, "count_turns", count_turns_mock)
    mocks.resultado = asyncio.run(
        runner.execute_turn(
            "debug:thread",
            "texto",
            workflow,
            user_token="token-abc",
            persist=False,
            save_history=True,
        )
    )
    return mocks


def test_execute_turn_debug_com_historico_grava_mensagens_sem_memoria(monkeypatch):
    mocks = _executar_debug_com_historico(monkeypatch)

    detalhes = mocks.criar_conversa_chatbot.await_args.args[1]
    assert detalhes["assistant"] == runner.ASSISTANT_ID
    assert detalhes["source"] == "debug"
    assert detalhes["threadId"] == "debug:thread"
    assert mocks.enviar_mensagem_usuario.await_args.args == (
        "api-conv-1",
        "texto anonimo",
        "token-abc",
    )
    assert mocks.enviar_mensagem_chatbot.await_args.args[:2] == (
        "api-conv-1",
        "resposta anonima",
    )
    mocks.get_user_memory.assert_not_awaited()
    mocks.agendar.assert_not_called()
    callbacks = mocks.workflow.ainvoke.await_args.kwargs["config"]["callbacks"]
    assert callbacks[0].conversation_id == "api-conv-1"
    assert mocks.resultado["messages"][-1].content == "oi"


@pytest.mark.parametrize(
    ("count_turns_mock", "esperado"),
    [
        (AsyncMock(return_value=3), {"threadTurn": 2}),
        (AsyncMock(side_effect=RuntimeError("x")), {}),
    ],
)
def test_execute_turn_debug_com_historico_grava_o_turno_da_thread(
    monkeypatch, count_turns_mock, esperado
):
    mocks = _executar_debug_com_historico(monkeypatch, count_turns_mock)

    metadata = mocks.enviar_mensagem_chatbot.await_args.args[2]
    assert {k: v for k, v in metadata.items() if k == "threadTurn"} == esperado


def _workflow_simples():
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="ok")], "turn_agents": []}
    )
    return workflow


def test_execute_turn_inclui_o_tracer_do_langsmith_e_os_metadados(monkeypatch):
    workflow = _workflow_simples()
    tracer = Mock(name="tracer")
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(runner, "_conversations_por_thread", {})
    monkeypatch.setattr(
        runner, "criar_conversa_chatbot", AsyncMock(return_value="api-conv-1")
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))
    monkeypatch.setattr(runner, "build_tracer", Mock(return_value=tracer))

    asyncio.run(
        runner.execute_turn("conversation-1", "oi", workflow, user_token="token-abc")
    )

    config = workflow.ainvoke.await_args.kwargs["config"]
    assert tracer in config["callbacks"]
    assert config["metadata"]["assistant"] == "ai-operational"
    assert config["metadata"]["conversation_id"] == "api-conv-1"
    assert config["metadata"]["source"] == "chat"
    assert config["tags"] == [runner.settings.ENVIRONMENT.lower()]


def test_execute_turn_sem_langsmith_nao_acrescenta_callback(monkeypatch):
    workflow = _workflow_simples()
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))
    monkeypatch.setattr(runner, "build_tracer", Mock(return_value=None))

    asyncio.run(
        runner.execute_turn(
            "debug:t", "oi", workflow, user_token="token-abc", persist=False
        )
    )

    config = workflow.ainvoke.await_args.kwargs["config"]
    assert config["callbacks"] == []
    assert config["metadata"]["source"] == "debug"


def _workflow_com_dono(owner):
    workflow = Mock()
    workflow.aget_state = AsyncMock(
        return_value=SimpleNamespace(values={"user_id": owner})
    )
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    return workflow


def _sem_api_messenger(monkeypatch):
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock(return_value="c"))
    monkeypatch.setattr(runner, "_conversations_por_thread", {})
    monkeypatch.setattr(runner, "get_user_memory", AsyncMock(return_value=[]))
    monkeypatch.setattr(runner, "_agendar_atualizacao_memoria", Mock())


def test_conversa_de_outro_usuario_e_recusada_antes_de_rodar_o_grafo(monkeypatch):
    _sem_api_messenger(monkeypatch)
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="mallory"))
    workflow = _workflow_com_dono("alice")

    with pytest.raises(runner.ConversationAccessDenied):
        asyncio.run(runner.execute_turn("c1", "oi", workflow, user_token="t"))

    workflow.ainvoke.assert_not_awaited()
    runner.enviar_mensagem_usuario.assert_not_awaited()


def test_dono_da_conversa_continua_podendo_usar_com_caixa_diferente(monkeypatch):
    _sem_api_messenger(monkeypatch)
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="ALICE"))
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    workflow = _workflow_com_dono("alice")

    asyncio.run(runner.execute_turn("c1", "oi", workflow, user_token="t"))

    workflow.ainvoke.assert_awaited_once()


def test_usuario_nao_identificado_so_passa_no_ambiente_local(monkeypatch):
    _sem_api_messenger(monkeypatch)
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))
    monkeypatch.setattr(runner.settings, "ENVIRONMENT", "QA")
    workflow = _workflow_com_dono(None)

    with pytest.raises(runner.ConversationAccessDenied):
        asyncio.run(runner.execute_turn("c1", "oi", workflow, user_token="t"))

    workflow.ainvoke.assert_not_awaited()


def test_dois_turnos_da_mesma_conversa_nao_rodam_ao_mesmo_tempo(monkeypatch):
    _sem_api_messenger(monkeypatch)
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="alice"))
    monkeypatch.setattr(runner, "anonymize_text", Mock(return_value=("a", {})))
    ativos = []
    maximo = []

    async def ainvoke(*args, **kwargs):
        ativos.append(1)
        maximo.append(len(ativos))
        await asyncio.sleep(0.01)
        ativos.pop()
        return {"messages": [AIMessage(content="oi", additional_kwargs={})]}

    workflow = _workflow_com_dono("alice")
    workflow.ainvoke = ainvoke

    async def dois():
        await asyncio.gather(
            runner.execute_turn("c1", "sim", workflow, user_token="t"),
            runner.execute_turn("c1", "sim", workflow, user_token="t"),
        )

    asyncio.run(dois())

    assert max(maximo) == 1


def test_thread_do_checkpoint_tem_prefixo_do_servico():
    from src.core.security.conversation_access import thread_key

    assert thread_key("abc") == "operational:abc"
    assert thread_key("abc") != "abc"
