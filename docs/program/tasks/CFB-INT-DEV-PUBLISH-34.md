# Task CFB-INT-DEV-PUBLISH-34 — integrate W57a verified citation reader

task_id: CFB-INT-DEV-PUBLISH-34

## Outcome

A clean fast-forward `origin/dev` candidate carries the unserved, read-only
W57a citation partition adapter. The served report retains its typed refusal.

## Depends on

- `CFB-INT-DEV-PUBLISH-33` — complete at `77d39efedd4d5c74582a02dbf5ea86acb4b054f7`;
- `W57A-INT-CITE-READ-PREP-01` — complete at `531e6468283ef63316eac5bb17cc701dcf36615a`.

## Frozen inputs

- base commit: `77d39efedd4d5c74582a02dbf5ea86acb4b054f7`
- published integration base: `origin/dev` at that commit;
- source commit `531e6468283ef63316eac5bb17cc701dcf36615a`, whose sole parent is that base;
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

- premise: the exact reader source is a direct child of published dev33 and
  touches only its four task-owned paths.

### P-01 — source parent and path set

- captured_at: 2026-10-16
- command: `git show --format='%H %P' --name-only 531e6468283ef63316eac5bb17cc701dcf36615a`
- captured_output:
  ```text
  531e6468283ef63316eac5bb17cc701dcf36615a 77d39efedd4d5c74582a02dbf5ea86acb4b054f7
  docs/program/W57A-INT-CITE-READ-PREP-01.md
  docs/program/tasks/W57A-INT-CITE-READ-PREP-01.md
  src/auditmanager/findings/citation_reader.py
  tests/integration/findings/test_w57a_citation_reader_offline.py
  ```
- interpretation: the source can be fast-forwarded without changing its bytes.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57A-INT-CITE-READ-PREP-01.md`
- `docs/program/tasks/W57A-INT-CITE-READ-PREP-01.md`
- `src/auditmanager/findings/citation_reader.py`
- `tests/integration/findings/test_w57a_citation_reader_offline.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-34.md`
- `docs/program/CFB-INT-DEV-PUBLISH-34.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

All other paths, especially contracts, migrations, root dependencies/locks,
composition root, existing findings adapters, API/UI, global styles,
production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No registered v3 profile, served report, provider call, W54 corpus, real DB/S3
acceptance, W55b deployment or beta verdict. This integration does not turn
persisted rows into public report authority.

## Deliverables

The exact four-path source, this task/report, bounded state update and direct
published-dev SHA readback.

## Required tests

- source reader/writer focused tests and programme governance suite;
- compilation, frozen-hash, source/path equality, whitespace and clean-tree checks;
- fresh remote fast-forward and post-push exact readback;
- no Docker/PG/S3 or complete beta gate while W55b owns the host.

## Integration contract

Fast-forward the exact source commit, add only these integration records and
publish a checked SHA to `origin/dev`. The future W57a owner supplies a
registered v3 profile, authorized consistent DB read, withheld/partial/error
report assembly and an owned API slot. Real PostgreSQL readback of 0023
partitions remains required. A moved remote ref stops publication.

## Failure/idempotency/security cases

The reader refuses stale or incomplete persisted facts; it remains unserved.
Do not map a NULL citation certificate to zero or use a caller's profile string
as proof of registration. Repeat publication only by exact fast-forward.

## Rollback / feature flag

Remove the additive reader/tests through a reviewed forward commit if
abandoned. No runtime flag or data rollback is required before activation.

## Handoff

- changed files: four source paths plus this task, report and state;
- contracts: none; forbidden hotspots unchanged;
- next: isolated real DB proof, v3 profile and report assembly owner.
