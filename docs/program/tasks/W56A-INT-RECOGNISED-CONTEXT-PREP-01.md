# Task W56A-INT-RECOGNISED-CONTEXT-PREP-01 — select marked OCR context for AR v2

## Outcome

A pure selector reads the W55b `prepared.recognised_text` artifact and the
version's frozen `textless_pages`. It returns only recognised TEXT entries
on those pages, retaining quality flags, and renders them as explicitly
uncitable context. Portal IMAGE descriptions never enter the prompt.

## Depends on

- `W55B-INT-CLOSE` — complete on `origin/dev`;
- `W56A-INT-SEAL-01` — complete on `origin/dev`;
- `W56A-INT-PROFILE-CONTENT-01` — complete at `d6d37e44`.

## Frozen inputs

- base `origin/dev=c6f8c254337b7d69d8fd7d3eef6b02ccd58e72ae`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; W56 §A3.4, R-134;
  `P02_SEAMS.md` §4.8 and W55b `DocumentVersion.textless_pages`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `contracts/analysis/v1/stage-registry.json` (read-only)
- enumerator_owner: `W56A-SEAL-01`
- totality_query: `tests/integration/analysis/test_ar_v2_recognised_context.py`

## Captured premise evidence

- premise: the W55b artifact distinguishes recognised TEXT from portal
  IMAGE descriptions and the version row records the textless pages; AR v2
  still has no pure selector for its marked prompt context.

### P-01 — committed selector absent

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/recognised_context.py`
- captured_output:
  ```text
  c6f8c254337b7d69d8fd7d3eef6b02ccd58e72ae
  c6f8c254337b7d69d8fd7d3eef6b02ccd58e72ae
  ```
- interpretation: the exact selector path is absent. Existing W55b
  artifact construction and version metadata are read-only inputs here.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recognised_context.py` (new);
- `tests/integration/analysis/test_ar_v2_recognised_context.py` (new);
- this task file, `docs/program/W56A-INT-RECOGNISED-CONTEXT-PREP-01.md` (new);
- `docs/program/CURRENT_STATE.md` (top development status only).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, W55b producer/ingest code,
existing application/run/text modules, provider, root dependencies/locks,
composition roots, global styles, `VERSION`, recordings, stand state,
`origin/main` and tags.

## Non-goals

No OCR generation, new quality-flag semantics, prompt-bundle activation,
budget mutation, quote grounding change, provider call, full local gate,
acceptance or beta claim.

## Deliverables

Pure selection/rendering with integrity refusals, focused tests including
image-description and textful-page exclusion, report and dev ref read-back.

## Required tests

Focused pytest for page selection, flags, missing/wrong artifact and hostile
delimiter text; module compilation, direct task governance, `git diff
--check`, exact changed-path proof. Do not run `make gate`.

## Integration contract

`W56A-PROFILES-01` may consume the returned context when assembling v2's
prompt, but only from the run version's stored `textless_pages`. It must
still account for recognised character count in its input budget and keep
grounding against the PDF text layer alone. A quote found only here is
ungrounded with `quote_in_recognised_text`, owned by that later lane.

## Failure/idempotency/security cases

An absent artifact for a bundle with textless pages, wrong version/role,
bad entry shape or unknown flag raises rather than silently dropping data.
Legacy versions without W55b counts and no artifact yield empty context.
Repeated selection is deterministic. Rendering JSON-quotes the untrusted
OCR text so delimiter-looking content stays data; it is never evidence.

## Rollback / feature flag

Revert the additive module before runtime wiring; no flag or DB rollback.
After wiring, correct forward under the profile owner.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: profile lane consumes this only under a fresh grant and retains
  the MODEL-PIN block for live activation.
