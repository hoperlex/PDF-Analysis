# CP-00 — erratum

Issued by `W0-INT-02` on the recovery candidate, under the repository owner's decision of
2026-09-07 (`docs/program/EXECUTION_PLAN.md` §3.3–§3.4): variant A, a formal superseding
checkpoint.

**What this document is.** Every claim in the shipped CP-00 evidence bundle that was found
false or unsupported, with the exact quote, where it stands, what is true instead, and the
command that established it. Nothing here is a contract, schema, fixture, identifier,
state-machine or golden defect. Ten acceptance rounds found none. All of it is the
checkpoint's record of itself.

**What it does not do.** It does not rewrite history. The dated primary acceptance reports
— every `manual-report-round-*.md` and `automated-report-round-*.md` — the independent
review report `docs/program/reviews/W0-QA-01.md`, and the annotation of the tag
`v0.0.0-architecture` are immutable. Their figures are correct measurements of the trees
they judged, and editing them would destroy the only evidence that makes this audit
repeatable. A superseded statement in any of them is corrected here, by quotation.

**How to read an entry.** `E-n` is an erratum against the bundle. `T-n` is against the tag
annotation. `D-n` is a recorded disposition. `L-n` is a limitation that could not be closed
inside this freeze, with its owner.

**Where the measurements were taken.** A full clone of the repository at
`6135f17fb76758dc1ab3a7c1195f5421814ba2fb`, working tree carrying this task's changes and
nothing else, `.git` a real directory. Not a linked worktree: `tests/contract` cannot be
measured in one, because `.git` is a file there and the sandbox tests cannot copy the object
database. (The failure mode of doing it anyway — 202 tests with 19 environment errors instead
of the real count — is the orchestrator's measurement recorded in
`docs/program/EXECUTION_PLAN.md` §3.4; it is quoted, not re-taken here.) No other process was
cloning this repository during any measurement, because the sandbox tests copy the working
tree and a concurrent clone corrupts a run. Every exit code below is the one the named
process returned, never `$?` after a pipeline.

**Every figure in this document was measured on the tree this document ships in**, unless it
names another commit, in which case it was measured at that commit. Some figures change when
the integrator commits this work, because two of the tools involved read `git ls-files` and an
uncommitted file is invisible to them. They are named rather than counted — an earlier form of
this paragraph said "three figures", which is a count of this document's own contents stated
inside it, the class `E-12` is about — and each is given with **both** values and the command,
rather than with the one that would be wrong the moment the work lands:

- the state-record sweep's tracked-path total and its axis-two findings: `E-6` and `E-12`;
- `tests/checkpoint/cp00_final_state.py`'s finding count, 4 falling to 3 as its accounting
  axis goes from 1 to 0: `L-1`.

The count of unlicensed post-freeze paths is **not** one of them, and that was checked rather
than assumed: `_digest_paths` enumerates `git ls-files --cached --others --exclude-standard`,
so an untracked file is already inside it. `_post_freeze_delta_problems` names ten paths on
this tree whether `erratum.md` is staged or not, and nine at the base commit. An earlier
draft of this erratum carried four figures taken on the pristine base and presented as
figures of this tree — the exact defect class `E-7` condemns, inside the record correcting
it. They were found by independent review and are re-measured here.

---

## E-1 — one field carried the pre- and post-ratification values of one recipe, under swapped labels

**Quoted, `artifacts/checkpoints/CP-00/contract-manifest.yaml` as shipped, lines 19–20:**

```
reviewed_manifest_digest: f362647cc9b1d2201ac4663bf5d877346eeeccf046734219103c3ac822d2845d
artifact_manifest_sha256: 39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
```

**Also quoted, the same file's recipe header, line 8:** "Recipe, reproducible from this file
alone:".

**What is true.** The two values are one field over two trees, and the labels were the wrong
way round. Measured with the recipe the file publishes — `git ls-tree -r --name-only <commit>
-- contracts fixtures docs/architecture scripts`, sorted, path bytes then the raw 32-byte
SHA-256 of the content, folded into one SHA-256:

| Commit | What it is | Files | Digest |
|---|---|---|---|
| `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` | the reviewed candidate `W0-QA-01` certified | 100 | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` |
| `2ea7b68b4c4455b03ed4f8437d12f5f35f56af58` | the round-ten frozen candidate | 100 | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` |
| `39a3a6430bd97c38cb20bafc793fc9d077d0df8e` | the ratification commit, which `v0.0.0-architecture` points at | 100 | `f362647cc9b1d2201ac4663bf5d877346eeeccf046734219103c3ac822d2845d` |
| this file's own commit | the recovery candidate | 100 | `a78572288a28b88be7f5dd58b9e79254a9e4f61cb55838ba4308b3be91109b84` |

So `39721aac…` is the reviewed **input** and `f362647c…` the tagged **checkpoint**;
`contract-manifest.yaml` labelled the first as the checkpoint manifest and the second as the
reviewed input. Its `families:` block described the pre-ratification tree, and
`build-info.json` carried the reviewed-input value under the name `artifact_manifest_sha256`
while `manifest.json` carried the tagged-tree value under that same name — two live records,
one field name, two values, and neither saying which tree it described.

**The mechanism, and it is the whole point.** The recipe was published as "reproducible from
this file alone" and named no commit. It is not reproducible from a recipe alone: the same
recipe over four trees of this repository gives three values. Measured at the tagged commit,
`git grep -o 39721aac 39a3a643 | wc -l` returns **36** occurrences and `git grep -l` **13**
files, against **2** occurrences of `f362647c`; the full 64-character form appears 20 times in
12 files, the difference being the abbreviated mentions. The recovery plan's organising note
records 35 sites, which is one short and was carried forward rather than re-measured; the
count here is this task's own.

**What was done.** `artifact_manifest_sha256` now carries one value in all three live
records — the digest of the tree that carries them — and each record states its subject.
The other two aggregates are recorded under their own names, each bound to a named commit.
`contract-manifest.yaml` now lists all 100 members with their own SHA-256, grouped by the
directory that holds them, in 25 blocks whose stated file counts sum to 100 and each of which
carries its own aggregate over exactly those files. Per-file coverage was 9 of 100 and
`scripts/` — the family carrying open security item `E-06` — had none; it is **100 of 100**
now and `scripts/` is enumerated. Counted the way the contour counts, every filename-keyed
SHA-256 anywhere in the record, the total is **109**: the 100 members plus the nine named
artefacts that the report and `W0-INT-01` deliverable 2 call out separately, whose values are
repeated from the member list rather than computed again so the two cannot drift.

---

## E-2 — "all four reviewed families byte-identical" is false in the tree that says it

**Quoted, `artifacts/checkpoints/CP-00/checkpoint-report.md` as shipped, lines 42–43:** "The
reviewed families are byte-identical to the candidate commit: `git diff` over the four
prefixes is empty."

**Quoted, `artifacts/checkpoints/CP-00/known-risks.md` as shipped, lines 6–7:** "the four
reviewed families are byte-identical to `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`."

**What is true.** Three of the four are. `docs/architecture/` is not, and was never meant to
be: ratification reconciles five files inside it, and `manifest.json` declares exactly those
five in `ratification.allowed_delta_paths`. At the tag's own commit the five that differ
from `92e13fa4` are `ADR_INDEX.md`, `ARCHITECTURE_LINT_RULES.md`,
`CP00_ARCHITECTURE_REVIEW.json`, `CP00_ARCHITECTURE_REVIEW.md` and `CP00_OWNER_DECISIONS.md`
— measured by `tests/checkpoint/cp00_final_state.py`, which recomputes the drift between the
tag's commit and the candidate. The mechanism module has always modelled this correctly: its
`IMMUTABLE_REVIEWED_PREFIXES` is three prefixes — `contracts/`, `fixtures/`, `scripts/` — and
`RATIFIABLE_REVIEWED_PREFIX` is the fourth. The prose is what was wrong, not the check.

**What was done.** Both records now state the three-and-one split exactly. The tag's own
annotation carries the same false claim and cannot be edited: `T-2`.

---

## E-3 — the bundle named two artifacts that exist at no commit, and four figures reason from them

**Quoted, `artifacts/checkpoints/CP-00/checkpoint-report.md` as shipped, lines 69–72:**

```
tests/contract/test_cp00_candidate.py moved, with its history, to
tests/checkpoint/test_cp00_mechanism.py. tests/contract/test_cp00_contracts.py
re-exports exactly the classes that check product semantics. The blocking contour is
now 103 tests: 77 semantic plus the 26 validator regressions.
```

(Code spans and bold are stripped from every quotation of a repository path in this
document. The paths named here do not exist, and several records in this bundle have their
path claims machine-checked; writing a non-existent path as a code span would create the
very claim this entry retracts.)

**Quoted, the same file, line 84:** "255 tests." **Line 86:** "Two of those 255 fail".

**Quoted, `artifacts/checkpoints/CP-00/known-risks.md` as shipped, line 22:** "The repair
already exists in this repository — tests/checkpoint/test_cp00_mechanism.py builds its
environment from an allowlist rather than stripping names from the inherited one".

**Quoted, the same file, line 38:** "tests/checkpoint/test_cp00_mechanism.py asserts
`contracts/`, `fixtures/` and `scripts/` byte-identical to the candidate". **Line 88:** "Two
tests in tests/checkpoint/test_cp00_mechanism.py fail as a direct consequence of the contour
split".

**What is true.** Neither module has ever existed. Measured:

```
$ git log --all --pretty=format: --name-only --diff-filter=AM | sort -u | grep -E '^tests/'
tests/characterization/README.md
tests/checkpoint/cp00_final_state.py
tests/checkpoint/test_cp00_final_state_contour.py
tests/contract/README.md
tests/contract/test_cp00_candidate.py
tests/contract/test_cp00_final_state.py
tests/contract/test_validate_bootstrap.py
tests/e2e/README.md
tests/integration/README.md
tests/README.md
tests/replay/README.md
```

Eleven paths under `tests/` across every commit on every ref. Neither name is among them.
`git log --all --follow` reports 0 commits for each. `tests/contract/test_cp00_candidate.py`
has never moved: seven revisions, all at that path. No split was performed, so the 103, 255,
281 and 77 figures partition a suite that does not exist.

**A caution that matters for a later reader.** `tests/checkpoint/` **does** exist in this
tree, and it did not when the claim was written: `git log --all --diff-filter=A -- 'tests/checkpoint/*'`
names `6135f17`, the `W0-QA-04` integration commit, as its first appearance. That directory
holds `W0-QA-04`'s final-state contour. It is a different directory of the same name, made
for a different purpose. The old claim did not come true.

**The contour, measured on the integration tree — the main checkout at `89d2303` with this
task's 27 paths applied.** That commit stays with these figures and is **not** a claim about
the tree this erratum ships in. The clause "which is the tree this erratum ships in" stood
here and is removed: a figure keeps the tree it was taken on for ever, while a sentence
asserting that tree is the current one goes stale the moment the tip moves. `E-13` rules
against exactly that, and this block had already been corrected for it once. Each figure is
what the runner collected, not a static count of `def test_`:

| Command | Collected | Failures | Exit |
|---|---|---|---|
| `.venv/bootstrap/bin/python -m unittest discover -s tests/contract` | 343 | 4 | **1** |
| `.venv/bootstrap/bin/python -m unittest tests.contract.test_cp00_candidate` | 303 | 2 | **1** |
| `.venv/bootstrap/bin/python -m unittest tests.contract.test_cp00_final_state` | 14 | 2 | **1** |
| `.venv/bootstrap/bin/python -m unittest tests.contract.test_validate_bootstrap` | 26 | 0 | 0 |
| `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint` | 47 | 0 | 0 |

**These five figures moved under this task and the previous form of this table did not name a
commit.** It read 340 / 300 / 14 / 26 / 46, which are the figures of the base `6135f17` and of
the integration tip `06be04e`; `c4f2d82` then landed `W0-QA-04`'s third round on `tests/**` and
added three contract tests and one checkpoint test. The failure counts and the four failing
names are unchanged. Re-run the commands rather than trusting the table: that is the rule
`E-13` states, and this table is the case that proved it needed a commit of its own.

Every exit code above is the one the named process returned. The four failures are `L-1`; the
collected counts are what the runner collected, and none of them is a static count of
`def test_`. An earlier draft of this table recorded exit 0 for
`tests.contract.test_cp00_final_state`, which exits 1 — a figure a reader is told to
reproduce that no tree produces, in the entry that exists to condemn exactly that.

**The 103-against-324 figure the recovery plan names.** `checkpoint-report.md` line 52 as
shipped read "bounded contract suite, `discover -s tests/contract` | 103 tests, `OK`, exit
0", in the same report whose own automated verdict row said "324-test contract suite". The
round-ten automated evidence, `automated-summary.txt`, records `Ran 324 tests` at `2ea7b68`.
324 is the number that tree produced; 103 is a partition of it that was never made.
`restore-or-rollback-note.md` line 28 carried the same 103 in a command a restorer is told to
run: `E-7`.

**What was done.** The contour section of `checkpoint-report.md` is replaced with the
measured contour; `known-risks.md` names the modules that exist; and neither record now
writes a non-existent path as a repository path.

---

## E-4 — `build-info.json` pinned the checkpoint to a commit that does not exist, and to a branch that does not contain it

**Quoted, `artifacts/checkpoints/CP-00/build-info.json` as shipped, lines 6–7:**

```
"closeout_branch": "closeout/CP-00",
"closeout_base_commit": "7a9ddcb7b8e8902d68fddec41baa8b48f417dd5f",
```

**What is true.** Measured:

```
$ git cat-file -t 7a9ddcb7b8e8902d68fddec41baa8b48f417dd5f
fatal: git cat-file: could not get object info                       # exit 128
$ git rev-parse origin/closeout/CP-00
4bf235115c2bbeabdcb8a8ae7637acd2ead275bd
$ git merge-base --is-ancestor 39a3a6430bd97c38cb20bafc793fc9d077d0df8e origin/closeout/CP-00
                                                                     # exit 1
```

No object with that SHA has ever existed in this repository. `closeout/CP-00` stands at
`4bf2351`, the commit that voided acceptance round nine before dispatch, and does not contain
the checkpoint. The branch that carries it is `integration/W0.3`, head
`39a3a6430bd97c38cb20bafc793fc9d077d0df8e`. The base the ratification commit was written on
is `2ea7b68b4c4455b03ed4f8437d12f5f35f56af58`, the commit that froze acceptance round ten's
`tested_candidate_digest`, resolved by walking the manifest's own history for the oldest
consecutive revision carrying the live value at the top level and in the round-ten entry.

**What was done.** Both fields corrected in `build-info.json`, each with the measurement
beside it.

---

## E-5 — the documented restore is not executable

**Quoted, `artifacts/checkpoints/CP-00/restore-or-rollback-note.md` as shipped, lines 22–29:**

```bash
git clone <origin> auditmanager && cd auditmanager
git checkout v0.0.0-architecture
```

**What is true.** `v0.0.0-architecture` is a local, unpublished tag. It exists on no remote,
so a fresh clone cannot check it out and the note's first two lines fail for any reader
outside this machine. This is the one deliverable whose entire purpose is to be run by
somebody who was not here.

**Attribution, because this is not measurable from inside this working clone.** The `origin`
of the clone these measurements were taken in is the local checkout
`/root/projects/PDF-Analysis`, not the publication remote, so `git ls-remote` here describes
the local checkout and proves nothing about publication. The publication facts are the
orchestrator's, measured in the main checkout on 2026-09-07 and recorded in
`docs/program/EXECUTION_PLAN.md` §3.4: `origin/main` at `43a84d93`,
`origin/integration/W0.3` at `803d22b8`, and no CP-00 tag on any remote. They are quoted
here with their source and are **not** re-measured by this task. `CP00-B11`'s further claim
that `origin/main` is 47 commits behind is carried the same way.

**What was done.** The restore note now states that the checkpoint is unpublished, gives a
procedure that works from a clone of a repository that has the objects, and says what a
restorer must be given if it does not.

---

## E-6 — a tool the manifest declares unusable as a gate was counted as a ground for the automated PASS

**Quoted, `artifacts/checkpoints/CP-00/checkpoint-report.md` as shipped, line 16:** "|
Automated | `PASS` — validator, 324-test contract suite and the state-record sweep, all exit
0; `automated-summary.txt` |".

**Quoted, `artifacts/checkpoints/CP-00/automated-summary.txt`, line 38:** "exit=0", under the
heading "=== 3. state record sweep ===".

**Quoted against them, `artifacts/checkpoints/CP-00/manifest.json` as shipped at `6135f17`,
`known_pre_ratification_items.sweep_has_no_ratified_state`:** the sweep "models the round
accounting as 'which round is owed', and after ratification no round is owed … Run it with
that in mind rather than as a gate."

The "as shipped at `6135f17`" is load-bearing and was missing through round seven, where
this was the one quotation on the page without the qualifier its neighbours carry. The
sentence is verbatim at the base commit and returns **zero** matches against the live
`manifest.json`, which `W0-INT-02` rewrote in this same round: the live field now reads
"models the round accounting as 'which round is owed', and a ratified checkpoint owes none"
and goes on to state in full that the tool is not a gate of this checkpoint. The quotation
is of the shipped bundle, which is what an erratum quotes; without the qualifier it read as
a quotation of a file that no longer says it.

**What is true.** Both statements were true of the trees they were written about, and
together they are a contradiction the bundle never resolved: one record counts the sweep
among three grounds for the automated verdict while another declares it unusable as a gate.
The `automated-summary.txt` figure is a correct measurement of `2ea7b68`, where the sweep did
exit 0 — it is dated evidence and is not edited. On the integration tree, the main checkout at
`89d2303` with this task's 27 paths applied:

```
$ git rev-parse HEAD
89d23039f75d379471359ddcb28f897f7fe40543
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 239 tracked paths
axis one - superseded commits presented as current: 0
axis two - stale round accounting: 16          # over nine files
                                                                     # exit 1
$ git add artifacts/checkpoints/CP-00/erratum.md   # what the integration commit does
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 240 tracked paths
axis two - stale round accounting: 19          # over ten files
                                                                     # exit 1
```

**The previous form of this block named no commit and carried the base's figures — 238 paths
and axis two 16 — under the words "the tree this erratum ships in".** That is the defect `E-13`
rules against, committed inside the entry that exists to condemn it; the corrected per-tree
figures were already one entry later, in `E-12`, and were not carried across. The block now
names its commit.

**And the block above is round seven's, on round seven's bytes of these 27 paths.** Round
eight rewrote `docs/program/tasks/W0-INT-03.md` and edited `manifest.json`, which moved the
same measurement on the base tree from 16 to 17 and from 19 to 20 — see `E-12`, where the
base-tree pair is re-taken and the extra finding is identified. `89d2303` is not in this
checkout, so the pair above has not been re-taken and moves the same way. It is kept as the
record of the direction. The command is the thing to re-run.

**This figure changes when the integrator commits, and the previous form of this paragraph
got both halves of that wrong.** The sweep enumerates with `git ls-files`, so
`artifacts/checkpoints/CP-00/erratum.md` is invisible to it while it is untracked. Sixteen
names **nine** files and not eight — the sweep prints its own file list and the list was not
read — and tracking this document adds **three** findings and not one: this paragraph,
because it says round eleven is owed; `L-2`'s heading, which says it again; and `E-12`'s
verbatim quotation of the sentence this paragraph replaces. The sweep has no way to read any
of the three as anything but a stale claim. So the sentence reporting the figure is one of the
findings it reports, and correcting it added another. The corrected figures, the command, the
tree, and what the records now assert in place of a total, are `E-12`. 15 was the figure of
the pristine base and it is not a figure of this tree.

Every axis-two finding is the shape the manifest already describes: the sweep has no model of
a ratified checkpoint, so it reads one as a defect and instructs the reader to "Open the next
round in `acceptance_rounds`" — which `tests/contract/test_cp00_candidate.py` refuses. See
`L-2` for the claim, and `E-12` for every site by class and anchor.

**What was done.** `checkpoint-report.md` no longer counts the sweep as a ground for the
verdict and states plainly that it is not a gate; `manifest.json` says so in the same words
and names the contour that replaced it, `tests/checkpoint/cp00_final_state.py`.

---

## E-7 — figures a reader is told to reproduce, that no tree produces

**Quoted, `artifacts/checkpoints/CP-00/restore-or-rollback-note.md` as shipped, line 28:**
".venv/bootstrap/bin/python -m unittest discover -s tests/contract # expect OK, 103 tests".

**What is true.** No tree of this repository produces 103. At the tagged commit the suite
collects 324; on the integration tree `89d2303` with this task's paths, 343. The 103 comes from the split described
in `E-3`, which was never performed.

**Quoted, `artifacts/checkpoints/CP-00/restore-or-rollback-note.md` as shipped, lines 33–34:**
"recomputing them from its own recipe reproduces `artifact_manifest_sha256`
`39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` over 100 files."

**What is true.** Recomputing the recipe at the tag's own commit gives
`f362647cc9b1d2201ac4663bf5d877346eeeccf046734219103c3ac822d2845d`. `39721aac…` is the
reviewed-input value: `E-1`.

**Quoted, `artifacts/checkpoints/CP-00/automated-summary.txt`, line 10:**
"markdown_files=155".

**What is true.** That figure reproduces at no commit. The tree it names, `2ea7b68`, tracks
154 Markdown files: `git ls-tree -r --name-only 2ea7b68 | grep -c '\.md$'` returns 154. The
validator walks the working tree rather than the index, so it counted one untracked file that
was present when the stream ran. The summary is dated evidence bound to `2ea7b68` in its own
first lines and is **not** edited; see `D-2` for why it was not regenerated either.

**What was done.** The restore note's command and digest claim are corrected. The summary is
left as the dated measurement it is, with this entry against it.

---

## E-8 — claims in records this task may not edit

Corrected here by quotation, never by edit, because each is a dated historical measurement
whose alteration would destroy the evidence that makes this audit repeatable.

**`docs/program/reviews/W0-QA-01.md` §9, "Commands and their actual results":** carries the
transcripts `Ran 284 tests` at `:718`, `Ran 26 tests` at `:722` and `Ran 310 tests` at `:726`,
with `Ran 310` repeated at `:3577`, `:3584` and `:3765` — each line number confirmed by
`sed -n` against the file in this tree. The tree that shipped them runs 298 / 26 / 324,
measured by the round-ten manual tester and recorded in `manual-report-round-10.md` F-4. The
integration tree `89d2303` with this task's paths runs 303 / 26 / 343, measured here; at the
base `6135f17` and at `06be04e` the same three commands gave 300 / 26 / 340, and `c4f2d82`
moved them.
The section invites re-execution, so a reader who runs the commands finds different numbers.
`W0-QA-01` is accepted and closed and the file is a forbidden hotspot for every task in the
recovery graph. **Owner: W1.**

**`docs/program/reviews/W0-QA-01.md` line 3656**, mutation #41. The line is confirmed: it
reads "| 41 | the ratified round need not appear at all |
`test_the_acceptance_record_may_not_be_behind_the_manifest` |". That the mutation does not
reproduce — the branch being dead by construction, because the completeness rule above it
already emits the message the named test asserts on — is `manifest.json`'s recorded finding
under `known_pre_ratification_items.unreproducible_mutation_row`, quoted here with its source.
**This task did not re-run the mutation** and does not present the claim as its own.
**Owner: W1.**

**`docs/program/reviews/W0-QA-01.md` §11.19.8**, six rows of the evidence table: read by
`check_state_records.py` as live claims because the sweep binds a claim to the table row
while the "Measured at `4bf2351`" label sits in the introducing paragraph. `manifest.json`
routed these six to `W0-QA-01`, an accepted and closed task — the path right and the actor
wrong, which `docs/program/tasks/W0-INT-01.md` names as the way a defect survives a round, in
the sentence "Assigning an item to an owner who cannot act on it is how the same defect
survived two acceptance rounds." That sentence stood at `:82` at the base `6135f17` and at
`89d2303`, and stands at `:95`–`:96` on the tree this erratum ships in, moved by this task's
own status-banner edit; re-derive it with
`grep -n "who cannot act on it" docs/program/tasks/W0-INT-01.md`.
Re-routed in the manifest. **Owner: W1**, by erratum rather than by edit.

**`docs/program/tasks/W0-QA-01.md`**: quotes the same superseded suite command and the count
281. Frozen by its acceptance; banner only is writable. **Owner: W1.**

**`docs/architecture/ADR_INDEX.md` lines 31 and 41 against 42–43:** the range is widened to
"`PD-01`–`PD-05`" while the result text enumerates only four — "`PD-01`, `PD-02` and `PD-03`
approved with modification, `PD-04` approved". `PD-05` was approved and is recorded in
`CP00_OWNER_DECISIONS.md`. Its substance is carried correctly elsewhere: the round-ten manual
tester verified that `contracts/analysis/v1/stage-registry.json` holds exactly nine stages and
no `optimization*` stage, which is what `PD-05` decided, and that measurement was reproduced
here — the registry's `stages` array has length 9 and no entry's **`stage_id`** is
`optimization`-prefixed: they are `source_preparation`, `page_geometry_extraction`,
`document_context_build`, `text_analysis`, `block_analysis`, `finding_merge`,
`finding_review`, `finding_correction` and `norm_verification`. The earlier form of this
sentence said "the file contains no `optimization`-prefixed name", which is false of the file
— `grep -c optimization contracts/analysis/v1/stage-registry.json` returns 21, in the `XS-11`
exclusion prose that names `optimization_critic`, `optimization_corrector` and
`optimization_review` as the capability `PD-05` moves *outside* the analysis boundary. The
substantive claim was never about the bytes; it is about the `stage_id` set, and it holds. Only the prose enumeration is short. `ADR_INDEX.md` is inside `RATIFICATION_DELTA_CEILING` and outside this task's allowed
paths — `W0-INT-02` may write one field of one architecture file and nothing else. **Owner:
`W0-INT-03`**, at the ratification act, as the one task licensed to reach that file.

---

## E-9 — findings of the accepted manual round that the risk note did not carry

`manual-report-round-10.md` records eight non-blocking findings. `known-risks.md` as shipped
carried none of `F-5`, `F-7` or `F-8`: `grep -c` for each in that file returned 0. A risk note
that silently drops a finding of the round it was accepted on is the failure the note exists
to prevent.

- **`F-5` — token naming.** `ADR-0007:6` says each Attempt carries "lease/heartbeat and
  fencing token" while `contracts/domain/v1/identifiers.json:27` makes `execution_token`
  canonical and `fencing_token` a legacy evidence name only, with `ALR-25` making the
  forbidden name a violation. Both lines confirmed by `sed -n` against this tree. Escalated in
  the tree as `E-ARC02-02`, not concealed.
- **`F-7` — comparison freeze boundary.** `contracts/comparison/v1/README.md:3` says "Freeze
  in S06" — line confirmed — over five separations, three of which its own stage plans gate at
  S07. The stage-plan half is the manual tester's reading and is not re-derived here.
- **`F-8` — the rerun model names no outcome for a `Finding` that is not re-observed**, or
  that reappears on a later run. The adjacent rules are present and fail-closed; the case is
  unnamed in a deferred, owned policy.

**What was done.** All three are now carried in `known-risks.md` with their owners.

---

## E-10 — two canonical copies of one manual report, and a tester without a stable identifier

**Measured:**

```
$ sha256sum artifacts/checkpoints/CP-00/manual-test-report.md artifacts/checkpoints/CP-00/manual-report-round-10.md
a1b68e545861f343887425ae6dca24b10c8bd3cf50d985dcdf767524c2a278ce  .../manual-test-report.md
a1b68e545861f343887425ae6dca24b10c8bd3cf50d985dcdf767524c2a278ce  .../manual-report-round-10.md
```

Byte-identical. `manual-test-report.md` is a named `W0-INT-01` deliverable and
`manual-report-round-10.md` is the round's dated primary report, which is immutable. Two
canonical copies of one document can diverge silently, and only one of them may ever be
edited.

**What was done.** Nothing to the bytes: the round report may not be touched and the
deliverable must exist. The duplication is recorded here, and `manifest.json` binds both to
the same round and the same freeze commit `2ea7b68b4c4455b03ed4f8437d12f5f35f56af58`, so a
divergence between them becomes visible rather than silent. **Owner of a real
de-duplication: `W0-INT-03`**, which can make the deliverable a pointer at the moment it
publishes a new bundle.

**The tester identifier.** `manual-test-report.md:32` records `tester:
cp00_manual_tester, independent manual acceptance stream` — a role, not a stable person or
agent identifier, and `started_at: 2026-09-07T11:42:59Z` beside it. No repository value can
say who ran a manual test; the mechanism module records this as shape rather than content
verification. It is recorded here so that a reader does not mistake the field for
attribution. **Owner: `W0-INT-03`**, to record a stable identifier for the round-eleven
manual stream at dispatch.

---

## E-11 — a universal this reconciliation asserted before it kept it

Found by independent review of `W0-INT-02`'s own work, and recorded here rather than quietly
fixed, because the defect is the one this document exists to condemn.

**Quoted, `artifacts/checkpoints/CP-00/manifest.json`, `artifact_manifest_recipe`, as this
task first wrote it:** "THE COMMIT IS PART OF THE RECIPE. … Every aggregate in this checkpoint
now names its commit, or states 'this file's own commit' where a commit cannot name its own
hash."

**What was true when that sentence was written.** Three aggregates in the same file named no
commit:

- `evidence_bundle_digest`, at the top level and in the round-ten entry, carried
  `8c368f0d…` with no subject at all. The round-ten entry named `2ea7b68` as its
  `candidate_frozen_at_commit`, which is the **wrong tree** for this field: the evidence digest
  is computed after the freeze by construction, because writing `PASS` into a tree changes it.
- `tested_candidate_digest` in the round-seven and round-eight entries named no freeze commit,
  while rounds 5, 6, 9 and 10 did. Round nine named its commit only in prose.

**What is true, resolved by recomputation and not from memory.** The manifest's own recipe,
with the field being computed blanked, was run over every one of the 24 revisions this file has
on any ref. Each value reproduces at exactly one of them:

| Field | Value | Reproduces at | Paths |
|---|---|---|---|
| `evidence_bundle_digest` | `8c368f0d…` | `39a3a6430bd97c38cb20bafc793fc9d077d0df8e` — the **ratification** commit | 230 |
| round 7 `tested_candidate_digest` | `ad26b42f…` | `c1376e1cf0ca39d137c3f88f1a823757de839bef` | 216 |
| round 8 `tested_candidate_digest` | `959d5db2…` | `b21e727500287152f258f405333acb9e72c6b311` | 218 |
| round 9 `tested_candidate_digest` | `ac3a1220…` | `ec63e752e00265aeabde9acf30199c0ab72b5f85` | 221 |
| round 10 `tested_candidate_digest` | `00977a87…` | `2ea7b68b4c4455b03ed4f8437d12f5f35f56af58` | 221 |

The two commits rounds 5 and 6 already recorded were re-run through the same recipe and both
reproduce, so the recovered values and the recorded ones were produced the same way.

**What was done.** `evidence_bundle_commit` and `evidence_bundle_subject` added at the top
level and in the round-ten entry; `candidate_frozen_at_commit` added to rounds seven, eight and
nine, each with the recomputation that recovered it; and `digest_model.every_aggregate_names_
its_commit` states the rule the file now actually keeps. Every non-empty per-round digest in
the manifest names its commit — verified by assertion over the file, not by reading it.

**Why it matters more than its size.** A universal falsified by a value in the same file is
worse than no universal: a reader who trusts the sentence stops checking. This is the
completeness-claim-without-a-check shape that failed rounds six, seven and eight, produced by
the task written to remove it.

---

## E-12 — the one class of figure the previous re-measurement did not reach

Found by the third independent review of `W0-INT-02`'s own work, and recorded here rather
than quietly corrected, for the reason `E-11` gives. `E-11` was a universal falsified by a
value in the same file. This one is a universal falsified by the sentence that states it.

**Quoted, this document, `E-6`, as the second remediation round wrote it:** "Once it is
tracked the sweep reports **17** across ten files rather than 16 across eight, because this
document says round eleven is owed and the sweep has no way to read that as anything but a
stale claim. Measured, not predicted, by running the sweep with that one path added to the
tracked set."

The same pair of figures stood in four other live records, each with its own wording: the
paragraph under "The record of the rounds is itself checked now" in
`artifacts/checkpoints/CP-00/acceptance.md`; the paragraph under **Verdict** in
`artifacts/checkpoints/CP-00/checkpoint-report.md` that removes the sweep as a ground;
the paragraph in `docs/program/CURRENT_STATE.md` that begins "`artifacts/checkpoints/CP-00/
check_state_records.py` was the runnable completeness check"; and
`artifacts/checkpoints/CP-00/manifest.json` under
`known_pre_ratification_items.round_accounting_outside_this_reconciliation`, which added
that the second value "was measured by running the sweep with that one path added to the
tracked set rather than predicted."

**What is true. Both numbers are wrong, and the second one is wrong in the direction that
matters.** Measured on the bytes this document ships in — and on **two** trees, not one,
because this figure moves with the base commit as well as with its own sentence. Every run is
on a `cp -a` copy, never a `git clone`: the suite copies the working tree.

The tree these bytes were written on, base `6135f17` with this task's 27 paths applied,
re-taken in round eight:

```
$ git rev-parse HEAD
6135f17fb76758dc1ab3a7c1195f5421814ba2fb
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 238 tracked paths
axis one - superseded commits presented as current: 0
axis two - stale round accounting: 17
axis two names these files: nine of them
                                                                     # exit 1
$ git add artifacts/checkpoints/CP-00/erratum.md      # what the integration commit does
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 239 tracked paths
axis two names these files: the nine above and this document
                                                                     # exit 1
```

**The untracked figure was 16 through round seven and is 17 here, and the base commit did not
move.** Round eight rewrote `docs/program/tasks/W0-INT-03.md`, which now carries one more
sentence naming the round another record names — the truth-forced table's
`docs/program/CURRENT_STATE.md` row, beside the registry sentence already there. It is `C-3`,
the quotation class: a description of what another document says, read as a claim that the
thing is so. The file list did not move; the count did. This is `E-13` on schedule — the
figure moves with the bytes of the sentences it counts as well as with the base.

**The tracked total is deliberately not stated, and that is round three's decision applied
rather than a gap.** It cannot be stated: the sentences that report it are themselves
sentences naming a round, so the sweep counts them, and the value moves at the exact step that
records it. Round eight measured that directly — writing one total produced a different total,
and correcting it produced a third — which is `E-12`'s own recursion one round later and
§3.6.9's finding verbatim: *the value shifted at the very step that was correcting it, which
is the proof of its unfitness as an object of assertion.* So the record asserts the invariant,
and the total is left to the command:

```
$ git add artifacts/checkpoints/CP-00/erratum.md
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
```

**The invariant, which does not move and is what this bundle rests on: axis one is 0, and
every axis-two finding falls into one of the four classes `E-12` names, none of which is a
stale record.** That held on every tree measured in rounds three through eight, tracked and
untracked, and it is what a reviewer checks. Do not re-state the tracked total here; re-run
the command.

The two figures below were taken in round seven, on those trees **and on round seven's bytes
of these same 27 paths**. Round eight changed two of the 27 — `W0-INT-03.md` and
`manifest.json` — so both figures move the same way the base-tree pair just did, and neither
has been re-taken: those trees are not in this checkout. They are kept as the record of the
direction, not as current values.

The tree the primary reviewer holds, the integration tip `06be04e` with the same 27 paths:

```
$ git rev-parse HEAD
06be04e8f11b7ed6a96aef6966c6185973781dc1
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 239 tracked paths
axis one - superseded commits presented as current: 0
axis two - stale round accounting: 17
axis two names these files: ten of them
                                                                     # exit 1
$ git add artifacts/checkpoints/CP-00/erratum.md
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 240 tracked paths
axis two - stale round accounting: 20
axis two names these files: eleven of them
                                                                     # exit 1
```

And the tree the primary reviewer actually holds, the integration tree `89d2303` with the same
27 paths — the base moved a third time, at `c4f2d82`:

```
$ git rev-parse HEAD
89d23039f75d379471359ddcb28f897f7fe40543
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 239 tracked paths
axis one - superseded commits presented as current: 0
axis two - stale round accounting: 16
axis two names these files: nine of them
                                                                     # exit 1
$ git add artifacts/checkpoints/CP-00/erratum.md
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
tree swept: the working tree, 240 tracked paths
axis two - stale round accounting: 19
axis two names these files: ten of them
                                                                     # exit 1
```

**Six figures, three trees, each named with its commit.** The third tree's numbers are not the
second's, and they are not a correction of them: `06be04e` gave 17 over ten and 20 over eleven,
and both were true there. This total moves with the base *and* with the bytes of the sentences
that state it, which is why nothing in this bundle rests on it — the invariant does, and the
invariant holds on all three: **axis one is 0, and every axis-two finding falls into one of the
four classes above.** Verified on the integration tree, tracked and untracked, after the last
edit of this round.

Deterministic across repeated runs, and identical whether the path is staged or committed.
**The whole of the difference between the base tree and `06be04e` is one path**,
`docs/program/tasks/W1-GOV-00.md`, which does not exist in the base tree's swept set and
carries one `C-3` finding in the tip's. It is not this task's to write. `E-13` records what
follows from that, including the fact that these four numbers will move again the next time
the base does — and the command above, not any of them, is the thing to re-run.

**The path in that sentence was wrong through round seven and is corrected here.** It named
`docs/program/EXECUTION_PLAN.md`, which is false in the only way that matters:
`git ls-tree -r --name-only 6135f17 -- docs/program/EXECUTION_PLAN.md` returns the path, so
it is in the base tree and cannot be the difference between the two trees. `L-1` at the foot
of this document had the right answer all along — ten swept files at the base, eleven at the
tip, the eleventh being `docs/program/tasks/W1-GOV-00.md` — so this sentence contradicted
its own evidence four hundred lines below it while both stood in the same document.

**The false claim was wrong in both halves, and correcting it moved the second one again.**
Sixteen named **nine** files and not eight: the sweep prints its own file list under "axis two
names these files" and the list was not read. And of the bytes the false claim shipped in,
tracking this document added **two** findings and not one — `E-6`'s sentence, and `L-2`'s
heading, which is the erratum's own live statement of the round the recovery owes. So the
sentence reporting the figure was one of the findings it was counting, and it counted neither
itself nor its neighbour. Of the bytes now shipping it adds **three**: the block
quotation of `E-6` at the top of this entry is the third, and *correcting the claim is what
created it*. That is not an untidiness to smooth over. It is the property, measured: a total
whose value includes the sentence stating it cannot be stated without changing it, which is
why the records below assert an invariant and report the total as an observation.

**Why this class survived a re-measurement that was otherwise real.** Every figure whose
value is fixed by the shipping tree was re-taken in the previous round. This one is not fixed
by the tree; it is fixed by the tree *including the sentence that reports it*. It has no
value to state until the sentence exists, and it changes again when the sentence changes.
Iterating to a fixed point would buy a number that the next legitimate edit to any live
record breaks, which is a defect scheduled rather than removed.

**What was done: the claim is moved off the total and onto an invariant.** The total is now
stated as an observation, with the command and the tree it was taken on and nothing resting
on it. What the records assert instead is this:

> **Axis one is 0, and every axis-two finding belongs to one of the four classes below.**

**A fourth clause stood here and is withdrawn.** Until the fourth remediation round the
sentence above ended "none of which is a stale record", and a reader was told that checking
the table against the sweep answered the question *is anything wrong*. It does not, and
`E-13` gives the measurement that shows it does not, the narrower claim that replaces it, and
the one live sentence in this bundle whose truth now rests on a human reading. The reason is
already visible in `C-2` below and was not carried through to the assertion: a class defined
by what the checker cannot read cannot also certify that what the checker cannot read is
current.

`C-1` — **the manifest's terminal state, read by a checker with no terminal state.** Emitted
by `round_truth` against `manifest.json` itself: `current_round` is 10, round ten's own
status is `accepted`, and no entry in `acceptance_rounds` is open. Both findings are true
descriptions of a ratified checkpoint. `manifest.json`,
`known_pre_ratification_items.sweep_has_no_ratified_state`, says so as data.

`C-2` — **a record that states the accounting in words this checker cannot read.**
`MUST_ACCOUNT` requires four records each to carry an owed-round claim and a round-count
claim in one of the shapes the checker matches, so that a record which says nothing cannot
pass for the wrong reason. Three of them fail that, and each for a reason worth naming rather
than fixing by rephrasing to suit a tool that is not a gate:

- `manifest.json` states both as data, in `current_round`, `acceptance_rounds` and
  `supersession`; it is the *source* the checker derives its truth from, and
  `round_problems_json` skips the per-round entries as history by construction, so the record
  of record cannot state the accounting to its own reader in prose.
- `docs/program/CURRENT_STATE.md` states the owed round twice, at the paragraph beginning
  "That ratification is bound to the tree it judged" and in the **Active wave** entry. Both
  sentences also carry the word *superseding*, and `supersed` is in the checker's
  `ROUND_HISTORY_LABELS`, so each unit is read as dated history: excused, and not counted as
  a claim either. The live, forward-looking sense of the word is invisible to it.
  **And the consequence, which the previous form of this entry stated the mechanism of and
  then did not draw: those two sentences can go stale without the sweep moving at all.**
  They are the primary live state record's statement of the round this recovery owes, they
  are excused before they are read, and no automated check in this checkpoint reads them.
  Measured in `E-13`. This is the single most load-bearing live claim in Deliverable 3 and it
  is verified by a reader, not by a checker; it is recorded that way rather than covered by
  an invariant that cannot reach it.
- `docs/program/CHECKPOINT_REGISTRY.md` states the count under "CP-00 — round accounting and
  supersession" as "Ten acceptance rounds are in `artifacts/checkpoints/CP-00/manifest.json`".
  `COUNT_SCOPE` recognises four totality phrasings and that is not one of them.

`artifacts/checkpoints/CP-00/acceptance.md` is the fourth `MUST_ACCOUNT` record and it is
**not** in this class, but it very nearly was, and how it got out is worth one sentence. Until
this repair its only readable owed-round claim sat in the paragraph reporting the sweep's own
figure — an incidental clause in a sentence about a tool. Rewriting that paragraph removed it,
and the first run of the corrected wording moved `acceptance.md` out of `C-3` and into `C-2`
without changing the total: one finding traded for another, invisibly. The claim is now stated
where a reader of an acceptance record looks for it, in the opening sentence of § "Round
eleven", and the trade is recorded here rather than absorbed.

It took two attempts, for the reason `CURRENT_STATE.md` is in this class at all. Written as
the first sentence of the section's opening paragraph, the claim shared a structural unit with
the sentence that follows it, which contains the word *superseding* — so `round_labelled`
excused the whole unit and the claim still did not register. It stands as its own paragraph,
which is the shape `CHECKPOINT_REGISTRY.md` already uses for the same sentence.

`C-3` — **a live record correctly naming the acceptance round this recovery owes.** That
round is eleven; the erratum makes the claim in `L-2` and the manifest carries the
disposition in `supersession.why_round_eleven_is_not_in_acceptance_rounds`, where all three
ways of opening it in `acceptance_rounds` were run against this tree and each is refused by a
frozen check. The checker derives its truth from `acceptance_rounds`, so it reports every
record that states the true thing. Every site in this class is a correct statement and none
is owed to anybody.

`C-4` — **a dated or quoted claim inside a file the checker does not treat as dated.**
`EVIDENCE_PREFIXES` excuses the numbered primary reports and the review reports; it does not
reach a report filed under a name without a round number, nor a needle carried as a string
literal in a test.

**The sites, by path and by an anchor that does not move when the file reflows.** Line
numbers are deliberately not used: every earlier form of this claim was pinned to one, and a
line number is the first thing an edit invalidates.

| Path | Anchor | Class | Findings |
|---|---|---|---|
| `artifacts/checkpoints/CP-00/manifest.json` | `round_truth` over `current_round` and `acceptance_rounds` | `C-1` | 2 |
| `artifacts/checkpoints/CP-00/manifest.json` | `MUST_ACCOUNT`, owed-round and round-count | `C-2` | 2 |
| `docs/program/CURRENT_STATE.md` | `MUST_ACCOUNT`, owed-round | `C-2` | 1 |
| `docs/program/CHECKPOINT_REGISTRY.md` | `MUST_ACCOUNT`, round-count | `C-2` | 1 |
| `artifacts/checkpoints/CP-00/acceptance.md` | § "Round eleven", its opening sentence | `C-3` | 1 |
| `artifacts/checkpoints/CP-00/checkpoint-report.md` | the `**Superseded:**` entry of the header block | `C-3` | 1 |
| `artifacts/checkpoints/CP-00/erratum.md` | `E-6`, the paragraph reporting this figure | `C-3` | 1 |
| `artifacts/checkpoints/CP-00/erratum.md` | `L-2`, its heading sentence | `C-3` | 1 |
| `docs/program/CHECKPOINT_REGISTRY.md` | § "CP-00 — round accounting and supersession", the emphasised sentence closing its first paragraph | `C-3` | 1 |
| `docs/program/tasks/W0-INT-01.md` | its status banner | `C-3` | 1 |
| `docs/program/tasks/W0-INT-03.md` | Part II § "How the delta was established", the truth-forced table's `docs/program/CURRENT_STATE.md` row | `C-3` | 1 |
| `artifacts/checkpoints/CP-00/erratum.md` | `E-12`, the block quotation of `E-6` at the top of this entry | `C-3` | 1 |
| `artifacts/checkpoints/CP-00/manual-test-report.md` | finding `F-1` | `C-4` | 4 |
| `tests/checkpoint/test_cp00_final_state_contour.py` | `test_MUTATION_a_status_row_still_calling_the_checkpoint_blocked` | `C-4` | 1 |

The three `erratum.md` rows are absent while this file is untracked, which is the whole of the
difference between the tracked and untracked run on either tree: on the base tree nineteen
findings over ten files becomes sixteen over nine, and on the integration tip the same three
rows separate the two runs recorded above. The table has fourteen rows because it catalogues
the tree this task can write; the integration tip adds a fifteenth site in a path this task
may not write, `docs/program/EXECUTION_PLAN.md`, class `C-3`, anchored at its statement of the
round the recovery owes. It is listed here rather than in the table for that reason, and
`E-13` says why the distinction is kept. `F-1` is one sentence and four of the checker's five
owed-claim patterns match inside it, which is why one anchor carries four findings; the
checker reports per match, not per site.

**Quoting a claim makes the claim, and the catalogue is written so that it does so once.**
`check_state_records.py` excludes itself from its own sweep because it "quotes what it
searches for". This erratum has no such exclusion, so a verbatim quotation of an owed-round
sentence *is* an owed-round sentence to the checker, and a catalogue that restated the claim
at each of its seven `C-3` sites would have manufactured one new finding per restatement. The rest of this entry therefore names sites
by anchor and refers to `L-2` for the claim itself rather than repeating it — a description
of where a claim lives, not a second instance of it. The one exception is deliberate and is
counted above: the block quotation of `E-6` at the top is the false statement being
corrected, and quoting it in full is what this document is for. It is the twelfth row of the
table and the third of this file's three findings, and the arithmetic is stated here rather
than left for a reader to discover — an entry that silently spent a finding on its own
quotation would be the defect it corrects, one level down.

**The fixed point, demonstrated rather than asserted.** Every total in this entry and in the
four records that carry it was first written as a literal placeholder token; the sweep was run
on those bytes; the measured values were substituted into all five records in one pass; and
the sweep was run again. The same nineteen findings, site for site and class for class. Two
`erratum.md` line numbers moved between those two runs, and the reason is stated rather than
left for a reader to notice: the same pass also rewrote the two sentences the first run had
just proved wrong, so that pair of runs is not a clean isolation of the substitution. Nor was
it the last pair — the `acceptance.md` trade recorded above was found by a later run and
repaired by two more, which is the same lesson from the other side.

The clean isolation was run separately, on a `cp -a` copy of the **final** bytes, with every
figure token replaced by a different one of the same shape and no other change, line counts
identical — 16 to 88, 19 to 77, nine to five, ten to six, three to seven:

```
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
axis two - stale round accounting: 19                     # unchanged
                                                          # exit 1
$ diff <the shipped finding list> <the perturbed finding list>
    the same nineteen findings, the same paths, the same line numbers. The only
    difference is the excerpt the tool echoes back, which contains the changed digits.
```

The figures are inert to both detectors, which is what makes substituting them safe: an
axis-two count claim is a number *immediately followed by* "round" or "rounds", and none of
these is. What is **not** inert is the wording around them. So this is a fixed point of the
substitution and not of the prose: writing a different sentence here moves the total again,
and `E-6`'s three-not-two above is that having already happened, once, inside this repair.
The invariant did not move in any of the three runs, and the invariant is what the records
assert. The totals printed at the top of this entry are from the run on the exact bytes a
reader has in front of them.

**What this costs, recorded rather than argued away.** The catalogue above is exact for these
bytes and will not survive an edit to any live record that adds or removes an owed-round
sentence. It is not a guard: nothing runs it. A reader who wants the current total runs the
command.

A reader who wants to know whether anything is *wrong* gets a **partial** answer from
checking that every path the sweep names appears in the table and that axis one is 0, and the
partiality is the point. That check detects a stale record that introduces a **new path**, and
it detects one on the tree that ships: the base moved under this task between rounds and the
first thing the check reported was an unlisted eleventh path. It does **not** detect staleness
*inside* a path the table already lists, because the finding for such a path is emitted for
its shape and not for its content. `E-13` gives both measurements and the narrower claim that
replaces the withdrawn one. **Owner of a checker that can classify these itself, and of one
that can read the `C-2` sites at all: W1**, with the other `check_state_records.py` items —
the tool is deliberately outside `POST_FREEZE_DELTA_CEILING` and cannot be corrected inside
this round.

---

## E-13 — an asserted guarantee, converted into a declared limitation, and the base that moved twice underneath it

Found by the fourth independent review of `W0-INT-02`'s own work. `E-12` replaced a total
with an invariant and that much stands. This entry records two things `E-12` got wrong about
the invariant it introduced, and a third defect of the same shape that the two of them share
with `L-5` and with the `W0-INT-03` delta.

### The first: the invariant was satisfied by a tree it exists to exclude

`E-12` asserted, and four other live records repeated, that every axis-two finding belongs to
one of four named classes **and that none of them is a stale record**. A reader was told that
checking the table against the sweep answered the question *is anything wrong*.

**Measured.** On the integration tip with this task's paths applied, the two sentences in
`docs/program/CURRENT_STATE.md` that state the round this recovery owes were rewritten to name
a different, wrong round — making the primary live state record false on exactly the axis the
sweep polices — and the sweep was re-run:

```
$ .venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py
axis one - superseded commits presented as current: 0                # unchanged
axis two - stale round accounting: 20                            # unchanged
                                                                     # exit 1
$ diff <the shipped finding list> <the perturbed finding list>
    no output: the same 20 findings, the same eleven paths, the same messages
```

Both suites unchanged. The recipe returned "nothing wrong" on a tree whose central live record
was false.

**The cause is structural, and `E-12` states the mechanism at `C-2` without drawing the
consequence.** `C-2` is *defined* as a record that states the accounting in words this checker
cannot read. A class defined by unreadability cannot also certify that what is unreadable is
current. So the withdrawn fourth clause was **asserted at every `C-2` site and measured at
none** — and the most load-bearing live claim in Deliverable 3 sits at one of them, excused
before it is read because both of its sentences carry the word *superseding* and `supersed` is
in the checker's `ROUND_HISTORY_LABELS`.

**The limit is precise and it is kept — and the "new path" half needs one more qualifier,
found by the fifth review round.** The recipe catches staleness that introduces a **new path**
*only when the stale claim is one the sweep can read*: the sweep reported the eleventh path the
moment this task's base moved, and a simulated post-ratification tree that leaves a readable
stale sentence in a file the table does not list raises the total and the path count together.
Measured on the integration tree, on
`docs/program/waves/W0.3_ratification_integration.md` — a live record `acceptance.md` says both
streams read, and a path the `E-12` table does not name. Append one sentence asserting that a
round below the current one is owed on this candidate, phrased so a cardinal stands immediately
before the word *owed*: axis two goes from `16` to `17` and that file joins the path list.
That is the claim working.

**But phrase the same falsehood as a `C-2` and it introduces nothing at all.** Prefix the very
same sentence with the word *superseding* and append it to the same file: the sweep's entire
output is **byte-identical**, exit 1 before and after, because `supersed` is in
`ROUND_HISTORY_LABELS` and the unit is excused before its round word is read. So the `C-2` hole
is not confined to paths the table already names: a `C-2`-shaped stale claim is invisible in
**any** file, listed or not, and therefore introduces no new path either. The claim that
survives is the narrow one: *a stale live record the sweep can read, in a file the table does
not name, is detected by the new path it introduces.*

Neither sentence is reproduced verbatim here, for the reason this entry already gives below:
quoting a countable claim inside a live record creates one. The first draft of this paragraph
did quote it, the sweep reported the new finding against this very line, and the paragraph was
rewritten as a procedure — `E-12`'s lesson catching its own successor a second time.

What the recipe cannot do, in addition, is catch staleness **inside a path the table already
names**, because the finding for such a path is emitted for the shape of the unit and not for
the truth of its content, and a false round word produces the identical finding to a true one.

### What is claimed now, and what is not

- **Claimed, and measured on the tree that ships:** axis one is 0, and every axis-two finding
  belongs to one of the four `E-12` classes.
- **Claimed, narrowly:** the check "every path the sweep names appears in the `E-12` table"
  detects a stale live record **that the sweep can read** and that introduces a path not in the
  table. It detects nothing about a `C-2`-shaped claim — one carrying `supersed` — in any file,
  listed or not; that variant leaves the sweep output byte-identical. Both halves measured
  above, on the same file and the same tree.
- **Not claimed, and previously asserted:** that the classification shows no live record is
  stale. It does not, and cannot, for the `C-2` sites.
- **Not claimed, and previously asserted:** that the invariant survives the next edit to any
  live record. See the second defect below.
- **The specific live claim whose truth now rests on a human reading, named rather than
  covered:** the two sentences in `docs/program/CURRENT_STATE.md` that state the round this
  recovery owes — the one beginning "That ratification is bound to the tree it judged", and the
  **Active wave** entry. Both are `C-2`. No automated check in this checkpoint reads either.
  A reviewer verifies them against `manifest.json`'s `supersession` object by reading.
- **Owner of a checker that can read a `C-2` site: W1**, with the other
  `check_state_records.py` items. The tool is deliberately outside `POST_FREEZE_DELTA_CEILING`
  and cannot be corrected inside this round, which is the same route `E-12` took for the
  catalogue and for the same reason.

### The second: the durability claim was false

`artifacts/checkpoints/CP-00/acceptance.md` called the invariant one "which survives the next
edit to any live record". It does not, and the counter-example is not adversarial.

**Measured**, on the same tree: appending to `docs/program/CURRENT_STATE.md` a single sentence
that is **true and not stale** — a statement of how many rounds one acceptance stream was
exercised in, phrased so that a cardinal stands immediately before the word *rounds* inside a
unit carrying one of `COUNT_SCOPE`'s four totality markers — takes axis two from `20` to
`21`. The extra finding belongs to **none** of the four classes: the checker reads a true
statement about one stream's rounds as a claim about the acceptance record's total and reports
the mismatch. Two different such sentences were tried and each produced exactly one.

The sentences are **not reproduced here.** Quoting a countable claim inside a live record
creates one, which is `E-12`'s own lesson applied to its successor; the procedure above
reproduces either of them in one line.

**What actually holds, and is what the records now say:** the invariant is stable under
re-measurement of the same tree, and under substitution of the figure tokens for others of the
same shape — `E-12` demonstrates both. It is **not** stable under an edit that adds a countable
claim in a unit the checker can read. "Survives the next edit" was the phrase that made the
invariant sound like a guarantee, and it is withdrawn rather than qualified.

### The third: every figure taken on the base went stale when the base moved

This task was dispatched on base `6135f17`. Between that dispatch and this round the base moved
to `06be04e`, which carries `4e916b0` — `W0-QA-04` resolving the checkpoint tag from the records
at every site. Two claims in this bundle were measured on the base and asserted about the tree
the primary reviewer holds, and both were false there. They are `L-5`'s precondition and the
`--tag` figure in `docs/program/tasks/W0-INT-03.md`; both are repaired at their sites.

**The recurrence matters more than the two instances, because the base will move again.**
`W0-QA-04` is working a third round on the same module: the `RATIFYING_TASK` pin and the
sandbox baseline are named in `L-6` and are exactly what it touches. At `f507d33` that round's
outcome was recorded in `docs/program/EXECUTION_PLAN.md` by `ce42958` and had not yet changed
`tests/**`, so every `L-6` figure below held at that commit.

**It has since landed, and this paragraph's prediction came true.** `c4f2d82` — "resolve the
ratifying task, and take the baseline from before ratification" — is an ancestor of the tip
this task now integrates onto, `89d2303`, and `tests/**` is **not** byte-identical to `06be04e`
there: `git diff --stat 06be04e 89d2303 -- tests/` reports 879 insertions and 99 deletions
across `tests/contract/test_cp00_candidate.py` and
`tests/checkpoint/test_cp00_final_state_contour.py`. The contour figures that moved with it are
re-derived at `E-3` and at every site that carried them. **The `L-6` figures and the
`W0-INT-03` delta rows that rest on `RATIFYING_TASK` were flagged here as owed and not
re-derived**, on the ground that re-deriving them changes what the delta asks the primary
reviewer to do and that this was too large for a closing round. **The sixth round took them,
at the integrator's direction, and the flag was right about the size**: re-derived on the
integration tree, the delta was missing a record, one of its two recorded causes was never a
`tests/**` defect at all, the other named the wrong function and is closed, and the repair
turns out to have preconditions of its own that no actor has met. All of it is at `L-6`, and
the delta rows are repaired at `docs/program/tasks/W0-INT-03.md`. So every claim in this
task's allowed paths that depends on the behaviour of `tests/**` was swept, and the rule
applied to each is:

> **A claim about `tests/**` behaviour carries the commit it was taken on, is anchored to a
> symbol rather than to a line number, and — where a reviewer will act on it — is written as a
> procedure the reviewer runs rather than as a figure this task already took.**

What the sweep found, and what was done:

| Claim | Sites | State at `06be04e` | Disposition |
|---|---|---|---|
| `test_cp00_candidate.py:11342` asserts the tag literal | `L-5`, `manifest.json` `supersession.external_dependency_of_the_delta`, `W0-INT-03.md` Part I step 0.1 | **gone**; `CHECKPOINT_TAG` is resolved by `_resolved_checkpoint_tag` from three record claims | precondition recorded as discharged; the `REJECT` instruction replaced by a check the reviewer runs |
| `cp00_final_state.py`'s `--tag` defaults to the tag literal and reports four tag-integrity findings | `W0-INT-03.md` Part I step 4 | **false**; the default is `recorded_tag(tree)` and reports one, byte-identical to the explicit flag | figure replaced by a procedure: run it both ways and treat disagreement as a finding |
| the constant's own assertion is at `:5826` | `L-6`, `W0-INT-03.md` | **stale**; the assertion was at `:5860` at `06be04e` and `:5826` was a `def` line | first re-anchored to `test_the_ratifying_task_is_anchored_to_the_documents_that_assign_the_act`; that test survives `c4f2d82` and now asserts the series, the floor and the needle rather than an instance, so the pin is gone with the constant. Both line numbers are recorded as history, not as locations |
| `RATIFYING_TASK = "W0-INT-01"` at `:100` | `L-6`, `W0-INT-03.md` | true at `06be04e`; **gone** at the integration tip, where `c4f2d82` replaced the literal with `_resolved_ratifying_task` over a series and a floor | re-derived at `L-6`. The `grep` this row installed still runs and now answers a different question, so `W0-INT-03.md` states both greps and what each answer means |
| the sweep totals, 16 over nine and 19 over ten | `E-12` and the four records that carry it | **base-specific**; the tip gives `17` over ten and `20` over eleven | both trees given, each with its commit, and the command named as the thing to re-run |
| the unlicensed post-freeze path set, "nine … a tenth" | `L-1`, `manifest.json` `supersession` | **base-specific**; eleven at the tip | given per tree with its commit |
| the contour is 340 under `tests/contract` and 46 under `tests/checkpoint` | `E-3`, `manifest.json` | **unchanged** at `6135f17` and `06be04e`; **stale on the integration tree**, where `c4f2d82` makes it 343 and 47 | re-taken on the integration tree `89d2303` and corrected at `E-3`, with the commit now named |
| the four failing contract tests of `L-1` | `L-1` | **unchanged**; same four names on both trees | re-taken on the tip and left as it stands |
| the eight-failure `RATIFYING_TASK` measurement of `L-6` | `L-6` | **stale**; that figure was one field applied to a 340-test contour against a constant that no longer exists | re-taken on the integration tree at `b0b42d6` as a four-row table of one field, one row, both and neither, in `L-6` and in `W0-INT-03.md`. The full-suite half is re-taken with it: 4 failures as it ships, 134 failures and 1 error with item 6 applied |
| `MUST_ACCOUNT`, `COUNT_SCOPE`, `ROUND_HISTORY_LABELS`, `EVIDENCE_PREFIXES` | `E-12` | **stable by construction** — they are in `artifacts/checkpoints/CP-00/check_state_records.py`, which is deliberately outside `POST_FREEZE_DELTA_CEILING` and is byte-identical at both commits | left as symbol references |
| `scripts/validate_bootstrap.py:116` and `tests/contract/test_validate_bootstrap.py:32` | `known-risks.md`, `manifest.json` `open_escalations.E-06` | **unchanged**; that file is byte-identical at both commits | left as it stands, with the commit now recorded here |

**The base moved a second time while this entry was being written, and the rule was exercised
on it.** The tip went from `06be04e` to `f507d33` mid-round. Every figure above was re-derived
against the new tip before this document was finished: `tests/**` and
`artifacts/checkpoints/CP-00/check_state_records.py` are **byte-identical** at the two commits
(`git diff 06be04e f507d33 -- tests/ artifacts/checkpoints/CP-00/check_state_records.py` is
empty), the sweep gives the same totals over the same eleven paths with the same messages, and
the unlicensed post-freeze set is the same eleven. So every figure in this bundle stated at
`06be04e` is true at `f507d33`, and each is left naming the commit it was taken on rather than
being silently re-stamped with a newer one. **It moved a third time, to `89d2303`, and that
move did not preserve `tests/**`** — see the paragraph above; the figures it changed are
corrected at their sites with the new commit named, and the ones the fifth round did not
re-derive were named there as owed. **It moved four more times during the sixth round, to
`fcf7666`, `b0b42d6`, `e8d9e65` and `923881f` while that round was running, and no move touched
`tests/**`**: `git diff --name-only 89d2303 923881f` is
`docs/program/EXECUTION_PLAN.md` and nothing else,
`git diff --stat 89d2303 923881f -- tests/ artifacts/checkpoints/CP-00/check_state_records.py`
is empty, and the unlicensed post-freeze set is the same eleven throughout. So every figure
this bundle states at `89d2303` is true at `923881f`; the ones the sixth round re-took, at
`L-6`, are stated at `b0b42d6` because that is the tree they were taken on, and they were
re-confirmed unchanged at `923881f`. **That is the form to keep: a figure names its commit, and a
reader who needs it for a different tree re-runs the command.** The one thing
that did move was a line number — a finding in `docs/program/tasks/W0-INT-03.md` shifted from
`:250` to `:350` because this round added a section above it, which is the same defect as
`:11342` and `:5826` in miniature and the reason `E-12`'s catalogue anchors to headings.

**The fifth review round found that this sweep was scoped to the wrong thing, and it was
widened.** Everything above is a sweep of claims about `tests/**` — the module where the
symptom had appeared. The defect is not "a claim about `tests/**`"; it is "a line pin", and a
line pin is no safer in a file the writer owns. Two live stale pins were sitting in this bundle
the whole time and no `tests/**`-bounded sweep could reach either, because both pin
`docs/program/tasks/W0-INT-01.md` — a file this task owns and itself moves.

The sweep was re-run against the shape of the defect: **every line pin into every file, over
all 27 paths this task ships, re-derived on the integration tree** (the main checkout at
`89d2303` with those 27 paths copied in) rather than on the base. Three forms were matched —
`<path>:NNN` and `<path>:NNN-MMM`, a bare `` `:NNN` `` code span, and prose "line NNN" /
"lines N, M and P" — giving **84 pin occurrences on the bytes this round received**, each
resolved by hand against the tree that ships. The same extractor over the repaired bytes gives
**100**, and the difference is not new debt: the sixteen added occurrences are this repair
recording the old numbers with the trees they were true of, which is what the fix consists of.
Like the sweep total in `E-12`, this figure counts the sentences that state it; both are given
with the command so a reader re-derives rather than compares. What it found, beyond what the
table above already had:

| Pin | Site | State on the integration tree | Disposition |
|---|---|---|---|
| `docs/program/tasks/W0-INT-01.md` line 180 requires `ratified` | `D-1` | **stale**; `:180` is blank and the requirement is at `:193` | re-anchored to the `## Required tests` bullet asserting `r['review_status']=='ratified'`, with `grep -n "review_status" docs/program/tasks/W0-INT-01.md` as the re-derive; both trees named |
| `docs/program/tasks/W0-INT-01.md:82` names how a defect survives a round | `E-8`, `manifest.json` `known_pre_ratification_items` | **stale**; the sentence is at `:95`–`:96` | re-anchored to the quoted sentence, with `grep -n "who cannot act on it" docs/program/tasks/W0-INT-01.md` as the re-derive; both trees named |

**Both have the same cause, and it is this task's own edit**: the `W0-INT-01` status banner
adds fourteen lines and removes one, so every pin below it moves by thirteen. Correct at
`6135f17`, correct at `89d2303`, wrong on the tree that ships — which is the one the primary
reviewer holds. Each re-derive above was checked to resolve to exactly one line.

Everything else in the 84 resolves. The pins into the frozen families, the immutable round
reports and `docs/program/reviews/W0-QA-01.md` are stable because those files are frozen, and
each was confirmed on the shipping tree rather than assumed; the erratum's own "as shipped,
lines N–M" quotations resolve at the base commit `6135f17`, which is what "as shipped" denotes
— the bundle this erratum corrects, not the tree it ships in; and the `tests/**` pins are
stated as dated measurements naming the commit they were taken on.

**What this does not fix.** The rule above is a discipline applied by hand, not a check. A
figure written tomorrow can still be pinned to a line number, in any file, and nothing in this
checkpoint will catch it. That is `L-7`.

---

## T — the tag annotation

`v0.0.0-architecture` is an annotated tag on `39a3a6430bd97c38cb20bafc793fc9d077d0df8e`. It
is never moved, re-pointed or deleted, and its message is immutable by construction. Three
claims about it are false of its own commit, measured by
`tests/checkpoint/cp00_final_state.py`:

- **`T-1`** — the message states `artifact_manifest_sha256`
  `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08`; the recipe over the
  tag's own commit gives `f362647cc9b1d2201ac4663bf5d877346eeeccf046734219103c3ac822d2845d`.
  It states the reviewed **input** value for the **checkpoint** tree: `E-1` again, in the one
  record that cannot be corrected.
- **`T-2`** — the message claims the reviewed families are byte identical to `92e13fa4`, and
  five differ at the tag's own commit: `E-2`.
- **`T-3`** — `manifest.json` publishes an `artifact_manifest_sha256` that is no longer the
  digest at the tag's commit, because the `review_status` disposition (`D-1`) moved two files
  inside a reviewed family after the tag was cut. The manifest is required by
  `tests/contract/test_cp00_candidate.py` to describe the tree it ships in, and the contour is
  right to say the tag no longer certifies that tree.

**None of the three is repairable by editing anything.** A tag message that is false of its
own commit is corrected by a superseding checkpoint. **Owner: `W0-INT-03`** — cut
`v0.0.1-architecture` on the accepted commit with a message that is true of it, and leave
`v0.0.0-architecture` exactly where it is.

---

## D — recorded dispositions

**`D-1` — the canonical value of `review_status` is `ratified`.** Recorded in
`docs/program/EXECUTION_PLAN.md` §3.6.1 and applied here. `docs/program/tasks/W0-INT-01.md`
requires exactly `ratified`, in the `## Required tests` bullet whose command asserts
`r['review_status']=='ratified'` — re-derive it with
`grep -n "review_status" docs/program/tasks/W0-INT-01.md`, which resolves to one line. That
requirement stood at `:180` at the base `6135f17` and at `89d2303`, and stands at `:193` on
the tree this erratum ships in, because this task's own status-banner edit inserts thirteen
lines above it; `docs/architecture/CP00_ARCHITECTURE_REVIEW.json`
carried `ratified_at_w0_3`. Two mandatory gates of one checkpoint required different values
of one field. **Which side moved: the architecture review.** The alternative — making the
task files require `ratified_at_w0_3` — needs four edits inside
`tests/contract/test_cp00_candidate.py`, and no task in the recovery graph may write that
file, so that branch is unreachable as the graph is written. The deadlock that once produced
`ratified_at_w0_3` is gone: the consistency check compares a **code span**, `` `ratified` ``.
Measured at the reviewed candidate rather than quoted from the plan —
`git show 92e13fa4:docs/architecture/CP00_ARCHITECTURE_REVIEW.md` piped through `grep -o` —
that span occurs **0** times there while the bare word `ratified` occurs **7**.
Cost: four edits — `CP00_ARCHITECTURE_REVIEW.json:6` and the three quotations at
`CP00_ARCHITECTURE_REVIEW.md:34,48,52`, which the consistency check requires to move
together. Zero test edits. Verified after the change:
`_reconciliation_problems`, `_ratification_delta_problems` and `_checkpoint_tag_problems` all
return empty, and the contour's cross-gate axis goes from 2 findings to 0.

**`D-2` — `automated-summary.txt` is not regenerated, and this is a deviation from the
recovery worklist, taken on a measurement.** The worklist directed that it be regenerated
against the tree it ships in rather than annotated. Measured, that would create a finding
rather than close one. The file declares its own subject in its first lines — "Candidate
frozen at 2ea7b68" — so `tests/checkpoint/cp00_final_state.py` classifies it as historical
and verifies its claims against `2ea7b68`; its "221 tracked paths" is exactly what
`git ls-tree -r --name-only 2ea7b68 | wc -l` returns, and the contour's live-versus-historical
axis reports 0 findings on it. It is simultaneously round ten's declared automated report in
`manifest.json`, so it cannot stop being bound to `2ea7b68` without the manifest naming a
different automated report — and the canonical one, `automated-report-round-10.md`, does not
exist. Regenerating its content against this tree while leaving it bound to `2ea7b68` makes
its path count false of its own subject: one correct dated measurement traded for one false
claim. It is therefore treated like the round reports — quoted, not rewritten — with `E-6`
and `E-7` against it, and the fresh measurements of this tree recorded in this erratum
instead. **Owner of a real replacement: `W0-INT-03`**, which produces round eleven's own
automated report.

---

## L — what could not be closed inside this freeze

**`L-1` — four contract-suite tests fail on this tree and no document can close them.**

Measured on all three trees this task was asked about — base `6135f17` with the 27 paths, the
integration tip `06be04e` with the same 27, and the integration tree `89d2303` with the same 27
— and the four are the same four on each, with the same names. The **total** is 340 on the
first two and 343 on the third, because `c4f2d82` added three contract tests; the failures are
4 and the exit is 1 on all three:

```
$ .venv/bootstrap/bin/python -m unittest discover -s tests/contract
FAIL: test_ratification_requires_an_accepted_acceptance_round (test_cp00_candidate.RatificationRecordTests)
FAIL: test_unresettable_names_a_reset_that_did_not_finish (test_cp00_candidate.SandboxResetTests)
FAIL: test_every_file_the_checkpoint_claims_exists_and_every_aggregate_is_enumerated (test_cp00_final_state.FileAndHashAccountingTests)
FAIL: test_the_tag_has_not_moved_and_its_message_is_true_of_its_commit (test_cp00_final_state.TagIntegrityTests)
Ran 340 tests        # 343 on the integration tree 89d2303
                                                                     # exit 1
```

**Re-taken by round seven on `29179c6`** — integrated main after `W0-QA-04` rounds four and
five, with this task's 27 paths copied into a `cp -a` copy, `.git` verified a real directory:
`Ran 343 tests`, `FAILED (failures=4)`, exit 1, and **the same four names**. The checkpoint
suite on that tree is `Ran 59 tests`, `OK`, exit 0 — it was 46 before `29179c6` and the
accounting failure above no longer appears there. Figures move with the base; the names have
not.

Two came with the base commit and two are the contour reporting what `T` and this entry
record.

`test_the_tag_has_not_moved_and_its_message_is_true_of_its_commit` is `T-1`, `T-2` and
`T-3`: a tag message false of its own commit, corrected only by a superseding checkpoint.
**Owner: `W0-INT-03`.**

`test_every_file_the_checkpoint_claims_exists_and_every_aggregate_is_enumerated` carries one
finding — `manifest.json` names `artifacts/checkpoints/CP-00/erratum.md` and this tree does
not *track* it, because it is new and uncommitted. The contour reads `git ls-files`.
Measured, by running the contour over the same tree with that one path added to the tracked
set: the accounting axis goes from 1 finding to 0 and the total from 4 to 3. **Owner: the
integrator**, at the commit that integrates this task. The claim is deliberately left in the
manifest rather than softened into prose: this check is precisely what `E-3` needed and did
not have.

The first two have one cause. The base commit lies outside acceptance round ten's post-freeze
delta ceiling: paths differ from the tree frozen at `2ea7b68` and nothing licenses them. The
set **grows every time the base moves**, so it is given per tree, each with its commit, and
`_post_freeze_delta_problems` is the thing to re-run rather than either list to be trusted:

- at base `6135f17` with this task's 27 paths, **ten**: `artifacts/checkpoints/CP-00/erratum.md`,
  `docs/program/EXECUTION_PLAN.md`, `docs/program/reviews/W0-QA-04.md`,
  `docs/program/tasks/W0-INT-02.md`, `docs/program/tasks/W0-INT-03.md`,
  `docs/program/tasks/W0-QA-04.md`, `tests/checkpoint/cp00_final_state.py`,
  `tests/checkpoint/test_cp00_final_state_contour.py`, `tests/contract/test_cp00_candidate.py`
  and `tests/contract/test_cp00_final_state.py`;
- at the tip `06be04e` with the same 27 paths, **eleven**: the same ten and
  `docs/program/tasks/W1-GOV-00.md`.

Nine of the ten and ten of the eleven are absent from the frozen tree altogether, which is what
the second test measures. By the checkpoint's own rule the round is void and a new one begins; the new round's
freeze is a **commit**, and `_freeze_commit` resolves only through committed history, so no
edit to a working tree can close either failure. **Owner: the integrator**, at the
round-eleven freeze commit. The base commit's own message records both failures as known and
sets the contour as the replacement gate for this task.

**`L-2` — acceptance round eleven is owed and cannot be opened in `manifest.json` inside this
freeze.** Three branches were run against this tree rather than argued:

| Branch | Measured result |
|---|---|
| add a round-11 entry, leave `current_round: 10` | the contour reports "current_round is 10 but acceptance_rounds reaches round 11; a terminal checkpoint's accepted round is the last one" |
| move `current_round` to 11 with `ratified: true` | `_acceptance_problems` requires round 11 to carry verdict `PASS`, both streams `PASS` and two existing primary reports — an acceptance nobody has run |
| set `ratified: false`, which is what an open round means | **4** reconciliation problems, **20** acceptance problems, **1** registry problem — all of them closable, see the correction below |

**CORRECTED by round seven, which built the freeze instead of arguing about it.** The
conclusion above — that round eleven cannot be opened inside this freeze because three
reviewed-family documents are writable by no task in the recovery graph — is **withdrawn**.
The reviewed families are not reverted by authoring pre-ratification prose; they are reverted
by `git checkout 92e13fa4 -- <the five>`, restoring bytes the repository already holds, and
the ratification re-applies them under the `allowed_delta_paths` `W0-INT-03` item 6 declares.
Measured on `29179c6` with this task's 27 paths, on a `cp -a` copy with `.git` verified a real
directory: the revert takes `_ratification_delta_problems` from 1 to 0 and
`_reconciliation_problems` from 4 to 0, and `artifact_manifest_sha256` recomputes to
`39721aac…`, which is the pre-ratification value at `2ea7b68` — the families are back at the
candidate exactly. With the rest of the opening written as `EXECUTION_PLAN.md` §3.8.2 and
§3.9.4 require, **all twelve root-argument `_*_problems` checkers return `[]` on the freeze
commit**, and the thirteenth — `_registry_state_problem`, which takes a root and returns
`str | None` rather than a list — closes with the CP-00 row rewritten to cite
`ratification_blocked`. What is
owed on `manifest.json` inside this freeze is therefore the opening itself, and `W0-INT-02`
owns it: `EXECUTION_PLAN.md` §3.8.5 assigns step 3 to **GOV**, which is this task. The full
list of what the freeze must contain, and the failure set that remains on it, are in
`docs/program/tasks/W0-INT-03.md` under Part I step 0.4, Part I step 1 and Part II "What
remains red on `F`". That set was sixteen when this entry was written and is **four**:
`5d07fe3` repaired the sandbox probe behind twelve of them, and the four that remain are
inherent to a freeze commit.

The twenty break down as 14 "degenerate requirement" and 6 "anchor rot", and **twelve of the
twenty name a task banner — ten of them the banners this task itself added**. That is the
anti-vacuity half of `_task_banner_problems` working exactly as designed: a banner that
already names the tag could not prove a ratification rewrote it. The figure is therefore given
with its composition rather than as a bare count, and it strengthens the conclusion rather
than weakening it. An earlier draft said ten acceptance problems, measured before those
banners existed and never re-measured on the tree the sentence names.

The state "a checkpoint was ratified, that ratification is superseded, and a new round judges
its successor" is not representable in `tests/contract/test_cp00_candidate.py`, which models
three states and not four. That module is `W0-QA-04`'s and is frozen by its acceptance. The
round-eleven disposition is therefore recorded in `manifest.json` under `supersession`, as
data a reader and a reviewer can act on, rather than fabricated in `acceptance_rounds`.
**Owner of the representation gap: `W0-QA-04` if a further round opens on it, otherwise W1.
Owner of opening round eleven: the integrator, at the freeze commit.**

**`L-3` — publication facts are not measurable from inside this clone.** See `E-5`. **Owner:
the integrator**, who alone can address the publication remote.

**`L-4` — three tag-integrity findings stand and are not closable by any edit.** See `T`.
**Owner: `W0-INT-03`.**

**`L-5` — the ratification delta had one precondition outside every path this task owns, and
it has been discharged. This entry now records a procedure instead of a figure.**

The precondition was real when it was written. At base `6135f17`,
`tests/contract/test_cp00_candidate.py:11342` asserted
`self.assertEqual(CHECKPOINT_TAG, "v0.0.0-architecture")` against the live repository, so
moving all three tag claims to `v0.0.1-architecture` turned a required suite red on a line
about the tag rather than about the checkpoint — round nine's shape one file over. It was
routed to `W0-QA-04`, and `W0-QA-04` closed it in `4e916b0`, which is an ancestor of the tip
this task integrates onto. `CHECKPOINT_TAG` is now resolved from the three record claims by
`_resolved_checkpoint_tag`; what is pinned is the series, the floor and the requirement that
the records agree, none of which a superseding checkpoint moves.

Measured on both trees, the tag half of the delta applied to a `cp -a` copy of each and the
exit code read from the process that produced it:

```
$ .venv/bootstrap/bin/python -m unittest discover -s tests/contract

  base 6135f17 + this task's 27 paths, tag half applied
  Ran 340 tests ... FAILED (failures=6)                              # exit 1
      + test_cp00_candidate.TableExpectationTests
            .test_the_checkpoint_tag_resolves_and_the_rule_can_fail
      + test_cp00_final_state.TagIntegrityTests
            .test_the_checkpoint_tag_exists_and_is_annotated

  tip 06be04e + the same 27 paths, tag half applied
  Ran 340 tests ... FAILED (failures=4)                              # exit 1
      the same four this document records at `L-1`, and no more
```

Four against six: on the base the tag half costs two named tests, and on the tree the reviewer
holds it costs none.

**`W0-INT-03` is therefore not told to stop on this condition, and is told how to test for it
instead.** The instruction that stood in `docs/program/tasks/W0-INT-03.md` — repair
`:11342` first, and `REJECT` if it has not landed — named a condition that no longer exists,
and a reviewer who obeyed it literally would have stopped a task that could proceed. It is
replaced there by a check the reviewer runs, which is correct under every version of the
module rather than under the one this was measured on. **Owner of the module: `W0-QA-04`.**
This entry is the record of a precondition met, not of one outstanding; `E-13` records why it
was stated in a form that could go stale, and what was done about the others.

**`L-6` — the ratification commit cannot be green either. Both recorded reasons have been
re-taken, both came out different, and what stops the commit is no longer either of them.**
`L-5` is one line; these were stated as two mechanisms in `tests/**`, and together they
falsified the sentence `docs/program/tasks/W0-INT-03.md` used to carry, "the ratification
commit is the first commit after it that can be green". Both were found by the integrator's
licence audit of the `W0-INT-03` delta. `c4f2d82` — `W0-QA-04`'s accepted third round —
touched both, so both were owed a re-derivation and neither had one; the sixth round of
`W0-INT-02` took them. Everything below was measured on the **integration tree**: the main
checkout at `b0b42d6` with this task's 27 paths copied in by `cp -a`, `.git` verified a real
directory, never a clone, never a linked worktree, with every exit code read from the process
that produced it and no other run in flight.

- **Cause 1 was not a `tests/**` defect. It was a defect in the delta.** The recorded form
  was: `RATIFYING_TASK = "W0-INT-01"`, a module constant in
  `tests/contract/test_cp00_candidate.py`, refuses delta item 6, and
  `_ratification_delta_problems` reports "ratification.task is 'W0-INT-03'; only W0-INT-01
  may ratify CP-00". Owner: `W0-QA-04`. **That constant no longer exists.** `c4f2d82`
  replaced it with a series, a floor and `_resolved_ratifying_task`, which reads every record
  that names the ratifying task — `manifest.json`'s `ratification.task` and the W0.3 wave
  plan's single `CP-00 review ratification` assignment row — and resolves to the value they
  agree on, falling back to the floor when they do not. The message is unchanged; what
  produces it is not a pin but a **disagreement**, and the disagreement was the delta's: it
  moved the manifest field and left the wave-plan row naming `W0-INT-01`.

  Measured, one field or one row at a time, on `cp -a` copies of the integration tree:

  ```
  as it ships                          _ratifying_task_problems 0   _ratification_delta_problems 0
  ratification.task -> W0-INT-03 only  _ratifying_task_problems 1   _ratification_delta_problems 2
  the assignment row -> W0-INT-03 only _ratifying_task_problems 1   _ratification_delta_problems 0
  both                                 _ratifying_task_problems 0   _ratification_delta_problems 0
  ```

  So the delta was **insufficient**, which is the property the integration contract requires
  of it, and the guard was right. Repaired at `docs/program/tasks/W0-INT-03.md`, item 6, which
  now names both records and places them in one step of the forced order. **The second finding
  in the two-problem row is the cascade this document and that file both described as arriving
  later**: `_ratification_record` returns an empty allowed set on any problem, so an
  inadmissible record licenses nothing and all five ceiling files read as undeclared drift.
  It arrives on **this** tree, not at the ratification commit, because round ten's own
  ratification already moved those five relative to the reviewed candidate. The earlier
  statement read that cost off `_reconciliation_problems`, which is 0 here and answers a
  different question.

- **Cause 1's repair costs more than the two records, and that cost is open.** The resolved
  value also derives `RATIFYING_TASK_FILE`, resolves the `{task}` placeholder in
  `RATIFICATION_PUBLICATION_RECORDS`, and selects the `docs/INDEX.md` row
  `_publication_record_problems` reads. Applying item 6 in full to a copy of the integration
  tree and running the contract suite gives `Ran 343 tests`, `FAILED (failures=134, errors=1)`,
  exit 1, against `Ran 343 tests`, `FAILED (failures=4)`, exit 1 as it ships. The four are the
  four this document records at `L-1` and every one of them survives; the **131** added have
  three causes and none is a defect in a guard: `_task_banner_problems` 0 → 2, because
  `RATIFYING_TASK_FILE` becomes `docs/program/tasks/W0-INT-03.md`, which is not in the tree
  frozen as `tested_candidate_digest` and whose banner names no tag;
  `_publication_record_problems` 0 → 1, because the record is row-scoped by
  `program/tasks/{task}.md` and the `W0-INT-03` row of `docs/INDEX.md` carries neither the
  denial nor its retraction; and the harness, where
  `_CheckpointSandbox.publish_program_documents` cannot retract a denial naming `W0-INT-03`
  from a sandbox built on the pre-ratification baseline — that assertion is the message on 72
  of the 131, and 130 of the 131 are in `RatificationRecordTests`, which cannot build its
  post-ratification sandbox at all. **The four preconditions this implies,
  with their owners and the reason the assignment row must move in the ratification commit and
  not before it, are in `docs/program/tasks/W0-INT-03.md` under "The reassignment's
  preconditions". Owners: `W0-INT-02` for two, the integrator for one, and the delta itself for
  the last — not `W0-QA-04`.** This entry records them as open.

- **Cause 2 named the wrong function, and the mechanism it named is repaired and verified.**
  The recorded form was: `_reset_to_the_frozen_tree` rebuilds every sandbox from the freeze
  commit, so after the ratification the anti-vacuity probes are given an anchor already
  changed. `_reset_to_the_frozen_tree` does still resolve `_freeze_commit`, and correctly —
  its question is "is this the tree the acceptance streams judged?", which is that commit by
  definition. The method that builds the *unratified* anchor is `normalise_to_candidate`, and
  `c4f2d82` changed it to resolve `_pre_ratification_baseline()`: the newest tree at or before
  the freeze at which CP-00 was not ratified. Verified rather than attributed, exit code read
  from the process:

  ```
  $ .venv/bootstrap/bin/python -m unittest -v \
      tests.contract.test_cp00_candidate.SandboxResetTests.test_the_baseline_is_a_tree_that_denies_the_ratification \
      tests.contract.test_cp00_candidate.SandboxResetTests.test_MUTATION_taking_the_baseline_from_the_freeze_commit_goes_red \
      tests.contract.test_cp00_candidate.SandboxResetTests.test_normalise_to_candidate_erases_an_ambient_mid_ratification_state
  Ran 3 tests ... OK                                                  # exit 0
  ```

  The middle one is what makes this a verification rather than a reading: it restores the old
  behaviour under `mock.patch`, with the freeze pointed at a ratified commit, and requires the
  anchors the sandbox has just destroyed to name themselves — the guard can fail. **And the
  cause does not arise for a correctly opened round eleven at all.** `F` is frozen with
  `ratified: false` and the denials restored, so `_was_ratified_at(F)` is false, the walk never
  runs and the baseline is `F` itself; the walk is the belt for a freeze taken *after* a
  ratification, which round eleven's is not. On today's tree the walk likewise does not
  execute — the round-ten freeze `2ea7b68` carries `ratified: false` — which is why the
  verification rests on the two probes that force the condition rather than on the tree.

**What is left open, and to whom.** Cause 2: nothing; closed and verified. Cause 1: the
delta's own defect is repaired, and the preconditions its repair creates are open and are
`W0-INT-02`'s and the integrator's, not `W0-QA-04`'s. **The aggregate that stood in
`docs/program/tasks/W0-INT-03.md` — 340 tests, 141 failures at a simulated ratification commit
— is withdrawn rather than restated**: it was taken before `c4f2d82`, before the contour grew
to 343, and on a chain whose two named causes have since been re-derived and one closed.
Building the commit it describes still means opening round eleven and fabricating both
round-eleven primary reports, which no task may do, so it is not replaced by a new figure but
by the procedure in that file's Part I step 4, run on the commit
itself. Do not soften the delta to reach a green suite: the delta was wrong in one row, that
row is repaired, and everything after it is a precondition rather than a licence to record
that `W0-INT-01` performed a ratification it did not perform.


**`L-7` — nothing checks that a line pin in a record still resolves, in any file.**
Three claims in this bundle went stale in one commit and were caught by an independent reader,
not by a gate; `E-13` records them and the rule now applied by hand. The rule is a discipline
and not a guard.

**This entry previously stated its own gap too narrowly, and the narrowness cost two findings.**
The earlier form read: "a records-layer document may pin a line number in a **module it does not
own**". Scoped that way, the mitigation sweep behind `E-13` was bounded to `tests/**` — the
place where the symptom had appeared — and it could not reach two live stale pins that were
sitting in this bundle the whole time. Both pinned `docs/program/tasks/W0-INT-01.md`, a file
this task **does** own and itself moved: `D-1` pinned the `review_status` requirement at
`:180` and `E-8` pinned a sentence at `:82`, and this task's own status-banner edit inserts
thirteen lines above both, so each pin was correct at the base `6135f17` and at `89d2303` and
wrong on the tree that ships. **The sweep was scoped to where the symptom had appeared rather
than to the shape of the defect.** A line pin does not care who owns the file, and a writer is
most likely to invalidate a pin in a file they are editing in the same commit.

**The class, stated as what it is.** Any record may pin a line number in **any** file — one it
owns, one it does not, one it moves in the same commit — and no check in this checkpoint
resolves that pin. The failure mode has three flavours and this bundle has now met all three: a
pin into a frozen module that moves underneath the record (`:11342`, `:5826`); a pin into a file
the record's own author moves (`W0-INT-01.md:180` and `:82`); and a pin into the record's own
neighbour, moved by adding a section above it (`W0-INT-03.md`, `:250` to `:350`).

**What was done about it in this round.** The sweep was re-scoped to the defect: every line pin
into every file, over all 27 paths this task ships, re-derived on the integration tree rather
than on the base. The extractor matched three forms — `<path>:NNN` and `<path>:NNN-MMM`, a bare
`` `:NNN` `` code span, and prose "line NNN" / "lines N, M and P" — and found **84** pin
occurrences. Every one was resolved by hand against the shipping tree. The two above were the
only live stale pins; both are now anchored to a quoted symbol with a `grep` that re-derives
them in one line, and each records the trees its old number was true of. The rest resolve:
those into frozen families and the immutable reports are stable because those files are frozen,
and those into `tests/**` are stated as dated measurements naming the commit they were taken on.

**Still not a check.** A checker that could close this — resolving every `path:NNN`, every bare
`` `:NNN` `` and every named symbol in the records against the tree, and failing when one does
not resolve — is a new checker, which this task's non-goals forbid and `W0-QA-04`'s freeze puts
out of reach. It is also the one gap in this bundle a checker could actually close cheaply,
because a line pin is decidable in a way a stale round word is not. **Owner: W1**, with the
other `check_state_records.py` items. Until then the mitigation is the one `E-13` states, with
the scope corrected: anchor to symbols, carry the commit, prefer a procedure the reader runs to
a figure the writer took — and sweep **every** file, not only the ones someone else owns.
