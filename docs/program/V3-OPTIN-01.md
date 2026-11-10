# V3-OPTIN-01 — the stages of plan v3 become opt-in; the default plan is v2

Owner ruling R-154b (2026-11-10): «v3 сделать подключаемым, по умолчанию выключеным». Only the
stages that plan v3 adds are opt-in: the cross-window check, the parameter passport, the critic and
the correction. The stage layout («Модели по этапам») is not touched. The switch is the server
environment only, `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN`; there is no UI switch.

"v3" here is the extended-review plan (`extended-review-v3`). It is not the AR v3 beta group, which
the wave AR-V3-REMOVE deletes.

## What changed

- `src/auditmanager/runs/preflight.py`
  - `EXTENDED_PLAN_DEFAULT = "v2"` (line 75) and the private `_requested_extended_plan()` (lines
    78-84) read the plan name in one place. An absent or blank value (also `"   "`) is `v2`. The
    default is a bare-name constant because the compose-forwarding contract test reads code defaults
    with a regex over `environ.get("NAME", CONST)`.
  - `stage_rows_in_use` (line 358) and `estimate_run` (line 449) both read it. Nothing else reads the
    variable (`grep -rn EXTENDED_ANALYSIS_PLAN` over `src`, `infra`, `scripts`, `tools`, `web/src`).
  - Unchanged: `v3` / `extended-review-v3` opts in exactly as before; `v2` / `extended-review-v2` is
    explicit v2; any other value is `validation_failed` / `analysis_workflow` / `unsupported_plan`
    (lines 363 and 583), never a fallback; `AUDITMANAGER_EXTENDED_ANALYSIS=0` is text only and does
    not even read the plan name.
- `infra/deploy/compose.server.yml:262` — the compose default is `:-v2`.
- `infra/deploy/env/alpha.env.example:375-381` — the example lists `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v2`
  and says v3 is opt-in and what it adds.
- Not changed: `estimate_group` and the `AR_V3_*` lines (another lane), the comment above
  `compose.server.yml:262`, the contract, the web, the ADRs.

## What stays as it was

- An accepted consent keeps the plan it was priced with (`extended_review.plan_version` is frozen in
  the consent). The worker never reads the variable: it runs from the frozen consent
  (`runs/executor.py:965-974`, `:1495-1497`). Running runs, stage reuse (`runs/stage_reuse.py:73`) and
  old results are unaffected.
- A start recomputes the estimate in its own transaction (`runs/commands.py:844`, `:1238`, `:1421`).
  An estimate shown before the operator switched the variable has another digest and is refused at the
  start as `run_cost_estimate_stale`. This is the existing binding, not new.

## Operator note

A stand whose own env file sets `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v3` explicitly (the example used
to recommend it) stays on v3. To follow the new default the operator edits the stand's env file (sets
`v2` or deletes the line) and recreates the `api` container with `deploy.sh` or
`docker compose up -d`. The compose default alone does not move such a stand. The switches
`AUDITMANAGER_EXTENDED_COVERAGE`, `_EXTENDED_CROSS_WINDOW`, `_PROJECT_PARAMETERS`,
`_PROJECT_PARAMETER_CONTEXT`, `_PROJECT_PARAMETER_REVIEW_CONTEXT` and `_NORM_PARAGRAPH_CONTEXT` are read
only under `v3` (`preflight.py` v3 branch, from line 450); under `v2` they do nothing.

## The readers and the implicit "v3 is the default" assumptions

Reading paths that reach the two readers: `startRun` (`runs/commands.py:844`), `reauditRun` (`:1238`),
start-from-stage (`:1421`), the estimate operations (`bootstrap/adapters.py:1362`, `:1371`, `:1375`)
and the readiness / one-button read (`runs/stage_plan.py:224-230`, `:257`). All end in `estimate_run`
or `stage_rows_in_use`; none reads the variable itself.

Backend consequences of v2 being the default (reported, not changed):

- Pages without a text layer. The path that lets a page with no embedded text and no portal block
  through is v3's (`runs/stage_reuse.py:73` `visual_only_pages_allowed`; `runs/executor.py:974`,
  `:1238`; `analysis/stages/source_preparation.py:301`). Under v2 such a page is refused at
  `source_preparation` (`validation_failed`, "every page must carry extractable embedded text"), before
  any paid call. A scanned PDF without a portal bundle therefore fails at preparation by default.
- The critic and the correction rows take no server slot under v2 (`runs/stage_layout.py:486-495`).

Web places that assume the critic and the correction exist (report only; no web change in this lane).
Under v2 the panel already says it is the previous plan
(`web/src/widgets/extended-review/ui/extended-review.tsx:191`), but:

- `extended-review.tsx:198` — the counters «Рекомендации машинного критика» and «Предложенные
  исправленные кандидаты» are drawn for v2 too, as zeros.
- `widgets/extended-review/ui/observation-list.tsx:70` — the critic queue tabs; `:79`, `:80` — the
  filters «Рекомендация критика» and «Уточнение»; all empty for v2 observations.
- `observation-list.tsx:103` — each v2 observation shows the block «Машинная критика и предложенное
  уточнение» with «Записи критика и корректора пока не переданы». v2 observations carry no
  `review_status`; it is set only on v3 paths (`runs/extended_review.py:1481`, `:1994`, `:2224`).
- `entities/audit-run/lib/extended-report.ts:62`, `:146` and `entities/audit-run/lib/extended-xlsx.ts:70`,
  `:78` — the exported report says «Машинная критика этого наблюдения не подтверждена переданными
  данными» and the XLSX has an empty critic sheet for v2.
- `widgets/executor-stage-models/ui/executor-stage-models.tsx` — «Модели по этапам» still shows all six
  rows (already an open owner question in `owner-answers.md`).
- Handled already: the run rail does not draw a chip that neither a stage state nor a procedure
  mentions (`entities/audit-run/model/run-chips.ts:8-9`); the v2 procedure list has no critic or
  correction (`analysis/extended/workflow.py:27-32`); the layout plan view leaves out a row without a
  cell (`entities/stage-layout/model/plan.ts:5`).

## v2 health report (does v2 deserve to be the default?)

### Tests that exercise v2

- Estimate: `tests/unit/runs/test_cost_preflight.py` (v2 for all 15 sections, 60 calls for one page; the
  exact image count against the fallback; the new default / blank / junk / text-only tests) and
  `tests/unit/runs/test_stage_plan_consent.py` (every pricing test is parametrised over both plans).
- Freeze with the layout on and off: `test_stage_plan_consent.py` (rows, readiness, "a row the run will
  not call does not block it"), `tests/unit/runs/test_stage_layout.py:244-248` (v2 binds four rows;
  `restricted_to` drops `review:main`), `tests/unit/runs/test_cost_policy.py` (a v2 consent is accepted),
  `test_stage_plan_binding.py`, `test_stage_plan_start.py`, `test_stage_plan_service*.py`,
  `test_hotfix_operator_stage_plans.py`.
- Worker execution of `extended-review-v2` in `runs/extended_review.py`:
  `tests/unit/analysis_extended/test_workflow_runtime.py` (5 test functions) — the true phases and the
  four-call cap with a bad norm answer and with a native mismatch, all 47 blocks of a full-document plan,
  comprehensive batches that cover every character, norm review over several calls, the planned receipt
  and the read helper — plus `test_workflow_core.py` and `test_core.py`.
- Publication: only through the read helper (`test_workflow_runtime.py`, planned and terminal receipts)
  and the web render test `web/tests/unit/analysis-extended/workflow.test.ts`.

Result of the 19-file set (command below): 402 passed, 5 failed. Four reds were a wrong assertion of my
own new text-only test (the key `extended_review` is absent from the authority, not `None`); fixed. The
fifth, `tests/integration/workers/test_worker_composition.py::TestTheComposeService::test_the_worker_has_the_apis_environment_except_the_secret`,
is red at the base: the `api` environment names `AR_V3_BETA_START_ALLOWED` (`compose.server.yml:298`,
present at `826470582`) and the test's allow-list does not. It is the AR v3 removal lane's line.

### What v2 has no test for

- No test runs the executor with a v2 consent: `runs/executor.py:1495-1570` (`publish_extended`,
  `extended_progress`, the degraded-to-partial rule at `:1517-1528`) is exercised for v3 paths and by
  fakes of `run_extended_review` only. No integration or e2e test carries an `extended-review-v2`
  consent through start, freeze, worker and publication.
- No test that a v2 run over 500 pages ends as a failed review and a partial run. The function-level
  refusal is pinned (`tests/unit/analysis/test_section_run_bounds.py:127`); the run-level outcome is not.
- No test that a scanned PDF without a portal bundle fails at `source_preparation` under a v2 consent
  (the stage-level rule is tested in `tests/integration/analysis/recognised/test_source_preparation_bundle.py`).
- The DB-backed layout tests (`tests/integration/runs/test_stage_plan_db.py`,
  `tests/integration/executors/test_hosts_int_wire.py`) freeze an explicit plan and do not depend on the
  default; they need Postgres and were not run in this lane.
- The web shows v2 correctly in words but with empty critic widgets (above).

### Limits a large document meets (numbers in code)

- No windows; calls grow with pages (`runs/preflight.py:564-582`):
  `image_calls = ceil(possible_images / 8)`, `comprehensive_calls = pages + ceil(chars / 40 000) +
  image_calls + windows`, `norm_calls = image_calls + comprehensive_calls + windows`,
  `extra = image_calls + comprehensive_calls + norm_calls`. There is no cap on calls; the consent
  `max_windows` is `max(12, windows)` (`:281`, `:332`) and the money ceiling is the bound.
- A version without `source.structured_companion` (a plain PDF) has an unknown image count and v2
  reserves `min(1000, pages * 100)` possible images (`:566-568`), that is 125 image calls even for a
  10-page file. A portal bundle gives the real count (`_image_block_count`, `:182-201`); a bundle with
  no images reserves one per page (`:569-570`).
- Per-call batches: block images 8 per call (`runs/extended_review.py:1266`); comprehensive: 8 page
  contexts, 40 000 characters and 40 items per call (`:872-874`, pieces of 40 000 at `:843`); norm review:
  40 items or 80 000 characters per call (`:906`).
- Native render of the whole document in one go: `max_pages=version.page_count` for a full-document v2
  (`runs/extended_review.py:1217`) against the 500-page ceiling (`analysis/extended/native_pages.py:27-29`,
  `analysis/extended/core.py:30`). v2 never passes `relaxed_limits` (only the v3 branch does), so a
  501-page document ends as `native_page_limit_invalid`, caught at `runs/extended_review.py:1456`: the
  procedures are saved failed and the text stage becomes partial. The standard intake caps a PDF at 500
  pages (`ingest/envelope.py:168`), so this needs `AUDITMANAGER_INTAKE_RELAXED=1`.
- A page whose PNG is over 4 MiB is skipped as `native_png_bytes_cap` (`native_pages.py:15`, `:53-54`), so
  the visual phase is partial.
- Every limit above fails closed: the base text analysis and its findings stay, the extended review is
  saved with its reason, the run is partial. Nothing falls back to another plan.

### Estimate table and its method

Figures are the pre-start estimate (`RunCostPreflight.estimate_run`), not a spend. Method: the read-only
script `v2_estimate_table.py` (kept in the session scratchpad, not in the repository) builds the service
of `tests/unit/runs/test_cost_preflight.py` (`service`, `version`, `estimate`: price pin `claude-opus-5`,
provider mode `recorded`, a manifest with only `source.document`, so no structured companion and an
unknown image count), sets `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN` to `v2` and then `v3`, and prints
`calls` and `estimated_cost_micros` for each document. It ran inside one locked command on the lane tree
(base `826470582` plus the uncommitted diff that became commit `07b248173`); the output is in
`.local/evidence/lane-V3-OPTIN-01/run2-final.log`. USD is micros divided by one million.

| Document | v2 calls | v2 USD | v3 calls | v3 USD |
|---|---|---|---|---|
| AR 30 p, 100 000 ch | 586 | 371 | 205 | 195 |
| AR 100 p, 300 000 ch | 760 | 490 | 623 | 595 |
| AR 300 p, 1 000 000 ch | 1 290 | 852 | 2 205 | 2 073 |
| AR 500 p, 2 000 000 ch | 1 868 | 1 249 | 5 267 | 4 886 |
| AI 500 p, 5 000 000 ch | 2 322 | 1 569 | 10 079 | 9 203 |
| AR 501 p, relaxed limits | 1 870 | 1 331 | 5 267 | 4 967 |
| AR 1200 p, relaxed limits | 3 802 | 2 770 | 23 343 | 21 543 |

v2 is cheaper than v3 from about 300 pages (no windows, no critic, no correction, no passport) and
dearer below about 100 pages only because of the 125-call image reservation for a file with no
structured companion. With the stage layout on and every cell on a subscription, the cost is zero in
both plans; the call counts still hold.

### Verdict for the owner

v2 is the plan that ran before v3, it fails closed, and its unit coverage of the workflow itself is
real. It is not proven end to end through the executor. Before v2 becomes the default on a stand:
run one recorded or live v2 run through start, worker and publication on that stand; decide whether a
scanned PDF without a portal bundle may be refused (it is refused under v2); and, if the web should stop
showing empty critic widgets for v2, schedule that web change.

## Checks

- Command, run 5 (committed tree `07b248173`, tree `a0bc33c1f7844b4f4e801e5b1bdf377725eb8da9`; log
  `.local/evidence/lane-V3-OPTIN-01/run5-committed-tree.log`): `.venv/bin/python -m pytest -c pyproject.toml
  --rootdir=. -q -p no:cacheprovider tests/unit/runs/test_cost_preflight.py tests/unit/runs/test_stage_plan_consent.py
  tests/contract/test_compose_flag_forwarding.py tests/contract/api_v1/test_surface_counts_in_prose.py` —
  138 passed.
- Run 2 (19 files, the touched tests plus the v2 tests listed above, before the text-only test fix):
  402 passed, 5 failed; the 5 are explained above. Run 3 (the three touched files after the fix): 105 passed.
- Mutation check (run 4): with `EXTENDED_PLAN_DEFAULT` set to `"v3"` the three touched files go red (23
  failed, 82 passed), so the new default tests and the compose guard can fail. The file was restored
  byte for byte.
- Not run: DB-backed integration tests (no Postgres in this lane) and web tests (no web change).
- Tests edited only because of the default: `test_cost_preflight.py` (the former "default v3" test now
  sets `v3`; the section-stats test sets `v3`), `test_stage_plan_consent.py` (the rows, legacy-coverage and
  readiness tests set `v3`), `test_compose_flag_forwarding.py` (the code default is `v2`; a new guard test
  fails in the compose file, the example and the code), `tests/support/run_consent.py` (a docstring).

## Risks

- A stand with an explicit `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v3` stays on v3 until its env is edited.
- Fresh starts on a stand that follows the new default lose the critic, the correction, the passport and
  the cross-window check, and lose the scanned-page path (above).
- Prose elsewhere still says the default is v3 (docs lane): `docs/program/SPRINT-SECTION-INT-1030.md:42`,
  `docs/program/SPRINT2-INT-1030.md:36`, `docs/program/tasks/AR-COST-PORTAL-STAMP-1030.md:66`, ADR-0028.
- The compose comment above `compose.server.yml:262` still says "names take `v2` / `legacy`"; it was left
  as it is, since the lane may touch only the plan line there.
- Real-world v2 cost on a plain PDF is over-reserved (125 image calls); the money ceiling is
  `recommended_ceiling_micros` (1.2 times the estimate), which a person must accept for an API-billed run.

## Integrator

Merge this lane first. Textual conflicts only, in `preflight.py`, `compose.server.yml` and
`alpha.env.example`, where other lanes edit other hunks. No contract, no migration, no web change, no
version bump (nothing user visible on the web; the effect is a server setting).
