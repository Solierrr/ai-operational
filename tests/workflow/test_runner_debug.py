import asyncio
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage

import src.workflow.runner as runner
from src.core.security.request_context import debug_dry_run


def _workflow():
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    return workflow


def test_execute_turn_sem_persistir_so_passa_pelo_grafo(monkeypatch):
    workflow = _workflow()
    criar_conversa_chatbot = AsyncMock()
    enviar_mensagem_usuario = AsyncMock()
    enviar_mensagem_chatbot = AsyncMock()
    get_user_memory = AsyncMock()
    agendar = Mock()
    monkeypatch.setattr(runner, "criar_conversa_chatbot", criar_conversa_chatbot)
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", enviar_mensagem_usuario)
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)
    monkeypatch.setattr(runner, "get_user_memory", get_user_memory)
    monkeypatch.setattr(runner, "_agendar_atualizacao_memoria", agendar)
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    coletor = object()

    resultado = asyncio.run(
        runner.execute_turn(
            "debug:thread",
            "texto",
            workflow,
            user_token="t",
            persist=False,
            extra_callbacks=[coletor],
        )
    )

    criar_conversa_chatbot.assert_not_awaited()
    enviar_mensagem_usuario.assert_not_awaited()
    enviar_mensagem_chatbot.assert_not_awaited()
    get_user_memory.assert_not_awaited()
    agendar.assert_not_called()
    assert resultado["messages"][0].content == "oi"
    config_usado = workflow.ainvoke.await_args.kwargs["config"]
    assert config_usado["callbacks"] == [coletor]
    assert config_usado["configurable"] == {"thread_id": "operational:debug:thread"}
    assert workflow.ainvoke.await_args.args[0]["user_memory"] == ""


def test_execute_turn_sem_persistir_liga_o_dry_run(monkeypatch):
    visto = {}
    workflow = Mock()

    async def ainvoke(estado, config):
        visto["dry_run"] = debug_dry_run.get()
        return {"messages": [AIMessage(content="oi", additional_kwargs={})]}

    workflow.ainvoke = ainvoke
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))

    asyncio.run(
        runner.execute_turn("c-1", "texto", workflow, user_token="t", persist=False)
    )

    assert visto["dry_run"] is True


def test_execute_turn_padrao_persiste_e_desliga_o_dry_run(monkeypatch):
    visto = {}
    workflow = Mock()

    async def ainvoke(estado, config):
        visto["dry_run"] = debug_dry_run.get()
        visto["callbacks"] = config["callbacks"]
        return {"messages": [AIMessage(content="oi", additional_kwargs={})]}

    workflow.ainvoke = ainvoke
    enviar_mensagem_chatbot = AsyncMock()
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)
    monkeypatch.setattr(runner, "_conversations_por_thread", {})
    monkeypatch.setattr(
        runner, "criar_conversa_chatbot", AsyncMock(return_value="api-conv-1")
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))
    debug_dry_run.set(True)

    asyncio.run(runner.execute_turn("c-1", "texto", workflow, user_token="t"))

    assert visto["dry_run"] is False
    assert len(visto["callbacks"]) == 1
    assert visto["callbacks"][0].conversation_id == "api-conv-1"
    enviar_mensagem_chatbot.assert_awaited_once()
