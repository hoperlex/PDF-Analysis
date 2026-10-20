# GATE-FIX-P02-01 — the P02 journey guards and the executor bridge head pin

Task: `docs/program/tasks/GATE-FIX-P02-01.md`. Branch `agent/gate-fix-p02-01`, based on `c90d52f3`
(`origin/dev` `a41cb90e` plus the two frozen task files); test commit `d457aee8`. Evidence of the
reds: `.local/gates/night-43670efc/rerun.log` (4 of the 15 real reds of the first complete gate on
`43670efc`). Debt `D-187`.

## Result

The four named tests pass, and so do `tests/integration/p02_journey` whole and the bridge DB
acceptance file whole (62 passed). Three reds were stale pins or stale claims and one was a guard
that measured the wrong set; **none was a product defect**. No `src/**` file changed, so the
`comparison/sheet_match_suggestions.py` question was settled by reading it and by a test, not by a
fix. No `contracts/**`, no migration, no `tests/support/**`, no `conftest.py`, no `fixtures/**`, no
`web/**`, no dependency file changed.

| Red | Cause | Decision |
| --- | --- | --- |
| `jobs/test_recorded_v2_executor_bridge_db_accept.py::test_persisted_recorded_executor_saves_five_stages_one_call_and_one_terminal` | the first statement asserted `alembic_version == "0022_findings_v2"`; the sealed head is `0027_optimisation_proposals` | stale pin, and only the pin. The test reads `FACTS.migration_head` from `tests/support/expected_facts.json` as `test_recorded_v2_publication_gate.py` does. Whether anything else in the test depends on the shape of `0022` was settled by running it: with the pin fixed it passes on the `0027` schema, and everything it reads (`stage_result`, `model_call`, `job`, `attempt`, `lease`, `audit_run`, `finding`, `finding_observation`) is untouched by `0023`..`0027` |
| `p02_journey/test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete` | `P02_TABLES` stopped at `0022`; the live schema also has `document_version_classification`, `finding_observation_norm_citation`, `norm_retrieval_set`, `optimisation_pass`, `optimisation_proposal`, `optimisation_proposal_decision`, `price_list_position`, `price_list_revision`, `vendor_list_entry`, `vendor_list_revision`, `work_assignment`, `work_assignment_event` (the list the failure message names; exactly the base tables of `0023`..`0027`, the `work_assignment_current` view is not a base table) | stale list. The twelve are added to `journey.py::P02_TABLES`, each group with a note on why a P02 replay leaves it unchanged (the journey runs the AR text profile: no norm retrieval or citation, no expert classification, no assignment, no price or vendor list, no optimisation pass). After the whole suite each of the twelve counts 0, so the replay claim for them is "stays at 0", and any replay that wrote to one of them would be seen by `table_counts`. The stale "sixteen P02 tables" in the module docstring is replaced by the statement the completeness guard actually enforces |
| `p02_journey/test_ungrounded_diagnostic_path.py::test_no_grounded_false_row_exists_anywhere` | the guard read **the whole `finding_observation` table**. In a complete run that table is shared with other suites, and one of them commits a hand-seeded `grounded=false` row: `jobs/test_recorded_v2_publication_gate.py::test_preexisting_observation_without_finding_refuses_publication` inserts `(grounded=false, ungrounded_reason='quotation_absent')` for the AR v2 recorded profile on a run that stays `running`, to prove the v2 publication refuses it, and `commit()`s it (`finding_observation` refuses `DELETE`, so it can never be cleaned up). This is the gate's `{(False, 'quotation_absent'), (True, None)}` | not a producer in the chain and **not** the W57a citation partition: `findings/citation_publication.py` and `v2_publication.py` write `grounded=true, NULL` only; the only code that writes `grounded=false` is the legacy `findings/publication.py`, which the AR text chain never reaches because the stage drops unresolvable anchors first. The claim is restated for the chain it is about: every run of the AR text profile and bundle (`AR_TEXT_PROFILE`, `AR_TEXT_PROMPT_BUNDLE`) in the database, any project, any variant. It also fixes a second defect: the test did not request `ungrounded_run`, so on its own it saw an empty table ("no observations at all") and was green only by the luck of running after a test that wrote rows. It now requests the fixture and carries a scope assertion (the profile filter selects the module's own run's rows) beside the existing non-empty assertion, so the narrowing cannot empty the claim |
| `p02_journey/test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes` | the guard scanned `src` for the literal `page_text_sha256`; `comparison/sheet_match_suggestions.py` names it on 8 lines | not a consumer. In that module `page_text_sha256` is the name of a dataclass field (`SheetMatchSuggestion`, and `source_`/`target_` in `SheetPairSuggestion`), a key of a dict that is hashed into `suggestion_sha256`, and a docstring. The value is `hashlib.sha256(<page text>.encode("utf-8")).hexdigest()` over the page snapshot the caller passes (`comparison/service.py` passes the verified `prepared.text_layer` pages). It reads neither the portal manifest nor `expected_issues.json`. The guard now holds a named allowance (below) |

### The page-hash allowance

`OWN_PAGE_HASH_ALLOWANCES = {"comparison/sheet_match_suggestions.py": <reason>}` in the test module.
It is not a blanket exclusion:

1. every other module naming `page_text_sha256` on any line (comment included) is still a consumer
   and fails the guard, exactly as before;
2. the allowed file is parsed (`ast`) and may use the name only to declare a class field, to key a
   dict display, or in a docstring; a subscript, `.get(...)`, an attribute access, a keyword
   argument or any other use is reported as a read;
3. an allowance whose file is gone, or no longer names the field, fails (so the list cannot outlive
   what it excuses);
4. `test_the_allowed_module_digests_the_text_it_is_given_and_not_the_manifest` (new) feeds the
   pinned extractor's page text of the baseline PDF to `suggest_exact_sheet_matches` and
   `suggest_sheet_pairs` and asserts that every reported digest equals the SHA-256 of that text and
   differs from the manifest's declared hash for the page. The divergence test above pins that the
   two never agree, so a module that took the manifest's value could not pass this.

## Quoted mutations (each repaired guard shown failing)

Method: a scratch copy of `src` (with symlinks to `contracts`, `db`, `docs`, `fixtures`, which the
code reads relative to the repository root) selected by `-o pythonpath=<copy>/src`; the guard resolves
the package from `auditmanager.__file__`, so it scans the mutated tree. Database mutations ran on a
throwaway database `auditmanager_gate_fix_p02_mut` created and migrated in the lane's own PostgreSQL,
so the lane database stayed clean. Tracked files were never mutated.

| Guard | Mutation | Failure |
| --- | --- | --- |
| head pin | throwaway database: `UPDATE alembic_version SET version_num='0026_price_lists'` | `AssertionError: assert '0026_price_lists' == '0027_optimisation_proposals'`; restored to `0027...`, the test passes |
| table list | throwaway database: `CREATE TABLE zz_uncounted_probe (id int)` | `tables exist that this suite's idempotency claim does not count: ['zz_uncounted_probe']. Add them to P02_TABLES`; table dropped, passes |
| grounded=false, chain scope | copy of `findings/grounding.py:195`: `if text_layer.slice(item.char_start, item.char_end) != quote:` -> `if True:` (the gate rejects every anchor, so the AR text chain writes `grounded=false` rows) | `assert {(False, 'quo... (True, None)} == {(True, None)}`, `Extra items in the left set: (False, 'quotation_absent')` (`test_nothing_ungrounded_is_published` and the vocabulary test fail with it); unmutated control on the same database: 5 passed |
| page hashes, allowed module reads the manifest | copy of `sheet_match_suggestions.py`, appended: `def _mutation(manifest): return manifest["baseline"]["page_text_sha256"]` | `a module allowed to name page_text_sha256 reads it instead of building it ... sheet_match_suggestions.py:364` |
| page hashes, any other module | new `comparison/zz_consumer.py`: `CONSUMER = {}.get("page_text_sha256")` | `a module now reads the reference extractor's page hashes ... zz_consumer.py:1` |
| page hashes, own digest | copy of `sheet_match_suggestions.py:145`: `hashlib.sha256(encoded).hexdigest()` -> `hashlib.sha256(encoded + b"x").hexdigest()` | `bound: page 1 is not the text's own digest` |
| page hashes, stale allowance | copy: every `page_text_sha256` renamed `page_digest` in the allowed file | `an allowance names a module that is gone or no longer names page_text_sha256 ...` |

The gate's own failure is also reproduced: on the lane database, after
`test_preexisting_observation_without_finding_refuses_publication` had committed its row,
`SELECT DISTINCT grounded, ungrounded_reason FROM finding_observation` returns
`{(t, NULL), (f, quotation_absent)}`; the rows by profile are `ap_01K7F4...QH` (the v2 recorded
profile) 2 grounded and 1 `quotation_absent`, and the AR text profile `ap_01M25P...` 124 grounded
and nothing else. The repaired guard passed on that database.

## Failing list before and after

Lane stack: `foundation_instance auditmanager-gate-fix-p02`, PostgreSQL 57630, MinIO 61230/61231,
database `auditmanager_gate_fix_p02`, bucket `auditmanager-gate-fix-p02`; `make up`, `make migrate`
(head `0027_optimisation_proposals`); the lane's fifteen `.env` names exported
(`set -a; . ./.env; set +a`); `.venv` in the worktree is symlinks to the shared runtime and
bootstrap environments. Runs were detached (`nohup setsid`, one log and one rc file each).
Command: `$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <paths>`. Free disk
(`df -BM /`) 3795 MiB and memory available 5106 MiB at the last measurement; a run of these files
builds no image and writes only a few MiB.

Before (tree `c90d52f3`):

| run | result |
| --- | --- |
| the four named tests | 4 failed in 0.3 s (on the fresh lane database `test_no_grounded_false_row_exists_anywhere` failed as "no observations at all", not yet as the gate's set) |
| `tests/integration/p02_journey` | 2 failed, 57 passed in 389 s: `test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes` and `test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete`. `test_no_grounded_false_row_exists_anywhere` was green on a database holding only this suite's rows: it is red only where another suite's committed row is present, which is what the gate had |

After (tree `d457aee8`, lane database holding the foreign `quotation_absent` row):

| run | result |
| --- | --- |
| the four named tests, `-v` | 4 passed in 6.8 s |
| `tests/integration/p02_journey` + `tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py` | 62 passed in 321 s (p02_journey 60: the 59 of before plus the new behavioural test; bridge file 2) |
| `tests/contract/program` | 28 passed in 1.0 s |

`tests/integration/comparison` was not run: `src/auditmanager/comparison/**` and
`tests/integration/comparison/**` were not touched.

## Checks on the final tree

`git diff --check` clean (exit 0). `tests/contract/program`: 28 passed in 1.0 s. The documentation prose
guards that read `docs/` (`tests/contract/api_v1/test_doc_prose_facts.py`,
`test_surface_counts_in_prose.py`, `tests/contract/domain_p02/test_seam_register.py`) with this report in
the tree: 97 passed in 14 s. All four exit statuses 0, read from the rc files of the runs.

## Contracts

None new or changed.

## Risks and known limitations

- The scoped guard (`test_no_grounded_false_row_exists_anywhere`) no longer sees a `grounded=false`
  row of another profile. That is the point (the AR v2 and v3 recorded chains have their own
  publication paths and tests), but it means this suite is silent about those chains. Nothing was
  lost that this suite could ever have asserted: the removed coverage was an accident of table
  sharing, and it is what turned the gate red.
- `jobs/test_recorded_v2_publication_gate.py::test_preexisting_observation_without_finding_refuses_publication`
  commits a permanent `grounded=false` row into the shared database. It is out of this task's allowed
  paths and `finding_observation` refuses `DELETE`; it is left as it is. Any future suite that
  asserts a property of the whole `finding_observation` table in a shared database will meet it.
- The page-hash scan is name-based: a module that built the name at runtime (`"page_text" +
  "_sha256"`) would not be found by it. The behavioural test covers the one allowed module's output
  regardless; the scan is a tripwire, as it was before.
- The twelve new tables are counted but the journey never writes them, so their replay claim is
  "stays at 0". It is not shown failing individually per table; the completeness guard is shown
  failing (above) and the counts are read by the same `table_counts` as the older groups.
- The mutation runs depend on the code reading `contracts`, `db`, `docs` and `fixtures` relative
  to the repository root; the scratch copies symlink them. Nothing tracked was mutated.

## Integrator instruction

Merge `agent/gate-fix-p02-01` (a real merge) into `integration/night-1020`, re-cut the candidate, and
let the complete gate run on the exact new SHA. These four tests are the ones to look at first:
`jobs/test_recorded_v2_executor_bridge_db_accept.py::test_persisted_recorded_executor_saves_five_stages_one_call_and_one_terminal`,
`p02_journey/test_whole_journey_idempotency.py::test_the_table_list_this_suite_counts_is_complete`,
`p02_journey/test_ungrounded_diagnostic_path.py::test_no_grounded_false_row_exists_anywhere`,
`p02_journey/test_extractor_divergence.py::test_no_module_consumes_the_manifest_page_hashes`.
In the complete gate the first of the four to be checked is the third: it is the one whose failure
depended on which other suites had run before it.

## Forbidden hotspots

`git diff --stat c90d52f3 d457aee8` lists exactly
`tests/integration/jobs/test_recorded_v2_executor_bridge_db_accept.py`,
`tests/integration/p02_journey/journey.py`,
`tests/integration/p02_journey/test_extractor_divergence.py`,
`tests/integration/p02_journey/test_ungrounded_diagnostic_path.py` and
`tests/integration/p02_journey/test_whole_journey_idempotency.py`; this report is the only other
path. `journey.py` is under `tests/integration/p02_journey/**`, which the task allows; it is not a
`conftest.py`.
