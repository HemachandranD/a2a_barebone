"""Centralized configuration for the real A2A multi-agent setup."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


REAL_A2A_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = REAL_A2A_ROOT.parent
ENV_PATH = REPO_ROOT / ".env"

if load_dotenv is not None and ENV_PATH.exists():
    load_dotenv(ENV_PATH)


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)


def _model(name: str, default: str) -> str:
    """Return an OpenRouter-ready model string. Auto-prefixes ``openrouter/``."""
    value = os.getenv(name, default)
    if not value.startswith("openrouter/"):
        value = f"openrouter/{value}"
    return value


ADMIN_MODEL = _model("ADMIN_MODEL", "openai/gpt-4o-mini")
TEXT2SQL_MODEL = _model("TEXT2SQL_MODEL", "openai/gpt-4o-mini")
RAG_MODEL = _model("RAG_MODEL", "openai/gpt-4o-mini")
DEEPRESEARCH_MODEL = _model("DEEPRESEARCH_MODEL", "openai/gpt-4o-mini")


ADMIN_HOST = os.getenv("ADMIN_HOST", "127.0.0.1")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "9000"))
ADMIN_BASE_URL = os.getenv("ADMIN_BASE_URL", f"http://{ADMIN_HOST}:{ADMIN_PORT}")

TEXT2SQL_HOST = os.getenv("TEXT2SQL_HOST", "127.0.0.1")
TEXT2SQL_PORT = int(os.getenv("TEXT2SQL_PORT", "9001"))
TEXT2SQL_BASE_URL = os.getenv(
    "TEXT2SQL_BASE_URL", f"http://{TEXT2SQL_HOST}:{TEXT2SQL_PORT}"
)

RAG_HOST = os.getenv("RAG_HOST", "127.0.0.1")
RAG_PORT = int(os.getenv("RAG_PORT", "9002"))
RAG_BASE_URL = os.getenv("RAG_BASE_URL", f"http://{RAG_HOST}:{RAG_PORT}")

DEEPRESEARCH_HOST = os.getenv("DEEPRESEARCH_HOST", "127.0.0.1")
DEEPRESEARCH_PORT = int(os.getenv("DEEPRESEARCH_PORT", "9003"))
DEEPRESEARCH_BASE_URL = os.getenv(
    "DEEPRESEARCH_BASE_URL", f"http://{DEEPRESEARCH_HOST}:{DEEPRESEARCH_PORT}"
)


DATA_DIR = REAL_A2A_ROOT / "data"
SEED_DB_PATH = DATA_DIR / "seed_demo.db"
SEED_DOCS_DIR = DATA_DIR / "seed_docs"


def ensure_openrouter_env() -> None:
    """LiteLLM (used by CrewAI and Google ADK) reads OPENROUTER_API_KEY from env."""
    if OPENROUTER_API_KEY:
        os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
