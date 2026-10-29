import asyncio
from unittest.mock import AsyncMock, Mock

from src.actions import base, cart, inventory, offer_status, order
from src.actions.registry import ACTIONS, describe_actions, get_action

MODELO = {"id": "m1", "brand": "Canadian", "model": "CS6R", "powerWp": 550.0}
OUTRO = {"id": "m2", "brand": "Jinko", "model": "Tiger", "powerWp": 600.0}


def _run(coro):
    return asyncio.run(coro)


def _client(**metodos):
    client = Mock()
    for nome, valor in metodos.items():
        setattr(client, nome, AsyncMock(return_value=valor))
    return client


def test_registro_expoe_as_cinco_acoes_e_rejeita_nomes_desconhecidos():
    assert set(ACTIONS) == {
        "create_offer",
        "set_offer_status",
        "set_inventory_quantity",
        "cancel_order",
        "update_cart",
    }
    assert get_action("drop_database") is None
    assert get_action(None) is None
    assert "cancel_order" in describe_actions()


OFERTA = {
    "id": "of1",
    "model": MODELO,
    "slug": "canadian-cs6r",
    "unitPrice": 900.5,
    "commercialStatus": "ACTIVE",
    "_empresa": "ACME",
}


def test_status_pausar_gera_proposta_comum_com_o_id_do_proprio_usuario():
    client = _client(my_offers=[OFERTA])

    resultado = _run(
        offer_status.prepare(
            offer_status.OfferStatusDraft(oferta="canadian 550", situacao="PAUSED"),
            client,
        )
    )

    assert isinstance(resultado, base.Ready)
    assert resultado.payload["offerId"] == "of1"
    assert resultado.irreversible is False
    assert "ativa -> pausada" in resultado.resumo


def test_status_encerrar_e_irreversivel():
    client = _client(my_offers=[OFERTA])

    resultado = _run(
        offer_status.prepare(
            offer_status.OfferStatusDraft(oferta="canadian", situacao="CLOSED"), client
        )
    )

    assert resultado.irreversible is True


def test_status_ignora_ids_inventados_e_so_enxerga_as_ofertas_do_usuario():
    client = _client(my_offers=[OFERTA])

    resultado = _run(
        offer_status.prepare(
            offer_status.OfferStatusDraft(oferta="jinko tiger", situacao="PAUSED"),
            client,
        )
    )

    assert isinstance(resultado, base.Ask)
    assert "Não encontrei" in resultado.text


def test_status_mesmo_estado_e_encerrada_nao_viram_proposta():
    igual = _run(
        offer_status.prepare(
            offer_status.OfferStatusDraft(oferta="canadian", situacao="ACTIVE"),
            _client(my_offers=[OFERTA]),
        )
    )
    encerrada = _run(
        offer_status.prepare(
            offer_status.OfferStatusDraft(oferta="canadian", situacao="ACTIVE"),
            _client(my_offers=[{**OFERTA, "commercialStatus": "CLOSED"}]),
        )
    )

    assert isinstance(igual, base.Ask) and "já está" in igual.text
    assert isinstance(encerrada, base.Ask) and "não pode ser reaberta" in encerrada.text


def test_status_pergunta_o_que_falta():
    client = _client(my_offers=[OFERTA])

    sem_oferta = _run(offer_status.prepare(offer_status.OfferStatusDraft(), client))
    sem_status = _run(
        offer_status.prepare(offer_status.OfferStatusDraft(oferta="canadian"), client)
    )

    assert "Qual oferta" in sem_oferta.text
    assert "pausar, reativar ou encerrar" in sem_status.text


def test_status_ambiguo_lista_as_candidatas():
    outra = {**OFERTA, "id": "of2", "model": {**MODELO, "powerWp": 600.0}}
    client = _client(my_offers=[OFERTA, outra])

    resultado = _run(
        offer_status.prepare(
            offer_status.OfferStatusDraft(oferta="canadian", situacao="PAUSED"), client
        )
    )

    assert "mais de uma oferta" in resultado.text


def test_status_execute_chama_o_api_core_com_o_id_da_proposta():
    client = _client(change_offer_status={"commercialStatus": "PAUSED"})

    _run(offer_status.execute(client, {"offerId": "of1", "status": "PAUSED"}))

    client.change_offer_status.assert_awaited_once_with("of1", "PAUSED")


ESTOQUE = {"id": "i1", "model": MODELO, "quantity": 10, "_empresa": "ACME"}


def test_estoque_propoe_de_para():
    resultado = _run(
        inventory.prepare(
            inventory.InventoryDraft(modelo="canadian", quantidade=25),
            _client(my_inventories=[ESTOQUE]),
        )
    )

    assert resultado.payload == {
        "inventoryId": "i1",
        "quantity": 25,
        "rotulo": "Canadian CS6R 550 Wp",
    }
    assert "10 -> 25" in resultado.resumo


def test_estoque_pergunta_total_e_recusa_quantidade_igual():
    client = _client(my_inventories=[ESTOQUE])

    faltando = _run(
        inventory.prepare(inventory.InventoryDraft(modelo="canadian"), client)
    )
    igual = _run(
        inventory.prepare(
            inventory.InventoryDraft(modelo="canadian", quantidade=10), client
        )
    )

    assert "nova quantidade total" in faltando.text
    assert "já é de 10" in igual.text


def test_estoque_nao_aceita_quantidade_negativa():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        inventory.InventoryDraft(modelo="x", quantidade=-1)


PEDIDOS = [
    {
        "id": "aaaaaaaa-1111-2222-3333-444444444444",
        "status": "PAID",
        "total": 1800.0,
        "createdAt": "2026-10-01T10:00:00Z",
        "items": [{"modelName": "Canadian CS6R", "quantity": 2}],
    },
    {
        "id": "bbbbbbbb-1111-2222-3333-444444444444",
        "status": "PAID",
        "total": 900.0,
        "createdAt": "2026-10-05T10:00:00Z",
        "items": [{"modelName": "Jinko Tiger", "quantity": 1}],
    },
    {
        "id": "cccccccc-1111-2222-3333-444444444444",
        "status": "CANCELED",
        "total": 10.0,
        "createdAt": "2026-10-06T10:00:00Z",
        "items": [],
    },
]


def test_pedido_ambiguo_lista_so_os_cancelaveis():
    resultado = _run(order.prepare(order.OrderDraft(), _client(my_orders=PEDIDOS)))

    assert isinstance(resultado, base.Ask)
    assert "aaaaaaaa" in resultado.text and "bbbbbbbb" in resultado.text
    assert "cccccccc" not in resultado.text


def test_pedido_por_codigo_e_sempre_irreversivel():
    resultado = _run(
        order.prepare(order.OrderDraft(pedido="BBBBBBBB"), _client(my_orders=PEDIDOS))
    )

    assert isinstance(resultado, base.Ready)
    assert resultado.payload["orderId"].startswith("bbbbbbbb")
    assert resultado.irreversible is True


def test_pedido_ultimo_pega_o_mais_recente_pago():
    resultado = _run(
        order.prepare(order.OrderDraft(referencia="ultimo"), _client(my_orders=PEDIDOS))
    )

    assert resultado.payload["orderId"].startswith("bbbbbbbb")


def test_pedido_ja_cancelado_ou_codigo_curto_demais_nao_vira_proposta():
    cancelado = _run(
        order.prepare(order.OrderDraft(pedido="cccccccc"), _client(my_orders=PEDIDOS))
    )
    curto = _run(
        order.prepare(order.OrderDraft(pedido="a"), _client(my_orders=PEDIDOS))
    )
    nenhum = _run(order.prepare(order.OrderDraft(), _client(my_orders=[PEDIDOS[2]])))

    assert isinstance(cancelado, base.Ask)
    assert isinstance(curto, base.Ask)
    assert "não tem pedidos" in nenhum.text


CATALOGO = [
    {
        "id": "o1",
        "model": MODELO,
        "unitPrice": 900.5,
        "availability": 40,
        "commercialStatus": "ACTIVE",
    },
    {
        "id": "o2",
        "model": OUTRO,
        "unitPrice": 1000.0,
        "availability": 5,
        "commercialStatus": "PAUSED",
    },
]


def test_carrinho_propoe_e_nao_finaliza_compra():
    resultado = _run(
        cart.prepare(
            cart.CartDraft(oferta="canadian 550", quantidade=3),
            _client(catalog_offers=CATALOGO),
        )
    )

    assert resultado.payload["quantity"] == 3
    assert "Isso não finaliza compra" in resultado.resumo


def test_carrinho_nao_mostra_oferta_pausada_nem_passa_do_estoque():
    pausada = _run(
        cart.prepare(
            cart.CartDraft(oferta="jinko tiger", quantidade=1),
            _client(catalog_offers=CATALOGO),
        )
    )
    demais = _run(
        cart.prepare(
            cart.CartDraft(oferta="canadian", quantidade=99),
            _client(catalog_offers=CATALOGO),
        )
    )

    assert "Não encontrei" in pausada.text
    assert "Só há 40" in demais.text


def test_carrinho_zero_remove_e_usa_a_rota_de_remocao():
    client = _client(remove_cart_item={"total": 0}, put_cart_item={"total": 1})

    _run(cart.execute(client, {"offerId": "o1", "quantity": 0}))
    _run(cart.execute(client, {"offerId": "o1", "quantity": 2}))

    client.remove_cart_item.assert_awaited_once_with("o1")
    client.put_cart_item.assert_awaited_once_with("o1", 2)
    assert "tirei" in cart.success({}, {"quantity": 0, "rotulo": "X"})
