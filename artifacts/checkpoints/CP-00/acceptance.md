# CP-00 acceptance record

> **Round 3 is spent; this document is history, not current acceptance.** Both streams
> returned `PASS` on 2026-09-02, then two things moved the tree: `W0-QA-01` was reopened
> because its suite accepted a ratification that is declared and not performed, and the
> digest model was corrected. Acceptance certifies a tree; both changes replaced it.
> Ten rounds are in the record. Round ten returned `PASS` from both streams and CP-00 is
> ratified on it at commit `39a3a6430bd97c38cb20bafc793fc9d077d0df8e`; no earlier result
> transferred to it. **Round ten stands for the tree it judged and for no other.** The tree
> that carries this document is not that tree, so an eleventh round is owed: see "Round
> eleven" below.
>
> Primary reports: `manual-report-round-3.md`, and both streams' primary reports for
> rounds six, seven and eight. No primary automated report exists for round 3 — that
> stream reported to the integrator only, which round six did not repeat: it produced the
> first primary automated report in this program. Rounds four, five and nine carry no
> report at all: each was voided before any stream reported.

Ten rounds have been opened. Rounds one and two returned `FAIL` from both streams;
round three returned `PASS` from both and is spent; rounds four, five and nine were
voided before either stream reported; rounds six, seven and eight each ran in full and
failed; round ten was frozen at `2ea7b68b4c4455b03ed4f8437d12f5f35f56af58`, ran in full,
and is accepted. An eleventh is owed.

The sentence that stood here — "round ten is accepted and has not been frozen" —
contradicted this document's own table row for round ten, which records the freeze, and the
manifest, which carries the frozen digest and the freeze commit. The manual tester of round
ten raised it as finding `F-1`. It is corrected rather than annotated: this document is a
live record, not a dated report.
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
| 10 | **PASS** | **PASS** — 6/6 | frozen at `2ea7b68`; **CP-00 ratified** at `39a3a643` |
| 11 | owed | owed | owed on the recovery candidate; not yet frozen — see "Round eleven" |

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
the paths to move. That alignment was made and independently accepted, round ten was then
frozen at `2ea7b68`, both streams ran, and CP-00 was ratified on it. The sentence that stood
here — "Round ten is accepted and must not be frozen until that alignment has been
independently accepted" — described a state two commits back and is superseded by the round
it was written about.

## Round eleven

**Acceptance round eleven is owed and is not opened.**

On 2026-09-07 the repository owner decided a formal superseding checkpoint
(`docs/program/EXECUTION_PLAN.md` §3.3–§3.4, variant A), whose fourth step is a further
acceptance round on one frozen commit. Round eleven is that round, and
`v0.0.1-architecture` is the tag it leads to.

**Why it is owed.** Round ten's acceptance is bound to the tree frozen at `2ea7b68`. Measured
on the base of this reconciliation, `6135f17fb76758dc1ab3a7c1195f5421814ba2fb`, nine paths
differ from that tree and nothing licenses them: `docs/program/EXECUTION_PLAN.md`,
`docs/program/reviews/W0-QA-04.md`, `docs/program/tasks/W0-INT-02.md`,
`docs/program/tasks/W0-INT-03.md`, `docs/program/tasks/W0-QA-04.md`,
`tests/checkpoint/cp00_final_state.py`, `tests/checkpoint/test_cp00_final_state_contour.py`,
`tests/contract/test_cp00_candidate.py` and `tests/contract/test_cp00_final_state.py`. By
this checkpoint's own recorded rule — if the frozen tree must change, the round is void and a
new one begins — round ten does not authorise ratifying this tree.

**Why it has no row in the table below and no entry in `acceptance_rounds`.** Not an
omission, and measured rather than assumed: opening it inside this freeze is unreachable in
all three available forms, because the mechanism module models three checkpoint states and
the recovery needs a fourth — ratified, superseded, and a new round judging the successor.
The three branches and what each produced are recorded in `erratum.md`, `L-2`, and the
disposition is carried in `manifest.json` under `supersession`, which is data a reviewer can
act on. **Owner of opening it: the integrator, at the freeze commit.**

**What it must judge.** The tree the integrator freezes after `W0-INT-02` is integrated, with
both streams reporting to canonical primary reports —
`artifacts/checkpoints/CP-00/manual-report-round-11.md` and
`artifacts/checkpoints/CP-00/automated-report-round-11.md`, which are the two names the
round's own evidence licence recognises.

## The record of the rounds is itself checked now

Rounds seven and eight both failed partly on stale round accounting, and the sweep written
after round eight covered only the superseded-evidence axis — a limit recorded at the time
rather than closed. It is closed here.
`artifacts/checkpoints/CP-00/check_state_records.py` now carries a second axis: which
acceptance round is owed, and how many rounds are in the record. It reads both values out
of `manifest.json`'s `current_round` and `acceptance_rounds` rather than restating them,
so the sweep cannot itself go stale; it binds a claim to the structural unit that makes it
— the enclosing JSON string under its key trail, the enclosing table row, the enclosing
sentence — so a label excuses only the claim it contains; it skips three paths, the dated
primary acceptance reports, the independent review reports and itself; and it requires this document, the
manifest, `CURRENT_STATE.md` and the checkpoint registry each to *state* both claims, so
that a record which says nothing cannot pass for the wrong reason.

Measured, in both directions, and **each measurement names the tree it was taken on**, which
the previous form of this paragraph did not do. `--selftest` fires each detector and shows a
history label excusing only its own unit. `--rev` sweeps any commit's objects without a
checkout, which is how every figure here can be reproduced by a reader on a dirty working
tree, and how the axis-one measurements at `bde3af3`, `a3eaf88` and `5b70ee4` — 1, 1 and 4
findings — were taken.

```
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py --rev 4bf2351
axis two - stale round accounting: 17          # across six files: the round-nine void,
                                               # the tree before the round-ten reconciliation
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py --rev 2ea7b68
axis two - stale round accounting: 0           # the frozen round-ten candidate: both axes
                                               # clean, which is the state the streams judged
```

**Neither of those is a figure of the tree this document ships in, and the sentence they
replace read as though the second one were.** "Run after it, the four records above are
clean" was true of `2ea7b68` and is false here: on this tree the sweep names all four, for
the reasons `erratum.md` `E-12` enumerates by class. The defect is the one `E-12` corrects —
a figure measured but not attributed to a tree — and it was found by sweeping this record for
the class rather than for the finding.

**Its exit code is 1 on the tree that carries this document, and both of this paragraph's
earlier forms are superseded.** It once said the exit code was non-zero with nine findings
across three files; it then said the exit code was zero on both axes. Measured on this tree,
with the command and the exit code taken from the process that produced it:

```
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 238 tracked paths
axis one - superseded commits presented as current: 0
axis two - stale round accounting: 16
                                                                     # exit 1
```

That figure is of the base tree `6135f17` with this task's paths applied, uncommitted, and it
names **nine** files. It becomes **19 across ten files** once
`artifacts/checkpoints/CP-00/erratum.md` is tracked, which the integration commit does: the
sweep enumerates with `git ls-files`, an uncommitted file is invisible to it, and the erratum
carries three owed-round sentences of its own. Both values are stated because stating only the
first would make this paragraph wrong the moment the work is committed.

**And a third reason to state more than one, learned this round: the total moves with the base
as well as with the commit.** On the integration tip `06be04e`, which is the tree the primary
reviewer holds, the same command gives **17 across ten files** uncommitted and
**20 across eleven files** tracked. The difference is one path this task may not write,
`docs/program/EXECUTION_PLAN.md`, which the sweep reads as a live record naming the round this
recovery owes. Four figures, two trees, each with its commit — and the command, not any of
them, is what a reader re-runs. `erratum.md`, `E-13`.

**Neither number is the claim.** The two figures this paragraph carried in its previous form
— sixteen across *eight* files, becoming *seventeen* — were both wrong, and they were wrong
in a way no re-measurement of the tree could have caught, because their value depends on the
bytes of the sentences that state them. This paragraph *was* one of the findings it counted,
until the repair moved this record's owed-round claim to where a reader looks for it, § "Round
eleven" above; that trade changed which finding this file contributes without changing the
total, and `erratum.md` E-12 records it rather than absorbing it. What is asserted here
instead is an invariant: **axis one is 0, and every axis-two finding belongs to one of four
named classes.** The classes, and every site by path and by an anchor that does not move when
a file reflows, are `erratum.md`, `E-12`. The totals above are observations, carrying the
command and the tree, and nothing rests on them.

**Two things this paragraph previously claimed for that invariant are withdrawn, and the
narrower true statements are `erratum.md`, `E-13`.** It said the invariant "survives the next
edit to any live record": it does not — an edit that adds a countable claim in a unit the
checker can read raises axis two by one, and the new finding belongs to none of the four
classes. And it carried a fourth clause, "none of which is a stale record", which was asserted
and never measured: the `C-2` class is *defined* as a record the checker cannot read, so
rewriting a `C-2` site to name the wrong round leaves the finding list byte-identical. Both
were measured on the integration tip, and `E-13` gives the transcripts. What the classification
establishes is that a stale live record introducing a **new path** shows up as a path not in
the `E-12` table; what it cannot establish is that a path already in the table is current. The
two sentences in `docs/program/CURRENT_STATE.md` that state the round this recovery owes are
`C-2` sites, and a reviewer verifies them by reading them against `manifest.json`'s
`supersession` object. Owner of a checker that could read them: W1.

**And the sweep is not a gate of this checkpoint.** `manifest.json` says so in
`known_pre_ratification_items.sweep_has_no_ratified_state`, and no acceptance verdict rests
on it. Its axis two models the round accounting as "which round is owed", and a ratified
checkpoint owes none, so it reports a correctly ratified manifest as a defect and instructs
the reader to open the next round in `acceptance_rounds` — which the mechanism module
refuses, for the reasons in `erratum.md`, `L-2`. The two checkers give contradictory
instructions about one field. The gate that replaced it is
`tests/checkpoint/cp00_final_state.py`, delivered by `W0-QA-04`, which models open,
closed-accepted and terminal-ratified states explicitly. `checkpoint-report.md` used to count
the sweep among three grounds for the automated `PASS`; that is corrected, and recorded in
`erratum.md`, E-6.

The nine findings the earlier form named were the W0.3 wave plan at two lines and the
`W0-INT-01` status banner, which are writable only by `W0-INT-01` and were corrected before
the round-ten freeze; and six rows of the evidence table in
`docs/program/reviews/W0-QA-01.md` §11.19.8, which are not findings at all: they are a dated
historical measurement, the table being introduced by "Measured at `4bf2351`", and the sweep
binds to the table row while the date sits in the introducing paragraph, so it cannot see the
label. Those six were routed in `manifest.json` to `W0-QA-01`, an accepted and closed task —
the path right and the actor wrong. Re-routed to W1, by erratum rather than by edit:
`erratum.md`, E-8.

**The integrator then excluded review reports by path, and that is a narrowing this
paragraph warned against in its previous form.** The warning was right and is recorded
here rather than deleted: the correct repair is to teach the sweep to honour a table's
introducing label, which is smaller and does not widen a skip list. The path exclusion
was taken instead, in the same commit that wrote the warning, and measured only to the
extent of confirming the sweep still reports seventeen stale sites at `4bf2351` — that
it is not inert, not that it is right. The sweep is outside `POST_FREEZE_DELTA_CEILING`
by deliberate design, so it cannot be corrected inside this round; the proper repair is
owed to W1 with the other `W0-QA-01` items. What can be said in its favour is narrow: a
review report is not a record any consumer reads for current state, and the manifest,
the registry, the state document, the wave plan and the task banners — which are — remain
unexcluded.

The three genuine sites were closed before the round-ten freeze, and it is worth being exact about why,
because an earlier form of this record gave the wrong reason. The wave plan and the task
banner are inside `POST_FREEZE_DELTA_CEILING`, so correcting them after a freeze would
*not* void the round; they are owed early because both acceptance streams read the state
records, and stale round accounting is what failed rounds six, seven and eight. The six in
the review report are a different case: that file is inside the candidate digest path set
and outside the ceiling, so correcting it after a freeze **would** void the round. It is
inside `W0-QA-01`'s two allowed paths, so it has an owner. The residue is recorded in
`manifest.json` under
`known_pre_ratification_items.round_accounting_outside_this_reconciliation`.
