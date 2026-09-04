# CP-00 acceptance record

> **Round 3 is spent; this document is history, not current acceptance.** Both streams
> returned `PASS` on 2026-09-02, then two things moved the tree: `W0-QA-01` was reopened
> because its suite accepted a ratification that is declared and not performed, and the
> digest model was corrected. Acceptance certifies a tree; both changes replaced it.
> Eight rounds are now in the record and round nine is owed; no earlier result transfers.
>
> Primary reports: `manual-report-round-3.md`, and both streams' primary reports for
> rounds six, seven and eight. No primary automated report exists for round 3 — that
> stream reported to the integrator only, which round six did not repeat: it produced the
> first primary automated report in this program.

Eight rounds ran or were opened. Rounds one and two returned `FAIL` from both streams;
round three returned `PASS` from both and is spent; rounds four and five were voided
before either stream reported; rounds six, seven and eight each ran in full and failed.
Every blocker across all eight sat in integrator-owned metadata, gate text or state
documents. None was a contract, fixture, schema or test defect: both streams confirmed
the four reviewed families byte-identical to `reviewed_candidate_commit` in every round,
which is what carried the `W0-QA-01` `ACCEPT` across every rebuild without re-running QA.

## Rounds

| Round | Automated | Manual | Candidate digest (prefix) |
|---|---|---|---|
| 1 | FAIL — 5 blockers | FAIL — MT00-01 | `0d6641718e78afc3` |
| 2 | FAIL — 4 blockers | FAIL — MT00-01 | `7170ff5bf6734947` |
| 3 | **PASS** | **PASS** — 6/6 | recorded in the manifest |
| 4 | — | — | voided before dispatch |
| 5 | — | — | voided; frozen at `5207fb55` and never reported |
| 6 | **PASS** | FAIL — MT00-01 | frozen at `5b70ee4e` |
| 7 | FAIL | FAIL — MT00-01 | frozen at `c1376e1c` |
| 8 | FAIL | FAIL — MT00-01 | frozen at `b21e7275` |

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

## Rounds six to eight — what failed, and what did not

None of the three found a contract, schema, fixture, state-machine, identifier or golden
defect. Every automated gate passed in rounds six and eight, every declared count
reproduced from the artifact that carries it, and the four reviewed families stayed
byte-identical to `reviewed_candidate_commit` throughout. What failed each time was this
programme's record of itself.

Round six: a superseded QA evidence commit was still presented as current in five sites
while the task and wave layers named it superseded, so a reader following the documented
route reached a superseded commit with a wrong round count.

Round seven: the remediation for that was declared exhaustive and was not. Two sites
survived in the file it had itself edited, thirty-six lines from the section it corrected,
and it introduced two new false statements while fixing one. Separately the round
accounting in three state documents was two rounds behind, on an axis no sweep had
searched.

Round eight: the reconciliation for both missed `acceptance.md` — this document — which
round seven had named explicitly and which stood first in the state audit's list. And the
check offered as proof that the sweep was complete had not itself been run against the
tree it was written for; run there, it passed.

The pattern is one defect repeated by the integrator: a completeness claim asserted in
prose beside no check that could fail on the thing it named. That is the same shape the
QA suite spent twelve review rounds eliminating from itself.
`artifacts/checkpoints/CP-00/check_state_records.py` is the replacement, bound to the
structural unit that contains an occurrence rather than to a line window. It exits 1 on
`bde3af3`, `a3eaf88` and `5b70ee4`, naming the defect at each — measured, not asserted.
