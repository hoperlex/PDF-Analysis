# CMP-STAGE-AI-CORE-01 — strict pure Stage AI methods

Task: [`CMP-STAGE-AI-CORE-01`](tasks/CMP-STAGE-AI-CORE-01.md). Base `9fa035029a3422b1c3e63d108fbe8c5fdde5dd8e`; frozen C3 API `1.12.0`, migration `0041`. This lane owns no shared runtime, API, migration or remote ref.

## Implemented

- Immutable fragment, preliminary-item, atomic-evidence and classified-card DTOs validate source identities, digests, side shapes and finite box anchors. Transport-neutral `CallPlan` binds phase, group/unit identity, canonical source SHA-256, prompt/schema content, pinned model and output budget into a content key. It exposes an `AiCallGroup` estimate for the existing C2 consent/spend caller without executing any provider operation.
- Reviewer requests contain at most 40 preliminary items. Items sharing a fragment are kept in one connected component, never split into separate calls; an over-40 component refuses. Each chunk carries its own digest and the full-group digest. Chunk parsing checks exact schema, digest, group/chunk identity, known IDs, side membership, status shape, profile membership and complete required-fragment coverage. `accept_review_group` validates every chunk and global coverage before returning any result.
- SAME/MOVED require high confidence. MOVED inside the accepted group becomes SAME; outside membership and unconfirmed recognised-text sameness become UNCERTAIN. A SAME touching a raw CHANGED item becomes UNCERTAIN. Unsupported numerical/identifier claims become safe UNCERTAIN text. The result retains every raw evidence ID; no function mutates a raw row or an input DTO.
- Classifier requests contain one source group. The validator enforces complete one-time evidence coverage, the original 18 categories, the three classes and the eleven systems agreed with the C4 seal. Deterministic class hints cannot be silently downgraded, uncertain evidence remains REVIEW, and unsupported titles refuse the whole group. Card keys bind class plus sorted evidence IDs; evidence digests bind their immutable source content keys.
- High-level synthesis rechecks card/evidence digests and exact evidence coverage. REAL_CHANGE cannot publish from one-sided, unchanged, REVIEW, uncertain-link or service-only evidence. Decision/type combinations are closed, titles/reasons are source-bound, and DETAIL_ONLY cannot claim a new object.
- JSON response parsing rejects duplicate keys, NaN, malformed UTF-8 and oversized bodies. Response schemas and Russian prompts are versioned in their method modules; no model names or provider transport are selected by the core.

## Public interface

`auditmanager.comparison.stage_ai` exports the DTOs, `CallPlan`, `StageAiValidationError`, `build_review_requests`, `parse_review_chunk`, `accept_review_group`, `build_classification_request`, `parse_classification`, `build_synthesis_request`, and `parse_synthesis`.

The C4 caller stores the plan's `content_key`, `source_sha256`, `unit_key` and prompt version before execution, obtains route/consent/spend authority from the shared C2 runtime, sends `request_document()` through that caller, then submits the received JSON to its matching parser. Only the validated result is eligible for immutable C4 answer storage. A model response never authorizes an expert verdict or changes raw evidence.

## Checks and scope proof

- `.venv/bin/pytest -q tests/unit/comparison/stage_ai`: **30 passed** in under two seconds. Cases cover bounded/connected chunking, whole-group atomicity, foreign/duplicate/missing IDs, digest mismatch, confidence and membership overrides, raw-evidence retention, closed vocabulary, classifier coverage/hints, unsupported numbers/marks, synthesis guards and stored-card digest revalidation.
- Package compile and `git diff --check` passed. Full gate and heavy windows are deferred under the owner's direct 2026-10-30 instruction.
- Changed code is entirely `src/auditmanager/comparison/stage_ai/**` and its owned unit tests, plus this report/task and the local `.venv` symlink. Contracts, migration head, composition, registry, root dependency/lock files, global styles, C2 runtime and raw Stage Text modules were not edited.

## Limits and integration instruction

This is a pure method core. The C4 runtime must supply persisted source IDs/content keys, enforce run authority and version pins, obtain consent, journal spend before each provider call, render/verify GRAPHIC crops where applicable and persist validated answers. The core checks references and lexical support, not the engineering truth of model interpretation. The independent C4 seal owner confirmed the system/category vocabularies and JSONB answer seams; no additional normalized column is required by this core.

Root remains the sole integrator. Merge this local branch before wiring the C4 Stage AI service; do not expose its methods as canonical expert decisions.
