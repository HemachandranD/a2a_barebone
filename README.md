# a2a_barebone

Minimal real A2A multi-agent setup: one CrewAI **Admin** orchestrator plus three specialist child agents (**CrewAI Text2SQL**, **LangGraph RAG**, **Google ADK DeepResearch**). All four services run as independent A2A JSON-RPC services and share a single OpenRouter API key with per-agent model selection.

Admin acts as the chat entrypoint: on each incoming query it classifies intent and dispatches to exactly one child over A2A.

## Layout

- `pilot/server.py`, `pilot/client.py`, `pilot/executor.py` - original hello-world A2A mock (kept as-is).
- `real_a2a/` - the real multi-agent setup.
  - `shared/` - config, LLM factories, and reusable A2A server/client/executor helpers.
  - `admin/` - CrewAI router that dispatches to the right child over A2A.
  - `children/text2sql_crewai/` - CrewAI Text2SQL over seeded SQLite.
  - `children/langgraph_rag/` - LangGraph RAG over seeded policy/manual docs.
  - `children/google_adk_research/` - Google ADK DeepResearch agent.
  - `data/` - seeded SQLite DB and markdown documents.
  - `run_all.py` - starts all 4 services.
  - `chat_cli.py` - interactive terminal chat with the Admin agent over A2A.
  - `client_smoke.py` - end-to-end smoke test.

## Setup

1. Install dependencies:
   ```
   uv sync
   ```
2. Copy the env template and fill in your OpenRouter key + models:
   ```
   cp .env.example .env
   ```
3. Seed the demo SQLite DB (only needed once):
   ```
   python -m real_a2a.data.init_db
   ```

## Environment

Set in `.env` (see `.env.example`):

- `OPENROUTER_API_KEY` - required.
- `ADMIN_MODEL`, `TEXT2SQL_MODEL`, `RAG_MODEL`, `DEEPRESEARCH_MODEL` - any OpenRouter model id (e.g. `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`).
- Optional per-service host/port overrides.

Default ports (overridable via env): Admin `10001`, Text2SQL `9001`, RAG `9002`, DeepResearch `9003`.

## Run

Start all 4 services:

```
python -m real_a2a.run_all
```

Or start any service on its own for iteration:

```
python -m real_a2a.children.text2sql_crewai.server
python -m real_a2a.children.langgraph_rag.server
python -m real_a2a.children.google_adk_research.server
python -m real_a2a.admin.server
```

Interactive chat with the Admin agent (with services running):

```
python -m real_a2a.chat_cli
```

Smoke test (with services running):

```
python -m real_a2a.client_smoke
```

## Observability

Instrumented end-to-end with the [observent](https://github.com/anthropics/claude-code) Claude Code skill: every service's agent boundary (admin router + all three children, across CrewAI/LangGraph/Google ADK) emits OpenTelemetry traces — input/output capture, LLM spans (tokens, model, prompt/completion), and W3C trace-context propagation across the admin -> child A2A hops — fanned out to **Arize Phoenix** and **Langfuse**.

- `real_a2a/shared/observent_otel.py` - shared `TracerProvider` setup + framework instrumentation.
- `real_a2a/shared/observent_capture.py` - transport-agnostic AI-boundary capture + trace-context middleware.
- `docker-compose.observent-phoenix.yml` - local Phoenix stack. Langfuse self-hosts via its own upstream compose (see `.observent/plan.md`).

Env vars (see `.env`): `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_API_KEY`, `PHOENIX_PROJECT_NAME`, `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`.

Start the backends, then the app as usual:

```
docker compose -f docker-compose.observent-phoenix.yml up -d --wait
```

Phoenix UI: `http://localhost:6006` · Langfuse UI: `http://localhost:3000`.

Full spec/plan/task history lives in `.observent/`; known gaps found while wiring this up are tracked in `feedback.md`, `feedback-crewai-llm-span.md`, and `feedback-google-adk-provider.md`.
