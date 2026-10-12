# Task W55A-FIX — W55a judge findings: refusals instead of 500s, a strict snapshot history, consistent designation tokens, a v2-only bundle, and isolated lease tests

## Outcome
The W55a judges' minor findings are closed: forged cursors, NUL, blank and oversized-range inputs are refused with 422, the current-snapshot history cannot be reused or bypassed, designation tokens split the same way in Python and SQL, a non-`characters-v2` bundle is refused at export, and two order-dependent lease tests are isolated.

## Depends on
- `W55A-JUDGE-X`, `W55A-JUDGE-Y` (`docs/program/reviews/W55A-JUDGE-{X,Y}.md`), `W55A-FIX-DB` (merged)

## Frozen inputs
- domain contract: after `W55A-SEAL-01`
- API contract: after `W55A-SEAL-01` (45 / 52 / 116)
- analysis/comparison/event contract: unchanged
- migration head: `0020_norms_search` (unreleased; this task may amend its guard)
- base commit: the FIX-DB merge on `integration/w54`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/norms/search/**`, `src/auditmanager/api/schemas/content.py`, `src/auditmanager/api/routers/norms.py`, `src/auditmanager/norms/current_snapshot.py`, `src/auditmanager/norms/bundle/{export,manifest,cli}.py`, `db/migrations/versions/20261012_0020_norms_search.py` (guard triggers only), `tests/integration/{norms,api,db,runs,jobs}/**` (new cases; and the two order-dependent lease tests named in `docs/program/W55A-FIX-DB.md`), `tests/contract/**` pins only if a change moves them, `docs/program/W55A-FIX.md`

## Forbidden hotspots
- contracts; migrations other than `0020`'s guard; lock files; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- X-M6 (search connection pool; registered as a debt).

## Deliverables
- X-M1: cursor ordinal bounded to ≤ 2^31−1; `OverflowError` in `_parse_instant` caught → `422 cursor/format`; tests for both forged tokens.
- X-M2: control characters (incl. NUL) in `q` refused with `422 q/format`.
- X-M3: `Range` digits bounded (`\d{0,19}`) or `ValueError` mapped to `format`; test with a 5000-digit range.
- X-M5: a `q` whose parse yields no designation, clause or words refused with `422 q/format`.
- X-M4 + Y-3: in `0020`, the current-snapshot guard requires `NEW.event_id` to be the newest event and not referenced by any earlier change; a deferred constraint trigger on event INSERT requires `norm_current_snapshot.event_id = NEW.event_id` at commit; `BEFORE TRUNCATE` refusal on both tables; an explicit `changed_at` refused or overwritten by `now()`. DB tests for each direct-SQL attack.
- Y-4: the parser rebuilds the designation from its tokens with ASCII separators and maps U+2010–U+2015 to `-` before binding; tests with NBSP, tab and en dash.
- Y-5: `bundle export` refuses a `--chunking-profile` that does not start with `characters-v2:`, and the manifest parser refuses one too.
- Order-dependent tests: `jobs/test_d141…::test_a_final_transaction_longer_than_the_lease_is_not_reclaimed` and `runs/test_w53_jobs_repair.py` count only their own leases (park or scope foreign ones) as `W55A-FIX-DB.md` suggests.

## Required tests
- command: container-free tests now; DB-backed cases may run on a private stack PostgreSQL `57310`, S3 `60910/60911` only when the integrator says the BGE build has finished (one heavy step at a time) — otherwise list the commands.
- expected: exit 0; each fix has a test that fails without it.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; never touch the stand, published refs or other worktrees.
