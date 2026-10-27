# Task FIX-P02-GUARDS-01 — the two P02 guards that wave B turned red, and the credential that expired in a long run

task_id: FIX-P02-GUARDS-01
status: delivered (branch `agent/fix-p02-guards-01`, not merged, not pushed); the report and the mutation table are in `docs/program/FIX-P02-GUARDS-01.md`.

## Outcome

`tests/integration/p02_journey` passes whole on the merged tree: `test_the_table_list_this_suite_counts_is_complete` (the two tables of migration `0035` are counted) and `test_no_module_consumes_the_manifest_page_hashes` (the three wave-B comparison modules that name their own page digests are allowed, each for a stated reason and for exactly the kinds of use they make, and the guard still fails for a read of the reference file, a new naming module and a stale entry). Besides, the other 57 reds of the 95-minute run of `tests/integration` — a credential minted at collection that outlived `TOKEN_LIFETIME_SECONDS` — are removed at their source (one shared driver file) and shown red/green under a simulated two-hour clock.

## Depends on

- `COMPARE-PERSISTED-SUMMARY-01` — completed and merged (migration `0035`, the modules under `src/auditmanager/comparison/`).
- `GATE-FIX-P02-01` — completed (the guards and the allowance idiom this task extends).

## Frozen inputs

- domain contract: not_applicable (no `contracts/**` file is touched)
- API contract: not_applicable
- analysis/comparison/event contract: not_applicable
- migration head: `0035_comparison_records` (read, not moved)
- base commit: `a660246f` (tip of `integration/ar-close-1026` at launch)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the two reds are exactly what the integrator reported and nothing else is red in `p02_journey`; the field name is used in `src` by the four comparison modules and by no other `*.py`; none of the four names the reference file or a manifest or opens a file; migration `0035` adds exactly two tables and nothing under `p02_journey` issues the operations that write them; the 57 other reds are the executors files and the credential is minted once at import with the production lifetime.

### P-01 — the two reds on the base tree
- captured_at: 2026-10-27
- command: `pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/p02_journey/test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete tests/integration/p02_journey/test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes`
- captured_output:
  ```text
  E       AssertionError: tables exist that this suite's idempotency claim does not count: ['comparison_sheet_link', 'comparison_summary']. Add them to P02_TABLES; an uncounted table is an uncovered claim.
  E       AssertionError: a module now reads the reference extractor's page hashes, which the pinned extractor does not reproduce: ['<base>/src/auditmanager/comparison/approved_evidence.py:74', '<base>/src/auditmanager/comparison/approved_evidence.py:81', '<base>/src/auditmanager/comparison/approved_evidence.py:95', '<base>/src/auditmanager/comparison/approved_evidence.py:96', '<base>/src/auditmanager/comparison/approved_evidence.py:256', '<base>/src/auditmanager/comparison/pairing.py:330', '<base>/src/auditmanager/comparison/pairing.py:331', '<base>/src/auditmanager/comparison/pairing.py:380', '<base>/src/auditmanager/comparison/pairing.py:381', '<base>/src/auditmanager/comparison/pairing.py:502', '<base>/src/auditmanager/comparison/pairing.py:503', '<base>/src/auditmanager/comparison/sheet_links.py:39', '<base>/src/auditmanager/comparison/sheet_links.py:62', '<base>/src/auditmanager/comparison/sheet_links.py:66', '<base>/src/auditmanager/comparison/sheet_links.py:86', '<base>/src/auditmanager/comparison/sheet_links.py:87', '<base>/src/auditmanager/comparison/sheet_links.py:141', '<base>/src/auditmanager/comparison/sheet_links.py:142']
  FAILED tests/integration/p02_journey/test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete
  FAILED tests/integration/p02_journey/test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes
  2 failed in 0.16s
  ```
- interpretation: Run on an export of `a660246f` (`git archive`, `<base>` is the export root) against a private database migrated to head. Both reds reproduce with the integrator's wording. The second lists eighteen lines in three modules; `sheet_match_suggestions.py` (already allowed) is not in the list.

### P-02 — every use of the field name in `src` at the base
- captured_at: 2026-10-27
- command: `git grep -n page_text_sha256 a660246f -- src`
- captured_output:
  ```text
  a660246f:src/auditmanager/analysis/README.md:211:  is **not** byte-identical to `baseline.page_text_sha256` in
  a660246f:src/auditmanager/analysis/README.md:215:  offsets. Do not assert `page_text_sha256` against this text layer.
  a660246f:src/auditmanager/comparison/approved_evidence.py:74:def page_text_sha256(text: str) -> str:
  a660246f:src/auditmanager/comparison/approved_evidence.py:81:        return page_text_sha256(text)
  a660246f:src/auditmanager/comparison/approved_evidence.py:95:        and _digest_or_none(source) == link.source_page_text_sha256
  a660246f:src/auditmanager/comparison/approved_evidence.py:96:        and _digest_or_none(target) == link.target_page_text_sha256
  a660246f:src/auditmanager/comparison/approved_evidence.py:256:    "hunk_id", "link_is_verified", "page_text_sha256", "project_approved_pairs", "raw_artifact",
  a660246f:src/auditmanager/comparison/pairing.py:330:                and link.source_page_text_sha256 == proposed.source_page_text_sha256
  a660246f:src/auditmanager/comparison/pairing.py:331:                and link.target_page_text_sha256 == proposed.target_page_text_sha256
  a660246f:src/auditmanager/comparison/pairing.py:380:            source_page_text_sha256=proposed.source_page_text_sha256,
  a660246f:src/auditmanager/comparison/pairing.py:381:            target_page_text_sha256=proposed.target_page_text_sha256,
  a660246f:src/auditmanager/comparison/pairing.py:502:            source_page_text_sha256=approval.source_page_text_sha256,
  a660246f:src/auditmanager/comparison/pairing.py:503:            target_page_text_sha256=approval.target_page_text_sha256,
  a660246f:src/auditmanager/comparison/sheet_links.py:39:    "source_page_text_sha256, target_page_text_sha256, suggestion_sha256, "
  a660246f:src/auditmanager/comparison/sheet_links.py:62:    "target_page_number, source_page_text_sha256, target_page_text_sha256, suggestion_sha256, "
  a660246f:src/auditmanager/comparison/sheet_links.py:66:    ":source_page_text_sha256, :target_page_text_sha256, :suggestion_sha256, "
  a660246f:src/auditmanager/comparison/sheet_links.py:86:    source_page_text_sha256: str
  a660246f:src/auditmanager/comparison/sheet_links.py:87:    target_page_text_sha256: str
  a660246f:src/auditmanager/comparison/sheet_links.py:141:    source_page_text_sha256: str
  a660246f:src/auditmanager/comparison/sheet_links.py:142:    target_page_text_sha256: str
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:71:    page_text_sha256: str
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:89:    source_page_text_sha256: str
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:90:    target_page_text_sha256: str
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:152:    """Unique identical nonblank pages: ``(page_text_sha256, source, target)``."""
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:199:            "page_text_sha256": digest,
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:320:            "page_text_sha256": digest,
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:342:            "source_page_text_sha256": source_text_sha256,
  a660246f:src/auditmanager/comparison/sheet_match_suggestions.py:343:            "target_page_text_sha256": target_text_sha256,
  ```
- interpretation: Four `.py` modules, all under `comparison/`. In `sheet_links.py` the name is two dataclass fields (`LinkEvent`, `NewLinkEvent`) and two SQL texts (the column list, the INSERT); in `approved_evidence.py` it is the module's own function, one call of it, two attribute reads of a stored link and one `__all__` entry; in `pairing.py` it is eight attribute reads and four keyword arguments. The two `README.md` lines are prose that says not to assert the reference hashes against the text layer; the guard scans `*.py` only.

### P-03 — none of the four modules can reach the reference file or a manifest
- captured_at: 2026-10-27
- command: `git grep -n -i "expected_issues\|manifest\|open(\|read_text\|read_bytes\|json.load" a660246f -- src/auditmanager/comparison/approved_evidence.py src/auditmanager/comparison/pairing.py src/auditmanager/comparison/sheet_links.py src/auditmanager/comparison/sheet_match_suggestions.py; echo "git grep exit=$?"`
- captured_output:
  ```text
  git grep exit=1
  ```
- interpretation: No line of the four modules mentions the reference file or a manifest or opens a file (exit 1 is "no match"). `git grep -n -i "expected_issues\|manifest" a660246f -- src/auditmanager/comparison` over the whole package also prints nothing. This is the property the new isolation rule of the guard asserts by syntax tree, so the allowance for attribute and keyword uses does not rest on trust.

### P-04 — migration 0035 adds two tables; the journey issues none of the operations that write them
- captured_at: 2026-10-27
- command: `git grep -n "CREATE TABLE" a660246f -- db/migrations/versions/20261027_0035_comparison_records.py; git grep -n -i "approveSheetPairing\|withdrawSheetPairing\|generateComparisonSummary\|compareDocumentVersions\|approve_sheet_pairing\|generate_comparison_summary\|comparison_summary\|comparison_sheet_link" a660246f -- tests/integration/p02_journey; echo "git grep exit=$?"`
- captured_output:
  ```text
  a660246f:db/migrations/versions/20261027_0035_comparison_records.py:272:        CREATE TABLE comparison_sheet_link (
  a660246f:db/migrations/versions/20261027_0035_comparison_records.py:394:        CREATE TABLE comparison_summary (
  git grep exit=1
  ```
- interpretation: Exactly two base tables, the two the guard names. Nothing under `p02_journey` names the operations (`approveSheetPairing`, `withdrawSheetPairing`, `generateComparisonSummary`, `compareDocumentVersions`) or the two tables, so both counts are expected unchanged across a replay; the report records the rows after a whole-directory run (0 and 0).

### P-05 — the 57 other reds are one cause: a credential minted at import with the production lifetime
- captured_at: 2026-10-27
- command: `git grep -n "TOKEN_LIFETIME_SECONDS: Final\|^TEST_TOKEN = \|credential: str | None = TEST_TOKEN" a660246f -- src/auditmanager/api/security.py tests/integration/api/driver.py; grep -E "^FAILED" .local/handoff/logs/int-all.log | sed -E 's/::.*//' | sort | uniq -c | sort -rn; grep -E "^[0-9]+ failed" .local/handoff/logs/int-all.log`
- captured_output:
  ```text
  a660246f:src/auditmanager/api/security.py:527:TOKEN_LIFETIME_SECONDS: Final[int] = 3600
  a660246f:tests/integration/api/driver.py:120:TEST_TOKEN = _SIGNER.issue(TEST_SUBJECT, is_default_credential=False).token
  a660246f:tests/integration/api/driver.py:432:        credential: str | None = TEST_TOKEN,
  a660246f:tests/integration/api/driver.py:487:    credential: str | None = TEST_TOKEN,
       26 FAILED tests/integration/executors/test_runner_channel.py
       10 FAILED tests/integration/executors/test_plain_http_destination.py
       10 FAILED tests/integration/executors/test_executor_surface.py
        5 FAILED tests/integration/executors/test_pull_run_path.py
        3 FAILED tests/integration/executors/test_agent_e2e.py
        2 FAILED tests/integration/executors/test_runner_bridge_e2e.py
        1 FAILED tests/integration/p02_journey/test_whole_journey_idempotency.py
        1 FAILED tests/integration/p02_journey/test_extractor_divergence.py
        1 FAILED tests/integration/executors/test_secret_never_leaves.py
  59 failed, 9883 passed, 27 skipped, 6 warnings, 248 subtests passed in 5740.86s (1:35:40)
  ```
- interpretation: 57 of the 59 reds are in seven files of `tests/integration/executors`; the other two are the guards above. The driver mints `TEST_TOKEN` once at module level (line 120) and binds it as the default of `Surface.send` (432) and `dispatch` (487); the executors `conftest.py` loads that driver. A run of 5740 s outlives the 3600 s lifetime. The log shows `assert 401 == 201` in the failing tests.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/integration/p02_journey/**`
- `tests/integration/api/driver.py`
- `tests/integration/api/test_suite_credential_outlives_a_run.py`
- `docs/program/FIX-P02-GUARDS-01.md`
- `docs/program/tasks/FIX-P02-GUARDS-01.md`

## Lane resources

Private database `auditmanager_fixp02` and bucket `auditmanager-fixp02`, created in the integrator's lane stack through a copy of its `.env` (untracked) and dropped at the end; the stack's main database and bucket were not used.

## Forbidden hotspots

- `src/**`, `contracts/**`, migrations, `web/**`, `infra/**`
- `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`
- root dependency/lock files, composition root, global styles

## Non-goals

- Renaming the `page_text_sha256` columns or fields of migration `0035` (they cannot be renamed).
- Changing any module under `src/auditmanager/comparison/`.
- Re-minting credentials in the other suites that mint per call or per module (they cannot outlive a run, see the report).
- A complete run of `tests/integration`.

## Deliverables

- `P02_TABLES` counts `comparison_sheet_link` and `comparison_summary`, each with the reason the journey leaves it unchanged.
- Three allowances in `OWN_PAGE_HASH_ALLOWANCES`, the table `OWN_PAGE_HASH_USES`, the isolation rule, the guard as a function proved on synthetic packages, and a behavioural test for `approved_evidence`.
- `TEST_TOKEN` of the shared API driver outlives a run, with a test that pins it.
- The report with the mutation table, the before/after of each modified test and the measured runs.

## Required tests

- command: `tests/integration/p02_journey` whole, on a private database; `tests/integration/api/test_suite_credential_outlives_a_run.py`; `tests/integration/executors` and `tests/integration/api` whole; `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py`, `tests/contract/api_v1/test_surface_counts_in_prose.py`; `git diff --check`
- expected: all green; the mutation table of the report shows each guard red under its mutation

## Integration contract

Tests only. A module under `src/auditmanager/comparison/` that names `page_text_sha256` for anything but a digest it computes or stores itself, a new module that names it, a kind of use not listed in `OWN_PAGE_HASH_USES`, or an allowed module that can open a file or names a manifest turns `p02_journey` red. A new migration that adds a table turns the table-list guard red until `P02_TABLES` names it.

## Failure/idempotency/security cases

- Reading `fixtures/synthetic/ar/expected_issues.json` page hashes from an allowed module, by key, by attribute fed from a file, or through an imported manifest reader: red.
- A stale allowance (file gone, name gone) and a stale kind (declared, no longer used): red.
- The suite credential equal to the production lifetime again, or widened to forever: red.

## Rollback / feature flag

Not applicable: test files only; `git revert` of the three commits restores the previous guards and the previous driver.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report
- integration notes: see the report
