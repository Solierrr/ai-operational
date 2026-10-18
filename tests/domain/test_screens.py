import pytest

from src.domain.screens import ROUTE_SEGMENTS, SCREENS, find_screens
from src.tools.screens import buscar_tela


def test_toda_tela_usa_segmentos_existentes_nos_tres_idiomas():
    for lang, tabela in ROUTE_SEGMENTS.items():
        for tela in SCREENS:
            for segmento in tela.segments:
                assert segmento in tabela, (lang, tela.id, segmento)


def test_ids_de_tela_sao_unicos():
    ids = [tela.id for tela in SCREENS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    "consulta, tela",
    [
        ("onde cadastro minha empresa?", "Cadastrar empresa"),
        ("quero criar uma oferta de placa", "Gerenciar ofertas"),
        ("onde troco minha senha", "Segurança"),
        ("ver meus pedidos", "Meus pedidos"),
        ("preciso achar a tela de funcionários", "Funcionários"),
        ("como cadastro um modelo de placa", "Modelos de placa solar"),
        ("como solicitar uma marca nova", "Solicitações de marca"),
        ("qual a tela dos meus projetos", "Projetos"),
    ],
)
def test_a_melhor_tela_responde_ao_que_o_usuario_quer(consulta, tela):
    assert find_screens(consulta)[0]["tela"] == tela


def test_caminhos_seguem_o_idioma():
    assert (
        find_screens("cadastrar empresa", "pt-BR")[0]["caminho"]
        == "/pt-BR/cadastro/empresa"
    )
    assert (
        find_screens("cadastrar empresa", "en-US")[0]["caminho"]
        == "/en-US/register/company"
    )
    assert (
        find_screens("cadastrar empresa", "es-ES")[0]["caminho"]
        == "/es-ES/registro/empresa"
    )


def test_idioma_desconhecido_usa_o_padrao():
    assert find_screens("carrinho", "fr-FR")[0]["caminho"] == "/pt-BR/carrinho"


def test_sem_correspondencia_devolve_lista_vazia():
    assert find_screens("xyzzy plugh") == []


def test_o_limite_de_resultados_e_respeitado():
    assert len(find_screens("empresa", limit=2)) <= 2


def test_ferramenta_devolve_as_telas_para_o_agente():
    resultado = buscar_tela.invoke({"consulta": "carrinho"})

    assert resultado[0]["tela"] == "Carrinho"
    assert set(resultado[0]) == {"tela", "descricao", "caminho", "para_quem"}
