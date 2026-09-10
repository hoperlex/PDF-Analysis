# Recorded `text_analysis` responses

`OD-13` makes automated suites recorded-only. Every test in
`tests/integration/analysis_text` and `tests/replay/text_analysis` runs against these
files and makes **zero network calls**; `tests/replay/text_analysis/conftest.py`
installs a socket guard that fails the suite if anything tries.

## Layout

| Path | What it is |
|---|---|
| `<request_sha256>.json` | the canonical recording, replayed by `RecordedAdapter()` with no arguments |
| `inputs/ar_baseline_text_layer.json` | a `prepared.text_layer` for `fixtures/synthetic/ar/ar_baseline.pdf` |
| `variants/<name>/<request_sha256>.json` | a second answer to the *same* request, reached by pointing an adapter at that directory |
| `build_fixtures.py` | rebuilds every file above |

`RecordedAdapter` only ever opens `<its directory>/<key>.json`, so `inputs/` and
`variants/` are invisible to the canonical adapter. Variants exist because a recording
is keyed by request checksum: the corpus, the bundle and the model are the same in
every case, so all four recordings share one key and cannot share one directory.

## The key

The file name is `sha256` of the canonical JSON of the exact request body — model,
`max_tokens`, system prompt, rendered document, `thinking` and `output_config`. It is
computed, never chosen. **Editing anything in `auditmanager.analysis.text.prompt`
changes every key here**, and the old recordings become unreachable: the adapter
reports `dependency_unavailable` rather than replaying an answer to a different
question. That coupling is deliberate. Re-run the builder after a prompt change.

## Adding or refreshing a recording

```
PYTHONPATH=src .venv/bin/python fixtures/recorded/text_analysis/build_fixtures.py
PYTHONPATH=src .venv/bin/python fixtures/recorded/text_analysis/build_fixtures.py --check
```

`--check` reports drift without writing, so a prompt edit that would orphan the
recordings is visible before the suite starts failing for a less obvious reason.

To capture a *live* response instead of an authored one, run the stage with
`AUDITMANAGER_PROVIDER_MODE=live` and an injected `ANTHROPIC_API_KEY`, then write the
returned `output_text`, `stop_reason` and `usage` through
`auditmanager.analysis.text.recorded.recording_document`. Do not hand-write the JSON:
that function is the only supported constructor, and it is what keeps the next point
true.

## A recording cannot claim to be live

There is **no `provider_mode` field in these files**, and `recording_document` has no
parameter that would add one. The mode written into a model call record and into
`analysis.text_observations` comes from the read-only class constant on the adapter
that produced the response, so editing a file here cannot make a replay present itself
as a live call. `assert_consistent_mode` then refuses to publish an artifact whose
declared mode disagrees with its own call records.

## Honesty note on the numbers

`usage.input_tokens`, `usage.output_tokens` and `latency_ms` in these recordings are
**authored, not measured** — no live call had been made when they were written. They
are plausible for this corpus at the rates `docs/program/P02_LOCK.json` pins, and the
cost meter charges them exactly as written. The first live run should replace them
with measured figures; the `over_budget` variant deliberately carries the usage of a
far larger document so the `OD-03` ceiling fires on measured cost.
