# Task W56A-INT-PROBE-TOOL-CORR-01 — refuse degenerate gateway evidence

## Outcome

The W56a probe tool rejects placeholder model names and zero-token or
zero-cost answers before MODEL-PIN can treat them as identity evidence.
The correction is published on `origin/dev` with focused checks only.

## Depends on

- `W56A-INT-PROBE-TOOL-01` — complete at `1a825fea`;
- `W56A-INT-MODEL-PIN-GRANT-01` — complete at `7fd152c0`.

## Frozen inputs

- base `origin/dev=7fd152c0f1b2445cd1a5381cb9c3b579aa94f9e9`;
- API/error/analysis SHA-256 `fad81bc0` / `89e155fc` / `bd1e5b91`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; `R-29`, `R-133`, `R-135`, `R-136`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: published probe code accepts positive-looking response names but
  does not yet reject `unknown` or a one-choice answer with zero usage/cost.

### P-01 — published base and lock

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && sha256sum docs/program/P02_LOCK.json`
- captured_output:
  ```text
  7fd152c0f1b2445cd1a5381cb9c3b579aa94f9e9
  7fd152c0f1b2445cd1a5381cb9c3b579aa94f9e9
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: this is the correction base and unchanged model lock;
  it does not prove a gateway model.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/W56A-PROBE-TOOL-PREP-01.md` (read-only handoff)
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tools/provider/identity_probe.py` (name and usage refusal only);
- `tests/contract/provider/test_identity_probe.py` (targeted cases);
- `docs/program/tasks/W56A-MODEL-PIN-01.md` (base/dependency/refusal text);
- `docs/program/CURRENT_STATE.md` (top test count only);
- this task and `docs/program/W56A-INT-PROBE-TOOL-CORR-01.md`;
- normal fast-forward of `origin/dev` from the frozen predecessor.

## Forbidden hotspots

- `P02_LOCK.json`, spend ledger, credentials, gateway configuration,
  contracts, migrations, root dependencies/locks, runtime adapter/UI,
  composition root, global styles, historical reports, `VERSION`,
  `origin/main`, tags and stand state.

## Non-goals

- No paid gateway call, model pin, PROVIDER grant, full local gate,
  manual acceptance, release or deployment.

## Deliverables

- refuse nonidentities `unknown`, `none`, `null`, `stub` and `model` in
  addition to the existing proxy/default/auto stubs;
- require positive prompt and completion counts and reported cost for a
  nonempty answer, before rate matching;
- focused regression tests and refreshed exact MODEL-PIN instruction;
- integration report and exact dev read-back.

## Required tests

- focused provider tests and contract-prose checks;
- Python compilation, direct task-governance check, `git diff --check`
  and exact allowed-path proof;
- remote predecessor comparison, normal fast-forward push, exact remote
  read-back. No full local gate.

## Integration contract

MODEL-PIN consumes this corrected tool from the new development tip and
still needs the two distinct gateway pairs and ledger projection. A
nonidentity or zero-charge echo is STOP. The cheaper tier remains unproven.

## Failure/idempotency/security cases

- Any fail remains a sanitized refusal; no answer text, URL or token is
  emitted. Timeout billing remains uncertain and is never auto-retried.
- If remote dev, lock bytes or contracts move, stop for a fresh freeze;
  never force-push.

## Rollback / feature flag

Revert before MODEL-PIN uses the tool, or correct forward afterward. No
runtime feature flag, schema or data rollback.

## Handoff

- changed files: the six Allowed paths;
- checks/results, ref, limitations: integration report;
- next: execute MODEL-PIN only after sanctioned access; no `origin/main`.
