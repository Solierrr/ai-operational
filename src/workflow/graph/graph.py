from langgraph.graph import END, StateGraph

from src.memory.session.mongo_checkpointer import create_mongo_checkpointer
from src.workflow.edges import (
    decide_post_input_guardrail,
    decide_post_judge,
    decide_post_proposal,
    decide_post_router,
)
from src.workflow.nodes.action_proposer_node import action_proposer_node
from src.workflow.nodes.data_reader_node import data_reader_node
from src.workflow.nodes.how_to_guide_node import how_to_guide_node
from src.workflow.nodes.input_guardrail_node import input_guardrail_node
from src.workflow.nodes.judge_node import judge_node
from src.workflow.nodes.orchestrator_node import orchestrator_node
from src.workflow.nodes.output_guardrail_node import output_guardrail_node
from src.workflow.nodes.proposal_decision_node import proposal_decision_node
from src.workflow.nodes.router_node import router_node
from src.workflow.nodes.screen_finder_node import screen_finder_node
from src.workflow.nodes.summary_node import condense_history_node
from src.workflow.state import GraphState

graph = StateGraph(GraphState)

graph.add_node("input_guardrail", input_guardrail_node)
graph.add_node("condense_memory", condense_history_node)
graph.add_node("router", router_node)
# Adicione um graph.add_node(...) aqui para cada novo especialista, com o
# mesmo nome usado em `src/workflow/config.py` (SPECIALIST_ROUTES).
graph.add_node("screen_finder", screen_finder_node)
graph.add_node("action_proposer", action_proposer_node)
graph.add_node("how_to_guide", how_to_guide_node)
graph.add_node("data_reader", data_reader_node)
graph.add_node("proposal_decision", proposal_decision_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("judge", judge_node)
graph.add_node("output_guardrail", output_guardrail_node)

graph.set_entry_point("input_guardrail")

graph.add_conditional_edges(
    "input_guardrail",
    decide_post_input_guardrail,
    {"proceed": "condense_memory", "end": END},
)

graph.add_edge("condense_memory", "router")

graph.add_conditional_edges(
    "router",
    decide_post_router,
    {
        "screen_finder": "screen_finder",
        "action_proposer": "action_proposer",
        "how_to_guide": "how_to_guide",
        "data_reader": "data_reader",
        "proposal_decision": "proposal_decision",
        "orchestrator": "orchestrator",
        "end": "output_guardrail",
    },
)

graph.add_edge("screen_finder", "router")
graph.add_edge("how_to_guide", "router")
graph.add_edge("data_reader", "router")
# Propostas e resultados de ações chegam ao usuário exatamente como foram montados.
graph.add_edge("action_proposer", END)
graph.add_conditional_edges(
    "proposal_decision",
    decide_post_proposal,
    {"router": "router", "end": END},
)
graph.add_edge("orchestrator", "judge")

graph.add_conditional_edges(
    "judge",
    decide_post_judge,
    {"retry": "orchestrator", "output_guardrail": "output_guardrail"},
)

graph.add_edge("output_guardrail", END)

memory = create_mongo_checkpointer()

compiled_app = graph.compile(checkpointer=memory)
