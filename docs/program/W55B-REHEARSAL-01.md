# W55B-REHEARSAL-01 — report (the two halves of W55b at their limits, and the real export once)

- Task: the wave integrator's brief for lane `W55B-REHEARSAL-01`; owner ruling `R-122` (`OWNER_RULINGS_2026-09-17.md` §3.33 on
  `integration/w55b`): runs now, in parallel with the judges and QA, on a disposable stack of this host; figures on a loaded host
  and on the tree before `W55B-FIX` are accepted; every figure records its tree, load and available memory. F-7 and `R-119`: the
  owner's export is read only, the report holds counts only, nothing derived from it is committed.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `e1233e7a` (the WEB-BLOCKS report).
- Written by one writer (a Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.
- Grant: `scripts/rehearsal/w55b/**` (new) and this file. Nothing else.

## 0. Status (living; updated at every commit)

| Step | State |
| --- | --- |
| living report, plan | done (`a35645fe`) |
| tools: generators, sampler, driver, figures, browser drive, crop fidelity, the hard memory cap | done (`58ddb5cf` to `ae85ab20` and after) |
| stack up (PostgreSQL 57480, S3 61080/61081, API 57580/57581, Next 31680), every heavy process in a capped systemd scope | up |
| (a) 500-page text-rich bundle: upload x3, budget refusal x2 | done: 201 in 0.82 to 1.05 s, `VmHWM` +28.8 MiB (first in a fresh process) then +3 to +6 MiB; 422 `analysis_input_budget_exceeded` (1 786 430 > 152 361), no row created |
| (b) 500-page low-text bundle: upload, run x2, «Блоки» x2 | done: upload 201 in 1.79 s, `VmHWM` +342 MiB; run `failed` at `text_analysis` (`recording_missing`, expected) after both deterministic stages succeeded; `source_preparation` 1.36/1.45 s, `page_geometry_extraction` 111.2/107.6 s; API peak RSS 600 MiB, scope `memory.peak` 806/814 MB under a 3 GiB cap; 500 crops, 415.9 MB of PNG; «Блоки» 1 500/1 500 blocks after 14 presses, 150 to 290 ms a press |
| (c) the owner's export: upload, run, «Блоки», crop fidelity (counts only) | pending |
| teardown, final report sections 1 to 6 | pending |

## 1. Plan and decisions (made while writing; each open to the integrator's veto)

1. **One private stack, recorded provider mode, no paid call.** `FOUNDATION_INSTANCE=auditmanager-w55b-rehearsal`, PostgreSQL
   `57480`, S3 `61080/61081`, the API (`infra/deploy/serve.py`) on `57580` with its health port on `57581`, Next on `31680`.
   `AUDITMANAGER_PROVIDER_MODE=recorded`, `EXECUTION_ROLE` unset (`all`): the run carrier is a thread of the serving process
   (`runs/carrier.py`), so both deterministic stages run inside the API process whose memory is sampled. No proxy key exists;
   `R-29` applies. The text-analysis stage may fail on a synthetic document for want of a recording; that is reported as such.
2. **Memory per phase.** Before each phase the API process's high-water mark is reset (`echo 5 > /proc/<pid>/clear_refs`) and
   `VmHWM` is read after; during a run `VmRSS` is sampled every 0.25 s with wall-clock timestamps and aligned with each stage's
   `started_at`/`finished_at` from `stage_result`, so each stage's peak is read separately although both run in one process.
   The sampler is checked against a known allocation before it is trusted.
3. **Every figure carries its context**: the worktree's `HEAD` and whether the tree is clean, `/proc/loadavg`, `MemAvailable`
   and free disk at the time. Before every heavy step: `MemAvailable >= 3 GiB`, `df /` free `>= 5 GiB`, no `make gate` running.
4. **Generators are deterministic given a seed** and reuse `tools/fixtures` (the portal-bundle builders, the AR corpus PDF
   writer and its embedded Cyrillic font, the reference validator); each bundle is also passed through the product's own reader
   and envelope (`extract_bundle`, `admit_bundle`) before it is used, so it is admitted for the right reasons.
5. **Outputs are build products** under `.local/rehearsal-w55b/` (git-ignored); they and the stack's volumes are deleted at the end.
6. **The live input-token count of the real set** (`W55B-BUDGET-01` §6 item 4) is **owed**: no live model call is made here.
7. **A hard memory cap on every heavy process** (the integrator's addendum, from JUDGE-X X-1/X-2): the API, Next, the
   bundle builds, the browser drive and the fidelity check each run in a transient systemd scope
   (`systemd-run --scope -p MemoryMax=<N> -p MemorySwapMax=0`), `N` at most 3 GiB and never above `MemAvailable` minus 1 GiB at
   its start; `N` and that `MemAvailable` are recorded per start. The API is restarted (a fresh scope) before each heavy phase,
   so the scope's `memory.peak` is that phase's. The API runs through `instrumented_serve.py`, which runs `serve.py` unchanged
   and records the resident set after every page of each stage's passes (no product file edited).
