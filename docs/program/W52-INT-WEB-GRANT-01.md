# W52-INT-WEB-GRANT-01 — account-menu action grant

## 1. Changed files and result

This docs-only integration correction changes
`tasks/W52-INT-WEB-GRANT-01.md`, `tasks/W52-RELEASES-WEB.md`,
this report and `dispatch/W52-PLAN.md`. It grants WEB one generic
action variant in `web/src/shared/ui/menu.tsx` and four existing tests
that pin the account menu's three-item shape. No WEB code is changed here.

## 2. Checks

The current `origin/dev` base is `fa3975a`; the menu source and test
assertions were read before the correction. Focused governance/prose and
`git diff --check` are required on the docs follow-up before publication.
The full gate is D-140, not a claim of this grant.

## 3. Contracts

No API/domain contract, migration, error code, generated client or
`contract_version` changes. The UI action is local and does not add a
route or screen-registry member.

## 4. Risks and known limits

WEB must preserve the existing menu keyboard path and sign-out POST.
This grant alone does not implement or test the panel. D-137–D-140
remain open.

## 5. Integrator instruction

Publish this checked docs-only fast-forward to `origin/dev`, read back
its SHA, then start WEB from that exact grant. Integrate WEB before
TRANSLATE. Do not touch `origin/main`.

## 6. Forbidden-hotspot proof

The follow-up is four docs paths only. No product code, tests,
contract, migration, dependency, lock, composition root, global style,
tag or deployed stand is touched.
