# CP-00 acceptance record

> **Round 3 is spent; this document is history, not current acceptance.** Both streams
> returned `PASS` on 2026-09-02, then two things moved the tree: `W0-QA-01` was reopened
> because its suite accepted a ratification that is declared and not performed, and the
> digest model was corrected. Acceptance certifies a tree; both changes replaced it.
> Ten rounds are now in the record and round ten is owed; no earlier result transfers.
>
> Primary reports: `manual-report-round-3.md`, and both streams' primary reports for
> rounds six, seven and eight. No primary automated report exists for round 3 — that
> stream reported to the integrator only, which round six did not repeat: it produced the
> first primary automated report in this program. Rounds four, five and nine carry no
> report at all: each was voided before any stream reported.

Ten rounds have been opened. Rounds one and two returned `FAIL` from both streams;
round three returned `PASS` from both and is spent; rounds four, five and nine were
voided before either stream reported; rounds six, seven and eight each ran in full and
failed; round ten is owed and has not been frozen.
Every blocker across all ten rounds sat in integrator-owned metadata, gate text or state
documents. None was a contract, fixture, schema or test defect: in every round that ran,
both streams confirmed the four reviewed families byte-identical to
`reviewed_candidate_commit`, which is what carried the `W0-QA-01` `ACCEPT` across every
rebuild without re-running QA.

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
| 9 | — | — | void; frozen at `ec63e75`, voided at `4bf2351` before dispatch |
| 10 | — | — | not frozen; the freeze is the step after the QA ceiling remediation |

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

## Round nine — frozen, then voided before dispatch

Round nine was frozen at `ec63e75` on the tree that carried the round-eight remediation,
and voided at `4bf2351` before either stream was sent. Nothing was spent on it and it
carries no report.

It was voided because the checkpoint mechanism had no executable final state. `W0-INT-01`
must create eight files under `artifacts/checkpoints/CP-00/` — `checkpoint-report.md`,
`contract-manifest.yaml`, `automated-summary.txt`, `manual-test-report.md`,
`migration-head.txt`, `build-info.json`, `known-risks.md` and
`restore-or-rollback-note.md` — none of which exists; it must reconcile the W0.3 wave
plan, the S00 stage checklist and `docs/INDEX.md`; and it must close the status banners
of the seventeen completed task files. The QA suite's post-freeze delta ceiling licensed
none of that: it honoured the checkpoint manifest, the registry, the state document, the
five architecture files ratification reconciles, and the current round's two declared
acceptance reports. Performing the ratification honestly would therefore have put more
than thirty unlicensed paths into the post-freeze delta and voided the round that
authorised it — by any sequence, in either order.

Finding it before dispatch is the one thing that went right: two full acceptance runs
were not spent on a candidate that could not be ratified without voiding itself. Nine
rounds had by then been opened and none had found a contract, schema, fixture,
state-machine, identifier or golden defect.

The repair is owned by the QA suite, not by the integrator: align the post-freeze ceiling
with `W0-INT-01`'s actual deliverables, license exactly the final state and evidence set
and nothing wider, and check the content of what it licenses rather than merely permitting
the paths to move. Round ten is owed and must not be frozen until that alignment has been
independently accepted, because a freeze taken first would be spent again for the same
reason.

## The record of the rounds is itself checked now

Rounds seven and eight both failed partly on stale round accounting, and the sweep written
after round eight covered only the superseded-evidence axis — a limit recorded at the time
rather than closed. It is closed here.
`artifacts/checkpoints/CP-00/check_state_records.py` now carries a second axis: which
acceptance round is owed, and how many rounds are in the record. It reads both values out
of `manifest.json`'s `current_round` and `acceptance_rounds` rather than restating them,
so the sweep cannot itself go stale; it binds a claim to the structural unit that makes it
— the enclosing JSON string under its key trail, the enclosing table row, the enclosing
sentence — so a label excuses only the claim it contains; it skips nothing by path except
the dated primary acceptance reports and itself; and it requires this document, the
manifest, `CURRENT_STATE.md` and the checkpoint registry each to *state* both claims, so
that a record which says nothing cannot pass for the wrong reason.

Measured, in both directions. `--selftest` fires each detector and shows a history label
excusing only its own unit. Run against the tree as it stood before this reconciliation it
named seventeen stale sites across six files; run after it, the four records above are
clean. `--rev` sweeps any commit's objects without a checkout, which is how the
axis-one measurements at `bde3af3`, `a3eaf88` and `5b70ee4` — 1, 1 and 4 findings — can be
reproduced by a reader on a dirty working tree.

Its exit code is still non-zero, and deliberately so. It names **nine findings across
three files**, not the three sites an earlier form of this paragraph claimed: the W0.3 wave
plan at two lines and the `W0-INT-01` status banner, which are writable only by
`W0-INT-01`; and six rows of the evidence table in `docs/program/reviews/W0-QA-01.md`
§11.19.8. Those six are a dated historical measurement — the table is introduced by
"Measured at `4bf2351`" — and the sweep binds to the table row while the date sits in the
introducing paragraph, so it cannot see the label. Narrowing the sweep until any of them
fell outside it would have been the round-eight defect committed a third time.

All nine are owed **before** the round-ten freeze, and it is worth being exact about why,
because an earlier form of this record gave the wrong reason. The wave plan and the task
banner are inside `POST_FREEZE_DELTA_CEILING`, so correcting them after a freeze would
*not* void the round; they are owed early because both acceptance streams read the state
records, and stale round accounting is what failed rounds six, seven and eight. The six in
the review report are a different case: that file is inside the candidate digest path set
and outside the ceiling, so correcting it after a freeze **would** void the round. It is
inside `W0-QA-01`'s two allowed paths, so it has an owner. The residue is recorded in
`manifest.json` under
`known_pre_ratification_items.round_accounting_outside_this_reconciliation`.
