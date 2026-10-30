import pytest

from src.domain.guides import GUIDES, find_guides
from src.domain.screens import SCREENS

TELAS = {screen.id for screen in SCREENS}


def test_todo_passo_aponta_para_uma_tela_que_existe():
    for guide in GUIDES:
        for passo in guide.passos:
            assert passo.tela is None or passo.tela in TELAS, (guide.id, passo.tela)


def test_ids_dos_guias_sao_unicos_e_todo_guia_tem_passos():
    ids = [guide.id for guide in GUIDES]
    assert len(ids) == len(set(ids))
    assert all(guide.passos for guide in GUIDES)


@pytest.mark.parametrize(
    "pergunta,esperado",
    [
        ("como eu cadastro uma oferta?", "Cadastrar uma oferta de placa"),
        ("quero pausar uma oferta", "Pausar, reativar ou encerrar uma oferta"),
        ("como faço para comprar placa", "Comprar placas"),
        ("esqueci minha senha", "Trocar ou recuperar a senha"),
        ("como ajustar estoque", "Ajustar o estoque"),
        ("como cadastrar minha empresa", "Cadastrar a sua empresa"),
    ],
)
def test_busca_acha_o_guia_certo_primeiro(pergunta, esperado):
    assert find_guides(pergunta)[0]["guia"] == esperado


def test_busca_sem_relacao_nao_devolve_guia():
    assert find_guides("qual a previsão do tempo amanhã") == []


def test_passos_trazem_caminho_no_idioma_pedido():
    guia = find_guides("cadastrar oferta", "en-US")[0]

    caminhos = [p["caminho"] for p in guia["passos"] if "caminho" in p]

    assert caminhos
    assert all(c.startswith("/en-US/") for c in caminhos)


def test_guia_indica_quando_o_assistente_pode_fazer_pelo_usuario():
    oferta = find_guides("cadastrar oferta")[0]
    senha = find_guides("esqueci minha senha")[0]

    assert oferta["o_assistente_pode_fazer"] is True
    assert senha["o_assistente_pode_fazer"] is False
