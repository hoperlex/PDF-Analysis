# BETA-COST-JOURNEY-1030 — narrow preflight compatibility

Date2026-10-30. Completed source compatibility after UI provider6fe0bd501349a66407e2d74b6828fac92f3898ea. **Browser/API/worker execution remains UNVERIFIED.** No model, build, gate, remote ref or deployed service was invoked.

## Result
The six existing ordinary start steps explicitly perform bounded `approve_run_cost` actions before their original start clicks. Each declares the real `estimateRunCost` POST and retains every previous start/terminal assertion. The action uses the actual UI, waits for a successful observed estimate, verifies its scope/version/options, reads and checks the exact prefilled recommended finite cap, then presses the unchecked agreement checkbox. Later observed starts must carry identical options and the exact approved digest/cap/confirmed consent plus a command key. An absent estimate, failure, malformed/nonfinite amount, changed start payload or missing agreement is a failure.

The closed action also supports `ar_v3_group` with its own endpoint/control. The current manifest has no served `startArV3BetaGroup` step; two historical AR v1 ordinary starts remain explicitly pending. No old step was reactivated or silently replaced, and no AR v3 acceptance is claimed. The C4 stage actions and their distinct consent mechanism are unchanged.

The first core Run now requires a recorded estimate unless the caller explicitly provides the existing `--allow-spend` flag. The driver never chooses a different provider mode. Live approval, when explicitly allowed, is still bounded by the observed estimate and finite recommended cap.

## Files
- `tests/e2e/pc01/journey/manifest.json`: six additive approval actions, cost POST declarations and consent/key expectations.
- `tests/e2e/pc01/journey/write.mjs`: closed two-scope action, bounded actual-UI approval and pure exchange verification.
- `tests/e2e/pc01/journey/README.md`: recorded/live permission, finite cap and honest pending/unverified instructions.
- `tests/e2e/test_pc01_journey_conformance.py`: closed action shape, before-start placement, exact operations and negative controls for both scopes; pure Node checks reject changed version/preset/raised-limit options, forged digest/cap/agreement and invalid amounts.
- Task and this report.

## Checks
- `python -m pytest -q tests/e2e/test_pc01_journey_conformance.py`: **139 passed in4.49s**.
- `node --check tests/e2e/pc01/journey/write.mjs`: passed.
- `node --test tests/e2e/pc01/journey/write.test.mjs`: passed.
- `node tests/e2e/pc01/journey/comparison-conformance.mjs`: passed; 14 comparison steps, exact corpus bytes and 56-row static census remain intact.
- `git diff --check`: passed.

## Integration and boundaries
Root integrates this local followup after BETA-COST-WEB-1030 and the backend provider. All changed paths are the root's exact journey/conformance grant plus task/report. Product source, shared API/contracts/generated files, migrations, locks, composition and styles are untouched by this commit. Tomorrow run the browser against the exact candidate and preserve its real exchange/terminal/download envelope; source checks are not acceptance. Revert only with the matching start-policy/UI change, since an old driver cannot press an unapproved start.
