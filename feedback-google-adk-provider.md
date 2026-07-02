# observent skill — feedback: Google ADK instrumentor hardcodes `llm.provider: "google"`

Context: same session as `feedback.md` (multi-service monorepo, `deepresearch`
child service on Google ADK, model routed through
`google.adk.models.lite_llm.LiteLlm` to OpenRouter — see
`real_a2a/shared/llm.py`'s `adk_model()`).

## Gap

`llm.provider` is **unconditionally hardcoded to `"google"`** for every LLM call
an ADK agent makes, regardless of which model backend is actually behind it.

Confirmed by reading the installed `openinference-instrumentation-google-adk`
source directly (`_wrappers.py`, class `_TraceCallLlm`, lines 252-255):

```python
span.set_attribute(
    SpanAttributes.LLM_PROVIDER,
    OpenInferenceLLMProviderValues.GOOGLE.value,
)  # TODO: other providers may also be possible
```

There is no branch, no inspection of the request/model string — every ADK LLM
span gets `llm.provider = "google"` unconditionally. The upstream author even
left a `# TODO: other providers may also be possible` comment acknowledging the
gap, so this isn't accidental — it's a known-incomplete implementation that
shipped anyway.

**What's still correct:** the real model name is captured properly a few lines
later (`span.set_attribute(SpanAttributes.LLM_MODEL_NAME, llm_request.model)`),
so `llm.model_name` shows the true `openrouter/<model>` (or `together/...`,
`groq/...`, etc.) string. Only the provider/system attribution is wrong — the
model identity itself is fine.

## Impact

Any ADK agent that routes through `google.adk.models.lite_llm.LiteLlm` to a
non-Google backend (OpenRouter, Together, Groq, Anthropic-via-LiteLLM, anything)
gets silently mis-attributed as a Google/Vertex call in every trace UI that
groups or filters by `llm.provider` / `gen_ai.system`. Concretely:

- Provider-based cost/usage dashboards would attribute spend to "Google" that
  never touched GCP.
- Filtering a trace UI by provider to isolate "which vendor is slow / erroring"
  silently merges unrelated backends into one bucket.
- Anyone auditing which LLM vendors an app actually calls (a real question for
  data-residency / vendor-risk reviews) gets a wrong answer from this attribute
  alone — they'd have to know to cross-check `llm.model_name` instead.

This is exactly the kind of thing that's invisible until someone asks "wait, why
does this say Google?" — which is what happened in this session — because the
span *looks* complete and correct in every other way (right model name, right
tokens, right input/output).

## Where this is (and isn't) already documented

`matrix.md § Google ADK` in the observent skill **does** already carry a
warning about this:

> ⚠️ Known instrumentor limitation — provider attribution is wrong for
> non-Gemini ADK agents... Don't trust `llm.provider` / `gen_ai.system` for
> LiteLLM-backed ADK agents — group by `llm.model_name` instead.

So the skill's reference docs are honest about the gap existing — good. But
two things are missing:

1. **It's not surfaced at generation time.** Nothing in `observent_otel.py`'s
   generated code, the Phase 1 spec confirmation, or the Phase 4 §4.3 summary
   flags this for a project that actually *is* running ADK-through-LiteLLM
   (which `detect_framework.py` could plausibly detect — the same signal that
   let it find `google-adk` as a declared dependency could also check whether
   `google.adk.models.lite_llm` is imported anywhere). A user has to already
   know to go read `matrix.md` prose to find this out; it never shows up as a
   proactive warning during setup for the exact case it applies to.
2. **It's upstream, not observent's to fix**, but observent could still close
   the gap on its own side: since `matrix.md` already tells you the "real"
   provider is knowable from the model string prefix (`openrouter/`,
   `together/`, `groq/`, ...), the generated `observent_otel.py` /
   `observent_capture.py` could optionally derive and stamp a corrective
   attribute (e.g. `llm.provider.corrected` or overwrite `llm.provider` after
   the ADK instrumentor runs, via a small span processor that post-processes
   ADK LLM spans) rather than leaving every downstream user to work around it
   by remembering "group by model_name instead."

## Suggestion

- Raise this upstream against `openinference-instrumentation-google-adk`
  (the `# TODO` comment suggests the maintainers already know) — replacing the
  hardcoded `GOOGLE` with a derivation from `llm_request.model`'s prefix
  (`openrouter/`, `together/`, `groq/`, bare model name → assume Google) would
  fix it at the source for every consumer, not just observent-generated code.
- Until that lands, have `detect_framework.py` check for
  `google.adk.models.lite_llm` usage specifically (not just `google-adk` as a
  dependency) and have Phase 1 surface the warning proactively as part of the
  spec confirmation for that project, instead of leaving it as prose in
  `matrix.md` that only self-selects for people who go looking.
- Consider a small "correct after the fact" `SpanProcessor` in the generated
  `observent_otel.py` for the specific case of ADK + LiteLLM, since observent
  already knows (from the user's framework-detection answers) when this
  combination is in play.
