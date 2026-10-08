# Task W52-INT-C-API-01 — accept the release backend and grant the remaining Stage-C lanes

task_id: W52-INT-C-API-01

## Outcome

The exact W52 release-backend candidate is reviewed, checked on the merged
development tree and published to `origin/dev`. RELEASES-WEB and TRANSLATE
receive current-tree grants for the following Stage-C work.

## Depends on

- `W52-INT-B2C-01`, published at `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`.
- `W52-RELEASES-API`, complete on clean `agent/w52-releases-api` at
  `81e5181a34dd6905814f1ecb02de305e2e99aabd`.

## Frozen inputs

- Integration base and `origin/dev`: `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`.
  API candidate `81e5181` has that exact parent.
- API 30 paths / 37 operations / 83 schemas; 23 error codes; domain
  revision 9 / 29 identities; migration head `0016_release_notes`;
  `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §§3.1–3.5, Stage C and §5; R-71–R-74.
  D-137–D-140 retain the complete gate, independent QA and live evidence.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the merged backend adds no API operation or migration;
  the release loader's entry/service inventories are covered by
  `W52-RELEASES-API`.

## Captured premise evidence

- premise: the exact completed lane is a direct descendant of the current
  development ref, and the deployment ref has not moved.

### P-01 — remote refs and candidate parent

- captured_at: 2026-10-08
- command: `git ls-remote origin refs/heads/dev refs/heads/main; git rev-parse 81e5181^`
- captured_output:
  ```text
  3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551 refs/heads/dev
  1e9bb1308b7b97cd75eef28e206b23c569871b68 refs/heads/main
  3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551
  ```
- interpretation: a checked fast-forward is possible; it gives no authority
  to update `origin/main`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- The exact 25 paths of `3fc0dcf..81e5181`, each already enumerated in
  `docs/program/W52-RELEASES-API.md` §1 and granted by
  `tasks/W52-RELEASES-API.md`, including its narrow integrator correction
  for `tests/integration/api/test_release_routes.py` and the task file.
- `docs/program/tasks/W52-INT-C-API-01.md`,
  `docs/program/W52-INT-C-API-01.md` — integration record.
- `docs/program/tasks/W52-RELEASES-WEB.md`,
  `docs/program/tasks/W52-TRANSLATE-01.md` — current-tree grants only.
- `docs/program/CURRENT_STATE.md` — opening W52 status only.
- `docs/program/dispatch/W52-PLAN.md` — Stage-C status and order only.
- `docs/program/dispatch/PORT_REGISTRY.md` — Stage-C lane rows only.
- Clean `integration/w51` ref and fast-forward of `origin/dev` only.

## Forbidden hotspots

All other paths, in particular `contracts/**`, `db/migrations/**`, root
dependency and lock files, generated client, web UI, global styles,
`origin/main`, tags, workflows and the deployed stand. The accepted API
candidate's composition-root/deploy edits are confined to its named grant;
this integration task adds no product-code edits.

## Non-goals

No WEB or TRANSLATE implementation, Stage C2 grant, full `make gate`, QA,
built-stand acceptance, release verdict, tag or deployment.

## Deliverables

- Reviewed 25-path candidate and integrator correction, checked exact
  merged candidate and a clean development publication with SHA readback.
- Fresh sweep and task grants for RELEASES-WEB and TRANSLATE with isolated
  resources and exact forbidden paths.
- Six-part integration report.

## Required checks

- `git diff --check 3fc0dcf..81e5181` and exact changed-path audit.
- `python3 tools/plan/pin_sweep.py table` and current-tree references for
  both Stage-C grants.
- Focused merged release/API database tests on the reserved `gate-w52r`
  instance; contract/governance tests, API client verification, frontend
  lint/typecheck and `git diff --check` on the docs follow-up.
- Full `make gate` is deferred by the owner's W52 code-first direction to
  D-140; no `GATE OK` claim from these checks.

## Integration contract

Fast-forward only from the checked candidate, then commit only the named
documentation follow-up. Re-read `origin/dev` immediately before pushing a
proven fast-forward and read back the pushed SHA. WEB and TRANSLATE begin
from that exact read-back grant, not from the pre-API Stage-C base.

## Failure / idempotency / security

A missing grant, unexpected path, stale remote ref or failed focused check
stops publication. Use no other lane's containers or credentials. The
loader is transactional and idempotent as evidenced by RELEASES-API.

## Rollback / feature flag

Revert the dev-only candidate with a new reviewed commit if necessary;
do not rewrite published history. The backend has no runtime feature flag.
No production deployment is authorized.

## Handoff

Return changed files, checks/results, contracts, risks, next integrator
step and forbidden-hotspot proof. No checkpoint or tag.
