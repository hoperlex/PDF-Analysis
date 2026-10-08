# W52-INT-C2-ACCEPT-01 — measured-build acceptance integrated

**Date:** 2026-10-08. **Lane:**
`8cbff0e91c14516d08622fe2e73ff2b5e9eb33ea`, descending from the
read-back ACCEPT grant `092466980912e3937ca794edd37cd22917e0b53f`.
`origin/main` remained
`9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c` at review.

## 1. Files and result

The integrator fast-forwarded the clean six-path ACCEPT lane. The
automated alpha command now gives `apiBuild` a measured candidate/server
verdict while retaining the existing SHA attestation, PC-01 journey,
provider-live, refusal and human-checklist conditions. RELNOTES and
ACCEPT are both merged locally; Stage C2 implementation is complete
pending development publication.

The integration follow-up changes exactly:

```text
docs/program/tasks/W52-INT-C2-ACCEPT-01.md
docs/program/W52-INT-C2-ACCEPT-01.md
docs/program/CURRENT_STATE.md
docs/program/dispatch/W52-PLAN.md
```

## 2. Checks and results

- Exact parent `0924669` and six-path inventory match
  `W52-ACCEPT-01.md` §1. The lane and merged diffs pass
  `git diff --check`.
- On the clean lane SHA, **25 acceptance contract tests passed**;
  shell syntax, ShellCheck and Node syntax passed. On the merged tree,
  the same acceptance tests, syntax checks and **93 wave-governance / prose
  / count tests** are required before development publication. Their
  final outcome is recorded in the integrator handoff.
- `pin_sweep.py table` completed on the combined Stage-C2 tree and
  listed 17 existing catalogue/pattern/live-claim/expected-facts
  readers. No new acceptance path appeared in that output, and the
  frozen count/head facts remain unchanged.
- Full `make gate`, independent QA/judgment, live automated acceptance
  and human A01–A20 are still due under D-137–D-140.

## 3. Contracts

No API/domain contract, migration, error catalog, generated client,
product VERSION, release-note entry, loader, web UI, root lock or
`contract_version` changed. The existing machine evidence
`w48-alpha-acceptance/v1` gains an `apiBuild` phase with measured
candidate and served IDs. The root PASS now requires that phase to
PASS. The sealed surface remains API 30/37/83 with 23 error codes,
domain revision 9 / 29 identities and head `0016_release_notes`.

## 4. Risks and limits

Local HTTP tests prove the command's comparison and refusal behavior,
not the current public stand. The API build hash excludes
`Dockerfile.api`-only and `serve.py`-only changes by the W52 design;
the deployed SHA remains operator attestation until workflow and host
verification. Any blocked or failed live measurement stops release
acceptance. D-137–D-140 keep the later validation obligations.

## 5. Next integrator step

Commit this exact four-path docs follow-up after merged checks,
re-read `origin/dev`, publish only the checked fast-forward SHA there,
and read it back. The next task is a separate W52 development close or
release-validation grant from that readback. No release ledger row,
tag or `origin/main` push follows from Stage C2 code completion.

## 6. Forbidden-hotspot proof

The lane's six paths match `tasks/W52-ACCEPT-01.md` and the four
follow-up paths are granted by `tasks/W52-INT-C2-ACCEPT-01.md`.
The historical ALPHA-MANUAL file has only a forward pointer, and the
runbook's three command blocks, A01–A20 IDs, Russian UI quotes and
numbered facts were preserved. `contracts/**`, migrations, root
dependencies/locks, API runtime, generated client, composition root,
global styles, journey manifest, `origin/main`, tags and deployment
were untouched.
