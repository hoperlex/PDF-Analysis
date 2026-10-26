# Task BETA-PB-PROFILE-TRUTH-01 — beta UI evidence follows the served ПБ profile

task_id: BETA-PB-PROFILE-TRUTH-01

## Outcome

The analysis settings and language guard test the actual fifteen-profile registry: ПБ is a draft authored profile. A missing-profile response remains covered as an explicit synthetic refusal, not attributed to ПБ.

## Depends on

- `PB-PROFILE-01`
- `SECTION-RECORDINGS-01`
- `PB-PINS-01`
- `AR-V3-BETA-GROUP-REVIEW-SCREEN-01`

## Frozen inputs

- base commit: `d1487c75fb80a02689c1ce3f08570448591b3c40`
- shared contract: `1.4.0`; API 91 paths / 103 operations / 298 schemas
- migration head: `0032_ar_v3_run_group`
- active registry: 15 profiles, ПБ `draft`, `source: null`; no contract or registry change

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the beta UI test fixtures give ПБ no profile although the served registry carries a draft authored ПБ profile

### P-01 — stale test fixture

- captured_at: 2026-10-26
- command: `git grep -n -E 'ПБ with none|ПБ with no profile|code === .PB.|code !== .PB.|says ПБ has no profile' d1487c75fb80a02689c1ce3f08570448591b3c40 -- web/tests/unit/analysis-settings/analysis-settings.test.ts web/tests/guards/rendered-language.guard.test.ts; git grep -n -E '"section_code"|"status"|"source"' d1487c75fb80a02689c1ce3f08570448591b3c40 -- src/auditmanager/analysis/text/profiles/pb/profile.json; git grep -n -E 'AUTHORED_SECTIONS: Final' d1487c75fb80a02689c1ce3f08570448591b3c40 -- src/auditmanager/analysis/text/profile_registry.py`
- captured_output:
  ```text
  d1487c75fb80a02689c1ce3f08570448591b3c40:web/tests/guards/rendered-language.guard.test.ts:774:    executable: section.code !== 'PB',
  d1487c75fb80a02689c1ce3f08570448591b3c40:web/tests/guards/rendered-language.guard.test.ts:1072: * source, ПБ with no profile, every other section a draft ported from a Cyrillic-named
  d1487c75fb80a02689c1ce3f08570448591b3c40:web/tests/guards/rendered-language.guard.test.ts:1078:  if (code === 'PB') return { section_code: code, section_name: section.name, profile: null };
  d1487c75fb80a02689c1ce3f08570448591b3c40:web/tests/unit/analysis-settings/analysis-settings.test.ts:7: * a reviewed profile, and ПБ with none.
  d1487c75fb80a02689c1ce3f08570448591b3c40:web/tests/unit/analysis-settings/analysis-settings.test.ts:36:  if (code === 'PB') return { section_code: code, section_name: section.name, profile: null };
  d1487c75fb80a02689c1ce3f08570448591b3c40:web/tests/unit/analysis-settings/analysis-settings.test.ts:100:  it('says ПБ has no profile, and what follows from it, without inventing one', () => {
  d1487c75fb80a02689c1ce3f08570448591b3c40:src/auditmanager/analysis/text/profiles/pb/profile.json:3:  "section_code": "PB",
  d1487c75fb80a02689c1ce3f08570448591b3c40:src/auditmanager/analysis/text/profiles/pb/profile.json:7:  "status": "draft",
  d1487c75fb80a02689c1ce3f08570448591b3c40:src/auditmanager/analysis/text/profiles/pb/profile.json:9:  "source": null
  d1487c75fb80a02689c1ce3f08570448591b3c40:src/auditmanager/analysis/text/profile_registry.py:102:AUTHORED_SECTIONS: Final[frozenset[str]] = frozenset({"PB"})
  ```
- interpretation: Re-captured on 2026-10-26 from base commit d1487c75fb80a02689c1ce3f08570448591b3c40 with git grep against that tree (not at dispatch time). At the base, rendered-language.guard.test.ts:1078 and analysis-settings.test.ts:36 return profile: null for code 'PB'; the guard marks executable: section.code !== 'PB' (774); comments and a test title at guard:1072, analysis-settings.test.ts:7 and :100 describe ПБ as having no profile. The served registry side: profiles/pb/profile.json has section_code PB (3), status draft (7) and source null (9), and profile_registry.py:102 puts PB in AUTHORED_SECTIONS. The fixtures therefore contradict the served registry at the base. Not shown: the registry's fifteen-profile count (stated in the task's Frozen inputs). Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'ПБ with none|ПБ with no profile|code === .PB.|code !== .PB.|says ПБ has no profile' web/tests/unit/analysis-settings/analysis-settings.test.ts web/tests/guards/rendered-language.guard.test.ts`; captured_output was a prose summary: the analysis-settings fixture returned `profile: null` for `PB`; the rendered-language guard returned `profile: null` and `executable: false` for `PB`. Original interpretation: test-only fixtures contradict the served registry and can give a false green for beta screen prose.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/tests/unit/analysis-settings/analysis-settings.test.ts`
- `web/tests/unit/sections/classification-panel.test.ts`
- `web/tests/unit/sections/classification-correction.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/node_modules`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/BETA-PB-PROFILE-TRUTH-01.md`
- `docs/program/BETA-PB-PROFILE-TRUTH-01.md`

## Forbidden hotspots

- `contracts/**`, migration head, root dependencies/locks, composition root, global styles, generated API, served registry/profile and normative pack
- `origin/main`, tags, deployment host

## Non-goals

- No change to `ProjectSection.analysed`: it is a legacy AR-only marker; executability is server supplied.
- No expert approval of the draft ПБ profile or acceptance of its synthetic recording.
- No new API, screen, provider call or normative conclusion.

## Deliverables

- Correct fifteen-profile screen and language fixtures; retain explicit synthetic no-profile states.
- Current-state sentence synchronized with the served registry.
- A result note with test evidence and limits.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run tests/unit/analysis-settings/analysis-settings.test.ts tests/unit/sections/classification-panel.test.ts tests/unit/sections/classification-correction.test.ts tests/guards/rendered-language.guard.test.ts`
- `git diff --check`
- `web/node_modules` may be a temporary ignored symlink to the existing gate worktree installation only after byte-comparing `web/package.json` and `web/package-lock.json`; remove it after the checks. No dependency or lock file changes.
- When dependencies remain unavailable, parse modified TypeScript and check fixture invariants directly; report unrun rendered tests.
- Full `make gate` remains at the final beta candidate under `R-135`.

## Integration contract

The normal fixture matches the served catalogue: all fifteen sections have a profile and are executable. A synthetic registry missing ГП remains the explicit no-profile refusal case. ПБ's authored `source: null` and `draft` status remain visible to rendered UI tests. No production behavior changes; development publication is `origin/dev` only.

## Failure/idempotency/security cases

- The no-profile branch remains asserted with a fabricated missing ГП entry.
- No durable state or side effect; a replay of tests is idempotent.

## Rollback / feature flag

Revert this test/document slice; no flag or migration.

## Handoff

- changed files: result note
- checks/results: result note
- known limits: no installed frontend dependencies in this checkout
- integration notes: rerun rendered suites in the full beta gate
