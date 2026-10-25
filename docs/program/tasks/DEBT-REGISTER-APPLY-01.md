# Task DEBT-REGISTER-APPLY-01 — apply three measured audits to the debt register

task_id: DEBT-REGISTER-APPLY-01
status: completed in development candidate

## Outcome

Every row of `docs/program/DEBT_REGISTER.md` that `DEBT-AUDIT-1`, `DEBT-AUDIT-2` or `DEBT-AUDIT-3` measured as closed, narrowed or carrying a stale cite or count now says what the audit measured, in the register's own table style:

- 18 rows are struck and carry `closed in the tree by <commit/task>, found on 2026-10-26 by DEBT-AUDIT-<N>` with the check command the audit quotes (`D-124`, `D-126`, `D-127`, `D-141`, `D-198`, `D-79`, `D-87`, `D-91`, `D-107`, `D-110`, `D-69`, `D-71`, `D-68`, `D-60`, `D-61`, `D-1.6`, `D-8`, `D-9`);
- six rows that the audit found fixed in code but that the register holds open for the deferred QA and complete-gate evidence (`D-125`, `D-128`, `D-131`, `D-134`, `D-135`, `D-136`) stay open as narrowed: code in the tree, validation waits for the complete gate (`D-139`/`D-140`);
- 20 narrowed rows carry the audit's narrowed statement and stay open (`D-119`, `D-121`, `D-129`, `D-133`, `D-137`, `D-138`, `D-140`, `D-144`, `D-165`, `D-183`, `D-184`, `D-186`, `D-197`, `D-199`, `D-203`, `D-75`, `D-83`, `D-108`, `D-117`, `D-59`; `D-104` was classified narrowed but the audit proposes its wording unchanged); three rows (`D-178`, `D-187`, `D-191`) have only the stale count or cite corrected;
- 31 detail sections get one italic line at the top pointing to the re-measured table row;
- every other table row and every other line of the register is byte-for-byte unchanged, including the five rows (`D-142`, `D-148`, `D-150`, `D-152`, `D-170`) and the new rows `D-204`…`D-212` that the orchestrator had already updated.

## Depends on

- `AR-CLOSE-1026` integration branch at `1703d5ba`, which carries the three merged audit reports `docs/program/DEBT-AUDIT-1.md`, `docs/program/DEBT-AUDIT-2.md` and `docs/program/DEBT-AUDIT-3.md` (read-only inputs; the audit lanes had no task files).

## Frozen inputs

- domain contract: unchanged
- API contract: `1.5.0`, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `1703d5bacacb1288fe7bdd7f99793705f1453406`
- the audits measured base `6b57928f72585d4c8019ae5fe1a5d78555929a1f`; the contract seal `a6761bf4` (1.5.0) landed between the two bases and was re-checked for the claims it could touch (see P-03).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the three audit reports exist on the base with the audited row counts they declare, and the register still lists the audited rows in the pre-audit wording

### P-01 — the three audits and their audited rows

- captured_at: 2026-10-26
- command: `grep -c '^| D-' docs/program/DEBT-AUDIT-1.md docs/program/DEBT-AUDIT-2.md docs/program/DEBT-AUDIT-3.md`
- captured_output:
  ```text
  docs/program/DEBT-AUDIT-1.md:27
  docs/program/DEBT-AUDIT-2.md:28
  docs/program/DEBT-AUDIT-3.md:26
  ```
- interpretation: 27 + 28 + 26 = 81 audited rows, the counts the three reports declare. For reference `grep -c '^| ' docs/program/DEBT-AUDIT-*.md` prints 28, 40 and 27 because it also counts each report's header and summary-table lines.

### P-02 — the register table before the change

- captured_at: 2026-10-26
- command: `git show 1703d5ba:docs/program/DEBT_REGISTER.md | sed -n 31,176p | grep -c '^| ~~'`
- captured_output:
  ```text
  55
  ```
- interpretation: 55 struck rows before the change; the table has 144 data rows, 89 of them open. After the change the table has 145 data rows (the shared `D-1.6, D-8` row becomes two rows), 73 struck and 72 open.

### P-03 — claims the contract seal could have moved

- captured_at: 2026-10-26
- command: `git log --oneline 6b57928f..HEAD -- contracts | cat`
- captured_output:
  ```text
  a6761bf4 AR-V3-BETA-PACK-STATUS-API-01 seal contract 1.5.0 (92 paths, 104 operations, 300 schemas)
  b02f680e Seal AR v3 beta pack status OpenAPI content
  ```
- interpretation: the seal changed `contracts/api/v1/openapi.json`, `contracts/analysis/v1/stage-registry.json` and the version fields of the domain and event contracts after the audits' base (33 files, `git diff --stat 6b57928f HEAD -- contracts`). The register claims this lane writes that depend on `contracts/` were re-measured on the base: no `429` response in the OpenAPI (`D-129`), `identifiers.schema.json` `required` of 36 names against 48 declared identifiers (`D-129`), and `RunStatus.terminal_message` read only in `api/schemas` (`D-133`) all still hold. The `stage-registry.json` hash quoted by `DEBT-AUDIT-2` for `D-187` (`d7b9994b…`) did not survive the seal (`7e1aaaaf…` at `a6761bf4`), so the `D-187` row states the current hash and the commits instead.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/DEBT_REGISTER.md`
- `docs/program/tasks/DEBT-REGISTER-APPLY-01.md`
- `docs/program/DEBT-REGISTER-APPLY-01.md`

## Forbidden hotspots

Everything outside the three allowed paths: `docs/program/CURRENT_STATE.md`, the three audit reports, `contracts/**`, `db/migrations/**`, root dependency and lock files, `Makefile`, `infra/**`, global styles, the composition root, all code and tests, `origin/main`, tags and the deployment host.

## Non-goals

- No new measurement against the tree beyond the re-checks in P-03 and the commit-existence check in the report; the audits are the evidence.
- No rewrite of a detail section: only one italic line is added at its top.
- No change to a row the audit left `unchanged`, to the rows already updated by the orchestrator (`D-142`, `D-148`, `D-150`, `D-152`, `D-170`, `D-204`…`D-212`) or to the prose before and after the table.
- The stale prose the audits list for rows that stay otherwise unchanged is not rewritten: `D-145` ("carried to the first minor version after the 1.0.0 seal"), `D-171` (figures predate `0c5ab9ca`), `D-109`/`D-50`/`D-11` (count and cites that sit only in their detail sections), `D-96` (the register's rows checked by nothing).

## Deliverables

- the edited `docs/program/DEBT_REGISTER.md`;
- this task file and the short report `docs/program/DEBT-REGISTER-APPLY-01.md`, which prints the set of changed rows next to the set the audits classified.

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: all pass.
- command: `git diff --check`
- expected: no output.
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/DEBT-REGISTER-APPLY-01.md',encoding='utf-8').read())))"`
- expected: `[]`
- command: the changed-set comparison described in the report (a script kept out of git lists the ids whose table row text changed and compares them with the ids the three audits classified CLOSED-IN-TREE or NARROWED plus the stale-cite rows).
- expected: `MATCH`, and the text outside the table is identical once the 31 note lines are removed.

## Integration contract

The integrator merges this lane after the three audit merges that are already on `integration/ar-close-1026`. The register rows now read as the audits measured them on 2026-10-26; rows marked closed still need the owner-facing note that `D-125`, `D-128`, `D-131`, `D-134`, `D-135` and `D-136` were deliberately not closed. Counts or lists elsewhere that name the open rows (for example in `CURRENT_STATE.md`) are not touched here.

## Failure/idempotency/security cases

A row text that no longer matches the audit's evidence (the tree moved after the audit) is the one failure mode: it was checked for the contract-dependent rows (P-03) and for every commit hash written (all 50 resolve to commits in this repository). The script that applied the edits (kept outside git) asserts the exact old text of every row, heading and cite before replacing it, and refuses on a mismatch.

## Rollback / feature flag

Documentation only. Forward-revert the lane's commit; no feature flag.

## Handoff

- changed files: `docs/program/DEBT_REGISTER.md`, this task file, `docs/program/DEBT-REGISTER-APPLY-01.md`
- commands/results: see the report
- known limits: the audits' own evidence is trusted for DB-, stand- and Vitest-bound claims that no lane could run; the closed rows `D-87` and `D-141` rest on tests that need PostgreSQL and were read, not run
- integration notes: see the integration contract
