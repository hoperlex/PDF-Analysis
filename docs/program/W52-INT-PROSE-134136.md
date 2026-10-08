# W52-INT-PROSE-134136 — W50 prose corrections

The two W50 judges established that invalid return-path input stays out of
visible text, the hidden form field and redirects but can appear escaped in
Next router metadata; that `/optimisation` is intentionally open by address
and hidden from the menu; and that four first-load routes shrank while the
review route grew 1,370 bytes within the 1,536-byte allowance.

This task updates the live comments in `web/src/shared/config/screen-registry.ts`
and the §3.2/§3.4 wording in `docs/program/dispatch/W50-PLAN.md` to those measured
facts. It does not edit the historical judge reports, route data or code
expressions. D-134…D-136 are narrowed to deferred validation, not used as a
release claim.

## Files and checks

Changed: `web/src/shared/config/screen-registry.ts`,
`docs/program/dispatch/W50-PLAN.md`, `docs/program/CURRENT_STATE.md`,
`docs/program/DEBT_REGISTER.md`, `docs/program/tasks/W52-INT-PROSE-134136.md`
and this report.

Focused return-path and navigation tests, governance/prose tests, frontend
lint and `git diff --check` passed. No browser stand, new production build,
QA or full gate was run; those remain D-139/D-140.

No contract, migration, dependency, composition root, global style or runtime
expression changed. Publish only to `origin/dev` after exact remote-ref and
fast-forward checks. Revert this one documentation commit if rolled back; no
feature flag is needed.
