"""Resultado do turno (outcome e reason): o que aconteceu dentro da conversa não é
erro HTTP, então volta 200 com um código que o front traduz."""

from enum import StrEnum


class Outcome(StrEnum):
    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"
    DEGRADED = "DEGRADED"
    TOOL_FAILED = "TOOL_FAILED"


class Reason(StrEnum):
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    MANIPULATION_ATTEMPT = "MANIPULATION_ATTEMPT"
    INTERNAL_DATA_REQUEST = "INTERNAL_DATA_REQUEST"
    FALSE_INFORMATION = "FALSE_INFORMATION"
    GUARDRAIL_REFUSED = "GUARDRAIL_REFUSED"
    GUARDRAIL_UNAVAILABLE = "GUARDRAIL_UNAVAILABLE"
    ANSWER_REJECTED = "ANSWER_REJECTED"
    ACTION_FAILED = "ACTION_FAILED"


_BLOCKED_PREFIX = "input_guardrail_blocked_"

_REFUSAL_REASONS = {
    "fora_escopo": Reason.OUT_OF_SCOPE,
    "redirecionar": Reason.OUT_OF_SCOPE,
    "manipulacao": Reason.MANIPULATION_ATTEMPT,
    "manipulacao_regex": Reason.MANIPULATION_ATTEMPT,
    "dados_internos": Reason.INTERNAL_DATA_REQUEST,
    "dados_internos_regex": Reason.INTERNAL_DATA_REQUEST,
    "informacao_falsa": Reason.FALSE_INFORMATION,
}


def outcome_kwargs(outcome: Outcome, reason: Reason) -> dict:
    return {"outcome": outcome.value, "reason": reason.value}


def turn_outcome(final_state: dict) -> tuple[Outcome, Reason | None]:
    """Lê o resultado marcado na mensagem final (falha de ação, guardrail de saída)
    ou, sem marca, deduz dos passos do turno (recusas dos guardrails e do juiz)."""
    metadata = final_state["messages"][-1].additional_kwargs
    if metadata.get("outcome"):
        return Outcome(metadata["outcome"]), Reason(metadata["reason"])

    steps = final_state.get("turn_agents", [])
    for step in steps:
        if step.startswith(_BLOCKED_PREFIX):
            category = step.removeprefix(_BLOCKED_PREFIX)
            if category == "falha_avaliacao_guardrail":
                return Outcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE
            return Outcome.REFUSED, _REFUSAL_REASONS.get(
                category, Reason.GUARDRAIL_REFUSED
            )
    if "judge_blocked" in steps:
        return Outcome.REFUSED, Reason.ANSWER_REJECTED
    return Outcome.ANSWERED, None
