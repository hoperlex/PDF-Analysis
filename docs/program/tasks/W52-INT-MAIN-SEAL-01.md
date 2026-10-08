# Task W52-INT-MAIN-SEAL-01 — publish the pinned Stage-B seal to main

task_id: W52-INT-MAIN-SEAL-01

## Outcome

Merge the exact development commit `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`
with deployed main `9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`, validate the resulting
tree, and publish only that verified fast-forward successor to `origin/main`.
The GitHub deployment and public origin must verify the same successor SHA.

## Depends on

- `W52-INT-MAIN-01`, completed on `origin/main` at `9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`.
- `W52-INT-B2C-01`, completed on `origin/dev` at `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`.

## Frozen inputs

- Main: `9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`; development snapshot:
  `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`. Later development commits
  are outside this task.
- Domain candidate revision 9 / 29 identities; API 30 paths / 37 operations /
  83 schemas; error catalog 23; migration head `0016_release_notes`;
  `contract_version=1.0.0-draft.1`.
- `docs/program/MAIN_AUTODEPLOY_POLICY.md` and the owner's direct 2026-10-08
  instruction to check `3fc0dcf` in isolation and merge it into main.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: inherited API and migration members are pinned by `W52-SEAL-01`

## Captured premise evidence

- premise: the owner pinned the exact development source while remote dev advanced.

### P-01 — publication refs before integration

- captured_at: 2026-10-08
- command: `git ls-remote --heads origin dev main`
- captured_output:
  ```text
  fa3975a32473d69bec1eb9bdba27cef21a6c29e4 refs/heads/dev
  9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c refs/heads/main
  ```
- interpretation: the user pinned `3fc0dcf` explicitly; the newer development
  tip is excluded. Main must still name the recorded base immediately before push.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/main
- origin_main_authority: separate direct owner instruction 3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551

The owner's message in this session names the exact development snapshot and
directly instructs merging it into main. This task alone owns that publication.

## Allowed paths

- Merge the two frozen commits with the exact tracked development blobs from
  `3fc0dcf` and preserve main's earlier gate repairs; no content conflict occurred.
- `docs/program/tasks/W52-INT-MAIN-SEAL-01.md` — this grant and evidence boundary.
- `docs/program/W52-INT-MAIN-SEAL-01.md` — prepublication report and risk record.
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` —
  enumerate the new unaddressed GET routes and assert their intentional
  Stage-B `dependency_unavailable` refusal.
- `tests/integration/composition/test_every_port_implementation_is_whole.py` —
  include the new `ReleasesPort` in the whole-port wiring guard.
- `tests/integration/api/identity_surface.py` — make its injected release
  stand-in explicit and runtime-check the forwarded port so the whole-port
  guard can verify this otherwise opaque wiring.
- Local isolated branch, ignored test configuration and services owned by this task.

## Forbidden hotspots

No newly authored `contracts/**`, migration, root dependency or lock file,
composition root, global style, generated client, deployment flow or product
runtime change. The inherited SEAL contract/migration/composition changes belong
to completed `W52-SEAL-01`; this task only integrates their exact blobs. No tag,
force-push, post-gate fix or update to `origin/dev`.

## Non-goals

No Stage-C release loader, VERSION, release notes, UI, release verdict or later
development commits. The three new release operations deliberately return
`dependency_unavailable` until Stage C; this publication does not represent a
completed product-version feature.

## Deliverables

- Clean merge successor with both parent histories, pinned SEAL blobs and the
  two narrow composition-guard corrections exposed by the first gate.
- Isolated focused contract, migration and route checks; production web and API
  image builds; complete `make gate` with literal `GATE OK` on one exact SHA.
- Fast-forward `origin/main` only after a fresh ref check, then verify the exact
  workflow, host script and public HTTPS/application boundary.

## Required tests

- `git diff --check`, clean tree and both-parent ancestry.
- Focused release contract, migration, API and generated-client checks.
- `make gate` to literal `GATE OK` on the committed candidate.
- Production Dockerfiles for API and web on the same candidate.
- After push: exact-SHA workflow success, host `verify-deployed.sh` success,
  verified TLS and public root/protected API probes.

## Integration contract

Only this task may publish the exact checked merge successor to `origin/main`
under the owner's direct instruction. Re-read `origin/main` just before push;
require it still names `9d5b010` and is an ancestor of the candidate. A failed
gate or image build stops publication. The workflow serializes deployments.

## Failure/idempotency/security cases

Do not publish a failing or modified candidate. The Stage-B release routes
remain a deliberate 503 for authorized callers and must not be described as
working release data. Do not include secrets in logs or reports.

## Rollback / feature flag

No feature flag. A rollback is a reviewed forward revert, complete gate and
new exact-SHA deployment; history rewrite is forbidden. Populated `0016`
cannot be downgraded in place and requires database restore.

## Handoff

Record changed files, exact checks, inherited contracts, risks, integration
instruction and forbidden-hotspot proof. No checkpoint or tag.
