# Task W48-FIX-B — close the upheld Stage-B guard false greens

## Outcome

The three cross-upheld Stage-B false greens become red for their intended reason:

- `X-01`: a live-provider dependency outage can never produce overall acceptance `PASS`, even
  when the browser journey itself exits zero after observing a `partial` terminal;
- `X-02`: root preflight accepts `/projects` only on the declared origin, never a suffix-equal
  path on another scheme, host or effective port;
- `Y-01`: every task file created after governance activation is enumerated automatically and
  validated by `governance_findings()`.

This repair does not close or redesign the durable provider/blob findings `A-01` and `A-02`, and
does not make W48 releasable by itself.

## Depends on

- `W48-JUDGE-X` — completed and cross-examined at `349e824`
- `W48-JUDGE-Y` — completed and cross-examined at `9a31264`
- Stage-B subject — `14caf886e78883ed771d81fbf463c98af727c938`

## Frozen inputs

- Stage-B subject: `14caf886e78883ed771d81fbf463c98af727c938`
- acceptance evidence schema: `w48-alpha-acceptance/v1`
- PC-01: 3 write steps, 16 routes, 6 refusal cases, viewport 780 x 900
- governance activation baseline: the 85 task paths present at the Stage-B subject
- API: 17 paths / 20 operations / 61 schemas; error catalog: 22
- migration head: `0013_norm_embeddings`

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/contract/program/test_wave_governance.py
- enumerator_owner: W48-FIX-B
- totality_query: `find docs/program/tasks -maxdepth 1 -type f -name '*.md' -print`

## Captured premise evidence

- premise: the governance activation subject contains 85 task paths

### P-01 — activation inventory

- captured_at: 2026-10-02
- command: `git ls-tree -r --name-only 14caf886e78883ed771d81fbf463c98af727c938 docs/program/tasks | wc -l`
- captured_output:
  ```text
  85
  ```
- interpretation: paths present at governance delivery are the explicit grandfathered baseline;
  every later filesystem member is validated without editing an include list.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/e2e/pc01/journey/verify-acceptance.mjs`
- `scripts/manual-alpha-check.sh`
- `tests/contract/test_alpha_acceptance_command.py`
- `tests/contract/program/test_wave_governance.py`
- `docs/program/W48-FIX-B.md`

## Forbidden hotspots

- contracts, generated clients, error catalog and `db/migrations/**`
- runtime/business source, persistence/storage implementation and composition roots
- root dependency/lock files, frontend dependencies/locks, workflows and global styles
- task briefs, immutable judge/audit reports, `CURRENT_STATE.md` and `DEBT_REGISTER.md`
- deployment state, credentials, public host mutations, refs, tags and remote branches

## Non-goals

- no repair or reinterpretation of `A-01`, `A-02` or `A-03`
- no live alpha run or public write
- no acceptance schema/version change and no new dependency
- no retrofit of the 85 pre-activation task documents
- no push to `origin/dev` or `origin/main`, deployment or tag

## Deliverables

- verifier verdict derived from the complete required-phase outcomes, with dependency outage
  blocking regardless of process exit
- same-origin `/projects` redirect validation with normalised scheme/host/effective port
- governance enumerator over all task files absent from the exact activation baseline
- red/green mutations for each upheld finding and neighbouring positive controls
- completion report `docs/program/W48-FIX-B.md`

## Required tests

- synthetic `partial + live + dependency_unavailable + journeyExit=0` evidence exits `2`, records
  `providerLive=BLOCKED`, overall `BLOCKED`, and never prints PASS
- every overall PASS fixture has PASS for identity, sign-in, write cardinality, route cardinality,
  width, provider-live and refusal phases
- relative `/projects` and absolute same-origin `/projects` pass; changed scheme, host, explicit
  non-default port and user-info fail; default-port normalisation is tested
- a new real task file missing all governance sections fails with its path and stable rule IDs;
  a compliant new task passes; baseline files are excluded only by exact activation inventory
- `/root/projects/PDF-Analysis/.venv/bin/python -m pytest
  tests/contract/test_alpha_acceptance_command.py
  tests/e2e/test_pc01_journey_conformance.py
  tests/contract/program/test_wave_governance.py -q`
- `bash -n scripts/manual-alpha-check.sh`; `git diff --check`; allowed-path-only diff

## Integration contract

The verifier's root verdict is a projection of every required phase: PASS iff all are PASS,
BLOCKED iff no phase failed and at least one is BLOCKED, otherwise FAIL. Process exits and
findings feed those phases but cannot override a BLOCKED phase into PASS.

Redirect validation resolves a relative `Location` against the declared origin, rejects user-info,
normalises host case and the default HTTP/HTTPS ports, requires the same origin tuple and the exact
`/projects` path. It does not follow or trust a different origin.

Governance activation is fixed at the exact Stage-B subject that introduced the rules. The
baseline is derived from that Git tree; the live set comes from the task directory. Therefore a
new extension-independent task member is visible without editing the test, while historical files
remain byte-untouched.

## Failure/idempotency/security cases

- missing/malformed phase evidence remains FAIL, never BLOCKED or PASS
- dependency outage remains BLOCKED whether the journey exits zero or non-zero
- URL parsing ambiguity, credentials in a URL, foreign origin and non-`/projects` path fail closed
- missing Git activation subject or unreadable task file fails the governance test loudly
- repeated focused runs create no repository file or external side effect
- no real credential, cookie, provider body or customer data enters evidence

## Rollback / feature flag

Guard/acceptance-instrument repair only. Rollback is a revert of the implementation commit; no
feature flag, data migration or host operation applies.

## Handoff

- changed files, checks and mutations are recorded in `docs/program/W48-FIX-B.md`
- contracts/migrations/dependencies remain unchanged
- known blockers after completion: `A-01`, `A-02`; `A-03` remains architecture debt
- integrator reruns affected scopes before deciding the separate durable-state task; no remote
  publication authority is granted
