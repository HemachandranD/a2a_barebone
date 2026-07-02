# observent skill — feedback: CrewAI instrumentor drops all LLM spans by default

Context: same session as `feedback.md` (multi-service monorepo, `text2sql` and
`admin` services on CrewAI, LLM routed through `crewai.LLM` to OpenRouter — see
`real_a2a/shared/llm.py`'s `crewai_llm()`).

## Gap

The generated `observent_otel.py` called
`CrewAIInstrumentor().instrument(tracer_provider=provider)` with no extra
kwargs, exactly as `matrix.md § CrewAI` describes it ("Phoenix / SigNoz:
`pip install ... 'openinference-instrumentation-crewai==1.1.6' ...` — captures
Crew → Agent → Task → LLM hierarchy"). In practice, **zero LLM-level spans were
ever produced** for any CrewAI service, for the entire session, no matter how
many requests were sent — only `Crew`/`Task`/`Agent`/`Flow`/`Tool` spans showed
up in Phoenix, never an `llm` span kind with model name, token counts, or
prompt/completion messages.

Root cause, found by reading `openinference-instrumentation-crewai==1.1.10`'s
source directly (nothing in `matrix.md` or `examples.md` mentions this):
`CrewAIInstrumentor._instrument()` has two structurally different code paths
gated on a kwarg:

- **`use_event_listener=False` (the default — what the generated code used)**
  — wraps `Crew.kickoff`, `Task._execute_core`, `Agent.kickoff`,
  `Flow.kickoff`/`kickoff_async`, `BaseTool.run`, and the memory save/search
  methods via `wrap_function_wrapper`. **There is no LLM-call wrapper anywhere
  in this path.** It cannot produce an LLM span, structurally, regardless of
  which LLM class CrewAI is configured with (`crewai.LLM`, LangChain's
  `ChatOpenAI`, anything) — the method that would need wrapping simply isn't
  wrapped.
- **`use_event_listener=True`** — instantiates an `OpenInferenceEventListener`
  that subscribes to CrewAI's internal event bus, including
  `LLMCallStartedEvent` / `LLMCallCompletedEvent` / `LLMCallFailedEvent` (plus a
  full superset of Crew/Task/Agent/LiteAgent/Tool/Flow/Method events — this
  mode *replaces* the wrapper-based hierarchy entirely, it doesn't layer on top
  of it). **This is the only path that emits LLM spans**, because CrewAI 1.10+
  fires LLM calls through its event bus rather than through a directly
  wrappable method.

This isn't a version-pin issue (unlike the `crewai` downgrade finding in
`feedback.md` #1) — it reproduces on whatever current
`openinference-instrumentation-crewai` resolves to, pinned or not.

## Impact

Every CrewAI-backed service in a multi-agent app instrumented by observent's
default generated code silently loses all LLM-level observability: no token
counts, no per-call model name, no prompt/completion messages, no per-call
latency — the single most important span kind for an *LLM* observability tool.
The Crew/Task/Agent spans still show up, so a trace superficially looks
"complete" (there's a waterfall, there are nested spans, nothing errors) —
which makes the gap easy to miss entirely unless someone goes looking
specifically for an `llm` span kind and doesn't find one. That's what happened
in this session: the miss wasn't caught until the user directly asked "why is
nothing being traced in CrewAI."

## Where this is (and isn't) already documented

`matrix.md § CrewAI` is the **only** framework section in the entire reference
that has no "Canonical setup snippet" code block — LangGraph, Microsoft Agent
Framework, Anthropic Agents SDK, OpenAI Agents SDK, smolagents, LlamaIndex, and
Google ADK all have one; CrewAI has prose only ("captures Crew → Agent → Task →
LLM hierarchy"). Every other framework's snippet is copy-pasteable and known to
work as documented (confirmed directly for LangGraph and Google ADK this
session); CrewAI's prose-only description is what let this slip through —
there was no runnable reference to diff the generated code against.

## Suggestion

- Add a "Canonical setup snippet" to `matrix.md § CrewAI`, matching the format
  every other framework section already has, and make sure it includes
  `CrewAIInstrumentor().instrument(tracer_provider=provider,
  use_event_listener=True)`.
- Better: raise upstream that `use_event_listener=True` should be the
  instrumentor's own default. "Silently drop every LLM span unless you pass an
  undiscoverable flag" is a surprising default for a package literally named
  `openinference-instrumentation-crewai` under an LLM-observability project —
  the failure mode is silent and looks like a complete trace, which is the
  worst kind of default for an observability tool to ship.
- Have `detect_framework.py` / Phase 2's plan generation include a
  post-generation self-check (or note in the Phase 4 §4.3 summary) along the
  lines of "run one request through each instrumented framework and confirm at
  least one `llm`-kind span was produced" — this specific class of bug (spans
  exist, but the *kind* that matters for the product's purpose is silently
  missing) wouldn't be caught by `validate_setup.py`'s current checks (env
  vars, package presence, endpoint reachability, synthetic span emission) since
  none of those assert anything about span *kind* coverage from a real
  framework call.
