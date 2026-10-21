# W57A-SEAL-01A — storage and custody seal

**Base:** exact published development SHA
`c157ee0d4601f2bf81c68708ebf556b95b87acd5`. **Status:** isolated 0023
storage acceptance passed; ready for integrator cherry-pick. No remote ref or
deployment was changed.

## Result in the candidate

`0023_norm_citations` is the sole successor of `0022_findings_v2`. It adds a
`nrs_` identity and an immutable retrieval-set row with separate expected and
observed SHA-256 values for the set and catalogue. A verified row needs exact
digest equality, both immutable Blob identities and exactly one confirmed R-76
custody binding for each `norm_retrieval_set` and `norm_catalogue` role. A
rejected row cannot be pinned. Both roles use `target_kind=norm_retrieval_set`;
the binding guard checks target state and Blob metadata at publication.
The deferred check also requires the declared chunk/window counts to match
stored rows, at least one chunk, and a vector window for every chunk.

The optional `audit_run.norm_retrieval_set_id` pin is frozen and must point to
a verified row under that Run's pinned snapshot. Old rows remain NULL. The
immutable citation relation binds an observation to its Run, snapshot, set,
document and canonical reliable paragraph. The raw quote must be the exact
substring at its stored offset and length.

`finding_observation.norm_citation_count` is nullable. NULL means an unsealed
legacy partition; 0 is a certified empty partition; 1–5 is the number of
verified rows. Deferred triggers compare the count with immutable rows at
commit. A non-NULL partition also needs a succeeded `norm_verification`
StageResult and a pinned verified set. Normative categories require 1–5 rows
and both values; nonnormative published observations can certify only zero.
This is the storage proof that a later reader can consume. The W57a served
reader and CITE publisher have not been installed.

The domain candidate revision advances from 13 to 14 across all three
catalogues and schemas. The identifier catalogue and Python value types add
`NormRetrievalSet`/`nrs_`. The five normative category literals are
`evacuation`, `fire_safety`, `accessibility`, `insulation`, `sound`; the six
new reasons exactly match W57 §A3.4 and `citation_prep`. Existing API,
analysis stage registry, model lock and migration 0022 bytes remain unchanged.
The forward migration also adds the direct `fobs_` format CHECK for 0022's
`finding.canonical_observation_id`, whose existing composite FK alone did not
satisfy the schema's identity-column rule.

## Checks

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/contract/domain_p02
  tests/integration/norms/custody/test_custody_offline.py
  tests/contract/test_domain_identifiers_schema.py`: **176 passed**.
- Isolated instance `auditmanager-w57a-seal-01a`, ports 57471/61072/61073:
  **49 passed in 34.12s** across new citation tests, migration lifecycle,
  schema shape, custody and invariant inventory. The eight new tests include
  a populated 0022→0023 forward upgrade and refused populated downgrade,
  certified zero, missing/mismatched partitions, exact quote binding, missing
  catalogue binding, incomplete vector build and rejected/frozen Run pins.
- Fresh PostgreSQL 0022 and 0023 catalogues compared: columns +34, relations
  +2, constraints +33, indexes +3, triggers +7, functions +4; the view,
  extension, sequences, policies and state topology stayed identical. The
  measured 0023 family hashes are pinned in `test_schema_invariant_inventory.py`.
- `python3 -m py_compile` on the migration and new DB test, `git diff --check`
  and direct `governance_findings` on the task: pass; findings `[]`.
- The advisory `pin_sweep.py reseal-surface migration table error-code route`
  inventory retained SHA-256
  `5412fa5a43a348c22cdaa9b99395d9ad2555d3c22210ffe680f37d1647f3ae47`.
  Its whole-wave `--check` reports 92 grants outside this serial storage task;
  those API, UI, operations and later-stage consumers remain 01B/integrator
  review. The actual 31 changed paths were compared to 01A's exact grants.
- The old migration `20261015_0022_findings_v2.py` remains byte-identical at
  SHA-256 `d705cf86910e4be29c71057148a13b440b4e08f4dbe49c18a3407d714fe9680e`.
- The W57A containers and network were stopped with `make down` after the
  focused tests; their separate local volumes remain disposable.

## Known limit in the published predecessor

Empty downgrades through `0022_findings_v2` toward 0021 fail in PostgreSQL:
0022 attempts `CREATE OR REPLACE VIEW finding_current_verdict` while removing
its `decided_severity` column, which PostgreSQL refuses. This happens after
0023 has downgraded successfully. The two 0018 custody tests now start at
0018 and test their own revision directly. Migration 0022 remains
byte-identical; a separate owned forward repair or approved historical
correction is needed before any operational rollback through 0022. The 0023
populated downgrade itself refuses before data loss as required.

## Integration boundary

The next serial `W57A-SEAL-01B` task must own the four API artifacts, stage
registry, refusing `getRunNormVerification` operation, roles, generated client
and direct UI enum consumers. It must identify the v3 profile and make the
served reader reject NULL, mismatched count, incomplete stage, wrong Run,
snapshot or set. The later CITE publisher must write observation, count and
rows in one transaction after the deterministic gate. Neither may interpret
an empty SELECT as verified zero.

The reviewed map, source repairs, qualified DB/S3 corpus, live provider and
v3 runtime remain pending. The database count check does not validate vector
values, their digest or source PDF bytes; the independent qualification gate
must do that. No source or stand qualification is inferred from the synthetic
database fixtures. No tag, remote push or stand was touched by this candidate.

## File and hotspot ledger

Exactly 31 source paths changed, each in the task's explicit grants:

- `db/migrations/versions/20261016_0023_norm_citations.py`;
- `contracts/domain/v1/{identifiers,error-codes,state-machines}{,.schema}.json`;
- `src/auditmanager/shared/identity/{ids,__init__}.py`;
- `src/auditmanager/norms/custody/{roles,__init__}.py`,
  `src/auditmanager/norms/public.py`;
- `docs/program/{NORM_CORPUS_CUSTODY,P02_SEAMS,W57A-SEAL-01A}.md`,
  `docs/program/tasks/W57A-SEAL-01A.md`;
- `tests/integration/db/{test_norm_citations_migration,test_migration_lifecycle,
  test_schema_shape,test_schema_invariant_inventory,test_accounts_migration,
  test_execution_workers_migration,test_findings_v2_migration,
  test_fixture_template,test_norm_custody_migration,test_norms_search_migration,
  test_portal_bundles_migration,test_release_notes_migration}.py`;
- `tests/integration/jobs/test_recorded_v2_publication_gate.py`,
  `tests/integration/norms/custody/test_custody_offline.py`,
  `tests/support/expected_facts.json`.

Old migrations, API contracts, composition root, root dependencies and
lockfiles, global styles and W56 executor paths are outside the diff. The
private ignored `.env` held only this lane's distinct local service settings.
