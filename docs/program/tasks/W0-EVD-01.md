# Task W0-EVD-01 — normalize legacy anchors and bind bootstrap evidence

## Outcome

Make every line-bearing legacy evidence reference in the accepted capability
inventory mechanically resolvable to the exact symbol or explicit line range at the
pinned legacy commit, and bind the recorded bootstrap transcript to the commit whose
119-Markdown snapshot it actually measured.

## Ownership

- implementation owner: agent `/root/w0_behavior_inventory`
- program integrator: primary agent `/root`
- independent reviewer: assigned by integrator; must not author reviewed files
- product/domain approval authority: only if a correction changes capability meaning

## Depends on

- Completed `W0-BHV-01`, accepted at
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`.

## Frozen inputs

- base commit: `ab1cfdab0ec5c413b188a44ff82a99586ecd7994`
- immutable legacy oracle:
  `32b9d903792b30506048a1d42b0e6b2d07aee403`
- original bootstrap package commit:
  `0761df0f21ed415083503bef0218dc29da3585be`
- all contracts, task meanings and migration head: read-only; migration head is none

## Allowed paths

- `docs/behavior/legacy_capability_inventory.md`
- `BOOTSTRAP_VALIDATION.md`

No other path is writable.

## Forbidden hotspots

- `docs/PRODUCT_SYNOPSIS.md`, source traceability and program/current/task docs
- scripts/tests, contracts, fixtures and architecture docs
- root dependency/lock files, migrations, production/composition/global styles
- every mutable legacy worktree/ref; only immutable Git object reads are allowed

## Non-goals

- No capability status, product meaning, journey selection or contract change unless
  exact immutable evidence disproves the accepted claim and owner review is obtained.
- No execution/import of legacy and no reading of credentials, `.env`, untracked
  files, databases or production payloads.
- No claim that descriptive semantic labels are real source symbols.

## Deliverables

- Replace every misleading `descriptive_label@line` with an exact source symbol and
  its definition line, or with an explicit `lines@start-end`/`module@start-end`
  locator when the evidence is a region rather than one symbol.
- Correct the known `projects_v2_shadow` include-router locator from line 242 to 243.
- Split composite evidence where one label previously covered multiple real symbols.
- Keep the full legacy commit SHA on every source reference and preserve the accepted
  24/24, 31/31, 40-capability and 36/36 coverage semantics.
- Label the `markdown_files=119` transcript as evidence from commit
  `0761df0f21ed415083503bef0218dc29da3585be`; do not present it as current output.

## Required tests

- Command: `git ls-tree -r --name-only 0761df0f21ed415083503bef0218dc29da3585be | rg '\.md$' | wc -l`.
  Expected: exact output `119`.
- Command: immutable Git-tree audit of every unique evidence path and every
  symbol/line-range locator in the inventory, recorded in the handoff.
  Expected: every path exists; exact symbols occur at the stated definition line;
  explicit ranges contain the claimed evidence; zero descriptive labels masquerade
  as source symbols.
- Command: `rg -n 'run_migrated_recheck@1436|worker_bootstrap/manager.py:run@118|run_text_differences@690|include_router@242' docs/behavior/legacy_capability_inventory.md`.
  Expected: exit `1` and no output.
- Command: `git diff --check -- docs/behavior/legacy_capability_inventory.md BOOTSTRAP_VALIDATION.md`.
  Expected: exit `0` and no output.
- Independent reviewer samples every changed locator against the immutable Git
  object and confirms no capability semantics changed.

## Integration contract

Fixture authors may treat an evidence locator as mechanically checkable: a symbol is
the literal source symbol at its stated line; a region is explicitly marked as a
range. The bootstrap transcript is historical evidence tied to one immutable commit,
not a moving repository-count assertion.

## Failure/idempotency/security cases

- Ambiguous source region becomes an explicit range; the agent does not invent a
  pseudo-symbol.
- A genuinely contradicted capability stops integration for owner review.
- Re-running normalization over the same immutable commit produces no further diff.
- Sensitive or mutable legacy data is never opened or copied.

## Rollback / feature flag

Documentation/evidence only; no feature flag. Revert only these two evidence files
if a locator correction is wrong.

## Handoff

- changed locators grouped by capability/ledger row
- immutable commands/results and exact coverage totals
- new/changed contracts: none
- known residual ambiguous regions, if any
- confirmation that capability semantics/counts did not change
- allowed-path and forbidden-hotspot proof
