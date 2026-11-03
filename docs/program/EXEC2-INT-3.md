# EXEC2-INT-3 — stage 3 of EXEC-2 (dispatch by group, cut-over)

Unverified development candidate published to `origin/dev`. This completes the EXEC-2 implementation. Plan `dispatch/EXEC2-PLAN.md`, decisions `ADR-0026`, rulings `R-149a`…`R-149i`.

## What is in

| Task | Result |
|---|---|
| `EXEC2-GROUP-RUN-01` | A Run is admitted by a named group, or by the `text_analysis` rule in mode `rules`. While `pending` it holds no connection. Dispatch happens inside the claim transaction: group row → member locks ascending → consent re-check → least-loaded choice → control → Run → Job → single bind and event → commit, with model I/O only after the commit. Durable wait reasons; after 1800 s offline the Run ends `no_executor_online`. Re-audit keeps the original selector kind. |
| `EXEC2-GROUP-CMP-01` | The five `comparison_*` kinds are admitted by rule. The group plan is in the estimate and consent. Each job binds to one member at its first call, under the group lock → member locks → day lock, with the USD 10 job and USD 50 day ceilings checked against that member. Later calls stay on that member. |
| `EXEC2-WEB-GROUPS-01` | The «Группы» and «Правила» tabs and the cut-over panel. The start screen offers three choices — automatic, a group, or a connection — and sends exactly one selector. Before dispatch the screens show the planned model; after it, the actual one. |
| `EXEC2-CUTOVER-01` | The preview shows six work kinds: a primary becomes a one-member group, a standby is flagged and never converted. The confirmed cut-over and the rollback each run in one transaction under the mode-journal lock. Under `rules`, `setExecutorRoute` is refused. Operator guide: `docs/manual-tests/EXEC2-CUTOVER.md`. |

## Integrator edits

- **Removed** the stage-2 refusal test.
- **Compose:** the worker gets `AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS:-1800`. A blank value would stop the worker.
- **Web:** `QueueItemWaiting` is wired into the execution queue. The dashboard-invalidation map is extended. The tabs and start-form tests are updated.
- **`dispatch_groups`** is wired into the worker `serve`, the in-process `RunAdapter` and the comparison claim gates.
- **Merges:** `origin/dev` `3bcf67cf` (REVIEW-VIEWER-01).

## Checks (`R-149d`: no test, build, typecheck, lint, database or browser run)

- `git diff --check` is clean.
- All 171 changed files: Python parses, JSON loads.
- `generate-api-client --check` reports OK, 277 operations.
- **All 277 contract operations are now served.**
- The independent read-only review of `750cdf66..da90b606` found 1 HIGH and 1 MEDIUM. Both were fixed before publication:
  - **HIGH:** the hint offered pending Runs whose only free member was ineligible, which stalled the queue. The hint now offers a pending Run only while `wait_reason IS NULL`, and a refused Run falls through to the comparison claim.
  - **MEDIUM:** a non-database worker could claim pending Runs. The `dispatch_groups` flag now prevents this.
- LOW findings fixed before publication:
  - the carrier sweep is isolated;
  - expiry is decided under the Run lock;
  - the sweep pages through every pending Run;
  - a Run whose consent no longer holds ends `analysis_input_invalid` / `cost_estimate_binding_changed`;
  - a terminal comparison job is never given a wait.

## Known limits

- **`D-292` still holds.** None of the written database or stress tests has run. They go into a common run through the host run slot (`R-149i`) once the disk allows about 6 GB, before any `origin/main` promotion.
- **`D-291` still holds.** Client documents are not enforced.
- **Rates.** Comparison prices at the group's rate snapshot. Runs price at the provider lock and re-check its hash, so the two must be unified. Members' rates are identical by construction.
- **Legacy routes under `rules`:**
  - the AR v3 group start uses the legacy route; this path is closed in the beta by the empty pack registry;
  - frozen pre-cut-over comparison jobs re-price through the legacy route;
  - admission reads the mode without the journal lock.
- **Wait classification.**
  - Every non-capacity unavailability counts as `runner_offline`, so it expires after 1800 s. That includes a revised or unprobed member.
  - The cut-over's `ready` does not check probes.
  - On the comparison side, the offline clock only advances when an item retries.
- **The CLI.** `python -m auditmanager.executors import-env` sets a first route, and under `rules` that is refused.
- **Comparison screens** do not show the binding yet.
- **`B3 §11` numbering.** The tests were mapped to ADR decisions, not to the design document's item numbers.

## Next

1. Run `D-292` through the host run slot.
2. On the stand, the owner confirms the cut-over (`docs/manual-tests/EXEC2-CUTOVER.md`).
3. Follow-ups: rate unification, comparison binding in the UI, enforcement of `D-291`.
