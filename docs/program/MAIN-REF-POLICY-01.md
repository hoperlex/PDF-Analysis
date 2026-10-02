# MAIN-REF-POLICY-01 — completion report

## Result

**DONE.** The repository now has one explicit default: a clean gated development candidate is
published to `origin/dev`. `origin/main` is an external auto-deploy action and requires a
separate direct owner instruction for the exact candidate; no wave-close wording, integration
role, green gate or previous permission grants it implicitly.

The successfully repaired auto-deploy mechanism is recorded independently: GitHub Actions run
`36873558201`, attempt 2, deployed and verified exact SHA
`608632a52940cbff70a1e8361f241901f48182aa`.

## Changed files

- `AGENTS.md` — mandatory default-dev/direct-main rule for every coding agent;
- `docs/program/MAIN_AUTODEPLOY_POLICY.md` — operational workflow evidence, two-ref model and
  direct-instruction precondition;
- `docs/program/VERSION_FIXATION.md` — current owner ruling above the retained historical record;
- `docs/program/CURRENT_STATE.md` — live W48 publication orientation;
- `docs/program/dispatch/W48-PLAN.md` — dev-first freeze/closeout and separately authorised
  deployment sequence;
- `docs/program/dispatch/W49-PLAN.md` — queued successor cannot inherit implicit main authority;
- `docs/program/tasks/MAIN-AUTODEPLOY-02.md` — successful attempt-2 handoff evidence;
- `docs/program/tasks/MAIN-REF-POLICY-01.md` — task contract;
- `docs/program/MAIN-REF-POLICY-01.md` — this report.

## Checks performed

- public GitHub API: run `36873558201`, attempt 2, status `completed`, conclusion `success`, exact
  head SHA `608632a`; both `Prepare SSH` and `Deploy and verify exact commit` concluded `success`;
- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — **47 passed**;
- policy/ref wording audit over `AGENTS.md`, `MAIN_AUTODEPLOY_POLICY.md`,
  `VERSION_FIXATION.md`, W48 and W49 plans — development and deployment paths are separate;
- `git diff --check` — clean.

## Contracts

No API, domain, analysis, comparison, event, error-catalog or migration contract changed. The
frozen surface remains API 17 paths / 20 operations / 61 schemas, domain candidate revision 8
with 27 opaque identities, 22 error codes and migration head `0013_norm_embeddings`.

## Risks and known limitations

- `origin/dev` does not deploy the public alpha. A dev-only candidate is intentionally not public
  release evidence.
- A release tag that requires deployed/manual acceptance remains blocked until the owner directly
  authorises the exact `origin/main` publication and the deployment/manual sequence passes.
- The old historical reports retain their original publication decisions; the current ruling is
  an addendum and policy supersession, not a rewrite of evidence.

## Integrator instruction

Run `W48-FREEZE-01`, publish its docs-only dispatch tip to `origin/dev`, and cut Stage-A work from
that tip. Do not update `origin/main`. If the owner later directly instructs publication of an
exact candidate to `main`, open a separately authorised integration action and execute every
step of `MAIN_AUTODEPLOY_POLICY.md`.

## Forbidden-hotspot proof

The staged-path audit contains only the nine documentation paths listed above. No workflow,
deploy script/composition, contract, migration, dependency/lock, runtime/UI, global style, host,
secret, tag or Git ref is changed by this task.
