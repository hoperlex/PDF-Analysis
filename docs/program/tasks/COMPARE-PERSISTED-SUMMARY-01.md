# Task COMPARE-PERSISTED-SUMMARY-01 — the comparison of two versions becomes a record: approved sheet pairings, sealed raw differences, an AI summary on top

task_id: COMPARE-PERSISTED-SUMMARY-01
status: delivered, B1 and B2 both (branch `agent/compare-persisted-summary-01`, not merged, not pushed). Lane B of wave PW4; the design and the report are in `docs/program/COMPARE-PERSISTED-SUMMARY-01.md`.

## Outcome

An expert approves (and withdraws) a sheet pairing of two versions of one set: one append-only table (migration `0035_comparison_records`) holds the approval by version ids, page coordinates and content digests, the actor, the time and the `raw_evidence_seal` of the approved set; `compareDocumentVersions` returns the approved pairs and, for approved pairs only, the deterministic text differences of `raw_text.diff_approved_pairs`, sealed by `raw_evidence_seal` (B1). A command, never a read, generates an AI summary over the approved pairs from `summary_input`'s bounded input through a port with a recorded implementation; the summary is stored append-only, references hunks that must exist, never alters the raw differences and is shown with the label «Сводка подготовлена моделью, проверка человеком не проводилась» (B2). Owner's `C-2`.

## Depends on

- `W59-VERSION-COMPARE-01`, `W59-DECISION-CARRYOVER-01`, `W59-INT-RAW-EVIDENCE-SEAL-PREP-01`, `W59-INT-SHEET-MATCH-SUGGESTIONS-02`, `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed (the modules read and extended).
- `PROD-06-ACCESS-AUDIT-01` — completed (the audit-event idiom).
- `OPT-PROJECT-ALL-SECTIONS-01` — completed and merged (migration `0034`, the contract reseal this lane follows).

## Frozen inputs

- domain contract: `contracts/domain/v1/error-codes.json` 1.7.0; prose only (the `analysis_input_budget_exceeded` text per the integrator's message of 2026-10-27, and the new conflict reasons and dependency class in the notes); no new code
- API contract: `contracts/api/v1/openapi.json` 1.7.0 (92 paths, 104 operations, 301 schemas) at the base; this task adds operations and schemas as sealed content under 1.7.0 (a minor bump is outside the grant, see P-10)
- analysis/comparison/event contract: not_applicable (`contracts/comparison/v1/README.md` names the conceptual separation this task implements; it is not edited)
- migration head: `0034_pass_scope_all_sections` at the base; this task moves it to `0035_comparison_records`
- base commit: `3561e1c8` (tip of `integration/ar-close-1026` at launch; contains the merged lane OP)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: COMPARE-PERSISTED-SUMMARY-01 (sole owner of the contract, the migration head and `bootstrap/adapters.py` in wave B of PW4)
- totality_query: `PYTHONPATH=src:$BS .venv/bin/python -c "from auditmanager.shared.db.migrations import head_revision; print(head_revision())"` and `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(len(d['paths']),sum(1 for v in d['paths'].values() for o in v.values() if isinstance(o,dict) and 'operationId' in o),len(d['components']['schemas']))"`

## Captured premise evidence

- premise: nothing persists a pairing or a summary; the pure modules take exactly the identities this task allocates; the comparison is served read-only; the grants, purge, erase, head and contract pins are the files listed below; the access rule and audit idiom are the precedents named. One constraint found: the contract version cannot move inside the grant (P-10), and the account-reference register is outside it (design note, section 0).

### P-01 — the comparison package, its README note and the tests that exist
- captured_at: 2026-10-27
- command: `ls src/auditmanager/comparison tests/unit/comparison tests/integration/comparison && wc -l src/auditmanager/comparison/*.py | tail -1 && tail -n 8 src/auditmanager/comparison/README.md`
- captured_output:
  ```text
  src/auditmanager/comparison:
  carryover.py
  decision_carryover.py
  finding_match_suggestions.py
  public.py
  __pycache__
  raw_evidence_seal.py
  raw_text.py
  README.md
  read_model.py
  service.py
  sheet_match_suggestions.py
  summary_input.py
  version_reader.py
  version_section_pair.py

  tests/integration/comparison:
  conftest.py
  test_decision_carryover_db.py
  test_decision_carryover.py
  test_finding_match_suggestions.py
  test_raw_evidence_seal.py
  test_raw_text.py
  test_service_db.py
  test_sheet_match_suggestions.py
  test_summary_input.py
  test_version_reader.py
  test_version_section_pair.py

  tests/unit/comparison:
  __pycache__
  test_finding_matches_on_sheet_suggestions.py
  test_sheet_pairs_and_line_diff.py
  test_stage_section_pair.py
  test_version_comparison_service.py
    3543 total

  Other contexts use `public.py` only. `W59-VERSION-COMPARE-01` serves a read-only comparison of
  two versions of one set through `service.VersionComparisonService`: its two ports
  (`VersionClassificationReader`, `VersionAnalysisReader`) are adapted by the composition root,
  and its read model (`read_model.py`) holds proposals only — no SheetLink, finding match,
  decision or AI artifact is written. The approved-link modules (`raw_text.diff_approved_pairs`,
  `raw_evidence_seal`, `summary_input`, `decision_carryover`) stay for the later persisted
  comparison.
  ```
- interpretation: The package holds the pure modules (`raw_text`, `raw_evidence_seal`, `summary_input`, `sheet_match_suggestions`, `decision_carryover`) and the served read (`service`, `read_model`, `carryover`). The README says the approved-link modules «stay for the later persisted comparison»: nothing persists them today.

### P-02 — nothing stores an approved pairing or a summary at head (the roadmap-gap premise, re-run)
- captured_at: 2026-10-27
- command: `grep -il 'sheet_link\|comparison_revision\|approved_pair\|sheetlink' db/migrations/versions/*.py; echo "grep exit=$?"; grep -il 'comparison_' db/migrations/versions/*.py; echo "grep exit=$?"; grep -n 'class ComparisonId\|class SheetLinkId' src/auditmanager/shared/identity/ids.py`
- captured_output:
  ```text
  grep exit=1
  grep exit=1
  306:class ComparisonId(OpaqueId, prefix="cmp", entity="Comparison"):
  310:class SheetLinkId(OpaqueId, prefix="sln", entity="SheetLink"):
  ```
- interpretation: Both greps print nothing (exit 1): no table names a sheet link, comparison revision or approved pair. The identities `cmp_` (ComparisonId) and `sln_` (SheetLinkId) are declared and "not allocated in PC-01"; this lane allocates them.

### P-03 — the operation and its handler: one GET and one write beside it
- captured_at: 2026-10-27
- command: `grep -rn 'compareDocumentVersions\|carryOverDecision' src/auditmanager --include=*.py | cut -c1-170`
- captured_output:
  ```text
  src/auditmanager/bootstrap/adapters.py:2883:    """``compareDocumentVersions`` (`W59-VERSION-COMPARE-01`).
  src/auditmanager/decisions/carryover.py:85:#: The comparison modes of ``compareDocumentVersions``, and how the provenance names them.
  src/auditmanager/api/routers/ports.py:1033:    """``compareDocumentVersions`` and ``carryOverDecision``. `W59-VERSION-COMPARE-01`,
  src/auditmanager/api/routers/comparison.py:1:"""``compareDocumentVersions`` (`W59-VERSION-COMPARE-01`) and ``carryOverDecision``
  src/auditmanager/api/routers/comparison.py:20:**The one write beside it** is ``carryOverDecision``: an expert confirms carrying one source
  src/auditmanager/api/routers/comparison.py:79:        operation_id="compareDocumentVersions",
  src/auditmanager/api/routers/comparison.py:130:        operation_id="carryOverDecision",
  src/auditmanager/api/app.py:220:    ``compareDocumentVersions`` (a required query and paging bounds) joined it, and
  src/auditmanager/api/app.py:223:    joined it; `W59-DECISION-CARRYOVER-01`'s ``carryOverDecision`` (a closed body)
  src/auditmanager/api/security.py:388:        "compareDocumentVersions": _ANY_ROLE,
  src/auditmanager/api/security.py:436:        "carryOverDecision": _EXPERT,
  src/auditmanager/api/schemas/models.py:2374:    nothing: only ``carryOverDecision``, confirmed by an expert, does."""
  ```
- interpretation: `compareDocumentVersions` (GET) and `carryOverDecision` (POST, `_EXPERT`) are served by `ComparisonPort` / `ComparisonAdapter`; the adapter proves the path with `get_version_in`, reads inside one session and for the write re-reads the role set in the transaction.

### P-04 — who may decide a finding today, and the comparison's own expert check
- captured_at: 2026-10-27
- command: `grep -n '"appendDecision"\|"carryOverDecision"\|"compareDocumentVersions"' src/auditmanager/api/security.py; sed -n 165,182p src/auditmanager/comparison/decision_carryover.py`
- captured_output:
  ```text
  388:        "compareDocumentVersions": _ANY_ROLE,
  433:        "appendDecision": _EXPERT,
  436:        "carryOverDecision": _EXPERT,
  def require_carryover_expert(expert_user_uid: str, actor_roles: frozenset[str]) -> None:
      """Only an account holding ``expert`` confirms a carryover; ``admin`` alone does not.

      ``actor_roles`` must be the account's role set read from authoritative state in the
      confirming transaction (`R-60`), never a client claim. Shared by the pure plan below
      and the served command (``comparison/carryover.py``).
      """
      try:
          UserUid.parse(expert_user_uid)
      except (DomainError, TypeError):
          raise DecisionCarryoverRefused("expert_identity_invalid") from None
      if (
          not isinstance(actor_roles, frozenset)
          or not actor_roles.issubset(ROLES)
          or ROLE_EXPERT not in actor_roles
      ):
          raise DecisionCarryoverRefused("expert_role_required")
  ```
- interpretation: `appendDecision` and `carryOverDecision` are `_EXPERT` at the seam; the command re-reads the role set in its own transaction and `require_carryover_expert` refuses an account without `expert` (`admin` alone does not imply it, `R-60`). Approving a pairing follows the same rule.

### P-05 — the audit-event precedent (`PROD-06`): same transaction, allow-listed payload
- captured_at: 2026-10-27
- command: `sed -n 1,16p src/auditmanager/access/audit.py; sed -n 1140,1162p db/migrations/versions/20260910_0002_pc01_schema.py`
- captured_output:
  ```text
  """The access journal: six ``access.*`` events in ``audit_event`` (`PROD-06`, ADR-0023 section 4).

  `R-146n` item 6, `AD-10`: sign-in, role grant and password change leave a row in the
  append-only ``audit_event`` table, **in the transaction of the change they describe**. A
  writer that opened its own connection, or that swallowed its own failure, would let the
  change commit without its event, or the event commit without its change; this one takes the
  caller's :class:`~sqlalchemy.orm.Session` and lets every error propagate, so the two commit
  or roll back together.

  Modelled on :mod:`auditmanager.jobs.events` and local to this context (nothing outside
  ``access`` writes these types, and no other context's allow-list is widened for them).

  What a payload may hold
  -----------------------
  Identities (``usr_`` ids), controlled classifiers (``source``, ``role``), one boolean and one
  count -- nothing else. **Never** a password, a digest, a token, a cookie, a registration's
          CREATE TABLE audit_event (
              audit_event_id text PRIMARY KEY,
              sequence_no    bigint GENERATED ALWAYS AS IDENTITY,
              event_type     text NOT NULL,
              aggregate_type text NOT NULL,
              aggregate_id   text NOT NULL,
              correlation_id text NULL,
              payload        jsonb NOT NULL DEFAULT '{{}}'::jsonb,
              occurred_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
              CONSTRAINT ck_audit_event_audit_event_id_format
                  CHECK ({id_check('audit_event_id', 'evt')}),
              CONSTRAINT ck_audit_event_event_type
                  CHECK (event_type ~ '^[a-z][a-z0-9_.]{{2,127}}$'),
              CONSTRAINT ck_audit_event_aggregate_type
                  CHECK (aggregate_type ~ '^[A-Za-z][A-Za-z0-9]{{2,63}}$'),
              CONSTRAINT ck_audit_event_aggregate_id
                  CHECK (aggregate_id ~ '^[a-z][a-z0-9]{{1,7}}_{ULID_BODY}$'),
              CONSTRAINT ck_audit_event_correlation_id
                  CHECK (correlation_id IS NULL
                         OR correlation_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{{0,127}}$'),
              CONSTRAINT ck_audit_event_payload_is_object
                  CHECK (jsonb_typeof(payload) = 'object')
          );
  ```
- interpretation: `audit_event` is the append-only trail; a writer takes the caller's Session and never swallows an error, so the event commits or rolls back with the change. `aggregate_id` must be `<prefix>_<ULID>` (`cmp_...` qualifies), payload an object.

### P-06 — migration style: revision id length, the downgrade that refuses, the append-only trigger
- captured_at: 2026-10-27
- command: `ls db/migrations/versions | tail -3; python3 -c "import re;t=open('db/migrations/versions/20261027_0034_pass_scope_all_sections.py').read();print(re.search(r'^revision: str = .*',t,re.M).group(0))"; grep -o 'alembic_version.version_num. is .varchar(32). and the longest existing revision id is exactly 32 characters' docs/program/tasks/OPT-PROJECT-ALL-SECTIONS-01.md; grep -n 'am_immutable_row' db/migrations/versions/20261020_0028_classification_corrections.py | head -3`
- captured_output:
  ```text
  20261023_0032_ar_v3_run_group.py
  20261026_0033_ar_v3_cite_stage_id.py
  20261027_0034_pass_scope_all_sections.py
  revision: str = "0034_pass_scope_all_sections"
  alembic_version.version_num` is `varchar(32)` and the longest existing revision id is exactly 32 characters
  19:UPDATE and DELETE are refused (``am_immutable_row``, SQLSTATE ``AM003``).
  177:            FOR EACH ROW EXECUTE FUNCTION am_immutable_row();
  231:        "the reason. Written once and never updated or deleted (am_immutable_row); each "
  ```
- interpretation: `alembic_version.version_num` is varchar(32); the longest id so far is exactly 32 characters. This revision is `0035_comparison_records` (23). Append-only tables use `am_immutable_row` (SQLSTATE AM003) and chain triggers raise AM001; a downgrade refuses while rows exist (`0006`, `0029`, `0032`, `0033`, `0034`).

### P-07 — every place that pins the head
- captured_at: 2026-10-27
- command: `grep -rl '0034_pass_scope_all_sections' . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.local --exclude-dir=.git --exclude-dir=__pycache__ | sort`
- captured_output:
  ```text
  ./contracts/api/v1/openapi.json
  ./db/migrations/versions/20261027_0034_pass_scope_all_sections.py
  ./docs/manual-tests/PC-01_prototype.md
  ./docs/program/CURRENT_STATE.md
  ./docs/program/dispatch/PRODUCTION-WAVE-PW4.md
  ./docs/program/OPT-PROJECT-ALL-SECTIONS-01.md
  ./docs/program/tasks/OPT-PROJECT-ALL-SECTIONS-01.md
  ./scripts/recovery/schema_coverage.py
  ./tests/integration/db/test_downgrade_chain_round_trip.py
  ./tests/integration/db/test_pass_scope_migration.py
  ./tests/integration/db/test_schema_invariant_inventory.py
  ./tests/support/expected_facts.json
  ./tests/unit/sections/test_pass_scope_migration_text.py
  ./web/openapi/openapi.json
  ```
- interpretation: Live pins to move with the head: `scripts/recovery/schema_coverage.py` (HEAD, TABLES, TRIGGERS), `tests/support/expected_facts.json`, `tests/integration/db/test_downgrade_chain_round_trip.py`, `tests/integration/db/test_schema_invariant_inventory.py`, `docs/manual-tests/PC-01_prototype.md` and `docs/program/CURRENT_STATE.md` (the integrator's, not edited here). `test_pass_scope_migration.py` reads `FACTS.migration_head` ("this revision or a later one"). The mentions in `openapi.json` and the OP/PW4 docs are history.

### P-08 — grants and purge/erase classification of a previous new table
- captured_at: 2026-10-27
- command: `grep -n 'work_assignment_event' infra/deploy/apply-grants.sh scripts/recovery/grant_classification.py scripts/recovery/product_purge.py scripts/recovery/schema_coverage.py | cut -c1-170; grep -n 'FOREIGN-KEY CLOSURE\|outside = sorted\|PRODUCT_TABLES' scripts/recovery/project_erase.py | cut -c1-170`
- captured_output:
  ```text
  infra/deploy/apply-grants.sh:305:  ('work_assignment_event', 'table', 'SELECT, INSERT', false),
  infra/deploy/apply-grants.sh:442:  ('work_assignment_event', 'table', 'SELECT, INSERT', false),
  scripts/recovery/grant_classification.py:140:    "work_assignment", "work_assignment_event",
  scripts/recovery/product_purge.py:124:    "work_assignment_event", "worker",
  scripts/recovery/schema_coverage.py:57:    "work_assignment_event", "worker"
  scripts/recovery/schema_coverage.py:168:    ("work_assignment", "trg_work_assignment_has_assigned_event", "am_require_work_assignment_event", 5),
  scripts/recovery/schema_coverage.py:170:    ("work_assignment_event", "trg_work_assignment_event_immutable", "am_immutable_row", 27),
  9:``project`` by foreign key, found by a FOREIGN-KEY CLOSURE read from the catalog and not by a hand
  98:UNSCOPED_PRODUCT_TABLES = frozenset(("worker",))
  496:    declared = purge.PRODUCT_TABLES | purge.KEEP_TABLES | purge.MIXED_TABLES
  546:    outside = sorted(set(closure.tables) - purge.PRODUCT_TABLES)
  547:    unscoped = sorted((purge.PRODUCT_TABLES - set(closure.tables)) - UNSCOPED_PRODUCT_TABLES)
  552:            f"neither the closure nor the declared unscoped set {sorted(UNSCOPED_PRODUCT_TABLES)}: {unscoped}. "
  1009:              for table in sorted(purge.KEEP_TABLES | UNSCOPED_PRODUCT_TABLES | {"audit_event"})}
  1089:                    purge.KEEP_TABLES | UNSCOPED_PRODUCT_TABLES) + " IN SHARE MODE"))
  ```
- interpretation: A new table must be named in `grant_classification.py` (APPEND_ONLY) and the generated `apply-grants.sh`, in `schema_coverage.py` (TABLES, TRIGGERS) and in `product_purge.PRODUCT_TABLES`; `project_erase.py` finds the project's rows by foreign-key closure and refuses a closure table that `PRODUCT_TABLES` does not name, so naming it there is what covers the erase.

### P-09 — how the recorded replays are keyed
- captured_at: 2026-10-27
- command: `sed -n 1,14p src/auditmanager/analysis/text/recorded.py | cut -c1-160; grep -n -A3 'def request_sha256' src/auditmanager/analysis/text/adapter.py; ls fixtures/recorded/text_analysis | head -3`
- captured_output:
  ```text
  """The recorded adapter: replay a committed response, keyed by request checksum.

  ``OD-13`` makes automated suites recorded-only, so this adapter is what every test
  runs against and it must be deterministic and offline. Two properties carry that:

  * **Keyed by ``request_sha256``.** The key is the checksum of the exact body that
    would have gone to the provider. A prompt edit, a parameter change or a different
    document changes the key, so a stale recording is reported missing rather than
    replayed against a question it does not answer.
  * **A missing recording is never a live call.** There is no fallback path in this
    class: it holds no client, no credential and no network code, so "fall back to live"
    is not something a future edit can accidentally switch on - it would have to be
    written from scratch.

  46:    def request_sha256(self) -> str:
  47-        return hashlib.sha256(canonical_json(self.body).encode("utf-8")).hexdigest()
  48-
  49-    @property
  6c208358cfa9ae3a7591223084f87250084c9c6f8070f211d8e2fd9e278dbd1d.json
  build_fixtures.py
  inputs
  ```
- interpretation: A recording is a file named by the sha256 of the canonical JSON of the exact request body; a different prompt or input is a different key, a missing file is an explicit refusal and no live call is possible from the class. The AR v3 path replays through the same adapter keyed by `provider_body_sha256`. The comparison summary reuses this shape with its own small port.

### P-10 — the contract surface and the version rule
- captured_at: 2026-10-27
- command: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));ops=[o['operationId'] for p,v in d['paths'].items() for m,o in v.items() if isinstance(o,dict) and 'operationId' in o];print(d['info']['version'],len(d['paths']),len(ops),len(d['components']['schemas']))"; git show --stat --format='%h %s' 8c1d3863 | tail -1; grep -n '^SEALED\|^PREVIOUS' tests/contract/api_v1/test_contract_seal.py`
- captured_output:
  ```text
  1.7.0 92 104 301
   92 files changed, 248 insertions(+), 176 deletions(-)
  33:SEALED = "1.7.0"
  35:PREVIOUS = "1.6.0"
  ```
- interpretation: 92 paths / 104 operations / 301 schemas at `1.7.0`. A minor bump rewrites the one shared literal in ~90 files across the analysis, domain and events families, the edge configs and unrelated web tests (`8c1d3863`), all outside this lane's grant: the lane adds operations as sealed OpenAPI content under `1.7.0` and lists the bump as the integrator's step.

### P-11 — the web side: where the comparison lives and what exists
- captured_at: 2026-10-27
- command: `ls web/src/widgets/version-comparison/ui web/src/_pages/stage-comparison/ui web/tests/unit/comparison; ls web/src/entities | grep -i compar; echo "entities/*compar* exit=$?"; grep -rln 'useVersionComparison' web/src | head`
- captured_output:
  ```text
  web/src/_pages/stage-comparison/ui:
  lazy-stage-comparison.tsx
  stage-comparison-page.tsx

  web/src/widgets/version-comparison/ui:
  version-comparison.module.css
  version-comparison.tsx

  web/tests/unit/comparison:
  carry-over-command.test.ts
  decision-carryover.test.ts
  version-comparison.test.ts
  entities/*compar* exit=1
  web/src/widgets/version-comparison/ui/version-comparison.tsx
  web/src/entities/document-version/api/use-version-comparison.ts
  web/src/entities/document-version/index.ts
  ```
- interpretation: The widget and the stage page exist; there is no `entities/version-comparison` yet (the comparison read hooks sit in `entities/document-version`, which is outside this lane's grant), so the new entity directory named in the grant is created for the pairing hooks and labels. The carry-over command is a separate feature (`features/carry-over-decision`) that this lane does not touch.

### P-12 — the resources: free disk and the lane stack
- captured_at: 2026-10-27
- command: `df -h / | tail -1; date -u +%FT%TZ; ls -a | grep -c '^.env$'; ls -ld .venv web/node_modules`
- captured_output:
  ```text
  /dev/vda3       119G  110G  2.5G  98% /
  2026-10-26T22:33:46Z
  1
  lrwxrwxrwx 1 root root 33 Oct 27 03:21 .venv -> /root/projects/PDF-Analysis/.venv
  lrwxrwxrwx 1 root root 72 Oct 27 03:21 web/node_modules -> /root/projects/PDF-Analysis/.local/worktrees/gate-night/web/node_modules
  ```
- interpretation: Free disk is above the 1.5 GiB launch floor of the wave and above MinIO's 1.2 GiB failure point; the lane `.env` is the integrator's copy (untracked); `.venv` and `web/node_modules` are symlinks (no `npm ci`).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/**`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/bootstrap/providers.py`
- `src/auditmanager/api/routers/comparison.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/api/schemas/models.py`
- `contracts/api/v1/openapi.json`
- `contracts/domain/v1/error-codes.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/generated/**`
- `web/FRONTEND_LOCK.json`
- `db/migrations/versions/20261027_0035_comparison_records.py`
- `scripts/recovery/grant_classification.py`
- `scripts/recovery/product_purge.py`
- `scripts/recovery/project_erase.py`
- `scripts/recovery/schema_coverage.py`
- `infra/deploy/apply-grants.sh`
- `fixtures/recorded/comparison/**`
- `tests/unit/comparison/**`
- `tests/integration/comparison/**`
- `tests/integration/db/test_comparison_records_migration.py`
- `tests/integration/db/test_downgrade_chain_round_trip.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/integration/recovery/**`
- `tests/integration/composition/test_comparison_records_over_http.py`
- `tests/integration/api/test_role_register.py`
- `tests/support/expected_facts.json`
- `tests/contract/api_v1/**`
- `web/src/widgets/version-comparison/**`
- `web/src/_pages/stage-comparison/**`
- `web/src/entities/version-comparison/**`
- `web/tests/unit/comparison/**`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/COMPARE-PERSISTED-SUMMARY-01.md`
- `docs/program/tasks/COMPARE-PERSISTED-SUMMARY-01.md`

Files the lane had to touch that the list above does not name, each forced by a guard that reads the member it enumerates
(the premise did not list them; every one is a prose figure, a count or a placeholder, never behaviour):

- `src/auditmanager/api/app.py`, `src/auditmanager/api/health.py`, `src/auditmanager/api/README.md`, `src/auditmanager/api/routers/__init__.py`, `src/auditmanager/api/routers/declarations.py`, `src/auditmanager/api/routers/errors.py`: the prose that states the sealed surface (95 paths, 107 operations, 314 schemas), read by `tests/contract/api_v1/test_surface_counts_in_prose.py`; `app.py` also had its measured 422 count re-measured (80 of 107)
- `docs/program/P02_SEAMS.md`: the seam table gains three rows and the sealed-operation count
- `tests/contract/domain_p02/test_openapi_document.py`, `tests/integration/api/test_authorization.py`, `tests/integration/api/test_operation_surface.py`, `tests/integration/api/test_served_document_and_health_plane.py`: tests that enumerate the operation list or the role map (one placeholder, three sets)
- `tests/integration/db/test_application_role_grants.py`, `tests/integration/db/test_comparison_summary_migration.py`: the table counts of the grant test and the new summary-table migration suite
- `tests/integration/composition/test_comparison_summary_over_http.py`: the summary over HTTP
- `web/tests/contract/seam-operations.contract.test.ts`: the web test that enumerates the operations

Granted by the integrator's message of 2026-10-27 (recorded here): the prose of `analysis_input_budget_exceeded` in `contracts/domain/v1/error-codes.json`, `contracts/api/v1/openapi.json` and `web/openapi/openapi.json`, in the same reseal. Test files that enumerate tables or the operation list (`tests/integration/db/*`, `tests/integration/recovery/**`, `tests/integration/api/test_role_register.py`, `tests/contract/api_v1/**`) are listed because the new table and operations are members of the sets they enumerate; each modified test is reported with its before and after.

## Lane resources

The lane stack is the integrator's (`ar-close-1026/.env`, copied untracked); tests that write use a private database (`cmp_<hex>`, created with the stack's maintenance role, migrated to head in the lane and dropped by the lane); the migration suites clone their own throw-away templates and drop them. The shared database is never migrated by this lane.

## Forbidden hotspots

- the optimisation, runs, jobs and analysis packages, `src/auditmanager/access/**` (the account-reference register), the shared kernel, the other web areas, the root lock files
- `tests/e2e/pc01/journey/manifest.json`, `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md`, rulings, ADRs
- any migration other than `0035`

## Non-goals

- a live model call or a live implementation of the summary port (`R-29`); the metered-cost path of a live model
- manual pairing of sheets the comparison did not propose; AI classification of sheet pairs or finding matches
- a contract version bump (the integrator's step); a foreign key to `app_user` (limit L-1)
- changing the proposal-only behaviour of the existing read for unapproved pairs, or `carryOverDecision`

## Deliverables

- `db/migrations/versions/20261027_0035_comparison_records.py` (B1: `comparison_sheet_link`; B2 adds `comparison_summary`)
- `src/auditmanager/comparison/**` (pairing store and service, audit writer, approved evidence in the read, B2: summary input prompt, port, recorded model, validator, service)
- API: three operations, their schemas, the role map, the adapter and the composition wiring
- contract and client reseal (`openapi.json` and mirror, generated client, `FRONTEND_LOCK.json`)
- grants, schema coverage, purge classification and the pins of the new head
- web: approve and withdraw, the approved pairs with their raw differences, B2 the summary with its label
- tests with a mutation table, `docs/program/COMPARE-PERSISTED-SUMMARY-01.md`, this file

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/comparison tests/integration/comparison tests/integration/db tests/contract` (minus the three `D-220` files; one pytest at a time; database tests on a private database)
- expected: green; `tests/contract/program` and the prose guards last on a clean tree; `npm --prefix web run api:verify` OK; web vitest, `tsc` and `eslint` clean on the touched files

## Integration contract

Provider: three operations under `.../versions/{version_uid}/comparison`, one append-only table per piece, the `comparison.` audit events, the three command types. Consumer behaviour the integrator can rely on: an expert-only write, idempotent by key, recomputing the comparison in the writing transaction; a read that never calls a model and never changes the raw differences; migration `0035` only adds objects and its downgrade refuses while any row exists.

## Failure/idempotency/security cases

- a key replayed returns the first answer; a changed body under one key is `idempotency_key_reuse`; an exact repeat of an active link under another key answers that link
- a stale proposal, an occupied page, the 33rd active link, an already withdrawn link are `409` with a `conflict_reason`
- an account without `expert` is `permission_denied` even with `admin`; an unknown path is `404` before any comparison is computed
- the row and its audit event commit or roll back together
- a summary referring to a hunk that does not exist is rejected whole; a recording that does not exist is an explicit refusal and never a live call; a non-recorded process answers `dependency_unavailable`

## Rollback / feature flag

Not a feature flag: the operations are new and the read gains one field. Rollback of the schema is `alembic downgrade 0034_pass_scope_all_sections`, refused while `comparison_sheet_link` or `comparison_summary` holds a row (restore a backup instead); without rows it drops the objects. The recorded model is wired only in `recorded` mode.

## Handoff

- changed files: `docs/program/COMPARE-PERSISTED-SUMMARY-01.md`, section «Files» (and `git diff --name-only 3561e1c8..HEAD`)
- commands/results: the same report, section «Commands and counts»
- known limits: the same report, section «Limits»
- integration notes: the same report, section «Integration notes» (the files that pin the head and the contract version, and the prose patch for the files outside this lane's grant)
