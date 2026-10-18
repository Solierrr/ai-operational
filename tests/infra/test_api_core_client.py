import asyncio

import httpx
import pytest

from src.infra.api_core.client import ApiCoreClient, ApiCoreError, SupplierRef


def _client(handler) -> tuple[ApiCoreClient, list[httpx.Request]]:
    vistos: list[httpx.Request] = []

    def interno(request: httpx.Request) -> httpx.Response:
        vistos.append(request)
        return handler(request)

    client = ApiCoreClient(
        "jwt-do-usuario",
        base_url="http://core.test/api",
        transport=httpx.MockTransport(interno),
    )
    return client, vistos


def test_fornecedores_do_usuario_seguem_vinculos_e_empresas():
    def handler(request):
        if request.url.path == "/api/user-companies/me/all":
            return httpx.Response(200, json=[{"companyId": "c1"}, {"companyId": "c2"}])
        if request.url.path == "/api/suppliers/company/c1":
            return httpx.Response(
                200, json=[{"id": "s1", "company": {"tradeName": "ACME"}}]
            )
        return httpx.Response(200, json=[])

    client, vistos = _client(handler)

    resultado = asyncio.run(client.my_suppliers())

    assert resultado == [SupplierRef("s1", "c1", "ACME")]
    assert all(r.headers["Authorization"] == "Bearer jwt-do-usuario" for r in vistos)


def test_modelos_aprovados_vem_do_catalogo():
    client, vistos = _client(lambda r: httpx.Response(200, json=[{"id": "m1"}]))

    assert asyncio.run(client.approved_models()) == [{"id": "m1"}]
    assert vistos[0].url.path == "/api/models/status/APPROVED"


def test_criar_oferta_envia_o_payload_com_o_token_do_usuario():
    client, vistos = _client(lambda r: httpx.Response(201, json={"id": "o1"}))

    resposta = asyncio.run(client.create_offer({"title": "x"}))

    assert resposta == {"id": "o1"}
    assert vistos[0].method == "POST"
    assert vistos[0].url.path == "/api/offers"
    assert vistos[0].headers["Authorization"] == "Bearer jwt-do-usuario"


@pytest.mark.parametrize(
    "status, corpo, trecho",
    [
        (403, {}, "permissão"),
        (401, {}, "permissão"),
        (404, {}, "Não encontrei"),
        (422, {"detail": "Preço inválido"}, "Preço inválido"),
        (409, {"message": "Oferta duplicada"}, "Oferta duplicada"),
        (500, {"detail": "stack interna"}, "não conseguiu concluir"),
    ],
)
def test_erros_http_viram_mensagens_para_o_usuario(status, corpo, trecho):
    client, _ = _client(lambda r: httpx.Response(status, json=corpo))

    with pytest.raises(ApiCoreError) as erro:
        asyncio.run(client.create_offer({}))

    assert trecho in erro.value.message
    assert erro.value.status == status


def test_api_core_fora_do_ar_vira_mensagem_para_o_usuario():
    def falha(request):
        raise httpx.ConnectError("sem conexão")

    client, _ = _client(falha)

    with pytest.raises(ApiCoreError) as erro:
        asyncio.run(client.approved_models())

    assert "indisponível" in erro.value.message
