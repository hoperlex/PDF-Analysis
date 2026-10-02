# Task W48-DURABLE-REPAIR — close the durable-effects judge escapes

## Outcome

The exact `W48-DURABLE-JUDGE` reproductions for provider cross-authority checkpointing,
pre-intent temporary upload and the contradictory standalone live runner become committed red-to-
green regressions, without widening the frozen API/error surface or publishing a ref.

## Depends on

- `W48-DURABLE-01` — completed at `00100e8129ab0d144d66f7bac4899c069879b3cb`
- `W48-DURABLE-JUDGE` — completed with REJECT at
  `b43185071af3b315df208245089e27f56fd91f64`
- the separate 2026-10-02 owner authority already recorded by `W48-DURABLE-01` for the unpublished
  `0014_durable_analysis_effects` migration and the `A-01`/`A-02` repair boundary

## Frozen inputs

- base commit: `b43185071af3b315df208245089e27f56fd91f64`
- reviewed implementation subject: `00100e8129ab0d144d66f7bac4899c069879b3cb`
- domain contract: `1.0.0-draft.1` revision 8
- API: 17 paths / 20 operations / 61 schemas; no wire change
- error catalog: 22; no new or reinterpreted code
- migration head: remains `0014_durable_analysis_effects`; this task may harden that unpublished
  migration but may not add a successor
- judge findings: `DJ-01`, `DJ-02` and `DJ-03` exactly as recorded in
  `docs/program/reviews/W48-DURABLE-JUDGE.md`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `tests/integration/db/test_schema_invariant_inventory.py`
- enumerator_owner: `W48-DURABLE-REPAIR`
- totality_query: the complete `_inventory()` catalog queries in that file against a database
  freshly migrated from empty

The member set changes only if the provider-effect/model-call composite database invariant adds
catalog members. No route, screen, error code or migration revision is added.

## Captured premise evidence

- premise: the exact base, linear migration, three unscoped provider updates, upload ordering and
  contradictory CLI are present

### P-01 — exact repair base

- captured_at: 2026-10-02
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  b43185071af3b315df208245089e27f56fd91f64
  ```
- interpretation: the repair includes the immutable red judge report; it does not prove that any
  remote ref names this commit.

### P-02 — migration remains one unpublished linear head

- captured_at: 2026-10-02
- command: `rg -n '^revision:|^down_revision:' db/migrations/versions/20261002_0014_durable_analysis_effects.py`
- captured_output:
  ```text
  19:revision: str = "0014_durable_analysis_effects"
  20:down_revision: str | None = "0013_norm_embeddings"
  ```
- interpretation: the correction may strengthen this unpublished migration under inherited
  ownership; it may not rewrite 0013 or create another head.

### P-03 — provider transitions do not bind their validated authority

- captured_at: 2026-10-02
- command: `rg -n "WHERE model_call_id = :model_call_id|self.require_current\\(session, authority\\)" src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  85:     WHERE model_call_id = :model_call_id AND state = 'prepared'
  93:     WHERE model_call_id = :model_call_id AND state = 'prepared'
  101:     WHERE model_call_id = :model_call_id AND state = 'response_received'
  234:        self.require_current(session, authority)
  268:        self.require_current(session, authority)
  297:        self.require_current(session, authority)
  321:        self.require_current(session, authority)
  338:        self.require_current(session, authority)
  382:        self.require_current(session, authority)
  403:        self.require_current(session, authority)
  ```
- interpretation: current-authority validation and target-effect ownership are separate facts;
  the three update predicates prove no relationship between them.

### P-04 — temporary upload precedes the only database callback

- captured_at: 2026-10-02
- command: `rg -n "stage_temporary|verify_temporary|_before_publish|except Exception" src/auditmanager/storage/durable_publication.py`
- captured_output:
  ```text
  22:    __slots__ = ("_store", "_before_publish", "_after_publish")
  73:        temporary = self.stage_temporary(
  81:            verified = self.verify_temporary(temporary)
  82:            self._before_publish(verified)
  87:        except Exception:
  ```
- interpretation: process loss after line 73 can leave external bytes before any callback can
  commit a database breadcrumb; ordinary exception cleanup does not close a process-kill gap.

### P-05 — standalone CLI advertises live while omitting the journal

- captured_at: 2026-10-02
- command: `rg -n "only way the live path|LiveAdapter|run_text_analysis\\(|call_journal" src/auditmanager/analysis/text/__main__.py src/auditmanager/analysis/text/stage.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/__main__.py:1:"""The manual runner. The only way the live path is ever reached.
  src/auditmanager/analysis/text/__main__.py:36:from auditmanager.analysis.text.live import LiveAdapter
  src/auditmanager/analysis/text/__main__.py:70:        return LiveAdapter(api_key=config.api_key)
  src/auditmanager/analysis/text/__main__.py:90:    outcome = run_text_analysis(
  src/auditmanager/analysis/text/stage.py:227:    call_journal: ModelCallJournal | None = None,
  src/auditmanager/analysis/text/stage.py:266:    if call_journal is None and mode is ProviderMode.LIVE:
  ```
- interpretation: the documented operator command cannot reach dispatch; the public Run executor,
  not this standalone diagnostic, is the owned live path.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W48-DURABLE-JUDGE.md`
- addendum_path: not_applicable

The judge report is immutable. This task records its own red-to-green evidence and does not edit
the report or reinterpret its verdict.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `db/migrations/versions/20261002_0014_durable_analysis_effects.py`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/storage/__init__.py`
- `src/auditmanager/storage/models.py`
- `src/auditmanager/storage/blob_repository.py`
- `src/auditmanager/storage/durable_publication.py`
- `src/auditmanager/storage/port.py`
- `src/auditmanager/storage/s3.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/ingest/reconciliation.py`
- `src/auditmanager/analysis/text/__main__.py`
- `tests/integration/db/test_durable_analysis_effects.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/runs/test_durable_effect_boundaries.py`
- `tests/integration/ingest/test_blob_metadata.py`
- `tests/integration/ingest/test_reconciliation.py`
- `tests/integration/storage/test_publication.py`
- `tests/integration/analysis_text/test_provider_modes.py`
- `docs/program/tasks/W48-DURABLE-REPAIR.md`
- `docs/program/W48-DURABLE-REPAIR.md`

## Forbidden hotspots

- `contracts/**`, generated clients, API routers/schemas and the error catalog
- every migration other than the unpublished owned 0014 file; no new migration head
- root/frontend dependency or lock files, composition root, `Makefile`, workflows, deploy files,
  authentication, global styles and public-host state
- immutable audit/judge reports, `CURRENT_STATE.md`, `DEBT_REGISTER.md` and unrelated task files
- tags, `origin/dev`, `origin/main`, credentials, live-provider calls and object deletion outside
  exact disposable test cleanup

## Non-goals

- no provider exactly-once claim, retry/resume scheduler or distributed worker
- no S3 bucket listing, silent object adoption or production orphan deletion
- no public Job/Attempt/effect API and no contract reseal
- no implementation of live provider access in the standalone diagnostic CLI; live execution
  remains owned by the durable Run executor and release acceptance flow
- no repair of `A-03`, tag, remote publication, deployment or public acceptance

## Deliverables

- authority-scoped response, unknown and completion writes plus a database invariant that prevents
  final model-call/run cross-wiring
- a validated declared-blob breadcrumb and attempt-scoped publication intent carrying an opaque
  DB-generated upload handle, committed before the temporary upload, followed by the existing
  verified/canonical checkpoints
- reconciliation evidence from a fresh transaction for process loss immediately after temporary
  upload/verification
- a truthful replay-only standalone diagnostic whose live configuration fails before constructing
  or dispatching a live adapter
- exact committed regressions for `DJ-01`, `DJ-02`, `DJ-03` and a completion report

## Required tests

- all three provider transitions reject a foreign but current authority, leave the owned effect
  unchanged and disclose no execution token
- direct database completion cannot bind an effect to a `model_call` from another run
- a process-exit signal after temporary verification leaves a `temporary` blob row and unbound
  attempt publication whose exact temporary object is point-inspected by `Reconciler.report()`
  from a new transaction, without exposing its handle or listing the bucket
- malformed blob declarations fail before a breadcrumb or S3 write; ordinary and successful paths
  preserve cleanup, idempotency and binding behaviour
- standalone live invocation with a synthetic key fails before adapter construction/network and
  its module/help text makes no live-capture promise; recorded capture remains green
- fresh migration inventory, exact durability/reconciliation scopes, `git diff --check`,
  allowed-path-only diff and full `make gate`

## Integration contract

A current Attempt may advance only provider effects whose stored run/job/attempt tuple exactly
equals that authority, and the database prevents the final immutable `model_call` from naming a
different run. For analysis artifacts, validated declared content identity plus the current
  Attempt's publication intent and opaque upload handle commit before the first S3 write;
  verification advances that same blob record before canonical publish. Every kill boundary is
  therefore enumerable and point-inspectable from database identity without bucket listing. The
  standalone module is a replay diagnostic; live calls occur only through the durable Run executor.

## Failure/idempotency/security cases

- foreign-current, stale and wrong-token authorities fail closed without a mutation or token leak
- identical declared content remains content-idempotent while each Attempt keeps its attribution
- invalid digest/size/role creates neither DB intent nor external upload
- process loss needs no Python cleanup to preserve the pre-effect database evidence
- canonical objects are never implicitly deleted and reconciliation remains read-only/point-based
- live CLI refusal never initializes the provider client and never writes a capture

## Rollback / feature flag

No feature flag: each old behaviour is a data-integrity or truthful-operator-path defect. Before
deployment, rollback is revert of this repair plus the original unpublished durable candidate.
After durable-effect data exists, use forward repair/restore; downgrade remains intentionally
refused for populated evidence tables.

## Handoff

- changed files and exact commands/results: `docs/program/W48-DURABLE-REPAIR.md`
- contracts: no external contract bytes or error entries change; migration head remains 0014
- known limits: organisationally independent re-judge and public live acceptance remain required
- integration notes: a clean full gate makes a new local candidate only; no remote ref moves under
  this task, and `W48-INT-CLOSE` remains blocked until a separate judge accepts the repair
