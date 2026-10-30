import pytest

from src.actions import proposal
from src.core.config.settings import settings


def _nova(**kwargs):
    return proposal.make_proposal(
        "create_offer", {"a": 1, "preco": 9.5}, "resumo", "user-1", now=1000.0, **kwargs
    )


def test_proposta_valida_do_mesmo_usuario_dentro_do_prazo():
    assert proposal.verify_proposal(_nova(), "user-1", now=1100.0) == proposal.OK


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("payload", {"a": 2, "preco": 9.5}),
        ("action", "cancel_order"),
        ("resumo", "outro"),
    ],
)
def test_adulterar_a_proposta_invalida_o_selo(campo, valor):
    pendente = {**_nova(), campo: valor}

    assert proposal.verify_proposal(pendente, "user-1", now=1100.0) == proposal.INVALIDA


def test_proposta_sem_selo_ou_vazia_e_invalida():
    assert proposal.verify_proposal(None, "user-1") == proposal.INVALIDA
    assert proposal.verify_proposal({"action": "x"}, "user-1") == proposal.INVALIDA


def test_proposta_de_outro_usuario_e_rejeitada():
    assert (
        proposal.verify_proposal(_nova(), "user-2", now=1100.0)
        == proposal.OUTRO_USUARIO
    )


def test_proposta_expira(monkeypatch):
    monkeypatch.setattr(settings, "PROPOSAL_TTL_SECONDS", 60)

    assert proposal.verify_proposal(_nova(), "user-1", now=1061.0) == proposal.EXPIRADA
    assert proposal.verify_proposal(_nova(), "user-1", now=1059.0) == proposal.OK


def test_selo_depende_da_chave(monkeypatch):
    pendente = _nova()
    monkeypatch.setattr(settings, "PROPOSAL_SIGNING_KEY", "outra-chave")

    assert proposal.verify_proposal(pendente, "user-1", now=1100.0) == proposal.INVALIDA


def test_irreversivel_fica_marcado_e_cada_proposta_tem_id_proprio():
    a = _nova(irreversible=True)
    b = _nova()

    assert a["irreversivel"] is True
    assert a["id"] != b["id"]
