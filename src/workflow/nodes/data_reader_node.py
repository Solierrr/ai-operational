from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.data_reader.data_reader_prompt import DATA_READER_AGENT
from src.tools.account import READER_TOOLS
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def data_reader_node(state: GraphState, config=None) -> dict:
    agent = build_agent(DATA_READER_AGENT, tools=READER_TOOLS)
    result = await agent.ainvoke(
        {"messages": messages_with_summary(state)}, config=config
    )
    return {
        "messages": [AIMessage(content=result["messages"][-1].content)],
        "turn_agents": append_turn_agent(state, "data_reader"),
    }
