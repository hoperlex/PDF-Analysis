# HOTFIX-RUN-COMPLETE-1106 — complete source plans and truthful execution states

task_id: HOTFIX-RUN-COMPLETE-1106

Outcome: a fresh full-document run processes all planned source pieces and cross-window
pairs, retains validator refusals and separate bounded repair attempts, and reports
execution failures separately from valid negative review outcomes. A green result must
include complete source coverage; old partial artifacts are immutable.

Owner: this session's release integrator, authorized by the owner's 2026-11-06 request
for another hotfix and a complete green run. Publish the exact buildable candidate to
`origin/dev`, then `origin/main`, observe its deployment and the new run. The owner's
build-only verification instruction still applies; no full gate or test batteries.

depends_on: HOTFIX-RUN-PARTIAL-1106 (deployed and verified at
9f440fbda8117c428fa89e772a1918c5f51a976d).

Frozen inputs: API/analysis/events 1.33.0; migration 0055_work_schedule; product 0.12.1;
the supplied immutable export of run_01M6R76M73Z8QKGJCN4D623PKB. New internal consent
policies are versioned separately; existing accepted v1 plans retain their limits.

Allowed paths and ownership:

- Integrator: `runs/{extended_review.py,preflight.py,cost_policy.py,norm_queries.py}`, analysis
  public wrappers, proportional task/release records and UI execution presentation. Release
  metadata slot includes VERSION, release-notes and their existing contract/integration
  revision/version pins; no new behavioral tests or test runs.
- Passport lane: `analysis/extended/project_parameters.py`, `runs/project_parameters.py`.
- Global lane: `analysis/extended/{coverage.py,cross_window.py,cross_window_review.py}`.
- Semantic lane: `analysis/extended/{core.py,review.py}`, `runs/norm_queries.py` until handoff.
- Runner lane: `tools/executor-runner/{agent.py,codex_answer.py}`; repair incomplete stdin
  writes across subprocess timeouts. Integrator installs reviewed scripts atomically on
  the already authorized local service; restart only after its active task finishes.
- Integrator owns narrowly scoped operator diagnostics/reaudit CLI and deployment workflow
  invocation if needed to inspect the production result without an interactive SSH key.
- Integration/composition slot: integrator alone owns exposing the existing configured
  run-control port as `Application.run_control` in `bootstrap/composition.py`; no rewiring.

Forbidden hotspots/non-goals: contracts/generated clients, migrations, root dependencies
and lockfiles, composition root outside the named slot, global styles, credentials, deterministic evidence and
expert decisions. No fuzzy source acceptance, blind retry after ambiguous provider effect,
retroactive consent expansion, forced green status, force-push, tag or unrelated changes.

Deliverables/integration: opt-in full-source consent policies and matching workers; a
separate journalled semantic repair after a received invalid response; exact refusal
codes and per-window causes; completed report generation without stale dependency reason;
literal norm-query derivation with provenance and explicit not-applicable outcomes.
Budget, cancellation and ambiguous-effect fences remain authoritative. Live rerun uses a
fresh estimate and the existing unmetered executor only; no new paid ceiling is inferred.

Checks: production web build, backend compile/import buildability, `git diff --check`;
record commands and missing behavioral coverage. Recheck refs, clean candidate and proven
fast-forward, exact-tree deployment verifier and public TLS/auth smoke. Observe the live
run independently of build success. Rollback: forward revert; no data migration. New
full-source behavior is frozen into fresh consent, never substituted into old plans.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none

## Publication authority

- development_target: origin/main
- origin_main_authority: delegated release integrator HOTFIX-RUN-COMPLETE-1106


## Completion evidence

Completed on 2026-11-06: production SHA `46b52dd068232236038d7ec4cbb0b13c63b9aa25`,
verified deployment 42241699088; fresh unmetered run `run_01M6RQ9SZPB01G22AV6VQRHJHD`
is published. All 7 procedures, 3 windows, 47 blocks, 30 pages and 1848 pairs completed;
all 74 provider effects completed, 0 unresolved. Strict quote/numeric guards are unchanged;
old partial runs are immutable. Build-only checks passed; no suites/gate under the explicit
owner instruction. Detailed changed paths, checks, limitations, protected-path proof and
integrator instructions are in `docs/program/HOTFIX-RUN-COMPLETE-1106.md` and the workspace
receipt. Closure records publish to dev only; runtime main remains verified 46b.
No tag/checkpoint or further model run.
