# Task W52-INT-C-WEB-01 — accept the release web lane

task_id: W52-INT-C-WEB-01

## Outcome

The exact W52 release-web candidate is reviewed on the merged development
tree and published to `origin/dev`, giving TRANSLATE a read-back base.

## Depends on

- `W52-INT-C-API-01`, published to `origin/dev`.
- `W52-INT-WEB-GRANT-01`, published at
  `ffcf0ac0fe42ab8539cca9c33ee71c334f4272e0`.
- `W52-RELEASES-WEB`, complete on clean `agent/w52-releases-web` at
  `93bd4da8d047d0717bd032221bb7255c340e8dea`.

## Frozen inputs

- Integration base and current `origin/dev`:
  `ffcf0ac0fe42ab8539cca9c33ee71c334f4272e0`.
  The WEB candidate has that exact parent.
- Frozen API 30 paths / 37 operations / 83 schemas, 23 error codes,
  domain revision 9 / 29 identities, migration head
  `0016_release_notes`, `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §3.5 and Stage C; `W52-RELEASES-WEB.md`
  reports lane evidence. D-137–D-140 retain complete gate, independent QA
  and live/browser acceptance.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/src/shared/api/query-keys.ts`,
  `tests/e2e/pc01/journey/manifest.json` and the language/credential
  inventories named in the lane report
- enumerator_owner: `W52-RELEASES-WEB`
- totality_query: exact 36-path diff, query-key, language, credential,
  contrast and journey-conformance tests on the merged tree

## Captured premise evidence

- premise: the completed candidate descends directly from the published
  WEB grant; `origin/main` is independent and not a publication target.

### P-01 — remote refs and candidate parent

- captured_at: 2026-10-08
- command: `git ls-remote origin refs/heads/dev refs/heads/main;
  git rev-parse 93bd4da^`
- captured_output:
  ```text
  ffcf0ac0fe42ab8539cca9c33ee71c334f4272e0 refs/heads/dev
  9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c refs/heads/main
  ffcf0ac0fe42ab8539cca9c33ee71c334f4272e0
  ```
- interpretation: a checked fast-forward of the WEB lane is possible;
  this supplies no authority to publish `origin/main`.

## Historical evidence

- correction_mode: none
- source_record: `W52-INT-WEB-GRANT-01` is the prior narrow task correction
- addendum_path: `docs/program/W52-INT-WEB-GRANT-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- The exact 36 paths of `ffcf0ac..93bd4da`, listed in
  `docs/program/W52-RELEASES-WEB.md` §1 and granted by
  `tasks/W52-RELEASES-WEB.md`.
- `docs/program/tasks/W52-INT-C-WEB-01.md`,
  `docs/program/W52-INT-C-WEB-01.md` — integration record.
- `docs/program/CURRENT_STATE.md` — opening W52 status only.
- `docs/program/dispatch/W52-PLAN.md` — Stage-C status only.
- `docs/program/tasks/W52-TRANSLATE-01.md` — read-back WEB base only.
- Clean `integration/w51` ref and fast-forward of `origin/dev` only.

## Forbidden hotspots

Every other path, in particular `contracts/**`, migrations, generated
client, root dependency/lock, composition root, `globals.css`,
`origin/main`, tags, workflows and deployed services. This task adds no
product-code edits to the accepted WEB lane.

## Non-goals

No TRANSLATE implementation, Stage C2 grant, full `make gate`, QA,
built-stand/browser acceptance, release verdict, tag or deployment.

## Deliverables

- Exact path/parent review and merged focused checks.
- A clean development publication with SHA readback and a six-part report.
- Updated TRANSLATE base after the readback.

## Required checks

- Exact parent, 36-path inventory and `git diff --check`.
- On merged tree: release/style/frontend guards, journey-manifest
  conformance, `api:verify`, lint and typecheck; docs governance/prose
  checks after the integration record.
- Re-read `origin/dev` immediately before a proven fast-forward push and
  read it back afterwards. Full `make gate` remains D-140, not claimed.

## Integration contract

Fast-forward the accepted WEB commit into the clean integration worktree.
Commit only the named integration documentation after merged checks.
Publish the checked SHA to `origin/dev` only if the remote ref still equals
the recorded base, then read back that exact SHA. TRANSLATE starts from that
readback, not a local candidate.

## Failure / idempotency / security

An unexpected path, stale remote ref or failed focused check stops
publication. No user credential enters a browser response or
`NEXT_PUBLIC_*`; the internal BFF version route is session protected.

## Rollback / feature flag

Revert on the development line with a new reviewed commit if necessary;
do not rewrite history. No runtime feature flag or deployment is used.

## Handoff

Return changed files, checks/results, contracts, risks, next integrator
step and forbidden-hotspot proof. No checkpoint or tag.
