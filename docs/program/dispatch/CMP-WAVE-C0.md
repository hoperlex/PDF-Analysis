# CMP wave C0 — the foundation lanes after CMP-SEAL-C0

Integrator: `pdf-analysis-4d` on `integration/compare-modules` (tip after the seal merge `0990de4b`). Plan:
`COMPARE-MODULES-PLAN.md` §3.2, §4 (wave C0), §4.0; ADR-0025 (decisions and the 2026-10-27 addendum); the seal's
report `docs/program/CMP-SEAL-C0.md` (operations, tables, the per-lane table in its last section).

## 1. Common rules (every lane)

1. **First commit: your task file** `docs/program/tasks/<TASK-ID>.md` from `docs/templates/TASK_TEMPLATE.md`, with the
   premise you captured (print the base facts: contract `1.9.0`, 115/130/351, head `0038_comparison_foundation`; STOP if
   different) and your allowed paths exactly as below. Last commit: your report `docs/program/<TASK-ID>.md` and the
   task file's Handoff.
2. **Environment (disk is the binding resource, ≈ 4 GB free on a shared host):** do NOT run `make bootstrap` or
   `npm ci`. Python: `/root/projects/PDF-Analysis/.local/worktrees/cmp-seal-c0/.venv/bin/python` with
   `PYTHONPATH=$PWD/src` from your worktree root (it has numpy, opencv-python-headless, reportlab). Web: `ln -s
   /root/projects/PDF-Analysis/.local/worktrees/cmp-seal-c0/web/node_modules web/node_modules` (never write into
   that directory; remove the symlink before your last commit is checked, it is git-ignored). Never edit anything in
   `.local/worktrees/cmp-seal-c0`.
3. **Containers:** only a lane listed with ports below starts its own foundation stack (`.env` both sides with its six
   values; `make up` / `make down` from its worktree). Bring it down when done. Never touch other containers.
   `df -h /` before every container start and every long run; stop and report under 1.5 GiB free.
4. **Wiring (plan §4.0 rule 1):** the lane that implements a sealed operation owns its adapter class in
   `src/auditmanager/bootstrap/adapters.py`, its rows in `src/auditmanager/api/routers/ports.py`, its router file, and
   the removal of its rows from `SEALED_STUB_GETS` / `SEALED_STUB_ADDRESSED` / `EXPECTED_ADDRESSED`
   (`tests/integration/composition/test_router_answers.py`, `test_an_absent_parent_is_not_an_empty_page.py`) and of its
   tables from `SEALED_NOT_YET_WRITTEN` (`scripts/recovery/grant_classification.py`). Appends to
   `src/auditmanager/comparison/public.py` are yours for your names only. Keep these hunks minimal: the integrator
   merges lanes in the order of §3 and resolves overlapping hunks.
5. **No contract or migration change.** A missing field → STOP and report (the wave's FIX slot), never edit
   `contracts/**` or `db/migrations/**`.
6. **ADR-0025 safety rules are acceptance criteria** (decisions 5, 7, 8 + addendum, 9, 10, 11, 16, 18, 20, 23), each
   with a mutation proof (show the guard red, restore, green).
7. **Checks (light acceptance):** `git diff --check`; your unit and integration directories; `pytest -q tests/contract`
   minus the three `D-220` files; for web changes `npm --prefix web run lint -- --quiet`, `typecheck`, `test -- --run`
   on your files; run with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`.
8. Never kill a process you did not start (no `pkill`/`killall`); no push, no merge; commit messages end with
   `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

## 2. Lanes

| Lane | Result | Own paths | Ports (pg / s3 / console) |
| --- | --- | --- | --- |
| CMP-WORK-01 | comparison durable queue (ADR-0025 decisions 4, 6, 7, 23): `comparison_work` / `comparison_work_attempt` claim, lease, heartbeat, reclaim, pause, cancel; strict priority of runs (claims only when no run is claimable; yields between items); honours `execution_control.paused` via `execution/public.py`; the module flag (`comparison/modules.py`) pauses queued work when a module is off; handler registry with one handler per `kind` (test); the worker loop hook | `src/auditmanager/comparison/work/**`, `src/auditmanager/workers/service.py`, `src/auditmanager/bootstrap/composition.py`, `tests/unit/comparison/work/**`, `tests/integration/comparison/work/**` | 57720 / 61720 / 61721 |
| CMP-STORAGE-PARTS-01 | multipart staging in the storage port (ADR-0025 decision 10): token persisted before the first part, upload part, complete, abort, verify whole; the abort sweep as a comparison work kind; unreferenced comparison blob report | `src/auditmanager/storage/**`, `scripts/recovery/blob_reference_audit.py`, `tests/unit/storage/**`, `tests/integration/storage/**` | 57730 / 61730 / 61731 |
| CMP-EXEC-IMAGES-01 | up to 8 images per task with opaque crop references on every served channel; server-side gating by the claim's declared `max_images` (absent = 1) — never hand more; `image_input_unsupported`; the runner tools; `ModelRequest` image list (ADR-0025 decision 18) | `src/auditmanager/executors/image_input.py`, `src/auditmanager/executors/pull.py`, `src/auditmanager/executors/http_adapter.py`, `src/auditmanager/executors/ssh_adapter.py`, `src/auditmanager/executors/ssh_tunnel_adapter.py`, `src/auditmanager/executors/runner_repository.py`, `src/auditmanager/analysis/text/adapter.py`, `tools/executor-runner/**`, `tests/unit/executors/**`, `tests/integration/executors/**` | 57740 / 61740 / 61741 |
| CMP-INGEST-ZIP-01 | safe reader for ZIP sets (ADR-0025 decision 12): the `bundle_archive` reader parameterised with a set policy (entries ≤ N, total ≤ 2 GiB, per-member PDF envelope, one nesting level, names never identity); its own refusal reasons under existing codes | `src/auditmanager/ingest/comparison_zip/**`, `src/auditmanager/ingest/bundle_archive.py`, `tests/unit/ingest/comparison_zip/**` | none |
| CMP-PROFILE-01 | page profiles (decisions 8, 9 + addendum): per-version rows of `comparison_page_profile`; full-page renderer in `analysis/geometry/render.py` exported from `analysis/public.py` under `PDFIUM_LOCK`; render and extraction in ceilinged children (768 / 1024 MiB, any end without a result → `RENDER_FAILED`); stored preview + thumbnail (+ tile levels ≥ 2), levels 0–1 rendered on request in a ceilinged child, never in the API process; the five sealed read operations; registration dpi rule; page profile = words with boxes, vector lines, stamp zone, sheet number/title, ink mask, scan flag | `src/auditmanager/comparison/profile/**`, `src/auditmanager/analysis/geometry/render.py`, `src/auditmanager/analysis/public.py`, `tests/unit/comparison/profile/**`, `tests/integration/comparison/profile/**` | 57750 / 61750 / 61751 |
| CMP-VERSION-MARK-01 | the «загружено без пакета портала» mark and the disabled run start on the existing version screens, from `DocumentVersion.upload_kind` | `web/src/_pages/version-detail/**`, `web/src/widgets/version-list/**`, `web/src/widgets/version-history/**`, `web/src/widgets/document-list/**`, `web/src/widgets/run-list/**`, `web/src/entities/document-version/**`, `web/tests/unit/**` (its own new files) | none |
| CMP-SPEND-01 (after WORK) | `comparison_model_call` journal `prepared → sent → completed | failed | unknown` with the pre-call breadcrumb, `spend_unknown` on reclaim (decision 5); `executor_task` origin `comparison_call`; the one-active-run-per-connection check counts comparison AI work; `dashboard` `_SPEND` union; USD ceilings of `Q-CMP-7` before each call | `src/auditmanager/comparison/spend/**`, `src/auditmanager/dashboard/repository.py`, `src/auditmanager/executors/runner_repository.py`, `tests/unit/comparison/spend/**`, `tests/integration/comparison/spend/**` (+ the one connection check in `src/auditmanager/jobs/repository.py` by grant of the PROD-20 owner, asked by the integrator) | 57780 / 61780 / 61781 |
| CMP-INGEST-01 (after STORAGE-PARTS) | plain-PDF comparison upload operations of the seal's per-lane table; comparison envelope policy with its own element limit (addendum item 3); stamp reading and proposals; `upload_kind` write/read; never `current_version_uid` over a portal version (decision 11); `comparison_only_version` refusal in `runs/commands.py`; version-order revisions | `src/auditmanager/ingest/comparison_pdf/**`, `src/auditmanager/documents/**`, `src/auditmanager/runs/commands.py`, `tests/unit/ingest/comparison_pdf/**`, `tests/integration/ingest/comparison_pdf/**` | 57760 / 61760 / 61761 |
| CMP-INGEST-02 (after WORK, INGEST-01) | the batch operations of the seal's per-lane table over comparison work; limits as typed refusals; statuses | `src/auditmanager/ingest/comparison_batch/**`, `tests/integration/ingest/comparison_batch/**` | 57770 / 61770 / 61771 |

## 3. Merge order (wiring files)
WORK → STORAGE-PARTS → SPEND → EXEC-IMAGES → INGEST-ZIP → INGEST-01 → INGEST-02 → PROFILE → VERSION-MARK.
First dispatch: WORK, STORAGE-PARTS, EXEC-IMAGES, INGEST-ZIP, PROFILE, VERSION-MARK; SPEND after WORK merges;
INGEST-01 after STORAGE-PARTS merges; INGEST-02 after INGEST-01.
