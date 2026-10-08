# Task W51-INT-HOTFIX-01 — restore the alpha web build

task_id: W51-INT-HOTFIX-01

## Outcome

The exact successor of `0df3649526ade130a8dcb715ec8190f3cce0e051` builds the
production web image and deploys from `origin/main` with verification of that
same commit. The owner explicitly waived the full gate for this urgent hotfix
on 2026-10-08 after reviewing its cost.

## Depends on

- `W51-AUTH-01` — completed and merged into `origin/dev` before the PR merge.
- `MAIN-AUTODEPLOY-02` — completed; the serialized exact-SHA workflow is active.

## Frozen inputs

- Base and currently failed `origin/main`: `0df3649526ade130a8dcb715ec8190f3cce0e051`.
- Deployment failure: the web image build rejects `next={next}` in
  `account-page.tsx` because `next` can be `undefined` while the receiving optional
  prop accepts `string | null` under `exactOptionalPropertyTypes`. A subsequent
  complete typecheck exposes the same prop boundary in `register-page.tsx`.
- Frontend validation also exposed existing W51 guard and route-test reds:
  unreachable identity-screen branches, a private query provider in the language
  guard, an explicit cache-read type parameter, and obsolete sign-in route props.
- Domain contract `1.0.0-draft.1`, candidate revision 9, 29 opaque identities;
  API 27 paths / 34 operations / 77 schemas; error catalog 23; migration head
  `0015_accounts_roles_registration`. No reseal is granted.
- Publication policy: `docs/program/MAIN_AUTODEPLOY_POLICY.md`. The owner's
  2026-10-08 instruction to push the hotfix to `main` is the separate direct
  publication instruction for the verified successor of the failed SHA. The
  owner's later 2026-10-08 instruction expressly waives the complete gate for
  this hotfix; all other publication and deployment checks remain required.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the deployed candidate's account screen passes a potentially absent
  `next` prop explicitly to a receiver whose optional prop excludes `undefined`.

### P-01 — failing source boundary

- captured_at: 2026-10-08
- command: `git show 0df3649526ade130a8dcb715ec8190f3cce0e051:web/src/_pages/account/ui/account-page.tsx | rg -n 'EditProfileForm account='`
- captured_output:
  ```text
  40:        <EditProfileForm account={account} next={next} />
  ```
- interpretation: the attached deployment log reports this expression as the
  production TypeScript failure; the pinned base revision keeps the premise
  reproducible after `main` moves.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/main
- origin_main_authority: separate direct owner instruction 2026-10-08 user request «Пупу, запуш в main хотфикс» for the verified successor of `0df36495`

## Allowed paths

- `web/src/_pages/account/ui/account-page.tsx` — preserve the validated return
  destination while supplying a prop value the receiving type accepts.
- `web/src/_pages/register/ui/register-page.tsx` — pass an explicit no-refusal
  value to the registration form when the page prop is absent.
- `web/src/features/manage-user/model/use-manage-user.ts` — inspect the cached
  own account without overriding the cache key's type with a type argument.
- `web/src/entities/account/model/account.ts` — keep a malformed account's
  visible error message in Russian when the `display_label` promise is broken.
- `web/tests/guards/rendered-language.guard.test.ts` — seed the identity-screen
  readings through the shared render harness and name any state a static pass
  cannot reach.
- `web/tests/unit/session/login-route.test.ts` — assert the complete current
  public props including the explicit unknown-refusal signal.
- `docs/program/tasks/W51-INT-HOTFIX-01.md` — this integration task and its
  pre-publication evidence.
- `.local/tasks.md` and `.local/handoff/w51-main-hotfix-2026-10-08.md` — ignored
  operator handoff for publication and host verification.
- One linear integration commit and one fast-forward update of `origin/main`
  after all required checks.

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency and lock files,
  composition roots, global styles and deployment inputs.
- All other runtime/UI paths, `origin/dev`, tags and history rewrites.

## Non-goals

- No account-flow redesign, API or schema change, dependency upgrade, or new
  release tag.
- No second publication to work around a failed gate or deployment.

## Deliverables

- A minimal account-screen type fix and a clean integration commit.
- Production web build, frontend and contract test evidence, and exact-SHA
  deployment evidence. The complete gate is waived by direct owner instruction
  for this hotfix only.

## Required tests

- `npm --prefix web run typecheck`, `npm --prefix web run build`, frontend
  lint and frontend tests succeed.
- `git diff --check`, contract tests and static PC-01 conformance succeed. The
  owner directed on 2026-10-08 that the full gate not be repeated for this
  urgent hotfix because of its cost; the earlier failed runs are not `GATE OK`
  evidence and must not be reported as such.
- Immediately before push, re-read the remote `main` ref and prove its ancestry
  to the candidate. After push, require a successful exact-SHA GitHub workflow,
  `infra/deploy/verify-deployed.sh` on the host and the public-origin probes in
  `MAIN_AUTODEPLOY_POLICY.md`.

## Integration contract

The account screen passes the same validated `next` string to `EditProfileForm`;
when no destination exists it passes `null`. The registration page passes the
same typed refusal to `RegisterForm`, with `null` when absent. No redirect or
refusal state is added or removed.
Only this integration task may publish its checked commit to `origin/main`
under the owner's direct hotfix instruction and explicit gate waiver.

## Failure/idempotency/security cases

- An absent destination keeps the current no-redirect behavior. An invalid or
  external destination remains rejected by the existing route-level validator.
- Any failed build, selected check, remote-ref recheck, workflow, host verification or
  public probe leaves the task incomplete; do not call a push a deployment.
- No credentials or host secrets are written to this task or the repository.

## Rollback / feature flag

No feature flag is needed for this type-only correction. A rollback is a newly
reviewed, fully gated forward revert commit; force-push is prohibited.

## Handoff

Report the exact candidate and workflow SHA, commands and outcomes, any limits,
and the changed-path proof in the task response. Do not commit a post-push
evidence edit, since that would trigger a second deployment.

The corrected working tree passed frontend Vitest (109 files, 1709 tests),
frontend lint, typecheck and production build, plus the 15-case task governance
suite on 2026-10-08. Contract and static PC-01 conformance passed (582 tests,
50 subtests). The complete gate has no `GATE OK` on this corrected tree: the
owner explicitly waived another full run because of its cost. Therefore
`D-138` and `D-140` remain open for this candidate; their gate-OK milestone is
not claimed.
