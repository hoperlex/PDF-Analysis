# Task PROD-14-0-EXPECTATIONS-01 — the section status and version pins are read from one file

task_id: PROD-14-0-EXPECTATIONS-01
status: completed in development candidate

## Outcome

Four shared test files pinned `draft` and `1.0.0` for the section profile packages, so every section lane of `PROD-14` (`R-146l`, `R-146v`) would have turned red on files it does not own. They now read one file with one line per package, `tests/unit/analysis/text_profiles/section_profile_expectations.json`, and a section lane that moves its profile out of `draft` changes its own `profile.json` and that one line. No product behaviour changes: no `src/**` file is edited and every package stays `draft` at `1.0.0`.

## Depends on

- `PRODUCTION-READINESS-PLAN-01` — completed; item `PROD-14.0` is this task.
- `W59-SECTION-PROFILES-01`, `PB-PROFILE-01` — completed; they created the fourteen packages the file lists.

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.5.0`, unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged
- base commit: `749e2efcb22bba53e38ae45801adced3c65bccc4` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No package is added or removed. The new file enumerates the existing fourteen packages' status and version, and its totality against `profiles/*/profile.json` is held by `test_section_profile_expectations.py` (see Deliverables).

## Captured premise evidence

- premise: four named test files hard-code `draft` / `1.0.0` for the section packages, and all fourteen `profile.json` files declare exactly that; the plan was written from reads and is re-verified here

### P-01 — the pins in the four shared test files

- captured_at: 2026-10-26
- command: `rg -n "draft|profile_version|1\.0\.0" tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles/test_text_profile_packages.py tests/integration/composition/test_analysis_profiles_over_http.py web/tests/unit/analysis-settings/analysis-settings.test.ts`
- captured_output:
  ```text
  tests/unit/analysis/test_text_profile_registry.py:42:        "profile_version": "1.0.0",
  tests/unit/analysis/test_text_profile_registry.py:43:        "status": "draft",
  tests/unit/analysis/test_text_profile_registry.py:92:    assert entry.status == "draft" and entry.package == "kj"
  tests/unit/analysis/test_text_profile_registry.py:126:        ("kj", _profile("KJ", profile_version="1.0"), "profile_version_invalid"),
  tests/unit/analysis/test_text_profile_registry.py:184:        assert entry.package == code.lower() and entry.status in {"draft", "reviewed"}
  tests/unit/analysis/test_text_profile_registry.py:195:    assert entry.status == "draft", "no expert review exists: the status says so"
  tests/unit/analysis/test_text_profile_registry.py:248:    assert entry.source is None and entry.status == "draft" and entry.package == "pb"
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:15:* every profile is ``draft``; each legacy profile's source files are hash-pinned, both
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:55:        "profile_version",
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:173:        assert manifest["profile_version"] == "1.0.0", code
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:174:        assert manifest["status"] == "draft", code
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:189:def test_the_authored_profile_declares_no_source_and_is_a_draft() -> None:
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:196:    assert manifest["profile_version"] == "1.0.0"
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:197:    assert manifest["status"] == "draft"
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:323:    # Honest about what the profile is: a draft without expert review, evidence or recordings.
  tests/unit/analysis/text_profiles/test_text_profile_packages.py:324:    assert "`draft`" in text and "D-178" in text
  tests/integration/composition/test_analysis_profiles_over_http.py:10:  ``draft`` with the source its ``profile.json`` declares; ``PB`` (`PB-PROFILE-01`) is the
  tests/integration/composition/test_analysis_profiles_over_http.py:90:        assert profile["profile_version"] == entry.profile.profile_version
  tests/integration/composition/test_analysis_profiles_over_http.py:98:        assert profile["status"] == "draft"
  tests/integration/composition/test_analysis_profiles_over_http.py:105:    assert pb["status"] == "draft", "no expert review exists for the authored profile"
  web/tests/unit/analysis-settings/analysis-settings.test.ts:6: * The fixture is the shape `listAnalysisProfiles` answers — AR builtin with no source, a draft,
  web/tests/unit/analysis-settings/analysis-settings.test.ts:7: * a reviewed profile, and ПБ as an authored draft. A missing profile is tested separately.
  web/tests/unit/analysis-settings/analysis-settings.test.ts:43:      profile_version: code === 'TX' ? '1.2.0' : '1.0.0',
  web/tests/unit/analysis-settings/analysis-settings.test.ts:44:      status: code === 'AR' ? 'builtin' : code === 'POS' ? 'reviewed' : 'draft',
  web/tests/unit/analysis-settings/analysis-settings.test.ts:92:  it('marks a draft as needing an expert review, in words', () => {
  web/tests/unit/analysis-settings/analysis-settings.test.ts:95:    expect(ps).toContain('data-profile="draft"');
  web/tests/unit/analysis-settings/analysis-settings.test.ts:96:    expect(ps).toContain('версия 1.0.0');
  web/tests/unit/analysis-settings/analysis-settings.test.ts:99:  it('shows the authored ПБ draft and its required expert review', () => {
  web/tests/unit/analysis-settings/analysis-settings.test.ts:101:    expect(pb).toContain('data-profile="draft"');
  web/tests/unit/analysis-settings/analysis-settings.test.ts:104:    expect(pb).toContain('версия 1.0.0');
  web/tests/unit/analysis-settings/analysis-settings.test.ts:152:    expect(Object.keys(ANALYSIS_PROFILE_STATUS_LABELS).sort()).toEqual(['builtin', 'draft', 'reviewed']);
  web/tests/unit/analysis-settings/analysis-settings.test.ts:153:    expect(analysisProfileStatusLabel('draft')).toBe('черновик, требует экспертной проверки');
  ```
- interpretation: the output is the command run, unedited, over the four files as they are at the base commit (extracted with `git archive 749e2efc` into an empty directory, because the lane had edited them by the time this record was written). All four files exist and pin as the plan says (its "lines 173-174 and 197" are confirmed). Three things the plan did not name: `test_text_profile_packages.py:324` asserts the literal ``draft`` in `pb/open_questions.md`; the web fixture at `analysis-settings.test.ts:43-44` bakes `TX` at `1.2.0` and `POS` as `reviewed` into the base rows (synthetic variants that the wording cases rely on); and the synthetic-package literals (`test_text_profile_registry.py:42-43`, `:92`, `:248`, which build a package in a temporary directory) are not pins on the real tree and stay.

### P-02 — every package declares `draft` at `1.0.0`

- captured_at: 2026-10-26
- command: `python3 -I -c "import json,glob;print(sorted((f.split('/')[-2],json.load(open(f))['status'],json.load(open(f)).get('profile_version')) for f in glob.glob('src/auditmanager/analysis/text/profiles/*/profile.json')))"`
- captured_output:
  ```text
  [('ai', 'draft', '1.0.0'), ('eom', 'draft', '1.0.0'), ('gp', 'draft', '1.0.0'), ('itp', 'draft', '1.0.0'), ('kj', 'draft', '1.0.0'), ('km', 'draft', '1.0.0'), ('ov', 'draft', '1.0.0'), ('pb', 'draft', '1.0.0'), ('pos', 'draft', '1.0.0'), ('ps', 'draft', '1.0.0'), ('pt', 'draft', '1.0.0'), ('ss', 'draft', '1.0.0'), ('tx', 'draft', '1.0.0'), ('vk', 'draft', '1.0.0')]
  ```
- interpretation: fourteen packages (thirteen legacy sections and PB), all `draft` at `1.0.0`, so a file recording exactly that is correct on this tree. AR has no package and no line.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/unit/analysis/test_text_profile_registry.py`
- `tests/unit/analysis/text_profiles/test_text_profile_packages.py`
- `tests/unit/analysis/text_profiles/section_profile_expectations.json`
- `tests/unit/analysis/text_profiles/test_section_profile_expectations.py`
- `tests/integration/composition/test_analysis_profiles_over_http.py`
- `web/tests/unit/analysis-settings/analysis-settings.test.ts`
- `docs/program/tasks/PROD-14-0-EXPECTATIONS-01.md`
- `docs/program/PROD-14-0-EXPECTATIONS-01.md`

## Forbidden hotspots

`src/**`, `contracts/**`, `db/**`, `infra/**`, every `profile.json` and `system_prompt.md`, `fixtures/recorded/**`, `P02_LOCK.json`, root dependency/lock files, `web/FRONTEND_LOCK.json`, the composition root, global styles, `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md`, `PRODUCTION-READINESS-PLAN-01.md`, `origin/main`, tags and the deployment host.

## Non-goals

- No change of any section's status or version: every line records `draft` / `1.0.0`.
- No change to the registry, the loader, the contract or any rendering code.
- No edit of `fixtures/recorded/sections/**` (their `origin.profile_status` is informational and is rebuilt by each section lane).
- No removal of `builtin` from the web test: that is `PROD-11`, which merges after this task.

## Deliverables

- `tests/unit/analysis/text_profiles/section_profile_expectations.json`: format `section-profile-expectations/1`, one physical line per non-AR package (`code`, `status`, `profile_version`) in the registry's order `AI, PS, POS, TX, KJ, KM, OV, VK, PT, EOM, SS, ITP, GP, PB`.
- `tests/unit/analysis/text_profiles/test_section_profile_expectations.py`: five cases that hold the file itself (format and key set, one line per section, vocabulary, order and no AR line, a line for every package and a package for every line, every line equal to its `profile.json`).
- The four shared tests read the file: `test_text_profile_registry.py`, `test_text_profile_packages.py`, `test_analysis_profiles_over_http.py` (a read of the file next to the registry) and `analysis-settings.test.ts` (a read of the file and of every `profile.json`, with the wording cases moved onto synthetic variants of one row).
- Report `docs/program/PROD-14-0-EXPECTATIONS-01.md`: the before/after reading of each assertion, the mutation table and the instruction for a section lane.

## Required tests

- `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles/test_text_profile_packages.py tests/unit/analysis/text_profiles/test_section_profile_expectations.py` — expected: 50 passed.
- `tests/integration/composition/test_analysis_profiles_over_http.py` with the lane `.env` exported — expected: 4 passed.
- `npx vitest run tests/unit/analysis-settings` in `web/`, `npx tsc --noEmit`, `npx eslint tests/unit/analysis-settings/analysis-settings.test.ts` — expected: 95 passed, exit 0, exit 0.
- `tests/integration/sections/test_section_recordings.py` — expected: 109 passed; `tests/contract/program` — expected: as on the base; `git diff --check` — expected: exit 0.
- `PYTHONPATH=src:$BS python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/PROD-14-0-EXPECTATIONS-01.md',encoding='utf-8').read())))"` — expected: `[]`.
- Mutations: for each of the five test files, change one expectation (a status, a version), delete a line and add a line without a package; each goes red naming the section, and green after the file is restored. The table is in the report.

## Integration contract

The integrator can rely on: the file `tests/unit/analysis/text_profiles/section_profile_expectations.json` is the single place a status or version of a section package is asserted; four test files plus the guard fail when it and any `profile.json` disagree, when a package has no line and when a line has no package. A section lane edits its own `profile.json` and its own line (a one-line diff); lines of different sections never touch the same hunk, so section lanes merge without conflict in these files. `PROD-11` rebases onto this task before it edits `analysis-settings.test.ts`.

## Failure/idempotency/security cases

A status other than `draft`/`reviewed`, a version that is not three numeric parts, a duplicate or reordered line, an AR line, two sections on one physical line and a changed format string each fail the guard. A missing line makes the web test fail at load with `expectations file: no line for <CODE>` (no silent default). No security surface; no runtime code.

## Rollback / feature flag

Forward-revert. No behaviour change, so no feature flag.

## Handoff

- changed files: the four shared tests, the expectations file, its guard test, this task file and the report
- commands/results: see the report
- known limits: see the report (the `pb/open_questions.md` text pin, the e2e journey manifest selector `tr[data-profile="draft"]`, the informational `profile_status` in recorded fixtures)
- integration notes: merge before any `PROD-14.<code>` section lane and before `PROD-11`
