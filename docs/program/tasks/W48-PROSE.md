# Task W48-PROSE — make surface prose and independent pins fail loudly when stale

## Outcome

D-98, D-99, D-100, D-104, D-105 and D-115 each have a mutation that turns the focused guard
red, while the closed D-76 stale-head exemption remains absent.

## Depends on

- `W48-FREEZE-01` — completed by the docs-only dispatch commit containing this task file
- `MAIN-REF-POLICY-01` — completed at `6118e66`

## Frozen inputs

- frozen code base: `6118e66033380661bb747244e0f7a222fb9a87b4`
- dispatch base: exact `origin/dev` tip carrying `docs/program/W48-FREEZE-01.md`
- API: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`
- error catalog: 22; migration head: `0013_norm_embeddings`
- debt evidence: `DEBT_REGISTER.md` D-76, D-98–D-100, D-104, D-105 and D-115

## Allowed paths

- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `tests/contract/api_v1/test_doc_prose_facts.py`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/P02_SEAMS.md`
- `src/auditmanager/api/app.py` — prose/comments/docstrings only
- `src/auditmanager/api/routers/declarations.py` — prose/comments/docstrings only
- `infra/deploy/**` — tracked prose/comment lines only; executable/configuration values are not
  owned
- `docs/program/W48-PROSE.md`

## Forbidden hotspots

- `contracts/**`, generated clients, error catalog and migrations
- executable runtime/deploy/workflow/composition semantics, root dependencies/locks, `Makefile`
- frontend source/tests and global styles
- `CURRENT_STATE.md`, `DEBT_REGISTER.md`, historical reports, refs, tags and alpha state

## Non-goals

- no contract reseal and no derivation that compares a source to itself
- no generic natural-language parser or claim that arbitrary prose is machine-verifiable
- no rewriting historical evidence; only live prose/comments and a new pin registry
- no executable change hidden beside a comment correction

## Deliverables

- derived tracked-file and textual-subject discovery for surface prose
- pin registry enumerating every independent surface/error/migration/history-boundary pin and
  the event that must move it
- corrections to live stale prose found by the derived scanner
- completion report `docs/program/W48-PROSE.md`

## Required tests

- `.venv/bin/python -m pytest tests/contract/api_v1/test_surface_counts_in_prose.py
  tests/contract/api_v1/test_doc_prose_facts.py -q`
- mutations: unlisted noun, previously excluded extension, `P02_SEAMS.md`, early valid-looking
  historical heading, and one changed pin per registry family each fail for the intended reason
- scanner inventory demonstrates no independent pin outside the registry
- `git diff --check` and an allowed-path-only diff

## Integration contract

The guard derives its candidate files and surface-bearing text from repository evidence rather
than a closed noun/extension list. The registry remains an intentionally independent checklist;
it must not derive expected values from the same artifact it judges. Comment-only source changes
do not alter executable AST/configuration bytes.

## Failure/idempotency/security cases

- decoding/binary/unparseable tracked files are classified explicitly, never silently skipped
- a historical boundary before required live claims fails
- an unknown surface synonym or tracked text extension cannot pass only because it was absent
  from a hand-maintained allowlist
- mutation copies leave the working tree unchanged

## Rollback / feature flag

Guards and documentation only; revert the task commit if the scanner overmatches. No runtime
feature flag or data rollback applies.

## Handoff

- changed files and checks: recorded in `docs/program/W48-PROSE.md`
- contracts: unchanged
- known limits: classify any deliberately unreadable/binary family explicitly
- integration notes: Stage-A judge must independently invent another noun/path/extension
