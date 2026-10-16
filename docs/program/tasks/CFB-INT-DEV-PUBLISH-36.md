# Task CFB-INT-DEV-PUBLISH-36 — integrate W57a set-custody input

task_id: CFB-INT-DEV-PUBLISH-36

## Outcome

A clean fast-forward `origin/dev` candidate carries an unserved W57a reader
of exact verified retrieval-set Blob bytes under current Attempt authority.

## Depends on

- `CFB-INT-DEV-PUBLISH-35` — complete at `75c558871535f456674af6fb70e3c0459ff8e8dd`;
- `W57A-INT-SET-CUSTODY-READ-PREP-01` — complete at `5ab5512eecbb90a6c89298bea4e9d93ede22c9e9`.

## Frozen inputs

- base commit: `75c558871535f456674af6fb70e3c0459ff8e8dd`
- source parent: `b9e26b0c154c1369742fe8124a91f3e5fdf986aa`;
- source/integrated patch SHA-256 `2f56aae5b494b1d1c80ce69630a915c9a7e0af472e28ea9423f64e1f0487bc59`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256 `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `VERSION=0.6.0`; R-135 defers the complete beta gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source has four unique additive paths, based on dev34, and its
  cherry-pick after dev35 preserves the complete patch.

### P-01 — exact source patch equality

- captured_at: 2026-10-16
- command: `git show --format= --binary 00bf1c82 | sha256sum`
- captured_output:
  ```text
  2f56aae5b494b1d1c80ce69630a915c9a7e0af472e28ea9423f64e1f0487bc59  -
  ```
- interpretation: source and integrated patch streams have the same hash;
  their four task-granted paths were not edited during integration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57A-INT-SET-CUSTODY-READ-PREP-01.md`
- `docs/program/tasks/W57A-INT-SET-CUSTODY-READ-PREP-01.md`
- `src/auditmanager/findings/retrieval_set_input.py`
- `tests/integration/findings/test_w57a_retrieval_set_input_offline.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-36.md`
- `docs/program/CFB-INT-DEV-PUBLISH-36.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

All other paths, especially contracts, migrations, existing findings
writers/readers, jobs/storage adapters, composition root, root dependencies
and locks, API/UI, global styles, production DB/S3, `origin/main`, tags and
deployment workflow.

## Non-goals

No W54 qualified set, served CITE stage, profile registration, model call,
response-to-candidate binding, real DB/S3 acceptance, W55b deployment or beta
verdict. The returned bytes are not publication authority by themselves.

## Deliverables

Exact four-path source patch, this task/report, bounded current-state update
and direct published-dev SHA readback.

## Required tests

- integrated W57a set reader, citation reader/writer, W56b TEXT and programme
  suites;
- compilation, direct task governance, frozen hashes, patch/path equality,
  whitespace, clean tree, fresh remote fast-forward and readback;
- no Docker/PG/S3 or complete beta gate while W55b owns the host.

## Integration contract

Cherry-pick exact source after dev35 and add only these integration records.
The future caller supplies authorized current Attempt and short transaction,
uses the verified bytes for the pure grounding gate, then rechecks publication
authority and recorded model response. Real PostgreSQL/S3 readback is required
before serving. A moved remote stops publication.

## Failure/idempotency/security cases

Missing/duplicate custody, wrong Run state, stale Attempt, invalid byte
ceiling, short/long/corrupt object and changed post-read pin refuse. The
object stream closes on success and failure; no fallback or write occurs.
Repeat publication only by exact fast-forward.

## Rollback / feature flag

Remove the additive unserved reader/tests through a reviewed forward commit
if abandoned. No data rollback or feature flag is needed before activation.

## Handoff

- changed files: four source paths plus this task, report and state;
- contracts: none; forbidden hotspots unchanged;
- next: isolated real DB/S3 custody proof and owned CITE-stage integration.
