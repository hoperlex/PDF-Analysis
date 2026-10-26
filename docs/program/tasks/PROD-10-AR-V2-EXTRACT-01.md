# Task PROD-10-AR-V2-EXTRACT-01 — what АР v3 needs moves out of ar_v2, and registered.py is split

task_id: PROD-10-AR-V2-EXTRACT-01
status: steps 1-3 completed in development candidate; step 4 (the live journey) is a scoped follow-up, not done

## Outcome

`grep -rn "profiles.ar_v2" src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised` prints nothing, and a committed AST test proves it for imports that run, so `PROD-11` can delete `ar_v2` without breaking АР v3. The three modules `content`, `recognised_context` and `grounding`, the six reviewed `.md` files `content.py` reads and the two identity constants of `registered.py` now live in `src/auditmanager/analysis/profiles/ar_shared/`; `resolve_recorded_profile` stays with v2. Behaviour is unchanged: the hashes of the loaded v2 and v3 profile objects, prompts and data files are equal before and after.

## Depends on

- `PRODUCTION-READINESS-PLAN-01` item `PROD-10` (`AD-12`, confirmed by `R-146w` as written at `83600aed`), design `ADR-0024` section 2 — completed documents.
- `SECTION-RECORDINGS-01` — completed (read for the journey scoping only).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged
- base commit: `bfcb8a978e9ec9dd9fb3ac500e4b17551674e24b` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No route, screen, error code or migration is added. The guard test enumerates the importers of `ar_v2` itself (`test_only_the_named_sink_imports_ar_v2_from_outside_it`).

## Captured premise evidence

- premise: the five `ar_v3` importers, the one `recognised` importer, the `registered.py` import lines, the six data files and the closure the plan calls "three modules, six data files, two constants" are re-read at the base commit; the closure matches, one count in the ADR is off by one, and the journey is not a small edit

### P-01 — who imports ar_v2 from ar_v3 and recognised, the registered.py imports, the six files, the history

- captured_at: 2026-10-26
- command: `see the first line of each block in the captured output (git rev-parse, grep, git log, ls, grep on registered.py, rg -ln | wc -l)`
- captured_output:
  ```text
  $ git rev-parse HEAD
  bfcb8a978e9ec9dd9fb3ac500e4b17551674e24b

  $ grep -rn "ar_v2" src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised
  src/auditmanager/analysis/profiles/ar_v3/v3_profile.py:15:from auditmanager.analysis.profiles.ar_v2.content import (
  src/auditmanager/analysis/profiles/ar_v3/v3_profile.py:19:from auditmanager.analysis.profiles.ar_v2.registered import (
  src/auditmanager/analysis/profiles/ar_v3/v3_profile.py:23:from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py:13:from auditmanager.analysis.profiles.ar_v2.grounding import resolve_v2_anchor
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py:14:from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py:15:from auditmanager.analysis.profiles.ar_v2.content import reviewed_sections
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py:16:from auditmanager.analysis.profiles.ar_v2.recognised_context import (
  src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py:13:from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py:15:from auditmanager.analysis.profiles.ar_v2.recognised_context import RecognisedContext
  src/auditmanager/analysis/recognised/region_candidate.py:22:from auditmanager.analysis.profiles.ar_v2.recognised_context import (

  $ git log --oneline -3 -- src/auditmanager/analysis/profiles/ar_v2
  af03b938 feat(w56a): plan recorded findings from saved artifacts
  539f1051 feat(w56a): persist recorded merge stage from saved evidence
  610f7844 W56A: seal complete recorded v2 text stage result

  $ ls src/auditmanager/analysis/profiles/ar_v2/*.md
  src/auditmanager/analysis/profiles/ar_v2/ar_checklist.md
  src/auditmanager/analysis/profiles/ar_v2/checklist.md
  src/auditmanager/analysis/profiles/ar_v2/drawing_types.md
  src/auditmanager/analysis/profiles/ar_v2/finding_categories.md
  src/auditmanager/analysis/profiles/ar_v2/project_params.md
  src/auditmanager/analysis/profiles/ar_v2/role.md

  $ grep -n "^from\|^import" src/auditmanager/analysis/profiles/ar_v2/registered.py | grep auditmanager
  14:from auditmanager.analysis.profiles.ar_v2.content import reviewed_content_sha256
  15:from auditmanager.analysis.profiles.ar_v2.prompt_material import material_sha256
  16:from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES, response_schema
  17:from auditmanager.shared.identity import AnalysisProfileId, PromptBundleId

  $ rg -ln "ar_v2" src tests web --glob "!node_modules" | sort | wc -l
  57

  $ rg -n "ar_v2" web --glob "!node_modules"
  ```
- interpretation: matches the plan. Five `ar_v3` modules (`v3_profile`, `citation_grounding`, `prompt_material`, `local_evaluation`, `request_candidate`) and one `recognised` module (`region_candidate`) import `ar_v2`; `registered.py` imports `content`, `prompt_material` and `response_schema`; the six `.md` files are `role`, `finding_categories`, `checklist`, `drawing_types`, `project_params`, `ar_checklist`. The history of `ar_v2` is the W56A lane (`af03b938`, `539f1051`, `610f7844`). No `web/` file names `ar_v2` (the last command's final block is empty).

### P-02 — the import closure, by AST, not by string

- captured_at: 2026-10-26
- command: `python -I closure.py <tree of bfcb8a97>` (an `ast` walk over `src/auditmanager`: runtime `import` and `from` statements including function-level ones, `if TYPE_CHECKING:` bodies skipped, relative imports resolved; the script is in the lane's scratch and is not committed; the committed equivalent is `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py`)
- captured_output:
  ```text
  ar_v2 modules (17): ar_v2, ar_v2.content, ar_v2.grounding, ar_v2.merge_input, ar_v2.prompt_material, ar_v2.proposal_grounding, ar_v2.recognised_context, ar_v2.recorded_artifact, ar_v2.recorded_call, ar_v2.recorded_input, ar_v2.recorded_request, ar_v2.recorded_response, ar_v2.recorded_stage_result, ar_v2.registered, ar_v2.response, ar_v2.response_pipeline, ar_v2.response_schema

  importers of ar_v2 outside ar_v2 (direct):
    auditmanager.analysis.profiles.ar_v3.citation_grounding        -> grounding, recognised_context
    auditmanager.analysis.profiles.ar_v3.local_evaluation          -> recognised_context
    auditmanager.analysis.profiles.ar_v3.prompt_material           -> content, recognised_context
    auditmanager.analysis.profiles.ar_v3.request_candidate         -> recognised_context
    auditmanager.analysis.profiles.ar_v3.v3_profile                -> content, recognised_context, registered
    auditmanager.analysis.public                                   -> merge_input, proposal_grounding, recognised_context, recorded_artifact, recorded_call, recorded_input, recorded_request, recorded_response, recorded_stage_result, registered, response, response_pipeline, response_schema
    auditmanager.analysis.recognised.region_candidate              -> recognised_context

  closure INSIDE ar_v2 of the names ar_v3 + recognised import (content, recognised_context, grounding, registered):
    content             -> content
    recognised_context  -> recognised_context
    grounding           -> grounding, recognised_context
    registered          -> content, prompt_material, recognised_context, registered, response_schema

  whole registered closure: ['content', 'prompt_material', 'recognised_context', 'registered', 'response_schema']

  non-v2 modules each closure member imports (outside ar_v2, inside auditmanager):
    content             -> (nothing)
    recognised_context  -> analysis.recognised.artifact, analysis.recognised.flags
    grounding           -> analysis.text.anchors, analysis.text.textlayer
    registered          -> shared.identity
    prompt_material     -> analysis.text.textlayer
    response_schema     -> (nothing)
  ```
- interpretation: the plan's claim holds. What `ar_v3` and `recognised` import is `content`, `recognised_context`, `grounding` (which imports `recognised_context`) and, from `registered`, only the two constants. `recognised_context` and `grounding` import only `analysis.recognised.{artifact,flags}`, `analysis.text.{anchors,textlayer}`: nothing of v2, so the three modules move together and alone. `registered` cannot move whole: its closure is `content`, `prompt_material`, `recognised_context`, `response_schema` and itself. The ADR counts "six modules" for that closure; the AST gives five (the sixth may be `grounding`, which `registered` does not import); the count is immaterial because the move is the three modules and the constants. The three modules the plan says "do not carry the name" (`findings/recorded_saved_plan.py`, `findings/merge_publication_plan.py`, `analysis/stages/finding_merge.py`) are not importers of any `ar_v2` module: the only importer of `ar_v2` outside it, besides `ar_v3` and `recognised`, is `analysis/public.py`, which they reach through the `analysis.public` names, and none of those names is moved. `analysis/public.py` is not in the lane's allowed paths and imports two moved names (`RecognisedContext`, and `PROFILE_ID` / `PROMPT_BUNDLE_ID`), so it had to be edited (two import statements); it is not a composition root.

### P-03 — every importer of a moved name, source and tests

- captured_at: 2026-10-26
- command: `python -I census.py <tree>` (an `ast` walk over `src`, `tests`, `tools`, `scripts`; it lists the lines that import `ar_v2.content`, `.recognised_context`, `.grounding`, or `PROFILE_ID` / `PROMPT_BUNDLE_ID` from `.registered`, or the package-level `from ...ar_v2 import content`)
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/ar_v2/grounding.py [(11, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/profiles/ar_v2/prompt_material.py [(13, 'content', ['reviewed_content_sha256', 'reviewed_sections']), (17, 'recognised_context', ['RecognisedContext', 'render_context'])]
  src/auditmanager/analysis/profiles/ar_v2/proposal_grounding.py [(13, 'grounding', ['resolve_v2_anchor']), (14, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py [(23, 'grounding', ['REASON_RECOGNISED_ONLY'])]
  src/auditmanager/analysis/profiles/ar_v2/recorded_input.py [(20, 'recognised_context', ['RecognisedContext', 'select_context'])]
  src/auditmanager/analysis/profiles/ar_v2/recorded_request.py [(15, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/profiles/ar_v2/registered.py [(14, 'content', ['reviewed_content_sha256'])]
  src/auditmanager/analysis/profiles/ar_v2/response_pipeline.py [(17, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py [(13, 'grounding', ['resolve_v2_anchor']), (14, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py [(13, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py [(15, 'content', ['reviewed_sections']), (16, 'recognised_context', ['RecognisedContext', 'render_context'])]
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py [(15, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/profiles/ar_v3/v3_profile.py [(15, 'content', ['ProfileContentError', 'reviewed_content_sha256']), (19, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID']), (23, 'recognised_context', ['RecognisedContext'])]
  src/auditmanager/analysis/public.py [(55, 'recognised_context', ['RecognisedContext']), (81, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID', 'RecordedProfileError', 'resolve_recorded_profile'])]
  src/auditmanager/analysis/recognised/region_candidate.py [(22, 'recognised_context', ['RecognisedContextError', 'select_context'])]
  tests/integration/analysis/test_ar_v2_grounding_prep.py [(7, 'grounding', ['REASON_RECOGNISED_ONLY', 'resolve_v2_anchor']), (11, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v2_profile_content.py [(12, 'pkg', ['content'])]
  tests/integration/analysis/test_ar_v2_prompt_material.py [(9, 'content', ['REVIEWED_SOURCES']), (16, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v2_proposal_grounding.py [(8, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v2_recognised_context.py [(10, 'recognised_context', ['RecognisedContextError', 'render_context', 'select_context'])]
  tests/integration/analysis/test_ar_v2_recorded_artifact.py [(25, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID'])]
  tests/integration/analysis/test_ar_v2_recorded_call.py [(19, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID'])]
  tests/integration/analysis/test_ar_v2_recorded_input.py [(18, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID']), (19, 'recognised_context', ['RecognisedContextError'])]
  tests/integration/analysis/test_ar_v2_recorded_request.py [(12, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v2_recorded_response.py [(19, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID'])]
  tests/integration/analysis/test_ar_v2_registered_profile.py [(9, 'pkg', ['content'])]
  tests/integration/analysis/test_ar_v2_response_pipeline.py [(9, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v3_citation_grounding.py [(7, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v3_local_evaluation.py [(11, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v3_prompt_material.py [(11, 'content', ['reviewed_sections']), (13, 'recognised_context', ['RecognisedContext'])]
  tests/integration/analysis/test_ar_v3_request_candidate.py [(11, 'recognised_context', ['RecognisedContext'])]
  tests/integration/findings/test_v2_recorded_saved_plan.py [(13, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID'])]
  tests/integration/runs/test_recorded_v2_sources.py [(19, 'registered', ['PROFILE_ID', 'PROMPT_BUNDLE_ID'])]
  ```
- interpretation: 15 source files (5 under `ar_v3`, `recognised/region_candidate.py`, `analysis/public.py`, and 8 inside `ar_v2`, one of them `grounding.py` itself) and 18 test files import a moved name; no `tools/` or `scripts/` file does. `ar_v2/recorded_request.py` and `recorded_artifact.py` also read `registered.<callable>` by attribute (`resolve_recorded_profile`, `response_schema`), which stays. Tests that monkeypatch `registered.material_sha256` and `registered.reviewed_content_sha256` keep working because `registered` still imports both names.

### P-04 — files naming ar_v2 at the base commit

- captured_at: 2026-10-26
- command: `git grep -l "ar_v2" bfcb8a97 -- src tests web ':!web/node_modules' | sort | head -80`
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/ar_v2/grounding.py
  src/auditmanager/analysis/profiles/ar_v2/merge_input.py
  src/auditmanager/analysis/profiles/ar_v2/prompt_material.py
  src/auditmanager/analysis/profiles/ar_v2/proposal_grounding.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_call.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_input.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_request.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_response.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_stage_result.py
  src/auditmanager/analysis/profiles/ar_v2/registered.py
  src/auditmanager/analysis/profiles/ar_v2/response_pipeline.py
  src/auditmanager/analysis/profiles/ar_v2/response.py
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py
  src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py
  src/auditmanager/analysis/profiles/ar_v3/v3_profile.py
  src/auditmanager/analysis/public.py
  src/auditmanager/analysis/recognised/region_candidate.py
  src/auditmanager/executors/answers.py
  tests/contract/evaluation/test_bridge.py
  tests/contract/evaluation/test_matcher_core.py
  tests/contract/fixtures_seeded/test_ar_v2_seeded.py
  tests/integration/analysis/test_ar_v2_grounding_prep.py
  tests/integration/analysis/test_ar_v2_merge_input.py
  tests/integration/analysis/test_ar_v2_profile_content.py
  tests/integration/analysis/test_ar_v2_prompt_material.py
  tests/integration/analysis/test_ar_v2_proposal_grounding.py
  tests/integration/analysis/test_ar_v2_recognised_context.py
  tests/integration/analysis/test_ar_v2_recorded_artifact.py
  tests/integration/analysis/test_ar_v2_recorded_call.py
  tests/integration/analysis/test_ar_v2_recorded_input.py
  tests/integration/analysis/test_ar_v2_recorded_request.py
  tests/integration/analysis/test_ar_v2_recorded_response.py
  tests/integration/analysis/test_ar_v2_recorded_stage_result.py
  tests/integration/analysis/test_ar_v2_registered_profile.py
  tests/integration/analysis/test_ar_v2_response_parser.py
  tests/integration/analysis/test_ar_v2_response_pipeline.py
  tests/integration/analysis/test_ar_v2_response_schema.py
  tests/integration/analysis/test_ar_v3_citation_grounding.py
  tests/integration/analysis/test_ar_v3_local_evaluation.py
  tests/integration/analysis/test_ar_v3_prompt_material.py
  tests/integration/analysis/test_ar_v3_request_candidate.py
  tests/integration/analysis/test_ar_v3_response_schema.py
  tests/integration/evaluation/test_local_bundle.py
  tests/integration/evaluation/test_run_sources.py
  tests/integration/findings/test_analysis_public_boundary.py
  tests/integration/findings/test_merge_publication_plan.py
  tests/integration/findings/test_v2_publication_sql.py
  tests/integration/findings/test_v2_recorded_chain.py
  tests/integration/findings/test_v2_recorded_saved_plan.py
  tests/integration/runs/test_recorded_v2_sources.py
  tests/integration/runs/test_v2_recorded_durable_stage.py
  tests/integration/runs/test_v2_recorded_executor.py
  tests/integration/runs/test_v2_recorded_merge_stage.py
  tests/unit/executors/test_runner_answers.py
  ```
- interpretation: 57 files (the plan's "about 15 test files" is 18 that import a moved name; the others are v2-only tests that stay and fixtures named `ar_v2`).

### P-05 — the live journey is not a small edit (step 4)

- captured_at: 2026-10-26
- command: `grep -c -E '"AR"|section-choice=\\"AR|ar_baseline|ar_specification|АР\b|\bAR\b' <file>` for each file of `tests/e2e/pc01/**`, `tests/e2e/test_pc01_journey_conformance.py`, `docs/manual-tests/*.md`, `scripts/manual-alpha-check.sh` (counts below), and `sed -n 207,216p src/auditmanager/optimisation/project_match.py`
- captured_output:
  ```text
  59 tests/e2e/pc01/journey/manifest.json
  12 tests/e2e/test_pc01_journey_conformance.py
  10 tests/e2e/pc01/journey/README.md
  7 tests/e2e/pc01/driver.py
  7 docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
  4 tests/e2e/pc01/journey/fixtures/redden-write.manifest.json
  4 tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json
  3 tests/e2e/pc01/journey/journey.mjs
  3 scripts/manual-alpha-check.sh
  2 tests/e2e/pc01/test_acceptance.py
  2 tests/e2e/pc01/journey/fixtures/w28-live/w28-measure.manifest.json
  1 tests/e2e/pc01/test_live_text_analysis.py
  (manifest.json: 7490 lines, 109 write steps, four that press «Запустить прогон»: start-run, start-second-run, start-third-run, start-specification-run; all classify the set as АР)
  def _newest_published(reader: SavedTextReader, session: Session, version_uid: str) -> str | None:
      runs = tuple(reader.runs_newest_first(session, version_uid=version_uid))
      ...
      return next((run.run_id for run in runs if run.state == RUN_STATE_PUBLISHED), None)
  ```
- interpretation: not mechanical, and not verifiable without a browser and a stand; the step stops at the end of step 3 as the lane file prescribes. The reasons and the follow-up are in the report (`docs/program/PROD-10-AR-V2-EXTRACT-01.md`, "The journey: a scoped follow-up"). One finding there contradicts a sentence of `ADR-0024` section 2 and matters to `PROD-11`: АР optimisation and Form-7 read the saved text layer of the newest published run of the version.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/**`
- `src/auditmanager/analysis/profiles/ar_v3/**`
- `src/auditmanager/analysis/profiles/ar_shared/**`
- `src/auditmanager/analysis/recognised/**`
- `src/auditmanager/analysis/public.py`
- `tests/integration/analysis/**`
- `tests/integration/findings/test_v2_recorded_saved_plan.py`
- `tests/integration/runs/test_recorded_v2_sources.py`
- `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py`
- `docs/program/tasks/PROD-10-AR-V2-EXTRACT-01.md`
- `docs/program/PROD-10-AR-V2-EXTRACT-01.md`

## Forbidden hotspots

`contracts/**`, `db/**` and migrations, `infra/**`, the composition roots (`src/auditmanager/api/composition*`, `serve`, `worker`, `bootstrap/**`), `src/auditmanager/runs/executor.py`, every `profile.json` and `system_prompt.md`, `P02_LOCK.json`, `fixtures/recorded/**` (byte-identical), `web/**`, `tests/e2e/**`, root dependency/lock files, global styles, `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md`, `PRODUCTION-READINESS-PLAN-01.md`, `OWNER_RULINGS_*`, the ADRs, `origin/main`, tags and the deployment host.

## Non-goals

- No removal of АР v1 or v2, no contract reseal, no change to `analysis/public.py` beyond the two import statements: that is `PROD-11`.
- No move of the live journey, `tests/e2e/pc01/**` or the manual protocol (step 4 is a scoped follow-up in the report).
- No re-export shim left in `ar_v2` for a moved name.
- No change to a prompt, a hash, a recording or an identity value.

## Deliverables

- `src/auditmanager/analysis/profiles/ar_shared/` with `content.py`, `recognised_context.py`, `grounding.py` and the six `.md` files (moved with `git mv`), `v2_identities.py` (the two constants) and `__init__.py`.
- `ar_v2/registered.py` reads the constants from `v2_identities`; `resolve_recorded_profile` and everything else of v2 is unchanged.
- Importers updated: five `ar_v3` modules, `recognised/region_candidate.py`, seven `ar_v2` modules (and `grounding.py`, which moved), `analysis/public.py`, 18 test files.
- `tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py`: 13 cases (6 guards on the real tree, 7 that feed a mutated copy of the sources to a guard and expect a violation).
- The report `docs/program/PROD-10-AR-V2-EXTRACT-01.md`.

## Required tests

- command: `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_ar_v3_independent_of_ar_v2.py`
- expected: `13 passed`; and the mutation table of the report: every row red, green after restoring.
- command: `tests/integration/analysis/test_*.py`, `tests/unit/analysis`, `tests/unit/runs`, `tests/unit/executors`, `tests/contract/analysis_packages`, `tests/contract/architecture`, `tests/e2e/test_pc01_journey_conformance.py`
- expected: all green; the counts are in the report.
- command: `PYTHONPATH=src:$BS python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/PROD-10-AR-V2-EXTRACT-01.md',encoding='utf-8').read())))"`
- expected: `[]`

## Integration contract

The integrator can rely on: nothing under `ar_v3/` or `analysis/recognised/` imports `ar_v2` (grep and AST); `ar_v2` imports `ar_shared` where it needs the moved modules; `ar_v2.registered` no longer carries `PROFILE_ID` or `PROMPT_BUNDLE_ID` (a test holds that, so a shim cannot come back); every hash of the v2 and v3 profile objects and of the six data files is equal to the base. `PROD-11` deletes `ar_v2` and the v2 exports of `analysis/public.py`, then drops `_SINKS` from the guard test and tightens `test_only_the_named_sink_imports_ar_v2_from_outside_it` to an empty set.

## Failure/idempotency/security cases

A module of `ar_v3` or `recognised` that imports `ar_v2` directly, a chain `ar_v3` to `ar_shared` (or `analysis.text`) to `ar_v2`, a new importer of `ar_v2` outside `analysis.public`, a v2 export of `analysis.public` taken by a module of the closure, a re-created `ar_v2/content.py`, a `.md` file back in `ar_v2` and `registered.PROFILE_ID` re-bound each fail the guard. No security surface; no runtime code beyond import paths.

## Rollback / feature flag

Forward-revert (`git revert` of the commit moves the files back). No behaviour change, so no feature flag.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: the strict whole-repository closure of `ar_v3` still reaches `ar_v2` through `analysis.public` and `runs.executor` until `PROD-11`; the journey is not moved; tests that need PostgreSQL or S3 were not run
- integration notes: `tests/integration/runs/test_w59_section_profile_recorded.py` (9 cases, DATABASE_URL) and `tests/integration/analysis/geometry|recognised` (S3) must be run by the integrator on a stack
