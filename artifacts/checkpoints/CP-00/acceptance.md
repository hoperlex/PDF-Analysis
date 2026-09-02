# CP-00 acceptance record

Three rounds ran. Rounds one and two returned `FAIL` from both streams; round three
returned `PASS` from both. Every blocker across all three sat in integrator-owned
metadata, gate text or state documents. None was a contract, fixture, schema or test
defect: both streams confirmed the four reviewed families byte-identical to
`reviewed_candidate_commit` in every round, which is what carried the `W0-QA-01`
`ACCEPT` across two rebuilds without re-running QA.

## Rounds

| Round | Automated | Manual | Candidate digest (prefix) |
|---|---|---|---|
| 1 | FAIL — 5 blockers | FAIL — MT00-01 | `0d6641718e78afc3` |
| 2 | FAIL — 4 blockers | FAIL — MT00-01 | `7170ff5bf6734947` |
| 3 | **PASS** | **PASS** — 6/6 | recorded in the manifest |

## What the failures were about

Rounds one and two failed on the same axis: the package could not identify its own
candidate. The first attempt promised the commit SHA was recorded in `CURRENT_STATE`
and did not record it. The second reworded the pointer while still recording nothing,
so the manifest cited `CURRENT_STATE` and `CURRENT_STATE` cited the manifest.

The round-two auditor found the deeper reason the substitute did not work:
`artifact_manifest_sha256` is identical across every rebuild that leaves the reviewed
families untouched — by construction, because that invariance is exactly what carries
the QA `ACCEPT` forward. It certifies; it cannot identify. A commit also cannot name
its own hash. The answer was to identify by content instead: `candidate_digest` over
the tracked tree.

The round-three manual tester then found a blind spot in that fix and produced the
counterexample: two commits differing only in the manifest shared one digest, which is
the exact shape a fourth rebuild fixing only manifest prose would have had. The
manifest is now included in its own digest with the field blanked, and the recipes
name the raw digest bytes rather than leaving the encoding to be inferred.

## Round-three results

**Automated** — validator standalone `PASS`; 96 tests green; 44 gate executions across
six task files, extracted programmatically and run verbatim, all exit 0; both digests
reproduced on a fresh clone; three allowed-path deviations found and matched exactly
to the three named in the recorded wave exception, no fourth; 0 broken links across
146 markdown files; `main` confirmed an ancestor of `integration/W0.3`, so the planned
fast-forward is genuine.

**Manual** — all six cases pass. The candidate was identified from the package alone,
without being told the SHA, and the manifest's record of the failed second round was
verified from inside the package. No unresolved decision is silently defaulted: a
numeric sweep for TTL, retention, lease, heartbeat, grace, backoff and retry-budget
values across contracts and fixtures returns nothing.

## Open at ratification, by decision and not by omission

`U-04` open with its own deadlines — tenant/IdP before `W2-C-01`, TTL and legal hold
before `W9-C-01`. `U-01` deferred with a deadline. `OQ-02` and `OQ-04` deferred to
named slots. `E-05` open as an integrator obligation carried forward. `ADR-0014` is the
single architecture `defer` and stays `proposed`.

None is closed by ratification and none is given an invented value.

## Runtime fields

`backend_runtime`, `frontend_runtime` and `local_infra_versions` are recorded as
`not applicable - architecture-only checkpoint`. No production runtime exists and
building one is prohibited before CP-01. A blank field would read as untested; a
version string would assert a runtime that does not exist.

## Method limitation, recorded rather than glossed

Both streams and both reviewers were independent agents, none of which authored the
artifacts it examined. For an architecture-only checkpoint the six manual cases are
reading and judgment over documents rather than exercise of a running system, so an
independent agent is the closest available analogue of a human tester — not a
substitute for one. This is stated so a later reader weighs the evidence for what it
is.
