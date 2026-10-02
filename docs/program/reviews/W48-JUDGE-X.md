# W48-JUDGE-X — black-box attack on the Stage-B acceptance boundary

## 1. Subject and verdict

- **Subject:** `14caf886e78883ed771d81fbf463c98af727c938`, the clean local merge of
  `W48-PORTS`, `W48-WEB`, `W48-LIVE` and `W48-GOV`.
- **Frozen surface:** API 17 paths / 20 operations / 61 schemas; error catalog 22;
  migration head `0013_norm_embeddings`.
- **PC-01:** 3 write steps, 16 cold routes, 6 refusal cases, viewport 780 x 900.
- **Date:** 2026-10-02.

**Verdict: REJECT.** The Stage-B acceptance verifier can print
`acceptance verdict: PASS` while its own `providerLive` phase is `BLOCKED` (`X-01`). The HTTP
preflight also reports `PREFLIGHT OK` when the application root redirects to an attacker-controlled
origin whose path happens to end in `/projects` (`X-02`). Both are fresh, restored, synthetic
reproductions on the exact subject. No public credential, public write, provider call, deployment,
tag or remote ref was touched.

The WEB changes fail closed for the four attacked transport values and carry the declared long
strings under the containment classes. Missing input, an unreachable origin, skipped/recorded
execution and a refusal finding all fail or block in the committed tests. Those green results do
not override the two false greens above.

## 2. Environment and method

The review ran on the exact subject in
`/root/projects/PDF-Analysis/.local/worktrees/w48-judge-x`. The checkout began clean and every
mutation was outside it under `/tmp`, except temporary untracked runtime links used for focused
tests; those links were removed. Credentials used by stubs were synthetic strings only and do
not authenticate anywhere.

No live alpha credential or deployment SHA was supplied to this task. Therefore the public-host
journey, direct-API denial with an authenticated browser session, session revocation and the
kill/restart cases are explicitly **not tested**, not replaced by a local PASS.

## 3. Findings

### X-01 — dependency outage is recorded as `BLOCKED` but the whole verdict is `PASS`

**Class:** release-blocking false green; acceptance completeness.

`tests/e2e/pc01/journey/verify-acceptance.mjs:164-169` changes the whole verdict to `BLOCKED`
only when `dependencyUnavailable && journeyExit !== 0`. The journey accepts `partial` as a
terminal, so a successful browser process can observe a real live-provider dependency outage,
exit `0`, and avoid both the BLOCKED branch and the findings list. The phase builder still records
`providerLive.outcome: BLOCKED` at lines 211-218; the final verdict contradicts its own phase.

A disposable evidence pair declared all 3/3 writes, all 16/16 routes, width 780, live provider,
6/6 refusal cases and zero process failures. Its final run response was:

```json
{
  "state": "partial",
  "provider_mode": "live",
  "terminal_reason": "dependency_unavailable",
  "stages": [{"stage_id": "text_analysis", "error_code": "dependency_unavailable"}]
}
```

The verifier exited `0` and printed:

```text
acceptance evidence: /tmp/w48-judge-x-partial-evidence/verdict.json
acceptance verdict: PASS
```

Yet that same `verdict.json` contains:

```text
phases.providerLive.outcome = BLOCKED
processes.journeyExit = 0
verdict = PASS
```

**Consequence.** A reachable deployment with a real but unavailable provider can be promoted by
the very release command intended to keep dependency outage out of PASS.

**Repair boundary.** Overall PASS must be possible only when every required phase is PASS.
`dependencyUnavailable` must yield BLOCKED regardless of browser-process exit, with a committed
mutation for the `partial`/exit-0 shape above.

### X-02 — `/projects` on a foreign origin passes the root preflight

**Class:** preflight false green; origin integrity.

`scripts/manual-alpha-check.sh:244-246` extracts `Location` and accepts any value matching
`*/projects`. It does not require a relative location or the same scheme/host/port as `--origin`.

A fake `curl` returned:

- root: `307 Location: https://attacker.invalid/projects`;
- `/login`: `200`;
- unauthenticated `/api/v1/openapi.json`: `401`.

Against declared origin `https://alpha.example.test`, `--preflight-only` exited `0` and wrote:

```text
| HTTP-root | PASS | 307 -> https://attacker.invalid/projects |
| HTTP-login | PASS | GET /login -> 200 |
| HTTP-auth-boundary | PASS | unauthenticated GET /api/v1/openapi.json -> 401 |
```

The command printed `PREFLIGHT OK` even though its root navigation crossed the declared trust
boundary.

**Consequence.** The root-origin check can certify a redirect controlled by a different host.
The later automated journey normally gives this another chance to fail, but preflight-only is a
published command in its own right and its positive verdict is false.

**Repair boundary.** Accept `/projects`, a relative equivalent, or an absolute URL whose
normalised origin equals `--origin`; independently reject scheme, host and effective-port changes.

## 4. Attacks that correctly failed closed

### Command and verifier completeness

The committed command/conformance suites cover missing origin, candidate/deployed SHA and both
credentials; skipped and recorded journeys; dependency outage; malformed phase/cardinality
evidence; and refusal findings:

```sh
/root/projects/PDF-Analysis/.venv/bin/python -m pytest \
  tests/contract/test_alpha_acceptance_command.py \
  tests/e2e/test_pc01_journey_conformance.py -q
```

Result: `82 passed in 8.08s`. The dependency fixture in that suite exits non-zero, but it does not
cover `partial + dependency_unavailable + journeyExit=0`, which is why `X-01` remains green.

An independent refusal mutation put one finding into the third refusal record and supplied
`refusalsExit=1`. The verifier exited `1`, printed `acceptance verdict: FAIL`, named both the
finding and the process exit, and never printed PASS.

An unreachable `http://127.0.0.1:9` origin with explicit synthetic credentials and exact matching
SHAs exited `2`. Its report records all three HTTP checks as BLOCKED and contains no PASS verdict.

### WEB fail-closed and containment boundary

The focused Stage-B screen set passed:

```text
8 test files, 111 tests passed
```

It includes unknown dashboard cost basis; unknown knowledge-base `current_verdict`, `category`,
`event_type` and event verdict; a 200-character unbroken project name; a 400-character unbroken
comment; and the shared screen renderer consumers. The relevant assertions require typed faults
rather than raw/blank fallbacks and require the long values to sit under the selectors whose CSS
sets `min-width: 0` and `overflow-wrap: anywhere`.

This is deterministic markup/CSS evidence. Pixel width at 780 x 900 on a credentialed deployed
browser remains untested here.

### Credential exposure boundary

The release command takes credentials only from `E2E_PC01_LOGIN` and
`E2E_PC01_PASSWORD`; the committed suite asserts the synthetic password is absent from the
report. The browser session manifest carries no credential action, and the session tests redact
form bodies and record cookie attributes rather than cookie values. No credential value appeared
in this report, the synthetic evidence reports or a URL.

Process-table inspection of a real credentialed run and browser-storage inspection on the public
host were unavailable; they are not claimed from static evidence.

## 5. Command/result ledger

| command / instrument | exit and result |
|---|---|
| `git rev-parse HEAD` | `14caf886e78883ed771d81fbf463c98af727c938` |
| acceptance command + PC-01 conformance pytest | `0`; 82 passed |
| eight focused WEB files | `0`; 111 passed |
| synthetic partial dependency evidence | `0`; verifier printed PASS while provider phase was BLOCKED — `X-01` |
| synthetic refusal finding | `1`; FAIL, finding and process exit named |
| explicit unreachable origin | `2`; three HTTP checks BLOCKED; no PASS |
| foreign-origin root redirect under `--preflight-only` | `0`; HTTP-root PASS and `PREFLIGHT OK` — `X-02` |

An initial focused frontend invocation ran from the repository root and therefore could not
resolve the web `@/` alias. The complete rerun above ran from `web/` with the same locked
`node_modules` as the integrated baseline and passed all 111 tests. A first Python rerun had an
untracked `.venv` link and correctly failed the clean-checkout assertion; the link was removed
and the complete 82-test rerun passed. Neither setup failure is used as product evidence.

## 6. Untested questions

1. Credentialed public journey: 3/3 writes, 16/16 cold routes, 780 x 900 layout, 6/6 refusals and
   live-provider success against the exact deployed SHA.
2. Authenticated browser attempting the direct API origin, credential revocation and cookie
   behaviour across process restart.
3. Kill after provider acceptance and kill after object publication; these require owned
   disposable provider/S3/DB infrastructure and are Judge Y's durable-state blockers.
4. Online dependency/container vulnerability and licence databases.

## 7. Integration, rollback and final diff

The integrator must uphold `X-01` and `X-02` unless cross-examination falsifies their exact
reproductions. Any repair needs a separately bounded task; this report grants no source path.
Even after those repairs, `W48-AUDIT` findings `A-01` and `A-02` remain release blockers.

Rollback is deletion/revert of this report. No contract, migration, dependency/lock, runtime,
test, composition root, global style, deployment state, ref or tag changed.

At report commit time the subject diff must contain exactly:

```text
docs/program/reviews/W48-JUDGE-X.md
```

## 8. Cross-examination

Judge X read `W48-JUDGE-Y` at report commit `59c58af` and repeated its decisive source query.
The following rulings are final:

- **`Y-01` upheld.** The governance module contains no task-directory enumerator and no call that
  applies `governance_findings()` to a repository task. Its ten tests operate on the template,
  embedded fixture strings and specifically named historical files. This independently explains
  why Y's real untracked `W49-*` mutation stayed green. The repair must own an explicit task-set
  boundary; merely adding a fifth embedded invalid string would preserve the false green.
- **`A-01` upheld.** X's acceptance finding does not weaken it. `X-01` concerns classification
  after a browser observed a terminal. `A-01` is the earlier kill interval between external
  provider effect and durable provenance; the acceptance verifier cannot recover evidence that
  never committed.
- **`A-02` upheld.** The object publication/DB commit order is explicit and no analysis-side
  metadata/outbox/orphan owner was found. X did not run Y's requested destructive fault injection,
  so the static finding stands with the same stated test debt.
- **`A-03` upheld as debt, not promoted to a new Stage-B regression.** The minimum sixteen sites
  predate these runtime lanes and need the owner ruling Y names.

One qualification is retained: Y's judge-worktree D-74 database command is not behavioural
evidence because its configured listener was absent. Its source trace and the completed PORTS
lane's isolated `20 passed` result are sufficient to uphold the narrow seam; the failed rerun is
correctly disclosed rather than counted.

Cross-verdict: neither Y's finding nor its three upheld audit rows is falsified. The repair slot
may combine `X-01`, `X-02` and `Y-01` only because all three are guard/acceptance false greens with
small disjoint paths. It must not absorb `A-01`, `A-02` or `A-03`.
