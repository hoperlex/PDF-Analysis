# BETA-PDF-PRECHECK-1030 — full background PDF check before model analysis

Implementation is complete for the owner's 2026-10-30 decision. The existing durable Run/Job/Attempt carries the full check in `source_preparation`, before the ordinary-section and AR v3 provider branches. Upload admission keeps its fast reader. No queue, migration, API operation, external provider call or unchecked-input bypass was introduced.

`pdf_precheck_child.py` runs the pinned pypdf envelope probe and pdfplumber's complete page interpreter (`page.objects`) followed by the existing normalized line/text extraction. It streams a bounded receipt to the worker, which validates page order/counts, text/line agreement, normalization and finite geometry and returns the same `ExtractedDocument` used to publish the prepared artifacts. Parser failures, resource limits, incomplete receipts and count disagreements refuse the stage; partial text is never published. The existing portal text-or-block rule still applies after full interpretation, before successful completion is reported.

The child receives only an inherited source descriptor and a bare environment, with stderr discarded. It uses the exact source tree of its launcher under isolated Python. The parent kills and reaps it on cancellation, timeout, authority loss and any receipt failure. The child also has its own real-time alarm so a vanished parent cannot remove its wall bound. Temporary verified source files retain their existing unconditional cleanup.

| Bound | Value |
|---|---:|
| Child address space | 1536 MiB |
| Child CPU time | 1200 s |
| Document wall time | 1800 s |
| Child startup | 45 s |
| Page interpretation / receipt | 180 s |
| Pages | 500 |
| Page / document characters | 200,000 / 20,000,000 |
| Receipt line / total bytes | 32 MiB / 256 MiB |

These are finite operational limits, not measurements of maximum-size acceptance. A valid document exceeding them gets an explicit refusal. Linux `/proc/self/fd`, POSIX resource limits and selectors are required, matching the worker environment. Full large-corpus/resource-window acceptance remains deferred with the owner's heavy checks.

The public seam is `analysis.public.run_source_preparation_with_progress(context, *, progress, checkpoint, expected_page_count)` and `PdfPrecheckProgress(phase, completed_pages, total_pages, error_code=None, reason=None)`. Executor supplies the handler directly; bootstrap changes are unnecessary. Existing execution-journal events use `stage.pdf_precheck`, aggregate `AuditRun`, the canonical Run ID, and scalar payload `stage_id='source_preparation'`, `phase=started|checking|completed|failed`, `completed_pages`, `total_pages`. A failed record adds a catalog error code and fixed screened reason. Neither raw PDF text, parser diagnostics nor file names enter the journal. `completed` follows all page and portal validation. Cancellation is represented by the existing Run state.

Executor checks current Attempt authority during parsing, without retaining an open DB transaction between checks, and fences every event write with `JobRepository.require_current`. Intermediate checking events are limited to one per second; the last page and terminal phase always commit. Only completed page receipts mark actual Attempt progress. A cancelled or superseded Attempt cannot append a terminal progress event or reach either provider branch. Root owns the progress widget and reuses its existing journal query/polling.

The same executor consumes cost-owner provider commit `29c9c870`: `read_run_cost_policy` restores accepted cap, window count/size and model/rate/connection pins. Approved caps apply in raised-limit mode. `_bind_provider` preserves the accepted fields when a DB route supplies its configuration. Historical commands retain the provider's legacy policy. The cost provider and its contracts are owned by the parallel cost task; this lane changes only its approved executor seam.

Changed implementation files: `analysis/stages/pdf_precheck.py`, `analysis/stages/pdf_precheck_child.py`, `analysis/stages/source_preparation.py`, `analysis/public.py`, `runs/executor.py`, and the progress scalar allowlist in `jobs/events.py`. Tests are scoped to `tests/unit/analysis/test_pdf_precheck.py`, `tests/unit/runs/test_pdf_precheck_executor.py` and `tests/integration/runs/test_pdf_precheck.py`; this report and its task file complete the change.

Focused verification on the root-assigned existing 58060/62060 disposable stack:

- 13 unit tests passed: real text/geometry equivalence, bad font after a readable first page, page-count disagreement, actual child memory bound, cancellation kill/reap, timeout, malformed/partial/bounded receipts, no-text refusal and preserved approved DB configuration.
- 4 integration tests passed: independently visible completed check before provider binding; full-interpreter failure before ordinary and AR v3 provider branches; cancellation after a real page, fenced loser progress and no model calls. The AR v3 refusal test injects reviewed-pack selection/binding only; it does not claim full reviewed-pack acceptance.
- 3 existing source-preparation regressions passed: a textless portal page with a block stays admissible; the verified temporary PDF is removed after success and extraction failure.
- Targeted Python compilation and `git diff --check` passed. Initial sandboxed DB setup was unable to connect; the same four tests passed with approved localhost access. No browser, build, full gate, live provider, large corpus or heavy acceptance window was run.

Integration: cherry-pick this lane's final commit after provider `29c9c870`, retain root progress UI `49b4018e`, and preserve both PDF and cost exports in `analysis/public.py`. No bootstrap/contract/migration follow-up is needed for PDF. The final commit's path list proves forbidden hotspots unchanged; the provider was merged by root in `24caa634` before this lane's commit. No remote ref, tag or deployment was changed. Rollback is the code revert; no persisted schema requires rollback.
