# Task W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01 — expose AR v2 publication inputs at analysis boundary

task_id: W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01

## Outcome

The W56a merge planner and transactional publisher import AR v2 types and
rule constants only through `auditmanager.analysis.public`, the established
public boundary. No behavior or schema changes.

## Depends on

- `W56A-INT-MERGE-PUBLICATION-PLAN-PREP-01` — completed planner on dev.
- `W56A-INT-V2-PUBLICATION-PREP-01` — completed additive publisher in this integration wave.

## Frozen inputs

- base commit and `origin/dev`: `3a9b64c0796e6d61ad33a6c9f87ff842525712f6`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`, §A3.3;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
  error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
  analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
  provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: src/auditmanager/analysis/public.py
- enumerator_owner: W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01
- totality_query: `sed -n '55,130p' src/auditmanager/analysis/public.py`

## Captured premise evidence

- premise: new findings modules import analysis implementation paths directly; the analysis bounded context already has a public seam.

### P-01 — deep imports and public seam

- captured_at: 2026-10-15
- command: `rg -n '^from auditmanager\.analysis\.(profiles\.ar_v2|stages\.finding_merge|text\.anchors)' src/auditmanager/findings/merge_publication_plan.py src/auditmanager/findings/v2_publication.py`
- captured_output:
  ```text
  src/auditmanager/findings/v2_publication.py:19:from auditmanager.analysis.profiles.ar_v2.proposal_grounding import RejectedProposal
  src/auditmanager/findings/v2_publication.py:20:from auditmanager.analysis.profiles.ar_v2.response_schema import CATEGORIES, SEVERITIES
  src/auditmanager/findings/merge_publication_plan.py:12:from auditmanager.analysis.profiles.ar_v2.merge_input import MergePreparation, prepare_merge
  src/auditmanager/findings/merge_publication_plan.py:13:from auditmanager.analysis.profiles.ar_v2.proposal_grounding import (
  src/auditmanager/findings/merge_publication_plan.py:17:from auditmanager.analysis.profiles.ar_v2.response import ProposedObservation
  src/auditmanager/findings/merge_publication_plan.py:18:from auditmanager.analysis.stages.finding_merge import ARTIFACT_ROLE, ARTIFACT_VERSION, MERGE_RULE_VERSION
  src/auditmanager/findings/merge_publication_plan.py:19:from auditmanager.analysis.text.anchors import ResolvedAnchor
  ```
- interpretation: the import path crosses internals; adding narrow explicit exports to `analysis.public` removes that coupling without changing rule implementations.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/public.py`
- `src/auditmanager/findings/merge_publication_plan.py`
- `src/auditmanager/findings/v2_publication.py`
- `tests/integration/findings/test_analysis_public_boundary.py`
- `docs/program/tasks/W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01.md`
- `docs/program/W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01.md`

## Forbidden hotspots

Analysis implementations, existing v1 publication, executor, contracts,
migrations, provider lock, root dependencies/locks, composition root, global
styles, `CURRENT_STATE.md`, tags and both remote refs.

## Non-goals

No runtime activation, rule change, provider call, DB acceptance, public API
reseal, complete gate or beta acceptance.

## Deliverables

Explicit public exports, converted findings imports, one boundary guard,
task file and report.

## Required tests

- focused merge/publication and public-boundary tests;
- Python compile, direct governance, whitespace and exact path check;
- full `make gate` deferred under R-135.

## Integration contract

Analysis owns the exported AR v2 input types and merge constants; findings
consumes them through `analysis.public`. Existing object identity and behavior
remain unchanged. Future runtime composition may use the same seam after its
separate grant.

## Failure/idempotency/security cases

The boundary guard fails if findings reaches back into AR v2 internals; no
new output, DB operation or external effect is introduced.

## Rollback / feature flag

Revert this boundary-only change with its consumer modules; no data rollback
or feature flag.
