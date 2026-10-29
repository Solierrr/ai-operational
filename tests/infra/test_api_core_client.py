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
        if request.url.path == "/api/users/me":
            return httpx.Response(
                200,
                json={
                    "companyMemberships": [
                        {"companyId": "c1", "companyName": "ACME", "position": "ADMIN"},
                        {
                            "companyId": "c2",
                            "companyName": "Outra",
                            "position": "MEMBER",
                        },
                    ]
                },
            )
        if request.url.path == "/api/suppliers/company/c1":
            return httpx.Response(200, json=[{"id": "s1"}])
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


def _perfil(request):
    return httpx.Response(
        200,
        json={
            "companyMemberships": [
                {"companyId": "c1", "companyName": "ACME", "position": "ADMIN"}
            ]
        },
    )


def test_ofertas_e_estoque_seguem_as_empresas_do_usuario_e_marcam_a_origem():
    def handler(request):
        if request.url.path == "/api/users/me":
            return _perfil(request)
        if request.url.path == "/api/offers/company/c1":
            return httpx.Response(200, json=[{"id": "of1"}])
        if request.url.path == "/api/inventories/company/c1":
            return httpx.Response(200, json=[{"id": "i1", "quantity": 3}])
        return httpx.Response(404)

    client, vistos = _client(handler)

    ofertas = asyncio.run(client.my_offers())
    estoque = asyncio.run(client.my_inventories())

    assert ofertas == [{"id": "of1", "_empresa": "ACME"}]
    assert estoque[0]["_empresa"] == "ACME"
    assert all(r.headers["Authorization"] == "Bearer jwt-do-usuario" for r in vistos)


@pytest.mark.parametrize(
    "chamada,metodo,caminho,corpo",
    [
        (
            lambda c: c.change_offer_status("of1", "PAUSED"),
            "PATCH",
            "/api/offers/of1/status",
            {"status": "PAUSED"},
        ),
        (
            lambda c: c.update_inventory_quantity("i1", 7),
            "PATCH",
            "/api/inventories/i1/quantity",
            {"quantity": 7},
        ),
        (lambda c: c.cancel_order("p1"), "PATCH", "/api/orders/p1/cancel", None),
        (
            lambda c: c.put_cart_item("of1", 2),
            "PUT",
            "/api/cart/items/of1",
            {"quantity": 2},
        ),
        (lambda c: c.remove_cart_item("of1"), "DELETE", "/api/cart/items/of1", None),
        (lambda c: c.create_offer({"a": 1}), "POST", "/api/offers", {"a": 1}),
    ],
)
def test_escritas_usam_o_metodo_o_caminho_e_o_corpo_certos(
    chamada, metodo, caminho, corpo
):
    import json

    client, vistos = _client(lambda request: httpx.Response(200, json={"ok": True}))

    asyncio.run(chamada(client))

    assert vistos[0].method == metodo
    assert vistos[0].url.path == caminho
    assert (json.loads(vistos[0].content) if vistos[0].content else None) == corpo
    assert vistos[0].headers["Authorization"] == "Bearer jwt-do-usuario"


@pytest.mark.parametrize(
    "chamada,caminho",
    [
        (lambda c: c.my_orders(), "/api/orders"),
        (lambda c: c.my_sales(), "/api/sales"),
        (lambda c: c.cart(), "/api/cart"),
        (lambda c: c.subscription(), "/api/subscription"),
        (lambda c: c.catalog_offers(), "/api/offers/catalog"),
    ],
)
def test_leituras_do_usuario_usam_os_caminhos_certos(chamada, caminho):
    client, vistos = _client(lambda request: httpx.Response(200, json=[]))

    asyncio.run(chamada(client))

    assert vistos[0].method == "GET"
    assert vistos[0].url.path == caminho


def _duas_empresas(request):
    return httpx.Response(
        200,
        json={
            "companyMemberships": [
                {"companyId": "c1", "companyName": "ACME", "position": "ADMIN"},
                {"companyId": "c2", "companyName": "Beta", "position": "MEMBER"},
            ]
        },
    )


def test_empresa_sem_acesso_nao_derruba_a_listagem_das_outras():
    def handler(request):
        if request.url.path == "/api/users/me":
            return _duas_empresas(request)
        if request.url.path == "/api/offers/company/c1":
            return httpx.Response(403)
        return httpx.Response(200, json=[{"id": "of2"}])

    client, _ = _client(handler)

    assert asyncio.run(client.my_offers()) == [{"id": "of2", "_empresa": "Beta"}]


def test_sem_acesso_a_nenhuma_empresa_devolve_o_erro():
    def handler(request):
        if request.url.path == "/api/users/me":
            return _duas_empresas(request)
        return httpx.Response(403)

    client, _ = _client(handler)

    with pytest.raises(ApiCoreError) as erro:
        asyncio.run(client.my_offers())
    assert erro.value.status == 403


def test_erro_de_servidor_em_uma_empresa_nao_e_engolido():
    def handler(request):
        if request.url.path == "/api/users/me":
            return _duas_empresas(request)
        return httpx.Response(500)

    client, _ = _client(handler)

    with pytest.raises(ApiCoreError):
        asyncio.run(client.my_offers())


def test_detalhe_do_erro_do_api_core_sai_sem_links():
    from src.infra.api_core.client import _mensagem_http

    resposta = httpx.Response(
        422, json={"detail": "Título inválido, veja https://mal.example/x agora"}
    )

    texto = _mensagem_http(resposta)

    assert "mal.example" not in texto
    assert "Título inválido" in texto
