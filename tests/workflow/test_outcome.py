from langchain_core.messages import AIMessage

from src.workflow.outcome import Outcome, Reason, outcome_kwargs, turn_outcome


def _state(steps, **kwargs):
    return {
        "messages": [AIMessage(content="x", additional_kwargs=kwargs)],
        "turn_agents": steps,
    }


def test_plain_turn_is_answered():
    assert turn_outcome(_state(["input_guardrail_approved", "router"])) == (
        Outcome.ANSWERED,
        None,
    )


def test_marked_message_wins():
    state = _state(
        ["input_guardrail_approved", "action_proposer"],
        **outcome_kwargs(Outcome.TOOL_FAILED, Reason.ACTION_FAILED),
    )

    assert turn_outcome(state) == (Outcome.TOOL_FAILED, Reason.ACTION_FAILED)


def test_input_guardrail_refusals_map_to_reasons():
    cases = {
        "fora_escopo": Reason.OUT_OF_SCOPE,
        "redirecionar": Reason.OUT_OF_SCOPE,
        "manipulacao_regex": Reason.MANIPULATION_ATTEMPT,
        "dados_internos": Reason.INTERNAL_DATA_REQUEST,
        "informacao_falsa": Reason.FALSE_INFORMATION,
        "categoria_nova": Reason.GUARDRAIL_REFUSED,
    }
    for category, reason in cases.items():
        state = _state([f"input_guardrail_blocked_{category}"])
        assert turn_outcome(state) == (Outcome.REFUSED, reason)


def test_guardrail_failure_is_degraded():
    state = _state(["input_guardrail_blocked_falha_avaliacao_guardrail"])

    assert turn_outcome(state) == (Outcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE)


def test_judge_block_is_refused():
    state = _state(["router", "orchestrator", "judge_blocked", "output_guardrail"])

    assert turn_outcome(state) == (Outcome.REFUSED, Reason.ANSWER_REJECTED)
