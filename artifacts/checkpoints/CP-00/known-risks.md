# CP-00 — known risks and deferred items

Recorded by `W0-INT-01` at the bounded closeout the repository owner authorised on
2026-09-04; reconciled by `W0-INT-02`. Everything here is open at the moment CP-00 is
ratified. Nothing in this list changes a contract, a schema, an identifier rule, a state
machine, an error contract or a golden expectation.

Three of the four reviewed families — `contracts/`, `fixtures/` and `scripts/` — are
byte-identical to `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`. The fourth,
`docs/architecture/`, is not: ratification reconciles five files inside it, declared in
`manifest.json` under `ratification.allowed_delta_paths`. This paragraph used to claim all
four; `erratum.md`, E-2.

## Security — one open item

### E-06 — the bootstrap validator spawns Git with an inherited environment

`scripts/validate_bootstrap.py:116` calls `subprocess.run(command, capture_output=True,
check=False)` with no `env=`. Git reads configuration from the ambient environment, so a
hostile `HOME`, `XDG_CONFIG_HOME`, `GIT_CONFIG_PARAMETERS` or `GIT_CONFIG_COUNT` can set
`core.fsmonitor`, `core.hooksPath` or `core.attributesFile` with `filter.*.clean`, each of
which Git **executes**. An independent reviewer measured it: under a `HOME` carrying a
`.gitconfig` with `core.fsmonitor`, a seeded victim repository lost every tracked file
from its index while the suite reported success.
`tests/contract/test_validate_bootstrap.py:32` is a second reachable call site.

The pattern of the repair exists in this repository, in the test modules rather than in
the validator: `tests/contract/test_cp00_candidate.py` and
`tests/checkpoint/cp00_final_state.py` each build a subprocess environment from an
allowlist, never reading `os.environ`, rather than stripping names from an inherited one.
Neither is `scripts/validate_bootstrap.py`, and the repair was deliberately **not** applied
there. An earlier form of this paragraph attributed it to a module named
tests/checkpoint/test_cp00_mechanism.py — written here without a code span deliberately,
because it is not a repository path: no such file exists at any commit on any ref, and this
document is one of the records whose path claims are checked. `erratum.md`, E-3 carries the
exact superseded quote. `tests/checkpoint/` exists today, with `W0-QA-04`'s
final-state contour in it — a different directory of the same name, created for a different
purpose. The old claim did not come true. `scripts/` is one of the immutable
reviewed families; the checkpoint's own policy is that no record licenses a byte of change
there, so repairing it inside CP-00 would break the byte identity the checkpoint certifies.

**Owner: W1**, as the first task of the stage that reopens `scripts/` for writing.
**Exposure:** an attacker who already controls the environment of the process running the
validator — a developer-workstation and CI-configuration risk, not a product runtime risk,
since CP-00 ships no runtime. The final manual acceptance read the line directly and
confirmed it is declared, owned and unrepairable inside the freeze.

## Unrepairable inside the freeze, by construction

### The CP-00 mechanism suite freezes the repository against S01

`tests/contract/test_cp00_candidate.py` asserts `contracts/`, `fixtures/` and `scripts/`
byte-identical to the candidate — its `IMMUTABLE_REVIEWED_PREFIXES`, three families and not
four — with the stated policy that no record can license a byte, and pins the reviewed set
at exactly 100 files. The module is at that path and has never been anywhere else. While that assertion runs in a blocking
contour, S01 cannot commit the first OpenAPI document under `contracts/api/v1/**`, add a
helper under `scripts/`, or create `docs/architecture/EXCEPTIONS.md`, which all 33 lint
rules name as the waiver record.

The 2026-09-04 owner decision was recorded as removing the mechanism suite from the
blocking contour. No such removal was performed — see `erratum.md`, E-3 — so the assertion
is still in `discover -s tests/contract` and S01 is not unblocked in practice by it. The disposition that closes it properly — reading the tree of the
`v0.0.0-architecture` tag rather than the working tree, so both sides are immutable and the
assertion becomes a permanent statement about history — is a **W1** decision, at the tag.

### The validator treats any JSON with a top-level `$schema` as a JSON Schema

and requires Draft 2020-12. An ordinary `package.json` or `tsconfig.json` carrying a
schemastore URL therefore breaks a CP-00 gate, and `scripts/` is frozen, so it cannot be
repaired inside the checkpoint. **Owner: W1**, with E-06, in the same task.

### `PD-01`–`PD-04` enumerations inside the frozen candidate

`docs/architecture/ARCHITECTURE_BIBLE.md:9`, `contracts/domain/v1/README.md:962` and
`fixtures/golden/SELECTION.md:19` enumerate four owner decisions where five are of record.
`contracts/` and `fixtures/` are immutable reviewed families and `ARCHITECTURE_BIBLE.md`
is outside the ratification delta ceiling, so editing any of them is undeclared drift.
They are inside the bytes `W0-QA-01` certified and covered by its `ACCEPT`. Recorded so a
later reader does not raise them as new.

`PD-05`'s **substance** is correctly carried: the final manual acceptance verified that
`contracts/analysis/v1/stage-registry.json` holds exactly nine stages and no
`optimization*` name, which is what `PD-05` decided. Only the prose count is short.

## Carried from the accepted manual round, and previously dropped

`manual-report-round-10.md` records eight non-blocking findings. Three of them were absent
from this note as shipped — `grep -c` for each returned 0 — and a risk note that silently
drops a finding of the round it was accepted on is the failure the note exists to prevent.
They are carried here now; the omission is recorded in `erratum.md`, E-9.

### `F-5` — token naming: an ADR body names a field the contracts forbid

`ADR-0007:6` says each Attempt carries "lease/heartbeat and fencing token", while
`contracts/domain/v1/identifiers.json:27` makes `execution_token` canonical and declares
`fencing_token` and `authority_token` "legacy or cross-lane evidence names only", with
`ALR-25` making the forbidden name a violation. Escalated in the tree rather than concealed:
`ARCHITECTURE_LINT_RULES.md` carries it as `E-ARC02-02` and routes it to the program
integrator. `GLOSSARY.md:14` carries the same word with no disposition row. **Owner:** the
integrator, to route to an ADR-owning task in W1. **Does not block:** the behaviour is
unambiguous in the contract that governs it and the divergence is a name in an ADR body.

### `F-7` — the comparison contract's freeze line covers three items its own stage plans gate later

`contracts/comparison/v1/README.md:3` says "Freeze in S06" over five required separations, of
which graphic evidence, AI review/synthesis and repair/undo appear in the S07 contract gate
rather than the S06 one. **Owner:** the CMP contract owner at S06. **Does not block:** it is
a conceptual README in a `not-active` family and asserts no graphic behaviour, so `PD-04`'s
stop condition is not triggered.

### `F-8` — the rerun model names no outcome for a `Finding` that is not re-observed

Nothing in `contracts/`, `docs/architecture/` or `fixtures/` states what happens to a
`Finding` that a rerun does not re-observe, or that reappears on a later run. The adjacent
rules are present and fail-closed — a rerun never rewrites or deletes an earlier observation,
and an unjustifiable match allocates a new `finding_uid` — and the four
`finding_current_verdict` values express no "no longer observed" outcome. **Owner:**
`W3-FND-01`, which owns the finding matcher, or the domain contract owner if the case should
be named in deferred scope now. **Does not block:** an unnamed case in a deferred, owned
policy is not an invented value and not a contradiction.

## Deferred by owner decision

- **`ADR-0014` — deferred.** Not ratified at CP-00 and explicitly out of scope.
- **`U-04`** — retention, legal-hold and tenant/IdP values remain open within their
  recorded scope. No numeric lease, heartbeat, grace, retry/backoff or cost policy is
  ratified here.
- **`U-01`** — open and carried forward, within its recorded scope.
- **`OQ-02`, `OQ-04`** — open.
- **`E-05`** — source-ADR proposed statuses are not inherited as accepted; an integrator
  obligation carried forward past ratification, not closed by it.

## Procedural residue, recorded rather than repaired

Ten acceptance rounds were opened, the tenth being this closeout. Rounds six, seven and eight each
ran in full with both streams. **None of the nine found a contract, schema, fixture,
state-machine, identifier or golden defect.** Every blocker any of them raised lived in the
mechanism that checks the checkpoint. On 2026-09-04 the repository owner ended that
recursion, and the residue it leaves is:

- Four tests fail on the tree this bundle ships in, out of 343 collected by
  `discover -s tests/contract` on the integration tree `89d2303` with this task's paths — 340
  at the base `6135f17` and at `06be04e`, before `c4f2d82` added three. They are **not** the two this entry used to name, and none
  is a consequence of a contour split, which never happened.
  `test_ratification_requires_an_accepted_acceptance_round` and
  `test_unresettable_names_a_reset_that_did_not_finish`, both in
  `tests/contract/test_cp00_candidate.py`, follow from the base commit lying outside
  acceptance round ten's post-freeze delta ceiling — the recovery work is itself the delta —
  and close when the integrator freezes acceptance round eleven.
  `test_the_tag_has_not_moved_and_its_message_is_true_of_its_commit` and
  `test_every_file_the_checkpoint_claims_exists_and_every_aggregate_is_enumerated`, both in
  `tests/contract/test_cp00_final_state.py`, assert the final-state contour is empty on two
  axes: the first carries three tag-integrity findings that only a superseding tag can
  close, the second one finding that closes when `erratum.md` is committed. None is
  repairable by editing a document. `erratum.md`, L-1 and T.
- Two prefix constants in that module are unpinned in the widening direction only;
  narrowing is caught. Measured, not argued.
- Dynamic dispatch — `eval`, `importlib`, `getattr` with a computed name — is not
  resolvable by that module's static spawn enumeration. A test module does not outrank its
  own author.
- Four integrator exceptions are recorded in
  `docs/program/waves/W0.3_ratification_integration.md`, three of one shape and one of
  another. They are for the stage-closing review, not for reopening accepted tasks.
- `docs/program/reviews/W0-QA-01.md` and `docs/program/tasks/W0-QA-01.md` still quote the
  pre-split suite command and count. `W0-QA-01` is accepted and closed; correcting its
  deliverable would reopen it. The split is recorded in `checkpoint-report.md`, which is
  the document a reader of this checkpoint is given.
