# Task HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030 — serve the original AR profile on dev

## Outcome

A version confirmed as АР can start the ordinary single-Run text analysis with a new immutable profile whose source material is copied verbatim from the current `PDF-proverka` АР profile. The default AR start control uses that route; the previous AR v3 solution remains on `ready/ar-v3-20261030` and old v3 Runs remain readable.

## Depends on

- `HOTFIX-AR-V3-SNAPSHOT-INT-20261030` (completed; remote branch verified at `99b337fb`).

## Frozen inputs

- Domain/API/analysis/events shared contract: `1.12.0` at base; this task owns the contract reseal required for the changed AR routing promise.
- API surface: 131 paths / 148 operations / 432 schemas at base.
- Migration head: `0039_comparison_core`, unchanged.
- Base commit: `99b337fb6e632ebd585f53134eb4425131cfe0b7` (`origin/dev`).
- Original source: `SU10KAZ/PDF-proverka` `main` at `3c99481719218b9cfa7560886529916646c61939`, checked in a clean `/tmp/pdf-proverka-original` clone because `/root/projects/PDF-proverka` is absent here. The AR `role.md` and `checklist.md` hashes still equal the previously frozen source hashes in `W56A-LEGACY-SOURCE-01.md`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/text/profile_registry.py`
- enumerator_owner: `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`
- totality_query: `PYTHONPATH=src python -c 'from auditmanager.analysis.text.profile_registry import load_text_profile_registry, SECTION_CODES; r=load_text_profile_registry(); print(sorted(r.entries)); print(set(r.entries)==SECTION_CODES)'`

## Captured premise evidence

- premise: at base `profile_registry.py` refuses an `AR` package and `startRun` therefore answers `section_profile_unavailable`; `web/src/widgets/run-list/ui/run-list.tsx` shows only the six-check group for АР. The original AR profile has `config.json`, eight Markdown resources, and a generic multi-stage pipeline whose stage templates are outside this profile-only hotfix.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`, by the owner's direct request to rewrite АР in dev.
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/HOTFIX-AR-V3-SNAPSHOT-INT-20261030.md`
- `docs/program/tasks/HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030.md`
- `docs/program/CURRENT_STATE.md`
- `src/auditmanager/analysis/text/profile_registry.py`
- `src/auditmanager/analysis/text/prompt.py`
- `src/auditmanager/analysis/text/profiles/ar/**`
- `src/auditmanager/analysis/text/ar_original_source/**`
- `tests/unit/analysis/**`
- `tests/unit/runs/test_section_relaxed_limits.py`
- `tests/integration/sections/**`
- `tests/integration/composition/test_comparison_stub_operations.py`
- `contracts/api/v1/**`
- `contracts/analysis/**`
- `contracts/domain/v1/**`
- `contracts/events/v1/**`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/analysis/engine/result.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `tests/support/expected_facts.json`
- `tests/contract/api_v1/**`
- `web/FRONTEND_LOCK.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/**`
- `web/src/entities/analysis-profile/**`
- `web/src/entities/project/model/section.ts`
- `web/src/features/classify-version/ui/classify-version-form.tsx`
- `web/src/widgets/analysis-profile-table/ui/analysis-profile-table.tsx`
- `web/src/widgets/run-list/ui/run-list.tsx`
- `web/src/widgets/version-classification/ui/version-classification.tsx`
- `web/tests/**`

## Forbidden hotspots

- `db/migrations/**`, root dependency/lock files, composition root and global styles.
- AR v3 group/worker, existing source profiles of other sections, comparison evidence and `origin/main`.

## Non-goals

- Porting the original app's block-analysis, findings-merge, norms and Excel stages, which the owner excluded by choosing profile and prompts only.
- Treating the original checklist's numerical norm statements as verified legal evidence or an expert verdict.
- Deleting the v3 API or historical v3 Runs, making a release tag, deploying, or running a full gate/live provider call.

## Deliverables

- Verbatim original AR source resources and SHA-checked provenance; a new `AR` text-profile package and immutable pair; focused tests.
- Ordinary AR start UI and updated profile/classification descriptions; coherent contract/client reseal and current-state record.
- One fast-forward dev commit after basic checks.

## Required tests

- Focused registry/prompt/routing and web start/profile tests pass.
- `npm --prefix web run api:verify`, typecheck and targeted lint pass.
- Contract seal and doc prose facts, `git diff --check`, pin sweep pass.
- Before push, verify clean tree, remote `dev` still at base and exact fast-forward; verify pushed SHA afterward.

## Integration contract

The new AR package is the default section route for `startRun` and `reauditRun`; old Runs retain pinned identities and the v3 reader remains available. The copied original files are exact, while the current single-Run transport/output schema and evidence gate still govern execution. A profile source file changing under the same identity is rejected by SHA validation. The original's unverified numeric statements are context for expert review, never canonical normative conclusions.

## Failure/idempotency/security cases

- Missing or modified original source material refuses registry startup, never silently substitutes another section.
- Same-key Run replay retains its pinned pair; a changed profile creates a new Run only under a new key.
- A model observation without exact document evidence is withheld; no normative conclusion is emitted from the original checklist alone.

## Rollback / feature flag

The saved `ready/ar-v3-20261030` branch is the exact pre-change solution. A revert of the dev commit removes new AR starts; keep execution support for already accepted new-profile Runs until they finish.

## Handoff

- Changed files: copied original АР resources and executable profile under
  `src/auditmanager/analysis/text/`, its registry/schema, version-screen start and
  profile/classification UI, focused Python/web tests, the `1.13.0` contract
  family and generated client/lock, and this program record. The exact file list
  is the integration commit's diff.
- Checks: all nine copied resources match the source clone byte for byte and by
  SHA-256; 907 focused Python tests passed, 73 skipped; 65 contract/prose tests
  passed on the final `1.13.0` seal; 103 focused web tests passed; frontend
  typecheck, lint, `api:verify`, pin sweep and `git diff --check` passed.
- Contracts: shared `1.12.0` → `1.13.0`, domain candidate revision `30` → `31`;
  131 paths, 148 operations and 432 schemas remain. No migration, identity,
  error code or operation was added.
- Limitation: only the original profile and prompt resources moved. The source
  app's drawing, norm, merger, review and Excel stages did not. The seven
  document-grounded categories are executable; the original normative categories
  need verified norm evidence and are not emitted by this text-only Run.
- Integrator: keep the saved `ready/ar-v3-20261030` branch; publish the tested
  commit by fast-forward to `origin/dev`, verify its SHA and leave `origin/main`
  untouched. Reverting this commit restores the old default start, but Runs
  accepted under the new immutable profile need its bundle retained to finish.
- Forbidden-hotspot proof: the integration diff contains no files under
  `db/migrations/`, no dependency/lockfile, composition root, global style,
  AR v3 group/worker, comparison evidence, or `origin/main` update.
