# Task W0-CLN-01 — retire point-in-time notes overtaken by the `ID-01` chain

> **Status: backlog draft. Not executable yet.**
> `AGENTS.md` §2 allows `depends_on` to name completed task IDs only. `W0-EVT-01` has
> not run. Pin its integration commit below and this task becomes executable
> unchanged.

## Outcome

Remove two stale point-in-time statements that the completed `ID-01` chain has
overtaken, so no CP-00 artifact carries a claim its neighbour contradicts.

Both are text. Neither changes a rule, a code, a state, an identifier, a schema
constraint or any value a consumer reads.

## Problem

Two artifacts recorded facts that were true when written and became false when the
work they described landed.

**Architecture.** `ARCHITECTURE_LINT_RULES.json` records in `open_items` that
`ALR-24` is contradicted by repository state, because `scripts/validate_bootstrap.py`
requires a bare `version` key, and that an enforcement run of `ALR-24` and the
validator cannot both be green until `W0-QA-03` and `W0-DOM-02` are integrated. The
matching `conflicts_checked_not_escalated` entry for `ALR-24` repeats it. Both are now
false: the validator reads `contract_version`, and the mirror is gone.

**Domain.** `identifiers.json` and `state-machines.json` carry, inside
`revision_note`, the sentence *"contract_version stays 1.0.0-draft.1 because no
1.0.0-draft.1 artifact was ever committed or frozen"*. The candidate was committed at
`cf7740474b1786163f54d93b013a0d526ef989e0`, so the stated reason is false, and it
directly contradicts the family's own README, which now records the candidate as
committed but neither frozen nor ratified. `error-codes.json` is already correct.

`W0-DOM-02` could not fix the domain half: those two catalogs were single-value paths
where only `candidate_revision` could change, and editing the string would have been a
scope violation. The repository owner accepted the round-4 note lag as historical, and
separately directed that this specific false claim be closed here rather than left
standing into the freeze.

## Ownership

- implementation owner: one assigned agent for both halves
- program integrator / freeze governor: primary agent `/root`
- independent reviewer: assigned by the integrator; must not author the reviewed text
- product/domain approval authority: not required; no product semantics change

One task deliberately spans two families here. The rule that one hotspot has one owner
per wave is satisfied — a single agent owns both path sets, no other task writes either
while this runs, and responsibility is undivided. Splitting two four-line text
corrections into two tasks would add ceremony without adding a control.

## Depends on

- `W0-EVT-01`, integrated at `<pending integration commit>`. Running earlier would
  rewrite notes about a chain that is not yet finished.
- `W0-DOM-02`, integrated at
  `478d32e90d1cbb2c691e0ac0b61b68dadcf0d397`, and `W0-QA-03`, integrated at
  `23dddf99f833d12cd4cc22d11e224d4b278872bf`, which are what make both statements
  false.

## Frozen inputs

- base commit: the `W0-EVT-01` integration commit
- accepted lint-rule specification from `W0-ARC-02`
- accepted domain candidate as left by `W0-DOM-02`, revision 5
- `docs/architecture/CP00_OWNER_DECISIONS.md` for `ID-01`; read-only
- migration head: none

## Allowed paths

Architecture half:

- `docs/architecture/ARCHITECTURE_LINT_RULES.json`
- `docs/architecture/ARCHITECTURE_LINT_RULES.md`

Domain half, `revision_note` string only:

- `contracts/domain/v1/identifiers.json`
- `contracts/domain/v1/state-machines.json`

No other path is writable.

## Forbidden hotspots

- every other `contracts/**` path, including `error-codes.*` and all four schemas
- `scripts/**`, `tests/**`, fixtures, program and checkpoint documents
- `docs/architecture/ADR_INDEX.md` and `docs/architecture/adr/**`
- root dependency/lock files, migrations, composition root, global styles
- every legacy repository file, ref and worktree entry

## Non-goals

- No rule added, removed, renumbered, rescoped or re-severitied; the 33 `ALR-*` rules
  and their `enforcement`/`severity` values stay exactly as accepted.
- No change to `candidate_revision`, `contract_version`, any code, identifier, state,
  transition or schema constraint.
- No new escalation and no resolution of an existing one.
- No claim that any rule now passes: the specification still makes no compliance claim.

## Deliverables

1. The `ALR-24` `open_items` entry is rewritten to record the resolution: the
   contradiction existed against repository state at the `W0-ARC-02` base commit, and
   was closed by `W0-QA-03` and `W0-DOM-02`, naming both integration commits. Keep the
   history — the entry says what was true and when it stopped being true, rather than
   disappearing as though it never applied.
2. The `ALR-24` `conflicts_checked_not_escalated` entry drops the same stale clause and
   keeps its actual finding, that `ADR-0003` names no version key and is therefore not
   contradicted.
3. `ARCHITECTURE_LINT_RULES.md` is updated wherever it mirrors either statement, so the
   two artifacts agree.
4. In `identifiers.json` and `state-machines.json`, the clause *"because no
   1.0.0-draft.1 artifact was ever committed or frozen"* is replaced by the true
   reason: the contract version does not move because the round redefined no meaning,
   while round-to-round distinguishability is carried by `candidate_revision`. The rest
   of each `revision_note`, including its round-4 framing, is left alone — the owner
   accepted that lag deliberately.

## Required tests

- Command: `.venv/bootstrap/bin/python -c "import json,glob; bad=[p for p in glob.glob('contracts/domain/v1/*.json')+glob.glob('docs/architecture/ARCHITECTURE_LINT_RULES.json') for t in [open(p).read()] if 'never committed' in t or 'was ever committed' in t or 'cannot both be green' in t]; assert not bad, bad"`.
  Expected: exit `0`; neither retired claim survives in either family.
- Command: `.venv/bootstrap/bin/python -c "import json,subprocess; base='<the commit this task started from>'
import re
for p in ['identifiers.json','state-machines.json']:
    rel='contracts/domain/v1/'+p
    old=json.loads(subprocess.run(['git','show',f'{base}:{rel}'],capture_output=True,text=True,check=True).stdout)
    new=json.loads(open(rel).read())
    old.pop('revision_note',None); new.pop('revision_note',None)
    assert old==new, p
print('domain halves differ in revision_note and nothing else')"`.
  Expected: exit `0`. Verify this gate rejects as well as accepts before trusting it:
  a change to any other key in either catalog must fail it.
- Command: `.venv/bootstrap/bin/python -c "import json,collections; s=json.load(open('docs/architecture/ARCHITECTURE_LINT_RULES.json')); r=s['rules']; assert len(r)==33; assert dict(collections.Counter(x['enforcement'] for x in r))=={'static':21,'review':10,'test':2}; assert dict(collections.Counter(x['severity'] for x in r))=={'error':32,'warning':1}; assert sum(1 for x in r if x['enforcement']=='static' and x['severity']=='error')==20"`.
  Expected: exit `0`; the accepted rule set is untouched.
- Command: the two `W0-ARC-02` required tests and Gates A–F, extracted from
  `ARCHITECTURE_LINT_RULES.md` and executed exactly as written.
  Expected: all exit `0`, as they did at acceptance.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with a standalone `PASS`.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract -p 'test_validate_bootstrap.py'`.
  Expected: exit `0`.
- Command: `git status --porcelain -- contracts docs fixtures scripts tests requirements`.
  Expected: exactly the four declared paths and nothing else.
- Independent reviewer confirms both retired statements are gone, that each was
  replaced by a true statement rather than deleted into silence, and that no rule,
  code, schema constraint or revision value moved.

## Integration contract

After acceptance, no CP-00 artifact asserts that the domain candidate is uncommitted
or that `ALR-24` and the bootstrap validator cannot both be green. The lint rule set,
the domain contract version and the family revision are exactly what they were at
acceptance of `W0-ARC-02` and `W0-DOM-02`.

## Failure/idempotency/security cases

- A retired statement is replaced by the true one, never deleted without a successor:
  a reader must be able to see what the artifact previously claimed and why it changed.
- Re-running is a no-op once both claims are gone; it cannot edit a second field.
- No credential, payload or path content is introduced.
- `U-04` stays open; no tenant, IdP, TTL, retention or legal-hold value appears.

## Rollback / feature flag

Text-only; no feature flag. Revert the four paths as one unit before freeze. After
freeze, a change to either artifact follows the freeze-break procedure.

## Handoff

- changed files split by half, with the before and after text of each retired statement
- commands/results, including the reject direction of the domain-half gate
- new/changed contracts: `none`; no rule, code, constraint or revision moved
- known limits: the round-4 framing of both `revision_note` strings is retained by
  owner decision and is not a defect
- integration notes for `W0-QA-01`, which reviews the converged set immediately after
- allowed-path proof via `git status --porcelain`
