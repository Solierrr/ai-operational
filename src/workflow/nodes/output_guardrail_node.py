from ai_lib.guardrails import make_output_guardrail_node

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.prompt import _PROMPT_COMPLIANCE
from src.core.llm.llm_groq import llm_groq
from src.workflow.config import SPECIALIST_ROUTES

OUTPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_COMPLIANCE, include_communication_standards=False
)

FALLBACK_RESPONSE = "Não foi possível processar sua solicitação no momento. Tente novamente em instantes."

output_guardrail_node = make_output_guardrail_node(
    prompt=OUTPUT_GUARDRAIL_PROMPT,
    llm=lambda: llm_groq(),
    fallback_response=FALLBACK_RESPONSE,
    specialists=SPECIALIST_ROUTES,
)
