"""Runs the LangGraph RAG child agent as an A2A service."""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from a2a.types import AgentSkill

from real_a2a.children.langgraph_rag.agent import invoke
from real_a2a.shared import config
from real_a2a.shared.a2a_server import build_agent_card, run_a2a_service
from real_a2a.shared.executor_base import SimpleAgentExecutor
from real_a2a.shared.observent_otel import init_observability


def main() -> None:
    init_observability("rag")
    skill = AgentSkill(
        id="policy_rag",
        name="Company Policy RAG",
        description="Answers questions grounded in the seeded policy and manual documents.",
        tags=["rag", "policy", "manual"],
        examples=[
            "How many days of annual leave do employees get?",
            "What is the data retention on the Pro Plan?",
        ],
    )
    card = build_agent_card(
        name="RAG Agent (LangGraph)",
        description="Retrieves relevant policy/manual chunks and answers using an LLM.",
        url=config.RAG_BASE_URL,
        skills=[skill],
    )
    executor = SimpleAgentExecutor(
        invoke=invoke, working_message="Retrieving and generating answer..."
    )
    run_a2a_service(
        agent_card=card,
        executor=executor,
        host=config.RAG_HOST,
        port=config.RAG_PORT,
    )


if __name__ == "__main__":
    main()
