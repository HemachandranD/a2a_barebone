"""Runs the CrewAI Text2SQL child agent as an A2A service."""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from a2a.types import AgentSkill

from real_a2a.children.text2sql_crewai.agent import invoke
from real_a2a.shared import config
from real_a2a.shared.a2a_server import build_agent_card, run_a2a_service
from real_a2a.shared.executor_base import SimpleAgentExecutor
from real_a2a.shared.observent_otel import init_observability


def main() -> None:
    init_observability("text2sql")
    skill = AgentSkill(
        id="text2sql",
        name="Text to SQL",
        description="Generates and runs read-only SQLite queries against the demo database.",
        tags=["sql", "text2sql", "analytics"],
        examples=[
            "How many customers signed up in March 2024?",
            "What is the total revenue from Pro Plan subscriptions?",
        ],
    )
    card = build_agent_card(
        name="Text2SQL Agent (CrewAI)",
        description="Translates natural language questions into SQLite queries.",
        url=config.TEXT2SQL_BASE_URL,
        skills=[skill],
    )
    executor = SimpleAgentExecutor(
        invoke=invoke, working_message="Generating and executing SQL..."
    )
    run_a2a_service(
        agent_card=card,
        executor=executor,
        host=config.TEXT2SQL_HOST,
        port=config.TEXT2SQL_PORT,
    )


if __name__ == "__main__":
    main()
