# BLOCK4-SPEC-1030

Unverified source-only candidate. No execution or checks were performed in this owner-authorised block.

## Behavior

Fresh whole-specification extraction uses `spec-batches-v1` / `cmp-whole-spec/batched-1`. The whole prepared source is no longer refused merely because it exceeds140k characters. It is divided into real, globally numbered source-line ownership slices, at most80 owned lines /60k owned characters, with actual neighbouring lines, repeated table headers and preceding section context. Context is bounded to12 neighbouring lines /8k characters per direction and a few genuine section lines. The actual rendered prompt is at most140k characters. Maximum512 batches per side. An oversized individual line, excessive batch count or oversized context is refused explicitly without cutting a prefix.

Every slice has a stable digest-bound batch ID, source SHA, actual pages and disjoint owned/context line IDs. All context comes from the same original prepared source. No OCR, new source content or guessed table headings are created. The model continues to copy nine fields verbatim, with exact quotes and global line evidence. The existing extraction checker validates the entire assigned packet.

The immutable existing extraction table stores raw paid responses under separate custody keys, checked batch results and the final aggregate. Raw responses are persisted before parsing or overrun handling; their request/prompt/response hashes and actual model-call IDs are retained. A stored paid result is rechecked or reused, never requested again under the same input. A journal fence defers in-flight work and refuses unknown effects or paid requests without response custody. The caller-to-custody crash/cancel gap therefore refuses a paid resend instead of silently retrying it.

Rows are aggregated by actual global evidence-line ownership. Identical fields at different real source rows retain their multiplicity. Repeated context evidence for the same actual owner is combined; conflicting values or one data line assigned to multiple positions make the whole side incomplete. The full original checker still gates field/quantity/source correctness. An incomplete side publishes no added/removed/no-change conclusion, and retains valid candidates and immutable batch answers for inspection. A failed batch stops further paid extraction of that side; unrequested tails remain explicit, and an incomplete old side does not cause an unnecessary paid new-side extraction.

## Consent, progress and reuse

The estimate enumerates every actually missing batch and reserves the actual32,000-token output ceiling used by each request. Stored raw/checked batches consume no new call estimate. New queued work pins the plan revision and both actual aggregate source keys in its payload and existing comparison coverage JSON. A legacy or changed-input resumed authority refuses before new dispatch; it never inherits hundreds of calls from an earlier one-request consent.

With zero missing model calls, `units` counts actual pending side aggregates or one pending transition assembly. `can_run_without_model` is true only after this real cached plan is known. The root-owned shared zero-call opt-in allows the free work without a fictional model call. A new transition with two reused whole inputs can assemble/compare them; a fully completed transition has zero pending units. Existing route/consent/ceiling rules remain in force, including the shared10USD/job limit.

Existing public coverage counters keep their meanings: original source blocks covered, real table rows and unresolved source rows. Exact batch counts, ownership/context lines, source hashes, issues, candidate positions and paid provenance remain in existing internal extraction/comparison coverage JSON. The frozen public DTO is not reinterpreted or extended. Existing source text, original units and deterministic evidence are preserved.

## Approved unit identity

A comparison-local helper implements only the owner's1:1 linear-metre aliases `м`, `п.м`, `пм`, `погм`, `мп` (including their dot/space spellings). Both the deterministic specification diff and whole-spec matching use it. Original displayed units and source lines remain unchanged. Other unit matching retains its former semantics; there is no kg/t/mm conversion or quantity rescaling. Fresh aggregate metadata binds `whole-spec-batched-v1-linear-metre1`. Existing persisted comparisons are not silently rewritten; they need a new authorised run to recompute derived results.

## Changed paths

- `src/auditmanager/comparison/specification/batches.py` (new).
- `src/auditmanager/comparison/specification/units.py` (new).
- `src/auditmanager/comparison/specification/source.py`.
- `src/auditmanager/comparison/specification/prompt.py`.
- `src/auditmanager/comparison/specification/transition.py`.
- `src/auditmanager/comparison/specification/method.py`.
- `src/auditmanager/comparison/specification/repository.py`.
- `src/auditmanager/comparison/specification/whole.py`.
- `src/auditmanager/comparison/specification/diff.py`.
- This report.

## Integration and limits

API1.14.0 and migration0043 remain unchanged. Root owns the shared zero-call service/UI integration, Git and dev publication. No other lane files, contracts, DDL, root dependencies/locks, composition root, global styles, tests or fixtures were edited. No Git writes were performed.

No tests, imports/compile, lint/typecheck/build, browser, DB/worker/provider/model execution or synthetic data generation was performed. The code is unverified; no PASS/quality/acceptance claim is made. Very long logical continuations can exceed the bounded neighbouring context; evidence conflicts then explicitly prevent a complete result. The original source/profile/row/request/output, shared spend and Attempt resource limits still apply. Raw reply custody retains paid data, while an uncovered crash gap or unknown provider outcome requires reconciliation. Roll back through a fresh prompt/policy boundary or forward revert; retain all existing paid replies and artifacts.
