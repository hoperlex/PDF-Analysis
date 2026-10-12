# W55A-FIX — the W55a judges' findings, closed

**Executor:** lane `agent/w55a-fix`, worktree `.local/worktrees/w55a-fix`.
**Task:** `docs/program/tasks/W55A-FIX.md`. **Base:** `cb4bdf1` (local `integration/w54`: W54 +
W55a + FIX-DB). **Date:** 2026-10-13.
**Inputs:** `reviews/W55A-JUDGE-X.md` (M1–M5), `reviews/W55A-JUDGE-Y.md` (Y-3, Y-4, Y-5),
`W55A-FIX-DB.md` §4.1 (the two order-dependent lease tests).
**Commits:** `bc5a641` (fixes and tests), `e2a0d8f` (inventory reseal); this report is the next
commit.
**Stack:** private `gate-w55a-fix` (PostgreSQL 17 + pgvector on `57310`, MinIO on
`60910/60911`), started only after the integrator's "BGE build done"; torn down at the end.

## 0. Per-finding status

| Finding | Status | Where | Test that fails without it |
| --- | --- | --- | --- |
| X-M1 forged cursor → 500 | **fixed** | `norms/search/cursor.py` | `test_w55a_fix_offline.py` (ordinal, edge instants, both listings, search), `test_w55a_fix_window.py::test_a_forged_ordinal_is_refused_not_a_database_error` |
| X-M2 NUL / control in `q` → 500 | **fixed** | `norms/search/query.py` (`unsearchable`), `service.py` | offline `test_a_control_character_*`, `test_the_search_refuses_it_with_422_before_any_statement[nul…]`; window `test_a_nul_in_q_is_refused_not_a_database_error` |
| X-M3 4 300-digit `Range` → 500 | **fixed** | `api/schemas/content.py` | offline `test_a_range_number_past_nineteen_digits_is_malformed`, `test_the_norm_pdf_answers_a_5000_digit_range_with_422_and_touches_no_store` |
| X-M4 + Y-3 history bypassable by direct SQL | **fixed** (four parts) | `0020` guard triggers only | `tests/integration/db/test_norms_current_snapshot_strict_history.py` (one test per attack) |
| X-M5 blank `q` sorts the snapshot | **fixed** | `query.py`, `service.py` | offline `test_a_blank_text_*`, `…before_any_statement[space…]`; window `test_a_blank_q_is_refused_not_a_sort_of_the_snapshot` |
| X-M6 search pool | not in scope | — | task non-goal (registered debt) |
| Y-4 NBSP / tab / dash designation → empty page | **fixed** | `query.py` | offline `test_a_designation_is_rebuilt_with_ascii_separators`, `test_the_search_binds_the_rebuilt_designation`; window `test_a_designation_with_unicode_separators_finds_what_ascii_finds` |
| Y-5 non-`characters-v2` bundle | **fixed** | `bundle/{manifest,export,cli}.py` | `tests/integration/norms/bundle/test_w55a_fix_chunking_profile.py` |
| d141 and w53 reclaim tests count foreign leases | **fixed** | the two test files | deterministic reproduction, §4.2 |

Fifteen mutations, applied one at a time and restored with `git checkout`, each turned its tests
red (§4.1).

## 1. What was done, and the readings taken

**X-M1.** `_ordinal` refuses anything outside `0..2^31-1` (`MAX_ORDINAL`: `norm_paragraph.ordinal`
is `integer`), for `s1d` and `p1` alike. `_parse_instant` catches `OverflowError` from
`astimezone` (year 1 at `+05:00`, year 9999 at `-05:00`) as a foreign token. Both answer `422
cursor/format`. The optional HMAC binding was not added: it is not a deliverable, and the
binding's purpose (a token cannot resume another query or snapshot) holds.

**X-M2.** Refused: every Unicode `Cc` character except tab, line feed and carriage return, and
any surrogate (`Cs`). Tab must stay accepted because Y-4 requires `СП<TAB>54` to search. The
refusal is `422 validation_failed {field: q, constraint: format}` and happens before any
statement — `statement_timeout` is not even set.

**X-M3.** `_RANGE` is `^bytes=(\d{0,19})-(\d{0,19})$` with `re.ASCII`. A 20-digit or longer number
is `422 Range/format`. 19 digits still parse and clamp to the object. This is the shared
`ByteRange`, so `streamDocumentVersionContent` is covered too. The SEAL oracle test (48 header/size
cases) is unchanged and green.

**X-M5.** `ParsedQuery.empty` is "no designation, no clause, no words", which is exactly a blank
`q` (Unicode whitespace only). Refused like X-M2. A `q` of punctuation only (`...`) is still words:
`websearch_to_tsquery` gives an empty query that matches nothing. That is not an unfiltered sort.
The web page already trims `q` and searches nothing when it is empty
(`web/src/app/norms/page.tsx`), so no screen regresses.

**X-M4 + Y-3** (`0020`, guard triggers only; the head stays `0020_norms_search`):

1. **The newest event only.** `am_guard_norm_current_snapshot` now also requires `NEW.event_id` to
   be first in the listing's own order: `changed_at`, then `event_id COLLATE "C"`, both
   descending. Reusing `A→B` after `B→A` is refused (`AM003`, "must name the newest history
   event").

   *"Not referenced by any earlier change"*: with part 2, every event is current when it
   commits, and only a newer event can displace it. So every older event has already been
   referenced by an earlier change, and "newest" is exactly "unreferenced". The newest event is
   named only by the row it would replace, which the existing `NEW.event_id = OLD.event_id` check
   refuses.
2. **Current at COMMIT.** `CREATE CONSTRAINT TRIGGER trg_norm_current_snapshot_event_designates
   AFTER INSERT … DEFERRABLE INITIALLY DEFERRED` requires `norm_current_snapshot.event_id =
   NEW.event_id` at commit.

   Consequence: **one designation per committed transaction**. That is what the setter writes. A
   second designation in the same transaction leaves the first event non-current and is refused.
   Rolled-back transactions never fire deferred triggers, so the PIN window tests and the
   API query-surface seeding keep designating twice in one rolled-back transaction.
3. **TRUNCATE refused** on both tables (`BEFORE TRUNCATE … FOR EACH STATEMENT`). This includes a
   TRUNCATE that reaches them by `CASCADE` from `norms_snapshot`; measured, §4.
4. **`changed_at` is the database's.** The insert trigger `trg_norm_current_snapshot_event_stamp`
   (`BEFORE INSERT`) sets `NEW.changed_at := clock_timestamp()`.

   It overwrites rather than refuses, because a BEFORE trigger cannot tell an explicit value
   from the column default.

   It uses `clock_timestamp()` (the column's own default), not `now()`. Under the setter's
   advisory lock, a designation can begin before the one it waits for commits. Its
   transaction-start time would then sort it below its predecessor, and part 1 would refuse a
   legitimate change.

   A post-dated event (year 2999) would otherwise have blocked every later designation; the
   test covers it.

Downgrade also drops the three new functions (the empty-0020 downgrade/upgrade test passes).

**Y-4.** In the designation only (never the words), `parse_query` does two things:

- maps U+2010–U+2015 to `-` before tokenising (one character for one, so spans are unchanged);
- rebuilds the designation with every run of Unicode whitespace as one ASCII space.

So `СП 54` typed with a no-break space, a tab or an em space, and `СНиП 2.01.07–85` typed with an
en or em dash, are bound as `СП 54` and `СНиП 2.01.07-85`. Every existing expectation
(`ГОСТ_10140-2003`, `СП 54.13330.2022`, …) is unchanged, because ASCII separators are kept as typed.

**Y-5.** `manifest.is_designatable_chunking(profile)` is `parse_chunking_profile` plus
`version == "characters-v2"`. The manifest parser refuses any other profile (`manifest_invalid`):
`verify`, `import` and `report` all parse.

The export refuses one with the new reason word `chunking_profile_refused` at three points:

- in `read_export_source`, before the session is touched;
- in `write_bundle`, before anything is written;
- in the CLI, before the promotion database is opened.

Stricter than "starts with `characters-v2:`": a malformed target (`characters-v2:`,
`characters-v2:01200`) is refused too.

**Lease tests.** Both tests now *park* every unreleased lease that is not their own: its
`expires_at` is set to 2099 for the test, and its original expiry is restored afterwards (only if
still unreleased). The reclaimer can then see only the test's own leases. The literal assertions
are unchanged: `recovered=0` in d141, and `periodic == 1` in w53.

## 2. Changed files (`git diff --name-only cb4bdf1..HEAD`, plus this report)

```
db/migrations/versions/20261012_0020_norms_search.py      (guard triggers only)
src/auditmanager/api/schemas/content.py
src/auditmanager/norms/bundle/cli.py
src/auditmanager/norms/bundle/export.py
src/auditmanager/norms/bundle/manifest.py
src/auditmanager/norms/current_snapshot.py                (docstring only)
src/auditmanager/norms/search/cursor.py
src/auditmanager/norms/search/query.py
src/auditmanager/norms/search/service.py
tests/integration/db/test_norms_current_snapshot_strict_history.py   (new)
tests/integration/db/test_norms_search_migration.py                  (adapted, see below)
tests/integration/db/test_schema_invariant_inventory.py              (reseal)
tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py
tests/integration/norms/bundle/conftest.py                           (reset helper)
tests/integration/norms/bundle/test_w55a_fix_chunking_profile.py     (new)
tests/integration/norms/custody/conftest.py                          (reset helper)
tests/integration/norms/reset.py                                     (new helper)
tests/integration/norms/search/conftest.py                           (reset helper; designate in one transaction)
tests/integration/norms/search/test_w55a_fix_offline.py              (new)
tests/integration/norms/search/test_w55a_fix_window.py               (new)
tests/integration/runs/test_w53_jobs_repair.py
docs/program/W55A-FIX.md
```

Every path is inside the grant's globs. Some existing test files were edited although the grant's
parenthesis reads "new cases". Each edit was **forced by the `0020` amendment** and is listed here
for the integrator.

The search, custody and bundle fixtures reset with `TRUNCATE … norms_snapshot … CASCADE`. That
TRUNCATE now reaches the refused tables, so the fixtures call
`tests/integration/norms/reset.py::truncate_tables`. The helper lifts the two refusals with the
owner's `ALTER TABLE … DISABLE TRIGGER`, in the same transaction, and asserts that both triggers
are enabled again.

The search fixture's `designate` committed the event and the current row in two transactions; it
now uses one.

`test_norms_search_migration.py` changed in four places:

- the trigger set gains the four new names;
- the two retained-data downgrade cases become one. A history row without a current row can no
  longer exist, so the case asserts the exact list `(norm_current_snapshot,
  norm_current_snapshot_event)`, which still proves both probes;
- the guard walk-through ends in a rollback, because its refused attempts leave orphan events;
- the append-only test now designates, so that its transaction can commit.

`test_schema_invariant_inventory.py` is resealed with the measured values (§4). No `tests/contract`
pin moved.

## 3. Checks

| Command | Result |
| --- | --- |
| `git diff --check cb4bdf1..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager db/migrations tests/integration/{norms,db,runs,jobs} tests/contract` | exit 0 |
| `pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` (no `DATABASE_URL`) | **619 passed**, 50 subtests (= base) |
| container-free, no service variables: `tests/integration/norms/search/{test_query_parsing,test_cursor_and_fragment,test_norms_surface_offline,test_w55a_fix_offline}.py`, `tests/integration/norms/bundle/{test_w55a_fix_chunking_profile,test_manifest,test_export_offline,test_import_refusals_offline,test_custody_reconcile_offline,test_layout,test_identity_offline}.py`, `tests/integration/api/{test_range_rules,test_document_content_streaming,test_streaming_wire_response}.py`, `tests/integration/runs/test_w55a_pin_offline.py` | **284 passed** |
| DB, first stack: `tests/integration/db/test_norms_current_snapshot_strict_history.py tests/integration/db/test_norms_search_migration.py` | **30 passed** |
| DB, first stack: `tests/integration/norms/{search,custody,bundle}` | **368 passed** |
| DB, **fresh** stack (volumes removed, `make up && make migrate` to `0020_norms_search`): `pytest -q -rfE tests/integration/norms tests/integration/db tests/integration/runs tests/integration/jobs` | **1267 passed, 1 skipped, 1 failed** in 164.7 s. The failure is environmental: `test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_resolves_to_the_exact_real_corpus` asserts `.local/norms/corpus` exists, and this worktree has no git-invisible corpus. With a temporary read-only symlink to the main checkout's corpus (removed straight after): **3 passed**. Both order-dependent lease tests passed in the run. |
| same fresh stack, after: `tests/integration/api/{test_query_surface,test_range_rules,test_document_content_streaming}.py tests/integration/composition/{test_an_absent_parent_is_not_an_empty_page,test_router_answers}.py` | **82 passed** |

Every run used `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`
with the lane `.env` exported, one pytest at a time.

## 4. Measurements

### 4.1 Mutations (`scratchpad/mutate.py`; tree clean afterwards)

Every mutation turned its tests red:

| Mutation | Red |
| --- | --- |
| ordinal unbounded | 3 |
| `OverflowError` uncaught | 4 |
| control characters allowed | 15 |
| blank `q` allowed | 13 |
| service refusal removed | 16 |
| designation left raw | 25 |
| dashes not mapped | 16 |
| `Range` unbounded | 5 |
| any chunking profile designatable | 5 |
| CLI check removed | 1 |
| parser check removed | 6 |
| `0020`: no newest-event check | 1 (`test_an_older_event_cannot_designate_again`) |
| `0020`: no commit-time check | 2 |
| `0020`: TRUNCATE allowed | 5 |
| `0020`: `changed_at` kept | 2 |

### 4.2 The lease tests, reproduced deterministically

A scratch pytest plugin (`-p w55afix_foreign_leases`, outside the tree) moves every unreleased
lease to `now() + offset` just before the test body. That is after the fixtures, so after
`quiet_queue`'s reclaim. The foreign leases themselves were made by
`tests/integration/runs/test_durable_effect_boundaries.py`, the source FIX-DB identified: 9 leases,
60 s each.

| Test | Base (`cb4bdf1`) | Fixed |
| --- | --- | --- |
| w53, offset −1 s | **failed**: `{'periodic': ('committed', 10)} != … 1` | **passed**; the 9 foreign leases are unreleased afterwards with their expiry restored |
| d141, offset +1.5 s | **failed**: `sweeps` not all `recovered=0` | **passed**; same restoration |

### 4.3 Inventory reseal

The delta was measured on two fresh databases: one with `0020` as at `cb4bdf1`, whose inventory
equalled the old seal, and one with this lane's `0020`. Every family's rows were diffed:

- constraints 449 → **450**: the constraint trigger's own `contype t` row;
- triggers 42 → **46**: `…event_stamp`, `…event_designates`, and the two `…no_truncate`;
- functions 15 → **18**: three new functions, plus `am_guard_norm_current_snapshot` redefined;
- every other family is byte-identical.

Both TRUNCATE-by-`CASCADE`-from-`norms_snapshot` refusals were observed on PostgreSQL 17.

## 5. Contracts, risks, integrator

**Contracts.**

- No change to `contracts/**`, the OpenAPI document or the error catalog. The refusals reuse
  `validation_failed` with `field` and `constraint`.
- The migration head is unchanged.
- New internal names:
  - `norms.search.query.unsearchable` and `ParsedQuery.empty`;
  - `cursor.MAX_ORDINAL`;
  - `bundle.manifest.is_designatable_chunking` and `bundle.export.require_designatable_chunking`;
  - the bundle reason word `chunking_profile_refused`.

**Risks and limitations.**

- `0020` is amended in place, so a database already at `0020` would keep the old guard. None should
  exist outside throwaway lanes (unreleased, `R-111`); migrate such a lane fresh, or downgrade the
  empty `0020` and upgrade again.
- "Newest" rests on the database clock. If it steps backwards between two designations, the later
  one is refused (`AM003`, a 500 through the setter) until the clock passes the earlier event.
- The database still does not check qualification. A direct-SQL designation of a non-qualifying
  snapshot, with its own event, remains possible (not a finding).
- Designation punctuation other than separators (a trailing comma, `СП 54,`) still binds into the
  last token. Y-4 covered whitespace and dashes only.
- The suites' reset needs table ownership (`DISABLE TRIGGER`). Every suite runs as the migration
  owner.

**Integrator.**

1. Read the diff and this report, then merge `agent/w55a-fix`.
2. Measure on a **fresh** database: `0020` and the inventory changed, so an old lane database
   holds the old guard.
3. For the corpus-dependent bake-off test, run where `.local/norms/corpus` exists.

## 6. Containment

- `git diff --name-only cb4bdf1..HEAD` is §2. Every path is inside the grant.
- Not touched:
  - contracts, other migrations, lock files;
  - `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`;
  - refs, tags, the stand, other worktrees.
- No push, merge, tag, stash or worktree. No process was killed.
- The stack was stopped with `make down`. Only `gate-w55a-fix-postgres-data` and
  `gate-w55a-fix-s3-data` were removed, `.env` was deleted, and the temporary corpus symlink was
  removed.
- `git status --porcelain -uall` is empty at this commit.
