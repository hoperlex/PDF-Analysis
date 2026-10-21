# W59-INT-SAME-SECTION-PAIR-PREP-01 — result

Base: published dev65 `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`.

Added an unserved pure preflight for the accepted W59 rule that an ordinary
version comparison uses two explicitly named versions of one set with the
same saved P/R stage and the same expert-confirmed section. It binds each
supplied classification to its exact VersionUid and returns an immutable
same-stage/same-section tuple. A P-versus-R pair and PS-versus-PB pair both
refuse; no filename, document-level section, display ordinal or current-head
pointer can supply a classification.

## Changed files

- `src/auditmanager/comparison/version_section_pair.py` — pure compatibility
  check with no I/O;
- `tests/integration/comparison/test_version_section_pair.py` — matching,
  mismatch, missing/foreign version and malformed pair cases;
- `docs/program/tasks/W59-INT-SAME-SECTION-PAIR-PREP-01.md` — frozen task;
- this result report.

## Checks

- Before implementation, the new regression could not import the absent
  module; pytest collection failed with `ModuleNotFoundError`.
- After implementation, the focused version-pair/section-route suite passed:
  **48 passed**.
- Complete offline comparison and section suites passed: **178 passed**.
  Direct task governance and ALR-05 architecture passed: **18 passed**
  (pytest reported five stale `/tmp` cleanup warnings unrelated to the tests).
- Python compilation, frozen SHA readback and whitespace passed. The
  clean-tree exact-path handoff is recorded in local evidence.
- No Docker, DB/S3, network, provider or full beta gate under R-135.

## Contracts and limits

No API/domain/error/stage contract, migration, saved classification, route,
profile, corpus or raw deterministic comparison evidence changed. The code
checks the section code's shape, not catalogue membership, and cannot prove
that the two supplied classifications were read from storage or confirmed by
an expert. The future owner must load them under the same authorized
transaction as the ordered pair and verify the sealed fifteen-code catalogue.
This result is not a section decision, run permission or comparison approval.

## Integration instruction

Cherry-pick the four owned paths after dev65. This module is disjoint from
concurrent W56/W57 lanes and stays unserved until the W59 SECTION-SEAL and
comparison owner implement persisted classifications and an authorized read.
Revert this source commit before activation if superseded; no data rollback or
feature flag is needed.

Forbidden hotspots, including `contracts/**`, `db/migrations/**`, existing
section/comparison modules, public facades, served API/UI, root locks,
composition root, global styles, `CURRENT_STATE.md`, refs and tags, were not
edited.
