# W57A-INT-REPORT-READ-PREP-01 — unserved v3 report read

**Base:** `f0580e089867ba6a9380a48dfca19a23e47f6788` (`origin/dev` dev37). **Status:** isolated source candidate; no remote publication or runtime activation.

`citation_report.py` composes the existing certified citation reader with three SELECT-only reads in the caller's repeatable-read transaction. It checks exact Run, Version, profile, snapshot and set identity; counts persisted withheld observations by the closed diagnostic reason vocabulary; preserves stored textless pages as context; and reads a typed error for a partial stage. Missing page metadata, inconsistent provenance, nonterminal stage state or competing partial error codes refuse. An empty diagnostic read yields zero only after the citation reader has certified the Run and CITE stage.

The result is an immutable DTO shaped for a later `NormVerificationReport` adapter. It is deliberately unserved: the current API adapter still returns `dependency_unavailable`, and no role authorization or registered profile wiring changes. Real PostgreSQL acceptance and a qualified corpus/set remain separate work.

## Checks

- Focused offline suite: `tests/integration/findings/test_w57a_citation_report_offline.py` plus existing citation reader tests — **43 passed**.
- `py_compile`, `git diff --check` — pass.
- Frozen API, stage, domain, error and migration SHA-256 — unchanged against task inputs.

## Integration

Cherry-pick this one bounded source commit after dev37. A later CITE integration task must supply authorized Run and registered v3 profile ID, hold one repeatable-read transaction, run real DB readback against 0023, map the DTO to the sealed API response, and own the route/composition edit. No host service or provider call was used.

Changed paths are exactly this report, its formal task, the additive reader and its focused offline tests. `contracts/**`, migrations, lock files, composition root, API/UI, `CURRENT_STATE.md` and remote refs were untouched.
