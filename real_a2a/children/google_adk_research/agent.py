"""Google ADK DeepResearch agent (plan then synthesize)."""

from ...shared import config
from ...shared.llm import adk_model


_APP_NAME = "deepresearch"
_USER_ID = "a2a-user"

_INSTRUCTION = (
    "You are a rigorous deep-research analyst. "
    "For every user query, follow these steps in the SAME response:\n"
    "1. Restate the question in one sentence.\n"
    "2. Decompose it into 3 focused sub-questions.\n"
    "3. Provide a concise, evidence-based analysis for each sub-question.\n"
    "4. Summarize the overall finding in 3-5 bullet points.\n"
    "5. Flag key uncertainties or missing information.\n"
    "Keep the total response under 400 words. "
    "Be factual, avoid speculation, and clearly label unknowns."
)


def _build_agent():
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="deep_researcher",
        model=adk_model(config.DEEPRESEARCH_MODEL),
        description="Performs structured multi-step research on a topic.",
        instruction=_INSTRUCTION,
    )


_AGENT = None
_RUNNER = None
_SESSION_SERVICE = None


def _runner():
    global _AGENT, _RUNNER, _SESSION_SERVICE
    if _RUNNER is not None:
        return _RUNNER, _SESSION_SERVICE

    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    _AGENT = _build_agent()
    _SESSION_SERVICE = InMemorySessionService()
    _RUNNER = Runner(
        agent=_AGENT, app_name=_APP_NAME, session_service=_SESSION_SERVICE
    )
    return _RUNNER, _SESSION_SERVICE


async def invoke(query: str) -> str:
    from google.genai import types

    from real_a2a.shared.observent_capture import capture_output, open_or_enrich_span, set_error, set_ok

    runner, session_service = _runner()

    with open_or_enrich_span(
        {"query": query},
        name="deepresearch.run",
        agent_name="deepresearch",
        agent_role="research-analyst",
        agent_framework="google-adk",
    ) as span:
        try:
            session = await session_service.create_session(
                app_name=_APP_NAME, user_id=_USER_ID
            )

            content = types.Content(
                role="user", parts=[types.Part.from_text(text=query)]
            )

            final_text = ""
            async for event in runner.run_async(
                user_id=_USER_ID, session_id=session.id, new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = "".join(
                        p.text or "" for p in event.content.parts if hasattr(p, "text")
                    )
        except BaseException as exc:
            set_error(exc, span)
            raise

        result = final_text or "(no response)"
        capture_output(result, span)
        set_ok(span)
        return result
