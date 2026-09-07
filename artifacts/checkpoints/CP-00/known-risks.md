# CP-00 — known risks and deferred items

Recorded by `W0-INT-01` at the bounded closeout the repository owner authorised on
2026-09-04. Everything here is open at the moment CP-00 is ratified. Nothing in this list
changes a contract, a schema, an identifier rule, a state machine, an error contract or a
golden expectation; the four reviewed families are byte-identical to
`92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`.

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

The repair already exists in this repository — `tests/checkpoint/test_cp00_mechanism.py`
builds its environment from an allowlist rather than stripping names from the inherited
one — and it was deliberately **not** applied here. `scripts/` is one of the immutable
reviewed families; the checkpoint's own policy is that no record licenses a byte of change
there, so repairing it inside CP-00 would break the byte identity the checkpoint certifies.

**Owner: W1**, as the first task of the stage that reopens `scripts/` for writing.
**Exposure:** an attacker who already controls the environment of the process running the
validator — a developer-workstation and CI-configuration risk, not a product runtime risk,
since CP-00 ships no runtime. The final manual acceptance read the line directly and
confirmed it is declared, owned and unrepairable inside the freeze.

## Unrepairable inside the freeze, by construction

### The CP-00 mechanism suite freezes the repository against S01

`tests/checkpoint/test_cp00_mechanism.py` asserts `contracts/`, `fixtures/` and `scripts/`
byte-identical to the candidate, with the stated policy that no record can license a byte,
and pins the reviewed set at exactly 100 files. While that assertion runs in a blocking
contour, S01 cannot commit the first OpenAPI document under `contracts/api/v1/**`, add a
helper under `scripts/`, or create `docs/architecture/EXCEPTIONS.md`, which all 33 lint
rules name as the waiver record.

The 2026-09-04 owner decision removes the mechanism suite from the blocking contour, which
unblocks S01 in practice. The disposition that closes it properly — reading the tree of the
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

Nine acceptance rounds were opened before this closeout. Rounds six, seven and eight each
ran in full with both streams. **None of the nine found a contract, schema, fixture,
state-machine, identifier or golden defect.** Every blocker any of them raised lived in the
mechanism that checks the checkpoint. On 2026-09-04 the repository owner ended that
recursion, and the residue it leaves is:

- Two tests in `tests/checkpoint/test_cp00_mechanism.py` fail as a direct consequence of
  the contour split: the sandbox-reset expectation, and an assertion that `W0-QA-01` owns
  exactly two paths, which a three-file layout makes false. Both are the mechanism's
  bookkeeping about its own location. Repairing them is the recursion that was ended.
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
