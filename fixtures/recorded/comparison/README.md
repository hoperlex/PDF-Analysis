# Synthetic recordings of the comparison summary (`COMPARE-PERSISTED-SUMMARY-01`)

**Every file here is synthetic.** The reply was authored by hand to prove that the summary command replays
a recording keyed by the digest of the exact request, with no model and no network. It is not field evidence
for anything, and every statement opens with «Синтетический ответ, не результат вызова модели».

| Path | What it is |
| --- | --- |
| `<request_sha256>.json` | the one recording, for the request the command makes over the synthetic pair of `build_fixtures.py` |
| `build_fixtures.py` | rebuilds it (`PYTHONPATH=src .venv/bin/python fixtures/recorded/comparison/build_fixtures.py`); `--check` reports drift |

`auditmanager.comparison.summary_model.RecordedSummaryModel()` reads this directory. The file name is the
SHA-256 of the canonical JSON of the exact request body: the prompt text and version, the response schema and
the bounded input (the changed lines of the approved pairs, each under its span identity, with the input's own
digest and the seal of the raw evidence). A different input or prompt is a different key, a missing file is
the refusal `recording_missing`, and nothing here can be turned into a live call.
