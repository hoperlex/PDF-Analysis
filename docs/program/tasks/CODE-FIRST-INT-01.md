# Task CODE-FIRST-INT-01 — принять кодовый план в dev

## Outcome

`origin/dev` fast-forwards from the closed W55b tip to one documentation-only
integration candidate with the code-first plan, W56a preparation, R-135/R-136,
and an explicit path to the first recorded-only code grants. No runtime or
release ref changes.

## Depends on

- `W55B-INT-CLOSE` — complete at `6d63802a` on `origin/dev`;
- `W56A-RULE-01`, `W56A-PROBE-01`,
  `W56A-MODEL-REQUIREMENT-REVIEW-01` — completed on captured
  `integration/w56a` `191fbb36`;
- `CODE-FIRST-BETA-01` — completed at `ca44d074` on
  `plan/code-first-beta`.

## Frozen inputs

- domain contract: candidate revision 12;
- API contract: SHA-256
  `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`;
- analysis contract: stage registry SHA-256
  `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`;
- migration head: `0021_portal_bundles`;
- base commit: `origin/dev` `6d63802ab465a0317839c9b57abd5e90f3d91769`;
- W56a preparation commit: `191fbb36`; plan commit: `ca44d074`;
- output reference: `origin/dev` only, after exact remote-ref check.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `docs/program/OWNER_RULINGS_2026-09-17.md`
- enumerator_owner: `CODE-FIRST-INT-01`
- totality_query: `rg -n 'R-13[3-6]' docs/program/OWNER_RULINGS_2026-09-17.md`

## Captured premise evidence

- premise: the exact W55b base, two merged documentation branches and frozen contract digests

### P-01 — merged source branches

- captured_at: 2026-10-15
- command: `git log -3 --oneline`
- captured_output on the pre-ruling integration tree:
  ```text
  45eb9756 Merge commit 'ca44d074f1273c5f2ad164155a36d37392185ea2' into integration/code-first-entry
  d66abc75 Merge commit '191fbb36' into integration/code-first-entry
  ca44d074 docs(plan): move beta code ahead of full gates and acceptance
  ```
- interpretation: both documentation lines are ancestors of this candidate;
  the branch is not yet published to `origin/dev` by this evidence.

### P-02 — unchanged frozen contract set

- captured_at: 2026-10-15
- command: `sha256sum contracts/api/v1/openapi.json contracts/domain/v1/error-codes.json contracts/analysis/v1/stage-registry.json docs/program/P02_LOCK.json`
- captured_output:
  ```text
  8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482  contracts/api/v1/openapi.json
  b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16  contracts/domain/v1/error-codes.json
  845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5  contracts/analysis/v1/stage-registry.json
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: the planning integration has no seal or model pin.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The stopped W56a freeze and failed probe remain unchanged historical files.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

The owner's direct instruction is to accept this plan in `dev` and prepare
code tasks. This task owns that development ref only; it owns no release tag.

## Allowed paths

- exact documentation and `AGENTS.md` paths in the two fixed source diffs
  `6d63802a..191fbb36` and `6d63802a..ca44d074` (listed by
  `git diff --name-only` before merge);
- `AGENTS.md` §8 code-first override;
- `docs/program/OWNER_RULINGS_2026-09-17.md` R-135/R-136;
- `docs/program/dispatch/W56-PLAN.md` R-135/R-136 header amendment;
- `docs/program/CURRENT_STATE.md` top orientation;
- `docs/program/tasks/CODE-FIRST-INT-01.md`;
- `docs/program/CODE-FIRST-INT-01.md`.

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency/lock files,
  composition roots, global styles, runtime/UI/test code;
- `docs/program/DEBT_REGISTER.md`, `VERSION`, release notes,
  `origin/main`, tags, deployed stand and credentials.

## Non-goals

- no W56a implementation, model pin, full local gate, acceptance or release;
- no claim that W58–W63 have final frozen code grants;
- no change to R-133 or beta criteria B1–B12.

## Deliverables

- merged documentation from the two source branches;
- R-135/R-136 and corresponding AGENTS, plan and state amendments;
- integration report with exact SHA, checks and dev publication proof.

## Required tests

- `git diff --check <base>...HEAD` — clean;
- `.venv/bin/python -m pytest -q -p no:cacheprovider
  tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py
  tests/contract/program/test_wave_governance.py` — green;
- changed-path proof against the base — only Allowed paths;
- before push: `git ls-remote origin refs/heads/dev` equals the frozen base;
  candidate is a fast-forward; after push: remote read-back equals candidate.

## Integration contract

On the published dev SHA, `W56A-DEV-FREEZE-01` may recheck current pins and
write exact SEAL/GENERATOR grants. No code task is licensed by this integration
task alone. Subsequent integration tasks may publish development candidates
to `origin/dev` with their own grants and focused checks; never infer main
authority from this publication.

## Failure/idempotency/security cases

- Remote dev movement aborts the push; reconcile by a new exact candidate.
- A red focused governance/prose check aborts publication.
- Ruling numbers are rechecked for collision before publication.
- No provider secret, endpoint or raw document content enters these files.

## Rollback / feature flag

Documentation-only fast-forward; a corrective commit or revert on dev can
undo it. No runtime flag or data rollback applies.

## Handoff

- changed files and checks: integration report;
- contracts: unchanged;
- limitations: gateway identity and W58–W63 freezes remain pending;
- next task: `W56A-DEV-FREEZE-01` after dev read-back.
