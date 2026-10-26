# Task PRODUCTION-ADR-PACK-01 — the architecture decisions of the production version, as four ADRs and a readiness plan

task_id: PRODUCTION-ADR-PACK-01
status: completed in a development candidate (documents only); round 2 applied (the judge's findings and `R-146o`…`R-146v`)

## Outcome

`ADR-0021`…`ADR-0024`, the `ADR-0014` addendum, the ADR index, `docs/program/PRODUCTION-READINESS-PLAN-01.md` and the report
`docs/program/PRODUCTION-ADR-PACK-01.md` state what the owner decided in `R-146` (`OWNER_RULINGS_2026-09-17.md` section 3.46) as testable architecture,
mark every implementation choice the owner has not made as an `AD-` decision awaiting confirmation, give each commitment a mechanical check, and break the road to the
production release into items with dependencies, hotspot owners, sizes and checks. Every path, operationId, ruling, debt id, migration, test and figure they cite was checked
mechanically against the tree.

## Depends on

- `BETA-STATIC-MATRIX-02` — completed (the static B1–B12 matrix whose facts the ADRs build on; it stays as written).
- `R-146` as recorded by commit `4d7b7c38` (`docs(program): R-146 records the owner's production architecture decisions, accepted risks and refusals`), and round 2 of the same section, `R-146o`…`R-146v`, recorded by commit `1a7f6f65`.

## Frozen inputs

- base: `integration/ar-close-1026` at `4d7b7c38dc8239df6831b2587b71c0d74e8b1ec0`;
- migration head `0032_ar_v3_run_group`; API 92 paths / 104 operations / 300 schemas; 27 error codes; shared contract `1.5.0`; `VERSION` `0.8.1`;
  this task changes no contract and adds no migration;
- rulings: `R-146a`…`R-146v` (the only source of owner decisions in this pack), `R-135` (no complete gate in a code-first lane), `R-141c` (closed beta on test data).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the surface and version figures, the 22 rulings, and the facts the design depends on (no dump in `deploy.sh`, no `access.check` call in the deploy scripts, v3 importing v2, an unread `allow_client_documents`, exact model comparison, no access audit writer, the copy record as receipt, the two restore formats, the must-change flag, the 900-second watchdog)

### P-01 — the surface, the version and the contract version

- captured_at: 2026-10-26
- command: `python3 -I -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(open('VERSION').read().strip(),d['info']['version'],len(d['paths']),sum(1 for p in d['paths'].values() for m in p if m in ('get','post','put','patch','delete')),len(d['components']['schemas']))"`
- captured_output:
  ```text
  0.8.1 1.5.0 92 104 300
  ```
- interpretation: `VERSION` 0.8.1, contract 1.5.0, 92 paths, 104 operations, 300 schemas: the triple `CURRENT_STATE.md` states.

### P-02 — the migration head

- captured_at: 2026-10-26
- command: `ls db/migrations/versions | tail -1`
- captured_output:
  ```text
  20261023_0032_ar_v3_run_group.py
  ```
- interpretation: the head is `0032_ar_v3_run_group`; the pack proposes the next revision (`0033`) and writes none.

### P-03 — the twenty-two rulings the pack quotes

- captured_at: 2026-10-26
- command: `grep -o '^| .R-146[a-v]' docs/program/OWNER_RULINGS_2026-09-17.md | grep -o 'R-146[a-v]' | tr '\n' ' '`
- captured_output:
  ```text
  R-146a R-146b R-146c R-146d R-146e R-146f R-146g R-146h R-146i R-146j R-146k R-146l R-146m R-146n R-146o R-146p R-146q R-146r R-146s R-146t R-146u R-146v
  ```
- interpretation: `R-146a` to `R-146v` exist as table rows of section 3.46 (`R-146o` to `R-146v` are the second poll round, merged in round 2). Every statement the pack attributes to the owner is a paraphrase of one of them.

### P-04 — `deploy.sh` takes no dump

- captured_at: 2026-10-26
- command: `echo "pg_dump lines in deploy.sh: $(grep -c pg_dump infra/deploy/deploy.sh)"; grep -n 'guard: stand-copy-unattested' infra/deploy/deploy.sh`
- captured_output:
  ```text
  pg_dump lines in deploy.sh: 0
  239:# >>> guard: stand-copy-unattested
  245:# <<< guard: stand-copy-unattested
  ```
- interpretation: `deploy.sh` runs no `pg_dump`; its `R-93` guard `stand-copy-unattested` refuses only while an open, unattested copy record exists. `ADR-0021` `AD-03` rests on this.

### P-05 — the deploy scripts do not run the default-credential check

- captured_at: 2026-10-26
- command: `echo "access.check mentions deploy.sh=$(grep -c 'access.check' infra/deploy/deploy.sh) verify-deployed.sh=$(grep -c 'access.check' infra/deploy/verify-deployed.sh) readiness.sh=$(grep -c 'auditmanager.access.check' infra/deploy/readiness.sh)"`
- captured_output:
  ```text
  access.check mentions deploy.sh=0 verify-deployed.sh=0 readiness.sh=3
  ```
- interpretation: only `readiness.sh`, which by `R-46` blocks nothing, runs `auditmanager.access.check`. `ADR-0023` section 3 (`AD-11`) rests on this.

### P-06 — v3 and one recognised module import v2

- captured_at: 2026-10-26
- command: `grep -rln 'profiles.ar_v2' src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised | sort`
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py
  src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py
  src/auditmanager/analysis/profiles/ar_v3/v3_profile.py
  src/auditmanager/analysis/recognised/region_candidate.py
  ```
- interpretation: removing `ar_v2` is not a deletion: six modules outside it import from it. `ADR-0024` `AD-12` orders the extraction before the removal.

### P-07 — nothing reads `allow_client_documents` to refuse a call

- captured_at: 2026-10-26
- command: `grep -rn 'allow_client_documents' src --include=*.py | grep -v 'api/schemas' | cut -c1-110`
- captured_output:
  ```text
  src/auditmanager/executors/operations.py:152:        allow_client_documents=False, timeout_seconds=_DEFAULT_TI
  src/auditmanager/executors/model.py:120:    allow_client_documents: bool
  src/auditmanager/executors/repository.py:45:    "billing, allow_client_documents, timeout_seconds, api_flavour
  src/auditmanager/executors/repository.py:63:    "pin_id", "gateway_model", "billing", "allow_client_documents"
  src/auditmanager/executors/repository.py:78:    if name == "allow_client_documents":
  ```
- interpretation: the flag is set at the import, typed, stored and cast to `boolean` (line 78); no line compares it to anything. The web card shows it. `ADR-0024` `AD-14` rests on this.

### P-08 — the model comparison on the run path is exact

- captured_at: 2026-10-26
- command: `grep -n 'reported != expected' src/auditmanager/analysis/text/stage.py; grep -n 'response.model != call.expected_model' src/auditmanager/runs/v3_provider_call.py`
- captured_output:
  ```text
  283:    elif not isinstance(reported, str) or reported != expected:
  279:    if mode is ProviderMode.LIVE and response.model != call.expected_model:
  ```
- interpretation: both run-path comparisons are string inequality with no alias list; `ProxySettings.model_aliases` is never set by `src/` (P-12). `ADR-0024` `AD-13` rests on this.

### P-09 — no access code writes `audit_event`

- captured_at: 2026-10-26
- command: `echo "access files naming audit_event: $(grep -rl audit_event src/auditmanager/access | wc -l)"`
- captured_output:
  ```text
  access files naming audit_event: 0
  ```
- interpretation: sign-in, role grant and password change leave no audit record today; `ADR-0023` section 4 (`AD-10`) adds one.

### P-10 — the live journey drives an АР run

- captured_at: 2026-10-26
- command: `grep -n 'upload the AR portal bundle' tests/e2e/pc01/journey/journey.mjs | cut -c1-120`
- captured_output:
  ```text
  33: * upload the AR portal bundle, start a run, wait for the run's terminal -- is `write.mjs`, driven
  ```
- interpretation: removing АР v1 breaks the live journey; `PROD-10` re-bases it first.

### P-11 — the executor payload clearing runs inside a runner's claim call

- captured_at: 2026-10-26
- command: `grep -n 'PAYLOAD_RETENTION_DAYS' src/auditmanager/executors/runner.py | tail -2`
- captured_output:
  ```text
  99:PAYLOAD_RETENTION_DAYS: Final[int] = 7
  377:                    session, older_than_days=PAYLOAD_RETENTION_DAYS, limit=20)
  ```
- interpretation: the only automatic retention in the code is called from the claim path (line 377 is inside the loop of `claim`); a stand without a polling runner never runs it. `ADR-0022` section 2 says so.

### P-12 — no `model_aliases` is ever passed

- captured_at: 2026-10-26
- command: `echo "ProxySettings( in composition.py: $(grep -c 'ProxySettings(' src/auditmanager/bootstrap/composition.py); model_aliases= in src: $(grep -rn 'model_aliases=' src | wc -l)"`
- captured_output:
  ```text
  ProxySettings( in composition.py: 1; model_aliases= in src: 0
  ```
- interpretation: the one served construction of `ProxySettings` passes no aliases, and nothing in `src/` assigns the field.

### P-13 — the copy key's record already is a receipt (round 2)

- captured_at: 2026-10-26
- command: `grep -n 'set_rec dump \|quiesced_at' infra/deploy/copy-serve.sh | cut -c1-110 | head -4`
- captured_output:
  ```text
  496:        quiesced_at null \
  515:    set_rec quiesced_at "\"$(fc_now)\""
  643:    set_rec dump "{\"file\": \"db.dump\", \"size_bytes\": $size, \"sha256\": \"$sha\"}"
  755:        if ! window_open_since "$(rec_str quiesced_at)"; then
  ```
- interpretation: `dump-db` writes the dump's file, size and SHA-256 and the quiesce time into the record, which is the file, SHA-256 and time `R-146t` asks for; `ADR-0021` section 5 uses it instead of a new script.

### P-14 — the two restore formats differ and the copy key's restore drops the grants (round 2)

- captured_at: 2026-10-26
- command: `grep -n 'for required in' infra/deploy/reset.sh; grep -n 'DROP SCHEMA IF EXISTS public' infra/deploy/copy-serve.sh | cut -c1-90; grep -c 'no-privileges' infra/deploy/reset.sh infra/deploy/copy-serve.sh infra/deploy/purge-product-data.sh`
- captured_output:
  ```text
  236:    for required in "$RESTORE/database.dump" "$RESTORE/objects.attrs" "$RESTORE/objects"; do
  931:    psql_stand --command "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;
  infra/deploy/reset.sh:1
  infra/deploy/copy-serve.sh:2
  infra/deploy/purge-product-data.sh:1
  ```
- interpretation: `reset.sh --restore` needs a directory with `database.dump`, `objects.attrs` and `objects`; `copy-serve.sh restore-db` consumes a PostgreSQL-only dump after recreating the schema, and every dump tool uses `--no-privileges`. `ADR-0021` sections 3 and 6 follow.

### P-15 — an administrator's password reset marks the account must-change (round 2)

- captured_at: 2026-10-26
- command: `grep -n 'is_default_credential = true' src/auditmanager/access/accounts.py`
- captured_output:
  ```text
  201:        is_default_credential = true,
  ```
- interpretation: `access.check` lists every account with that flag, so the gate of `R-146s` also fires for a temporary password; this is `AD-19`.

### P-16 — the attempt watchdog is 900 seconds (round 2)

- captured_at: 2026-10-26
- command: `grep -n 'ATTEMPT_WATCHDOG_SECONDS = ' src/auditmanager/jobs/lease.py`
- captured_output:
  ```text
  21:ATTEMPT_WATCHDOG_SECONDS = 900
  ```
- interpretation: an attempt is failed at 900 seconds while the deterministic stages of a 500-page set take 722 seconds (`D-171`); `AD-18`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/architecture/adr/ADR-0021-production-topology-and-operations.md`
- `docs/architecture/adr/ADR-0022-production-data-governance.md`
- `docs/architecture/adr/ADR-0023-production-identity-and-access.md`
- `docs/architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md`
- `docs/architecture/adr/ADR-0014-authz-classification-retention.md`
- `docs/architecture/adr/ADR-0012-expert-decision-ledger-and-kb-projection.md` (an addendum only, round 2)
- `docs/architecture/ADR_INDEX.md`
- `docs/program/PRODUCTION-READINESS-PLAN-01.md`
- `docs/program/tasks/PRODUCTION-ADR-PACK-01.md`
- `docs/program/PRODUCTION-ADR-PACK-01.md`

## Forbidden hotspots

Everything else. In particular `docs/program/DEBT_REGISTER.md` and `docs/program/CURRENT_STATE.md` (the integrator enters the proposed rows), `docs/program/OWNER_RULINGS_2026-09-17.md`,
`contracts/**`, `db/migrations/**`, root dependency and lock files, `Makefile`, `infra/**`, `.github/**`, global styles, the composition roots, `src/**`, `web/**`, `scripts/**`, `tests/**`,
refs, tags, `origin/main` and any stand.

## Non-goals

No code, test, contract (the frozen domain-contract sentence the erase exception names is left to `PROD-22`), migration, script, workflow or compose change; no stand, container, battery, gate, live journey or paid call; no decision attributed to the owner that `R-146` does not
contain; no `PASS` for any criterion; no change to the register, to `CURRENT_STATE.md` or to the ruling record; no push, tag or `origin/main` update.

## Deliverables

- the four ADRs, with a table of commitments and mechanical checks in `ADR-0021`, `ADR-0023` and `ADR-0024`;
- the `ADR-0014` and `ADR-0012` addenda and the index rows;
- `docs/program/PRODUCTION-READINESS-PLAN-01.md`;
- `docs/program/PRODUCTION-ADR-PACK-01.md`, whose last section proposes the debt-register rows;
- this task file.

## Required tests

- command: `PYTHONPATH=src:$BS python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/PRODUCTION-ADR-PACK-01.md',encoding='utf-8').read())))"`
- expected: prints `[]`
- command: `git diff --check`
- expected: exit 0, no output
- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: no failure that the base tree does not already have (the results are in the Handoff)
- command: `python3 -I <scratchpad>/pa/check_docs.py . <the nine files>`
- expected: ends `N checked, 0 missing, 0 unclassified` (the existence check, kept outside git)

## Integration contract

The integrator may merge this lane at any point: it reads `CURRENT_STATE.md` and `DEBT_REGISTER.md` and writes neither, edits no code, and its only shared file is `docs/architecture/ADR_INDEX.md`. After the merge the integrator
(1) polls the owner on the `AD-` decisions and open questions of `PRODUCTION-READINESS-PLAN-01.md` sections 7 (`PROD-00`), (2) records the answers as a ruling, (3) enters the proposed rows of the report into the register with their ids, and
(4) dispatches `PROD-` items only after the `AD-` decisions they depend on are confirmed. If the debt register changes state after this task, the existence check (re-run it) and the `(closed)` or open statements in the ADRs are the places to look.
The ADRs record the state of 2026-10-26 on tree `4d7b7c38`.

## Failure/idempotency/security cases

Documents only. A stale citation is the failure mode; the existence check is the defence and its mutation proofs are in the Handoff. A statement attributed to the owner that `R-146` does not make would be a defect:
every owner decision is cited through its `R-146` row and every other choice is an `AD-` id. The ADRs contain no secret, credential, host address or personal data.

## Rollback / feature flag

Forward revert of the nine files. Behaviour is unchanged.

## Handoff

- changed files: the ten files of the allowed paths, on branch `agent/production-adr-pack-01` from base `4d7b7c38dc8239df6831b2587b71c0d74e8b1ec0`, merged with `integration/ar-close-1026` at `1a7f6f65` in round 2; nothing else (`git diff --name-only 1a7f6f65 HEAD` lists exactly them).
- commands/results (2026-10-26, lane worktree production-adr-pack-01, on the committed tree): see the report's Checks section for the existence check (the final line), its 14 mutations, the governance one-liner (`[]`), `git diff --check` (exit 0), the 105 passed tests and the unchanged failing set of the two ADR-index test files.
- round 2: the report's "Round 2" section gives, per judge finding 1-13 and gap G1-G3, `fixed` with the document and section, or `refuted` with the evidence, and applies `R-146o`…`R-146v`. New decisions `AD-17`, `AD-18`, `AD-19`; new items `PROD-19`…`PROD-22`; new accepted risk `A-5`; no migration is proposed any more.
- known limits: nothing was executed against a stand, a container or a database; a check marked "no" in an ADR table does not exist yet; thirteen `AD-` decisions are unconfirmed; the sizes in the plan are counted, not experienced; the local tracking refs were not fetched; the whole contract battery, the web battery and the gate were not run (`R-135`).
- integration notes: see the integration contract above and the report's "Instruction to the integrator".
