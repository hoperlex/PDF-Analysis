# Task W55B-INT-MAIN-01 — publish exact W55b candidate to main

task_id: W55B-INT-MAIN-01

## Outcome

Publish the clean, gate-completed W55b candidate
`37393a979a430e490843d7f410e9eca9491a4ea1` to `origin/main`, then
prove that the serialized workflow deployed and verified that same commit.

## Depends on

- `W55B-INT-CLOSE`, completed at `6d63802ab465a0317839c9b57abd5e90f3d91769`.
- `W55B-INT-D142-GATE-REPAIR-01`, completed at the exact candidate SHA above.
- `W55B-INT-MAIN-PREP-03`, completed on `origin/dev` with the exact-candidate R-125 gate record.

## Frozen inputs

- base commit: `45d5772480f62006b430151d464a7f7200be511b`
- task/report record starts from that published `origin/dev` commit;
- candidate: `37393a979a430e490843d7f410e9eca9491a4ea1`, `VERSION=0.6.0`;
- observed `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- API: 47 paths / 54 operations / 123 schemas; error catalog: 24;
- migration head: `0021_portal_bundles`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- main policy SHA-256: `1be97f93e6a8573ff88bc58a75a4166403d0db8badf401dd8e4fe39972fbf818`;
- R-125 gate evidence: `W55B-INT-MAIN-PREP-03.md` and ignored `.local/gates/r125-evidence.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the repository owner directly corrected the requested publication target to main immediately after the integrator named this exact candidate SHA and the current main SHA.

### P-01 — observed remote refs

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/main refs/heads/dev`
- captured_output:
  ```text
  45d5772480f62006b430151d464a7f7200be511b refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: these were the observed refs before the mandatory final main re-read.

### P-02 — candidate ancestry

- captured_at: 2026-10-16
- command: `git merge-base --is-ancestor 23fd729dbb06c642be0588017f6b195305e2e53e 37393a979a430e490843d7f410e9eca9491a4ea1`
- captured_output:
  ```text
  exit status 0
  ```
- interpretation: the candidate is a fast-forward descendant of the observed main.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/main
- origin_main_authority: separate direct owner instruction 37393a979a430e490843d7f410e9eca9491a4ea1

On 2026-10-16 the owner said «Нет, надо публиковать в main» in direct
response to the integrator's statement naming this exact W55b candidate.

## Allowed paths

- `docs/program/tasks/W55B-INT-MAIN-01.md`
- `docs/program/W55B-INT-MAIN-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application source, test source, deployment files, candidate
tree, `origin/dev`, tags and any other remote ref.

## Non-goals

No W56–W59 source publication, normative-corpus import, live provider
credential repair or post-gate code change.

## Deliverables

This task and evidence report; exact-SHA fast-forward push; workflow run and
same-SHA host `verify-deployed.sh` result; public TLS, application and protected
API checks. Record any failed or incomplete deployment truthfully.

## Required checks

- Reconfirm R-110's generated-test-data-only condition immediately before push; if real client data is present, take the required quiesced DB/Blob copy first.
- Check the deployment host's `AUDITMANAGER_RUN_COST_CEILING_USD` is at least USD 0.80, or stop per W55b ruling; record R-46 readiness findings without secrets.
- Recheck clean candidate, R-125 same-SHA gate logs/digests, frozen surfaces and deployment inputs.
- Fetch and reread `origin/main`; prove fast-forward; push only the exact candidate SHA.
- Verify GitHub workflow success, selected commit, host script success and public origin boundary for that same SHA.
- `.venv/bin/python scripts/task_handoff.py --task docs/program/tasks/W55B-INT-MAIN-01.md --worktree .` and `git diff --check` for task/report.

## Integration contract

Only this integration task may update `origin/main` for the exact candidate
under the owner's direct instruction. If any precondition changes, stop. The
authorized remote mutation is only a fast-forward of `refs/heads/main` to
`37393a979a430e490843d7f410e9eca9491a4ea1`; it is not a repository
file in the allowlist above. The
workflow has `cancel-in-progress: false`; do not race a second publication.
Release completion requires the full `MAIN_AUTODEPLOY_POLICY.md` post-push
chain. No tag until that chain and W55b acceptance are complete.

## Failure/idempotency/security cases

No force push or unreviewed follow-up fix. A successful Git push alone is an
incomplete deployment. Keep credentials, ignored env files and logs out of
Git and the report. Repeating read-only preflight is safe; repeat publication
only after proving main still has the old SHA.

## Rollback / feature flag

No flag applies. Rollback requires a reviewed, gated forward revert and a
new exact-SHA deployment; never rewrite main.

## Handoff

- changed files: this task and its outcome report only;
- contracts: unchanged;
- known limit: host readiness values and workflow result are release evidence;
- forbidden hotspots are excluded by the allowlist above.
