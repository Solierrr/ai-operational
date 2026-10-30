from langchain_core.messages import AIMessage

from src.workflow.outcome import Outcome, Reason, outcome_kwargs
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def reply(
    state: GraphState,
    agent: str,
    text: str,
    *,
    outcome: tuple[Outcome, Reason] | None = None,
    **state_updates,
) -> dict:
    """Resposta final de um nó que fala direto com o usuário, sem passar pelo
    orquestrador, pelo juiz e pelo guardrail de saída: o texto é montado a partir de
    campos validados e precisa chegar exatamente como foi escrito."""
    steps = append_turn_agent(state, agent)
    message = AIMessage(
        content=text,
        additional_kwargs={
            "specialists_used": [agent],
            "workflow_steps": steps,
            **(outcome_kwargs(*outcome) if outcome else {}),
        },
    )
    return {"messages": [message], "turn_agents": steps, **state_updates}
