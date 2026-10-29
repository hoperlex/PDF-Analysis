# CMP wave C2 — version comparison AI, specifications, reports, queue

Integrator: the CMP integrator on `integration/compare-modules` (wave C1 closed, `docs/program/CMP-WAVE-C1-REPORT.md`;
CMP-SEAL-C2 merged). Plan `COMPARE-MODULES-PLAN.md` §1.1 (steps 4/6/7, «ИИ-описание изменений», «Полные спецификации
(СО)», «Сводка MD и отчёт для заказчика», the PDF report window, the side panel «Изменения в листе»), §3 (A-6, A-8,
A-12), §3.2, §4.0, §4 wave C2; ADR-0025 and both addenda; the seal's report `docs/program/CMP-SEAL-C2.md` (operations,
tables, the per-lane list — binding); the original's version comparison in
`docs/program/compare/ORIGINAL-VERSION-COMPARISON-INVENTORY.md` and `ORIGINAL-UNREAD-SOURCES.md` (read the original at
commit `23f379fd` from `https://raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd/<path>` where they are not
precise enough; the local clone does not exist); the corpus `fixtures/comparison/` with its answer keys.

## 1. Common rules
The rules of `docs/program/dispatch/CMP-WAVE-C0.md` §1 and `CMP-WAVE-C1.md` §1 apply (task file first with the
premise block, base facts printed — now contract `1.11.0`, `176 paths / 198 operations / 517 schemas`, head `0040_comparison_ai_reports`; shared `.venv` and
`web/node_modules` read-only; own containers; wiring hunks minimal; no contract or migration change — STOP to the FIX
slot; ADR safety rules with mutation proofs; light acceptance; never kill others' processes; no push, no merge; after
the last commit the whole `tests/unit` and `tests/contract` minus `D-220`). Additionally:

1. **Every model call goes through «Исполнители»** (plan A-6): a C2 lane never calls a provider directly; its work kind
   is routed in «Назначения»; the model is the routed connection's pinned model (`R-133`). Every test runs in
   **recorded mode** (a recorded answer per prompt digest); no lane makes a live model call.
2. **Spend before the call** (ADR-0025 decisions 10, 11 and `CMP-SPEND-01`): the journal row `comparison_model_call`
   is written `prepared` before the request, `sent` / `completed` / `failed` / `unknown` after; an unknown outcome is
   never retried blindly; the ceilings of `Q-CMP-7` ($10 per job, $50 per day per installation, a ×1.2 overrun pauses
   the job; `not_metered` unlimited) and the consented estimate are checked before every call.
3. **Images (`A-12`)**: drawing images reach a model only while `ProductVersion.comparison_modules` includes
   `versions`; at most 8 images per request, the server checks the declared `max_images` (ADR-0025); crops are opaque
   references (`CMP-EXEC-IMAGES-01`). The real measurement set never reaches a model and is gone after CMP-MEASURE-01.
4. **AI output is never the expert's decision** (AGENTS §4) and never rewrites raw deterministic evidence: a model's
   SAME or MOVED on a fragment whose deterministic status is CHANGED, REMOVED or ADDED becomes UNCERTAIN (ADR-0025);
   every AI text carries the «не подтверждено инженером» label; a recorded (test) answer is labelled as such.
5. **Content-keyed answers are never re-sent**: the key includes `project_uid`, the prompt version and the input
   digests; a stored answer is reused.
6. **Disk**: every pytest with `--basetemp=/tmp/pytest-<lane>/<run>` (outside the repo: 26 contract tests refuse an output directory inside it; `mkdir -p /tmp/pytest-<lane>` first — pytest does not create the parent), `rm -rf` it after; before a stack start or a
   whole-directory run `df -h /`, wait under 2.0 GiB, STOP under 1.5 GiB. Before an integration pytest run
   `set -a; . ./.env; set +a`. Run `tests/integration/comparison` in one process (CMP-C1-FIX-A made it possible).

## 2. Lanes
| Lane | Result | Own paths | Ports |
| --- | --- | --- | --- |
| CMP-AI-JOBS-01 (first) | the shared consented-AI-job core over `comparison_ai_job` (seal §4, §9): estimate builder protocol, USD estimate from the routed connection, `estimate_digest`, start with consent (module gate, stale estimate, ceilings, one live job per scope), the state edges pause / resume / cancel / finish / dequeue / retry, the ×1.2 overrun pause, spend and progress reads via `comparison_work.comparison_ai_job_id`, recorded-mode test support | `src/auditmanager/comparison/ai_jobs/**` (new), tests | 57940/61940/61941 |
| CMP-VC-SPEC-01 | part A first (deterministic ГОСТ 21.110 positions from profile words and vector lines, positions across pages, the engine's `spec_positions` channel input, `getVersionPageSpecPositions`, `getComparisonSheetPairSpecPositions`); part B after AI-JOBS (AI whole-specification comparison per transition, method `spec`) | `src/auditmanager/comparison/specification/**` (new), `src/auditmanager/comparison/engine/**` (the `spec_positions` channel only), tests | 57950/61950/61951 |
| CMP-VC-AIPAIR-01 (after AI-JOBS) | the doubtful-pair check with images (method `pair_check`), accepted links by rule, hints, counts | `src/auditmanager/comparison/ai_pairs/**` (new), tests | 57960/61960/61961 |
| CMP-VC-AISHEET-01 (after AI-JOBS) | per-sheet description, per-series run, single-sheet description, review list, MD per sheet, history (method `sheet_changes`) | `src/auditmanager/comparison/ai_sheets/**` (new), tests | 57970/61970/61971 |
| CMP-VC-REPORT-01 (after AI-JOBS) | the deterministic MD summary; the PDF report (client and analytic kinds, method `report`), program fact checks, reportlab with a Cyrillic font under `report/fonts/**` | `src/auditmanager/comparison/report/**` (new), tests | 57980/61980/61981 |
| CMP-VC-QUEUE-01 (after the AI lanes) | the per-project launch queue as comparison work; the installation AI queue read | `src/auditmanager/comparison/queue/**` (new), tests | 57990/61990/61991 |
| CMP-VC-UI-02 (now, against the contract) | the C2 screens of plan §1.1 | the web paths of plan §4 C2 plus `web/src/widgets/execution-queue/**` (the AI queue block only) | none |

## 3. Order and merge order
SEAL-C2 (done) → AI-JOBS (∥ SPEC part A ∥ VC-UI-02) → (AIPAIR ∥ AISHEET ∥ SPEC part B ∥ REPORT) → QUEUE → VC-UI-02 merge.
Merge order for wiring files: AI-JOBS, SPEC, AIPAIR, AISHEET, REPORT, QUEUE, VC-UI-02. A FIX lane closes the wave.
Deviation from the plan order (QUEUE before REPORT): REPORT does not depend on QUEUE, and QUEUE runs the entries of
every step, so it goes last among the backend lanes (integrator decision in the owner's 12-hour window).
