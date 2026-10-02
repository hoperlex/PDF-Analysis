# Task W48-JUDGE-X — attack the merged alpha boundary

## Outcome

An attacker/black-box report tries to make every Stage-B release instrument lie, records every
unavailable external measurement as not tested, and repairs nothing.

## Depends on

- `W48-PORTS` — completed at `81b1f2a`
- `W48-WEB` — completed at `996b546`
- `W48-LIVE` — completed at `300567a`
- `W48-GOV` — completed at `1843db5`

## Frozen inputs

- subject: `14caf886e78883ed771d81fbf463c98af727c938`
- API: 17 paths / 20 operations / 61 schemas; error catalog: 22
- migration head: `0013_norm_embeddings`
- PC-01: 3 write steps, 16 routes, 6 refusal cases, 780 x 900

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: Stage-B subject and PC-01 cardinalities

### P-01 — exact subject

- captured_at: 2026-10-02
- command: `git rev-parse HEAD`
- captured_output:
  ```text
  14caf886e78883ed771d81fbf463c98af727c938
  ```
- interpretation: all four Stage-B merge commits are ancestors of this clean local SHA; no remote
  publication or deployment is implied.

### P-02 — declared external phases

- captured_at: 2026-10-02
- command: `node -e "const m=require('./tests/e2e/pc01/journey/manifest.json'); console.log(m.write.steps.length,m.routes.length,m.refusals.cases.length,m.viewport.width,m.viewport.height)"`
- captured_output:
  ```text
  3 16 6 780 900
  ```
- interpretation: the judge must reject any acceptance evidence covering fewer phases or a
  different viewport.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/reviews/W48-JUDGE-X.md`

## Forbidden hotspots

- every other tracked path
- contracts, migrations, dependencies/locks, runtime sources and test instruments
- refs, tags, remote branches, host deployment state and secret stores

## Non-goals

- no repair
- no public-host mutation without an explicitly supplied reviewer credential and deployment SHA
- no claim that an unavailable black-box check passed
- no push, deployment or tag

## Deliverables

- exact-subject report with environment, commands/status, findings and safe reproductions
- mutations against each new WEB/LIVE/GOV guard, all restored
- explicit untested/blocked questions and release verdict

## Required tests

- missing origin, credential and SHA; unreachable origin; skipped phase; recorded provider;
  refusal finding — none may print `ALPHA ACCEPTANCE PASS`
- unknown cost/category/event/verdict values and malformed identifiers fail closed
- 200-character name and 400-character token remain contained at the declared width
- credential does not enter argv, URL, browser storage, body or report
- if a credentialed disposable stand is unavailable, state that boundary without substitution

## Integration contract

Report only. A finding is not a repair grant. The integrator may open one later bounded fix task
only after cross-examination.

## Failure/idempotency/security cases

- missing access is `BLOCKED`, never PASS
- public writes are forbidden without exact deployment evidence and authorised credentials
- scratch evidence contains synthetic data only and no secret value

## Rollback / feature flag

Not applicable: report only.

## Handoff

- changed files: the one report
- commands/results: quoted with exit status
- known limits: explicit
- integration note: cross-examine with `W48-JUDGE-Y` before repair
