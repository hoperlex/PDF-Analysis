# Task PROD-07A-PROJECT-ERASE-CORE-01 — the operator tool that erases one project

task_id: PROD-07A-PROJECT-ERASE-CORE-01
status: completed in development candidate (the core; the shell wrapper `infra/deploy/erase-project.sh` is a later lane)

## Outcome

`scripts/recovery/project_erase.py` erases ONE project as `ADR-0022` section 3 defines it: its documents, versions, manifest entries, runs, jobs, attempts, model-call records, artifacts, findings, evidence quotes, comments and expert decisions are removed together with the idempotency receipts of those rows and every Blob no other project and no corpus table references, with its object (`R-146o`, the deliberate exception to `ADR-0012`). Dry run by default; the apply is given back the SHA-256 of the plan it was shown and refuses a plan whose data no longer matches; four phases with `--resume` after a crash; `erasure.requested` and `erasure.completed` in `audit_event` with identities, counts and digests only; erased `blob` rows are deleted and a manifest digest is in the completion event; a byte-identical re-upload succeeds. It refuses to apply or resume without `--owner-permission-ref` (`R-146aj`) and records it.

## Depends on

- `PROD-06-ACCESS-AUDIT-01` — completed (the `access.` keep prefix; this task adds the second prefix to the same tuple).
- `ADR-0022` section 3, `ADR-0012` addendum, `R-146c`, `R-146o`, `R-146aj` — accepted.
- `PROD-04` (the owner role and the migrator URL) is not a dependency of the core: the tool refuses any role that does not own the tables, exactly as `product_purge.py` does; the wrapper that passes the migrator's URL is the later lane.

## Frozen inputs

- domain contract: not_applicable (`ErasureRequest` / `era_` and the Blob state machine are used as frozen; `contracts/**` is not touched)
- API contract: not_applicable (an operator tool; no route)
- analysis/comparison/event contract: not_applicable (the event envelope has no list of event types)
- migration head: unchanged (`0033_ar_v3_cite_stage_id`, `schema_coverage.HEAD`); no table is added
- base commit: `8453869731599e8f5815efb919859bd0159c9342` (`integration/ar-close-1026`), branch `agent/prod-07a-project-erase-core-01`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: scripts/recovery/product_purge.py
- enumerator_owner: PROD-07A-PROJECT-ERASE-CORE-01 (the plan makes the `product_purge.py` chain serial: `PROD-06` then `PROD-07`; the edit is one prefix)
- totality_query: `python3 -I -c "import re,pathlib as p;t=p.Path('scripts/recovery/product_purge.py').read_text();k=re.search(r'KEEP_EVENT_PREFIXES = \((.*?)\)',t).group(1);q=re.search(r'PRODUCT_EVENT_PREFIXES = \((.*?)\)',t,re.S).group(1);pre=tuple(re.findall(r'\"([a-z_.]+)\"',k+q));ev=set();[ev.update(re.findall(r'event_type\s*=\s*\"([a-z_][a-z0-9_.]*)\"',f.read_text())) for f in p.Path('src').rglob('*.py')];ev.update(re.findall(r'EVENT_(?:REQUESTED|COMPLETED) = \"([a-z_.]+)\"',p.Path('scripts/recovery/project_erase.py').read_text()));print(sorted(e for e in ev if not e.startswith(pre)))"`

The set is the `audit_event.event_type` families the purge tool has classified. This task adds `erasure.` to the keep side. The query lists every `event_type="..."` literal under `src/` and the two event constants of the erase tool that start with no classified prefix, and prints `[]`.

## Captured premise evidence

- premise: ten reads of the plan, the ADRs, the rulings and the schema, re-run on the base commit; none disagrees materially (P-10 states the three places where the ADR is silent and what was chosen)

### P-01 — the ADR's phase design, guards and idempotency sentences are where the plan says they are
- captured_at: 2026-10-26
- command: `grep -n "Phases (\|^\*\*Guards\|A crash after phase 2\|Re-running a finished erase" docs/architecture/adr/ADR-0022-production-data-governance.md | cut -c1-200`
- captured_output:
  ```text
  147:**Phases (`AD-07`).** The external side effect (object deletion) must not be a dual write
  159:A crash after phase 2 leaves Blobs in `erasure_pending` and nothing referencing them; the same command
  160:with `--resume era_<ULID>` completes phases 3 and 4. Re-running a finished erase finds
  164:**Guards.** The project exists and no run, job, attempt or executor task of it is non-terminal (a
  ```
- interpretation: Phases 1 to 4, the crash/resume sentence, the finished-erase sentence and the guard list are present at the lines the lane read in full. The tool follows them; the three places they are silent are P-10.

### P-02 — the three owner rulings the tool implements
- captured_at: 2026-10-26
- command: `grep -n -o "^| .R-146\(c\|o\|aj\). | [^.]*\.[^.]*\." docs/program/OWNER_RULINGS_2026-09-17.md | cut -c1-330`
- captured_output:
  ```text
  1761:| `R-146c` | **Retention.** Chosen: «Без автоочистки + стирание проекта оператором».
  1773:| `R-146o` | **Scope of the project erase.** Chosen: «Всё, включая замечания и решения» (recommended).
  1794:| `R-146aj` | **Legal hold.** Chosen: «Оператор не стирает проект без вашего разрешения» (recommended).
  ```
- interpretation: `R-146c` (no automatic retention, a journalled operator erase of one project), `R-146o` (everything including findings, evidence quotes, comments and expert decisions; a deliberate exception to `ADR-0012`), `R-146aj` (the operator never erases a project without the owner's permission; no legal-hold mechanism in 1.0). The lines are cut at 330 characters for the record.

### P-03 — the ADR-0012 addendum names this operation, its mechanism and its record
- captured_at: 2026-10-26
- command: `sed -n 8,12p docs/architecture/adr/ADR-0012-expert-decision-ledger-and-kb-projection.md | cut -c1-200`
- captured_output:
  ```text
  ## Addendum — amended by R-146o for the operator project erase only (2026-10-26)

  Recorded by `PRODUCTION-ADR-PACK-01` under owner ruling `R-146o` (`OWNER_RULINGS_2026-09-17.md` section 3.46). The text above
  stays as written and stays true for every path of the product: a verdict change creates a new immutable event, and no API
  operation, screen or job deletes or rewrites an expert decision event.
  ```
- interpretation: The addendum (lines 8 to 22) says the exception is the operator script switching the append-only trigger off inside one transaction, that what stays is the `erasure.requested` / `erasure.completed` pair and a manifest, and that "Nothing exists yet: the tool is not written".

### P-04 — the purge tool's classification (32 PRODUCT, 29 KEEP, 3 MIXED), its 27 guard blocks, its keep tuple and its owner guard
- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -c "from scripts.recovery import product_purge as p;print(len(p.PRODUCT_TABLES),len(p.KEEP_TABLES),len(p.MIXED_TABLES))"` and `git show 84538697:scripts/recovery/product_purge.py | grep -c '# >>> guard'`
- captured_output:
  ```text
  32 29 3
  27
  132:KEEP_EVENT_PREFIXES = ("norm_custody.", "executor.", "access.")
  352:    # >>> guard: owner-may-write
  358:           AND NOT pg_catalog.pg_has_role(current_user, c.relowner, 'MEMBER')
  366:    # <<< guard: owner-may-write
  ```
- interpretation: The declaration the erase reuses (`PRODUCT_TABLES`, `KEEP_TABLES`, `MIXED_TABLES`, `classification_problems`, `PRODUCT_COMMAND_TYPES`, the Blob-column helpers) is closed and has 27 guard blocks at the base; the keep tuple was `("norm_custody.", "executor.", "access.")` (the edit adds `erasure.`); `owner-may-write` is `pg_has_role(current_user, relowner, 'MEMBER')` over the tables the tool writes, which the erase repeats over the tables it writes.

### P-05 — the foreign-key closure from `project`, read from the live catalog by an independent recursive query
- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -c "import os,textwrap;from sqlalchemy import create_engine,text;c=create_engine(os.environ['DATABASE_URL']).connect();n,names=c.execute(text(\"WITH RECURSIVE t(n) AS (SELECT 'project'::text COLLATE \\\"C\\\" UNION SELECT child.relname::text FROM pg_constraint k JOIN pg_class child ON child.oid=k.conrelid JOIN pg_class par ON par.oid=k.confrelid JOIN t ON t.n=par.relname WHERE k.contype='f' AND child.relnamespace='public'::regnamespace) SELECT count(*), string_agg(n, ' ' ORDER BY n) FROM t\")).one();print(n);print(textwrap.fill(names,100))"`
- captured_output:
  ```text
  31
  analysis_artifact_publication ar_v3_run_group ar_v3_run_group_member attempt audit_run document
  document_version document_version_classification document_version_classification_correction
  executor_task expert_decision_event finding finding_evidence finding_observation
  finding_observation_norm_citation input_manifest_entry job lease model_call optimisation_pass
  optimisation_proposal optimisation_proposal_decision price_list_position price_list_revision project
  provider_call_effect stage_result vendor_list_entry vendor_list_revision work_assignment
  work_assignment_event
  ```
- interpretation: 31 of the 32 PRODUCT tables are reachable from `project` by foreign key; the one that is not is `worker` (the ADR says it is not project-scoped). No KEEP or MIXED table is in the closure. The tool derives this closure at run time (`load_closure`) and refuses a database where it differs (`closure-is-product`); the test file compares it with a hand-written addressing of the same 31 tables.

### P-06 — the Blob-reference columns and the Blob state machine
- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -c "from scripts.recovery.blob_reference_audit import _CATALOG_EXPECTED as e;print(len(e));print(sorted((t,c) for _,t,c in e))"` and a `select from_state, to_state from contract_state_transition where machine='blob'`
- captured_output:
  ```text
  8
  [('analysis_artifact_publication', 'blob_id'), ('blob', 'blob_id'), ('input_manifest_entry', 'blob_id'), ('norm_custody_admission', 'blob_id'), ('norm_custody_binding', 'blob_id'), ('norm_retrieval_set', 'catalogue_blob_id'), ('norm_retrieval_set', 'set_blob_id'), ('price_list_revision', 'blob_id')]
  [(None, 'temporary'), ('available', 'erasure_pending'), ('erasure_pending', 'available'), ('erasure_pending', 'erased'), ('temporary', 'rejected'), ('temporary', 'verifying'), ('verifying', 'available'), ('verifying', 'rejected')]
  ```
- interpretation: Eight reference columns in a closed set: three PRODUCT-side (`analysis_artifact_publication`, `input_manifest_entry`, `price_list_revision`) and four KEEP-side (`norm_custody_admission`, `norm_custody_binding`, `norm_retrieval_set` twice), plus the `blob` key itself. A Blob becomes `erasure_pending` only from `available`; the terminal `erased` is reachable only from `erasure_pending`, and the ADR chooses not to use it (the row is deleted).

### P-07 — the triggers that fire on DELETE of a closure table
- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -c "..."` (a `pg_trigger` query with `tgtype & 8` over the 31 closure tables)
- captured_output:
  ```text
  [('am_append_only', 1), ('am_immutable_row', 19)]
  ```
- interpretation: Nineteen `am_immutable_row` triggers and the one `am_append_only` (on `expert_decision_event`) are the only DELETE guards on the closure; no other function fires on DELETE there. The tool switches off exactly these two functions, one named trigger at a time, and refuses a closure table that carries any other DELETE trigger (`delete-triggers-known`).

### P-08 — how object deletion is recorded today: nowhere; the storage port has no delete
- captured_at: 2026-10-26
- command: `grep -rn "erasure_pending\|ERASURE_PENDING\|\.delete_object(\|BlobState.ERASED" src scripts --include=*.py | grep -v "scripts/recovery/project_erase.py" | cut -c1-175`
- captured_output:
  ```text
  src/auditmanager/storage/blob_repository.py:120:        return self.state in (BlobState.AVAILABLE, BlobState.REJECTED, BlobState.ERASED)
  src/auditmanager/storage/s3.py:557:        Erasure of real content is an ``erasure_pending -> erased`` transition
  src/auditmanager/storage/s3.py:579:            self._client.delete_object(Bucket=self._bucket, Key=key)
  scripts/recovery/product_purge.py:817:            client.delete_object(Bucket=bucket, Key=item.key)
  src/auditmanager/storage/models.py:167:    ``-> rejected`` guards. ``erasure_pending`` and ``erased`` are declared so
  src/auditmanager/storage/models.py:176:    ERASURE_PENDING = "erasure_pending"
  scripts/recovery/blob_reference_audit.py:177:            "temporary", "verifying", "available", "rejected", "erasure_pending", "erased"
  ```
- interpretation: The states exist in the vocabulary and no code writes `erasure_pending` or `erased`; `S3BlobStore._purge_published` is a private cleanup helper "not part of the port"; the only object deletion of a whole project's data is `product_purge.py` by exact key. The erase therefore deletes through a boto3 client with the purge's exact-key discipline and records the deletion only in the two events (counts) and the manifest (identities and hashes).

### P-09 — what a command receipt's outcome names (the link between a project and its receipts)
- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -c "..."` (`select command_type, count(*) from command_record group by 1` and the keys of each type's `outcome`)
- captured_output:
  ```text
  [('append_decision', 3), ('create_project', 2), ('start_audit_run', 5), ('start_optimisation_pass', 1), ('upload_price_list', 1), ('upload_source_document', 5)]
  [('append_decision', 'decision_id'), ('create_project', 'project_uid'), ('start_audit_run', 'run_id'), ('start_optimisation_pass', 'optimisation_pass_id'), ('upload_price_list', 'blob_id,price_list_id'), ('upload_source_document', 'blob_id,version_uid')]
  ```
- interpretation: A receipt names the identity of what it created (`project_uid`, `run_id`, `version_uid`, `decision_id`, `optimisation_pass_id`, `price_list_id`) and no project; `audit_run`, `ar_v3_run_group`, `expert_decision_event` and `optimisation_proposal_decision` also hold a `command_id` foreign key. So the receipts of a project are found by both: by foreign key from its rows, and by an outcome that names the identity of one of its rows. Left behind, a receipt refuses the same idempotency key for the project that comes back (`idempotency_key_reuse`).

### P-10 — the ADR against the schema: no material disagreement; three places the ADR is silent
- captured_at: 2026-10-26
- command: `git diff --name-only 8453869731599e8f5815efb919859bd0159c9342..HEAD -- docs/architecture db contracts`
- captured_output:
  ```text
  (no output)
  ```
- interpretation: The lane edits no ADR, no migration and no contract (the command prints nothing). The ADR's scope, phases, guards, journal keys and "what it keeps" match the schema read in P-04 to P-09. Silent places: (1) how a receipt is tied to a project (P-09 answers it); (2) a Blob only this project references that is not `available` (a failed or abandoned upload bound by an `abandoned` publication) cannot enter `erasure_pending` under the state machine; the tool refuses such a project and names the Blobs, an owner/ADR question is listed; (3) the staged `temporary/` objects named by a project's publication rows are not Blobs; the tool deletes them too and keeps their list in `plan.json`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/recovery/project_erase.py`
- `scripts/recovery/product_purge.py`
- `scripts/recovery/schema_coverage.py`
- `tests/integration/recovery/test_project_erase.py`
- `tests/integration/recovery/test_project_erase_shapes.py`
- `tests/unit/recovery/**`
- `docs/program/tasks/PROD-07A-PROJECT-ERASE-CORE-01.md`
- `docs/program/PROD-07A-PROJECT-ERASE-CORE-01.md`

`product_purge.py` is edited at its keep tuple and the comment above it, nothing else (no guard block is touched). `schema_coverage.py` is not edited: its inventory (tables, triggers, Blob columns) is unchanged because no table is added.

## Forbidden hotspots

`contracts/**`, `db/**` and the migration head, `src/**`, `infra/**` (the wrapper `infra/deploy/erase-project.sh` waits for the database-role work), `web/**`, the ADRs, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, root dependency and lock files, every composition root, every other test file.

## Non-goals

- The shell wrapper `infra/deploy/erase-project.sh` and the runbook text (the report states exactly what the wrapper must do).
- Any API route, screen or job that erases (rejected by the ADR, alternative 4).
- A dump before the erase: it would keep the erased data (the wrapper must not take one).
- Reaching copies, mirrors, the provider's side or the disk blocks of a deleted object (the tool's closing message says so).
- A legal-hold mechanism (`R-146aj`: a procedure, not a feature).
- Erasing the identity-only run journal (`audit_event` rows of the project's runs stay, `R-146w`).

## Deliverables

- `scripts/recovery/project_erase.py` (the module and its CLI), `erasure.` in `KEEP_EVENT_PREFIXES`.
- `tests/integration/recovery/test_project_erase.py`, `test_project_erase_shapes.py`, `tests/unit/recovery/test_project_erase_pure.py`.
- Report `docs/program/PROD-07A-PROJECT-ERASE-CORE-01.md`: the guard table (44 guards, each shown failing), the mutation table of the behaviours that are not guards, the decisions of the lane, what the wrapper must do, the integration notes and the limits.

## Required tests

- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/recovery` — expected: 81 passed.
- command: the same with `tests/integration/recovery/test_project_erase.py` on the integration lane stack — expected: 128 passed.
- command: the same with `tests/integration/recovery/test_project_erase_shapes.py` — expected: 3 passed.
- command: the same with `tests/integration/recovery/test_product_purge.py tests/integration/recovery/test_product_purge_executor_events.py tests/integration/recovery/test_product_purge_run_group.py tests/integration/recovery/test_schema_coverage.py tests/unit/runs/test_executor_choice.py` — expected: 123 passed (the edited tool's own suites, unchanged); `test_product_purge_script.py`: 7 passed.
- command: the same with `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on a committed tree — expected: as on the base.
- command: `git diff --check` — expected: exit 0.
- mutations: every guard block deleted from a copy of the source (44), sixteen edits of the behaviour that is not a guard, and the test-level mutations of the second-apply path, the re-upload, the receipts and the isolation check — each goes red and green again after the revert (the tables are in the report).

## Integration contract

The integrator can rely on: `python -m scripts.recovery.project_erase` with `--database`, `--bucket` (typed, equal to the connected ones), `--project prj_...` prints a plan and its `plan-sha256` and changes nothing; `--apply --plan-sha256 <that> --actor <admin login> --reason <client_request|end_of_engagement|test_data|other> --owner-permission-ref "<text>" --dump-dir DIR` erases exactly that plan or refuses with exit 3 and nothing changed; a failure after the commit exits 4, prints `erase-id: era_...` and is finished by `--resume era_... --actor ... --owner-permission-ref ... --dump-dir DIR`; a repeat of a finished erase exits 0 with "nothing to do". `DIR/<era_id>/plan.json` and `manifest.json` are written before the commit; `sha256sum manifest.json` is the `manifest_sha256` of both events. `product_purge.py` keeps the `erasure.` events. Exit codes: 0, 2, 3, 4 as in the purge. The tool needs `scripts/recovery/{project_erase,product_purge,schema_coverage,blob_reference_audit}.py` together and `PYTHONPATH` with `src` and the directory that holds `scripts/`.

## Failure/idempotency/security cases

Refused before the commit with nothing changed: every guard of the report's table. After the commit: a crash before the objects, between the objects and the finish, or in the finish leaves `erasure_pending` Blobs and nothing referencing them, and `--resume` completes; a second resume says "already complete". A byte-identical upload between phase 2 and phase 4 is refused by the Blob state machine (`erasure_pending` cannot become `verifying`) and succeeds after the finish. Client text never reaches an event, the manifest or the plan file (a test scans them for the project's names, file names, quotes and comments). The one free-text field is the operator's permission reference (one line, at most 200 characters), recorded as given.

## Rollback / feature flag

Not applicable to the tool (it runs only when an operator starts it). Forward-revert of the code leaves the written events; the purge of the reverted tree would then refuse `erasure.*` as unclassified. The erase itself is irreversible except from a copy (`ADR-0022` consequences).

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: Blobs only this project references that are not `available` stop the erase; the KEEP-table fingerprint inside the transaction scales with the corpus; the wrapper, the runbook text and the rehearsal on a restored copy (`PROD-17`) are not in this lane
- integration notes: merge after `PROD-06`; the wrapper lane (`PROD-07` second half) depends on `PROD-04`; `schema_coverage.HEAD` must move with each migration or the tool refuses (`head-is-declared`)
