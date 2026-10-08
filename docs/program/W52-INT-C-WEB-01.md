# W52-INT-C-WEB-01 — release web accepted, TRANSLATE next

**Date:** 2026-10-08. **WEB candidate:**
`93bd4da8d047d0717bd032221bb7255c340e8dea`, the direct child of
the read-back WEB grant `ffcf0ac0fe42ab8539cca9c33ee71c334f4272e0`.
At review, `origin/dev` was `ffcf0ac` and `origin/main` was
`9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`.

## 1. Changed files and acceptance

The integrator checked the exact 36-path WEB diff against its published
grant and fast-forwarded it into clean `integration/w51`. It contains
the account-menu history panel, release-query hooks and typed presentation,
session-protected web-build route, build-ID image input, banner and
server-selected What's New host, inventory updates, tests and lane report.
The prior `W52-INT-WEB-GRANT-01` correction covers the generic menu action
and four affected historical menu tests. No new grant correction was needed.

This integration follow-up changes exactly:

```text
docs/program/tasks/W52-INT-C-WEB-01.md
docs/program/W52-INT-C-WEB-01.md
docs/program/CURRENT_STATE.md
docs/program/dispatch/W52-PLAN.md
docs/program/tasks/W52-TRANSLATE-01.md
```

## 2. Checks and results

- Candidate parent equaled the published grant; all 36 changed paths
  matched `W52-RELEASES-WEB.md` §1 and `git diff --check` passed.
  The merged candidate is exactly the lane commit plus this docs-only
  follow-up.
- On the merged tree, release, contrast, language, credential, cache-key
  and invalidation checks: **129 passed**. The initial unprivileged run
  could not spawn the query-key fixture's `tsc`; the permitted rerun
  passed all 129.
- Journey conformance, wave governance and API prose/count checks:
  **175 passed**. An initial governance run found two malformed metadata
  fields in this new integration task; they were corrected before the
  final 175-pass run.
- `npm --prefix web run api:verify`: 37 operations and the sealed
  contract digest. Frontend lint and typecheck passed.
- The WEB lane's full 1726-pass frontend suite and final real image
  build/parity check are in `W52-RELEASES-WEB.md`; no product code changed
  after that lane commit. No full `make gate`, QA or live acceptance is
  claimed; D-137–D-140 retain those obligations.

## 3. Contracts

No API/domain contract, generated client, error catalog, migration head or
`contract_version` changed. The frozen surface remains 30 paths /
37 operations / 83 schemas, 23 error codes, domain revision 9 /
29 identities and head `0016_release_notes`. The internal
`GET /bff/version` response and `releases` query-key namespace are
documented in the WEB lane report.

## 4. Risks and known limits

The 780-pixel live-browser panel check is still unrun because this host's
snap Firefox could not enter its mount namespace; D-137–D-140 own built
stand and browser acceptance. `W52-TRANSLATE-01` remains Stage C's last
implementation lane. Stage C2 grants, release-note prose judgment, exact
candidate full gate and release verdict remain open. No tag or
`origin/main` authority exists.

## 5. Integrator instruction

Commit the five docs paths, re-read `origin/dev`, then push only the
proved fast-forward of the clean checked integration SHA to
`origin/dev` and read back that SHA. Start TRANSLATE only from the
read-back SHA. Do not push `origin/main`.

## 6. Forbidden-hotspot proof

`git diff --name-only ffcf0ac..93bd4da` lists exactly the 36 paths in
`W52-RELEASES-WEB.md` §1, all granted by its task plus the earlier
`W52-INT-WEB-GRANT-01` correction. This follow-up is confined to the
five documentation paths in §1. It touches no `contracts/**`,
migration, root dependency/lock, generated client, composition root,
global style, unrelated test, `origin/main`, tag or deployed stand.
No checkpoint was created.
