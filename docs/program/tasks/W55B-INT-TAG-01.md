# Task W55B-INT-TAG-01 — release deployed W55b as v0.6.0

task_id: W55B-INT-TAG-01

## Outcome

Publish annotated `v0.6.0` on the exact deployed W55b commit
`37393a979a430e490843d7f410e9eca9491a4ea1` and record the owner's
explicit waiver of five credentialed live acceptance checks.

## Depends on

- `W55B-INT-MAIN-PREP-03`, completed for the exact candidate.
- `W55B-INT-MAIN-VERIFY-ADDENDUM-01`, completed at `f0b12ea705a9ccb476b5b69a5797de7d3731f543`.

## Frozen inputs

- candidate and deployed `origin/main`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- `VERSION=0.6.0`, `release-notes/0.6.0.json` revision 2;
- API 47 paths / 54 operations / 123 schemas, 24 errors;
- migration head `0021_portal_bundles`;
- full gate completion under R-125 on the exact candidate;
- workflow run `38897018419`, owner-run `verify-deployed.sh`, public preflight;
- base commit: `f0b12ea705a9ccb476b5b69a5797de7d3731f543`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the owner explicitly waived the five credentialed live checks and instructed release as-is.

### P-01 — deployed commit and published tag

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/main refs/tags/v0.6.0 'refs/tags/v0.6.0^{}'`
- captured_output:
  ```text
  37393a979a430e490843d7f410e9eca9491a4ea1 refs/heads/main
  6c0558508cb20cd2ee98f026b90b1798ab1ae26a refs/tags/v0.6.0
  37393a979a430e490843d7f410e9eca9491a4ea1 refs/tags/v0.6.0^{}
  ```
- interpretation: the published annotated tag dereferences to the already deployed main commit; the owner's quoted waiver above leaves five product checks unverified.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/W55B-INT-MAIN-VERIFY-ADDENDUM-01.md
- addendum_path: docs/program/W55B-INT-TAG-01.md

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

The owner directly instructed publication of the version as-is after naming
the exact candidate and waiving the acceptance requirement. Only the
`refs/tags/v0.6.0` tag ref is newly published; `origin/main` is not moved.

## Allowed paths

- `docs/program/tasks/W55B-INT-TAG-01.md`
- `docs/program/W55B-INT-TAG-01.md`
- `docs/program/RELEASES.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/test source, deployment workflow, historical
evidence, production DB/S3 and `origin/main`.

## Non-goals

No credentialed product journey, workflow-fix deployment, beta claim,
normative corpus import or code change.

## Deliverables

Annotated tag and remote dereference on exact SHA; additive release evidence
report; release ledger row on `origin/dev` that distinguishes measured and
unmeasured image metadata.

## Required checks

- Before tag: clean exact candidate, no existing remote tag, remote main exact SHA.
- After tag: direct remote tag dereference to exact SHA; no main movement.
- Release note validation, API build ID calculation, ledger consistency.
- `.venv/bin/python -m pytest tests/contract/program/test_wave_governance.py -q`,
  `.venv/bin/python scripts/task_handoff.py --task docs/program/tasks/W55B-INT-TAG-01.md --worktree .`,
  `git diff --check`.

## Integration contract

The tag names the already deployed and host-verified W55b tree. The five
credentialed live checks were waived by the owner, not passed; downstream
readers must preserve that distinction. The release record changes no
deployed bytes. Dev publication is a fast-forward after documentation checks.

## Failure/idempotency/security cases

If `v0.6.0` exists at any target, do not rewrite it. If main moves away from
the candidate before publication, stop. No credentials or private host logs
enter Git. A repeated push of the same tag is a no-op.

## Rollback / feature flag

No runtime change or feature flag. Correct evidence with a later addendum;
never rewrite a published tag or `origin/main`.

## Handoff

- changed files: this task, its report and release ledger;
- contracts: unchanged;
- known limits: five owner-waived live checks, workflow verification defect;
- forbidden hotspots: untouched by the exact allowed-path diff.
