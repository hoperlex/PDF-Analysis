# Task W52-TRANSLATE-01 — translate human runbooks to English

task_id: W52-TRANSLATE-01

## Outcome

The human-runbook prose in `docs/manual-tests/` is English while Russian
product and fixture text remains verbatim and identifiable to an operator.

## Depends on

- `W52-SEAL-01`, accepted by `W52-INT-B2C-01` on `origin/dev`.
- `W52-RELEASES-API`, accepted by `W52-INT-C-API-01` on `origin/dev`.

## Frozen inputs

- Start from the exact `origin/dev` SHA read back by `W52-INT-C-API-01`;
  record it in the lane report.
- W52 API 30 paths / 37 operations / 83 schemas; 23 error codes;
  migration head `0016_release_notes`; domain revision 9 / 29 identities;
  `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` Stage C TRANSLATE and §8; R-69. D-137–D-140
  retain deferred QA and complete gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: all 14 `docs/manual-tests/*.md` files are inventoried;
  the 11 checkpoint runbooks and their case IDs remain unchanged.

## Captured premise evidence

- premise: the current runbook corpus has six files with Cyrillic text;
  literal path consumers are enumerated for translation review.

### P-01 — current runbook and reader sweep

- captured_at: 2026-10-08
- command: `rg -l '[А-Яа-яЁё]' docs/manual-tests/*.md | sort; rg --files docs/manual-tests | wc -l; rg -l 'docs/manual-tests|ALPHA_PUBLIC_ACCEPTANCE|PC-01_prototype|CP-[01][0-9]_' --glob '!docs/**' --glob '!artifacts/**' . | sort`
- captured_output:
  ```text
  docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
  docs/manual-tests/CP-00_architecture.md
  docs/manual-tests/CP-01_foundation.md
  docs/manual-tests/CP-02_walking_skeleton.md
  docs/manual-tests/PC-01_prototype.md
  docs/manual-tests/README.md
  14
  ./REPOSITORY_TREE.txt
  ./scripts/manual-alpha-check.sh
  ./scripts/validate_bootstrap.py
  ./tests/contract/api_v1/test_doc_prose_facts.py
  ./tests/contract/test_cp00_candidate.py
  ./tests/contract/test_validate_bootstrap.py
  ./tests/contract/tools/fixtures/pin_sweep/w49_before_seal.json
  ./tests/e2e/p02/test_journey_figures_pinned.py
  ./tests/e2e/test_pc01_journey_conformance.py
  ./tests/integration/p02_journey/journey.py
  ./tools/plan/pin_sweep.py
  ```
- interpretation: `PC-01_prototype.md` now contains Russian text after
  SEAL, in addition to the five earlier files. A path hit is a review
  obligation, not permission to edit its reader. The content-window sweep
  from the W52 plan must be repeated before changing any test literal.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/manual-tests/**` — English human prose only, with original Russian
  product and fixture quotations retained and glossed at first use.
- Only when the translation itself forces a change, name and justify each
  edit in the report: `tests/contract/test_cp00_candidate.py`,
  `tests/contract/test_validate_bootstrap.py`,
  `scripts/validate_bootstrap.py`,
  `tests/contract/api_v1/test_doc_prose_facts.py`,
  `tests/integration/p02_journey/journey.py`,
  `tests/e2e/p02/test_journey_figures_pinned.py`.
- `docs/program/W52-TRANSLATE-01.md`; local `agent/w52-translate-01`
  branch/worktree.

## Forbidden hotspots

Every other path, including product/UI code, `scripts/manual-alpha-check.sh`,
contracts, migrations, root dependency/lock files, composition root,
global styles, `origin/dev`, `origin/main`, tags and deployment. Existing
case IDs, front-matter keys, table shapes, figures, digests, paths and
commands are immutable within the runbooks.

## Non-goals

No product copy translation, API reseal, fixture rewrite, new acceptance
steps, release-note prose, full gate, QA, live acceptance or publication.

## Deliverables

- English runbook prose in all 14 files; Russian product/fixture quotes
  preserved and every remaining Cyrillic line accounted for in the report.
- Checkpoint case IDs and count unchanged; current prose counts and head
  accurate; focused tests and a six-part hand-back.

## Required checks

- `rg -n '[А-Яа-яЁё]' docs/manual-tests/` — classify every remaining line
  as a retained product/fixture quote.
- Re-count 11 checkpoint runbooks and compare CP-00 case IDs before/after.
- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/test_cp00_candidate.py -q`
  and `git diff --check`.
- Report any unrun check. Complete `make gate` remains D-140.

## Integration contract

The runbooks remain usable against the current Russian UI: quoted labels,
messages and seeded texts are verbatim. No service ports are reserved or
needed. Hand a clean branch to the integrator after WEB's Stage-C merge;
the following ACCEPT lane writes its new runbook sentences in English.

## Failure / idempotency / security

If a translation changes an executable step, exact expected text or
case ID, stop and correct it before hand-back. Do not hide a stale live
count behind a historical claim. No credentials enter the translated prose.

## Rollback / feature flag

Revert the docs-only candidate with a reviewed development commit if
needed. There is no behavior flag or deployment.

## Handoff

Return changed files, checks/results, contracts, risks, integrator steps
and forbidden-hotspot proof. No checkpoint or tag.
