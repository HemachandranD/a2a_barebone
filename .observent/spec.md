---
schema_version: 1
created_at: 2026-07-02T08:27:09Z
updated_at: 2026-07-02T08:27:09Z
status: locked
detection:
  frameworks_detected: [langgraph, crewai, google-adk]
  backends_installed: [opentelemetry]
  web_frameworks: [starlette]
  existing_setup:
    - {name: phoenix, kind: backend, imports: [], env_vars_in_files: [".env"], env_files: [".env"]}
    - {name: signoz, kind: backend, imports: [], env_vars_in_files: [".env"], env_files: [".env"]}
  docker_available: true
  docker_compose_available: true
  backends_reachable:
    phoenix: false
    langfuse: false
  project_fingerprint: sha256:1cc1a4f4f28d49fa68f587a52c61cfa72ff102df182247bc7ff85bf5c027fd40
choice:
  framework: crewai   # NOTE: this is a multi-framework monorepo, see prose below — schema's single `framework` field doesn't fit; all three detected frameworks are instrumented.
  backends: [phoenix, langfuse]
  convention: both
  existing_setup_decision: replace
  endpoints:
    phoenix:  {mode: self-host, url: "http://localhost:6006/v1/traces"}
    langfuse: {mode: self-host, url: "http://localhost:3000/api/public/otel/v1/traces"}
  env_vars_required: [PHOENIX_API_KEY, PHOENIX_PROJECT_NAME, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST]
  http_body_capture: false
  http_transport_spans: none
  self_host_provision:
    phoenix: true
    langfuse: true
  auto_instrumenting_deps:
    a2a-sdk: disable
---

# Observability Spec

This is a **multi-service, multi-framework** A2A app, not a single agent:

| Service | Entry point | Framework |
|---|---|---|
| Admin router | `real_a2a/admin/server.py` | CrewAI (classifier) |
| Text2SQL | `real_a2a/children/text2sql_crewai/server.py` | CrewAI |
| RAG | `real_a2a/children/langgraph_rag/server.py` | LangGraph |
| DeepResearch | `real_a2a/children/google_adk_research/server.py` | Google ADK |

Each runs as its own OS process (spawned by `real_a2a/run_all.py`) and they call each
other over HTTP/JSON-RPC via `real_a2a/shared/a2a_client.py` (A2A protocol). All three
detected frameworks (LangGraph, CrewAI, Google ADK) are instrumented — user chose "all
three" over instrumenting a single service, since full observability here means seeing
every hop of the admin -> child call chain in one trace.

Backends: **Arize Phoenix** (local-first LLM trace UI) + **Langfuse** (token-cost
tracking, prompt versioning), fanned out from one manual `TracerProvider` per process
(convention: `both` — OpenInference + OTel-GenAI attributes on every span).

`.env` already had `PHOENIX_*` / `SIGNOZ_*` var names scaffolded from an earlier, never-
completed observent attempt. User chose to drop SigNoz for Langfuse instead
(`existing_setup_decision: replace`) — no instrumentation code existed yet, so this is a
clean slate on top of the existing env var names that survive (`PHOENIX_*`).

`a2a-sdk` ships its own dormant OTel instrumentation (`OTEL_INSTRUMENTATION_A2A_SDK_ENABLED`,
already `false` in `.env` from the earlier attempt) — kept disabled, since it would only add
A2A-protocol plumbing spans, not agent/LLM-level detail.

Neither Phoenix nor Langfuse is reachable locally yet; both get provisioned via Docker
(Phoenix: vendored single-container compose; Langfuse: upstream `git clone` + compose,
since its v3 stack is 6 coupled services with generated secrets).

HTTP transport spans: `none` — Phoenix and Langfuse are LLM-native backends with no use
for generic HTTP server/transport spans, and the JSON-RPC endpoints stream SSE chunks
that would otherwise spam a `http send` span per chunk. A context-only middleware still
propagates `traceparent` across the admin -> child hops so traces stay linked.
