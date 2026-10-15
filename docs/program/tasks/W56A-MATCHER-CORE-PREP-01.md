# Task W56A-MATCHER-CORE-PREP-01 — pure recorded-evaluation matching

## Outcome

A deterministic, provider-free matcher scores the synthetic AR v2 manifest
against groups of finding observations. It reports seeded recall, control
false-positive pressure, per-category counts, unmatched groups and over-merge.
It creates no baseline or quality verdict.

## Depends on

- `W56A-INT-GENERATOR-01` — complete at `0d7d27bb`;
- `W56A-INT-MERGE-CORE-01` — complete on dev at `68b6f81f`.

## Frozen inputs and contracts

- base `origin/dev=68b6f81f241e00192b52bf0a2cc4351897f06c3c`;
- manifest SHA-256
  `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
- `docs/program/validation/PC-02_PROTOCOL.md` §11's mechanical match rule;
- `W56-PLAN.md` §A3.6's any-member and over-merge rule. No API, domain,
  stage or model contract changes.

## Enumerator ownership

- enumerated_set_changed: no;
- enumerator_path: `fixtures/evaluation/ar_v2/expected_issues.json` (read-only);
- enumerator_owner: `W56A-GENERATOR-PREP-01`;
- totality_query: `tests/contract/evaluation/test_matcher_core.py`.

## Captured premise

The code-first plan §4 allows independent code while MODEL-PIN is blocked.
This pure matcher is a sequential subset of later `W56A-HARNESS-01`, which
still owns the runner, recordings, baseline, live cap and gate thresholds.

## Allowed paths

- `tools/evaluation/__init__.py` and `tools/evaluation/matcher.py` (new);
- `tests/contract/evaluation/test_matcher_core.py` (new);
- this task and `docs/program/W56A-MATCHER-CORE-PREP-01.md` (new report).

## Forbidden hotspots

Existing fixtures and generator, `fixtures/evaluation/ar_v2/baseline.json`,
recordings, `contracts/**`, migrations, application and web code, root
dependencies/locks, `P02_LOCK.json`, composition root, global styles,
`CURRENT_STATE.md`, `VERSION`, refs, tags and stand state.

## Non-goals

No provider call, invented baseline, live spend, runtime activation,
acceptance, full local gate or beta verdict.

## Deliverables and checks

- mechanical match on same bundle/category/page and substring-compatible
  quote, across any group member, without using finding identity;
- distinct seeded/control denominators, per-category rates, unmatched groups
  and over-merge when one group hits two seeded issues;
- refuse empty/duplicated ground truth and malformed predictions rather than
  treating an empty manifest as a perfect score;
- tests with real synthetic manifest and planted cases for any-member,
  boundaries, over-merge, controls, empty prediction and vacuity;
- Python compilation, focused pytest, `git diff --check` and exact path
  proof. No full local gate under R-135.

## Integration contract and rollback

Later HARNESS adapts recorded run outputs to this pure input and owns measured
baseline and thresholds. If an upstream profile changes, recordings must be
remeasured; this module alone never establishes quality. Revert the new files
before use or correct forward after integration. The lane hands its commit to
a dedicated dev integration slot and pushes no ref.
