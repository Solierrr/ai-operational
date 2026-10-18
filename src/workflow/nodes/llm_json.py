import json
import re

from langchain_core.messages import HumanMessage

from src.core.llm.llm_chain import llm_chain

_JSON_OBJETO = re.compile(r"\{.*\}", re.DOTALL)


class InvalidJsonReply(ValueError):
    """O LLM não devolveu um objeto JSON utilizável."""


def parse_json_object(texto: str) -> dict:
    if not isinstance(texto, str):
        raise InvalidJsonReply("A resposta do LLM não é texto")
    achado = _JSON_OBJETO.search(texto)
    if not achado:
        raise InvalidJsonReply("A resposta do LLM não tem objeto JSON")
    try:
        dados = json.loads(achado.group(0))
    except json.JSONDecodeError as erro:
        raise InvalidJsonReply("JSON inválido na resposta do LLM") from erro
    if not isinstance(dados, dict):
        raise InvalidJsonReply("A resposta do LLM não é um objeto JSON")
    return dados


async def ask_json(prompt: str, config=None) -> dict:
    resposta = await llm_chain(temperature=0).ainvoke(
        [HumanMessage(content=prompt)], config=config
    )
    return parse_json_object(resposta.content)


async def ask_text(prompt: str, config=None) -> str:
    resposta = await llm_chain(temperature=0.3).ainvoke(
        [HumanMessage(content=prompt)], config=config
    )
    return str(resposta.content).strip()
