# BLOCK-ANALYSIS-LIMITS-01-JUDGE — independent review

## Initial verdict: REJECT

- Reviewer: independent `block_limits_judge` agent; did not author the implementation.
- Date: 2026-11-12.
- Reviewed candidate: `bfbce73ffc51e3a51087980813ab3d383ebd17a4`.
- Base: `ec1c7931eafe46f44f742a3d1ee561b199ae4152`.
- Scope: remove the two-query observation limit and the 300-character relationship
  explanation limit while retaining source, citation and relationship checks.
- This section is the verdict on that exact candidate. Any repair is reviewed separately below.

## Blocking finding J-01 — cross-window replies now raise KeyError

**P1, reproducible regression.** `analysis/extended/cross_window_review.py:30` removes
`maxItems` from the `norm_queries` array schema, but `analysis/extended/review.py:107`
validates every array using `schema["maxItems"]`. It assumes an upper bound is present.

`parse_global_cross_window_reply` calls that validator for each observation. Consequently
every nonempty reply containing an otherwise valid cross-window observation raises
`KeyError("maxItems")`, including an observation with `norm_queries: []`. The per-record
handler catches `ValueError`, so the error escapes instead of becoming a refused record.
An empty observations array does not exercise the broken path.

Minimal reproduction on the reviewed candidate:

```python
from auditmanager.analysis.extended.cross_window_review import response_schema
from auditmanager.analysis.extended.review import _validate

schema = response_schema()["properties"]["observations"]["items"]["properties"]["norm_queries"]
_validate([], schema)  # KeyError: 'maxItems'
```

An independent full-parser probe loaded source from the exact Git objects, rather than
depending on a worktree being edited during review. It constructed two valid text sources
from distinct windows and cited both exact quotes:

```text
Exact base: valid cross-window observation with norm_queries=[] accepted
Exact candidate bfbce73ff: 0 queries -> uncaught KeyError(maxItems)
Exact candidate bfbce73ff: 3 queries -> uncaught KeyError(maxItems)
```

Probe: `/tmp/block_limits_cross_window_repro.py`. Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/plan-exec2/.venv/bin/python /tmp/block_limits_cross_window_repro.py
```

**Required repair:** teach the shared array validator that an absent `maxItems` means no
upper bound, retaining type, lower-bound, item and any explicitly declared upper-bound
checks. Add regression tests through the real `parse_global_cross_window_reply` for empty
and at least three norm queries, with strict and per-record parsing. Include negative
controls for source/quote binding and existing declared bounds. Do not replace the removed
limit with another arbitrary maximum.

## Other review results

- The leg parser and judge relationship parser do remove the requested restrictions.
  The original attachment's six refused records passed the candidate parsers unchanged;
  the baseline parser rejected each with its recorded error code.
- The merge, lookup loop and literal query planner no longer slice or partition queries
  at two. Source identities, exact norm citations and relationship uniqueness checks
  remain in the inspected code. Independent probes retained 100 queries and a 50,000
  character explanation, and still refused foreign/repeated/empty source references,
  foreign relationship references, a non-string reason and a repeated relationship pair.
- The internal schema changes explain the updated request digest fixtures. Persisted
  replies are keyed and checked against `request_sha256`; changed requests are not accepted
  as the earlier request's saved reply. This is no assertion that an active old run can
  resume across a deployment; integration must not relabel or rewrite stored reports.
- The existing 12-call lookup window and six-candidate projection in limited mode remain
  separate resource limits. Full-document mode retains all selected candidates. These
  existing limits and norm completion semantics are not part of this requested change.
- No contract, migration, dependency, composition or global-style modification appears in
  the candidate's diff. Release 0.25.1 revision 2 includes the user-visible change.

## Tests executed independently

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/plan-exec2/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/analysis_extended/test_response_limits.py tests/unit/runs/test_analysis_reply_limits.py tests/unit/analysis_extended/test_core.py tests/unit/analysis_extended/test_workflow_core.py tests/unit/runs/test_blocks_ensemble.py tests/unit/runs/test_block_sources_v2.py tests/unit/runs/test_norm_reply_per_record.py tests/unit/runs/test_norm_any_words.py tests/unit/runs/test_norm_coverage.py tests/contract/release_notes/test_release_notes_form.py
```

Result: **179 passed in 12.97s** on the reviewed candidate. These passing tests did not
exercise real cross-window parsing after the schema change: the new cross-window assertion
checks only schema shape. J-01 is why the green suite does not establish integration safety.

## Integrator handoff

Repair J-01 and obtain a follow-up review of the exact repaired SHA before integration.
The reviewer changed only this report and temporary probes under `/tmp`; no source/test,
contract, Git ref, deployment or stored run was changed. No external model/service call,
full gate, commit, tag or publication was performed by the reviewer.

## Follow-up verdict: ACCEPT

- Re-reviewed runtime candidate: `c7c9d5273e1e0d2021905022dafc616a7b9732f8`.
- Scope: the complete accumulated diff from `ec1c7931eafe46f44f742a3d1ee561b199ae4152`,
  including the J-01 repair. The initial REJECT above remains the verdict on `bfbce73ff`.
- Blocking findings remaining: **none**.

J-01 is fixed. The shared array validator now checks an upper bound only when the schema
declares one. It still rejects a non-list, checks `minItems`, validates every item and
enforces an explicitly declared `maxItems`. The change introduces no replacement ceiling.

The follow-up regressions exercise the actual cross-window parser, with both strict and
per-record handling. Independently, the Git-object probe was extended to load the exact
repaired source and its exact validator. It retains 0, 3, 20 and 100 norm queries in both
modes, with all eight cases passing. The same probe continues to demonstrate the failure
on `bfbce73ff` and the passing empty-query case on the original base.

The six original rejected records also pass unchanged on the repaired candidate. Additional
probes preserve 100 queries and a 50,000-character relationship explanation, while refusing
foreign, repeated and empty sources, foreign relationship references, non-string reasons,
repeated pairing, fabricated paragraph IDs and changed norm quotations. A structural schema
comparison with the base confirms that the core/judge schemas differ only by the requested
count and explanation-length removals. The limited-mode search resource windows described
above remain existing constraints, not a new unreported two-query slice.

### Follow-up checks

The exact ten-file pytest command recorded under “Tests executed independently” above was
rerun on `c7c9d527`: **194 passed in 12.84s**. The extra 15 cases cover the repaired seam.

The affected critic/corrector parsing checks were run separately:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/plan-exec2/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/analysis_extended/test_critic_reply_downgrade.py tests/unit/analysis_extended/test_critic_reference_section.py tests/unit/analysis_extended/test_batched_reply_refusal.py
```

Result: **41 passed in 1.77s**. Independent probes:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/plan-exec2/.venv/bin/python /tmp/block_limits_independent_probe.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /root/projects/PDF-Analysis/.local/worktrees/plan-exec2/.venv/bin/python /tmp/block_limits_cross_window_repro.py
git diff --check ec1c7931eafe46f44f742a3d1ee561b199ae4152..c7c9d5273e1e0d2021905022dafc616a7b9732f8
```

All passed. The accumulated diff contains no contract, migration, root dependency/lock,
composition, deployment configuration or global-style change. No live model call or full
gate was run; this acceptance is local code/parser evidence, not live deployment evidence.

### Current handoff boundary

The owner's latest instruction, relayed during follow-up, defers integration and asks for
the next investigation of repeated questions. Therefore **do not integrate or publish as
part of this review**. Runtime `c7c9d527` is independently accepted for the two-limit fix;
the reviewer leaves the report uncommitted and changes no code, tests, branches or remotes.
