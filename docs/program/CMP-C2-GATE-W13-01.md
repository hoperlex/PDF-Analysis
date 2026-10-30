# CMP-C2-GATE-W13-01 — historical W13 response compatibility

Task: [`CMP-C2-GATE-W13-01`](tasks/CMP-C2-GATE-W13-01.md). Frozen C2 input: API `1.11.0` (176 paths / 198 operations / 517 schemas), migration head `0040_comparison_ai_reports`, product `VERSION` `0.9.0`.

## Gate finding

The first full C2 code-candidate gate on `06c312a3` passed frontend lint, typecheck and 3,653 Vitest tests, 1,310 contract tests, the 35-test foundation and the changed-context integration battery (**6,592 passed / 13 skipped / 244 subtests passed**). The canonical rest reached the historical W13 response corpus and showed 20 failures, so the already-red gate was stopped for diagnosis; it did not produce `GATE OK`.

The twenty response differences have two exact causes: sixteen historical error bodies say `contract_version: 1.0.0` while the live API correctly says `1.11.0`; four version reads now include the `CMP-SEAL-C0` additive `upload_kind: portal_bundle` member. No status or header difference was reported. A focused run with the gate's local DB/S3 permissions reproduced **20 failed / 50 passed** in 7.86 s. A default-sandbox attempt lacked DB access and is not used as evidence.

## Repair

The records under `tests/characterization/w13_baseline/records/**` remain byte-for-byte unchanged. `test_response_baseline.py` now projects only those two additive surface changes in memory before the original byte comparison. It names the exact 16 error cases and 4 version cases, pins SHA-256 `6518c1253e1d269585b71c7f68c398bc0f33812abad0ef974653336fe3b436fd` over the complete bytes of those 20 record files, and refuses a changed record. The projected error version comes from this tree's frozen OpenAPI `info.version`, not from the server response. The projected upload kind is the literal `portal_bundle`. Length changes are applied to the expected pre-token body length, as the earlier CSV compatibility projection does.

The original comparison still checks every other body byte, status and header. New planted-difference controls prove that a wrong current contract version, a wrong upload kind and an altered historical body are red.

## Verification and scope

After repair, the complete focused W13 file passed **73 tests in 7.32 s** with the same local DB/S3 permissions (`/tmp/cmp-c2-w13-after-controls.log`). The full `make gate` remains assigned to `CMP-WAVE-C2-INT` on its exact final clean candidate. `git diff --check`, governance, unchanged record Git objects and final scope proof are recorded in the task Handoff after commit.

Only this test file, its task and this report changed in the repair. No historical record, application source, contract, migration, dependency/lockfile, composition root, global style or infrastructure file changed. The projection assumes OpenAPI `info.version` is the authoritative current error-envelope version; contract tests independently enforce that pin. It does not make a claim about live model calls or deployment.
