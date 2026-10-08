# W51-FREEZE-01 — identity screens frozen for Stage A

**Date:** 2026-10-07. **Base:** W50's verified development close
`75dd70843b7c3a2a7451368da28376abb899cf26`. This report is part of the docs-only freeze
candidate and therefore does not name its own SHA. The integrator publishes only its clean
R-70-accepted commit to `origin/dev` and hands that exact SHA to `W51-ROUTES-01`.

## Contract set and entry

```yaml
wave_id: W51
frozen_code_base: 75dd70843b7c3a2a7451368da28376abb899cf26
domain: 1.0.0-draft.1 revision 9, 29 opaque identities
api: 27 paths / 34 operations / 77 schemas
error_catalog: 23
migration_head: 0015_accounts_roles_registration
last_full_gate_tree: d8ea61351489fcf08c7ebfe8ff90045b2127b559
last_full_gate: GATE OK, backend 3201 passed / 6 skipped; frontend 1660; foundation 35
acceptance_rule: R-70, AGENTS.md section 8
```

W50's clean `W50-INT-CLOSE` candidate passed light acceptance with literal
`LIGHT ACCEPTANCE OK`, then `origin/dev` was read back at the base above. The generated client
already contains W49's `getMe`, `updateMyProfile`, `listUsers`, `getUser`,
`listRegistrations`, `archiveUser`, `purgeUser` and `resetUserPassword` operations. No W51
contract, migration, backend or root-lock edit is authorized.

The W50 shell registers **22** real screens. W51 Stage A adds five: `/register`,
`/register/submitted`, `/admin/users`, `/admin/users/[user_uid]` and
`/admin/registrations`, yielding **27** real screen addresses. The production build's
`/_not-found` row is synthetic and is not a registry member. Stage A registers and guards
these addresses as placeholders; AUTH and the two ADMIN lanes implement them later.

## Presweep disposition and direct re-check

The planning-owned, read-only `W51-PRESWEEP.md` at `plan/roadmap-to-beta` `2b45a11` records
P-1…P-18 and re-checks P-5, P-16 and P-17 after SHELL-FRAME merged. Its planning branch
and worktree were neither edited nor merged. `W51-PLAN.md` now resolves the findings that
affect grants:

| Evidence | Freeze resolution |
| --- | --- |
| P-1 | AUTH owns the BFF's two validated `next` redirects and the password page path, so refused sign-in and forced password/profile completion can carry the destination. |
| P-2 | Remove the protected `app/admin/loading.tsx` grant; a segment Suspense boundary would change a guest's 307 into streamed 200. |
| P-3, P-4, P-5 | ROUTES owns registry, shell, home and role-gate tests pinned to the W50-only empty admin set. |
| P-6, P-7, P-10, P-16, P-17, P-18 | Stage B becomes AUTH → ADMIN-USERS → ADMIN-REQUESTS, giving shared mutation, rendered-language, census and journey files one writer at a time. Each lane tests its exact invalidated keys and rendered identity vocabularies. |
| P-8, P-9 | Existing `queryKeys.users` and `.registrations` factories stay frozen; ROUTES re-exports the two filter types from the public API barrel. |
| P-11, P-12 | The W51 journey uses an administrator account; E2E may update A09 routes/home and the A01–A20 wording as well as append A13–A20 steps. |
| P-13, P-14, P-15 | Public sign-in/registration rows are in `account` out of menu; administrator labels are fixed; user widgets reuse account role/name helpers. |

Direct verification on the accepted W50 base found additional first-day reds beyond the
presweep. `web/tests/unit/qa_w50/role-gated.test.ts` pins a live empty admin set and builds a
fixture by appending the future rows to the live registry; adding those rows would duplicate
addresses. `r66-navigation.test.ts` compares every role's live menu with the pre-admin menu.
`guest-redirects.test.ts` walks every session route but has no well-formed `user_uid` sample.
`frame.test.ts`, `return-path.test.ts` and `screen-decision.test.ts` assume every live menu
row admits an expert or `/403` names no role. `routes.test.ts` requires a builder for every
dynamic address, but `routes.ts` has no user-detail builder. These files are explicitly in
`W51-ROUTES-01`'s narrow Stage-A grant. Existing synthetic role tests remain as controls;
the live assertions move to the W51 set. The R-66 work/knowledge/system order remains pinned.

No Stage-B task is dispatched now. Each receives an exact grant and base after the preceding
lane is accepted. The W51 E2E grant excludes `conftest.py` by default; an explicitly needed
shared-fixture edit requires a full lane gate under `R-70`.

## Resource, checks and integration

`PORT_REGISTRY.md` reserves Stage A's `gate-w51routes` lane at PostgreSQL `56760`, S3
`60360/60361`, API `56860` and Next `31360`. `ss -ltn` showed no listener on these ports when
allocated. The executor checks again immediately before use, runs its own disposable stand,
and removes only its own containers, volumes and credentials on hand-back. No W51 service was
started by this docs-only freeze.

The freeze changes only `tasks/W51-FREEZE-01.md`, `tasks/W51-ROUTES-01.md`, this report,
`dispatch/W51-PLAN.md` and `dispatch/PORT_REGISTRY.md`. `git diff --check`, governance and
prose guards are required; the clean exact candidate then runs
`make light-acceptance BASE=d8ea61351489fcf08c7ebfe8ff90045b2127b559` to literal
`LIGHT ACCEPTANCE OK`. R-70 supersedes the older generic `GATE OK` wording in
`IDENTITY-WAVES.md` for this docs-only development publication. The complete gate already
passed on the last Makefile-changing W50-FIX lane; another full gate is required if this
freeze unexpectedly touches an R-70 risk path.

The integrator re-reads `origin/dev` immediately before publication, proves it is an ancestor
of the exact clean candidate, pushes without force and reads back the ref. `origin/main` and
tags remain unchanged. Stage A starts only from that verified `dev` SHA. This is no deployment
claim; `infra/deploy/verify-deployed.sh` answers the deployed-state question.

## Risks, rollback and handoff

Stage A still needs a built stand for the live PC-01 journey selected by its changed screens;
the freeze does not count a static test as browser evidence. W51's additional screen and
identity vocabularies may reveal another concrete guard pin; an executor reports an extra
path to the integrator for a written grant before editing it. The Stage-B shared-file order
is a plan commitment, not parallel ownership.

No product flag or behavior changes here. Revert the freeze commit on `dev` if its grant or
premise is false, then rebase Stage A on a corrected freeze. **New/changed contracts:** none.
**Forbidden-hotspot proof:** the freeze path diff must name only the five Markdown files above,
with no product, contract, migration, lock, composition root, global style or planning path.
