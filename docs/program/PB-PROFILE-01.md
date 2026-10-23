# PB-PROFILE-01 — the fire-safety (ПБ) section has a draft text profile and runs instead of being refused

Task: `docs/program/tasks/PB-PROFILE-01.md`. Branch `agent/lane-b-01`, base `ffdc32d1` (`origin/dev`);
slice 2 of lane B, after `MODEL-IDENTITY-CHECK-01`. Container-free (`R-126`): no stand, no database
suite, no model call, no recording.

## Result

A version confirmed in section `PB` is routed by `start_audit_run` / `reaudit_run` to its own profile
(`status: draft`, the fifteenth) instead of `section_profile_unavailable`. Another section never gets
the PB profile and PB never gets another section's: the registry holds fifteen distinct identity pairs and
`route_classified_version` refuses a missing entry exactly as before, with no AR fallback.
`listAnalysisProfiles` lists fifteen profiles; PB's carries `source: null`, which the frozen
`AnalysisProfileSummary.source` already allowed (AR has none either).

**This is a draft, not a reviewed profile.** No expert has reviewed it (`D-178` stays open), no field case
or recorded response exists for it, and it must not count towards beta acceptance. Its open questions are
in the package.

## What changed

| File | Change |
| --- | --- |
| `src/auditmanager/analysis/text/profile_registry.py` | the loader accepts a profile authored for this product: `AUTHORED_SECTIONS = {"PB"}`; for those sections `"source": null` is accepted and required (the key set is unchanged, so a missing key still refuses), and the package carries a third file, `open_questions.md`, required non-blank; every other section still needs a legacy `source` and no questions file |
| `src/auditmanager/analysis/text/profiles/pb/profile.json` | new: `PB`, `draft`, `1.0.0`, `title_ru` «Пожарная безопасность» (the catalogue's name), `source: null`, fresh `ap_01M5G4NZVKNZJYH722M0SXXP3X` and `pb_01M5G4NZVKHM9GP4EH22JACW2X` (`AnalysisProfileId.new()`, `PromptBundleId.new()`, neither present anywhere else in `src`) |
| `src/auditmanager/analysis/text/profiles/pb/system_prompt.md` | new, see below |
| `src/auditmanager/analysis/text/profiles/pb/open_questions.md` | new: eleven numbered questions for the expert, plus a pointer to the four cross-section questions of `W59-SECTION-PROFILES-01.md` |
| `tests/unit/analysis/test_text_profile_registry.py` | the real-tree test no longer pins "PB has no profile"; fifteen-section, PB-identity and authored-package cases added |
| `tests/unit/analysis/text_profiles/test_text_profile_packages.py` | thirteen legacy packages plus one authored (`AUTHORED_SECTIONS`); AR alone has none; PB-specific cases for the prompt and the questions |
| `tests/integration/sections/test_routing.py`, `test_staged_routing.py` | the "section with no profile" cases keep their synthetic table without PB; PB routes to its own profile and others never inherit it |
| `tests/integration/composition/test_analysis_profiles_over_http.py` | no `profile: null` row remains; fifteen entries; PB `draft` with `source: null` (database-backed, not run) |
| `tests/integration/runs/test_w59_section_profile_recorded.py` | the refusal is shown on `WITHOUT_PB`, a registry built without the PB entry; a PB version starts a run pinned to the PB pair; a KJ version never gets it (database-backed, not run) |

No contract, migration, `bootstrap/**`, `web/**` or the thirteen existing profiles changed.

## How the PB prompt is built

There is no legacy material for PB, so the prompt is v1's served `SYSTEM_PROMPT` with the same six anchored
substitutions the thirteen ported prompts use (each anchor occurs exactly once in v1; the unit test holds
the unchanged parts byte for byte): the opening names «Пожарная безопасность» (ПБ); a «Где в документе
раздела ПБ искать…» hint block; the object kinds of condition 1; near-miss pairs for condition 2;
«спецификацию, лист» in condition 4; the exclusion sentence. The question, the two categories and the whole
output contract are v1's.

The hint block lists places to cross-check, never requirements. It has one bullet for each area the task
names, plus the building's general figures, premises categories, the alarm and extinguishing systems and the
placeholder places:

| Area | Bullet compares, for the same object |
| --- | --- |
| general | fire-resistance degree, constructional and functional hazard classes, storeys and height of one building, section or compartment |
| fire resistance | fire-resistance limit and hazard class of one structure, in the note, the structures table and the plans |
| fire compartments | boundaries, area and storeys of one compartment; type, limit and place of its barriers, doors, hatches, vestibules, dampers |
| evacuation | number, clear width and place of exits, width and length of routes, people, stair types |
| fire-fighting access | width of the access road, distance to the wall, entrances, hydrants and apparatus areas |
| smoke control | designation, purpose, protected zones, capacity, fans, opening area and damper types of one system |

**No invented requirement.** The prompt carries no clause number, no limit and no class threshold: the only
numerals outside the five numbered conditions are `123` and `13130`, in the sentence that names what the
model must **not** check against («Федеральному закону № 123-ФЗ и сводам правил серии 13130»). Both are
corpus documents named in this repository (`docs/program/dispatch/W57-PLAN.md` lines 52–54 and 87,
`W57A-CORPUS-SOURCE-PREP-01.md`). The norms corpus itself (`.local/norms/corpus/MANIFEST.json`) is not
visible from a lane worktree and was **not read**; the choice rests on those two tracked documents. `СП 2.13130`
and `СП 4.13130` are deliberately not named: `W57-PLAN.md` records them as absent from the corpus
(`W54-LOCAL-IMPORT-01.md:120` shows a search hit titled «Приказ МЧС России № 288 (СП 4.13130)» in the local
import, which does not agree with that statement; not resolved here, and the prompt is safe either way
because it names neither). A test fails on any other numeral, on a second norm identifier and on a missing
one.

## Decisions taken

1. **How a package declares "no legacy source".** `"source": null` in `profile.json`, with the key set
   unchanged. Declaration is also in code: `AUTHORED_SECTIONS` names the sections, and a package cannot
   declare itself authored. The equivalence is two-way: an authored section with a source, a legacy section
   with `source: null`, an authored package without questions and a legacy package with a questions file
   all refuse the whole load. Reason: a legacy section silently losing its provenance, or PB claiming a
   legacy repository it does not have, must fail, not load.
2. **Open questions live in the package**, as `open_questions.md`, required for an authored package. The
   task says "listed in the package"; a fourth file next to the prompt cannot reach the model (the loader
   reads `system_prompt.md` only) and is a structural requirement instead of a convention.
3. **`status: draft`**, like the other thirteen; `reviewed` stays loadable but nothing here claims it.
4. **Authored-section seam for tests.** Where a test used PB as "a section without a profile", it now uses a
   table built without PB (`TextProfileRegistry(...)` filtered, or a literal mapping), so the refusal is
   exercised exactly as before and not weakened.
5. **Two points of vocabulary the expert may overturn** (listed as questions): a derived `REI`/`EI` mismatch
   for one structure is left to the expert (question 3); a result value such as an evacuation time written in
   the text is compared as a value and never recomputed (question 9).

## Outside the allowed paths: pins that go red when PB gets a profile

Found by grep and by running what runs without containers; **not edited** (not in the allowed list):

| Where | Pin | Runnable here? | Fix |
| --- | --- | --- | --- |
| `tests/integration/sections/test_section_recordings.py::test_the_registry_keeps_each_packages_source_block` | reads `declared["source"]["repository"]` for every non-AR package; PB's source is `null` (`TypeError`) | yes: 16 passed, 1 failed at this tip | `SECTION-RECORDINGS-01` owns the file; lane B fixes it in slice 3 (`source` is `None` for PB) |
| `tests/integration/runs/test_w59_section_routing_over_http.py` lines 8, 22, 365–369 (`assert "PB" not in executable`), 412–416 (`test_a_section_without_a_profile_is_refused_without_an_ar_fallback` starts a PB version and expects `section_profile_unavailable`) | PB as the unprofiled section | no (database) | use a table without PB for the refusal; `PB in executable` |
| `tests/integration/composition/test_the_served_application_routes_by_section.py:114` | `assert "PB" not in kwargs["section_profiles"]` | no (database) | `"PB" in` |
| `web/src/entities/project/model/section.ts:111` (`analysed: false` for PB), `web/tests/unit/styles/screens.ts:202,214,665,1070`, `web/tests/unit/sections/classification-correction.test.ts:282`, `web/tests/unit/sections/classification-panel.test.ts:120` | the UI treats PB as having no analysis profile | `web/**` is forbidden and `npm` is out of this lane | the integrator's frontend slice |
| stale prose only: `src/auditmanager/api/routers/analysis_profiles.py:8` ("`PB` today"), `src/auditmanager/analysis/profiles/section_candidates/metadata.py:5` | comments | n/a | next touch of those files |

`tests/integration/analysis/test_section_profile_candidates.py` and the candidate metadata are unaffected: they
describe the fourteen legacy candidates, and PB is still not one.

## Commands and exit statuses

From `/root/projects/PDF-Analysis/.local/worktrees/lane-b`, shared venv interpreter, `nice -n 10`,
`-c pyproject.toml --rootdir=. -q -p no:cacheprovider`, status read from pytest's own `$?`. A plugin printed
`IMPORTED ... FROM <worktree>/src/...` and `PACKAGES_ROOT <worktree>/src/...` at session start.

| Command (files) | Before (base `ffdc32d1`, a `git archive` copy) | After |
| --- | --- | --- |
| `tests/unit/analysis` (`test_text_profile_registry.py`, `text_profiles`) with `tests/integration/sections/test_routing.py test_staged_routing.py` | rc 0, 52 passed | rc 0, 73 passed |
| the new and updated tests run against the **base** `src` (`-o pythonpath=<base>/src`) | | rc 2, collection error: `cannot import name 'AUTHORED_SECTIONS'` |
| the base loader over the new PB package | | refuses: `package_files_invalid: pb: ['open_questions.md', 'profile.json', 'system_prompt.md']` |
| slice 1 files, rerun on this tip (`test_model_identity`, `test_proxy_adapter`, `test_w53c_proxy_answer_shapes`, `test_provider_modes`, `test_proxy_truncation_reaches_partial`) | | rc 0, 188 passed |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, `tests/integration/runs/test_w59_section_profile_recorded.py` | | `python -m py_compile` ok; `--collect-only` rc 0, 13 tests collected |
| `tests/integration/sections/test_section_recordings.py` (outside the allowed paths, run only) | against the base `src` (`-o pythonpath=<base>/src`): the source-block test passes; the one failure there, `test_the_served_adapter_answers_ar_exactly_as_the_canonical_directory`, is an artefact of the copy (a `src` copy resolves `fixtures/` through its own location) | rc 1, 16 passed, 1 failed: the source-block test above |
| `git diff --check` | | rc 0 |

The routing seam of the two database-backed files was also exercised once without a database by a throw-away
script (not committed): `route_classified_version` over the real registry routes a PB version to PB's
pair and a KJ version to KJ's, and over a registry without PB refuses with `section_profile_unavailable`.

## Mutation probes

Two kinds, because a copy of `src/` is not what the file-reading tests see. **Copy**: `.local/mut-b1/src`
(`-o pythonpath=<copy>/src`; the plugin line proved the copy and its `PACKAGES_ROOT` were imported; the
unmutated copy passed 73 of 73). **In place**: the tests of `text_profiles` read the prompt and manifest
through the repository root of the test file, so a mutated copy never reaches them (the first run of these
mutations passed for that reason and was discarded); each in-place mutation backed the file up, restored it
and proved the restore by a byte comparison (`restored=True` every time).

| Guard | Mutation | Result |
| --- | --- | --- |
| a registry without the PB entry reddens the new test | the copy's `profiles/pb` moved away | 2 failed (`..._fifteen_sections_pb_included`, `test_pb_never_shares_an_identity...`) |
| the foreign-section refusal still holds | `routing.py`: a missing profile falls back to the AR profile | 4 failed (PB, PS and AI cases) |
| authored set | `AUTHORED_SECTIONS` empty | 8 failed |
| authored set | gains `KJ` | 18 failed |
| questions required | the missing-questions check removed | 1 failed |
| questions non-blank | the blank check removed | 1 failed |
| authored may not carry a source | the check removed | 1 failed |
| legacy may not carry questions | the check removed | 1 failed |
| legacy needs its source | `source: null` accepted for a legacy section | 1 failed |
| file set | loader reverted to the two-file set | 7 failed |
| file set | any superset of the two files accepted | 2 failed |
| PB status | `reviewed` | 1 failed |
| source declared | the `source` key dropped from `profile.json` | 3 failed |
| identity | PB reuses PT's profile id | 3 failed |
| title | PB's title changed | 1 failed |
| prompt names its section | PB's opening names АР | 1 failed |
| each named area is present | each of the five hint bullets removed in turn (evacuation, fire resistance, fire compartments, access, smoke control) | 1 failed each |
| each area is present once | the access bullet's phrase duplicated | 1 failed |
| no invented number | «не менее 1,2 м» inserted | 1 failed |
| norms named | `СП 2.13130.2020` instead of the series | 1 failed |
| norms named | the 123-ФЗ named dropped | 1 failed |
| v1 contract kept | a third category word added | 1 failed |
| v1 contract kept | one line of the output contract removed | 1 failed |
| prompt file shape | a trailing blank line | 1 failed |
| questions numbered | the number of question 8 stripped, leaving a gap | 1 failed |
| questions numbered | question 6 renumbered 7 | 1 failed |
| honest status | `D-178` removed from the questions | 1 failed |
| honest status | `draft` removed from the questions | 1 failed |

Honest account of one weakness found by this: the first version of the area test used single words
(`проезд`, `противодымной`) that also occur in other bullets, so four mutations survived. The
markers are now one phrase unique to each bullet, matched after whitespace normalisation and counted exactly
once; the mutations above were rerun against them.

## Not exercised

- No database suite and no composition build: `test_analysis_profiles_over_http.py` and
  `test_w59_section_profile_recorded.py` were written and compiled and collected, not run; the three outside
  database tests named above will fail on this tip until they are updated.
- No recorded response and no model call for PB: that is `SECTION-RECORDINGS-01`. The PB profile has never
  produced an observation, so its prompt quality is unknown.
- `npm`, the web suite and the live journey (`web/**` is forbidden here and `R-135` forbids the rest).
- The norms corpus manifest was not read (see above).
- No `tests/contract` battery (once, at the end of slice 3).

## Risks

- A draft prompt written without a reference corpus: its hint list is plausible for the section, not
  validated. It may produce false findings on abbreviations and on mixed-use buildings (questions 4 and 11).
- PB becomes executable the moment this merges. A classified PB version now starts a run that, in recorded
  mode, ends `failed` with `recording_missing` until `SECTION-RECORDINGS-01` merges, and in proxy or live mode
  goes to the model with a draft prompt. The web still presents PB as unavailable (`analysed: false`).
- Debt: one row for the draft authored profile (no expert review, no evidence, no recording), joining the
  thirteen of `W59-SECTION-PROFILES-01`.

## Instruction for the integrator

Merge `PB-PROFILE-01` and `SECTION-RECORDINGS-01` together or in that order; the source-block test of the
latter's file is fixed there. Register: the draft-profile debt row; the three outside database pins and the
web pins in the table above; the stale prose. Light acceptance: `git diff --check`, the named test files,
`tests/contract` with the three ignores. Before any real PB run: answer `open_questions.md`.
