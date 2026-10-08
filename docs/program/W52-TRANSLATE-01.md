# W52-TRANSLATE-01 — English operator runbooks hand-back

**Base:** `a17ddfdb4481e599c36098706b5898952fb8b28e`, the exact
`origin/dev` SHA read back after `W52-INT-C-WEB-01`.
**Lane:** `agent/w52-translate-01`. This lane changed no origin ref, tag,
stand or application behavior.

## 1. Changed files and result

Operator prose is English across all 14 manual-test files. Six files
needed edits; the other eight already contained no Russian prose.
The A01–A20 public-alpha journey remains a 27-route, five-PDF procedure
with the same case IDs, expectations, figures and Bash blocks. Product UI
labels and synthetic fixture text remain in Russian with English glosses.

Exact changed paths:

```text
docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
docs/manual-tests/CP-00_architecture.md
docs/manual-tests/CP-01_foundation.md
docs/manual-tests/CP-02_walking_skeleton.md
docs/manual-tests/PC-01_prototype.md
docs/manual-tests/README.md
docs/program/W52-TRANSLATE-01.md
```

## 2. Checks

- API documentation prose and surface counts: **77 passed**.
  Bootstrap-validator contract suite: **26 passed, 9 subtests passed**
  after provisioning the pinned `requirements/validation.lock` into an
  ignored local virtual environment. No tracked dependency changed.
- Exact comparisons with the base show: all three Bash blocks in the alpha
  runbook unchanged; all six `MT00` IDs unchanged; 11 checkpoint runbooks
  remain; all 64-character digests, case IDs and backticked file/route
  paths in edited files unchanged; the five-PDF table still has seven
  rows including header/rule and five columns. All 18 original quoted
  Russian UI strings in the alpha runbook remain present.
- The direct CP-00 checkpoint-tag/manual-vocabulary test passed. The
  full `test_cp00_candidate.py` was attempted in a linked worktree, where
  its sandbox expects a directory rather than a worktree `.git` file.
  It was then attempted in a normal local checkout. Its first failure,
  `ACandidateIntegrityTests.test_the_reviewed_delta_is_exactly_what_is_declared`,
  was reproduced on the **unmodified** `a17ddfd` base: the historic
  ratification manifest does not cover later contract/fixture changes.
  The full suite is therefore not claimed green; no CP-00 code or
  ratification record was changed to mask this baseline failure.
- `test_journey_figures_pinned.py` requires a live P02 `.env` and services;
  its two cases could not start in this docs-only lane. The static figures
  and path comparison above covers the changed runbook text.
- `test_alpha_acceptance_command.py` passed 124 tests and failed one
  clean-checkout assertion while the translation was uncommitted. Rerun it
  on the clean lane commit before integration. `git diff --check` passed.

## 3. Contracts

No API/domain contract, generated client, error catalog, migration,
front-matter key, manual case ID or executable command changed. The frozen
API remains 30 paths / 37 operations / 83 schemas, 23 error codes, domain
revision 9 / 29 identities, head `0016_release_notes` and
`contract_version=1.0.0-draft.1`. No reader code required an edit.

## 4. Risks and known limits

The two Cyrillic lines in the `make alpha-acceptance` Bash block are
immutable SHA metavariable labels, not operator prose or product output.
Every other Cyrillic line in the six edited files is a verbatim Russian
product label, message, or synthetic placeholder with an English gloss.
The CP-00 ratification suite's baseline drift and the live P02 fixture
require separate validation; this lane makes no gate, QA or live
acceptance claim. The later ACCEPT task must write new operator sentences
in English.

## 5. Integrator instruction

Review the seven-path diff and the byte-preservation checks, rerun the
clean-checkout alpha-command test, then merge the clean lane after the
WEB readback. Repeat prose/count and governance checks on the merged
candidate. Only an integration task may publish a checked SHA to
`origin/dev`; `origin/main` requires a separate direct owner instruction.

## 6. Forbidden-hotspot proof

All seven paths in §1 are granted by `tasks/W52-TRANSLATE-01.md`.
No permitted reader code needed a change. No `contracts/**`, migration,
root dependency/lock, product/UI code, global style,
`scripts/manual-alpha-check.sh`, `origin/main`, tag or deployed stand
changed. No checkpoint was created.
