# Task W56A-INT-MODEL-PIN-GRANT-01 — publish exact MODEL-PIN grant

## Outcome

`origin/dev` contains an executable `W56A-MODEL-PIN-01` task definition with
the verified probe tool, four-call acceptance rule, spend bound and sole
lock ownership. The gateway result remains pending.

## Depends on

- `W56A-INT-PROBE-TOOL-01` — complete at `1a825fea`.

## Frozen inputs

- base `origin/dev=1a825fea25f1ea5413c213f4cedfb53e88c12e3e`;
- API/error/analysis contract SHA-256 `fad81bc0` / `89e155fc` / `bd1e5b91`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; R-29/R-133/R-136 and the failed
  `W56A-PROBE-01` remain binding.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the probe tool is published on dev and the lock remains unpinned.

### P-01 — development base and lock

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && sha256sum docs/program/P02_LOCK.json`
- captured_output:
  ```text
  1a825fea25f1ea5413c213f4cedfb53e88c12e3e
  1a825fea25f1ea5413c213f4cedfb53e88c12e3e
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: the code base matches dev and the lock is unchanged;
  neither gateway has current identity evidence.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/W56A-PROBE-01.md` (failed, read-only)
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-MODEL-PIN-01.md` (new grant only);
- this task and `docs/program/W56A-INT-MODEL-PIN-GRANT-01.md`;
- normal fast-forward of `origin/dev` from the frozen predecessor.

## Forbidden hotspots

- `P02_LOCK.json`, spend ledger, live probe report, contracts, migrations,
  root dependencies/locks, application and web code, composition root,
  global styles, deployment configuration, credentials, `CURRENT_STATE.md`,
  `VERSION`, `origin/main`, tags and stand state.

## Non-goals

- No gateway call, spend, identity verdict, PROVIDER grant, full local gate,
  manual acceptance, release or deployment.

## Deliverables

- exact MODEL-PIN task with completed dependencies, frozen pins,
  two-gateway acceptance rule, allowed paths and refusal cases;
- integration report and exact dev read-back.

## Required tests

- executable governance check for both new task files;
- focused contract-prose tests, `git diff --check`, exact three-path diff;
- remote dev equals predecessor before normal fast-forward, then exact
  read-back equals the integration SHA. No full local gate.

## Integration contract

`W56A-MODEL-PIN-01` may execute from the documentation-only dispatch tip
only after sanctioned authenticated access to two distinct gateways is
available. It alone may write `P02_LOCK.json`, and only after both explicit
and default probes pass. A failed or absent signal retains the block on
PROVIDER and live recordings.

## Failure/idempotency/security cases

- Changed remote ref or pin bytes stop publication and require refresh.
- No historical password is recovered from logs; automatic approval review
  rejected that credential source. No URL, token or response body enters Git.
- Re-running a paid probe is new spend under R-29, never an automatic retry.

## Rollback / feature flag

Documentation only; revert the three files before task execution. No
runtime feature flag or data rollback.

## Handoff

- changed files: the three Allowed document paths;
- checks/results, ref, limitations: the integration report;
- next: wait for sanctioned gateway access, then execute MODEL-PIN; no
  claim of beta or `origin/main` publication.
