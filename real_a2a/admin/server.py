"""Runs the Admin CrewAI orchestrator as an A2A service."""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from a2a.types import AgentSkill

from real_a2a.admin.router import route_and_call
from real_a2a.shared import config
from real_a2a.shared.a2a_server import build_agent_card, run_a2a_service
from real_a2a.shared.executor_base import SimpleAgentExecutor


async def _admin_invoke(query: str) -> str:
    target, reply = await route_and_call(query)
    return f"[routed to: {target}]\n\n{reply}"


def main() -> None:
    skill = AgentSkill(
        id="admin_router",
        name="Admin Router",
        description="Routes user queries to text2sql, rag, or deep-research child agents.",
        tags=["admin", "router", "orchestrator"],
        examples=[
            "How many orders did we get in June?",
            "What is our remote work policy?",
            "Research trade-offs of monolith vs microservices.",
        ],
    )
    card = build_agent_card(
        name="Admin Agent (CrewAI)",
        description="Chat entrypoint that routes to Text2SQL, RAG, or DeepResearch children.",
        url=config.ADMIN_BASE_URL,
        skills=[skill],
    )
    executor = SimpleAgentExecutor(
        invoke=_admin_invoke, working_message="Routing to a specialist..."
    )
    run_a2a_service(
        agent_card=card,
        executor=executor,
        host=config.ADMIN_HOST,
        port=config.ADMIN_PORT,
    )


if __name__ == "__main__":
    main()
