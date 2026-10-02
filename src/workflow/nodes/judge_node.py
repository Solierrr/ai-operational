from ai_lib.guardrails import make_judge_node

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.judge.judge_prompt import JUDGE_AGENT
from src.core.llm.llm_groq import llm_groq

JUDGE_PROMPT = build_system_prompt(JUDGE_AGENT, include_communication_standards=False)

MAX_JUDGE_RETRIES = 1

BLOCKED_RESPONSE = (
    "Não foi possível gerar uma resposta confiável para essa solicitação. "
    "Poderia reformular sua pergunta com mais detalhes?"
)

judge_node = make_judge_node(
    prompt=JUDGE_PROMPT,
    llm=lambda: llm_groq(),
    blocked_response=BLOCKED_RESPONSE,
    max_retries=MAX_JUDGE_RETRIES,
)
