import pytest

from src.workflow.edges.routing_edges import (
    decide_post_input_guardrail,
    decide_post_judge,
    decide_post_proposal,
    decide_post_router,
)


def test_decide_post_input_guardrail_returns_end_for_end_route():
    assert decide_post_input_guardrail({"route": "end"}) == "end"


def test_decide_post_input_guardrail_returns_proceed_for_other_routes():
    assert decide_post_input_guardrail({"route": "screen_finder"}) == "proceed"


@pytest.mark.parametrize(
    "route",
    [
        "screen_finder",
        "action_proposer",
        "end",
    ],
)
def test_decide_post_router_returns_the_selected_route(route):
    assert decide_post_router({"route": route}) == route


def test_decide_post_router_returns_orchestrator_directly():
    assert decide_post_router({"route": "orchestrator"}) == "orchestrator"


def test_decide_post_router_falls_back_to_orchestrator_when_route_was_already_consulted():
    assert (
        decide_post_router(
            {
                "route": "screen_finder",
                "turn_agents": ["screen_finder", "router"],
            }
        )
        == "orchestrator"
    )


def test_decide_post_judge_returns_retry():
    assert decide_post_judge({"judge_status": "retry"}) == "retry"


def test_decide_post_judge_returns_output_guardrail_when_approved():
    assert decide_post_judge({"judge_status": "approved"}) == "output_guardrail"


def test_decide_post_judge_returns_output_guardrail_when_blocked():
    assert decide_post_judge({"judge_status": "blocked"}) == "output_guardrail"


def test_decide_post_proposal_volta_ao_roteador_so_no_reroute():
    assert decide_post_proposal({"route": "reroute"}) == "router"
    assert decide_post_proposal({"route": "end"}) == "end"
    assert decide_post_proposal({}) == "end"


@pytest.mark.parametrize("route", ["how_to_guide", "data_reader"])
def test_decide_post_router_aceita_os_novos_especialistas(route):
    assert decide_post_router({"route": route}) == route
