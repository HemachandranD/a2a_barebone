"""Runs the Google ADK DeepResearch child agent as an A2A service."""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from a2a.types import AgentSkill

from real_a2a.children.google_adk_research.agent import invoke
from real_a2a.shared import config
from real_a2a.shared.a2a_server import build_agent_card, run_a2a_service
from real_a2a.shared.executor_base import SimpleAgentExecutor
from real_a2a.shared.observent_otel import init_observability


def main() -> None:
    init_observability("deepresearch")
    skill = AgentSkill(
        id="deep_research",
        name="Deep Research",
        description="Decomposes a question into sub-questions and synthesizes a structured research answer.",
        tags=["research", "analysis", "deepresearch"],
        examples=[
            "Research the impact of remote work on knowledge worker productivity.",
            "Analyze the trade-offs of monolith vs microservices architecture.",
        ],
    )
    card = build_agent_card(
        name="DeepResearch Agent (Google ADK)",
        description="Structured multi-step research answers via Google ADK.",
        url=config.DEEPRESEARCH_BASE_URL,
        skills=[skill],
    )
    executor = SimpleAgentExecutor(
        invoke=invoke, working_message="Running deep research..."
    )
    run_a2a_service(
        agent_card=card,
        executor=executor,
        host=config.DEEPRESEARCH_HOST,
        port=config.DEEPRESEARCH_PORT,
    )


if __name__ == "__main__":
    main()
