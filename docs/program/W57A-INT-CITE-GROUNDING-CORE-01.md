# W57A-INT-CITE-GROUNDING-CORE-01 — pure v3 grounding candidate

**Base:** exact published dev30
`f6f19220fa5ae019daae07a3771846e2523ce55a`.
**Status:** isolated pure source candidate; no provider, Docker, PostgreSQL,
S3, remote ref, tag or stand operation.

## Result

The existing norm gate now accepts separate prompt-label bindings while it
continues to require one unique full-text row per canonical paragraph. This
repairs a real cardinality mismatch: the retrieval-set builder permits the
same paragraph under labels from different map items, but the old gate's
single `NormParagraph.label` field could represent only one. The original
five-positional-argument call remains supported. Explicit bindings reject
duplicate labels, unknown paragraph targets and mixed inline labels.

The new unserved AR v3 bridge grounds every proposed PDF evidence quote first,
using the existing v2 exact quote/OCR-only resolver. If any PDF quote fails,
the complete proposal is withheld before normative checks. A normative
proposal then goes through `ground_norm_observation` with separate labels;
the first citation/value failure withholds every anchor and citation from
that proposal. A nonnormative proposal carries an empty *candidate* citation
tuple. Accepted candidates carry exact PDF offsets and raw norm substring
offsets but no finding, Run, persisted count or expert verdict.

## Evidence

- Focused existing norm gate, new v3 bridge and v3 parser tests:
  **43 passed**.
- ALR-05 cross-context import boundary tests: **2 passed**.
- Python compilation, `git diff --check`, and direct task governance:
  **passed**; governance findings `[]`.
- API, stage, domain and 0023 migration hashes match the formal task's
  frozen inputs. No DB/S3 or full suite was started while W55b held the host.

## Limits and next integration

This slice does **not** verify that supplied paragraphs and labels came from
the exact Run-pinned retrieval set. The eventual caller must check the
retrieval-set bytes against the persisted verified row, map/snapshot identity
and R-76 custody before this pure result can enter the atomic CITE writer.
The served report remains typed 503 until the v3 profile, CITE publication and
persisted reader exist. A quote state of `verified` in this result means only
local text grounding, not that a retrieval-set row was qualified or a citation
was written. No corpus qualification or certified zero is inferred from the
synthetic tests.

Exactly seven paths changed: this report and its formal task;
`src/auditmanager/norms/{citation_prep,public}.py`;
`src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py`;
`tests/integration/norms/test_citation_prep.py`; and
`tests/integration/analysis/test_ar_v3_citation_grounding.py`.
No contract, migration, API router, bootstrap composition, v1/v2 production
module, W56b geometry/crop path, W55 gate input, root dependency/lock,
`CURRENT_STATE.md`, UI or global style was touched. The integrator can
cherry-pick this single source commit after dev30; keep the bridge unserved.
Rollback is the bounded source commit and needs no feature flag.
