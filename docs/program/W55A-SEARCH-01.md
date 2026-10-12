# W55A-SEARCH-01 — hand-back report

- Task: `docs/program/tasks/W55A-SEARCH-01.md`. Grant: `dispatch/W55-PLAN.md` §A4 Stage B
  item 2, plus this file. Design: §A3.2, §A3.4, §A3.6; rulings R-80, R-112, R-113.
- Branch `agent/w55a-search-01`, worktree `.local/worktrees/w55a-search`. Base `60c6e6e`
  (local `integration/w54`: W54, the W55a seal with head `0020_norms_search`, WEB-NORMS and
  CONTENT merged).
- Commits: `a8f57bb` (implementation and tests), `83f6aea` (an `ORDER BY` fix found in
  review), and `ac81635` (a structural guard). This report is the last commit.
- Checks follow `R-102`/`R-111`: light and container-free. **No container was started and no
  database was reached.** The database- and S3-backed cases are written; the window commands
  are in §5.

## 0. What was built

| Plan item | Where |
| --- | --- |
| The sealed stubs replaced: the six norms reads and the designation (`NormsSearchAdapter`), and the norm PDF (`NormContentAdapter`). | `bootstrap/adapters.py`, wired in `bootstrap/composition.py` |
| **Current snapshot (§A3.2).** The reader `current_snapshot(session)`, the predicate `qualification(session, id)`, the setter and the history listing. | `norms/current_snapshot.py`, exported through `norms/public.py` |
| **The predicate.** (a) a `norm_embedding_build` row for `bge-m3-dense-v1` over `characters-v2:*`. W54's loader writes that completion row last, in the windows' own transaction, so the row means the build is complete. (b) every document has a `norm_source` binding in the slot `(norm_document, <ndoc>, pdf, <source_document_ref>)`. That is the slot W54's bundle declares for `document.pdf`, and `0018`'s guard admits a binding only for a confirmed admission. | `BUILD_COMPLETE_SQL`, `SOURCES_CONFIRMED_SQL` and `PDF_BINDING_SQL`. These are used **verbatim** by the setter, by `listNormSnapshots.qualified`, by `content_available` and by the PDF read. |
| **Setter order.** It runs under one advisory transaction lock and checks in this order: unknown target → `404 NormsSnapshot`; target already current → replay, nothing written, `expected_current` ignored; no build → `required_norm_unavailable/norm_embedding_build`; a document without its PDF binding → `…/norm_source`; stale `expected_current` → `409 conflict/stale_current_snapshot`. Otherwise it appends one event and then writes the singleton row that names it. | `set_current_snapshot` |
| **Text search (§A3.4).** `q` is split into a designation, a clause and words. **Designation:** a document-type word from a closed folded list (ГОСТ, СП, СНиП, ВСН, МДС, РД, ПЭУ…) followed by its tokens up to the last numeric one; `norm_designation_tokens` matches it in SQL against the leading tokens. **Clause:** `п. 7.1.4`, matched as a dotted-segment prefix. **Words:** `websearch_to_tsquery('russian')`, ranked by `ts_rank_cd`. Without words, results are ordered by designation, then document, then `ordinal`. | `norms/search/query.py`, `service.py` |
| **Window and cursor.** The candidates are cut to **1 000** before paging. The cursor binds the first 128 bits of SHA-256 over `(q, snapshot)` plus the position: the rank as exact `float4` bits and `npar_`, or `ndoc_`, `ordinal` and `npar_`. A cursor from another query, another snapshot or another mode is refused as `validation_failed/cursor/format`. | `norms/search/cursor.py` |
| **Scope.** The current snapshot by default. An explicit snapshot is used only if some history row has it as `to`. Otherwise the search refuses `required_norm_unavailable/norms_snapshot`. | `resolve_scope` |
| **Timeout.** `set_config('statement_timeout', ms, true)` runs first in the search transaction. SQLSTATE `57014` maps to `422 validation_failed {field: q, constraint: norms_search_too_broad}`. Other database failures stay failures. | `service.search`; `AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS` in `bootstrap/settings.py`: default 3000, integer 1–600 000, malformed values refuse the start |
| **Fragment (NORM-Q01).** `ts_headline` with two private-use markers, which are first stripped from the text and then turned into plain text with code-point offsets. Designation and clause hits carry the paragraph's opening, unmarked. | `norms/search/fragment.py` |
| **PDF.** CONTENT's recipe in its order: the binding (`404`, or `422 norm_source`), then the range resolved against the binding's size, then `open_stream` with the binding's SHA-256 and size. Storage failures are typed as in ingest, with `role: norm_source`. A malformed `Range` on an unknown document is `404`, which is `_parsed_range`'s precedence from `documents.py`. | `NormContentAdapter`, `api/routers/norms.py` |

## 1. Changed files

`git diff --name-only 60c6e6e..HEAD`: 24 paths, plus this report.

- **Source.**
  - New: `src/auditmanager/norms/current_snapshot.py`, `src/auditmanager/norms/search/{__init__,cursor,fragment,query,service}.py`.
  - Changed: `src/auditmanager/norms/public.py` (export lines), `src/auditmanager/api/routers/norms.py` (the content body's `Range` precedence and the stub sentence of its docstring), `src/auditmanager/bootstrap/{adapters,composition,settings}.py`.
- **Tests, new.** All under `tests/integration/norms/search/`:
  - `conftest.py` and `support.py`;
  - offline: `test_query_parsing.py`, `test_cursor_and_fragment.py`, `test_norms_surface_offline.py`;
  - window: `test_search_window.py`, `test_current_snapshot_window.py`, `test_norm_pdf_window.py`, `test_norms_roles_window.py`.
- **Tests, changed.**
  - `tests/integration/composition/test_router_answers.py`: `SEALED_STUB_GETS` emptied.
  - `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`: `SEALED_STUB_COLLECTIONS` and `SEALED_STUB_ADDRESSED` emptied. `QUERY_OPERATIONS` keeps the bare-`q` refusal. With `q`, the answer is `200` with a page or `422 required_norm_unavailable/norms_snapshot`, never `503`.
  - `tests/integration/composition/test_settings_defaults.py`: the timeout's name, default, override and refusals.
  - `tests/contract/api_v1/test_w55a_norms_seal.py`: **outside the grant, see §6.**

## 2. Checks run

All on the committed tree unless stated otherwise.

| Command | Result |
| --- | --- |
| `git diff --check 60c6e6e..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager tests/integration/norms/search tests/integration/composition tests/contract/api_v1` | exit 0 |
| `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **619 passed**, 50 subtests (base 620; one sealed-stub case retired, §6) |
| `pytest -q tests/integration/norms/search/{test_query_parsing,test_cursor_and_fragment,test_norms_surface_offline}.py` | **66 passed** (24 + 18 + 24) |
| `pytest -q tests/integration/api/test_document_content_streaming.py tests/integration/api/test_streaming_wire_response.py` | passed. CONTENT's suites are unaffected. |
| `pytest -q tests/integration/composition/test_settings_defaults.py`, run with placeholder service variables (`DATABASE_URL=postgresql+psycopg://x:y@127.0.0.1:1/z`, `S3_*`); `load()` validates them and never connects | **19 passed** |
| `pytest -q tests/integration/composition/test_every_port_implementation_is_whole.py` (commit `a8f57bb`) | 18 passed (3 min 56 s) |
| `pytest --co` over `tests/integration/{composition,norms/search,api}` and `tests/integration/db/test_norms_search_migration.py`, with no `DATABASE_URL` | 1363 collected, 0 errors |
| Every SQL statement and every search variant (2 modes × designation × clause) rendered and parsed by `pglast` 8.5 in a scratch venv | 21 of 21 parse. This checks **syntax only**. It is how the `ORDER BY` fix in `83f6aea` was found, by reading the parsed shapes against PostgreSQL's alias rule. |

**Each new behaviour fails without its change.** Fifteen mutations were applied one at a time
by `scratchpad/tools/mutate.py`. Each file was restored with `git checkout -- <file>`, and the
tree was clean afterwards. All 15 turned their tests **red**:

- the timeout mapping removed;
- the timeout never set;
- a never-current snapshot accepted;
- none-current answering a page;
- the cursor binding unchecked;
- the replay moved after the stale check;
- the stale check removed;
- either qualification half ignored (two mutations);
- `Range` parsed before the document lookup;
- the range resolved without the binding's size;
- any first token taken as a designation;
- the clause not extracted;
- the highlights left as markup;
- the timeout default moved.

**Not run.** These can only be proved against PostgreSQL and S3, in the window (§5):

- morphology;
- `СП 54` ≠ `СП 542` in SQL;
- unreliable paragraphs absent;
- the 1 000-hit cap;
- cancellation under a real lock;
- both qualification conditions and the agreement of `qualified` with the setter;
- one history row per change;
- the PDF from MinIO;
- role-less refused on all seven, and events admin-only, on the composed application.

## 3. Contracts

No change to `contracts/**`, migrations (head `0020_norms_search`), the OpenAPI document, the
error catalog or the surface counts. Only values the seal registered are used:

- `required_norm_unavailable` with `reference_kind` `norms_snapshot`, `norm_embedding_build` or `norm_source`;
- `conflict` with `conflict_reason: stale_current_snapshot`;
- `validation_failed` with `field: q, constraint: norms_search_too_broad`;
- `not_found` with `aggregate_type` `NormDocument` or `NormsSnapshot`.

New **internal** interfaces, from `auditmanager.norms.public`:

- `current_snapshot(session) -> CurrentSnapshot | None`, with `norms_snapshot_id`, `event_id`, `designated_at` and `designated_by`. **This is the reader `W55A-PIN-01` calls.**
- `qualification(session, id) -> Qualification | None`, which W57a extends.
- `set_current_snapshot(session, *, norms_snapshot_id, expected_current, actor_user_uid) -> Designation`.
- `has_been_current`, `list_snapshot_events`.
- `search_norms`, `get_norm_document`, `list_norm_paragraphs`, `list_norm_snapshots`, `norm_pdf_binding`.
- `EventPosition`, `encode_event_cursor`, `decode_event_cursor`, `SEARCH_WINDOW`.

There is one new setting: `AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS`. It is read from the process
environment, which on the stand means `provider.env`. `compose.server.yml` already passes that
file to the API through `env_file`.

### Readings where the plan was silent (conservative choices)

1. **The designation cursor carries `ndoc_`, `ordinal` and `npar_`, not the tokens.** The SQL
   looks the document's key up again. This keeps every token under the contract's 512
   characters whatever a slug holds. The order is designation, then document, then `ordinal`,
   so one document's paragraphs stay together.
2. **Document, paragraph and PDF reads are not scoped to once-current snapshots.** Only search
   carries the scope rule. An administrator can inspect a snapshot before designating it, and
   the corpus stays internal (D-4.1).
3. **A replay wins over a stale `expected_current`.** If the target is already current, the
   answer is the current designation. Qualification is checked before staleness.
4. **`build_state` values.**
   - `incomplete`: a `characters-v2` chunk build or any embedding build exists, but not the
     qualifying one.
   - `absent`: neither exists.
   - The snapshot's `paragraph_count` is the sum of its documents' declared counts. It is not a
     row count.
5. **Designation types are a closed list.** A document whose type is not on it, such as
   «Приказ» or «Постановление», is found by its words, not by designation lookup. The
   displayed designation is the slug's head with spaces. The slug lost the source's dots, so it
   reads `СП 54 13330 2022`.
6. **The cursor binding is a hash, not a MAC.** A forged position inside the same query can
   only skip rows. It can never resume another query or another snapshot.

## 4. Risks and known limitations

- **No SQL has been executed.** Statements are syntax-checked only. Two kinds of behaviour rest
  on PostgreSQL semantics this lane could not observe:
  - psycopg 3's typing of untyped parameters (`CAST(:x AS real)`, `char_length(:body)`);
  - the planner's use of `0020`'s partial indexes.

  Every search statement does carry the literal `text_reliability = 'reliable'` that those
  indexes need.
- **The timeout window case is real.** Another connection holds `LOCK TABLE norm_paragraph IN
  ACCESS EXCLUSIVE MODE`, and the search with a 300 ms timeout must be cancelled.
- **The 3000 ms default is provisional.** `W55A-D124-MEASURE` re-fixes it.
- **`SEALED_STUB_QUERY_OPERATIONS` is not emptied.** It lives in
  `tests/integration/api/test_query_surface.py`, which is outside this grant.
  - It stays green: it pins the four operations' declared parameters and does not assert the
    stub.
  - Driving them there needs seeded norms rows and query-string targets in that suite.
  - `q`, `norms_snapshot_id`, `cursor` and `limit` are each shown to change the answer in
    `test_search_window.py` and `test_current_snapshot_window.py`.
  - This is a follow-up for QA or the integrator.
- **`api/routers/ports.py` docstrings still describe sealed stubs.** That file is SEAL's (`api/**` except router bodies), so it was not edited.

## 5. Integrator instructions

1. Read the diff and this report, then merge `agent/w55a-search-01`. Stage B continues with
   `W55A-PIN-01`, which now owns `bootstrap/{adapters,composition}.py`.
2. **Window (D-157).** Use this lane's stack: PostgreSQL `57230`, S3 `60830/60831`, with a lane
   `.env`. Run from the worktree:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q tests/integration/norms/search
   .venv/bin/python -m pytest -q \
       tests/integration/composition/test_router_answers.py \
       tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py \
       tests/integration/composition/test_composition_root.py \
       tests/integration/composition/test_settings_defaults.py \
       tests/integration/api/test_role_register.py \
       tests/integration/api/test_query_surface.py \
       tests/integration/db/test_norms_search_migration.py
   ```

   Expected: everything green.
   - The first command covers the four window suites: search, current snapshot, PDF and roles.
     The search and current-snapshot suites each create and drop a throwaway database
     `w55a_search_<hex>`. The PDF suite creates and drops a throwaway bucket.
   - The roles suite writes three suite accounts, `norms-roles-{none,expert,admin}@suite.invalid`, into the lane database.
3. Stop the lane stack by its own compose project. Kill nothing by pattern.

**Notes for `W55A-PIN-01`:**

- Read `auditmanager.norms.public.current_snapshot(session)` inside the run-creating
  transaction. `None` means none is current, and the run pins NULL (CD-6).
- The reader takes no lock. Designations serialise among themselves on
  `pg_advisory_xact_lock(hashtextextended('auditmanager.norm_current_snapshot', 0))`.
- In `composition.py`, `NormsSearchAdapter` now takes `timeout_ms=resolved.norms_search_timeout_ms`.

## 6. Containment

`git diff --name-only 60c6e6e..HEAD` lists the 24 paths of §1 plus this report. Every path
except one is inside the §A4 item 2 grant:

- `norms/search/**`, `norms/current_snapshot.py`, `norms/public.py`;
- `routers/norms.py`, `bootstrap/{adapters,composition,settings}.py`;
- the three named composition tests and `tests/integration/norms/search/**`.

The current-snapshot tests sit in `norms/search/` so that they share its database fixture. The
grant also names `tests/integration/norms/test_current_snapshot*.py`, which was not needed.

**One path outside the grant, forced by the change:**
`tests/contract/api_v1/test_w55a_norms_seal.py`.

- It asserted that every norms adapter method refused as a sealed stub, and it would be red now.
- That one test function and its import were removed. Its docstring line and a comment point to
  the suites that now drive the bodies.
- CONTENT made the same kind of edit to the same file.
- Revert it only together with the adapters.

Not touched:

- `contracts/**`, migrations, `api/routers/{ports,wire,documents}.py`, `api/schemas/**`, `security.py`;
- `tests/integration/api/**`;
- `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`;
- root dependency and lock files, `.venv`, `web/**`;
- refs, tags, the stand, other worktrees.

No container, push, merge, tag or stash. No process was killed. `git status --porcelain -uall`
is empty after this commit.
