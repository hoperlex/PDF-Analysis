# Task CFB-INT-DEV-PUBLISH-37 — integrate W54 CPU-window preflight

task_id: CFB-INT-DEV-PUBLISH-37

## Outcome

A clean fast-forward `origin/dev` candidate adds explicit 1-minute CPU-load
evidence and refusal to the offline W54 corpus preflight.

## Depends on

- `CFB-INT-DEV-PUBLISH-36` — complete at `cf9b64a0c99042cdfe207de776f0296d6857b930`;
- `W54-CORPUS-CPU-WINDOW-PREFLIGHT-01` — complete at `a0eff1a321878f4156636fa6640351c9e3c9539b`.

## Frozen inputs

- base commit: `cf9b64a0c99042cdfe207de776f0296d6857b930`
- source parent: the same exact base;
- source/integrated patch SHA-256 `0355182ded3faa993d63dbe07264ab37a39241696793389b6026d42b093798b8`;
- W54 plan SHA-256 `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- recorded W54 promotion on this eight-CPU host used load under 8, in addition
  to §3.9 disk/RAM floors and one heavy lane;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256 `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`; `VERSION=0.6.0`; R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source is a direct child of published dev36, changes four
  task-owned paths and can fast-forward without editing its payload.

### P-01 — exact source parent and patch

- captured_at: 2026-10-16
- command: `git show --format='%H %P' --name-only a0eff1a321878f4156636fa6640351c9e3c9539b; git show --format= --binary cb2194b7 | sha256sum`
- captured_output:
  ```text
  a0eff1a321878f4156636fa6640351c9e3c9539b cf9b64a0c99042cdfe207de776f0296d6857b930
  docs/program/W54-CORPUS-CPU-WINDOW-PREFLIGHT-01.md
  docs/program/tasks/W54-CORPUS-CPU-WINDOW-PREFLIGHT-01.md
  scripts/norms/corpus_preflight.py
  tests/integration/norms/test_corpus_preflight.py
  0355182ded3faa993d63dbe07264ab37a39241696793389b6026d42b093798b8  -
  ```
- interpretation: the integrated source patch matches the standalone source
  and adds no contract, migration or runtime consumer.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-CORPUS-CPU-WINDOW-PREFLIGHT-01.md`
- `docs/program/tasks/W54-CORPUS-CPU-WINDOW-PREFLIGHT-01.md`
- `scripts/norms/corpus_preflight.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-37.md`
- `docs/program/CFB-INT-DEV-PUBLISH-37.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

All other paths, especially contracts, migrations, root dependencies/locks,
composition root, global styles, source corpus/sums/dump, repair journal,
embedding/bundle artifacts, production DB/S3, `origin/main`, tags and deploy.

## Non-goals

No paid repair, embedding build, qualified bundle, DB/S3 publication, service
operation, W55b deployment or beta verdict. A passing preflight does not
reserve a future resource window.

## Deliverables

Exact four-path source patch, this task/report, bounded state update and
direct published-dev SHA readback.

## Required tests

- focused W54 preflight and programme suites, including CPU boundary and
  invalid measurement tests;
- compilation, direct task governance, frozen hashes, patch/path equality,
  whitespace, clean tree, fresh remote fast-forward and readback;
- no Docker/PG/S3, provider or full gate while W55b owns the host.

## Integration contract

Fast-forward exact source, then add only integration records. The operator
must still perform each W54 step's complete checksum/restore/journal/build/
bundle verification and remeasure resources immediately before heavy work.
The exclusive load<8 criterion is recorded for this host; it is not a
universal W54 contract. A moved remote stops publication.

## Failure/idempotency/security cases

Load at least 8 refuses; unavailable, negative or nonfinite load refuses
without invalid JSON. The existing CLI choices and 0/2 exit semantics remain.
No credential or source payload is printed or written.

## Rollback / feature flag

Revert the bounded offline preflight patch through a reviewed forward commit
if abandoned. No runtime flag or data rollback applies.

## Handoff

- changed files: four source paths plus this task, report and state;
- contracts: none; forbidden hotspots unchanged;
- next: resource window and external proxy credential for W54 paid sample.
