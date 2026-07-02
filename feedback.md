# observent skill — feedback from a real run

Context: multi-service monorepo (`a2a_barebone`), 4 A2A services on 3 frameworks
(CrewAI x2, LangGraph, Google ADK), backends Phoenix + Langfuse, package manager `uv`.
Session ran the full Spec → Plan → Tasks → Implement lifecycle by hand (no `/observent`
slash command available in this environment — the skill body was invoked directly).
Notes below are gaps/rough edges hit along the way, roughly in order of severity.

## 1. Pinned "Verified Versions" caused a silent, hazardous dependency downgrade

`matrix.md § Verified Versions` pins `opentelemetry-sdk==1.41.1` and
`openinference-instrumentation-crewai==1.1.6`. Running the generated
`pip_install` line verbatim via `uv add ...==1.41.1 ...==1.1.6` **downgraded the
project's already-installed `crewai` from 1.15.1 to 1.6.1** (9 minor versions) —
because current `crewai` depends on `opentelemetry-api>=1.42.1`, which conflicts
with the stale exact pin, so the resolver silently picked an old `crewai` that
still satisfied `pyproject.toml`'s loose `crewai>=0.80.0` constraint instead of
surfacing a conflict error.

This is dangerous specifically because it's silent — `uv add` exits 0, the
uninstall/reinstall log is easy to miss, and the app still imports and runs
(just on a much older, less-patched framework version). Someone following the
skill's task list mechanically (not eyeballing the diff of `uv add`'s output)
would ship this regression without noticing.

**Suggestion:** for any project with an existing lockfile (`uv.lock`,
`poetry.lock`, `Pipfile.lock`), don't emit hard `==` pins from the matrix table
for packages that share a dependency graph with something already installed
(here: `opentelemetry-*` and `openinference-instrumentation-crewai` both touch
`crewai`'s own `opentelemetry-api` floor). Either (a) install unpinned and let
the project's resolver pick, or (b) resolve first (`uv add --dry-run` /
equivalent) and diff the *full* resolution against current versions before
presenting the `pip_install` line in the Phase 3 confirm — if anything outside
the newly-added packages would change version, surface that explicitly and ask.
The Phase 3 confirm task already renders a diff preview for files; it should do
the same for the dependency resolution, not just list the install command as a
string.

## 2. `validate_setup.py`'s Langfuse check has no OTLP-fanout-aware branch

`check_phoenix` in `validate_setup.py` has a `fanout: bool` parameter and treats
a missing `arize-phoenix` package as `[INFO]`, not `[FAIL]`, because
`matrix.md § Arize Phoenix` explicitly documents the manual-`TracerProvider`
multi-backend path as not needing that package.

`check_langfuse` has no equivalent branch — it always does
`if not _is_installed("langfuse"): r.fail(...)`, even though
`matrix.md § Langfuse` documents the exact same thing for Langfuse's OTLP path:
*"The `langfuse` PyPI package is not required for the OTLP path... install it
only if you also want to use the `langfuse` SDK directly."* This is the same
documented exception Phoenix already gets, just not implemented for Langfuse
(and, by extension, probably SigNoz/Opik/Jaeger/LangSmith too — I didn't test
those, but they have the identical "no SDK required for OTLP" language in
`matrix.md`).

Net effect: I had to `uv add langfuse` (a package the generated code never
imports) purely to make the validator stop failing. That's dead weight in the
lockfile for no functional reason.

**Suggestion:** give `check_langfuse` (and the other OTLP-only backends) the
same `fanout`-aware treatment as `check_phoenix`, driven by whether the
generated `observent_otel.py` actually imports the vendor SDK or uses a raw
`OTLPSpanExporter`.

## 3. `validate_setup.py` doesn't load `.env`

It reads `os.environ` directly (e.g. `os.environ.get("LANGFUSE_HOST", ...)`),
so running it standalone (`python validate_setup.py phoenix,langfuse`) without
first exporting the project's `.env` reports the wrong host (cloud default
instead of the actual `http://localhost:3000` configured in `.env`) and could
plausibly misreport reachability for anyone who runs the validator the "obvious"
way instead of through the app's own dotenv-loading entry point.

**Suggestion:** either have the script `try: from dotenv import load_dotenv;
load_dotenv()` at startup (optional dependency, skip silently if `python-dotenv`
isn't installed), or explicitly document in its `--help` / SKILL.md Phase 4
that the caller is responsible for sourcing `.env` first.

## 4. Schema's `choice.framework` (singular) doesn't fit multi-service monorepos

`spec_schema.md § 1` models exactly one framework per spec
(`choice.framework: langgraph`). This app has three frameworks across four
independent service processes in one repo — a legitimate and probably common
shape for "multi-agent app," not an edge case. I worked around it by picking one
representative value (`crewai`) and writing the real per-service breakdown into
the free-form prose body, but:

- Phase 1 § 1.2's framework-resolution flow ("if multiple detected, ask which
  one to instrument") implicitly assumes you're choosing *one to instrument*,
  not *instrumenting all of them per-service*. I had to deviate from the
  documented flow (asked "all three vs. just one," user picked "all three") —
  worked fine, but it's not what the skill body describes as the option space.
- Nothing downstream (`matrix.md § Per-Framework Reference`,
  `capture.md § Per-framework wrap points`) has a per-service instantiation
  point in the schema — I had to design the four wrap points myself from the
  single-framework guidance.

**Suggestion:** support `choice.services: [{name, framework, entry_point}, ...]`
as an alternative to the singular `choice.framework`, with Phase 1 § 1.2
detecting "multiple frameworks *and* multiple plausible entry points (multiple
`server.py`/`main.py`-shaped files under different subpackages)" as the signal
to offer the multi-service path instead of "pick one."

## 5. `observent_capture.py`'s identity literals assume one framework per file

`_SERVICE_NAME` / `_AGENT_NAME` / `_AGENT_ROLE` / `_FRAMEWORK` are documented as
"generation-time literals" — fine for a single-service app, but this repo shares
one `observent_capture.py` across four processes on three frameworks. The
canonical `open_or_enrich_span(inputs, *, name=None, agent_name=None,
agent_role=None)` signature has no `agent_framework` parameter, so there was no
documented way to set `agent.framework` correctly per-call — only the one global
`_FRAMEWORK` literal, which can't be right for more than one framework at a
time.

I extended `_set_agent_identity` and `open_or_enrich_span` with an
`agent_framework` parameter (defaults to `None`, falls back to `_FRAMEWORK`) to
fix this — a small, backward-compatible change. This seems like a genuine gap
rather than a "just don't share the file" situation, since sharing one capture
engine across services in a monorepo is exactly the multi-agent case observent
is for.

**Suggestion:** add `agent_framework` as a first-class parameter to
`open_or_enrich_span` / `_set_agent_identity` in the canonical `capture.md`
engine, matching `agent_name` / `agent_role`.

## 6. Self-host readiness guidance is uneven across backends

`self_host.md` documents SigNoz's opamp settle delay in detail (~2 min after
`--wait` reports healthy, with a specific retry/backoff recommendation for
`validate_setup.py`). Langfuse's first-boot (image pull + Postgres/ClickHouse
migrations + Next.js compile) also took several minutes after `docker compose
... up -d --wait` returned — `langfuse-web` has no `healthcheck:` in the
upstream compose (so `--wait` can't block on it) and doesn't accept connections
until well after the containers report "Up." I ended up polling manually for
~10 minutes before the health endpoint responded. This isn't called out
anywhere for Langfuse specifically, so the Phase 4 §4.3 "next step: refresh each
UI" summary would be misleading if said right after `up --wait` returns.

**Suggestion:** add a Langfuse-specific readiness note (analogous to SigNoz's)
to `self_host.md`, and have the `validate` task's TCP/HTTP check retry with
backoff for any backend whose compose file lacks a `healthcheck:` on its
user-facing service, not just SigNoz.

## 7. `pip_install` field/vocabulary is pip-specific; project used `uv`

`spec_schema.md § plan.md` and the Phase 3 task table hard-code the field name
`pip_install` and phrase the canonical task payload as a literal `pip install
...` string. This repo manages dependencies with `uv` (has a `uv.lock`, no
`requirements.txt`). I substituted `uv add` myself, which was the obviously
correct call once I saw the lockfile, but the schema doesn't mention detecting
or branching on the package manager at all — someone following the docs
literally would run `pip install` into a `uv`-managed venv, which works but
doesn't update `uv.lock` / `pyproject.toml`, silently drifting the two out of
sync.

**Suggestion:** have `detect_framework.py` report the detected package manager
(presence of `uv.lock` → uv, `poetry.lock` → poetry, else pip/`requirements.txt`)
and have Phase 2 § 2.1 generate the install command in that manager's syntax.

## 8. `existing_setup_decision` enum doesn't cover "scaffolded but never implemented"

This repo's `.env` already had `PHOENIX_*` / `SIGNOZ_*` variable *names* (blank
values) from an earlier, incomplete observent attempt — no `.observent/`
artifacts, no instrumentation code. `spec_schema.md`'s
`existing_setup_decision: extend | replace | abort | none` doesn't have a clean
fit: it's not "extend" (nothing to extend — no code), not really "replace" in
the sense of overwriting a working setup (there was no working setup, just env
var names), and not "none" (`existing_setup.py` did detect something). I picked
`replace` and explained the nuance in `spec.md`'s prose, which worked, but the
enum forced an approximation.

**Suggestion:** either add a fifth state (e.g. `scaffold_only` — env vars/config
exist but no instrumentation code was ever generated) or have
`existing_setup.py` distinguish this case in its own output (e.g. an
`instrumentation_code_found: bool` alongside the existing `kind: backend`
detection) so Phase 1 § 1.4's prompt can name it explicitly instead of forcing
extend/replace/abort.

---

## 9. `CrewAIInstrumentor().instrument(...)` needs `use_event_listener=True` for LLM spans — undocumented, and off by default

Found post-implementation: the generated `observent_otel.py` called
`CrewAIInstrumentor().instrument(tracer_provider=provider)` (no extra kwargs),
following `matrix.md § CrewAI`'s instructions exactly ("Phoenix / SigNoz:
`pip install ... 'openinference-instrumentation-crewai==1.1.6' ...` — captures
Crew → Agent → Task → LLM hierarchy"). In practice, **zero LLM-level spans were
ever produced** — Phoenix only ever showed Crew/Task/Agent/Flow/Tool spans,
never an `llm` span kind with model name / token counts / prompt-completion
messages, no matter how many requests were sent.

Root cause (found by reading `openinference-instrumentation-crewai==1.1.10`'s
source directly, since nothing in `matrix.md` or `examples.md` mentions this):
`CrewAIInstrumentor._instrument()` has two completely different code paths
gated on a kwarg:

- **`use_event_listener=False` (the default)** — wraps `Crew.kickoff`,
  `Task._execute_core`, `Agent.kickoff`, `Flow.kickoff`/`kickoff_async`,
  `BaseTool.run`, and the memory save/search methods via `wrap_function_wrapper`.
  **There is no LLM-call wrapper anywhere in this path.** It cannot produce an
  LLM span, structurally, regardless of which CrewAI LLM class is used
  (`crewai.LLM`, LangChain's `ChatOpenAI`, anything).
- **`use_event_listener=True`** — instantiates an `OpenInferenceEventListener`
  that subscribes to CrewAI's internal event bus, including
  `LLMCallStartedEvent` / `LLMCallCompletedEvent` / `LLMCallFailedEvent` (plus a
  full superset of Crew/Task/Agent/LiteAgent/Tool/Flow/Method events — it
  replaces the wrapper-based hierarchy entirely, doesn't layer on top of it).
  **This is the only path that emits LLM spans**, because CrewAI 1.10+ fires LLM
  calls through its event bus rather than through a directly wrappable method.

This isn't a version-pin issue (unlike finding #1) — it reproduces on whatever
current `openinference-instrumentation-crewai` resolves to. It's a genuine
"the canonical setup snippet is incomplete" gap: `matrix.md § CrewAI` has no
"Canonical setup snippet" code block at all (every other framework/backend
section has one), so there was nothing to catch this against — the LangGraph
and Google ADK sections' snippets both work as documented; only CrewAI's
prose-only description silently omitted the flag that makes LLM tracing work.

Confirmed fixed by adding `use_event_listener=True`: re-ran a minimal
`Crew.kickoff()` afterward and Phoenix showed a proper `llm` span kind
(`nvidia/nemotron-3-ultra-550b-a55b:free.llm_call`, `openinference.span.kind:
LLM`, `llm.token_count: {prompt, completion, total}`, full input/output
messages) for the first time all session.

**Suggestion:** add a "Canonical setup snippet" to `matrix.md § CrewAI` like
every other section has, and make sure it includes
`CrewAIInstrumentor().instrument(tracer_provider=provider,
use_event_listener=True)` — or, better, ship `use_event_listener=True` as the
instrumentor's own default upstream and only document the flag for people who
explicitly want the older wrapper-only behavior, since "silently drop all LLM
spans" is a surprising default for something billed as an *LLM observability*
instrumentor.

## What worked well (worth keeping, not gaps)

- `detect_framework.py` / `existing_setup.py` correctly identified all three
  frameworks, the dormant `a2a-sdk` auto-instrumentation, and the stale
  Phoenix/SigNoz env var scaffold in one pass — no manual digging needed.
- The enrich-vs-fallback span logic in `capture.md` (`open_or_enrich_span`) is
  well-designed and worked exactly as documented across all four services once
  the `agent_framework` gap above was patched locally.
- Phoenix's `4327` gRPC host-port remap (to avoid the SigNoz/Jaeger collision)
  worked with zero intervention needed.
- The `PHOENIX_PROJECT_NAME` → `openinference.project.name` resource-attribute
  fold for the manual multi-backend fan-out path (`matrix.md § Arize Phoenix`)
  is exactly right and non-obvious enough that having it spelled out saved real
  debugging time — traces landed in the correct named project on the first try.
- End-to-end live verification (real request through the instrumented
  text2sql service) confirmed spans actually reached Phoenix (23 traces in the
  `a2a` project), including on the error path (`set_error` + re-raise) when the
  underlying OpenRouter call hit a rate limit.
