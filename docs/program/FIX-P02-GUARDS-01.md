# FIX-P02-GUARDS-01 — the two P02 guards that wave B turned red, and the credential that expired in a long run

Task: `docs/program/tasks/FIX-P02-GUARDS-01.md`. Branch `agent/fix-p02-guards-01`, base `a660246f` (tip of
`integration/ar-close-1026`). Code commits: `67edfd0a` (part A), `20b1e719` (part B), `85c7f6d3` (part C);
the task file and this report follow. Evidence of the reds: `.local/handoff/logs/int-all.log` (59 failures
in 5740.86 s: 57 executors, 2 here).

## Result

| Part | What was red | Cause | Decision |
| --- | --- | --- | --- |
| A | `p02_journey/test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete` | migration `0035` added `comparison_sheet_link` and `comparison_summary`; `P02_TABLES` did not count them | stale list, not a defect: both added, each with the reason the journey leaves it unchanged |
| B | `p02_journey/test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes` | the guard scans `src` for `page_text_sha256`; wave B's `comparison/{sheet_links,approved_evidence,pairing}.py` use it as the name of digests they compute or store (the `0035` column names) | not consumers: three allowances, each for exactly the kinds of use the module makes, plus an AST proof that the module cannot reach the reference file; the guard is shown failing under 16 mutations of the real package and 18 synthetic cases |
| C | 57 reds in `tests/integration/executors` of the same run | `driver.TEST_TOKEN` is minted once at import (collection) with the 3600 s production lifetime; the run lasted 5740 s; every default-credential request after the first hour was a `401` | one shared file changed (the driver), one test added; red/green shown under a simulated two-hour signer clock |

`tests/integration/p02_journey` whole: 80 passed (60 before this task + 20 new). No `src/**`, `contracts/**`,
migration, `web/**`, `infra/**`, `DEBT_REGISTER.md` or `CURRENT_STATE.md` path changed (proof at the end). None of
the three was a product defect.

## Files

| File | Change |
| --- | --- |
| `tests/integration/p02_journey/journey.py` | `P02_TABLES` + two entries and a comment |
| `tests/integration/p02_journey/test_extractor_divergence.py` | guard rewritten as a function of `(root, allowances, uses)`; three allowances; `OWN_PAGE_HASH_USES`; isolation rule; 18 synthetic-package cases; one behavioural test |
| `tests/integration/api/driver.py` | `TEST_TOKEN` minted by a signer with a 24 h lifetime (6 lines + comment); `_SIGNER` unchanged |
| `tests/integration/api/test_suite_credential_outlives_a_run.py` | new, 2 tests |
| `docs/program/tasks/FIX-P02-GUARDS-01.md`, `docs/program/FIX-P02-GUARDS-01.md` | task file and this report |

Part C touched two shared-integration files (one edit, one new test), inside the "at most three" the task allowed.

## Part A — the table list

`comparison_sheet_link` is written only by the commands `approve_sheet_pairing` and `withdraw_sheet_pairing`
(`approveSheetPairing`, `withdrawSheetPairing`); `comparison_summary` only by `generate_comparison_summary`
(`generateComparisonSummary`). Nothing under `p02_journey` names those operations (P-04), so both counts are
expected unchanged across a replay, which is the claim the other never-written tables (`ar_v3_run_group`, the executor
tables) already carry; they are counted, not skipped. Measured on the private database after the whole
`p02_journey` directory had run: `comparison_sheet_link` 0 rows, `comparison_summary` 0 rows (while `audit_run`
held 27, `document_version` 13, `blob` 76), so the "unchanged" is "stays at 0". The completeness guard itself
(`journey.assert_table_list_is_complete`: live base tables minus `P02_TABLES` must be empty) is unchanged.

## Part B — the page-hash guard

### What changed and why it is still meaningful

The old guard rejected every module outside `OWN_PAGE_HASH_ALLOWANCES` that names the field, and held an allowed
module to "declare a field, key a dict it builds, prose in a docstring". The three wave-B modules need two more
things: the field's *longer* names as attributes and keyword arguments of their own records (`link.source_page_text_sha256`,
`NewLinkEvent(source_page_text_sha256=...)`), and in `sheet_links.py` the column names in SQL text, in
`approved_evidence.py` its own function `page_text_sha256(text)`. The change is the smallest that admits those and
no more:

1. **Three allowances**, each with its precise reason (what the name is in that module, where the value comes from,
   that the module opens no file and names neither the portal manifest nor `expected_issues.json`).
2. **`OWN_PAGE_HASH_USES`**: per allowed module, exactly the kinds of use beyond declaring and building.
   Five kinds: `attribute` (an attribute whose name *ends with* the field), `keyword` (a keyword argument ending with
   it), `own function` (a `def` ending with it and mentions of it in the module that defines it), `export` (an
   entry of `__all__`), `sql text` (a string containing the name **and white space**). Everything else is
   still a `read`: a subscript, `.get("page_text_sha256")`, a comparison with the bare name, a parameter, a variable.
   The guard demands **equality** between the kinds a module makes and the kinds listed: an unlisted kind is a finding,
   and so is a listed kind the module no longer makes (an allowance cannot stay wider than the code).
   `sheet_match_suggestions.py` has no entry: it stays held to declaring and building, exactly as before.
3. **The isolation rule.** A JSON file has keys, not attributes, so the relaxed kinds are sound only if the module
   cannot be handed the reference hashes by its own hand. For every allowed module the guard parses the file and
   fails if any identifier, string (docstrings excepted), import or alias contains `expected_issues` or `manifest`,
   if it imports `os`, `pathlib`, `io`, `zipfile`, `shutil`, `glob`, `tempfile` or `fileinput`, or if it uses `open`,
   `.open`, `.read_text`, `.read_bytes`, `.load` or `.loads`. This is asserted by syntax tree, not by trust; P-03 shows
   the four modules satisfy it today (and the whole `comparison/` package never mentions either word).
4. **The guard is a function** `page_hash_guard_findings(root, allowances, uses)` returning seven classes of finding
   (`stale`, `orphan_uses`, `consumers`, `reads`, `undeclared_uses`, `stale_uses`, `reference_access`). The real test
   asserts every class empty on the real package; `test_the_page_hash_guard_fails_where_it_must_and_only_there`
   runs the *same function* on 18 synthetic packages and asserts the exact set of classes that fire.
5. **Behavioural half for `approved_evidence`** (the one new module that digests page text): its
   `page_text_sha256` equals the SHA-256 of the pinned extractor's own page text and never the manifest's declared hash
   on any of the eight pages; `link_is_verified` is true for a link storing the own digests and false for a link
   storing the manifest's on either side. The divergence test above pins that the two never agree, so a module that took
   the manifest's value could not pass it. For `pairing` and `sheet_links` (which only carry digests) the existing
   `tests/integration/comparison/test_sheet_pairing_db.py` asserts the stored digests equal the SHA-256 of the page text
   (28 passed together with `tests/unit/comparison/test_approved_evidence.py`).

The global rule is untouched: any module outside the allowances that names the field, in code or in a comment, is a
consumer. A reader of the reference hashes has to name the field to look it up, so it either is a new module (red),
is an allowed module (red by the `read` kind or the isolation rule), or does not name the field (outside what this guard
ever claimed, see Limits).

### Mutations (each guard shown failing, then green)

Method for the real package: a scratch copy of `src/auditmanager` with symlinks to `contracts`, `db`, `docs`, `fixtures`
(the code reads them relative to the repository root), mutated in the copy only and selected by `-o pythonpath=<copy>/src`;
the guard resolves the package from `auditmanager.__file__`, so it scans the mutated tree. Tracked files were never
mutated for part B. The unmutated copy passes (`1 passed`).

| # | Mutation (in the copy) | Failure of `test_no_module_consumes_the_manifest_page_hashes` |
| --- | --- | --- |
| a1 | `pairing.py` appended: `json.loads(Path("fixtures/synthetic/ar/expected_issues.json").read_text())["baseline"]["page_text_sha256"]` | `reads`: `...pairing.py:557` (`reference_access` also fires; the assertion stops at the first class) |
| a2 | `approved_evidence.py` appended: `manifest["baseline"]["page_text_sha256"]` (dict handed in, no file named) | `reads`: `...approved_evidence.py:261` |
| a3 | `pairing.py` appended: opens `expected_issues.json` with `Path(...).read_text()` and only *attribute-reads* `record.source_page_text_sha256` | `reference_access`: `imports pathlib`, names `expected_issues`, uses `.read_text` (the relaxed rule is no loophole) |
| a4 | `sheet_links.py`: `from auditmanager.ingest.public import read_portal_manifest` | `reference_access`: `sheet_links.py:27: names 'read_portal_manifest'` |
| b1 | new `comparison/zz_consumer.py`: `CONSUMER = {}.get("page_text_sha256")` | `consumers`: `comparison/zz_consumer.py:1` |
| b2 | new `comparison/zz_consumer.py` naming only `link.source_page_text_sha256` | `consumers`: `comparison/zz_consumer.py:2` |
| b3 | new `runs/zz_consumer.py` (another context): `KEY = "page_text_sha256"` | `consumers`: `runs/zz_consumer.py:1` |
| c1 | `sheet_match_suggestions.py`: every `page_text_sha256` renamed `page_digest` | `stale`: `comparison/sheet_match_suggestions.py` |
| c2 | `sheet_links.py`: every `page_text_sha256` renamed `page_digest` | `stale`: `comparison/sheet_links.py` |
| c3 | `approved_evidence.py`: the `__all__` entry removed | `stale_uses`: `comparison/approved_evidence.py (export)` |
| c4 | `pairing.py`: both keyword arguments renamed | `stale_uses`: `comparison/pairing.py (keyword)` |
| d1 | `sheet_match_suggestions.py` appended: `x.source_page_text_sha256` (the strict module gains an attribute use) | `undeclared_uses`: `sheet_match_suggestions.py:364 (attribute)` |
| d2 | `sheet_links.py` appended: `row["source_page_text_sha256"]` (bare key where only SQL text is allowed) | `reads`: `sheet_links.py:240` |
| d3 | `approved_evidence.py` appended: `open(path).read()` | `reference_access`: `approved_evidence.py:261: calls open` |
| e1 | `approved_evidence.page_text_sha256` hashes `text + " "` (behavioural test) | `page 1 is not the text's own digest` |
| e2 | `link_is_verified` drops its two digest comparisons (behavioural test) | `assert True is False` |

The mutations a1 to d3 map to the three the task required: (a) a comparison module reading the reference file's page
hashes is red (a1 to a4); (b) a new module outside the allowances naming the field is red (b1 to b3); (c) an allowance
for a module that no longer names the field is red (c1, c2), and so is a kind no longer made (c3, c4). The 18
synthetic cases (permanent, in the test file) repeat all of these on temporary packages and add: the clean case, a
docstring that talks about the manifest, SQL text, own function with its export, a manifest reader imported, a file
opened under another name, a bare key where only SQL text is allowed, `.get` by key from a dict handed in, a comment that
names the field in a new module, an allowance for a missing file, a kinds entry for a module that is not allowed and a
module absent from the kinds table.

Part A mutations (on `journey.py`, restored after each): removing `comparison_summary` from `P02_TABLES` fails with
`tables exist that this suite's idempotency claim does not count: ['comparison_summary']`; removing
`comparison_sheet_link` fails with `['comparison_sheet_link']`; both passed again once restored.

### Before and after, per modified test

| Test | Asserted before | Asserted after | Weakened? |
| --- | --- | --- | --- |
| `test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete` | live base tables minus `P02_TABLES` is empty | same (file unchanged; `P02_TABLES` gained two names) | no |
| `test_whole_journey_idempotency.py::test_repeating_the_sequence_under_one_key_adds_no_row_anywhere` | count of every table in `P02_TABLES` unchanged by a replay | same, now over two more tables (both 0) | no, wider |
| `test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes` | (1) no allowance is stale; (2) no module outside the allowance names the field; (3) an allowed module only declares a field, keys a dict, writes prose | same three, over three more allowed modules, plus: kinds table consistent and equal to the kinds used (undeclared and stale kinds), every allowed module passes the isolation rule | no. What an allowed module may do widened only for the three new modules and only for the five kinds above; for `sheet_match_suggestions.py` it is unchanged and now additionally isolation-checked |
| `test_extractor_divergence.py::test_the_allowed_module_digests_the_text_it_is_given_and_not_the_manifest` | `sheet_match_suggestions` reports the text's own digest, never the manifest's | unchanged | no |
| `test_extractor_divergence.py::test_the_divergence_is_real_and_is_confined_to_the_page_hashes`, `test_every_declared_quotation_resolves_at_its_declared_offset`, `test_the_corpus_declares_the_anchors_this_suite_checks` | unchanged | unchanged | no |

New tests: `test_the_page_hash_guard_fails_where_it_must_and_only_there` (18 cases),
`test_every_allowance_of_the_real_package_has_a_reason_and_the_kinds_are_known`,
`test_the_approved_evidence_digests_the_text_it_is_given_and_not_the_manifest` (all in `test_extractor_divergence.py`),
`test_the_suite_credential_is_valid_after_a_run_longer_than_the_production_lifetime` and
`test_the_suite_credential_is_still_bounded` (in `tests/integration/api/test_suite_credential_outlives_a_run.py`).

## Part C — the credential that expired in a long run

### Finding

The failing files are seven in `tests/integration/executors` (26 + 10 + 10 + 5 + 3 + 2 + 1 = 57), all with
`assert 401 == 201` (P-05). The executors `conftest.py` loads `tests/integration/api/driver.py` by path; the driver
mints `TEST_TOKEN` at module level with `_SIGNER` (lifetime `TOKEN_LIFETIME_SECONDS` = 3600 s) and binds it as the
default `credential=` of `Surface.send` and `dispatch` at definition time. The driver is imported at **collection**, so
in a run longer than an hour every directory after the first hour that sends a default-credential request meets an
expired credential. `grep` over `tests/integration` for `TOKEN_LIFETIME_SECONDS`, `.issue(`, `credential(` and
`provisioned_credential(`, with the scope of each caller read, finds exactly one mint at import/collection time: this one.

### Fix and proof

`TEST_TOKEN` is now minted by `TokenSigner(derive_signing_key(DEPLOYMENT_SECRET), lifetime_seconds=24 * 3600)`: the same
key (the application under test verifies by HMAC and by the payload's `exp`, never by the signer's lifetime), a 24 h
lifetime. `_SIGNER` keeps the production lifetime because `SuiteCredentialAdapter` mints through it and
`test_authorization.py` asserts `expires_in == 3600` for the exchange (700). A re-minting accessor was considered and
rejected: seven test files and the `api` conftest import `TEST_TOKEN` *by value*, and the defaults are bound at
definition, so only a credential that outlives the run helps all of them without editing a call site.

Measured with a scratch plugin outside the repository that moves the *signer's* clock (`auditmanager.api.security.time`) two
hours ahead after collection, so that issue and verify move together and the database, the other modules and the
subprocesses keep the real clock. Whole directory `tests/integration/executors` on the private database:

| Tree | Result |
| --- | --- |
| driver of `a660246f`, signer clock +2 h | 57 failed, 113 passed, 16 skipped in 107.68 s; the failures by file are 26 / 10 / 10 / 5 / 3 / 2 / 1 over the same seven files as the real run |
| driver as committed, signer clock +2 h | 170 passed, 16 skipped in 122.13 s; no `401` anywhere in the log |
| driver as committed, real clock (control, one file) | `test_executor_surface.py`: 10 passed; `test_agent_e2e.py`: 3 passed |

(A first, cruder warp that moved `time.time` for the whole process also reproduced the 401s — 10 of 10 in
`test_executor_surface.py` — but made the three `test_agent_e2e.py` tests fail with `protocol_error` after the fix, because
they run a real agent subprocess and a database whose clock the warp cannot move; they pass on the real clock. The signer-only
warp above is the reported measurement.)

Mutations of the fix (on `driver.py`, restored after each; the new test `test_suite_credential_outlives_a_run.py`):

| Mutation | Failure |
| --- | --- |
| `TEST_TOKEN` minted by `_SIGNER` again | `the suite credential has expired after 3601 s` |
| lifetime `100 * 365 * 24 * 3600` | `assert 3153600000 <= 604800` (the bound is written in the test, not read from the driver) |
| lifetime `3 * 3600` | `assert 21600 < 10800` (shorter than a six-hour run) |

Regression: `tests/integration/api` whole, 668 passed in 457.12 s (it includes the two new tests).

### Residual exposure (not changed) and sized proposal

Every other mint in `tests/integration` happens inside a function, a function-scoped or module-scoped fixture, or a
module-level cache filled at first use, so its exposure is the runtime of one file or one directory above 3600 s, not the
runtime of the run:

| Where | Scope | Exposure | Proposal and size |
| --- | --- | --- | --- |
| `tests/integration/qa_w55b/conftest.py:93-101` (`accounts`, `expert`) | session, minted at first use | qa_w55b after its first use of `expert` longer than 3600 s (not measured; the log has only the total) | `expert` to function scope or return a callable that mints per use: 1 file, about 3 lines |
| `_STATIC_TOKEN_CACHE` in `composition/test_a_published_run_reports_itself.py`, `composition/test_router_answers.py`, `composition/test_the_run_leaves_the_request_thread.py`, `composition/test_version_blocks_wire_shape.py`, `ingest/test_size_guard_boundary.py`, `p02_journey/test_query_surface_over_the_corpus.py`, `p02_journey/test_truncated_end_to_end.py` | module, minted at first use | one file longer than an hour (the whole `p02_journey` directory takes 27 s) | none now |
| `scope="module"` fixtures minting `provisioned_credential(...)` in `composition/test_analysis_profiles_over_http.py`, `composition/test_optimisation_over_http.py`, `composition/test_optimisation_proposals_over_http.py`, `optimisation/test_ar_specification_journey.py` | module | same | none now |

A standing guard would keep this from returning: one contract test (about 40 lines, one new file under `tests/contract/`)
that parses `tests/integration/**` and fails on a credential mint (`.issue(`, `provisioned_credential(`,
`credential(`) at module level or in a session-scoped fixture, with an allowlist for the two known cases above and a
mutation. Size: small (under an hour), not done here because it is a new rule over files outside this lane.

## Commands and counts

Private database `auditmanager_fixp02` and bucket `auditmanager-fixp02` created in the integrator's lane stack through
a copy of its `.env` (untracked), migrated to `0035_comparison_records`; the stack's main database was not touched. One
pytest at a time; pytest temp dirs removed after each run. Command (prefix `env $(grep -v '^#' .env | grep -v '^$' | xargs)`):
`PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`.

| Run | Result |
| --- | --- |
| the two reds on an export of `a660246f` | 2 failed in 0.16 s |
| `tests/integration/p02_journey/test_extractor_divergence.py` | 25 passed in 0.29 s |
| `tests/integration/p02_journey` whole | 80 passed in 26.54 s |
| `tests/integration/api/test_suite_credential_outlives_a_run.py` | 2 passed |
| `tests/integration/executors` whole, signer clock +2 h, before / after | 57 failed, 113 passed, 16 skipped / 170 passed, 16 skipped |
| `tests/integration/api` whole | 668 passed in 457.12 s |
| `tests/integration/comparison/test_sheet_pairing_db.py` + `tests/unit/comparison/test_approved_evidence.py` | 28 passed |
| `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py`, `tests/contract/api_v1/test_surface_counts_in_prose.py` | 105 passed in 24.06 s (run on the committed tree with this report in it) |
| `git diff --check` | clean |

## Contracts

None new or changed.

## Risks and known limitations

- The page-hash scan is name-based, as before: a module that built the name at runtime, or obtained the reference hashes
  without writing `page_text_sha256` anywhere (for example by iterating the keys of `manifest["baseline"]`), is outside what
  this guard ever claimed. It is a tripwire, backed by the behavioural tests for the modules that digest text.
- The isolation rule looks at the allowed module's own code. It does not follow imports; the argument that it need not
  is the global rule (the only way to be handed the field's values from the reference file is a module that names the
  field, and every such module is either allowlisted and isolated or red).
- `sql text` is classified by white space in the string. A string with white space that names the field is accepted in
  a module that lists that kind (today only `sheet_links.py`); a bare key is not.
- The clock-warp measurement is a simulation of a long run, not a long run. The real proof is the next complete run of
  `tests/integration`; the expected result is that the executors files pass.
- The three never-written-by-the-journey claims for the new tables rest on the journey not issuing the operations and
  on the measured 0 rows, not on a per-table failing test; the completeness guard is the one shown failing.

## Integrator instruction

Merge `agent/fix-p02-guards-01` (a real merge) into `integration/ar-close-1026`. No migration, contract or `src` file
moves, so no pin follows. Re-run `tests/integration/p02_journey` and `tests/integration/executors` after the merge; a
future module that has to name `page_text_sha256` adds an allowance with a reason and its row in `OWN_PAGE_HASH_USES`
(the failing message names the missing piece), and a future migration that adds a table adds a name to `P02_TABLES`.

## Forbidden hotspots

`git diff --name-only a660246f..HEAD` lists exactly the four test files of the table above and the two docs; nothing under
`src/`, `contracts/`, `db/`, `web/`, `infra/`, no `DEBT_REGISTER.md`, no `CURRENT_STATE.md`.
