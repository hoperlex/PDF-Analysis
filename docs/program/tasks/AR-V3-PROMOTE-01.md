# Task AR-V3-PROMOTE-01 — independent second check of the six AR v3 bundles, six promotions, replay, seal and offline verify

task_id: AR-V3-PROMOTE-01
status: completed in development candidate (lane AR-B3, part 3 of wave PW5; step 8b and step 9 of the activation plan, on the local custody lane only)

## Outcome

A second, separate AI lane (not an expert) recomputed the inputs of the six AR v3 beta bundles from the verified W54 bundle and the tracked records, ran its own `promote_cli plan` on copies of the bundles, compared with the first lane's `plan` outputs (all equal), wrote its own `expected_set_sha256` and `expected_catalogue_sha256` into its copies, ran `plan` (`verdict: matched`), `promote` for the six sets one at a time, and the replay of each (`replayed: true`, nothing changed). It then sealed `pack.json` against the custody lane with the Russian review record of the feasibility report, section 6, and `v3_pack_cli verify` exits 0 offline. `pack.json` stays under `.local/` (not in Git); the report records its SHA-256.

## Depends on

- `AR-V3-PROMOTE-REHEARSAL-01` — completed; the six bundles, set ids and `plan` outputs under `.local/ar-v3-draft/`.
- `AR-V3-ACTIVATION-FEASIBILITY-01` — completed; section 6 (seal values) and section 8 (steps 8 and 9).
- `AR-V3-BETA-SET-TOOL-01` — completed; `promote_cli` and the bundle format.
- `AR-V3-BETA-PACK-INSTALL-01` — completed; `v3_pack_cli seal` and `verify`.
- `AR-V3-ACTIVATION-PREP-01` — completed; `decisions.json`, `query-texts.json`, `scopes.json`, `vectors-provenance.json`.
- `AR-BETA-LOCAL-CUSTODY-01` — completed; the qualified snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` in the custody lane.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.8.0`, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0035_comparison_records` in the tree, unchanged; the custody lane stays at `0031_executor_pull_channel` and is not migrated
- base commit: `6fcbec57` (`integration/ar-close-1026`)
- rulings `R-146ba` and `R-146bb` (`docs/program/OWNER_RULINGS_2026-09-17.md`); accepted risks `A-10` and `A-11` (`docs/program/PRODUCTION-READINESS-PLAN-01.md`)
- the six maps `.local/ar-v3-draft/pack/scope-<S>.map.json` (digests in `docs/program/ar-v3-beta/scopes.json`), the vector responses `.local/ar-v3-draft/embed-<S>.response.json`, the bundles `.local/ar-v3-draft/bundle-<S>/`
- the verified W54 bundle `.local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the custody lane is stopped and holds no retrieval set and no pending admission; the verified bundle's two proof digests are hash-chained to `SHA256SUMS`; the lane is at head 0031 and is not migrated

### P-01 — the three containers of the custody lane are stopped before the run

- captured_at: 2026-10-27
- command: `docker ps -a --filter name=auditmanager-ar-beta-custody --format '{{.Names}}  {{.Status}}'`
- captured_output:
  ```text
  auditmanager-ar-beta-custody-s3-init-1  Exited (255) 3 days ago
  auditmanager-ar-beta-custody-postgres-1  Exited (0) 7 minutes ago
  auditmanager-ar-beta-custody-s3-1  Exited (255) 3 days ago
  ```
- interpretation: nothing runs; the lane may be started by `docker start` on exactly these names.

### P-02 — the proof digests come from the verified bundle and the files read are hash-chained

- captured_at: 2026-10-27
- command: `cd .local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245 && sha256sum manifest.json rows/snapshot.json && grep -F -e ' manifest.json' -e ' rows/snapshot.json' SHA256SUMS && python3 -c "import json;m=json.load(open('manifest.json'));print(m['snapshot']['content_digest']);print(m['build']['embedding_set_sha256'])"`
- captured_output:
  ```text
  cc0f5ee80ef4b2be43ff41789930ed8e5d14056cdfa6101f97ef582f138f21cf  manifest.json
  929cacef6cb59c432ec1e7972f92832c83d6598313b96001bd7c5b097b28b124  rows/snapshot.json
  cc0f5ee80ef4b2be43ff41789930ed8e5d14056cdfa6101f97ef582f138f21cf  manifest.json
  929cacef6cb59c432ec1e7972f92832c83d6598313b96001bd7c5b097b28b124  rows/snapshot.json
  0a1bafe103ff2df5d53108af602b7aa788d0831353228bfc92c9506a411a3b10
  e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df
  ```
- interpretation: the first two lines are the files' own hashes, the next two the lines of `SHA256SUMS` (equal); the last two are the source proof digest (`snapshot.content_digest`) and the embedding-set digest (`build.embedding_set_sha256`) that the six requests must carry. The SHA-256 of `SHA256SUMS` itself equals the tail of the directory name (checked in the report, section 3).

### P-03 — the custody lane holds no retrieval set and no foreign pending admission

- captured_at: 2026-10-27
- command: a read-only query run through the application's own session factory (`REPEATABLE READ READ ONLY`): `select version_num from alembic_version`; `select state, count(*) from norm_retrieval_set group by 1`; `select role, state, count(*) from norm_custody_admission group by 1,2`; `select role, count(*) from norm_custody_binding group by 1`; one `select ... from norm_retrieval_set where norm_retrieval_set_id = :id` per set id
- captured_output:
  ```text
  migration head ['0031_executor_pull_channel']
  norm_retrieval_set by state []
  norm_custody_admission by role,state [('norm_source', 'confirmed', 28920)]
  norm_custody_binding by role [('norm_source', 28920)]
  nrs_01M5YF1W4BG5260JTSCAZP3F58 [] bindings []
  nrs_01M5YF1WVZYFD50K47BDYZM59D [] bindings []
  nrs_01M5YF1XMMCHT6F6K6HWZEJG4H [] bindings []
  nrs_01M5YF1Y8EBK2CBW9JGFADFK31 [] bindings []
  nrs_01M5YF1YXN8WZTV8TFKZ0EWVTZ [] bindings []
  nrs_01M5YF1ZFPGBN4PMERTPN6GA27 [] bindings []
  ```
- interpretation: the six ids are free, no admission is pending (so `promote` will not refuse with `foreign_pending_admissions`), and the lane's head is `0031`, which this task leaves as it is: `promote` and `seal` write additively to the norm tables and the bucket, and migrations `0032` to `0035` do not alter them (feasibility report, section 2.2).

### P-04 — disk before the run

- captured_at: 2026-10-27
- command: `df -B1 /`
- captured_output:
  ```text
  Filesystem          1B-blocks         Used    Available Use% Mounted on
  /dev/vda3        126828056576 114104627200   6269960192  95% /
  ```
- interpretation: 6.27 GB free; the six sets add about 6.4 MB of Blobs and the lane's volumes a few tens of MB, so the run fits; the report gives the figure after.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/AR-V3-PROMOTE-01.md`
- `docs/program/tasks/AR-V3-PROMOTE-01.md`

Untracked files this lane writes outside the repository, all under `/root/projects/PDF-Analysis/.local/ar-v3-draft/` and never added to Git: `independent/` (the check results, six bundle copies with the `expected_*` keys, `own-plan*`, `promote-*`, `replay-*`, `seal*`, `verify*`, database snapshots) and `pack.json` (mode 0600). Temporary lane file in the worktree: the `.venv` symlink (ignored).

## Forbidden hotspots

All of `src/**`, `tests/**`, `contracts/**`, `db/**`, `infra/**`, `web/**`, `scripts/**` and every other path under `docs/program/**` (so also `docs/program/ar-v3-beta/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md` and `OWNER_RULINGS_*.md`), the migration head, root dependency/lock files, the composition root, global styles, any corpus text or vector in Git, `decisions.json`, the maps and the vectors (a difference is reported, never repaired), `pack.json` in Git, `origin/dev`, `origin/main`, tags, other worktrees. The lane's database is not migrated.

## Lane resources

Uses the stopped local custody lane, not a new instance. It is not isolated from other readers, so the use is announced and short.

- foundation_instance: `auditmanager-ar-beta-custody`
- postgres_port: `58490`
- s3_api_port: `62090`
- s3_console_port: `62091`
- postgres_db: `auditmanager_ar_beta_custody`
- s3_bucket: `auditmanager-ar-beta-custody`

Allowed docker verbs, on exactly the three containers `auditmanager-ar-beta-custody-postgres-1`, `-s3-1` and `-s3-init-1`: `start`, `stop`, `ps`, `inspect`, each as a separate command. No build, `rm`, `exec`, volume or image command, no other container, no kill by pattern. `DATABASE_URL` and the S3 settings are built from the containers' own environment at run time and are never printed or stored.

## Non-goals

- No change to `decisions.json`, the maps, the vectors or the tool. If a check had differed, the lane would have stopped before writing `expected_*` and reported the difference verbatim with the smallest fix.
- No migration of the lane, no promotion on any other database, no `seal` against any other database, no install of `pack.json` anywhere.
- No expert review. This is a second AI check; the record in `pack.json` and the report say so, and no text claims that an edition is current, that a branch applies to a real project, or that anyone compared a norm with its official edition.
- No re-derivation of the query vectors from the BGE-M3 image and no recomputation of the embedding-set digest from the window vectors.

## Deliverables

- `independent/` and `pack.json` (untracked) as listed under Allowed paths;
- the report `docs/program/AR-V3-PROMOTE-01.md`: every comparison with its result, the digests (no corpus text), commands, wall times, refusals (none), containers state, `df`, the SHA-256 of `pack.json` and the seal values;
- this task file.

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: green apart from failures present at the base (named in the handoff).
- governance: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-PROMOTE-01.md',encoding='utf-8').read())))"` — expected `[]`.
- `git diff --check` clean; only the two allowed paths changed; `docker ps --filter name=auditmanager-ar-beta-custody --format '{{.Names}}'` prints nothing.

## Integration contract

The integrator reads the report (sections 3 to 6 and 10) and keeps `.local/ar-v3-draft/independent/bundle-<S>/` (the bundles with the `expected_*` keys) and `pack.json` with the custody of the lane. The live host (feasibility step 10) promotes the same six bundles with the same `set_id`s; `plan` there must end `verdict: matched` against the digests of the report, section 4; then `seal` against the live database. The pack sealed here names rows of the custody lane's database and is not the file to install. The tool's refusal semantics are those of `AR-V3-BETA-SET-TOOL-01`: a difference is never repaired by editing bundle bytes.

## Failure/idempotency/security cases

`promote` is idempotent for a `set_id`: the replay of all six printed `replayed: true` and a before/after snapshot of the table counts and set rows is identical. A digest mismatch would have exited 2 with nothing written and the id free (`expected_digest_mismatch`); no refusal occurred. `seal` refuses an existing `--out` without `--force` (`out_exists`); the file was new and written with mode 0600. No password is in any file or in the report: `DATABASE_URL` and the S3 settings exist only in the environment of the processes. The bundles hold query vectors and the check outputs hold ids, digests and ordinals; none is in Git and no corpus text was written.

## Rollback / feature flag

Not applicable: two new documents. Revert the commit to remove them. The six verified sets in the custody lane are additive and are removed only by dropping that lane's volumes (an integrator decision); `pack.json` can be deleted from `.local/`. The server reads a pack only when `AR_V3_BETA_PACK_MANIFEST` names one, and this task installs none.

## Handoff

- changed files: the two documents named under Allowed paths (both new)
- commands/results: see the report; all comparisons equal and none different (463 input checks, 60 own-plan checks, 28 vector-digest checks against the tracked provenance, 36 field and 6 whole-output comparisons with the first lane); six `plan` (matched), six `promote` (verified, `replayed: false`), six replays (`replayed: true`, nothing changed), `seal` exit 0, `verify` exit 0; `pack_sha256` `5d87c1ef52b09aaaab73325c0504c401b29a5af23a16162165ef5954de59251d`, file SHA-256 `9c2cdc9d71402f80cef1e13da54ab3f15f06d833c30345fe3e240ad77ec8cd78`
- known limits: AI-to-AI check, no expert; set and catalogue digests are from the same tool and database as the first lane; S1 has 79 characters under the 22,000 cap; F2, A1 and A2 carry target rows only (the cap removed every retrieved window); vectors not re-derived from the image
- integration notes: merge-independent (new paths only); `pack.json` and the bundles are untracked under `.local/ar-v3-draft/`
