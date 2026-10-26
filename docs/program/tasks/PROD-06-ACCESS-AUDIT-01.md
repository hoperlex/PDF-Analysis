# Task PROD-06-ACCESS-AUDIT-01 — sign-in, role grant and password change leave an audit event

task_id: PROD-06-ACCESS-AUDIT-01
status: completed in development candidate

## Outcome

The six `access.*` event types of `ADR-0023` section 4 (`R-146n` item 6, `AD-10`, confirmed by `R-146w` at `83600aed`) are appended to `audit_event` **in the transaction of the change they describe**, from the sign-in path, the registration approval, the administrator's role change, the password change and reset, and the host command `python -m auditmanager.access.grant`; the product purge keeps them. No password, hash, token, cookie, name, e-mail, IP address or user agent is in any payload, and a test scans the stored rows of every type for each of those values.

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-06` is this task.
- `ADR-0023` — accepted for production; section 4 and its commitments 5 and 6 are what this task delivers.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable (the event envelope schema has no list of event types, see P-05)
- migration head: unchanged (`0032_ar_v3_run_group`); `audit_event` has no closed registry of event types (P-03, P-04)
- base commit: `bfcb8a978e9ec9dd9fb3ac500e4b17551674e24b` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: scripts/recovery/product_purge.py
- enumerator_owner: PROD-06-ACCESS-AUDIT-01 (the plan names this task the only editor of `product_purge.py` in its wave: one prefix)
- totality_query: `python3 -I -c "import re,pathlib as p;t=p.Path('scripts/recovery/product_purge.py').read_text();k=re.search(r'KEEP_EVENT_PREFIXES = \((.*?)\)',t).group(1);q=re.search(r'PRODUCT_EVENT_PREFIXES = \((.*?)\)',t,re.S).group(1);pre=tuple(re.findall(r'\"([a-z_.]+)\"',k+q));ev=set();[ev.update(re.findall(r'event_type\s*=\s*\"([a-z_][a-z0-9_.]*)\"',f.read_text())) for f in p.Path('src').rglob('*.py')];print(sorted(e for e in ev if not e.startswith(pre)))"`

The set is the `audit_event.event_type` families the purge tool has classified (`KEEP_EVENT_PREFIXES` and `PRODUCT_EVENT_PREFIXES`). This task adds one family, `access.`, to the keep side. The query lists every `event_type="..."` literal under `src/` that starts with no classified prefix, and prints `[]`.

## Captured premise evidence

- premise: eleven reads the plan and the lane file rely on, plus the green baseline, re-run on the base commit; every one matches the plan except two facts the plan did not state and the task handles (P-10: the correlation id cannot reach the access context without an API edit; P-11: the purge suite's own seeds journal access events, so two kept-row counts change)

### P-01 — audit_event is written today by two other contexts' own writers and by nobody in access; there is no access-local writer
- captured_at: 2026-10-26
- command: `git grep -n audit_event bfcb8a97 -- src/auditmanager | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  src/auditmanager/execution/public.py:99:        SELECT e.occurred_at, e.sequence_no FROM audit_event e
  src/auditmanager/execution/public.py:100:         WHERE e.audit_event_id = :cursor AND (
  src/auditmanager/execution/public.py:109:    SELECT e.audit_event_id, e.aggregate_type, e.aggregate_id, e.event_type,
  src/auditmanager/execution/public.py:112:      FROM audit_event e
  src/auditmanager/execution/public.py:136:        SELECT e.occurred_at, e.sequence_no FROM audit_event e
  src/auditmanager/execution/public.py:139:         WHERE e.audit_event_id = :cursor
  src/auditmanager/execution/public.py:141:    SELECT e.audit_event_id, e.aggregate_type, e.aggregate_id, e.event_type,
  src/auditmanager/execution/public.py:144:      JOIN audit_event e ON e.aggregate_type = ids.aggregate_type
  src/auditmanager/execution/public.py:180:            event_id=row["audit_event_id"],
  src/auditmanager/jobs/events.py:34:    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, "
  src/auditmanager/jobs/repository.py:83:    "SELECT e.payload ->> 'stage_id' FROM audit_event e "
  src/auditmanager/norms/bundle/copy_record.py:34:``norm*`` table, an ``audit_event`` of type ``norm_custody.*``, or a ``blob`` row a
  src/auditmanager/norms/bundle/copy_record.py:73:        WHEN c.relname = 'audit_event' THEN 'WHERE x.event_type NOT LIKE ''norm\_custody.%'''
  src/auditmanager/norms/custody/repository.py:130:    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
  src/auditmanager/norms/custody/repository.py:230:    """Rows of the two custody tables, and the custody events in ``audit_event``."""
  ```
- interpretation: Writers: jobs/events.py (an allow-list writer, the model) and norms/custody/repository.py (raw INSERT); the rest are reads. Nothing under src/auditmanager/access appears, so the access writer is new and no existing writer is reused or widened.

### P-02 — the access files and tests the plan names exist; audit.py and tests/unit/access do not (audit.py is new by the plan; the unit directory is created by this task)
- captured_at: 2026-10-26
- command: `git ls-tree -r --name-only bfcb8a97 -- src/auditmanager/access tests/integration/access tests/unit/access`
- captured_output:
  ```text
  src/auditmanager/access/README.md
  src/auditmanager/access/__init__.py
  src/auditmanager/access/accounts.py
  src/auditmanager/access/check.py
  src/auditmanager/access/grant.py
  src/auditmanager/access/models.py
  src/auditmanager/access/passwords.py
  src/auditmanager/access/policy.py
  src/auditmanager/access/ports.py
  src/auditmanager/access/profile.py
  src/auditmanager/access/public.py
  src/auditmanager/access/queue_lock.py
  src/auditmanager/access/references.py
  src/auditmanager/access/registrations.py
  src/auditmanager/access/repository.py
  src/auditmanager/access/revoke.py
  src/auditmanager/access/unlock.py
  tests/integration/access/conftest.py
  tests/integration/access/qa_w49/test_qa_w49_invariants_without_a_router.py
  tests/integration/access/test_account_management.py
  tests/integration/access/test_account_names.py
  tests/integration/access/test_login_queue_lock.py
  tests/integration/access/test_password_hashing.py
  tests/integration/access/test_password_policy.py
  tests/integration/access/test_registrations.py
  tests/integration/access/test_roles.py
  ```
- interpretation: repository, accounts, registrations, grant all exist; audit.py is absent (the plan says 'a new audit.py'); tests/unit/access has no tracked file.

### P-03 — audit_event's event_type column is not a closed registry: the only constraints are the four named CHECKs, all in migration 0002, and no later migration touches them
- captured_at: 2026-10-26
- command: `git grep -n -E 'ck_audit_event|ALTER TABLE audit_event' bfcb8a97 -- db/migrations | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  db/migrations/versions/20260910_0002_pc01_schema.py:1149:            CONSTRAINT ck_audit_event_audit_event_id_format
  db/migrations/versions/20260910_0002_pc01_schema.py:1151:            CONSTRAINT ck_audit_event_event_type
  db/migrations/versions/20260910_0002_pc01_schema.py:1153:            CONSTRAINT ck_audit_event_aggregate_type
  db/migrations/versions/20260910_0002_pc01_schema.py:1155:            CONSTRAINT ck_audit_event_aggregate_id
  db/migrations/versions/20260910_0002_pc01_schema.py:1157:            CONSTRAINT ck_audit_event_correlation_id
  db/migrations/versions/20260910_0002_pc01_schema.py:1160:            CONSTRAINT ck_audit_event_payload_is_object
  ```
- interpretation: Four CHECKs, all in 0002_pc01_schema; no ALTER TABLE audit_event anywhere. A new event type needs no migration.

### P-04 — the CHECKs admit access.* types, aggregate type Account and a usr_ aggregate id
- captured_at: 2026-10-26
- command: `git grep -n -E "event_type ~|aggregate_type ~|aggregate_id ~|correlation_id ~" bfcb8a97 -- db/migrations/versions/20260910_0002_pc01_schema.py | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  db/migrations/versions/20260910_0002_pc01_schema.py:1075:                       OR correlation_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{{0,127}}$'),
  db/migrations/versions/20260910_0002_pc01_schema.py:1152:                CHECK (event_type ~ '^[a-z][a-z0-9_.]{{2,127}}$'),
  db/migrations/versions/20260910_0002_pc01_schema.py:1154:                CHECK (aggregate_type ~ '^[A-Za-z][A-Za-z0-9]{{2,63}}$'),
  db/migrations/versions/20260910_0002_pc01_schema.py:1156:                CHECK (aggregate_id ~ '^[a-z][a-z0-9]{{1,7}}_{ULID_BODY}$'),
  db/migrations/versions/20260910_0002_pc01_schema.py:1159:                       OR correlation_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{{0,127}}$'),
  ```
- interpretation: event_type ~ ^[a-z][a-z0-9_.]{2,127}$ admits access.sign_in_succeeded; aggregate_type ~ ^[A-Za-z][A-Za-z0-9]{2,63}$ admits Account; aggregate_id ~ ^[a-z][a-z0-9]{1,7}_<ULID> admits usr_<ULID>; correlation_id is NULL or the contract CorrelationId pattern.

### P-05 — the event envelope contract has no enumeration of event types (no contract change is needed)
- captured_at: 2026-10-26
- command: `git grep -n -A3 '"event_type"' bfcb8a97 -- contracts/events/v1/event-envelope.schema.json | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  contracts/events/v1/event-envelope.schema.json:10:    "event_type",
  contracts/events/v1/event-envelope.schema.json-11-    "aggregate_type",
  contracts/events/v1/event-envelope.schema.json-12-    "aggregate_id",
  contracts/events/v1/event-envelope.schema.json-13-    "occurred_at",
  --
  contracts/events/v1/event-envelope.schema.json:26:    "event_type": {
  contracts/events/v1/event-envelope.schema.json-27-      "type": "string",
  contracts/events/v1/event-envelope.schema.json-28-      "minLength": 1
  contracts/events/v1/event-envelope.schema.json-29-    },
  ```
- interpretation: event_type is 'type: string, minLength: 1' in the envelope; no enum. contracts/** is not touched.

### P-06 — ADR-0023 section 4 (rows 5 and 6 of its commitments table, and the six-event table) is as confirmed by R-146w at 83600aed: the only difference is the Status line
- captured_at: 2026-10-26
- command: `bash -c "diff <(git show 83600aed:docs/architecture/adr/ADR-0023-production-identity-and-access.md | sed -n '/^### 4\. Audit events/,/^### 5\./p') <(git show bfcb8a97:docs/architecture/adr/ADR-0023-production-identity-and-access.md | sed -n '/^### 4\. Audit events/,/^### 5\./p')"`
- captured_output:
  ```text
  3c3
  < `AD-10` (architect's implementation decision within `R-146n` item 6, to be confirmed).
  ---
  > `AD-10`, confirmed by `R-146w` as written at commit `83600aed` (an implementation decision within `R-146n` item 6).
  ```
- interpretation: A two-line diff of the AD-10 status sentence only; the six event types, their keys and the retention sentence are byte-identical to the confirmed text.

### P-07 — the six event rows and the two commitment rows of ADR-0023 that this task implements
- captured_at: 2026-10-26
- command: `bash -c "git show bfcb8a97:docs/architecture/adr/ADR-0023-production-identity-and-access.md | grep -n -E '^\| .?access\.|^\| [56] \|' | cut -c1-230"`
- captured_output:
  ```text
  129:| `access.sign_in_succeeded` | `issueToken` accepts a password | `Account`, the account's `usr_` id | `subject_uid`, `source` (`api`), `default_credential` (true when the account was still on the seeded or reset password) |
  130:| `access.sign_in_blocked` | a failed attempt starts a cooling-off period on a known account | `Account` | `subject_uid`, `source`, `failures` |
  131:| `access.role_granted` | `approveRegistration` grants, an administrator adds a role, `python -m auditmanager.access.grant` runs | `Account` | `subject_uid`, `actor_uid` (absent for the host command), `role`, `source` (`api` o
  132:| `access.role_revoked` | an administrator removes a role | `Account` | `subject_uid`, `actor_uid`, `role`, `source` |
  133:| `access.password_changed` | `changePassword` succeeds | `Account` | `subject_uid`, `actor_uid` (the same), `source` |
  134:| `access.password_reset` | `resetUserPassword` by an administrator | `Account` | `subject_uid`, `actor_uid`, `source` |
  168:| 5 | Sign-in, role grant and password change are journalled | `select event_type, count(*) from audit_event where event_type like 'access.%' group by 1` after one of each; a test per code path (API, registration approval, hos
  169:| 6 | No event payload carries a secret or a name | a test that every key an `access.*` event writes is in the writer's allow-list and every value is a scalar | no | `PROD-06` |
  ```
- interpretation: Six access.* rows (sign_in_succeeded, sign_in_blocked, role_granted, role_revoked, password_changed, password_reset) and commitment rows 5 and 6 with 'PROD-06' as the deliverer. Lines are cut at 230 characters for the record; the ADR holds the full text.

### P-08 — the purge tool's keep prefixes and the guard that stops on an unclassified event type
- captured_at: 2026-10-26
- command: `git grep -n -E 'KEEP_EVENT_PREFIXES|def _event_keep|event-types-classified' bfcb8a97 -- scripts/recovery/product_purge.py | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  scripts/recovery/product_purge.py:129:KEEP_EVENT_PREFIXES = ("norm_custody.", "executor.")
  scripts/recovery/product_purge.py:376:    # >>> guard: event-types-classified
  scripts/recovery/product_purge.py:378:    unknown = sorted(e for e in events if not e.startswith(KEEP_EVENT_PREFIXES + PRODUCT_EVENT_PREFIXES))
  scripts/recovery/product_purge.py:384:    # <<< guard: event-types-classified
  scripts/recovery/product_purge.py:398:def _event_keep() -> str:
  scripts/recovery/product_purge.py:399:    """The keep rows of ``audit_event``: every family of :data:`KEEP_EVENT_PREFIXES`, no other list."""
  scripts/recovery/product_purge.py:400:    return "(" + " OR ".join(f"starts_with(t.event_type, '{prefix}')" for prefix in KEEP_EVENT_PREFIXES) + ")"
  ```
- interpretation: KEEP_EVENT_PREFIXES = ('norm_custody.', 'executor.'): 'access.' is absent, so an access.* event would stop the tool (event-types-classified) and, were it bypassed, would be deleted. _event_keep() builds the predicate from the tuple alone.

### P-09 — every caller of the changed repository methods is inside the access context or the API adapters, which only pass a session in: no composition-root edit is needed
- captured_at: 2026-10-26
- command: `git grep -n -E '\.authenticate\(|\.change_password\(|\.grant_role\(|\.set_roles\(|\.reset_password\(|_registrations\.approve\(' bfcb8a97 -- src scripts | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  scripts/recovery/synthetic_drill_seed.py:194:                accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
  src/auditmanager/access/grant.py:79:            changed = accounts.grant_role(
  src/auditmanager/api/routers/auth.py:258:        issued = credentials.change_password(
  src/auditmanager/api/routers/users.py:183:        view = accounts.reset_password(
  src/auditmanager/bootstrap/adapters.py:2041:        record = self._write(lambda session: self._users.authenticate(session, login, password))
  src/auditmanager/bootstrap/adapters.py:2081:            lambda session: self._users.change_password(
  src/auditmanager/bootstrap/adapters.py:2273:                self._accounts.set_roles(
  src/auditmanager/bootstrap/adapters.py:2316:            self._accounts.reset_password(
  src/auditmanager/bootstrap/adapters.py:2447:            decided, _account = self._registrations.approve(
  ```
- interpretation: bootstrap/adapters.py (the composition root) calls the repositories inside self._write(lambda session: ...), which commits; the emission goes inside the repository on that session, so the root is unchanged. scripts/recovery/synthetic_drill_seed.py calls grant_role(granted_by=None) and is unchanged.

### P-10 — the correlation id lives in the API transport as a ContextVar; the access context has no reader of it
- captured_at: 2026-10-26
- command: `git grep -n -E 'ContextVar|_CURRENT\.set' bfcb8a97 -- src/auditmanager/api/routers/correlation.py src/auditmanager/access | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  src/auditmanager/api/routers/correlation.py:26:from contextvars import ContextVar
  src/auditmanager/api/routers/correlation.py:48:#: handler without threading it through every signature. A ``ContextVar`` rather than a
  src/auditmanager/api/routers/correlation.py:52:_CURRENT: ContextVar[str] = ContextVar("auditmanager_correlation_id")
  src/auditmanager/api/routers/correlation.py:113:        token = _CURRENT.set(resolved)
  ```
- interpretation: Only api/routers/correlation.py holds the variable and sets it in CorrelationMiddleware. access may not import api (ALR-05 / AGENTS section 4), so the id can reach an access event only through a seam the transport binds; binding it is an edit of src/auditmanager/api/**, outside this lane.

### P-11 — the seeds of the purge suite journal access events once the writer exists (explains the keep-row count change in test_product_purge.py)
- captured_at: 2026-10-26
- command: `git grep -n -E 'change_password|grant_role' bfcb8a97 -- tests/integration/recovery/purge_seed.py scripts/recovery/synthetic_drill_seed.py | sed 's/^bfcb8a97://'`
- captured_output:
  ```text
  scripts/recovery/synthetic_drill_seed.py:194:                accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
  tests/integration/recovery/purge_seed.py:82:            changed = UserRepository().change_password(
  ```
- interpretation: purge_seed changes the administrator's password through UserRepository.change_password (1 password_changed); synthetic_drill_seed grants roles through AccountRepository.grant_role (3 role_granted, loop over roles). 3 norm_custody + 4 access = 7 kept rows.

### P-12 — the two suites the plan names are green on the base, before the first edit
- captured_at: 2026-10-26
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/access tests/integration/recovery/test_product_purge.py`
- captured_output:
  ```text
  246 passed in 34.37s   (tests/integration/access, run alone)
  64 passed in 45.01s    (tests/integration/recovery/test_product_purge.py, run alone)
  ```
- interpretation: measured on the base commit with the integration lane stack's isolated database clones, before any edit; the two were run one after the other, as the host allows one pytest at a time. tests/unit/access did not exist.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/access/**`
- `scripts/recovery/product_purge.py`
- `tests/unit/access/**`
- `tests/integration/access/**`
- `tests/integration/recovery/test_product_purge.py`
- `docs/program/tasks/PROD-06-ACCESS-AUDIT-01.md`
- `docs/program/PROD-06-ACCESS-AUDIT-01.md`

`product_purge.py` is edited at its keep-prefix tuple and the two prose lines that describe it (a docstring bullet and the comment above the tuple); no guard block is touched. `test_product_purge.py` gets two new cases and two changed expectations (the report lists each before and after).

## Forbidden hotspots

`contracts/**`, `db/**` and the migration head, `src/auditmanager/api/**` (the sign-in event is emitted from `access`, so no edit there is needed), `src/auditmanager/bootstrap/**` (the composition root), `infra/**`, root dependency and lock files, `web/**`, global styles, every other test file (including `tests/integration/recovery/test_product_purge_executor_events.py`, see the report), `DEBT_REGISTER.md`, `CURRENT_STATE.md`, `PRODUCTION-READINESS-PLAN-01.md`, `OWNER_RULINGS_*`, the ADRs.

## Non-goals

- No IP address, user agent or any request metadata in an event (`ADR-0023`: the address behind a terminator is the proxy's, a wrong fact in an append-only table).
- No event for registration approval or rejection as such, archive, restore, purge or unlock; no event for a failed attempt that starts no cooling-off period or for an unknown login (the ADR lists them as the first additions if the audit is widened).
- No binding of the request's correlation id from the API middleware: that is an edit of `src/auditmanager/api/routers/correlation.py`, outside this lane. The access side of the seam is delivered and tested; until the transport binds it the column is `NULL` (the report names the one-line change and its owner slot).
- No change to `copy_record.py` or `copy-serve.sh` (their `audit_event` fingerprint will see a sign-in written during an import window; the procedure quiesces the writers).
- No edit of `test_product_purge_executor_events.py`, which two of its three tests now fail because the seed journals kept `access.*` events (the report gives the one-line fix and shows it turns the file green).

## Deliverables

- `src/auditmanager/access/audit.py`: the writer. `PAYLOAD_KEYS` (per-type required and optional keys), closed value rules, six typed entry points (`record_sign_in_succeeded`, `record_sign_in_blocked`, `record_role_granted`, `record_role_revoked`, `record_password_changed`, `record_password_reset`), `bind_correlation_id` / `reset_correlation_id` / `correlation_scope` for the transport. It uses the caller's session, never commits and never swallows.
- Emissions: `UserRepository.authenticate` and `_note_a_failed_sign_in` and `change_password` (`repository.py`), `AccountRepository.reset_password`, `grant_role` and `set_roles` (`accounts.py`), `RegistrationRepository.approve` (`registrations.py`); `grant.py` documents that the host command's commit carries its event; `public.py` re-exports the correlation seam.
- `scripts/recovery/product_purge.py`: `access.` in `KEEP_EVENT_PREFIXES`.
- Tests: `tests/unit/access/test_access_audit_payloads.py`, `tests/integration/access/test_access_audit.py`, and in `tests/integration/recovery/test_product_purge.py` two new cases and two changed expectations.
- Report `docs/program/PROD-06-ACCESS-AUDIT-01.md`: the mutation table, the before and after of every modified test, the commands and counts, the ambiguities of the ADR and what was chosen, the integration notes.

## Required tests

- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/access` — expected: 88 passed.
- command: the same with `tests/integration/access` — expected: 270 passed (246 on the base, plus 24).
- command: the same with `tests/integration/recovery/test_product_purge.py` — expected: 66 passed (64 on the base, plus 2).
- command: the same with `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on a committed tree — expected: as on the base.
- command: `git diff --check` — expected: exit 0.
- mutations: each emission deleted, the event written outside the transaction, a failed write swallowed, an IP / a digest / a login put into a payload, each value rule and the allow-list neutered, every failed attempt journalled, the correlation id ignored, the host command mislabelled, the keep prefix removed — each goes red and green again after the revert (the table is in the report).

## Integration contract

The integrator can rely on: after this merge every accepted sign-in, every sign-in that starts a cooling-off, every role granted or revoked, every password change and every administrator reset appends one row to `audit_event` (aggregate `Account`, aggregate id the account's `usr_` id) in the same transaction as the change; the payload holds only identities, `source` (`api` or `host_cli`), `role`, `default_credential` and `failures`; the purge tool keeps the family and refuses nothing it did not refuse before. Two things the integrator must do: apply the one-line change to `test_product_purge_executor_events.py` named in the report (or the recovery suite stays red on two tests), and assign the correlation binding to the owner of `src/auditmanager/api/routers/correlation.py` if the tie to the server log is wanted for 1.0.

## Failure/idempotency/security cases

A refused change writes no event (wrong current password, same password, short password, self reset, self demotion, last administrator, no role chosen at approval, a rejection). A role already held changes nothing and writes nothing. A failed event write aborts the change (it is not swallowed, and the writer opens no connection of its own). A key outside the type's allow-list, a missing key, a value outside the closed rule (a login, a token-shaped string or an address under `subject_uid`, a role outside the vocabulary, a `source` that is an address, a non-positive count, a non-boolean flag) is refused before the INSERT.

## Rollback / feature flag

Forward-revert. The change adds rows to an append-only table and removes none; reverting the code stops the new rows and leaves the written ones, which the purge tool of the reverted tree would then refuse as unclassified. No feature flag: the journal is a security record and a switch would be a way to turn it off.

## Handoff

- changed files: the report lists them
- commands/results: see the report
- known limits: the correlation id is not bound by the transport yet; `test_product_purge_executor_events.py` needs one line; `copy_record`'s fingerprint now sees sign-in events
- integration notes: merge with the report's two follow-ups; the next editor of `product_purge.py` is `PROD-07`, which depends on this task
