"""Smoke test that verifies each A2A route end-to-end.

Assumes all 4 services are running (see ``run_all.py``).
"""

import asyncio
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from real_a2a.shared import config
from real_a2a.shared.a2a_client import call_agent


TESTS = [
    (
        "Text2SQL child",
        config.TEXT2SQL_BASE_URL,
        "How many customers are from India?",
    ),
    (
        "RAG child",
        config.RAG_BASE_URL,
        "How many days of paid annual leave do full time employees receive?",
    ),
    (
        "DeepResearch child",
        config.DEEPRESEARCH_BASE_URL,
        "What are the trade-offs of remote-only vs hybrid work for engineering teams?",
    ),
    (
        "Admin (routes to text2sql)",
        config.ADMIN_BASE_URL,
        "How many customers are from India?",
    ),
    (
        "Admin (routes to rag)",
        config.ADMIN_BASE_URL,
        "What is our expense policy for meals during business travel?",
    ),
    (
        "Admin (routes to research)",
        config.ADMIN_BASE_URL,
        "Research the impact of async communication on distributed teams.",
    ),
]


async def _run() -> None:
    for label, url, question in TESTS:
        print(f"\n=== {label} ===")
        print(f"URL: {url}")
        print(f"Q: {question}")
        try:
            answer = await call_agent(url, question, timeout=180.0)
        except Exception as exc:
            answer = f"[error] {exc}"
        print(f"A:\n{answer}")


if __name__ == "__main__":
    asyncio.run(_run())
