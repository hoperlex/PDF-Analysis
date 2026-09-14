# Checkpoint registry

## Prototype checkpoints

These approval records govern the prototype-first route and do not move or replace any
CP tag. PC-01 carries no tag: it is a product checkpoint, and CP-00 remains unratified on its
own line, which this record neither advances nor disturbs.

| ID | Tag | Entry requirement | Status |
|---|---|---|---|
| FF-01 | none | owner accepts `PROTOTYPE_FOUNDATION_FREEZE.md` | **accepted 2026-09-09**; exact `FF-01 ACCEPTED` record in freeze; `P1-INT-00` unlocked |
| PF-01 | none | accepted P1 providers, convergence suite and independent integration review | planned; `P1-INT-01` is the sole status writer |
| PC-01 | none | ten criteria of `PROTOTYPE_PROFILE.md` §8, certified by a session that authored none of the slices | **accepted 2026-09-14** at `6d3c0f3`; live run found 3 of 3 seeded issues and flagged 0 of 6 controls; two criterion-10 failures are not inducible through the twelve operations and are named in `artifacts/checkpoints/PC-01/report.json` |

## Historical CP checkpoints

| CP | Tag | Entry requirement | Manual runbook | Status |
|---|---|---|---|---|
| CP-00 | `v0.0.1-architecture` | S00 complete | `manual-tests/CP-00_architecture.md` | **blocked** — acceptance round eleven is open and both streams are owed; the round-ten ratification is void and its tag superseded; not ratified, not tagged in the superseding series; see `ratification_blocked` |
| CP-01 | `v0.1.0-foundation` | reproducible toolchain/local services | `manual-tests/CP-01_foundation.md` | planned |
| CP-02 | `v0.2.0-walking-skeleton` | fake E2E route | `manual-tests/CP-02_walking_skeleton.md` | planned |
| CP-03 | `v0.3.0-audit-alpha` | real stage/evidence | `manual-tests/CP-03_audit_alpha.md` | planned |
| CP-04 | `v0.4.0-audit-beta` | core audit pipeline | `manual-tests/CP-04_audit_beta.md` | planned |
| CP-05 | `v0.5.0-expert` | decisions/KB | `manual-tests/CP-05_expert.md` | planned |
| CP-06 | `v0.6.0-comparison-core` | deterministic compare | `manual-tests/CP-06_comparison_core.md` | planned |
| CP-07 | `v0.7.0-comparison-advanced` | AI/graphic layers | `manual-tests/CP-07_comparison_advanced.md` | planned |
| CP-08 | `v0.8.0-distributed` | remote worker recovery | `manual-tests/CP-08_distributed.md` | planned |
| CP-09 | `v0.9.0-hardening` | production gates | `manual-tests/CP-09_hardening.md` | planned |
| CP-10 | `v1.0.0` | release acceptance | `manual-tests/CP-10_release.md` | planned |

## CP-00 — round accounting and supersession

Ten acceptance rounds are in `artifacts/checkpoints/CP-00/manifest.json`; the tenth is
accepted and is the round the status row above cites. **Acceptance round eleven is owed and
is not yet opened.**

CP-00 was ratified on round ten at `39a3a6430bd97c38cb20bafc793fc9d077d0df8e`, and the
annotated tag `v0.0.0-architecture` points there. The tag is **local and unpublished**, and
it is never moved, re-pointed or deleted.

On 2026-09-07 the repository owner decided a formal superseding checkpoint
(`docs/program/EXECUTION_PLAN.md` §3.3–§3.4). The recovery work committed after the
ratification lies outside acceptance round ten's post-freeze delta ceiling, so round ten
authorises the tree it judged and no later one. The successor is tagged
`v0.0.1-architecture`, cut by `W0-INT-03` on the commit round eleven accepts. Until it
exists, this row states CP-00's terminal state as ratified on round ten, which is what the
manifest derives and what is true of `39a3a643`.

Corrections to the CP-00 evidence bundle — every claim found false or unsupported, with the
quote, the location, what is true and how it was measured — are in
`artifacts/checkpoints/CP-00/erratum.md`.

## Evidence folder convention (created during development)

```text
artifacts/checkpoints/CP-04/
  checkpoint-report.md
  contract-manifest.yaml
  automated-summary.txt
  manual-test-report.md
  migration-head.txt
  build-info.json
  known-risks.md
  restore-or-rollback-note.md
```

Не коммитить production payloads/screenshots with sensitive data. For committed evidence use synthetic/anonymized artifacts; protected CI/artifact store can hold restricted evidence according to retention policy.
