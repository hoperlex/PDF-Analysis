# Task W56A-PREP-GOV-FIX-01 — complete premise declarations in draft task definitions

task_id: W56A-PREP-GOV-FIX-01

## Outcome

The two unintegrated W56a preparation task definitions explicitly declare the
premise already supported by their captured commands and outputs. The governed
task inventory on this branch passes without changing either historical report.

## Depends on

- `W56A-PREFREEZE-01` — completed at `5bac83533b482c5635da5baa20edab35aaddea50`.
- `W56A-LEGACY-SOURCE-01` — completed at `5f742b22c109b8f0b289962750d305495a3449c3`.
- `W57A-CORPUS-SOURCE-PREP-01` — completed at `290325315c72d384013466fb6259096ac3f5d0ac`.

## Frozen inputs

- base commit: `290325315c72d384013466fb6259096ac3f5d0ac`.
- domain contract: candidate revision 12; error catalogue SHA-256
  `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`.
- API contract: 47 paths / 54 operations / 123 schemas; OpenAPI SHA-256
  `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`.
- analysis contract: stage registry SHA-256
  `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`.
- migration head: `0021_portal_bundles`.
- `tests/contract/program/test_wave_governance.py` on the base; both task
  files' existing `Captured premise evidence` sections and P-01 records.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the base governance check fails only because two preparation task
  definitions omit their explicit `- premise:` declaration.

### P-01 — exact failing task inventory

- captured_at: 2026-10-14
- command: `/root/projects/PDF-Analysis/.venv/bin/python - <<'PY'
from runpy import run_path
print(run_path('tests/contract/program/test_wave_governance.py')['governed_task_findings']())
PY`
- captured_output:
  ```text
  {'docs/program/tasks/W56A-LEGACY-SOURCE-01.md': {'PREMISE_DECLARATION_REQUIRED'}, 'docs/program/tasks/W56A-PREFREEZE-01.md': {'PREMISE_DECLARATION_REQUIRED'}}
  ```
- interpretation: this is the complete checker finding map. The two task
  definitions need only a declaration; their P-01
  commands, captured outputs and source reports remain valid as written.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

These are unintegrated draft task definitions. Their captured outputs and
completed reports are not altered. A new report records this metadata fix.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-PREFREEZE-01.md` (one premise declaration)
- `docs/program/tasks/W56A-LEGACY-SOURCE-01.md` (one premise declaration)
- `docs/program/tasks/W56A-PREP-GOV-FIX-01.md`
- `docs/program/W56A-PREP-GOV-FIX-01.md`

## Forbidden hotspots

- all other tracked paths, including `contracts/**`, migrations, root dependencies
  and lockfiles, composition roots, global styles, prior reports and reviews
- W56a ruling branch, W55b refs/worktrees, stand, credentials and source corpus

## Non-goals

- Changing a captured command/output, rewriting historical reports, altering
  governance test rules, integrating W56a/W57a, running a paid call or publishing.

## Deliverables

- Two short premise declarations, this task, and a brief report with the
  before/after governance result and integration instruction.

## Required tests

- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program/test_wave_governance.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`.
- expected: all pass on this branch.
- command: `git diff --check <base>..HEAD` and `git diff --name-only <base>..HEAD`.
- expected: exit 0 and exactly the four allowed paths.

## Integration contract

The integrator uses this branch tip as the complete W56a prefreeze/legacy
source and W57a corpus-preparation chain. The separate `W56A-RULE-01` branch
still needs its own premise declaration before merge; this task does not
silently edit that branch.

## Failure/idempotency/security cases

- If the governance test names another task, record and fix that task in its
  owning slot, not by weakening the test.
- No source content, secret, private export or paid response changes.

## Rollback / feature flag

Revert this document-only commit. No runtime rollback or feature flag.

## Handoff

- changed files: see Allowed paths.
- commands/results: report §2.
- known limits: the separate W56a ruling branch remains outside this branch.
- integration notes: report §3.
