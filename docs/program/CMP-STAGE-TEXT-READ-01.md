# CMP-STAGE-TEXT-READ-01 — served immutable evidence reads

Task: [`CMP-STAGE-TEXT-READ-01`](tasks/CMP-STAGE-TEXT-READ-01.md). Base `ff0ba71bc86a1e17cff045d2b5304b22c8026e60` contains the worker-side evidence writer. The frozen `1.12.0` contract and `0041` migration stay unchanged.

## Implemented

- Four sealed GET operations now read stored fragments, exact exclusions, raw differences and nonbinding hints through `StageTextReadService`. Pair/revision identity is checked before rows, pagination uses stable content-key cursors, and a foreign or malformed cursor refuses. Fragment reads keep only ready profiles of the current document version; historical revision evidence remains readable by its explicit revision ID after a newer map revision appears.
- A known pair/revision without stored evidence returns a typed `comparison_stage_text_evidence` dependency refusal. An unknown pair/revision returns `not_found`, so absence does not silently become an empty page. The recomputation POST remains the sealed `comparison_stage_text` refusal. Module `none`/`versions` still refuses all five operations via `comparison_modules`.
- The composition root supplies the shared session factory to the adapter. SQL stays inside the comparison bounded context; the router only calls its port. No model or storage side effect occurs in a GET.

## Evidence

- Isolated PostgreSQL store/read plus real ASGI HTTP: **6 passed**. The tests cover unmaterialized, unknown parent, two-page fragment pagination, exact/difference/hint views, invalid cursor, historical revision and module-off/refused recompute. C3 composition registry: **67 passed**, including the four newly served GETs. Stage Text unit suite **17 passed** in the earlier pure slices; package compile and whitespace checks passed.
- No API contract or migration change, generated-client edit, root dependency/lock, global style, C2 runtime, C3 pair/link service or remote ref change.

## Remaining boundary

No durable recomputation command or worker currently calls the evidence writer from an API request. A completely textless result cannot yet be sealed, so its GETs correctly refuse rather than claim zero text. A future run step must pin profiles, store a complete batch or an explicit empty seal, and report staleness when the map/version changes. UI masks, text search and full `CMP-STAGE-TEXT-01` parity remain open.

## Integration instruction

Merge after the evidence writer. Keep the four GETs read-only and the recompute POST gated until it has a durable run. Use the explicit revision ID for historical evidence; the current stage screen must compare it with the current map revision before treating old rows as current.
