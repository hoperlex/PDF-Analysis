# W56A-INT-AR-V2-RECORDED-REQUEST-01 — offline request builder

The new pure builder resolves the pinned AR v2 descriptor before it renders
anything, then creates the existing `ModelRequest` body from the reviewed
system prompt/schema, exact PDF text layer, marked OCR context and explicit
generation settings. Its checksum is the adapter's canonical SHA-256 of the
entire body. No v1 bundle settings or provider lock are silently inherited.

`fixture/...` is an **offline-only model namespace** for keyed recorded
responses. It is not a verified gateway model, tariff or configuration value
for a live call. The exact fixture ID and generation settings must be supplied
by the caller; the active executor is still v1. The caller must separately
select OCR from the version's stored `textless_pages`; this builder validates
the selected context against the text layer, but has no version-row access.

## Checks

- Focused pytest: **21 passed** for this module; **38 passed** with the
  existing registered-profile, prompt-material and response-pipeline tests.
  Checks cover stable body/key, changed PDF,
  OCR, model and parameters; prompt/schema fields in the checksum; profile
  and material tamper refusal; malformed text/OCR; and an offline keyed
  `RecordedAdapter` replay through `finish_response`. Altered PDF text looks
  for a different key and gets `recording_missing`.
- Python compilation, direct task governance (`[]`), all six frozen hashes,
  whitespace and exact owned-path check passed on this lane's four new paths.
  The integrator rechecks the combined candidate.
- No PostgreSQL, provider call, full `make gate` or beta acceptance was run.
  R-135 defers the full gate.

## Integration boundary

Changed paths are the additive `recorded_request.py`, its focused test, this
report and its task file. No contract, migration, provider lock, existing
runtime or adapter module, recording, corpus, root dependency/lock,
composition root, global style, `CURRENT_STATE.md`, Git ref or tag changed.
The next owner must bind a durable request checksum and recorded adapter
provenance to the run before an active AR v2 stage can consume this builder.
The current `RecordedAdapter` checks a recording's request SHA but does not
compare its `model_id` field with the request. Active wiring needs that
provenance check in an owned adapter/runtime task; this pure builder alone
does not authenticate a recording's model claim.
Rollback before runtime wiring is removal of the additive module.
