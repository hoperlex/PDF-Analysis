# Task CFB-INT-DEV-PUBLISH-27 — integrate W56b OCR-region candidate

task_id: CFB-INT-DEV-PUBLISH-27

## Outcome

A clean fast-forward `origin/dev` candidate carries the pure unserved W56b
selector that binds an exact marked OCR quote to a verified portal region
for an explicitly textless page. It also corrects the stale recognised-input
guard to the already frozen optional W56a context rule. No finding or
citation is published.

## Depends on

- `CFB-INT-DEV-PUBLISH-26` — complete at
  `4efd756c67b5160aeca3dbc58903f72df6c93636`;
- `W56B-INT-RECOGNISED-REGION-PREP-01` — complete at
  `e770cb0fed2e6522ccc01a7d6e57575ab89b1de4`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `4efd756c67b5160aeca3dbc58903f72df6c93636`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- source parent `3d131d2966e0efeea7b53d9662785f253165a9a4`,
  source commit `e770cb0fed2e6522ccc01a7d6e57575ab89b1de4`;
- source four-path additive diff, 21 new plus 65 adjacent tests, no services;
- `test_recognised_never_reaches_analysis.py` still asserted that no stage
  reads `prepared.recognised_text`, while the completed W56a registry already
  declares it optional marked context for `text_analysis` and prohibits it
  as a quotation source; this stale guard fails on the dev26 base;
- current API 48 paths / 55 operations / 131 schemas, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage registry SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`,
  error catalogue SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`,
  migration head `0023_norm_citations`;
- R-135 defers complete beta gate; W55b main release gate is separate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: source is a completed four-path additive patch from dev25; dev26
  changed API/stage but did not touch the recognised module directory.

### P-01 — source path scope

- captured_at: 2026-10-16
- command: `git show --format= --name-only e770cb0fed2e6522ccc01a7d6e57575ab89b1de4`
- captured_output:
  ```text
  docs/program/W56B-INT-RECOGNISED-REGION-PREP-01.md
  docs/program/tasks/W56B-INT-RECOGNISED-REGION-PREP-01.md
  src/auditmanager/analysis/recognised/region_candidate.py
  tests/integration/analysis/recognised/test_region_candidate.py
  ```
- interpretation: accept the exact source without modifying contract or
  existing OCR/portal producers.

### P-02 — stale recognised-input guard

- captured_at: 2026-10-16
- command: `PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/integration/analysis/recognised tests/contract/program -p no:cacheprovider --tb=short`
- captured_output:
  ```text
  AssertionError: assert 'prepared.recognised_text' not in readers
  1 failed, 190 passed, 22 errors (DB-backed files: DATABASE_URL unset)
  ```
- interpretation: update only the guard's expected optional-context
  relation; preserve its prohibition on direct text-prompt package imports
  and on using OCR as a PDF quote.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-RECOGNISED-REGION-PREP-01.md`;
- `docs/program/tasks/W56B-INT-RECOGNISED-REGION-PREP-01.md`;
- `src/auditmanager/analysis/recognised/region_candidate.py`;
- `tests/integration/analysis/recognised/test_region_candidate.py`;
- `tests/integration/analysis/recognised/test_recognised_never_reaches_analysis.py`
  (integration-owned stale guard assertion only);
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-27.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-27.md`;
- `docs/program/CURRENT_STATE.md`;
- ignored `.venv` link to the existing Python environment for focused tests.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root dependencies
and locks, composition root, existing producer/consumer files, global
styles, production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No OCR finding, PDF text-layer claim, served profile, provider request,
Blob custody proof, corpus publication, W55b deployment or beta acceptance.

## Deliverables

Exact four-path source payload, bounded current-state update, this
task/report and direct published-dev SHA readback.

## Required tests

- source 21 new and 65 adjacent tests; integrated container-free recognised
  tests and programme governance, including the corrected guard, direct
  task governance;
- exact patch/path and frozen contract checks, whitespace, clean-tree,
  fresh remote fast-forward and post-push readback;
- complete W56–W63 beta gate deferred by R-135; W55b gate separate.

## Integration contract

Cherry-pick exact source commit after dev26. The selector may be consumed
only after later same-run checksum-verified Blob custody and an approved OCR
citation policy; it carries `quote_source=recognised`, not a PDF text-layer
offset. A moved ref or changed source stops publication; never force-push.

## Failure/idempotency/security cases

Cross-version, duplicate/ambiguous quote, image-description, wrong-page,
untrusted geometry or missing textless-page evidence refuses. Repeated
valid input yields the same immutable candidate and no external write.

## Rollback / feature flag

No served behavior is wired. Revert the four source paths and these three
integration documents through a reviewed forward commit if abandoned.

## Handoff

- source files: exact four W56b task paths, plus one integration-owned stale
  guard test correction;
- integration files: this task, report and bounded state update;
- contracts: none; OCR citation activation waits for its separate seal;
- forbidden hotspots and `origin/main` remain untouched.
