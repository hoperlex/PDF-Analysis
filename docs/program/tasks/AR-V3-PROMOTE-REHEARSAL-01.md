# Task AR-V3-PROMOTE-REHEARSAL-01 — six request bundles and six read-only `promote_cli plan` runs on the custody lane

task_id: AR-V3-PROMOTE-REHEARSAL-01
status: completed in development candidate (lane AR-B2, part 2 of wave PW5; step 8a of the activation plan; bundles and `plan` only, no `promote`)

## Outcome

For each of the six scopes F1 F2 A1 A2 S1 S2 of the AR v3 beta pack there is one minted `nrs_` identity (`.local/ar-v3-draft/set-ids.json`), one request bundle (`.local/ar-v3-draft/bundle-<S>/` with `map.json` and `request.json`, no `expected_*` key), and one `promote_cli plan` run against the stopped custody lane `auditmanager-ar-beta-custody` that exited 0 and whose stdout is saved. The report records the wall time of each run and the digests the next, independent lane has to recompute. Nothing was written to the database or the object store, and all three containers of the lane are stopped again.

## Depends on

- `AR-V3-ACTIVATION-FEASIBILITY-01` — completed; section 8 step 8 is the plan.
- `AR-V3-BETA-SET-TOOL-01` — completed; `promote_cli` and its bundle format.
- `AR-V3-ACTIVATION-PREP-01` — completed; `decisions.json`, `query-texts.json`, `scopes.json`.
- `AR-BETA-LOCAL-CUSTODY-01` — completed; the qualified snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` in the custody lane.
- The integrator's steps 4 to 7 of the activation order (paragraph export, query vectors, `map_pack build` and `validate`), recorded in commits `4561f63f` and `cb7a34d3`.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.8.0`, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0035_comparison_records` in the tree, unchanged; the custody lane stays at `0031_executor_pull_channel` and is not migrated
- base commit: `cb7a34d3` (`integration/ar-close-1026`)
- rulings `R-146ba` and `R-146bb` (`docs/program/OWNER_RULINGS_2026-09-17.md`); accepted risks `A-10` and `A-11` (`docs/program/PRODUCTION-READINESS-PLAN-01.md`)
- the six maps `.local/ar-v3-draft/pack/scope-<S>.map.json` (digests in `docs/program/ar-v3-beta/scopes.json`), the six vector responses `.local/ar-v3-draft/embed-<S>.response.json` (digests in `decisions.json`)
- the verified W54 bundle `.local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the custody lane is stopped; the two proof digests exist in the verified bundle manifest; the six map digests of the tracked `scopes.json` equal the bytes the bundles carry; `plan` never opens the object store, so the PostgreSQL container is the only one needed

### P-01 — the three containers of the custody lane are stopped before the run

- captured_at: 2026-10-27
- command: `docker ps -a --filter name=auditmanager-ar-beta-custody --format '{{.Names}}  {{.Status}}'`
- captured_output:
  ```text
  auditmanager-ar-beta-custody-s3-init-1  Exited (255) 3 days ago
  auditmanager-ar-beta-custody-postgres-1  Exited (0) 5 minutes ago
  auditmanager-ar-beta-custody-s3-1  Exited (255) 3 days ago
  ```
- interpretation: nothing runs. The PostgreSQL container was stopped by the integrator after the paragraph export (5 minutes before this listing); the S3 pair is three days old.

### P-02 — the proof digests come from the verified bundle manifest

- captured_at: 2026-10-27
- command: `python3 -c "import json,glob;m=json.load(open(glob.glob('/root/projects/PDF-Analysis/.local/norms/bundles/*/manifest.json')[0]));print(m['snapshot']['content_digest']);print(m['build']['embedding_set_sha256']);print(m['chunking_profile'])"`
- captured_output:
  ```text
  0a1bafe103ff2df5d53108af602b7aa788d0831353228bfc92c9506a411a3b10
  e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df
  characters-v2:1200
  ```
- interpretation: the source proof digest (`snapshot.content_digest`), the embedding-set digest (`build.embedding_set_sha256`, equal to the `build` digest of `AR-BETA-LOCAL-CUSTODY-01`) and the chunking profile. The manifest's SHA-256 was also compared with its line in the bundle's `SHA256SUMS` before use (equal, `cc0f5ee8...`). These values are not read from the database being qualified.

### P-03 — the six bundle maps are the maps the tracked pack summary names

- captured_at: 2026-10-27
- command: `python3 -c "import json,hashlib;s=json.load(open('docs/program/ar-v3-beta/scopes.json'));print([(r['scope_id'],r['map_sha256']==hashlib.sha256(open('/root/projects/PDF-Analysis/.local/ar-v3-draft/bundle-%s/map.json'%r['scope_id'],'rb').read()).hexdigest()) for r in s['scopes']])"`
- captured_output:
  ```text
  [('F1', True), ('F2', True), ('A1', True), ('A2', True), ('S1', True), ('S2', True)]
  ```
- interpretation: each `bundle-<S>/map.json` is byte-identical to the map whose digest is in `scopes.json`. It does not show that the maps are right; no person reviewed them.

### P-04 — `plan` builds its runner without an object store

- captured_at: 2026-10-27
- command: `grep -n "factory(" src/auditmanager/norms/retrieval/promote_cli.py`
- captured_output:
  ```text
  593:        session = self._factory()
  665:    return DatabaseRunner(get_session_factory(), store)
  763:        prepared = factory(False).prepare(loaded.request)
  779:        runner = factory(True)
  ```
- interpretation: line 763 is in `_plan` (starts at line 760) and asks for no store; line 779 is in `_promote` (starts at line 774) and asks for the store. So `plan` needs `DATABASE_URL` only and the S3 containers stay stopped. This does not prove that `plan` writes nothing; the tool report's tests do.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/AR-V3-PROMOTE-REHEARSAL-01.md`
- `docs/program/tasks/AR-V3-PROMOTE-REHEARSAL-01.md`

Untracked files this lane writes outside the repository, all under `/root/projects/PDF-Analysis/.local/ar-v3-draft/` and never added to Git: `set-ids.json`, `bundle-<S>/`, `plan-<S>.txt`, `plan-<S>.err`, `plan-<S>.time`, `make_bundles.py`, `run_plan.sh`. Temporary lane file in the worktree: the `.venv` symlink (ignored).

## Forbidden hotspots

All of `src/**`, `tests/**`, `contracts/**`, `db/**`, `infra/**`, `web/**`, `scripts/**` and every other path under `docs/program/**` (so also `docs/program/ar-v3-beta/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md` and `OWNER_RULINGS_*.md`), the migration head, root dependency/lock files, the composition root, global styles, any corpus text or vector in git, `decisions.json`, the maps and the vectors (a refusal is reported, never repaired), `origin/dev`, `origin/main`, tags, other worktrees. The lane's database is not migrated, `promote` is not run, and no `expected_*` key is written.

## Lane resources

Uses the stopped local custody lane, not a new instance. It is not isolated from other readers, so the use is read-only.

- foundation_instance: `auditmanager-ar-beta-custody`
- postgres_port: `58490`
- s3_api_port: `62090`
- s3_console_port: `62091`
- postgres_db: `auditmanager_ar_beta_custody`
- s3_bucket: `auditmanager-ar-beta-custody`

Allowed docker verbs, on exactly the three containers `auditmanager-ar-beta-custody-postgres-1`, `-s3-1` and `-s3-init-1`: `start`, `stop`, `ps`, `inspect`. No build, `rm`, `exec`, volume or image command, no other container, no kill by pattern. `DATABASE_URL` is built from the container's own environment at run time and is never printed or stored.

## Non-goals

- No `promote`, no replay, no `expected_*` key, no `seal`, no migration of the lane, no object-store access.
- No independent recomputation: the same lane built the bundles and ran `plan`, so this is the first half of the two-person check only, and the report says so.
- No change to `decisions.json`, the maps, the vectors or the tool. If `plan` had refused, the refusal would be reported verbatim with the smallest proposed fix.
- No claim that an edition is current, that a branch applies to a real project, or that anyone reviewed a norm: the activation is prepared by the AI integrator under `R-146ba` and `R-146bb`, with no subject-matter expert.

## Deliverables

- the six set ids, the six bundles and the six saved `plan` outputs, untracked, under `.local/ar-v3-draft/`;
- the report `docs/program/AR-V3-PROMOTE-REHEARSAL-01.md`: what was done, the commands, the wall time and exit code of each run, the digests the independent lane recomputes, the observations, the proof that the containers are stopped;
- this task file.

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: green apart from failures present at the base (named in the handoff).
- governance: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-PROMOTE-REHEARSAL-01.md',encoding='utf-8').read())))"` — expected `[]`.
- `git diff --check` clean; only the two allowed paths changed; `docker ps --filter name=auditmanager-ar-beta-custody --format '{{.Names}}'` prints nothing.

## Integration contract

The next lane (independent recomputation) reads the report and the bundles under `.local/ar-v3-draft/`, recomputes the digests of section 6 of the report from the verified W54 bundle and its own reading of the snapshot, and writes `expected_set_sha256` and `expected_catalogue_sha256` into its own copy of the bundles. Only then may `promote` run, with the same `set_id`s (`set-ids.json`); a second id for a scope is never minted. The live host repeats `promote` with the same bundles and `plan` must end `verdict: matched` against these digests.

## Failure/idempotency/security cases

The bundle directories are created with mode 700 and the script refuses to overwrite one. `plan` is a read-only transaction and the same bundle gives a byte-identical stdout (F1 run twice, `cmp` equal). The request bundles hold query vectors and the `plan` files hold ids, digests, ordinals and designation labels: none of them is in Git, and no corpus text was read or written. No password is in any file: `DATABASE_URL` exists only in the environment of the `plan` process. A refusal exits 2 with nothing written and leaves the `set_id` free.

## Rollback / feature flag

Not applicable: two new documents. Revert the commit to remove them; the untracked `.local/ar-v3-draft/` files can be deleted by the integrator, but the six set ids in `set-ids.json` must be kept for as long as any bundle is.

## Handoff

- changed files: the two documents named under Allowed paths (both new)
- commands/results: see the report; six `plan` runs, exit 0, 1.7 to 2.3 s each; governance prints `[]`
- known limits: not independent; `promote` and the replay were not run; `prompt_part_characters` of F1, S1 and S2 differ from the target-only values of `pack-summary.json` (S1 is 79 characters under the cap of 22,000); the six catalogues are byte-identical; nobody reviewed any norm
- integration notes: merge-independent (new paths only); the integrator reads section 4 and section 6 of the report before dispatching the independent lane
