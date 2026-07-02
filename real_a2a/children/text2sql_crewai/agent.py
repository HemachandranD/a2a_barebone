"""CrewAI Text2SQL agent that generates and executes read-only SQL."""

import re
import sqlite3
import textwrap
from typing import List

from ...shared import config
from ...shared.llm import crewai_llm


def _schema_summary(db_path=config.SEED_DB_PATH) -> str:
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        lines: List[str] = []
        for (table,) in tables:
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            col_defs = ", ".join(f"{c[1]} {c[2]}" for c in cols)
            lines.append(f"- {table}({col_defs})")
    return "\n".join(lines)


def _extract_sql(text: str) -> str:
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip().rstrip(";")
    match = re.search(
        r"(SELECT|WITH)\s+.*", text, re.IGNORECASE | re.DOTALL
    )
    if match:
        return match.group(0).strip().rstrip(";")
    return text.strip().rstrip(";")


def _is_read_only(sql: str) -> bool:
    lowered = sql.lower().strip()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False
    banned = ["insert ", "update ", "delete ", "drop ", "alter ", "create ", "attach "]
    return not any(b in lowered for b in banned)


def _run_query(sql: str, db_path=config.SEED_DB_PATH) -> str:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(sql)
        columns = [c[0] for c in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(50)
    if not rows:
        return "(no rows)"
    header = " | ".join(columns)
    separator = "-+-".join("-" * len(c) for c in columns)
    body = "\n".join(" | ".join(str(v) for v in row) for row in rows)
    return f"{header}\n{separator}\n{body}"


def _build_crew(question: str):
    from crewai import Agent, Crew, Process, Task

    llm = crewai_llm(config.TEXT2SQL_MODEL)
    schema = _schema_summary()

    sql_writer = Agent(
        role="SQLite SQL Writer",
        goal="Translate a business question into a single valid read-only SQLite SELECT query.",
        backstory=(
            "You are a careful SQL analyst. You always work with the provided schema, "
            "never invent columns, and always return read-only SELECT statements."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=False,
    )

    task = Task(
        description=textwrap.dedent(
            f"""
            Database schema:
            {schema}

            User question:
            {question}

            Rules:
            - Return ONLY a single SQLite-compatible SELECT statement.
            - Do not modify data (no INSERT/UPDATE/DELETE/DROP/ALTER).
            - Wrap the final SQL in a ```sql code block.
            """
        ).strip(),
        expected_output="A single SQLite SELECT statement inside a ```sql block.",
        agent=sql_writer,
    )

    return Crew(
        agents=[sql_writer],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


async def invoke(query: str) -> str:
    """Turn a natural language question into a SQL query, execute it, and return results."""
    from real_a2a.shared.observent_capture import capture_output, open_or_enrich_span, set_error, set_ok

    with open_or_enrich_span(
        {"query": query},
        name="text2sql.run",
        agent_name="text2sql",
        agent_role="sql-writer",
        agent_framework="crewai",
    ) as span:
        try:
            crew = _build_crew(query)
            generation = await crew.kickoff_async()
            sql = _extract_sql(str(generation))
            if not _is_read_only(sql):
                result = (
                    "Refusing to run non read-only SQL. Generated statement was:\n"
                    f"{sql}"
                )
            else:
                try:
                    results = _run_query(sql)
                    result = f"SQL:\n{sql}\n\nResults (up to 50 rows):\n{results}"
                except Exception as exc:
                    result = f"SQL failed: {exc}\n\nAttempted SQL:\n{sql}"
        except BaseException as exc:
            set_error(exc, span)
            raise

        capture_output(result, span)
        set_ok(span)
        return result
