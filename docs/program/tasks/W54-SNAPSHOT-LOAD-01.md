# Task W54-SNAPSHOT-LOAD-01 — load the repaired snapshot into the promotion database

task_id: W54-SNAPSHOT-LOAD-01

## Outcome

The repaired corpus snapshot (base projection plus the 121 session repairs of
`R-137`/`R-138`, `characters-v2:1200`) is committed once, atomically, to the
persistent promotion database beside the base snapshot. Its opaque `ns_`, content key,
row digest and counts are recorded, and a `pg_dump` of the database is
restore-verified against the table fingerprint. The promotion database is then
stopped. This is W54 step 3's first half; the embedding build is not part of it.

## Depends on

- `W54-CORPUS-PROMOTION-01` — completed restore-verified base dump and base snapshot;
- `W54-SESSION-REPAIR-01` — completed ledger accepted by `R-138`.

## Frozen inputs

- code base: `origin/dev` `db3dd97e84dee13cde0b79f9693fafa0fc299aeb`, worktree
  `.local/worktrees/w54-session-repair`; migration head `0023_norm_citations`;
- source drop: `/root/projects/PDF-Analysis/.local/norms/corpus` (read-only);
- source SHA256SUMS: `/root/projects/PDF-Analysis/.local/norms/corpus-sums/2026-10-15/SHA256SUMS`,
  SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- ledger: `/root/projects/PDF-Analysis/.local/norms/repairs/session-20261019/ledger.json`,
  SHA-256 `9639ce91c1605db8c2b0e9bfe5ae0f1ee858a76481f2308aed1f087efcd3c833`;
- base snapshot `ns_01M4ZW72BS7QHAMDJ993VHNJ7K`, content key
  `2026-07-23..2026-08-20+17d.4b74348debf7` (674 documents, 348,777 paragraphs,
  55,702 chunks); expected repaired content key
  `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`;
- promotion base: env file and verified base dump under
  `.local/worktrees/code-first-entry/.local/` (dump SHA-256
  `e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`), Docker volume
  `auditmanager-promotion-data`;
- Python: the lock-matched venv of `.local/worktrees/w55b-main-candidate`, called by
  path with `PYTHONPATH=src`;
- owner direction (2026-10-19, direct poll in this session): the 6 GiB available-RAM
  floor of `W54-PLAN.md` §3.9 is waived for this step only — the load and its dump and
  restore-verify. The disk floor is kept. The embedding build keeps the 6 GiB floor.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the promotion database holds exactly the base snapshot, so the repaired
  snapshot has not been loaded and the load adds a second snapshot rather than
  replacing one.

### P-01 — promotion database state before the load

- captured_at: 2026-10-19
- command: `docker exec auditmanager-promotion-postgres-1 sh -c 'psql -X -U $POSTGRES_USER -d $POSTGRES_DB -Atc "select norms_snapshot_id, content_key, document_count from norms_snapshot"'`
- captured_output:
  ```text
  ns_01M4ZW72BS7QHAMDJ993VHNJ7K|2026-07-23..2026-08-20+17d.4b74348debf7|674
  ```
- interpretation: one snapshot, the base; `alembic_version` was `0022_findings_v2`
  and is upgraded to the code head `0023_norm_citations` before the load (additive:
  retrieval-set and citation tables, no norm row touched).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-SNAPSHOT-LOAD-01.md`;
- `docs/program/W54-SNAPSHOT-LOAD-01.md`;
- the promotion database and its volume `auditmanager-promotion-data` (the load, the
  `0023` upgrade, nothing else);
- `.local/worktrees/code-first-entry/.local/norms/promotion-dumps/**` (the new dump and
  its sidecars; `verify-dump.sh` prunes the older dump);
- ignored `/root/projects/PDF-Analysis/.local/norms/promotion-records/20261019/**` and
  `/root/projects/PDF-Analysis/.local/norms/promotion-dumps-keep/20261015-base/**`
  (a copy of the base dump taken before pruning).

## Forbidden hotspots

`contracts/**`, migration files, root dependencies/locks, composition root, global
styles, the loader and repair code, source corpus and sums bytes, the ledger, the
production stand, S3, the env file's contents (never printed or copied),
`CURRENT_STATE.md`, remote `origin/main` and tags. Other projects' processes,
containers and volumes are not touched.

## Non-goals

No embedding prepare, build or load, no norm-worker image build, no bundle export,
no stand import, no deployment, no full gate. Those are the next W54 steps.

## Deliverables

- the repaired snapshot loaded once: `ns_`, content key, row digest, counts and
  `unreliable_count` recorded in the report;
- a `pg_dump` with its `.sha256` and fingerprint, restore-verified (`.verified`);
- measured peak RSS of the loader and the minimum available RAM during the run;
- the promotion database stopped;
- the result report.

## Required checks

- the loader result: `created` true, content key equal to the expected one,
  `unreliable_count` 0, documents 674;
- both snapshots present in the database after the load, and the base snapshot's rows
  unchanged (its table fingerprint share equals the base dump's);
- dump `.verified`, and the verified fingerprint reproduced by the restore;
- `git diff --check` and direct task `governance_findings` = `[]`.

## Integration contract

The recorded repaired `ns_` and content key are inputs of the embedding steps
(`embedding prepare --snapshot`) and of `bundle export`. The newest verified dump is the
recovery artifact for both. Nothing here changes a contract or a runtime path.

## Failure/idempotency/security cases

An exact repeat of the loader command reuses every stored id and creates nothing. A
failed or killed load rolls back as one transaction and leaves only the base snapshot.
The RAM watchdog stops only the confirmed own loader PID. No credential is printed.

## Rollback / feature flag

Delete the repaired snapshot's rows or restore the base dump kept in
`promotion-dumps-keep/20261015-base/`; revert the two documentation files. No runtime,
contract or deployed change.

## Handoff

- changed files: the allowed paths above;
- contracts: none;
- next: embedding `prepare`, the norm-worker image build and the encode windows under
  the 6 GiB floor, then the bundle;
- forbidden hotspots remain untouched.
