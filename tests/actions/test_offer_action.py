from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.actions import offer
from src.infra.api_core.client import SupplierRef

MODELOS = [
    {"id": "m1", "brand": "Canadian", "model": "CS6R", "powerWp": 550.0},
    {"id": "m2", "brand": "Canadian", "model": "HiKu6", "powerWp": 600.0},
    {"id": "m3", "brand": "Jinko", "model": "Tiger Neo", "powerWp": 550.0},
]
ACME = SupplierRef("s1", "c1", "ACME Solar")
BETA = SupplierRef("s2", "c2", "Beta Energia")


def test_campos_obrigatorios_faltando_sao_descritos():
    rascunho = offer.OfferDraft(modelo="Canadian CS6R")

    faltando = offer.missing_fields(rascunho)

    assert len(faltando) == 2
    assert any("preço" in item for item in faltando)
    assert any("quantidade" in item for item in faltando)


def test_rascunho_completo_nao_tem_pendencias():
    rascunho = offer.OfferDraft(
        modelo="x", preco_unitario=Decimal(900), disponibilidade=0
    )

    assert offer.missing_fields(rascunho) == []


@pytest.mark.parametrize(
    "campo, valor",
    [("preco_unitario", 0), ("preco_unitario", -5), ("disponibilidade", -1)],
)
def test_valores_invalidos_sao_recusados(campo, valor):
    with pytest.raises(ValidationError):
        offer.OfferDraft(**{campo: valor})


def test_um_unico_fornecedor_e_escolhido_direto():
    assert offer.pick_supplier(offer.OfferDraft(), [ACME]) == ACME


def test_varios_fornecedores_exigem_a_empresa():
    assert offer.pick_supplier(offer.OfferDraft(), [ACME, BETA]) == [ACME, BETA]


def test_varios_fornecedores_resolvem_pelo_nome_da_empresa():
    assert offer.pick_supplier(offer.OfferDraft(empresa="beta"), [ACME, BETA]) == BETA


def test_nome_de_empresa_ambiguo_continua_perguntando():
    assert offer.pick_supplier(offer.OfferDraft(empresa="a"), [ACME, BETA]) == [
        ACME,
        BETA,
    ]


@pytest.mark.parametrize(
    "consulta, esperado",
    [
        ("Canadian CS6R 550", ["m1"]),
        ("canadian", ["m1", "m2"]),
        ("jinko tiger neo", ["m3"]),
        ("550wp", ["m1", "m3"]),
        ("marca inexistente", []),
        ("", []),
    ],
)
def test_modelos_casam_por_palavras_marca_modelo_e_potencia(consulta, esperado):
    assert [m["id"] for m in offer.match_models(consulta, MODELOS)] == esperado


def test_payload_usa_titulo_e_descricao_padrao():
    rascunho = offer.OfferDraft(
        modelo="Canadian CS6R", preco_unitario=Decimal("899.9"), disponibilidade=40
    )

    payload = offer.build_payload(rascunho, MODELOS[0], ACME)

    assert payload == {
        "supplierId": "s1",
        "modelId": "m1",
        "title": "Placa solar Canadian CS6R 550 Wp",
        "description": "Placa solar Canadian CS6R 550 Wp disponível para venda.",
        "unitPrice": 899.9,
        "availability": 40,
    }


def test_payload_respeita_titulo_e_descricao_do_usuario():
    rascunho = offer.OfferDraft(
        modelo="x",
        titulo="Promoção",
        descricao="Lote novo",
        preco_unitario=Decimal(1),
        disponibilidade=1,
    )

    payload = offer.build_payload(rascunho, MODELOS[0], ACME)

    assert payload["title"] == "Promoção"
    assert payload["description"] == "Lote novo"


def test_proposta_mostra_tudo_o_que_sera_gravado():
    rascunho = offer.OfferDraft(
        modelo="x", preco_unitario=Decimal("1234.5"), disponibilidade=40
    )
    payload = offer.build_payload(rascunho, MODELOS[0], ACME)

    texto = offer.render_proposal(payload, MODELOS[0], ACME)

    assert "ACME Solar" in texto
    assert "Canadian CS6R 550 Wp" in texto
    assert "R$ 1.234,50" in texto
    assert "40 unidades" in texto
    assert "só depois do seu aceite" in texto
