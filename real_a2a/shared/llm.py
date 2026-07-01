"""Per-framework LLM factories that all target OpenRouter."""

from . import config


def crewai_llm(model: str):
    """Return a CrewAI ``LLM`` wired to OpenRouter."""
    from crewai import LLM

    config.ensure_openrouter_env()
    return LLM(
        model=model,
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
    )


def langchain_llm(model: str, temperature: float = 0.2):
    """Return a LangChain ``ChatOpenAI`` wired to OpenRouter."""
    from langchain_openai import ChatOpenAI

    litellm_prefix = "openrouter/"
    openai_model = (
        model[len(litellm_prefix):] if model.startswith(litellm_prefix) else model
    )
    return ChatOpenAI(
        model=openai_model,
        base_url=config.OPENROUTER_BASE_URL,
        api_key=config.OPENROUTER_API_KEY,
        temperature=temperature,
    )


def adk_model(model: str):
    """Return a Google ADK ``LiteLlm`` wired to OpenRouter."""
    from google.adk.models.lite_llm import LiteLlm

    config.ensure_openrouter_env()
    return LiteLlm(model=model)
