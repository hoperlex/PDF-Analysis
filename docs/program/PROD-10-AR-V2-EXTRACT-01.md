# PROD-10-AR-V2-EXTRACT-01 — what АР v3 needs moves out of ar_v2, and registered.py is split

Task: `docs/program/tasks/PROD-10-AR-V2-EXTRACT-01.md`. Branch `agent/prod-10-ar-v2-extract-01`, base `bfcb8a97` (`integration/ar-close-1026`). Plan item `PROD-10` of `PRODUCTION-READINESS-PLAN-01.md`, design `ADR-0024` section 2 (`AD-12`, `R-146w`, `R-146l`, `R-146g`). Behaviour-preserving: АР v1 and v2 keep working; the removal and the contract reseal are `PROD-11`.

## Result

Steps 1 to 3 are done. `grep -rn "profiles.ar_v2" src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised` prints nothing, and a committed AST test proves it for imports that run. The three modules (`content`, `recognised_context`, `grounding`), the six `.md` files `content.py` reads and the two identity constants now live in `src/auditmanager/analysis/profiles/ar_shared/` (`ADR-0024` names no location; the lane file suggested this one). `resolve_recorded_profile` stays with v2.

Step 4 (the live journey) is **not done, deliberately**: it is not a small edit and cannot be verified without a browser and a stand. A scoped follow-up is below, with one finding that `PROD-11` must see (section "The journey").

## Premise: match, with three deviations (evidence in the task file, P-01 to P-05)

- Match: the five `ar_v3` importers and the one `recognised` importer are the ones the plan names; `registered.py` imports `content`, `prompt_material`, `response_schema`; the six `.md` files are the six the ADR lists; the closure of what v3 and `recognised` use is exactly `content`, `recognised_context`, `grounding` and the two constants of `registered` (AST closure, P-02). The three modules "that do not carry the name" are not importers of `ar_v2` at all; they reach it through `analysis.public`, and none of the names they take is moved.
- Deviation 1: the ADR says the closure of the whole `registered` is "six modules"; the AST gives five (`registered`, `content`, `prompt_material`, `recognised_context`, `response_schema`). Immaterial: the move is the three modules and the constants.
- Deviation 2: `src/auditmanager/analysis/public.py` imports two moved names (`RecognisedContext`, and `PROFILE_ID` / `PROMPT_BUNDLE_ID`). It is not in the lane's allowed paths and it is the module `PROD-11` prunes. I edited its two import statements and nothing else; it is not a composition root. If the integrator wants that edit owned elsewhere, it is one hunk (`git show 55f8ce4e -- src/auditmanager/analysis/public.py`).
- Deviation 3: the plan says `web/tests/e2e/pc01/`; the journey is `tests/e2e/pc01/` (no `web/` file names `ar_v2`).

## Files changed (commit `55f8ce4e`, 44 files; `git diff --name-only bfcb8a97..HEAD` for the exact list)

| Path | Change |
|---|---|
| `ar_shared/{content,recognised_context,grounding}.py`, `ar_shared/{role,finding_categories,checklist,drawing_types,project_params,ar_checklist}.md` | `git mv` from `ar_v2/`; the `.md` files are 100 % renames (bytes unchanged); `grounding.py` differs by one import line |
| `ar_shared/v2_identities.py` | new: `PROFILE_ID`, `PROMPT_BUNDLE_ID`, values unchanged |
| `ar_shared/__init__.py` | new: docstring only |
| `ar_v2/registered.py` | the two constants removed; reads them as `v2_identities.PROFILE_ID` (module-qualified, so `registered.PROFILE_ID` no longer exists: no shim); `content` import re-pointed; everything else untouched |
| `ar_v2/{prompt_material,proposal_grounding,recorded_artifact,recorded_input,recorded_request,response_pipeline}.py` | import paths of the moved modules |
| `ar_v3/{v3_profile,citation_grounding,prompt_material,local_evaluation,request_candidate}.py`, `analysis/recognised/region_candidate.py` | import paths; `v3_profile` takes the constants from `v2_identities` |
| `analysis/public.py` | two import statements (see deviation 2) |
| 18 test files under `tests/integration/{analysis,findings,runs}` | import paths and, where a test read `registered.PROFILE_ID`, `v2_identities.PROFILE_ID` |
| `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py` | new guard, 13 cases |
| this report, the task file | records |

## Modified tests: what each asserted before and after

No assertion was added, removed, loosened or changed in value; every edit is an import path or the qualifier of an identical value. `git diff -U0 bfcb8a97..HEAD -- tests/integration` shows only `import` lines and the qualifier changes below.

| Test file | Before | After |
|---|---|---|
| `test_ar_v2_grounding_prep`, `_prompt_material`, `_proposal_grounding`, `_recognised_context`, `_response_pipeline`, `_recorded_input` (recognised part), `_recorded_request` (import part) | import `ar_v2.{recognised_context,grounding,content}` | import `ar_shared.{...}`; same assertions |
| `test_ar_v2_profile_content` | `from ...ar_v2 import content` | `from ...ar_shared import content`; the tamper cases copy the `.md` files from `Path(content.__file__).parent`, which moved with the module |
| `test_ar_v2_registered_profile` | `registered.PROFILE_ID`, `registered.PROMPT_BUNDLE_ID`, `ar_v2 import content` | `v2_identities.PROFILE_ID`, `v2_identities.PROMPT_BUNDLE_ID`, `ar_shared import content`; every `resolve_recorded_profile` and monkeypatch case unchanged (`registered` still has `reviewed_content_sha256`, `material_sha256`, `response_schema`) |
| `test_ar_v2_recorded_request` | `registered.PROFILE_ID` / `.PROMPT_BUNDLE_ID` in `_build` | `v2_identities.` of the same values |
| `test_ar_v2_recorded_artifact`, `_recorded_call`, `_recorded_response`, `_recorded_input`; `findings/test_v2_recorded_saved_plan`; `runs/test_recorded_v2_sources` | `from ...ar_v2.registered import PROFILE_ID, PROMPT_BUNDLE_ID` | `from ...ar_shared.v2_identities import PROFILE_ID, PROMPT_BUNDLE_ID` |
| `test_ar_v3_citation_grounding`, `_local_evaluation`, `_prompt_material`, `_request_candidate` | import `ar_v2.{recognised_context,content}` | import `ar_shared.{...}`; same assertions |

## Byte-identity proof

`identity_probe.py` (scratch, not committed) loads the objects and prints, as sorted JSON: the SHA-256 of each of the six `.md` files, `reviewed_content_sha256()`, the SHA-256 of each reviewed prompt section, the two v2 constants, the whole `RecordedArV2Profile` from `resolve_recorded_profile`, `v2 material_sha256()`, the canonical hash of the v2 response schema, the whole `BetaV3Profile` from `resolve_beta_v3_profile` (identities, `content_sha256`, `bundle_sha256`, scenario, snapshot, policy and composition hashes, scopes), the SHA-256 of the v3 system prompt (twice, from the profile and from `render_v3_system_prompt()`) and of the v3 response-schema JSON. The probe imports from `ar_shared` when it exists and from `ar_v2` otherwise.

```text
before (tree bfcb8a97):  sha256 3aecb11b94220f280dd5535307904a367fb3d3c339fa61b39a3313b921500280
after  (tree 55f8ce4e):  sha256 3aecb11b94220f280dd5535307904a367fb3d3c339fa61b39a3313b921500280   cmp: IDENTICAL
```

`git diff --stat bfcb8a97..HEAD -- fixtures` prints nothing (recordings byte-identical). `resolve_beta_v3_profile` and `resolve_recorded_profile` also check their pinned hashes on every call, and both still succeed.

## The guard and its mutation table

`tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py` reads `src/auditmanager` with `ast` (executes nothing) and holds: (a) no module under `ar_v3/` or `analysis/recognised/` imports `ar_v2`; (b) no chain of runtime imports from them reaches `ar_v2` inside the analysis context (`auditmanager.analysis.*` and `auditmanager.shared.*`), and a module of another context that they import must itself not import `ar_v2`; (c) no module of that closure takes a v2 export of `analysis.public` (names, or `*`); (d) `analysis.public` is the only module outside `ar_v2` that imports `ar_v2`; (e) `ar_v2` holds none of the six `.md` files, no `content.py`/`recognised_context.py`/`grounding.py` and `registered` has no `PROFILE_ID`/`PROMPT_BUNDLE_ID`. Seven more cases feed a mutated copy of the real sources to the same functions and expect the violation (direct, relative import, chain through `ar_shared`, v2 export from `analysis.public`, through the `auditmanager.analysis` package, new importer, and the negative: an import under `TYPE_CHECKING` is not an edge).

Real-file mutations, each applied alone to the committed tree, the suite run, the file restored; last row after restoring:

| Mutation | Red (guards) |
|---|---|
| M1 `ar_v3/prompt_material.py` += `from ...ar_v2.registered import PROFILE_ID` | direct, transitive, only-sink-imports, shim (suite 7 failed) |
| M2 `analysis/recognised/flags.py` += `from auditmanager.analysis.public import resolve_recorded_profile` | closure-takes-a-v2-export (3 failed; the shim case fails too because the mutated tree no longer imports cleanly) |
| M3 `ar_shared/content.py` += import of `ar_v2.response_schema` | transitive (`ar_v3...prompt_material <- ar_shared.content <- ar_v2.response_schema`), only-sink-imports |
| M5 `norms/public.py` += import of `ar_v2.response_schema` | transitive (a module outside the analysis context imports `ar_v2`), only-sink-imports |
| M6 `analysis/text/anchors.py` += import of `ar_v2.response_schema` | transitive, only-sink-imports |
| M4a `ar_v2/registered.py` += `from ...ar_shared.v2_identities import PROFILE_ID` | shim case (1 failed) |
| M4b re-create `ar_v2/content.py` | shim case (1 failed) |
| M4c copy `role.md` back into `ar_v2/` | shim case (1 failed) |
| restored | `13 passed` |

## Test results

Run in this worktree on the committed code tree, one pytest at a time; `PYTHONPATH=src:<bootstrap site-packages>` with the repo `.venv`. No database or object store was available.

| Command | Result |
|---|---|
| `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py` | 13 passed |
| `tests/integration/analysis/test_ar_v2_*.py test_ar_v3_*.py` (before the new guard existed, same files) | 244 passed, 6 skipped (`AR_SCOPE_BUNDLE_ROWS` unset in `test_ar_v3_scope_partition.py`, unrelated) |
| `tests/integration/analysis/test_*.py` (top level) | 507 passed, 6 skipped |
| `tests/integration/findings/test_v2_recorded_chain.py`, `tests/integration/analysis/recognised/test_region_candidate.py` | 26 passed |
| `tests/integration/findings/test_v2_recorded_saved_plan.py`, `runs/test_recorded_v2_sources.py`, `runs/test_v2_recorded_executor.py` | 40 passed |
| `tests/integration/runs/test_v3_*.py`, `test_v2_recorded_*.py`, `test_w59_section_profile_recorded.py`, `findings/test_merge_publication_plan.py`, `findings/test_analysis_public_boundary.py` | 304 passed, 9 errors, all `DATABASE_URL is not set` in `test_w59_section_profile_recorded.py` |
| `tests/unit/analysis` / `runs` / `executors` | 76 / 11 / 437 passed |
| `tests/unit/executor_runner` | 121 passed, 5 failed: `test_ssh_forced_command.py::test_quoted_and_bare_key_lines_are_accepted` (a shell-script test with no import from `src`); the same 5 fail on an untouched extraction of `bfcb8a97` (`tools/executor-runner`, `tests/unit/executor_runner`), so not caused here |
| `tests/contract/analysis_packages` / `tests/contract/architecture` (ALR-05 boundary, `ar_shared` satisfies it) | 52 / 4 passed |
| `tests/e2e/test_pc01_journey_conformance.py` (static) | 135 passed |
| `python -c "import auditmanager.analysis.profiles.ar_v3, ...ar_v3.v3_profile, ...recognised.region_candidate, auditmanager.analysis.public, auditmanager.runs.executor"` | import ok |
| docs guards `tests/contract/program`, `test_doc_prose_facts.py`, `test_surface_counts_in_prose.py`, `git diff --check`, governance one-liner | see the last section |

**Not run (need a stack), for the integrator:** `tests/integration/runs/test_w59_section_profile_recorded.py` (9 cases, PostgreSQL), `tests/integration/analysis/geometry` and the S3-backed files of `tests/integration/analysis/recognised` (object store), and the rest of `tests/integration/{runs,findings,analysis}` on a lane stack. Every test file that imports a moved name is in `tests/integration` and was run here except through those database fixtures: the 18 modified files are all in the green rows above.

## Known limits

1. **The strict whole-repository closure of `ar_v3` still reaches `ar_v2`, and cannot not before `PROD-11`.** `ar_v3.citation_grounding` imports `norms.public`, which reaches `jobs.public`, `runs.public`, `runs.executor`, the `runs.recorded_v2_*` modules and so `analysis.public`, which imports `ar_v2`. Separately, importing any module under `auditmanager.analysis` runs `analysis/__init__.py`, which imports `analysis.public`: `python -c "import auditmanager.analysis.profiles.ar_v3.v3_profile"` loads `ar_v2` modules into `sys.modules`. The guard therefore names `analysis.public` as the one sink and forbids taking its v2 exports (docstring of the test). Both dissolve when `PROD-11` removes the v2 exports and the recorded-v2 modules; it then deletes `_SINKS` and tightens (d) to an empty set. Dynamic `importlib` calls are not followed.
2. `ar_v2` still imports `ar_shared` (allowed: "the v2 package may import the shared one").
3. The module `__module__` of `RecognisedContext`, `ProfileContentError` etc. changed (`ar_shared.*`); no test or source file reads `__module__` or `__qualname__` of a moved class (`rg -n "__module__|__qualname__" src tests fixtures --glob '*.py'`: the hits concern norms, storage and boto classes).
4. Module docstrings of the moved files still say "AR v2" in their first line (kept so the move stays a pure move); `PROD-11` or a later cleanup may reword.

## The journey: a scoped follow-up (step 4 stopped on purpose)

**Why it is not a small edit.** `tests/e2e/pc01/journey/manifest.json` (7 490 lines, 109 write steps) has four steps that press «Запустить прогон», every one on a set confirmed as АР, and the AR-ness is spread over 59 lines of the manifest and the files below. After `PROD-11` an АР version answers `section_profile_unavailable`, so those four steps cannot publish. The same bundle is uploaded three times (`fixtures/synthetic/ar/bundles/ar_baseline.zip`), so a non-АР section's recording (`fixtures/recorded/sections/<code>/`, built over `ar_baseline_text_layer.json`, `SECTION-RECORDINGS-01.md`) would be found for all three. But it carries different findings than the AR baseline recording (КЖ: one fire-resistance observation; КМ: exits), and the steps `record-decision`, `compare-versions-read-only`, `carry-over-decision`, `run-exports`, `classification-correction`, `dashboard-sections-panel`, the queue and blocks steps read those findings. Nothing here can be verified without a browser and a stand, and a half-moved journey is worse than a clean follow-up.

**The finding that matters to `PROD-11`.** `ADR-0024` section 2 says АР project optimisation and the specification reads "are not part of the АР analysis path". They depend on it: `optimisation/project_match.py` (`_newest_published`, lines 207-216) and `optimisation/section_specification.py:529` read the saved `prepared.text_layer` of the **newest published run of the version**, and answer `analysis_missing` when there is none. Today that run is an АР v1 run (the journey's `start-specification-run`). After `PROD-11` an АР version can start only the v3 group; whether a v3 group run publishes with a saved text layer is not established here. So «Спецификация и цены», the optimisation pass, Form-7 (`section-form7`, `dashboard-sections-panel`) and 32 steps of the journey (the 29 from `upload-specification-set` to `proposals-csv-with-a-formula-vendor`, plus `section-form7`, `section-form7-without-members`, `dashboard-sections-panel`) lose their input unless a published run can still exist for an АР version. This needs a decision before `PROD-11` merges (owner or the contract/executor owner), not a Sonnet lane.

**Scope of the follow-up (one lane, needs a stand to verify).**

| Item | Files and places |
|---|---|
| Section of the three analysis runs | `manifest.json` steps `classify-version` (`data-section-choice="AR"` near lines 1101 and 1131), `classify-second-version` (1488, 1519), `classify-third-version` (1858, 1883): change the section and the `section_code` response pins; `classification-correction` (keeps АР in its comment and pins) |
| The specification set | `upload-specification-set`, `classify-specification-set` (3028), `start-specification-run` (replays `fixtures/recorded/sections/ar_specification/`): depends on the finding above |
| Settings screen | `analysis-settings-lists-the-profiles` pins `tr[data-section="AR"][data-profile="builtin"]` (line 2086): `PROD-11` and `PROD-14.0` territory (`builtin` disappears) |
| Counts that assume the journey's set is АР | `section-form7`, `section-form7-without-members`, `dashboard-sections-panel` (`li[data-section="AR"] strong`, lines 5556-5651) |
| Static pins | `tests/e2e/test_pc01_journey_conformance.py` (12 AR pins; 135 cases pass now), `tests/e2e/pc01/driver.py` (`section_code="AR"` default, lines 204 and 243-255), `test_acceptance.py:184,567-568`, `test_live_text_analysis.py:202`, `journey/fixtures/redden-write.manifest.json`, `redden-write-bound.manifest.json`, `w28-live/*.manifest.json`, `journey/README.md`, `journey.mjs` comments |
| Manual protocol | `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` (7 mentions), `scripts/manual-alpha-check.sh` (3) |

What would be verified live (`npm --prefix web run e2e:pc01 -- --phase all` on a lane stand, `PROD-18`'s window): each moved run publishes from its section recording; the P to R comparison still has a «Без изменений» row whose older finding carries the verdict, so `carry-over-decision` has its precondition; `run-exports`, blocks, queue and dashboard counts against the new findings; the specification and optimisation segment under whatever the decision above says.

## Integration notes

- Merge after `PROD-14.0` (already on the base) and before `PROD-11`. `PROD-11` must: delete `ar_v2`, drop the v2 exports of `analysis/public.py`, then remove `_SINKS` and tighten (d) in `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py`.
- The integrator runs the stack-bound tests listed above.
- No contract, migration, composition-root, `runs/executor.py`, `infra/`, `web/` or `fixtures/` file is touched.

## Forbidden paths untouched

```text
$ git diff --name-only bfcb8a97..HEAD | grep -E '^(contracts/|db/|infra/|web/|fixtures/|tests/e2e/|src/auditmanager/(runs|bootstrap|api|findings|norms|optimisation)/|pyproject|requirements|package)|P02_LOCK|profile\.json|system_prompt\.md|CURRENT_STATE|DEBT_REGISTER|PRODUCTION-READINESS|OWNER_RULINGS|/adr/'
(no output)
```

The list is in the last section's command output below.
