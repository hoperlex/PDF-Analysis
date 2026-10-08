# Task W52-INT-C-TRANSLATE-01 — accept English operator runbooks

task_id: W52-INT-C-TRANSLATE-01

## Outcome

The exact W52 runbook-translation candidate is reviewed on the merged
development tree and published to `origin/dev`, completing Stage C code.

## Depends on

- `W52-INT-C-WEB-01`, published to `origin/dev` at
  `a17ddfdb4481e599c36098706b5898952fb8b28e`.
- `W52-TRANSLATE-01`, complete on clean `agent/w52-translate-01` at
  `167706974dfc55e1b0f24c5e43b28e4591746e2f`.

## Frozen inputs

- Integration base and current `origin/dev`:
  `a17ddfdb4481e599c36098706b5898952fb8b28e`.
  The translation candidate has that exact parent.
- API 30 paths / 37 operations / 83 schemas; 23 error codes;
  domain revision 9 / 29 identities; migration head
  `0016_release_notes`; `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` Stage C and §8; `W52-TRANSLATE-01.md`
  reports lane evidence. D-137–D-140 retain full gate, QA and live checks.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: exact seven-path diff and unchanged 11 checkpoint runbooks

## Captured premise evidence

- premise: the candidate descends directly from the published WEB
  integration; the deployment ref is not a publication target.

### P-01 — remote refs and candidate parent

- captured_at: 2026-10-08
- command: `git ls-remote origin refs/heads/dev refs/heads/main;
  git rev-parse 1677069^`
- captured_output:
  ```text
  a17ddfdb4481e599c36098706b5898952fb8b28e refs/heads/dev
  9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c refs/heads/main
  a17ddfdb4481e599c36098706b5898952fb8b28e
  ```
- interpretation: the clean translation lane can be fast-forwarded.
  No `origin/main` authority follows.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- The exact seven paths of `a17ddfd..1677069`, listed in
  `docs/program/W52-TRANSLATE-01.md` §1 and granted by
  `tasks/W52-TRANSLATE-01.md`.
- `docs/program/tasks/W52-INT-C-TRANSLATE-01.md`,
  `docs/program/W52-INT-C-TRANSLATE-01.md` — integration record.
- `docs/program/CURRENT_STATE.md` — opening W52 Stage-C status only.
- `docs/program/dispatch/W52-PLAN.md` — Stage-C status only.
- Clean `integration/w51` ref and fast-forward of `origin/dev` only.

## Forbidden hotspots

All other paths, especially contracts, migrations, root dependencies/locks,
generated client, composition root, product UI, global styles, executable
acceptance scripts, `origin/main`, tags and deployed services.

## Non-goals

No Stage C2 grant or implementation, full `make gate`, QA, live acceptance,
release verdict, tag or deployment.

## Deliverables

- Exact path/parent and preserved-command review, merged focused checks,
  clean development publication with SHA readback, and a six-part report.

## Required checks

- Exact parent, seven-path inventory, Bash/ID/figure preservation and
  `git diff --check`.
- On the merged tree: prose/count, bootstrap, alpha-command and wave
  governance checks. Report the CP-00 baseline failure and P02 service
  dependency without claiming them green.
- Re-read `origin/dev` immediately before the fast-forward push and
  read it back afterwards. Full gate remains D-140.

## Integration contract

Fast-forward the accepted translation commit into clean `integration/w51`.
Commit only the named docs follow-up after merged checks. Publish the
checked SHA to `origin/dev` if the remote still equals the recorded base;
read back the exact result. Stage C2 needs a separate fresh grant.

## Failure / idempotency / security

An unexpected path, changed command/case ID, stale ref or failed applicable
check stops publication. No credentials are included in the runbooks.

## Rollback / feature flag

Revert a dev-only mistake with a new reviewed commit, not rewritten
history. This prose has no runtime feature flag.

## Handoff

Return changed files, checks/results, contracts, risks, next integrator
step and forbidden-hotspot proof. No checkpoint or tag.
