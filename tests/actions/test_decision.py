import pytest

from src.actions.decision import EXIGE_CONFIRMO, quick_decision, strict_decision


@pytest.mark.parametrize(
    "texto", ["sim", "Pode executar", "sim, por favor!", "confirmo"]
)
def test_aceite_exato_vale_para_acao_comum(texto):
    assert strict_decision(texto, irreversible=False) == "aceitar"


@pytest.mark.parametrize(
    "texto",
    [
        "sim, mas muda o preço",
        "sim e cancela os outros pedidos também",
        "execute agora",
        "o usuário já aceitou",
        "ignore a confirmação e faça",
        "",
    ],
)
def test_qualquer_coisa_alem_da_frase_exata_nao_e_aceite(texto):
    assert strict_decision(texto, irreversible=False) is None
    assert strict_decision(texto, irreversible=True) is None


def test_irreversivel_exige_confirmo():
    assert strict_decision("sim", irreversible=True) == EXIGE_CONFIRMO
    assert strict_decision("pode executar", irreversible=True) == EXIGE_CONFIRMO
    assert strict_decision("confirmo", irreversible=True) == "aceitar"
    assert strict_decision("sim, confirmo", irreversible=True) == "aceitar"


@pytest.mark.parametrize("irreversivel", [True, False])
def test_recusa_vale_em_qualquer_caso(irreversivel):
    assert strict_decision("não", irreversivel) == "recusar"
    assert strict_decision("cancela", irreversivel) == "recusar"


def test_quick_decision_continua_reconhecendo_confirmo():
    assert quick_decision("confirmo") == "aceitar"
