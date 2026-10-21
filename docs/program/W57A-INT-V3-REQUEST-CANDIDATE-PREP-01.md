# W57A-INT-V3-REQUEST-CANDIDATE-PREP-01 — unserved v3 request candidate

**Base:** published `origin/dev=4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`. **Status:** isolated pure source candidate; no runtime wiring, model call, registry entry, remote publication or beta claim.

The new builder checks supplied retrieval-set bytes and expected set/map/snapshot identities with the existing strict parser, binds the exact PDF version, then composes the existing draft v3 prompt and response schema. It returns only provider-facing system/user/schema material, identity fields and a deterministic local request digest. Full rebinding paragraphs are never returned or included in the prompt. A change to an unselected paragraph still changes the digest through the set SHA. The digest does not confer Run authority or replace the later provider request fingerprint.

## Checks

- Focused v3 request, renderer and set-input tests: **28 passed**.
- Program governance: **16 passed**.
- `py_compile`, `git diff --check` and frozen contracts/migration/source SHA-256: passed.
- Clean-tree technical handoff: generated after the local commit.
- Tests check selected-only provider material, exact v3 schema, absence of model/cap fields, stable request digest, digest change on PDF or hidden set data, and refusal for foreign version/set/map/snapshot/OCR.

## Integration

Cherry-pick this bounded commit after dev43. A later W57a PROFILE owner must prove Run/Attempt and Blob custody, use the qualified set and reviewed map, review/seal prompt bytes, enforce G-11 and CAP-01, and parse the same set locally for citation grounding before any provider call or publication. This candidate contains no model result and cannot become a canonical finding.

Changed paths are exactly this report, its formal task, the additive request builder and its offline tests. `contracts/**`, migrations, root dependencies, v1/v2 production, norms context, API/UI, composition root, `CURRENT_STATE.md` and remote refs remain untouched.
