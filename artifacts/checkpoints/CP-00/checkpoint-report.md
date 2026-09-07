# CP-00 — checkpoint report

**Checkpoint:** CP-00 — architecture and behaviour freeze
**Tag:** `v0.0.0-architecture`
**Ratifying task:** `W0-INT-01`
**Closed out:** 2026-09-07, on acceptance round ten — the single final round the
repository owner authorised. No round eleven was opened.

## Verdict

**Accepted.** Both acceptance streams passed against the semantic freeze recorded below,
and no contract, schema, fixture, state-machine, identifier or golden defect was found.

| Stream | Result |
|---|---|
| Automated | `PASS` — validator, 324-test contract suite and the state-record sweep, all exit 0; `automated-summary.txt` |
| Manual, independent | `PASS 6/6` — `manual-test-report.md`, frozen candidate `2ea7b68` |

## What is frozen

The semantic freeze is the four reviewed families and their content, recorded in
`contract-manifest.yaml`. It is **not** a whole-tree digest, and that is a deliberate
change made at this closeout: adding a checkpoint report to the tree must not invalidate
the acceptance of the contracts.

| | |
|---|---|
| `reviewed_candidate_commit` | `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` |
| `qa_evidence_commit` | `3da104e5d6fafb2a581bda377a07911183af803f` |
| `artifact_manifest_sha256` | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` |
| files certified | 100 — `contracts` 33, `fixtures` 32, `docs/architecture` 33, `scripts` 2 |
| contract versions | domain, analysis, events `1.0.0-draft.1`; golden selection schema `1`; candidate revision `5` |
| canonical version key | `contract_version` (`ID-01`) |
| canonical authority token | `execution_token` (`ID-02`, `ALR-25`) |
| `migration_head` | `none` |

The manifest hash was recomputed independently by the integrator and again by the manual
tester, each from the recipe text rather than by calling the module's helper, and both
reproduce it over exactly 100 files. The manual tester additionally ran six discrimination
probes — a byte changed in each of three families, a dropped path, hex text instead of raw
digest bytes, reversed path order — and every one produces a different value, so the match
means something. The reviewed families are byte-identical to the candidate commit:
`git diff` over the four prefixes is empty.

## What was checked

Run once, from the repository root, each exit code read from the process that produced it:

| Check | Result |
|---|---|
| bootstrap validator, standalone | `PASS`, exit 0 |
| bounded contract suite, `discover -s tests/contract` | 103 tests, `OK`, exit 0 |
| documented analysis gates A–D, extracted and run verbatim | all exit 0, all four markers printed |
| schema positive and negative examples, golden checksums and assertions, error-catalog parity, contract-version invariants, referential integrity, ADR and lint coverage, candidate integrity | 45 tests run explicitly, 0 failures |
| Markdown link sweep | 154 files, 252 relative links, 0 broken |
| `git diff --check` | exit 0, no output |
| manual `MT00-01`–`MT00-06`, independent tester | `PASS 6/6`, checklist 3/3 |

Recomputed from repository data rather than read from a report: 9 registry stages, 62
legacy name rows, 31 declaration sites, 293 immutable evidence locators, 20 error codes,
25 identifiers, 6 state machines, 33 lint rules, 18 ADRs, 5 golden journeys, 95 assertions
as 92 inventory-mapped plus 3 target-scope.

## The blocking test contour was reduced, by owner decision

This is the largest procedural change at closeout and it is stated here because no other
tracked document carried it when the final acceptance ran.

`tests/contract/test_cp00_candidate.py` moved, with its history, to
`tests/checkpoint/test_cp00_mechanism.py`. `tests/contract/test_cp00_contracts.py`
re-exports exactly the classes that check **product semantics**. The blocking contour is
now **103 tests**: 77 semantic plus the 26 validator regressions.

Blocking: JSON Schema and examples, cross-family references, contract-version invariants,
identifiers and state machines, error-catalog parity, the stage registry, golden checksums
and assertions, ADR and lint-rule coverage, the documented analysis and neighbour gates,
byte identity of the reviewed candidate, and the mutation controls that prove each of
those can fail.

Out of the contour, still in the repository, still runnable with
`unittest discover -s tests/checkpoint`: ratification self-reference, post-freeze delta
licensing, the mutation census of the module's own tables, Git hook and configuration
attack simulations, the completeness checks of its own completeness checks, and the
sandboxed history of acceptance rounds. 255 tests.

**Two of those 255 fail**, both as a direct consequence of this split: the sandbox-reset
expectation, and an assertion that `W0-QA-01` owns exactly two paths, which a three-file
layout makes false. Both are the mechanism's bookkeeping about its own location. They are
named here rather than repaired, because repairing them is the recursion this decision
ended.

**Why.** Nine acceptance rounds were opened. Rounds six, seven and eight each ran in full
with both streams. Not one of the nine found a defect in a contract, a schema, a fixture, a
state machine, an identifier or a golden expectation. Every blocker any of them raised
lived in the mechanism that checks the checkpoint — and three of those blockers were
completeness claims the integrator asserted without measuring. The architecture was sound
throughout; the procedure had no executable end.

Consequently `docs/program/reviews/W0-QA-01.md` and `docs/program/tasks/W0-QA-01.md` still
quote the pre-split command and the count 281. `W0-QA-01` is accepted and closed;
correcting its deliverables would reopen it, which is the recursion that was ended. This
report is the record a reader of the checkpoint is given.

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
| closeout | **PASS** | **PASS** 6/6 | this report |

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
