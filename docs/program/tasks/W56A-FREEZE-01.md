# Task W56A-FREEZE-01 — freeze the W56a implementation grants

**Status: DRAFT / STOPPED.** This definition records the accepted W55b base and the
remaining entry checks. It grants no implementation lane until the integrator records
both gateway probes and publishes a completed freeze report.

## Outcome

The integrator fixes one W56a base, model identities, corpus specification, migration
number, pin inventory, lane ownership and verification rules so that Stage A can start
from an auditable SHA.

## Depends on

- `W55B-INT-CLOSE` — complete on `origin/dev` at `6d63802ab465a0317839c9b57abd5e90f3d91769`.
- `W56A-RULE-01` — completed on the local `integration/w56a` line at
  `f47c129e6d08d509ad3d2288926244afe265468b`; its `R-129`…`R-134` entries have been
  checked against the `R-128` last number on `origin/dev`.

## Frozen inputs

- base commit: local `integration/w56a` `f47c129e6d08d509ad3d2288926244afe265468b`
  (including completed RULE and prep chain), descending from `origin/dev`
  `6d63802ab465a0317839c9b57abd5e90f3d91769`; recheck immediately before completion.
- domain contract: `contracts/domain/v1/error-codes.json` SHA-256 `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`; candidate revision 12.
- API contract: `contracts/api/v1/openapi.json` SHA-256 `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`; 47 paths / 54 operations / 123 schemas.
- analysis contract: `contracts/analysis/v1/stage-registry.json` SHA-256 `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`.
- provider lock: `docs/program/P02_LOCK.json` SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- `contract_version`: unchanged, `1.0.0-draft.1`; migration head `0021_portal_bundles`; proposed next migration `0022_findings_v2` belongs to `W56A-SEAL-01` only.
- governing plan: `docs/program/dispatch/W56-PLAN.md` Part A on the local base,
  adjusted by the completed `W56A-RULE-01` for `R-124` and `R-126`.
- legacy inputs: six files at clean `/root/projects/PDF-proverka` checkout `16ba8e5d23e4782550e79355002fde1365f682b7`; SHA-256 values in the preflight report, to be rechecked at completion.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

This freeze is a document grant. `W56A-SEAL-01` will own enumerated contract, error,
migration and surface changes. Its complete `pin_sweep.py` inventory must be an explicit
part of its post-freeze task grant.

## Captured premise evidence

- premise: accepted W55b plus locally completed W56a RULE and prep chain

### P-01 — integration base with completed RULE

- captured_at: 2026-10-15
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  f47c129e6d08d509ad3d2288926244afe265468b
  ```
- interpretation: the local W56a integration line includes the accepted W55b close
  and the completed RULE and prep tasks. A later ref movement requires a fresh sweep.

### P-02 — model and legacy inputs

- captured_at: 2026-10-15
- command: `sha256sum contracts/api/v1/openapi.json contracts/domain/v1/error-codes.json contracts/analysis/v1/stage-registry.json docs/program/P02_LOCK.json`
- captured_output:
  ```text
  8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482  contracts/api/v1/openapi.json
  b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16  contracts/domain/v1/error-codes.json
  845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5  contracts/analysis/v1/stage-registry.json
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: these are the current pre-seal files, not W56a contract versions.

### P-03 — advisory reseal inventory

- captured_at: 2026-10-15
- command: `/root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface migration table error-code`
- captured_output: the complete 98-line stdout is transcribed in `docs/program/W56A-FREEZE-01.md` §4; SHA-256 `dd6d025853316a6764b8c66856b6952408f1e43e72c01b664f01c30cd250c11b`.
- interpretation: advisory grant inventory, not evidence that every path must change.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-FREEZE-01.md`
- `docs/program/W56A-FREEZE-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lockfiles, composition roots,
  global styles, `AGENTS.md`, `OWNER_RULINGS_*.md`, `P02_LOCK.json`, `VERSION`, release notes,
  refs, tags, stand state, model recordings and all implementation paths.

## Non-goals

- Paid calls or changes to provider credentials; contract seal; corpus generation;
  implementation dispatch; a W56a release or `origin/main` publication.

## Deliverables

- A completed freeze report with two distinct gateway identity probes, each with a
  configured-model response and a stub/default response, reported model identity,
  `usage.cost` rate check at a stated tolerance, spent amount and decision.
- Fresh source digests, pin inventory, predecessor-version hits, corpus rules,
  migration/head and debt status; precise task and ownership grants, including
  the actual exhaustive `CATEGORY_LABELS` file and the knowledge-base page's
  explicit category choices (the plan's label-file location is stale).
- If a probe cannot run or fails, a blocked report with the missing fact and no grant.

## Required tests

- command: `git diff --check`; expected: exit 0.
- command: `git diff --name-only <base>...HEAD`; expected: only the two allowed paths.
- command: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program/test_wave_governance.py`; expected: exit 0 on a completed candidate.
- command: re-run `tools/plan/pin_sweep.py reseal-surface migration table error-code` on the final accepted base; expected: exit 0, complete path list captured.
- command: re-run six-file SHA-256 and `git grep -n '0\.6\.0' -- tests web/tests`; expected: source identity and predecessor hits captured.
- command: per-gateway identity probes of plan §A3.5; expected: two independent passes within the $5 ledger, or a named stop. No probe has been run in this draft.

## Integration contract

No code lane may use this draft. After both probes pass, the integrator amends this
task/report on the current base, records the final freeze
SHA and grants the ordered lanes in plan §§A4–A5: SEAL owns all shared contracts,
migration `0022`, generated client and direct pins; GENERATOR owns its new fixture
families after SEAL; Stage B is PROVIDER → PROFILES → MERGE → DECIDE → HARNESS → WEB,
each from the prior merge. Shared adapters, executor, finding queries and language
guard change hands only in that order. Each lane gets a task file with its own exact
`allowed_paths`; the freeze does not itself license edits to those paths.

## Failure/idempotency/security cases

- A missing/echoed/fallback model, wrong price rate, absent gateway, or spend
  projection above $5 stops the relevant probe; no recording is accepted from it.
- No token, gateway host or provider-env value enters reports or tool output.
- A repeated freeze check on the same SHA is read-only; a changed base restarts its
  premise and pin checks.

## Rollback / feature flag

This task changes only two documents; revert those docs to abandon this draft.
The runtime feature flag remains the future profile setting in plan §A3.1, default
v1 in development; the host-owned switch to v2 is a later owner act.

## Handoff

- changed files: this task and `docs/program/W56A-FREEZE-01.md` only.
- commands/results: record in the preflight report and update on completion.
- known limits: two gateway probes are pending; RULE is complete locally.
- integration notes: publish no Stage A grant while this file says STOPPED.
