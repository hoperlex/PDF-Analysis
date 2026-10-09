# W52-INT-VALIDATION-ENTRY-01 — deferred validation entry

**Date:** 2026-10-09. **Verdict:** the W51/W52 validation sequence is
specified on the exact development readback
`aeed8e35f3b12c5f2f506fdc9dd0585058b04385`. This is a docs-only
entry, not a QA or release verdict. D-137–D-140 remain open.

## 1. Changed files and subject

- `docs/program/tasks/W52-INT-VALIDATION-ENTRY-01.md` grants this entry.
- `docs/program/W52-INT-VALIDATION-ENTRY-01.md` records its evidence and order.

The clean development base is `aeed8e3` on `origin/dev`; the separately
published main is `21eba6e`. Their common ancestor is `3fc0dcf`, with
8 main-only and 20 dev-only commits. Neither tip is an ancestor of the
other. The last release tag remains `alpha-w48.1`.

## 2. Checks and operational observations

Read-only `git ls-remote origin refs/heads/main refs/heads/dev
refs/tags/alpha-w48.1` on 2026-10-09 returned the exact refs in the task's
P-02. The development worktree had no tracked or untracked changes before
this entry. `VERSION` reads `0.3.0`; `tests/support/expected_facts.json`
pins API 30 paths / 37 operations / 83 schemas, 23 API error codes,
head `0016_release_notes` and `contract_version=1.0.0-draft.1`.
Focused governance and prose checks passed: **93 passed** from
`test_wave_governance.py`, `test_doc_prose_facts.py` and
`test_surface_counts_in_prose.py` using the repository runtime Python.
No full `make gate` was run for this docs-only entry.

The public GitHub Actions API reports
[run 37797524976](https://github.com/hoperlex/PDF-Analysis/actions/runs/37797524976)
for `21eba6e`: push event, one completed successful attempt; job
`113380751437`, **Deploy exact AuditManager revision**, completed
successfully, including its **Deploy and verify exact commit** step. The
workflow source at that SHA selects `github.sha`, runs `deploy.sh` and
`verify-deployed.sh`, checks clean exact HEAD and prints `DEPLOY OK` only on
success. The public log API returned HTTP 403, so its literal verifier output
was unavailable. A verified-TLS probe of the public `/` reached
`/login?next=%2F` with HTTP 200; anonymous `/api/v1/openapi.json` returned
401. These checks do not prove which Git tree is on the host **now**.

Main's own `W52-INT-MAIN-SEAL-01.md` records three full gate attempts with
no literal `GATE OK`; the last was storage-affected. There is no later gate
result on that main history. Workflow success is deployment evidence for its
push, not a replacement for the missing prepublication gate. The only local
containers seen were the owner's `auditmanager-w19a` API, web, proxy,
PostgreSQL and S3 stand; no isolated W52 gate container was running. No
container or owner stand was changed by this entry.

The main-only tracked test delta after `3fc0dcf` covers:

```text
tests/characterization/w13_baseline/journey.py
tests/integration/access/conftest.py
tests/integration/api/identity_surface.py
tests/integration/api/qa_w49/conftest.py
tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py
tests/integration/composition/test_every_port_implementation_is_whole.py
tests/integration/composition/test_router_answers.py
tests/integration/db/test_fixture_template.py
```

Dev still pins `0015` in `test_fixture_template.py`, omits the release
port from the whole-port guard and still counts six unaddressed GETs in the
composition guard. Main corrects those for the Stage-B seal, but its two
release GET tests require deliberate 503 responses; Stage C on dev now
implements the release backend. Reconcile these tests against the complete
dev behavior before a combined candidate or final gate. Main's provider-mode
and database-fixture corrections also need comparison with dev's later
test-isolation work; do not copy the eight files wholesale.

## 3. Validation and correction order

1. Issue separate exact-SHA tasks for `W52-AUDIT-01` and `W52-ATTACK-01`.
   Audit W48–W52 seams; attack identity black-box first on a disposable
   built stand, including roles, registration throttles, IDOR, redirects,
   sessions, CSRF, account purge and the 780 px hostile-text case. Record
   path:line, reproduction, consequence and release-blocking priority.
2. Triage both reports. Grant every upheld correction an exact path set;
   include main/dev test reconciliation as its own integration grant. Preserve
   frozen contracts and migration unless a separately owned reseal is ruled.
3. Run Stage-D `W52-QA-01`, `W52-JUDGE-X`, `W52-JUDGE-Y` and
   `W52-NOTES-JUDGE` on the integrated candidate, with the two judges
   cross-examining each other. The attacker covers release operations by
   each role and guest/profile case, mark monotonicity, loader tampering and
   rollback, unchanged redeploy, banner behavior and BFF session refusal.
   The architecture judge checks ALR-05, server-owned `whats_new`, independent
   facts and each debt closure's own check. The notes judge verifies every
   release-note claim against the diff and tree.
4. Perform `W52-FIX`, rerun the notes judge, run W51/W52 browser and human
   acceptance A01–A20 on the candidate, and run a complete `make gate` on
   that exact clean SHA with literal `GATE OK`. Arrange an isolated gate slot
   with stand owners first. Record the measured API build, workflow and
   deployed-tree verification only when those checks actually run.
5. At validation close, reconcile the register actions listed in W52 plan
   §4 and D-137–D-140 by evidence, then publish a gated candidate to
   `origin/dev`. A later `origin/main` update and `v0.3.0` tag require the
   owner's separate direct instruction naming that exact candidate.

## 4. Contracts and risks

No contract, migration, generated client, runtime behavior, dependency,
composition root or global style changes. The frozen W52 set is
`VERSION=0.3.0`, API 30/37/83, 23 API error codes, domain revision 9 / 29
opaque identities, migration head `0016_release_notes` and contract version
`1.0.0-draft.1`. Dev's code-first close did not run a complete gate,
independent QA or live/manual acceptance. The successful workflow on main
does not resolve D-137–D-140 or demonstrate a current host SHA.

## 5. Integrator instruction

Run the focused docs governance/prose checks and `git diff --check`; commit
only the two named files, prove a fast-forward and publish the docs-only
entry to `origin/dev` after a fresh remote readback. The next work is the
AUDIT/ATTACK grant on that exact readback. Before any combined candidate,
review the eight main-only test paths semantically, especially the Stage-B
503 assertions that no longer describe completed Stage C.

## 6. Forbidden-hotspot proof

This entry's diff contains only its task and report. It does not change the
owner root worktree or stand, main/dev code, `contracts/**`, a migration,
root dependency or lock file, composition root, global style, generated
client, release notes, `origin/main` or a tag. No checkpoint was created.
