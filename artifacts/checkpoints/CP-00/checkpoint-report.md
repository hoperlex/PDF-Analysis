# CP-00 — checkpoint report

**Checkpoint:** CP-00 — architecture and behaviour freeze
**Tag:** `v0.0.0-architecture`
**Ratifying task:** `W0-INT-01`
**Closed out:** 2026-09-07, on acceptance round ten, at commit
`39a3a6430bd97c38cb20bafc793fc9d077d0df8e`, which the annotated tag
`v0.0.0-architecture` points at.
**Superseded:** on 2026-09-07 the repository owner decided a formal superseding
checkpoint (`docs/program/EXECUTION_PLAN.md` §3.3–§3.4). Round ten stands for the tree it
judged and for no other; acceptance round eleven is owed on the recovery candidate, and the
successor tag is recorded in `manifest.json` under `supersession` and in
`docs/program/CHECKPOINT_REGISTRY.md`. The successor's name is deliberately not written into
this report: `tests/contract/test_cp00_candidate.py` requires this file to carry the tag the
records resolve to, and a report that already mentions the next one satisfies that
requirement by mention rather than by being brought up to date. The sentence that stood here
— "No round eleven was opened" — was true when it was written and is not true now.
**Corrections:** `erratum.md` carries every claim in this bundle that was found false or
unsupported, with the exact quote, its location, what is true and how it was measured.

## Verdict

**Accepted.** Both acceptance streams passed against the semantic freeze recorded below,
and no contract, schema, fixture, state-machine, identifier or golden defect was found.

| Stream | Result |
|---|---|
| Automated | `PASS` — bootstrap validator and the 324-test contract suite, both exit 0 on the candidate frozen at `2ea7b68`; `automated-summary.txt` |
| Manual, independent | `PASS 6/6` — `manual-test-report.md`, frozen candidate `2ea7b68` |

The state-record sweep also ran clean on that tree — `--rev 2ea7b68`, both axes 0 — and is
recorded in `automated-summary.txt`. It is **not** a gate of this checkpoint and no verdict
rests on it: `manifest.json` declares it unusable as one, and this report used to count it as
one of three grounds for the automated `PASS`. That contradiction is `erratum.md`, E-6. On
the base tree `6135f17` with this task's paths applied the sweep exits 1: axis one 0, axis two
16 across nine files uncommitted, 19 across ten files once `erratum.md` is tracked, which the
integration commit does. On the integration tip `06be04e` with the same paths the same command
gives 17 across ten files and 20 across eleven files; the difference is one path
outside this task's licence. Every finding is the shape the manifest already describes — the
sweep has no model of a ratified checkpoint — and every one is classified by path and anchor in
`erratum.md`, E-12, which is also where the two figures this paragraph carried in its previous
form are corrected. The totals are observations with a command and a tree; the claim is the
classification, and `erratum.md`, `E-13`, states what that classification does and does not
establish.
The gate that replaced it is `tests/checkpoint/cp00_final_state.py`, delivered by
`W0-QA-04`.

## What is frozen

The semantic freeze is the four reviewed families and their content, recorded in
`contract-manifest.yaml`. It is **not** a whole-tree digest, and that is a deliberate
change made at this closeout: adding a checkpoint report to the tree must not invalidate
the acceptance of the contracts.

| | |
|---|---|
| `reviewed_candidate_commit` | `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` |
| `qa_evidence_commit` | `3da104e5d6fafb2a581bda377a07911183af803f` |
| reviewed-input manifest, at `92e13fa4` | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` |
| checkpoint manifest, at the tagged commit `39a3a643` | `f362647cc9b1d2201ac4663bf5d877346eeeccf046734219103c3ac822d2845d` |
| `artifact_manifest_sha256`, over the tree this report ships in | `a78572288a28b88be7f5dd58b9e79254a9e4f61cb55838ba4308b3be91109b84` |
| files certified | 100 — `contracts` 33, `fixtures` 32, `docs/architecture` 33, `scripts` 2 |
| contract versions | domain, analysis, events `1.0.0-draft.1`; golden selection schema `1`; candidate revision `5` |
| canonical version key | `contract_version` (`ID-01`) |
| canonical authority token | `execution_token` (`ID-02`, `ALR-25`) |
| `migration_head` | `none` |

One recipe, three trees, three values. The recipe was published as "reproducible from
this file alone" and bound to no commit, so the bundle carried the first two of those
values under swapped labels for ten acceptance rounds. Every aggregate now names its
commit; `contract-manifest.yaml` lists all 100 members with their own SHA-256, grouped by
directory, so no aggregate carries a member it does not list. `scripts/` — the family
holding open security item `E-06` — is enumerated there for the first time.

The manifest hash was recomputed independently by the integrator and again by the manual
tester, each from the recipe text rather than by calling the module's helper, and both
reproduce it over exactly 100 files. The manual tester additionally ran six discrimination
probes — a byte changed in each of three families, a dropped path, hex text instead of raw
digest bytes, reversed path order — and every one produces a different value, so the match
means something.

**Byte identity, stated exactly.** Three of the four families — `contracts/`, `fixtures/`
and `scripts/`, the three the mechanism module pins as `IMMUTABLE_REVIEWED_PREFIXES` — are
byte-identical to `92e13fa4`, and `git diff` over those three prefixes is empty. The
fourth, `docs/architecture/`, is not and was never meant to be: ratification reconciles
five files inside it, `manifest.json` declares them in `ratification.allowed_delta_paths`,
and the `review_status` disposition of `W0-INT-02` moved two of those five again. The
earlier form of this paragraph said all four were byte-identical, which is false of the
tree it was written in; `erratum.md`, E-2.

## What was checked

**On the frozen round-ten candidate `2ea7b68b4c4455b03ed4f8437d12f5f35f56af58`** — the tree
both acceptance streams judged, and the tree every figure in this section and the next is a
figure *of*. Run once, from the repository root of a checkout of that commit, each exit code
read from the process that produced it. The tree was unnamed here until the third independent
review of `W0-INT-02` observed that a section headed only "run once, from the repository root"
reads as a description of whatever tree the reader is holding — and it is not one. On the integration
tree — the main checkout at `89d2303` with this task's 27 paths applied, which is the tree this
report ships in — the contract suite collects 343, `git ls-files | grep -c '\.md$'` returns
165, and the validator, which walks the working tree rather than the index, prints
`markdown_files=166` because the erratum is present and not yet tracked. All three moved after
the base did: at `6135f17` and `06be04e` they were 340, 164 and 165.

The attribution was re-measured at `2ea7b68` rather than assumed, in a `cp -a` copy checked
out at that commit, each exit code taken from the process:
`.venv/bootstrap/bin/python -m unittest discover -s tests/contract` → `Ran 324 tests`, `OK`,
exit 0; `.venv/bootstrap/bin/python scripts/validate_bootstrap.py` → `markdown_files=154`,
`PASS`, exit 0; and the validator's own link rule, applied over those 154 tracked files, finds
264 link targets of which 252 are relative and 0 broken. The figures of the tree this report
*ships* in are in `erratum.md`, E-3, E-7 and E-12.

| Check | Result |
|---|---|
| bootstrap validator, standalone | `PASS`, exit 0 |
| contract suite, `discover -s tests/contract` | 324 tests, `OK`, exit 0 |
| documented analysis gates A–D, extracted and run verbatim | all exit 0, all four markers printed |
| schema positive and negative examples, golden checksums and assertions, error-catalog parity, contract-version invariants, referential integrity, ADR and lint coverage, candidate integrity | 45 tests run explicitly, 0 failures |
| Markdown link sweep | 154 files, 252 relative links, 0 broken |
| `git diff --check` | exit 0, no output |
| manual `MT00-01`–`MT00-06`, independent tester | `PASS 6/6`, checklist 3/3 |

Recomputed from repository data rather than read from a report, at that same commit
`2ea7b68`. These eleven read only the reviewed families, and `contracts/`, `fixtures/` and
`scripts/` are byte-identical between `2ea7b68` and the tree this report ships in — `git diff
--name-only 2ea7b68 -- contracts fixtures docs/architecture scripts` names five files, all
under `docs/architecture/`, which are `W0-INT-01`'s ratification delta and `W0-INT-02`'s
`review_status` disposition. Of the eleven, two were re-taken on both trees and agree: 9
registry stages (`stages` has length 9 in `contracts/analysis/v1/stage-registry.json`) and 18
ADRs (`validate_bootstrap.py` prints `adrs=18` at both). The other nine are `W0-INT-01`'s
closeout measurement at `2ea7b68`, attributed and **not** re-taken here; a reader who needs
them for this tree runs the recomputation again. The list: 9 registry stages, 62
legacy name rows, 31 declaration sites, 293 immutable evidence locators, 20 error codes,
25 identifiers, 6 state machines, 33 lint rules, 18 ADRs, 5 golden journeys, 95 assertions
as 92 inventory-mapped plus 3 target-scope.

## The blocking test contour: what was claimed, and what is there

This section previously recorded a contour split as an accomplished fact. It did not
happen, and the paragraphs that described it are the largest single defect in this bundle.
They are replaced here rather than annotated, because a reader of the checkpoint is
entitled to a description of the tree in front of them; the exact superseded wording, its
location and the measurement that refutes it are in `erratum.md`, E-3.

**What was claimed.** That `tests/contract/test_cp00_candidate.py` had moved, with its
history, to a mechanism module under `tests/checkpoint/`; that a second module under
`tests/contract/` re-exported the classes checking product semantics; and that the blocking
contour was consequently 103 tests, with 255 out of contour and two of those failing.

**What is true.** Neither of the two named modules exists, at this commit or at any commit
on any ref in this repository. `git log --all --pretty=format: --name-only` over the whole
history lists eleven paths under `tests/`, and neither name is among them.
`tests/contract/test_cp00_candidate.py` has never moved: it has seven revisions, all at
that path. No split was ever performed, so the 103, 255, 281 and 77 figures all count a
partition of the suite that does not exist.

**The contour, measured on the tree this report ships in.** Each figure is the number the
runner collected, not a count of `def test_`:

| Command | Result |
|---|---|
| `.venv/bootstrap/bin/python -m unittest discover -s tests/contract` | 343 tests |
| — of which `tests/contract/test_cp00_candidate.py` | 303 |
| — of which `tests/contract/test_cp00_final_state.py` | 14 |
| — of which `tests/contract/test_validate_bootstrap.py` | 26 |
| `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint` | 47 tests |

**Four of the 343 fail on this tree, and not one is a contract, schema, fixture,
identifier, state-machine or golden defect.** Two are in
`tests/contract/test_cp00_candidate.py` and follow from the base commit sitting outside
acceptance round ten's post-freeze delta ceiling — the recovery work is itself the delta —
and they close when the integrator freezes acceptance round eleven. Two are in
`tests/contract/test_cp00_final_state.py`, which asserts the final-state contour is empty:
one is the tag-integrity axis, three findings that only a superseding tag can close, and one
is the accounting axis, a single finding that closes the moment
`artifacts/checkpoints/CP-00/erratum.md` is committed. All four are named in `erratum.md`,
`L-1` and `T`, with their owners.

**Why the claim was made.** Ten acceptance rounds were opened. Rounds six, seven and eight
each ran in full with both streams. Not one of the ten found a defect in a contract, a
schema, a fixture, a state machine, an identifier or a golden expectation. Every blocker
any of them raised lived in the mechanism that checks the checkpoint, and three of those
blockers were completeness claims the integrator asserted without measuring. This section
was a fourth: a change described in the past tense in the one document a reader of the
checkpoint is handed, with no check that could fail on the thing it named. The
architecture was sound throughout; the procedure had no executable end.

Consequently `docs/program/reviews/W0-QA-01.md` and `docs/program/tasks/W0-QA-01.md` still
quote a suite command and a count of 281 that describe neither the tree they ship in nor
any other. `W0-QA-01` is accepted and closed, and both files are dated historical records
whose editing would destroy the evidence this audit rests on, so they are corrected by
`erratum.md`, E-8, and not by edit.

## Acceptance history

| Round | Automated | Manual | Outcome |
|---|---|---|---|
| 1 | FAIL — 5 blockers | FAIL — MT00-01 | candidate could not identify itself |
| 2 | FAIL — 4 blockers | FAIL — MT00-01 | pointer reworded, still recording nothing |
| 3 | **PASS** | **PASS** 6/6 | spent; the tree moved afterwards |
| 4 | — | — | void before dispatch |
| 5 | — | — | void; frozen, never reported |
| 6 | **PASS** | FAIL — MT00-01 | superseded evidence commit presented as current in five sites |
| 7 | FAIL | FAIL — MT00-01 | the remediation for round six was declared exhaustive and was not |
| 8 | FAIL | FAIL — MT00-01 | the acceptance record was three rounds stale; the completeness check had never been run against the tree it was written for |
| 9 | — | — | void before dispatch: the mechanism had no executable final state |
| 10 | **PASS** | **PASS** 6/6 | accepted; ratified at `39a3a643`. Superseded for the recovery tree — see the closeout note above |

Round nine was voided before either stream was sent, by the repository owner, on finding
that `W0-INT-01` must create eight files and reconcile four documents that the post-freeze
delta ceiling did not license — so performing the ratification would have voided the round
authorising it. Dispatching would have spent two full runs on a candidate that could not be
ratified without destroying its own acceptance.

## Merged tasks

Every task `integrated_w03_tasks` records, with the commit that integrated it:

| Task | Integrated at |
|---|---|
| `W0-QA-03` | `23dddf99f833d12cd4cc22d11e224d4b278872bf` |
| `W0-ARC-02` | `a67ba31e7748c02974ae9ae93c7f30b6f141d417` |
| `W0-DOM-02` | `478d32e90d1cbb2c691e0ac0b61b68dadcf0d397` |
| `W0-EVT-01` | `3ca8e25413426ff8efec41cd850c325331d181fc` |
| `W0-CLN-01` | `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` |
| `W0-QA-01` | `3da104e5d6fafb2a581bda377a07911183af803f` |

The manual acceptance is `manual-test-report.md`; the open items are `known-risks.md`;
the restore and rollback procedure is `restore-or-rollback-note.md`.

## Deliverables

`checkpoint-report.md` · `contract-manifest.yaml` · `automated-summary.txt` ·
`manual-test-report.md` · `migration-head.txt` · `build-info.json` · `known-risks.md` ·
`restore-or-rollback-note.md`

## Open at ratification

`known-risks.md` carries the full list. In short: one security item, `E-06`, in the
bootstrap validator, owned by W1 and unrepairable inside the freeze because `scripts/` is
an immutable reviewed family; the mechanism suite's freeze of `contracts/`, `fixtures/` and
`scripts/` against S01, to be dispositioned at the tag; `ADR-0014` deferred; `U-04`,
`OQ-02`, `OQ-04` and `E-05` open; and four recorded integrator exceptions for the
stage-closing review.

Nothing in that list changes a contract, a schema, an identifier rule, a state machine, an
error contract or a golden expectation.

## Round ten, and what it cost to get here

Ten acceptance rounds were opened. Rounds six, seven and eight each ran in full with both
streams; rounds four, five and nine were voided before or during dispatch. **Not one of
the ten found a defect in a contract, a schema, a fixture, a state machine, an identifier,
an error contract, an evidence anchor or a golden expectation.** Every blocker any of them
raised lived in the checkpoint's record of itself.

Round nine was voided before dispatch on finding that the mechanism had no executable
final state: `W0-INT-01` must create eight files and reconcile four documents that the
post-freeze delta ceiling did not license, so performing the ratification would have
voided the round authorising it. The remediation that fixed it was itself rejected by
four independent reviewers with fifteen blockers, of which eight are closed in commits
`49bdcee` and `1ab8bac` and seven are recorded as known items owned by W1.

Two of those eight are worth naming here because without them this checkpoint could not
be published at all. **M1**: `_freeze_commit` stopped resolving once the newest manifest
revision carried the frozen value, so committing the deliverable took the suite from 318
green to 129 failures — the green baseline existed only while the deliverable stayed
uncommitted. **M2**: `_retro_edited_digests` walked from `HEAD`, so every re-derivation of
a committed publication compared its own freshly computed evidence digest against the
committed one, which can never match, and the probe written to answer round nine's void
failed on any published tree.

Three sessions worked this checkpoint concurrently and twice collided. The recorded
lessons: the suite's sandbox tests copy the working tree, so a concurrent clone corrupts
a run, which produced phantom failures three separate times; and a measurement taken while
another writer is editing describes nothing, so two green figures measured minutes apart
were discarded rather than reconciled.
