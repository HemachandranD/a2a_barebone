"""CrewAI-based router that picks one of three child agents for a query."""

import textwrap

from ..shared import config
from ..shared.a2a_client import call_agent
from ..shared.llm import crewai_llm


_VALID_TARGETS = {"text2sql", "rag", "research"}


def _classify_sync(question: str) -> str:
    from crewai import Agent, Crew, Process, Task

    llm = crewai_llm(config.ADMIN_MODEL)

    classifier = Agent(
        role="Query Router",
        goal="Route each user question to exactly one specialist agent.",
        backstory=(
            "You are a strict router. You never answer questions. "
            "You only pick ONE of: text2sql, rag, research."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )

    task = Task(
        description=textwrap.dedent(
            f"""
            Available specialists:
            - text2sql: answers questions that need to query the internal SQLite
              analytics database (customers, products, orders, revenue, counts).
            - rag: answers questions about internal company policies and product
              manuals (leave policy, expenses, plan pricing, data retention).
            - research: answers general open-ended research questions that
              require decomposition and synthesis (industry topics, trade-offs).

            User question:
            {question}

            Respond with EXACTLY one of these three lowercase tokens and nothing else:
            text2sql
            rag
            research
            """
        ).strip(),
        expected_output="One of: text2sql | rag | research",
        agent=classifier,
    )

    crew = Crew(
        agents=[classifier],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    output = str(crew.kickoff()).strip().lower()
    for token in _VALID_TARGETS:
        if token in output:
            return token
    return "research"


async def route_and_call(question: str) -> tuple[str, str]:
    """Classify the question, dispatch to the chosen child agent, return (target, text)."""
    import asyncio

    target = await asyncio.to_thread(_classify_sync, question)

    if target == "text2sql":
        base_url = config.TEXT2SQL_BASE_URL
    elif target == "rag":
        base_url = config.RAG_BASE_URL
    else:
        base_url = config.DEEPRESEARCH_BASE_URL

    reply = await call_agent(base_url, question)
    return target, reply
