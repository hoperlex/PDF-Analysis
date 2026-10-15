# Task W56A-PLAN-PATH-FIX-01 — correct W56a category-label ownership paths

task_id: W56A-PLAN-PATH-FIX-01

## Outcome

The W56a plan names the current source of the exhaustive `FindingCategory` label map and assigns
that map to SEAL, while WEB owns the knowledge-base page filter that consumes it. The freeze
owner can grant the two lanes without relying on the map's former widget path.

## Depends on

- `W55B-INT-CLOSE` — completed on `origin/dev` at `6d63802a`.
- `W56A-RULE-01` — completed and merged on the integration base.

## Frozen inputs

- base commit: `f47c129e6d08d509ad3d2288926244afe265468b` (`integration/w56a`).
- domain error catalog: candidate revision 12; `contracts/domain/v1/error-codes.json`
  SHA-256 `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`.
- API contract: 47 paths / 54 operations / 123 schemas; `contracts/api/v1/openapi.json`
  SHA-256 `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`.
- analysis contract: `contracts/analysis/v1/stage-registry.json` SHA-256
  `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`.
- migration head: `0021_portal_bundles`; controlling plan: `docs/program/dispatch/W56-PLAN.md`
  §A2, §A4 and §A5 at the base above.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the exhaustive category label map is in the expert-decision entity, while the
  knowledge-base page derives its filter choices from that map.

### P-01 — current category-label and filter locations

- captured_at: 2026-10-15
- command: `rg -n --sort path '^export const CATEGORY_LABELS|^const CATEGORY_CHOICE_LABELS|^  \.\.\.CATEGORY_LABELS' web/src/entities/expert-decision/model/category-labels.ts web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`
- captured_output:
  ```text
  web/src/entities/expert-decision/model/category-labels.ts:20:export const CATEGORY_LABELS: Readonly<Record<FindingCategory, string>> = {
  web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:60:const CATEGORY_CHOICE_LABELS: Readonly<Record<CategoryChoice, string>> = {
  web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:62:  ...CATEGORY_LABELS,
  ```
- interpretation: SEAL must own the exhaustive map to keep the widened generated enum typed;
  WEB may later change the page's filter UI while consuming that map. The widget imports the map
  but no longer declares it.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The W56a plan is a current dispatch document. This task corrects its prospective path grant;
completed task and review evidence remains untouched.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/dispatch/W56-PLAN.md` §A2, §A4 and §A5 path/ownership wording only
- `docs/program/tasks/W56A-PLAN-PATH-FIX-01.md`
- `docs/program/W56A-PLAN-PATH-FIX-01.md`

## Forbidden hotspots

- all code, tests, fixtures, `contracts/**`, `db/migrations/**`, root dependencies and lockfiles,
  composition roots and global styles
- `AGENTS.md`, `CURRENT_STATE.md`, `OWNER_RULINGS_*.md`, other plans, prior task/review reports,
  W55b refs, the stand and credentials

## Non-goals

- W56a freeze, SEAL/WEB implementation, a new owner decision, gateway probes or a paid call.

## Deliverables

- Corrected path and ownership wording in the W56a plan; this task definition and a report
  stating checks, limits and the freeze handoff.

## Required tests

- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program/test_wave_governance.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: exit 0.
- command: `git diff --check f47c129e..HEAD` and `git diff --name-only f47c129e..HEAD`
- expected: exit 0 and exactly the three allowed paths.
- command: the P-01 `rg` query.
- expected: the same three source lines; no source file is changed.

## Integration contract

Cherry-pick this document-only task onto `integration/w56a` before `W56A-FREEZE-01`.
The freeze grants SEAL the exact `category-labels.ts` path and excludes it from WEB's broad
entity family; WEB owns the page filter. This task grants no implementation lane by itself.

## Failure/idempotency/security cases

- If either source path moves before freeze, rerun P-01 and correct the plan through a new
  owning task rather than silently granting the old path.
- No runtime, corpus, credential or deployment effect is created.

## Rollback / feature flag

Revert this document-only commit before freeze; no feature flag or data rollback is needed.

## Handoff

- changed files: the three Allowed paths.
- commands/results: report §2.
- known limits: freeze and code work remain separate.
- integration notes: report §3.
