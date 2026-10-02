# Task W48-FIX — close the upheld Stage-A discovery false greens

## Outcome

`W48-JUDGE-A` findings `JA-01`, `JA-02` and `JA-03` are independently reproducible and become
red for the intended reason: a whole-surface statement is not admitted by a closed subject
synonym list, a new tracked live path is not admitted by a live-path include list, and an
independent TypeScript contract pin is not invisible to the registry inventory.

This is the single bounded `W48-FIX` slot opened by the Stage-A triage. It repairs only the
instrument findings required to obtain an accepted Stage-A base. Later product work remains with
the disjoint Stage-B owners.

## Depends on

- `W48-FREEZE-01` — completed at dispatch tip `9b5219e`
- `W48-PROSE` — completed and integrated in Stage-A subject `39e06c2`
- `W48-GUARDS` — completed and integrated in Stage-A subject `39e06c2`
- `W48-AUDIT` — completed as report `c11f1b6`
- `W48-JUDGE-A` — completed as report `d5655ec`

## Frozen inputs

- frozen runtime code base: `6118e66033380661bb747244e0f7a222fb9a87b4`
- rejected Stage-A implementation subject: `39e06c2cae7531481da80b0ace70668d26b1416e`
- reports integrated above that subject: `W48-AUDIT.md` and `W48-JUDGE-A.md`
- domain contract: 1.0.0-draft.1 revision 8, 27 opaque identities
- API: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`
- error catalog: 22
- migration head: `0013_norm_embeddings`

## Allowed paths

- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `tests/contract/api_v1/test_doc_prose_facts.py`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/W48-FIX.md`

## Forbidden hotspots

- `contracts/**`, generated clients, error catalog and `db/migrations/**`
- runtime source, frontend source, deployment/configuration semantics and workflows
- root dependency/lock files, `Makefile`, composition root and global styles
- `CURRENT_STATE.md`, `DEBT_REGISTER.md`, owner rulings and immutable judge/audit reports
- tags, deployment state, `origin/dev` and `origin/main`

## Non-goals

- no attempt to repair `W48-AUDIT` `A-01` or `A-02` without a migration/outbox/attempt contract
  owner; both remain release blockers under the frozen migration rule
- no mechanical cross-context import rewrite for `A-03`
- no frontend repair for `A-04`; `W48-WEB` owns that family
- no D-52 register correction for `A-05`; `W48-GOV`/integration owns its append-only addendum
- no natural-language-understanding claim: the guard must instead define and test a conservative
  structural rule whose candidate universe cannot be widened only by editing an include list

## Deliverables

- tracked-text source discovery that includes a new live path by default and explicitly excludes
  only test fixtures, immutable historical evidence and canonical machine artifacts
- whole-surface claim detection that catches both judge sentences without adding their exact
  subject phrases as one-off aliases
- a language-independent pin inventory for Python, TypeScript and TSX test sources, including
  every already-present independent frontend error-catalog count
- adversarial tests for the exact `JA-01`/`JA-02`/`JA-03` probes and neighbouring counterexamples
- `docs/program/W48-FIX.md` completion report

## Required tests

- `/root/projects/PDF-Analysis/.venv/bin/python -m pytest
  tests/contract/api_v1/test_surface_counts_in_prose.py
  tests/contract/api_v1/test_doc_prose_facts.py -q` — all pass
- staged/synthetic `scripts/judge-surface.toml` with `The API surface has twelve facets.` — red
- tracked/synthetic live text with `The complete HTTP interface exposes twelve endpoints.` — red
- the same stale count in a test fixture or immutable historical record — excluded only by the
  declared role rule, not an extension/path omission
- unregistered `web/tests/contract/*.test.ts` with `const FROZEN_OPERATION_COUNT = 12` — registry
  completeness red
- each registered Python and frontend pin changed alone — its exact `pin_id` red
- `git diff --check`; allowed-path-only diff; focused suite re-run from a clean tree

## Integration contract

The prose guard consumes Git's tracked UTF-8 inventory. A new live file does not require adding
its parent directory or suffix to a scanner include list. Exclusions are role-based, explicit and
mutation-tested. Whole-surface claims are judged by totality plus historical/current contract
values, while exact local-subset and historical exceptions remain registered by path and phrase.

The pin registry inventory scans maintained test sources in all repository test languages it
currently has (`.py`, `.ts`, `.tsx`). It admits symbolic frozen literals and narrowly specified
semantic count assertions; derived values, HTTP statuses, fixture sizes and local enum counts are
not pins merely because their number equals a surface value.

## Failure/idempotency/security cases

- binary, non-UTF-8 and unreadable tracked files remain explicit classifications
- adding a new extension or top-level live path requires no scanner edit to become visible
- a new whole-surface synonym cannot evade the totality rule
- comments/string literals cannot manufacture TypeScript executable-pin syntax
- duplicate registry IDs, missing needles, unregistered paths and per-path overflow fail loudly
- mutations run in memory or disposable copies and restore the tree

## Rollback / feature flag

Guard and documentation changes only. Rollback is a revert of the W48-FIX commit; no feature
flag, data migration or host action applies.

## Handoff

- changed files: recorded in `docs/program/W48-FIX.md`
- commands/results and every red mutation: recorded in the completion report
- contracts: unchanged
- known limits: `A-01` and `A-02` still prohibit alpha release/tag closure
- integration notes: accept Stage A only after a clean focused run and complete `make gate` on the
  merged exact SHA; do not push either remote ref from this task
