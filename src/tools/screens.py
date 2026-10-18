from langchain_core.tools import tool

from src.domain.screens import find_screens


@tool
def buscar_tela(consulta: str, idioma: str = "pt-BR") -> list[dict]:
    """Procura no web-app a tela que atende ao que o usuário quer fazer ou achar.
    Devolve até 3 telas com nome, descrição, caminho e para quem se destina.
    Idiomas: pt-BR, en-US ou es-ES."""
    return find_screens(consulta, idioma)
