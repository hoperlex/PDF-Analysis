# Task W56A-INT-MATCHER-CORE-01 — publish offline matcher on dev

## Outcome

`origin/dev` contains the pure W56a seeded matcher after the corpus and merge
core, without a baseline or provider activation.

## Depends on

- `W56A-INT-MERGE-CORE-01` — complete at `68b6f81f`;
- `W56A-MATCHER-CORE-PREP-01` — complete at `98aa2df5`.

## Frozen inputs and contracts

- remote predecessor `68b6f81f241e00192b52bf0a2cc4351897f06c3c`;
- source SHA `98aa2df5c12f05f1efd55fc90ecdb8ee3091fe04`;
- seeded manifest SHA-256
  `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
- migration head `0022_findings_v2`; API/domain/stage and model lock unchanged.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `fixtures/evaluation/ar_v2/expected_issues.json` (read-only);
- enumerator_owner: `W56A-GENERATOR-PREP-01`;
- totality_query: `tests/contract/evaluation/test_matcher_core.py`.

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W56A-INT-MATCHER-CORE-01.md at `e61fc457`
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths and publication authority

- `docs/program/CURRENT_STATE.md`, this task and
  `docs/program/W56A-INT-MATCHER-CORE-01.md`;
- fast-forward `origin/dev` from the frozen predecessor to the checked
  integration commit. No `origin/main` or tag authority.

## Forbidden hotspots

Existing corpus, `baseline.json`, recordings, contracts, migrations, source
runtime, root dependencies/locks, `P02_LOCK.json`, composition root, global
styles, `VERSION`, stand state and `origin/main`.

## Non-goals

No measured quality verdict, recorded run, paid call, live/manual acceptance,
full local gate or beta release.

## Deliverables and checks

- fast-forward exact source commit and update current-state claim;
- focused matcher tests and compilation on integration tree;
- `git diff --check`, three allowed-doc integration diff, clean tree;
- re-read remote predecessor before normal fast-forward push and verify the
  resulting remote ref.

## Integration contract and rollback

HARNESS later consumes this function and owns recordings, baseline, spend,
threshold and gate. If the remote ref moved, stop and remeasure. Before
dependent use, revert the new matcher; afterward correct forward. Report
files, checks, pins, limitations, ref and forbidden-hotspot proof. The
two-gateway model identity requirement remains binding.
