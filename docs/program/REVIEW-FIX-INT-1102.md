# REVIEW-FIX-INT-1102 — integration record of the 2026-11-02 review-fix wave

The owner asked on 2026-11-02 for a review of the week 2026-10-26..30 against its own documentation
(not against a full gate), then, by direct poll, for the P0 and P1 fixes of that review, published to
`origin/dev` only, with the mandatory-checks rule waived for the fixes. The review report is kept out
of the tree (`.local/reports/code-review-2026-11-02.md`, per-slice findings beside it).

Base: `origin/dev` `4ab295607806d030cf8066c2f21ab1cac45003e1` (read with `git ls-remote` at dispatch).
Branch: `integration/review-fix-1102`. `origin/main` is not a target.

## Owner decisions taken by direct poll on 2026-11-02

- FIX-03: the intake sandbox comes back for everyone; lifted quotas apply only in relaxed mode
  (per-run `relaxed_limits`; `AUDITMANAGER_INTAKE_RELAXED=1` for intake).
- Statistics mode keeps its uncapped money ceiling; only the BETA-COST report text is to be corrected
  (not in this wave).
- Run P0 and P1 now; publish to `origin/dev`; `origin/main` only on a separate instruction.

## Commits

| Commit | Task | What it does |
| --- | --- | --- |
| `72070af1`, `068d48ce` | REVIEW-FIX-INT-1102 | task files of the wave and their two extensions |
| `5de87c2b` | REVIEW-FIX-SEAMS-1102 | web typecheck fixed; unbounded comparison tests bounded; nine rollback flags and `AUDITMANAGER_INTAKE_RELAXED` forwarded by compose with a guard; recovery head 0044 with a guard; `apply-grants.sh` regenerated (row order only) |
| `733ac3f7` | REVIEW-FIX-BOUNDS-1102 | sandbox always finite; ADR quotas by default; relaxed only per run or by flag; 500-page comparison cap again |
| `3137abda` | REVIEW-FIX-ANALYSIS-1102 | critic refusals contained per batch; two-fragment norm quotes; request ceiling after decorators |
| `efcf75e4` | REVIEW-FIX-CMP-RUNTIME-1102 | queue done/skipped labels; launch race; undo on finished runs; batch failure audit event |
| `d0573f05` | REVIEW-FIX-CMP-SPEC-1102 | migration `0045_comparison_page_bounds`; resumable specification batches; typed page refusal; no PDF parse in the start transaction |
| `b51aa02a` | REVIEW-FIX-TESTS-1102 | consent helper and served-gate tests; five unit reds were wrong tests, re-pinned exactly; FRONTEND_LOCK, expected-facts head 0045, surface counts 259, R-66 guard, upload envelope 250 MiB / 500 pages |
| `fac93e8e` | REVIEW-FIX-INT-1102 | merge of `origin/dev` `9617c759` (CTX-NAV-20261102, docs only; no file overlap) |

## Checks

No full gate ran (waived). What ran, by whom, on which tree:

- Integrator, base `4ab29560`: web `tsc --noEmit` one error (`saved-results.ts:199`, TS18047).
- Lanes: each lane's unit suites and guard mutations, quoted in its commit message.
- Integrator, `733ac3f7`: web `tsc` exit 0; `tests/contract/test_compose_flag_forwarding.py`,
  `test_recovery_schema_head.py`, `test_proxy_rate_limits.py` 74 passed.
- Integrator, `d0573f05`: web `tsc` exit 0; unit suites of the touched contexts 3569 passed, 5 failed,
  all five failing on the base as well (handed to REVIEW-FIX-TESTS-1102, which found the tests wrong).
- Lane REVIEW-FIX-TESTS-1102: `tests/unit` 6158 passed, 9 failed, all nine failing on the base too
  (technical export writer, executor-runner heartbeat, explicit executor ×3, stage_v3 ×4).
- Integrator, merged tree `fac93e8e`: web `tsc` exit 0; `tests/contract/program`, compose-flag, recovery
  head, proxy rate-limit and security-header, surface-count prose and OpenAPI conformance tests 240 passed,
  1 failed — `test_process_acceleration.py::CurrentStateTest::test_archive_is_the_exact_base_document_and_live_entry_is_short`,
  which reads only `docs/program/CURRENT_STATE*` (untouched by this wave) and is red on the base; web vitest
  `frontend-lock.guard` and `r66-navigation` 26 passed.

Not run anywhere in the wave: `tests/integration/**` (no database assigned), any migration upgrade or
downgrade against a database (0045 included), the web suite as a whole, the live journey, `make gate`.

## Not done in this wave

- S1-sprints-05 (`comparison/report/method.py`: zero-call assembly when nothing is editable) — the task
  named the wrong file; one-line fix recorded in the review.
- S4-04 (provider mode of the launch handler; needs the composition root), S5-03 (graphic window count;
  needs a contract change).
- S6-04 partly: the first comparison-PDF estimate still parses the PDF in the request.
- P2 (interface and accessibility) and P3 (documentation drift) of the review.
- **Contract prose still describes the lift.** `contracts/api/v1/openapi.json` (and its web snapshot) keeps
  the `af581631` wording that temporary statistics intake removes the ceilings, while REVIEW-FIX-BOUNDS-1102
  restored them by default. The schema stays unbounded on purpose (`AUDITMANAGER_INTAKE_RELAXED=1` may exceed
  500 pages), so the fix is prose plus re-pinning the web "numbers from the contract" test and the W55b
  "page_count maximum" test, with a regenerated snapshot and a re-measured FRONTEND_LOCK. It needs the contract
  slot and is the first follow-up.
- The characterization journey (`tests/characterization/w13_baseline/journey.py`) and the qa_w55b start helper
  still start Runs without a consent; both need a database to change honestly.

## Effects an operator must know

- Queued runs consented after `af581631` need a fresh consent: rules digests changed, and a non-relaxed
  run above the restored bounds is refused.
- The proxy is back to its pre-`af581631` configuration: the comparison ZIP import is held by the
  server-wide body limit; a relaxed PDF is still capped by the sandbox member size (~250 MiB).
- `AUDITMANAGER_INTAKE_RELAXED=0` by default: set it to `1` on the stand where statistics intake must
  accept the lifted quotas.
- DB-measured inventories (`tests/integration/db/test_schema_invariant_inventory.py`,
  `test_schema_shape.py`, `test_migration_lifecycle.py`) predate 0042 and need a re-measure on a database
  at `0045_comparison_page_bounds`.
