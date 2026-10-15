# Task W57B-INT-CATALOGUE-SLUG-AUDIT-01 — audit source designation coverage

task_id: W57B-INT-CATALOGUE-SLUG-AUDIT-01

## Outcome

The W57b pure parser recognizes the corpus's ГОСТ IEC/ISO and ГОСТ Р
ИСО/МЭК designation forms, and a digest-pinned audit reports exactly which
local manifest slugs remain unparsed for owner review. The source manifest
and document bytes remain unchanged.

## Depends on

- `W57B-INT-REFERENCE-RESOLUTION-PREP-01` — completed pure parser and resolver on `origin/dev`.

## Frozen inputs

- base commit and `origin/dev`: `129168691f692fd24e38565b87fc27117f5384cc`;
- source manifest SHA-256 `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §B3.2;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: src/auditmanager/norms/references/families.json
- enumerator_owner: W57B-INT-CATALOGUE-SLUG-AUDIT-01
- totality_query: scan all 674 manifest slugs with the exact parser; each is parsed or appears once in the 57-row local candidate, and 617 + 57 = 674

## Captured premise evidence

- premise: the current parser leaves common standard subfamilies unparsed in the local 674-document manifest.

### P-01 — exact base and designation coverage

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && sha256sum /root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json`
- captured_output:
  ```text
  129168691f692fd24e38565b87fc27117f5384cc
  129168691f692fd24e38565b87fc27117f5384cc
  160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b  /root/projects/PDF-Analysis/.local/norms/corpus/MANIFEST.json
  ```
- interpretation: the unchanged manifest can be audited read-only; a baseline scan found 588 parsed and 86 unparsed slugs, including 29 ГОСТ composites.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/references/families.py`
- `src/auditmanager/norms/references/resolution.py`
- `src/auditmanager/norms/references/families.json`
- `tests/integration/norms/references/test_reference_resolution.py`
- `docs/program/tasks/W57B-INT-CATALOGUE-SLUG-AUDIT-01.md`
- `docs/program/W57B-INT-CATALOGUE-SLUG-AUDIT-01.md`
- `docs/program/CURRENT_STATE.md`
- `/root/projects/PDF-Analysis/.local/norms/reference-unparsed-candidate.json` (ignored local candidate only)

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing search/retrieval modules,
corpus source bytes and manifest, promotion DB, embeddings, verified custody,
runtime/API, root dependency/lock files, composition root, global styles,
stand, tags and `origin/main`.

## Non-goals

No claim that local slugs equal a future promoted catalogue, no legal edition
decision, no owner-reviewed exception list, source checksum sweep, heavy W54
operation, paid call, full gate or beta acceptance.

## Deliverables

Improved family parser/extractor, focused tests, digest-pinned local exception
candidate, source-coverage report and updated current state.

## Required tests

- focused W57b references tests;
- repeat the 674-slug audit and check candidate-list digest;
- compilation, task governance, frozen hashes, exact allowed-path and
  whitespace checks;
- no full `make gate` under R-135.

## Integration contract

The later W57b owner reviews the 57 remaining exceptions against the actual
promoted catalogue and either extends a named family or approves each
unparsed slug. The ignored candidate is a local input for that review, never
a runtime allowlist. The parser's new composite family keys must keep IEC,
ISO, ИСО and МЭК distinct from ordinary numeric ГОСТ series.

## Failure/idempotency/security cases

If the manifest digest moves, do not carry its exception list forward.
Ambiguous family labels are left unparsed rather than guessed. A repeated
scan of the same manifest yields the same sorted candidate bytes and digest.
No corpus document content or credential enters Git.

## Rollback / feature flag

Revert the additive parser refinement before runtime activation. The ignored
candidate can be deleted; no database rollback or flag is needed.
