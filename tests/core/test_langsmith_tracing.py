import logging

import pytest
from langchain_core.tracers.langchain import LangChainTracer

from src.core.observability import langsmith_tracing as ls


@pytest.fixture(autouse=True)
def _limpa_cache(monkeypatch):
    monkeypatch.setattr(ls, "_client", None)


def _configura(monkeypatch, enabled, api_key="chave-de-teste"):
    monkeypatch.setattr(ls.settings, "SOLARIA_LANGSMITH_ENABLED", enabled)
    monkeypatch.setattr(ls.settings, "SOLARIA_LANGSMITH_API_KEY", api_key)
    monkeypatch.setattr(ls.settings, "SOLARIA_LANGSMITH_PROJECT", "solaria-teste")
    monkeypatch.setattr(ls.settings, "SOLARIA_LANGSMITH_ENDPOINT", None)
    monkeypatch.setattr(ls.settings, "SOLARIA_LANGSMITH_SAMPLING_RATE", 1.0)


def test_build_tracer_devolve_none_quando_desligado(monkeypatch):
    _configura(monkeypatch, enabled=False)

    assert ls.build_tracer() is None


def test_build_tracer_devolve_none_sem_chave(monkeypatch):
    _configura(monkeypatch, enabled=True, api_key=None)

    assert ls.build_tracer() is None


def test_build_tracer_cria_um_tracer_por_chamada_sobre_o_mesmo_client(monkeypatch):
    _configura(monkeypatch, enabled=True)

    primeiro = ls.build_tracer()
    segundo = ls.build_tracer()

    assert isinstance(primeiro, LangChainTracer)
    assert primeiro is not segundo
    assert primeiro.client is segundo.client
    assert primeiro.project_name == "solaria-teste"


def test_anonymizer_mascara_pii_em_estrutura_aninhada():
    anonymizer = ls.build_anonymizer()

    resultado = anonymizer(
        {
            "msg": "meu cpf 123.456.789-09 e email ana@empresa.com",
            "n": {"x": ["12345678909"]},
        }
    )

    assert resultado["msg"] == "meu cpf [CPF] e email [EMAIL]"
    assert resultado["n"]["x"] == ["[CPF]"]


def test_warn_if_global_tracing_avisa_quando_tracing_global_esta_ligado(
    monkeypatch, caplog
):
    _configura(monkeypatch, enabled=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")

    with caplog.at_level(logging.WARNING):
        ls.warn_if_global_tracing()

    assert "tracing global" in caplog.text


def test_warn_if_global_tracing_fica_em_silencio_sem_a_variavel(monkeypatch, caplog):
    _configura(monkeypatch, enabled=False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    with caplog.at_level(logging.WARNING):
        ls.warn_if_global_tracing()

    assert caplog.text == ""
