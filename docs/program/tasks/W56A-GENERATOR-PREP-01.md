# Task W56A-GENERATOR-PREP-01 — deterministic synthetic AR v2 corpus

## Outcome

About ten byte-stable synthetic portal PDF bundles cover all seven v2 text
categories with at least three grounded positive cases and one near-miss
control per category. They can test the future recorded evaluation harness
without any live model call or customer document.

## Depends on

- `W55B-INT-CLOSE` — complete;
- `W56A-RULE-01` — complete, category scope R-129/R-134;
- `W56A-DEV-FREEZE-01` — complete on the published dispatch tip.

## Frozen inputs

- code base: `d600fe69777c923e246d89bc4a9451c3974eaf53`; resolve the
  documentation-only dev dispatch tip and record it;
- API contract SHA-256
  `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`;
- domain candidate revision 12, error-code SHA-256
  `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`;
- analysis stage-registry SHA-256
  `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`;
- migration head `0021_portal_bundles` on the code base; SEAL owns its
  successor. Generator does not migrate or change contracts;
- seeded corpus case specification: `W56A-FREEZE-01.md` §3; category
  rules in W56 plan §A3.6, R-129 and R-134.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `fixtures/evaluation/ar_v2/expected_issues.json`
- enumerator_owner: `W56A-GENERATOR-PREP-01`
- totality_query: `.venv/bin/python tools/fixtures/seeded/generate.py --check`

The generated fixture manifest enumerates only synthetic cases. It is not
the API or domain category enumerator; SEAL owns those.

## Captured premise evidence

- premise: no seeded AR v2 corpus or generator paths exist on the frozen base

### P-01 — existing path inventory

- captured_at: 2026-10-15
- command: `rg --files tools/fixtures fixtures/evaluation tests/contract | rg 'ar_v2|fixtures_seeded|seeded'`
- captured_output:
  ```text
  (no matching paths; exit 1)
  ```
- interpretation: these new path families are free for this task; this does
  not measure their eventual quality.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/fixtures/seeded/**` (new files only, including generator CLI);
- `fixtures/evaluation/ar_v2/**` (new synthetic bundles, manifests and
  `expected_issues.json`) **except** `baseline.json`;
- `tests/contract/fixtures_seeded/**` (new contract tests only);
- `docs/program/W56A-GENERATOR-PREP-01.md` (new lane report).

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies/locks, `P02_LOCK.json`,
  composition roots, global styles, `VERSION`, release notes;
- `fixtures/evaluation/ar_v2/baseline.json`,
  `fixtures/recorded/**`, `tools/evaluation/**` (later HARNESS owner);
- all `src/**`, `web/**`, existing customer/owner fixtures and stand data;
- `origin/dev`, `origin/main`, tags and provider credentials.

## Non-goals

- no model recording, recall/precision baseline or live quality verdict;
- no contract seal, migration, runtime logic or activation;
- no full local gate, browser/manual acceptance or paid call.

## Deliverables

- deterministic PDF/portal-bundle generator and a `--check` mode;
- `expected_issues.json` with at least 21 positive cases (three per
  category) and seven near-miss controls (one per category), across at
  least two bundles per category;
- every positive cites an exact page and a verbatim quote from the PDF
  text layer. Portal descriptions and recognised-only text are never
  citation sources. A missing-content issue names an explicit promise in
  the supplied set, never an assumed norm or checklist;
- byte-stable generated artefacts and tests that detect mutations in
  positive and control cases.

## Required tests

- `.venv/bin/python tools/fixtures/seeded/generate.py --check` — two
  generations match byte for byte; declared members match stored bytes;
- `.venv/bin/python -m pytest tests/contract/fixtures_seeded -q` — all
  seven categories meet 3-positive/1-control minimum, quote/page integrity,
  missing-promise scope and per-case mutation checks;
- `git diff --check` and allowed-path proof. No full gate under R-135.

## Integration contract

The corpus is a deterministic fixture input for the later HARNESS task.
Merge it after SEAL so its categories and manifests can be checked against
the newly sealed enum. No baseline figure may be invented from generator
expectations. The later evaluation task owns `baseline.json`, recordings,
matching and quality-gate thresholds.

## Failure/idempotency/security cases

- Regeneration with identical inputs must yield identical bytes and IDs.
- A quote missing from its declared page or present only in OCR/description
  fails, rather than being relabelled as grounded.
- No real client PDF or private corpus content enters fixtures or reports.
- Unknown category or malformed portal member fails loudly.

## Rollback / feature flag

Delete these new synthetic paths if the fixture design is rejected; no
runtime, data or feature flag change.

## Handoff

- report exact files, fixture counts, byte digests and mutation results;
- prove no existing fixture, model recording, contract, migration, runtime
  path or forbidden hotspot changed;
- hand branch and SHA to the integrator without pushing refs.
