from ai_lib.guardrails import make_input_guardrail_node

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.prompt import _PROMPT_CLASSIFICADOR
from src.core.llm.llm_groq import llm_groq

INPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_CLASSIFICADOR, include_communication_standards=False
)

BLOCKED_RESPONSE = (
    "Desculpe, não posso processar essa solicitação por políticas de segurança."
)

input_guardrail_node = make_input_guardrail_node(
    prompt=INPUT_GUARDRAIL_PROMPT,
    llm=lambda: llm_groq(),
    blocked_response=BLOCKED_RESPONSE,
)
