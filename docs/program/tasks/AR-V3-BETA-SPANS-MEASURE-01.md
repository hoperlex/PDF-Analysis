# Task AR-V3-BETA-SPANS-MEASURE-01 — paragraph-row exporter and a measurement of the C01–C22 candidate spans

task_id: AR-V3-BETA-SPANS-MEASURE-01
status: completed in development candidate

## Outcome

`scripts/norms/export_paragraph_rows.py` exports the exact `paragraphs` input of `map_pack` for requested spans of the qualified snapshot, read-only, and measures spans without emitting corpus text. With it the 22 candidate spans of the decision sheet were measured against the real snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, and `map_pack build` was run on a temporary, placeholder-marked decision file to get the target-only prompt-part size of each of the six scopes. Nothing is decided, approved, signed or promoted.

## Depends on

- `AR-V3-BETA-MAP-TOOL-01` — completed; `map_pack` and its paragraph-row format.
- `AR-BETA-LOCAL-CUSTODY-01` — completed; the qualified local snapshot and its stopped stack.
- `AR-BETA-AVAILABLE-SOURCE-GATE-01` — completed; the beta modes (14 provisional, 8 context-only).
- `AR-NORM-MAP-APPROVAL-PREP-01` — completed; the item decision sheet with the candidate spans.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.5.0`, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`
- base commit: `30aa736776e7cfacbd7bb5c86d70345731aa557b` (`integration/ar-close-1026`)
- beta source policy digest `9d3b7e53b512fbde1ea478a77a63c3c48042e85ddc50d57c96241c79bcb91d58`; composition digest `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`
- snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the qualified snapshot is present with 350,194 paragraphs in a healthy stopped-then-started custody container, and no paragraph-row exporter exists at the base

### P-01 — the custody container is healthy after `docker start`

- captured_at: 2026-10-26
- command: `docker inspect auditmanager-ar-beta-custody-postgres-1 --format '{{.State.Health.Status}}'`
- captured_output:
  ```text
  healthy
  ```
- interpretation: the only docker commands this lane ran were `docker start auditmanager-ar-beta-custody-postgres-1`, this inspect, and `docker stop auditmanager-ar-beta-custody-postgres-1` at the end. The `s3` containers were never started.

### P-02 — the snapshot holds 350,194 paragraphs

- captured_at: 2026-10-26
- command: `DATABASE_URL=<the custody stack .env value> PYTHONPATH=src .venv/bin/python -I -c "import os;from sqlalchemy import create_engine,text;c=create_engine(os.environ['DATABASE_URL']).connect();c.execute(text('SET TRANSACTION READ ONLY'));print(c.execute(text('select count(*) from norm_paragraph where norms_snapshot_id=:s'),{'s':'ns_01M59N8QNBVN91ACA2HCE6VE74'}).scalar())"`
- captured_output:
  ```text
  350194
  ```
- interpretation: matches `AR-BETA-LOCAL-CUSTODY-01` (350,194 paragraphs, 674 documents, 0 unreliable). The read ran in a `READ ONLY` transaction; nothing was written.

### P-03 — no exporter existed at the base

- captured_at: 2026-10-26
- command: `git grep -n "ar-beta-map-paragraphs-v1" 30aa7367 -- src scripts`
- captured_output:
  ```text
  30aa7367:src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.py:45:PARAGRAPHS_VERSION: Final[str] = "ar-beta-map-paragraphs-v1"
  ```
- interpretation: the only producer-side mention of the paragraphs format is the consumer's own constant; `scripts/norms/` held only `corpus_preflight.py`. The runbook of `AR-V3-BETA-MAP-TOOL-01` ("no exporter exists") was true at the base.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `scripts/norms/export_paragraph_rows.py`
- `tests/unit/scripts/test_export_paragraph_rows.py`
- `docs/program/ar-v3-beta/spans.proposal.json`
- `docs/program/tasks/AR-V3-BETA-SPANS-MEASURE-01.md`
- `docs/program/AR-V3-BETA-SPANS-MEASURE-01.md`

## Forbidden hotspots

All of `src/**`, `contracts/**`, `db/**`, `infra/**`, `web/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, the migration head, root dependency/lock files, the composition root, global styles, any corpus text anywhere in git, `origin/main`, tags and the deployment host.

## Non-goals

No span is approved or changed and no mode is decided: the beta policy still fixes 14 provisional and 8 context-only items. No edition page, BGE-M3 query vector, reviewed content decision or signature is produced or invented. No map built here may be promoted. The database is never written. No stand, S3 or provider is touched.

## Deliverables

- The exporter (`--out` rows, `--measure` numbers) with typed refusals, exit 2, `O_EXCL` mode-0600 output, a read-only transaction proven before the first query, and a refusal to write corpus text inside the repository tree outside `.local/`.
- Unit tests with a fake corpus for the format (including a run through the real `build_scope_maps` and `validate_scope_maps`) and every refusal, plus an optional class that runs against the qualified snapshot.
- `docs/program/ar-v3-beta/spans.proposal.json` — the sheet's spans as ids and ordinals, status `proposal_from_sheet_not_a_decision`.
- The report with the per-item and per-scope tables, the discrepancies and the list of what is still owed.

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/scripts/test_export_paragraph_rows.py`
- expected: 91 passed, 3 skipped (the skipped class needs `EXPORT_PARAGRAPH_ROWS_TEST_DATABASE_URL`); with it set to the started custody stack, 94 passed.
- governance: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-BETA-SPANS-MEASURE-01.md',encoding='utf-8').read())))"` prints `[]`.

## Integration contract

The exporter is an operator tool: `DATABASE_URL=… python scripts/norms/export_paragraph_rows.py --spans spans.json --snapshot ns_… --out .local/…/paragraphs.json` writes the file `map_pack build --paragraphs` and `map_pack validate --paragraphs` read; `--measure` prints one JSON object of numbers. Nothing imports the script and no other file depends on it. `spans.proposal.json` is the starting point for the owner's decision file, not an input any code reads.

## Failure/idempotency/security cases

Unknown document, document of another snapshot, missing first or last ordinal, gap inside a range, unreliable paragraph, duplicate ordinal from the source, rows `map_pack` would refuse (non-NFC text, unencodable text), invalid spans file (one code for every defect, including a 5,000-digit integer), invalid snapshot id, missing or invalid `DATABASE_URL` (the value is never echoed), a transaction that is not read-only, an existing output (also a dangling symlink), an unwritable output, and an output inside the repository tree: each is a typed `REFUSED: <code>` with exit 2 and no output file. A re-run on the same inputs writes an identical file into a new path.

## Rollback / feature flag

Not applicable: unserved, read-only tooling. Forward-revert the five files.

## Handoff

- changed files: the exporter, its tests, the proposal JSON, this task and the report
- commands/results: see the report; 91 tests green without a database, 94 against the qualified snapshot; 26 mutation probes all red
- known limits: the measured prompt parts are lower bounds on placeholder decisions; see the report
- integration notes: merge-independent; the custody container was stopped again at the end
