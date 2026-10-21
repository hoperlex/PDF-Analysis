# W56B-INT-WINDOW-COHORT-PREP-01 — complete supplied TEXT replies

Base: `origin/dev` candidate 40 at
`f0b12ea705a9ccb476b5b69a5797de7d3731f543`.

The pure `bind_window_claim_cohort` check demands one ordered supplied reply
for each checked saved TEXT window. A reply with zero claims is valid; a
missing reply is refused. Each claim is constrained to its reply's window and
resolved through the existing literal page-anchor rule, retaining original
document-global Unicode offsets or an explicit unresolved result.

`validate_window_plan` is extracted from the previous one-quote W56b binder
so both entrypoints check complete source coverage, including empty replies,
without duplicating the plan rule. The one-quote behavior is unchanged.

## Checks

- Focused cohort, window-anchor and partition suites: **35 passed**.
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace and exact five-path proof: passed at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or complete gate was run.

## Contracts and limits

No contract, migration, stage registry, provider, API/UI, composition,
dependency or served runtime change. These inputs are supplied claims, not
authenticated provider responses. The future caller must prove saved
Run/Attempt and effect-journal provenance, decide cross-window semantics and
obtain W56b policy/freeze before any request or publication.

Rollback is removal of the additive module/test and reversal of the validator
extraction before wiring; no data migration or flag is needed.

Only these five paths change:

- `src/auditmanager/analysis/text/window_anchor.py`;
- `src/auditmanager/analysis/text/window_cohort.py`;
- `tests/integration/analysis_text/test_window_cohort.py`;
- `docs/program/tasks/W56B-INT-WINDOW-COHORT-PREP-01.md`;
- this report.

The integrator can cherry-pick the exact source commit after checking the
frozen surfaces and direct handoff. Do not mistake cohort completeness for
provider authenticity, accepted evidence or finding publication.
