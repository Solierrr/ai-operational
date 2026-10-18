from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.screen_finder.screen_finder_prompt import SCREEN_FINDER_AGENT
from src.tools.screens import buscar_tela
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def screen_finder_node(state: GraphState, config=None) -> dict:
    agent = build_agent(SCREEN_FINDER_AGENT, tools=[buscar_tela])
    result = await agent.ainvoke(
        {"messages": messages_with_summary(state)}, config=config
    )
    return {
        "messages": [AIMessage(content=result["messages"][-1].content)],
        "turn_agents": append_turn_agent(state, "screen_finder"),
    }
