# GATE-FIX-CONTRACT-01 — the stale contract-level reds before the complete gate

Task: `docs/program/tasks/GATE-FIX-CONTRACT-01.md`. Branch `agent/gate-fix-contract-01`, based on
`7bdb254e` (`origin/dev` `8697baea` plus the three frozen task files). Debt `D-187` named both reds.

## Result

`tests/contract` is green on this tree apart from the three environment-only families. The two
non-environment reds were stale pins, not product defects; no `contracts/**`, `src/**`, migration,
`web/**` or dependency file changed.

| Red | Cause | Decision |
| --- | --- | --- |
| `shared_kernel/test_error_kernel.py::TheEnumIsExactlyTheCatalog::test_there_are_twenty_four` | pinned 24; the enum and `contracts/domain/v1/error-codes.json` hold 25 since `W56A-SEAL-01` (`bcd5ad26`, candidate revision 13, `R-133`) added `model_identity_mismatch` | stale pin: now `test_there_are_twenty_five`, pin 25, docstring history names the 25th code and the 24th (`analysis_input_budget_exceeded`, `W55B-SEAL-01`) |
| `fixtures_seeded/test_ar_v2_seeded.py::test_seeded_categories_equal_the_sealed_api_enum` | `FindingCategory` in `contracts/api/v1/openapi.json` grew from 7 to 12 values in `W57A-SEAL-01B` (`56efead4`: `evacuation`, `fire_safety`, `accessibility`, `insulation`, `sound` appended in that order); the seeded generator still had the original 7 | stale vocabulary: the seeded corpus was extended so every sealed category has three issues in at least two bundles and a control; the guard stays an exact tuple equality |

## Failing list before and after

Command, both times: `$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract -rf`
from the worktree (`PY` = the `w55b-main-candidate` interpreter; `.venv/bootstrap` symlinked, ignored
by git), container-free, about 2 min 25 s. Before: tree `7bdb254e`. After: tree `b7031f33` (code)
and again on the report commit, same result.

| | before | after |
| --- | --- | --- |
| summary line | 84 failed, 1061 passed, 126 errors, 19685 subtests passed | 82 failed, 1089 passed, 126 errors, 19685 subtests passed |
| `test_error_kernel.py` | 1 | 0 |
| `test_ar_v2_seeded.py` | 1 | 0 |
| `test_cp00_candidate.py` | 48 failed + 3 subtests failed + 126 errors | identical |
| `test_cp00_final_state.py` | 3 | identical |
| `test_validate_bootstrap.py` | 21 failed + 7 subtests failed | identical |

The last three rows are the environment-only families the task leaves. Observed causes: in a git
worktree `.git` is a file (`NotADirectoryError: ... gate-fix-contract/.git` at
`shutil.copytree(REPOSITORY_ROOT / ".git", ...)`, the source of the 126 setup errors in
`test_cp00_candidate`); the interpreter lacks `jsonschema` (`test_validate_bootstrap`, "required Python
dependency 'jsonschema' is unavailable"). The three `test_cp00_final_state` failures (tag integrity,
file and hash accounting, cross-gate agreement) compare the checkpoint's recorded artifacts with the
live repository; they are the integrator's classification and were not re-diagnosed here.
`tests/unit`: 517 passed before and after.
The 28 added passes are the two repaired tests, one new guard and 25 parametrised cases for the new
categories.

## How the cases for the five new categories were written

Rule (the same as the original seven, stated in the `cases.py` docstring): a planted contradiction
between two statements of the document itself, three per category, and one near-miss control whose
two values belong to different named objects. No case names a norm, a clause number or a normative
threshold, so the oracle needs no norm text and cannot assert a normative claim; whether a value
would also violate a norm is the retrieval layer's question. Every designator is unique across the
corpus (`Э-1`, `ПР-1`, `ПН-1`, `НС-1`, `ПГ-1`, ...) so cases in the same bundle cannot contradict one
another by accident, and no new statement starts with `Лист АР-` (that prefix feeds the
supplied-header inventory). All 79 quotes in the manifest are distinct.

| Category | Issues (archetype) | Control |
| --- | --- | --- |
| `evacuation` | `ev_width` (exit width 1,20 m vs 0,80 m), `ev_route` (route length 25 m vs 40 m), `ev_stairs` (2 vs 1 escape stairs) | `control_exits`: two different exits |
| `fire_safety` | `fs_rating` (partition EI 45 vs EI 15), `fs_door` (door EI 30 vs ordinary), `fs_class` (structural fire hazard class С0 vs С1) | `control_ratings`: two different partitions |
| `accessibility` | `ac_ramp` (ramp slope 5 vs 10 percent), `ac_lift` (cabin depth 2100 vs 1400 mm), `ac_parking` (4 vs 2 places) | `control_ramps`: two different ramps |
| `insulation` | `in_thickness` (150 vs 100 mm), `in_material` (extruded polystyrene vs mineral wool), `in_glazing` (two-chamber vs one-chamber unit) | `control_walls`: two different walls |
| `sound` | `so_index` (52 vs 41 dB), `so_impact` (impact noise 58 vs 70 dB), `so_layer` (50 vs 30 mm) | `control_partitions`: two different partitions |

Mechanics. The cases are appended to the end of `ISSUES` and `CONTROLS`, so the 21 original issues
and 7 controls keep their index, bundle and manifest entry (verified: every original entry is equal
in the new manifest). The generator places an issue in bundle `index % 10`; the new issues therefore
spread each category over three bundles. Controls were placed by `index == bundle number`, which with
12 controls on 10 bundles would have silently dropped two; the rule is now `index % BUNDLE_COUNT`
(identical for the original 7). The validator's minimum case count is derived from `CATEGORIES`
(`3 * 12` issues, `12` controls) instead of the literals 21 and 7. Regeneration:
`$PY tools/fixtures/seeded/generate.py` then `$PY tools/fixtures/seeded/generate.py --check`
("AR v2 seeded corpus OK: 10 bundles, 36 issues, 12 controls"). Every bundle gained lines, so all 20
PDF and ZIP files are new bytes; the digest table in `W56A-GENERATOR-PREP-01.md` and the manifest
SHA-256 `95e07c29...6dae6fb7` there and in the `W56A-INT-*` records are historical. The manifest
SHA-256 is now `067fafb9bf4b489a7bf869ba86134f4e5c23406e8cbe03e0c490aa0a127b89ae`.

## Consumers of the seeded set

`grep` over `src`, `tests`, `tools`, `web/src`, `Makefile`, `infra`, `scripts` finds these readers of
`fixtures/evaluation/ar_v2` (the other `expected_issues.json` readers use `fixtures/synthetic/ar`, a
different corpus, and were not touched):

| Consumer | Effect | Action |
| --- | --- | --- |
| `tests/contract/fixtures_seeded/test_ar_v2_seeded.py` | counts 21/7 | pin 36/12; the per-case and per-category parametrised guards cover the new cases without edits |
| `tests/contract/evaluation/test_matcher_core.py` | literals 21, 7, `1/21`, `1/7`, seven categories | 36, 12, `1/36`, `1/12`, twelve; test renamed `..._one_thirty_sixth` |
| `tests/contract/evaluation/test_bridge.py` | literals 21 (three times), `20/21` | 36, `35/36` |
| `tools/evaluation/local_bundle.py` | `FROZEN_SEEDED_MANIFEST_SHA256` pinned the old manifest; every saved-Run join refused with `seeded_local_manifest_changed` (8 failures in `tests/integration/evaluation/test_local_bundle.py`) | the pin moves to the new SHA-256 (still an exact digest, comment names the previous value); a new container-free contract test, `test_the_evaluation_adapter_freezes_the_committed_manifest_digest`, now reddens in `tests/contract` if the corpus is regenerated without re-freezing |
| `tests/integration/evaluation/*` | manifest-derived, no literals | 27 passed, run container-free |
| `tools/evaluation/{matcher,bridge,run_sources}.py` | read categories from the manifest | no change needed |

## Mutation proofs

Each against the repaired tree, one edit, run, restore; the tree hash of `tests`, `tools` and
`fixtures` was identical before the probes and after the last restore.

1. Stale pin back to 24: `self.assertEqual(len(list(ErrorCode)), 24)` gives
   `AssertionError: 25 != 24` and `FAILED ...test_error_kernel.py::TheEnumIsExactlyTheCatalog::test_there_are_twenty_five`.
2. `"sound"` removed from `cases.CATEGORIES`:
   `assert tuple(contract[...]["FindingCategory"]["enum"]) == cases.CATEGORIES` fails
   (`test_seeded_categories_equal_the_sealed_api_enum`).
3. The previous digest `95e07c29...` restored in `local_bundle.py`:
   `assert '95e07c2919d4...0126d6dae6fb7' == '067fafb9bf4b...0aa0a127b89ae'` in
   `test_the_evaluation_adapter_freezes_the_committed_manifest_digest`.
4. Issue `so_layer` deleted from `cases.ISSUES`: `seeded.validate.CorpusError: sound: fewer than three
   issues`, `test_regeneration_is_byte_stable_and_matches_committed_bytes` fails.
5. The control-placement fix reverted (`if index != number or ...`): `CorpusError: control category
   coverage incomplete`, the same test fails.

Probe hygiene: the first run of the final measurement read a stale `.pyc` of the mutated
`test_error_kernel.py` (the restore landed in the same second as the same-length mutation, so the
cached bytecode still matched the source's size and whole-second mtime) and showed the repaired pin
red. After clearing the worktree's `__pycache__` the full directory was measured again with
`PYTHONDONTWRITEBYTECODE=1`; the figures above are that run. A same-length mutation needs the cache
cleared or a second between edit and restore.

## Deviations from the task file

The task's `allowed_paths` name `tools/seeded/**` and `tools/ar_corpus/**`, which do not exist; the
generator lives in `tools/fixtures/seeded/**` (and `tools/fixtures/ar_corpus/**`, not touched), its
fixtures in `fixtures/evaluation/ar_v2/**` (not `fixtures/validation/**` or `fixtures/synthetic/**`).
The consumers named above live in `tests/contract/evaluation/**` and `tools/evaluation/local_bundle.py`.
Those four paths are the evident referents of the stale globs and the dependent tests the integrator's
brief asked to repair; none is a forbidden hotspot (`contracts/**`, migrations, `src/**`, `web/**`,
dependency files, `CURRENT_STATE.md`, refs, tags, the stand). The task file itself was left unedited;
the integrator may correct its globs.

## Risks and known limitations

- The AR v2 analysis profile's own response schema
  (`src/auditmanager/analysis/profiles/ar_v2/response_schema.py`) emits only the original seven
  categories; the five normative ones belong to `ar_v3`. Scored over the whole manifest, a v2 run's
  recall ceiling is now 21/36. No `baseline.json`, recording or no-regression gate exists on this tree,
  so nothing breaks today, but a future v2 baseline must score the seven categories it can emit
  (the matcher already reports `per_category`) or run the v3 profile. The alternative reading of the
  red, keeping the frozen v2 corpus and making the guard compare against the profile's seven plus a
  documented normative remainder, was not taken because it relaxes an exact equality; reverting commit
  `b7031f33` returns to the frozen seven-category corpus (and to the red guard).
- The manifest digest is re-frozen: `FROZEN_SEEDED_MANIFEST_SHA256` and the 20 fixture binaries moved
  together. Historical records that quote `95e07c29...` are not edited.
- `tests/integration/*` outside `tests/integration/evaluation` and every database-backed suite were not
  run (`R-126`, `R-135`); only the container-free evaluation integration directory was.
- No full gate, no `CURRENT_STATE.md` edit, no ref or tag.

## Checks

| Command | Result |
| --- | --- |
| `$PY tools/fixtures/seeded/generate.py --check` | exit 0, "10 bundles, 36 issues, 12 controls" |
| `$PY -m pytest ... tests/contract` | 82 failed (environment families only), 1089 passed, 126 errors (same family) |
| `$PY -m pytest ... tests/contract/shared_kernel tests/contract/fixtures_seeded tests/contract/evaluation tests/integration/evaluation` | 134 passed |
| `$PY -m pytest ... tests/unit` | 517 passed |
| `git diff --check` | exit 0 |

## Hotspot proof

`git diff --name-only 7bdb254e..HEAD` touches only: `tools/fixtures/seeded/{cases,generate,validate}.py`,
`tools/evaluation/local_bundle.py`, `fixtures/evaluation/ar_v2/` (the manifest and 20 bundle files),
`tests/contract/{shared_kernel,fixtures_seeded,evaluation}/`, and this report. A match for
`contracts/`, `db/`, `src/`, `web/`, `pyproject.toml`, `uv.lock`, `requirements`, `infra/` or
`docs/program/CURRENT_STATE.md` returns zero paths.

## Integrator instruction

Merge `agent/gate-fix-contract-01` (a real merge) into `integration/night-1020`; on the merged tree
re-run `generate.py --check`, `tests/contract` (expect only the three environment families) and
`tests/integration/evaluation`. Debt `D-187` loses its `test_error_kernel` and `test_ar_v2_seeded`
entries.
