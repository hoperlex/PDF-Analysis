# Task SMALL-HARDENING-02 — the run CSV does not hand a spreadsheet a formula, and open registration cannot flood its queue

task_id: SMALL-HARDENING-02
status: lane S1 of wave PW5, parts (a) and (b); parts (c) and (d) of `PRODUCTION-WAVE-PW5.md` section 4 are not in this task

## Outcome

Two owner rulings of 2026-10-27 are in the tree, each with a test that proves it can fail:

- `R-146ax` (`F-11` of `EXPOSURE-REVIEW-02.md`): a text cell of `exportRunCsv` whose first character is `=`, `+`, `-`, `@`, tab or carriage return gets one leading apostrophe; every other byte of the file is unchanged, and the frozen `OD-11` byte format (BOM, CRLF, comma, minimal quoting, empty cells) is untouched.
- `R-146ay` (`F-19`, `F-09`, `F-18` in part): registration and sign-in stay public, and at most 40 registration requests are accepted in any rolling 24 hours (the next answers the existing `conflict` / `queue_full`), computed from the existing `submitted_at` column. The short life of a pending request and the `limit_req` of part (b) were examined first and need no change in this lane; the premise blocks and the report say why.

## Depends on

- `R-146ax`, `R-146ay` — recorded rulings in `docs/program/OWNER_RULINGS_2026-09-17.md`.
- `EXPOSURE-REVIEW-02` — completed review.
- `PRODUCTION-WAVE-PW5` section 4 — the brief (parts (a) and (b) only).

## Frozen inputs

- domain contract: unchanged (`contracts/**` is not touched)
- API contract: unchanged; `queue_full` is an existing value of `details.conflict_reason`
- analysis/comparison/event contract: not_applicable
- migration head: `0035_comparison_records`, unchanged (no migration)
- base commit: `9e42c18a` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: every file, line and number the brief names was re-read at the base commit and matches it, with three findings the brief did not name: the column is `submitted_at` (there is no `created_at`), no existing registration state can carry "expired" or "withdrawn" (so the short life of a pending request is not built, as the brief instructs), and the `limit_req` the brief asks for on `POST /api/v1/registrations` already exists in the same zone as the status call

### P-01 — the run CSV writes a text cell exactly as it is

- captured_at: 2026-10-27
- command: `git show 9e42c18a:src/auditmanager/exports/serializer.py | rg -n "return str\(value\)|QUOTE_MINIMAL|writer.writerow|escape|neutralis"`
- captured_output:
  ```text
  12:* **Comma delimiter, RFC 4180 quoting.** ``QUOTE_MINIMAL`` quotes a field exactly when
  89:    return str(value)
  110:        quoting=csv.QUOTE_MINIMAL,
  113:    writer.writerow(COLUMNS)
  115:        writer.writerow(row_values(row))
  ```
- interpretation: at the base `_cell` ends in `return str(value)` and no line mentions escaping or neutralising: a text cell is written as it came. The serializer is the only writer of the run CSV (`export_run_csv` calls `render_csv`, `src/auditmanager/exports/service.py`).

### P-02 — the base exports a hostile cell unchanged, each of the six classes

- captured_at: 2026-10-27
- command: `PYTHONPATH=src python probe_cells.py` (run on the base tree before the first edit; the script is below)
- captured_output:
  ```text
  '=HYPERLINK("http://x","y")' -> '=HYPERLINK("http://x","y")'
  '+1' -> '+1'
  '-5' -> '-5'
  '@SUM(1)' -> '@SUM(1)'
  '\tx' -> '\tx'
  '\rx' -> '\rx'
  'plain' -> 'plain'
  ```
- interpretation: each of the six first characters of `R-146ax` reaches the file as written, and `plain` is the control. `probe_cells.py`:
  ```python
  from auditmanager.exports.query import ExportRow
  from auditmanager.exports.serializer import row_values
  def mk(**kw):
      base = dict(project_uid="p", document_uid="d", version_uid="v", run_id="r", run_state="published",
                  provider_mode="recorded", finding_uid="f", finding_observation_id="o", category="c",
                  finding_text="t", recommendation_text=None, evidence_page=1, evidence_quote="q",
                  current_verdict="pending", latest_comment=None, latest_decision_id=None,
                  decision_recorded_at=None, evidence_ordinal=1)
      base.update(kw)
      return ExportRow(**base)
  for q in ['=HYPERLINK("http://x","y")', "+1", "-5", "@SUM(1)", "\tx", "\rx", "plain"]:
      print(repr(q), "->", repr(row_values(mk(evidence_quote=q))[12]))
  ```

### P-03 — the two other exports already neutralise, and say how

- captured_at: 2026-10-27
- command: `rg -n "Inline strings are text|t=.inlineStr|xlsx_count_invalid" src/auditmanager/exports/xlsx/writer.py; rg -n "^FORMULA_TRIGGERS|def escape_formula|return \"'\" \+ text" src/auditmanager/optimisation/proposals/export.py`
- captured_output:
  ```text
  137:    # Inline strings are text even when their first character is =, +, - or @.
  139:        f'<c r="{address}" s="{style}" t="inlineStr"><is>'
  146:        raise ValueError("xlsx_count_invalid")
  93:FORMULA_TRIGGERS: Final[frozenset[str]] = frozenset({"=", "+", "-", "@", "\t", "\r", "\n"})
  107:def escape_formula(text: str) -> str:
  111:        return "'" + text
  ```
- interpretation: the XLSX writer stores every string as an `inlineStr`, which is text whatever its first character, and refuses a negative number (`value < 0` -> `xlsx_count_invalid`), so a number never starts with `-` there. The optimisation CSV prefixes `'` on the same six characters plus a line feed, looking past leading spaces. The run CSV rule of this task is the ruling's wording (the first character, six characters) and is equivalent in intent. `escape_formula` lives in another bounded context (`optimisation`) and is not imported (`AGENTS.md` section 4: no deep imports).

### P-04 — the only integer column is a page number, at least 1

- captured_at: 2026-10-27
- command: `rg -n "evidence_page: int|ck_finding_evidence_page_number" src/auditmanager/exports/query.py db/migrations/versions/20260910_0002_pc01_schema.py`
- captured_output:
  ```text
  db/migrations/versions/20260910_0002_pc01_schema.py:1001:            CONSTRAINT ck_finding_evidence_page_number CHECK (page_number >= 1),
  src/auditmanager/exports/query.py:139:    evidence_page: int
  ```
- interpretation: of the nineteen columns exactly one is an integer, `evidence_page`, and the database refuses a page below 1. So no numeric column of the CSV legitimately starts with `-`; the decision on negative numbers (a number is not a text cell and is never altered; a negative number inside a text column is text and is neutralised) changes no real cell.

### P-05 — the frozen reference of the run CSV holds no cell that starts with a trigger

- captured_at: 2026-10-27
- command: `python3 -c "import json,base64,csv,io;d=json.load(open('tests/characterization/w13_baseline/records/12-exportRunCsv.success.json'));t=base64.b64decode(d['response']['body']['base64'])[3:].decode();r=list(csv.reader(io.StringIO(t,newline='')));print(len(r)-1,'rows',len(r[0]),'columns');print([c for row in r for c in row if c[:1] in ('=','+','-','@','\t','\r')])"`
- captured_output:
  ```text
  5 rows 17 columns
  []
  ```
- interpretation: the byte-for-byte record of `exportRunCsv` (`tests/characterization/w13_baseline/records/12-exportRunCsv.success.json`, projected to nineteen columns by `W56A-INT-CSV-CHARACTERIZATION-COMPAT-01`) has five rows and no cell starting with any of the six characters, so the rule changes none of its bytes and the record is not edited. The other places that pin CSV bytes (`tests/integration/exports/test_csv_contract.py`, `test_v2_csv_severity.py`, `test_frozen_column_list.py`) assert on the recorded run's real cells, which `P-05`'s result and `tests/integration/exports/test_csv_formula_neutralisation_over_a_run.py` show have none either. No reference file is updated.

### P-06 — the registration cap at the base is a count of pending requests only

- captured_at: 2026-10-27
- command: `git show 9e42c18a:src/auditmanager/access/registrations.py | rg -n "^MAX_PENDING_REQUESTS|^_COUNT_PENDING|raise _conflict\(\"queue_full|take_queue_lock\(session\)|login_has_pending_request\(session"`
- captured_output:
  ```text
  111:MAX_PENDING_REQUESTS: Final[int] = 100
  190:_COUNT_PENDING = text("SELECT count(*) FROM registration_request WHERE status = 'pending'")
  356:        take_queue_lock(session)
  359:        if login_has_pending_request(session, email):
  362:            raise _conflict("queue_full", "too many registration requests are pending")
  420:        take_queue_lock(session)
  ```
- interpretation: `submit` takes the queue lock (356), refuses a held login, a pending login and then 100 pending requests (362) with `conflict` / `queue_full`. Nothing limits requests per unit of time, and a decided request frees its place at once. The new check goes after 362, under the same lock.

### P-07 — a single source fills the queue at the base

- captured_at: 2026-10-27
- command: `N=45 python flood.py` (run on the base tree before the first edit of `registrations.py`; the script opens one transaction on the private database `auditmanager_sh02`, calls `RegistrationRepository().submit` 45 times with distinct logins and policy-compliant passwords, prints the outcome and rolls back)
- captured_output:
  ```text
  database: auditmanager_sh02 MAX_PENDING_REQUESTS = 100
  submitted 45 requests in one transaction (one address, one moment): accepted=45 refused=0 reasons=[] in 5.6s
  pending: 45  in last 24h: 45
  rolled back; rows left:
  ```
- interpretation: forty-five requests in six seconds, none refused; the only limit is the 100-slot count. `EXPOSURE-REVIEW-02.md` `F-19` puts a single address at about a quarter of an hour through the edge: `(100 - 10) / 6 = 15.0` minutes at 6 r/m after a burst of 10 (`python3 -c "print((100-10)/6)"` printed `15.0`). Through the browser the edge zone is not met at all (`P-10`).
  `flood.py`:
  ```python
  import os, time
  from sqlalchemy import text
  from sqlalchemy.orm import sessionmaker
  from auditmanager.access.registrations import RegistrationRepository, MAX_PENDING_REQUESTS
  from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
  from auditmanager.shared.db.engine import create_database_engine
  from auditmanager.shared.errors import DomainError

  engine = create_database_engine(DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"])))
  print("database:", engine.url.database, "MAX_PENDING_REQUESTS =", MAX_PENDING_REQUESTS)
  N = int(os.environ.get("N", "45"))
  connection = engine.connect()
  transaction = connection.begin()
  session = sessionmaker(bind=connection, expire_on_commit=False)()
  repo = RegistrationRepository()
  accepted = refused = 0
  started = time.monotonic()
  reasons = set()
  for index in range(N):
      try:
          repo.submit(session, login=f"flood{index:03d}@example.com", password="Qz7-flood-passphrase-%03d" % index,
                      last_name="Потопов", first_name="Иван")
          accepted += 1
      except DomainError as exc:
          refused += 1
          reasons.add(str(exc.detail_fields))
  print(f"submitted {N} requests in one transaction (one address, one moment): accepted={accepted} refused={refused} reasons={sorted(reasons)} in {time.monotonic()-started:.1f}s")
  print("pending:", session.execute(text("select count(*) from registration_request where status='pending'")).scalar_one(),
        " in last 24h:", session.execute(text("select count(*) from registration_request where submitted_at > now() - interval '24 hours'")).scalar_one())
  transaction.rollback(); connection.close(); engine.dispose()
  print("rolled back; rows left:", end=" ")
  ```

### P-08 — the table: `submitted_at`, three states, and a decision needs a user

- captured_at: 2026-10-27
- command: `rg -n "submitted_at +timestamptz|created_at|CHECK \(status IN|decided_by IS NOT NULL" db/migrations/versions/20261005_0015_accounts_roles_registration.py | head`
- captured_output:
  ```text
  270:            submitted_at           timestamptz NOT NULL DEFAULT now(),
  300:                CHECK (status IN ('pending', 'approved', 'rejected')),
  320:                    AND decided_at IS NOT NULL AND decided_by IS NOT NULL
  324:                    AND decided_at IS NOT NULL AND decided_by IS NOT NULL
  ```
- interpretation: (1) the existing column the brief calls `created_at` is `submitted_at`; there is no `created_at`. (2) The states are exactly `pending`, `approved`, `rejected`, closed by `ck_registration_request_status`, by the contract's `registration_request` machine and by `trg_registration_request_guard` (a row may only be inserted pending and leave it by one decision). (3) A decided row must name `decided_by`, a foreign key to `app_user`, and `rejected` also a reason. No existing state means "expired" or "withdrawn", and moving a stale request to `rejected` from the unauthenticated submit path would need a decider that is not a person. The brief says: if no existing state fits, do only (1) and report. This task does so.

### P-09 — the closed error code the refusal must use

- captured_at: 2026-10-27
- command: `rg -n "queue_full" contracts/domain/v1/error-codes.json | cut -c1-120; rg -n "queue_full" web/src/features/register/model/exchange.ts | cut -c1-120`
- captured_output:
  ```text
  182:        "conflict_reason (W49-SEAL-01, R-55/R-61) classifies the account and registration conflicts: login_taken (an
  26:    case 'queue_full': return 'Очередь заявок заполнена. Попробуйте позже.'
  ```
- interpretation: `conflict_reason` is a closed classifier whose registration values are `login_taken`, `request_pending`, `queue_full`; the refusal of the day cap is `conflict` / `queue_full`, so no new code and no contract change. The browser already renders `queue_full` as «Очередь заявок заполнена. Попробуйте позже.», which is true of a spent day as well.

### P-10 — the nginx zone for registration is the status zone, and the browser does not meet it

- captured_at: 2026-10-27
- command: `rg -n "^limit_req_zone .guest_registration_client|\"POST:/api/v1/registrations|limit_req zone=guest_registration" infra/deploy/proxy/nginx.conf infra/deploy/proxy/tls-server.conf; rg -n "THROTTLED_OPERATIONS =|\"guest_registration\": THROTTLED_OPERATIONS" tests/contract/test_proxy_rate_limits.py; sed -n 107,108p infra/deploy/proxy/nginx.conf`
- captured_output:
  ```text
  infra/deploy/proxy/tls-server.conf:132:        limit_req zone=guest_registration burst=10 nodelay;
  infra/deploy/proxy/tls-server.conf:155:        limit_req zone=guest_registration burst=10 nodelay;
  infra/deploy/proxy/nginx.conf:126:    "POST:/api/v1/registrations"        $binary_remote_addr;
  infra/deploy/proxy/nginx.conf:127:    "POST:/api/v1/registrations/status" $binary_remote_addr;
  infra/deploy/proxy/nginx.conf:130:limit_req_zone $guest_registration_client zone=guest_registration:1m rate=6r/m;
  infra/deploy/proxy/nginx.conf:345:        limit_req zone=guest_registration burst=10 nodelay;
  infra/deploy/proxy/nginx.conf:398:        limit_req zone=guest_registration burst=10 nodelay;
  83:THROTTLED_OPERATIONS = frozenset({"submitRegistration", "readRegistrationStatus"})
  107:    "guest_registration": THROTTLED_OPERATIONS,
  # the browser's own registration goes through `/bff/v1` to `http://api:8000` and never meets
  # this limit (it meets the web tier's bucket instead, keyed by `X-Real-IP` below).
  ```
- interpretation: `POST /api/v1/registrations` and `POST /api/v1/registrations/status` are keyed into one zone, `guest_registration`, 6 r/m per address with a burst of 10 and `nodelay`, applied in both server bodies and in the upload location, and `tests/contract/test_proxy_rate_limits.py` binds both operations to that zone (`ZONES`). So the registration call is exactly as tight as the status call, and no test pins a tighter intent: part (3) of the brief changes nothing in `infra/deploy/proxy/*.conf`. The comment at nginx.conf 107-108 is the reason the day cap lives in the application: the browser's registration reaches the API through the web tier and never meets this zone, and the web tier's bucket is in memory and per address (`F-18`, `PROD-05`'s lane).

### P-11 — the tests that fill the queue to 100 fill it in one instant

- captured_at: 2026-10-27
- command: `git show 9e42c18a:tests/integration/access/test_registrations.py | rg -n "MAX_PENDING_REQUESTS - 1"; git show 9e42c18a:tests/integration/api/qa_w49/test_qa_w49_queue_cap.py | rg -n "_fill\("`
- captured_output:
  ```text
  129:        for index in range(MAX_PENDING_REQUESTS - 1):
  35:def _fill(engine: Engine, count: int) -> None:
  70:    _fill(migrated_engine, 98)
  113:    _fill(migrated_engine, 99)
  ```
- interpretation: three tests (`test_the_queue_holds_100_and_refuses_the_101st`, `test_the_hundredth_is_accepted_the_hundred_and_first_is_queue_full`, `test_two_applications_racing_for_the_last_place_get_one`) write 98 or 99 pending rows with the default `submitted_at = now()`, so with a day cap of 40 they would be refused by the day cap before the pending cap they test. They are the only modified tests; each is changed by writing its filler rows three days old. Their assertions are untouched (see the report).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/exports/**`
- `src/auditmanager/access/registrations.py`
- `tests/unit/exports/**`
- `tests/integration/exports/**`
- `tests/integration/access/**`
- `tests/integration/api/qa_w49/test_qa_w49_queue_cap.py`
- `tests/characterization/w13_baseline/records/12-exportRunCsv.success.json`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `tests/contract/test_proxy_rate_limits.py`
- `docs/program/SMALL-HARDENING-02.md`
- `docs/program/tasks/SMALL-HARDENING-02.md`

## Forbidden hotspots

- `contracts/**`
- `db/migrations/**`
- the composition root (`src/auditmanager/bootstrap/**`)
- `web/**`
- the section, АР and comparison code
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings, root dependency/lock files

## Non-goals

- the disclosure of existing logins (`E-9`): `login_taken` and `request_pending` are answered as before
- the account brake (`F-09`) and the BFF doors' `limit_req` (`F-18`, `PROD-05`)
- the switch of `R-146ba` (part (c)) and `A-9` (part (d))
- the short life of a pending request, an `expired`/`withdrawn` state, any migration or contract change
- a per-address limit inside the application (it never sees the address)

## Deliverables

- `src/auditmanager/exports/serializer.py`: `FORMULA_TRIGGERS`, `FORMULA_NEUTRALISER`, `neutralise_formula`, applied to every text cell in `_cell`
- `src/auditmanager/access/registrations.py`: `MAX_REQUESTS_PER_DAY = 40`, `REQUEST_WINDOW_HOURS = 24`, the count over `submitted_at` and the refusal in `submit`
- tests: `tests/unit/exports/test_csv_formula_neutralisation.py`, `tests/integration/exports/test_csv_formula_neutralisation_over_a_run.py`, `tests/integration/access/test_registration_day_cap.py`, two added tests in `tests/integration/api/qa_w49/test_qa_w49_queue_cap.py`, and two fixture-only edits (the age of the filler rows) that touch three existing tests
- `docs/program/SMALL-HARDENING-02.md`

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/exports tests/integration/exports tests/unit/access tests/integration/access tests/integration/api` with `DATABASE_URL` and `POSTGRES_DB` pointing at a private database created for the run and dropped after (the lane stack's other variables from the untracked `.env`)
- expected: all pass; then `tests/contract` without `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py`, and `git diff --check`

## Integration contract

The integrator can rely on: (1) every text cell of `GET /runs/{run_id}/export.csv` that begins with `=`, `+`, `-`, `@`, tab or carriage return is served with one extra leading `'`, and no other byte of the file differs from before; (2) `POST /api/v1/registrations` answers `409` / `conflict` / `details.conflict_reason = queue_full` when 40 requests were accepted in the previous 24 hours, in any state, as it already did for 100 pending; the shape of the request, of the success answer and of every other refusal is unchanged; (3) no contract file, migration or web file changed, so the contract prose that says «100 pending requests in all `queue_full`» (`contracts/api/v1/openapi.json`, `contracts/domain/v1/state-machines.json`) is now incomplete and is the contract slot's to amend.

## Failure/idempotency/security cases

- a cell that starts with a trigger inside a quoted CSV field (comma, quote, line break in it): the apostrophe goes in front of the cell's text and the quoting is applied after, so the file parses to `'` + original (tested for all six classes and a mixed row)
- an empty cell, a cell with a leading space, a cell with a trigger in the middle, a cell that already begins with `'`: unchanged
- two submissions racing for the last place of the day: one is accepted and one is `queue_full`, because the count is read under the queue lock (tested over HTTP with the interleaving forced)
- a refused attempt writes nothing and so does not spend the window
- the day cap answer is the same for any login, so it adds nothing to the disclosure of `E-9`

## Rollback / feature flag

Not a flag. Reverting `FORMULA_TRIGGERS` use in `_cell` restores the previous CSV bytes; reverting the one check in `submit` restores the previous registration behaviour. Both are single-commit reverts (`79f42492`, `42ea4768`).

## Handoff

- changed files: see `docs/program/SMALL-HARDENING-02.md`
- commands/results: see `docs/program/SMALL-HARDENING-02.md`
- known limits: the short life of a pending request is not built (no existing state fits); the day cap is global, not per address; the contract prose about «100 pending» is not amended (contracts are forbidden here)
- integration notes: see `docs/program/SMALL-HARDENING-02.md`
