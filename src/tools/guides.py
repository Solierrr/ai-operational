from langchain_core.tools import tool

from src.domain.guides import find_guides


@tool
def buscar_guia(assunto: str, idioma: str = "pt-BR") -> list[dict]:
    """Procura o passo a passo de como fazer algo na plataforma (cadastrar empresa,
    cadastrar oferta, comprar, ajustar estoque etc.). Devolve até 2 guias com
    requisitos, passos numerados, caminhos das telas e dicas. Idiomas: pt-BR,
    en-US ou es-ES."""
    return find_guides(assunto, idioma)
