# HOTFIX-ANALYSIS-1030 — implementation handoff

2026-10-30, shared `cmp-int`; root is the sole integrator and Git writer. API 1.14.0 and migration 0043 are root-owned inputs. This lane changes no contract, migration, root dependency, global style or deployment ref.

## Delivered behavior

Fresh ordinary Runs with the immutable accepted policy `{enabled:true,max_blocks:16,plan_version:"extended-review-v1"}` now execute a real multimodal preliminary review after text analysis. All 15 existing ordinary section profiles use the common bounded method. Historical commands without that policy make no additional calls.

The method selects at most 16 saved, geometrically matched IMAGE blocks, checks their PNG size/SHA and attaches actual bytes in at most two requests of eight images. Inputs include native page text, distinctly marked recognized context, neighboring pages and the document-context section titles. Page contexts are deduplicated and bounded to 24,000 characters per request. One further request semantically merges visual and existing text observations. Thus the additional provider budget is at most three calls. Explicit input IDs bind merge results to their exact source union; omitted input observations are retained with a warning.

The output is separate preliminary observations, not canonical findings or expert decisions. Sources retain version/block identities, page, normalized box and crop SHA, or an existing native text quote. Counts and skipped block identities disclose coverage beyond the approved window, unavailable geometry and clipped context. No image observation fabricates a native quote or native text coordinates.

Normative queries use the Run's pinned corpus snapshot through `norms.public.search_norms`: at most 12 unique queries, three hits/query, six candidates/observation. Retrieval happens **before** the existing third semantic-merge call. That call receives deduplicated actual paragraph/document/snapshot IDs and corpus quotes, tied to each input observation's candidate IDs. It returns a provisional `norm_assessment` (`supports`, `contradicts` or `insufficient`), a bounded explanation and exact paragraph citations. The parser rejects foreign paragraph IDs, changed or missing quotes, and assessments without candidate context. This is a model comparison with a quote, not verification of edition, applicability or a violation. Missing corpus/query or exhausted lookup window is explicit `unavailable`. A failed or malformed merge preserves every original text and visual observation.

## Runtime and custody

- Public read seam: `runs.public.read_extended_review(sessions, blob_store, run_id) -> {run_id,status,result}`; root supplies authorization and transport.
- Roles: `analysis.extended_review` / `analysis.extended_reply`; corresponding generic Blob roles are `analysis_extended_review` / `analysis_extended_reply`. Publication uses actual artifact intents, binding and available Blob metadata. The latest review ref lives in the existing `text_analysis` StageResult.
- Every extra call uses the ordinary Run's attempt authority, approved model/price/connection guard, shared CostMeter and durable `provider_call_effect` / `model_call` journal. Saved replies retain checksum-verified Blob custody and are reused without resending or charging again.
- A prepared/received/unknown/abandoned effect fences retransmission. Source or same-phase request changes after a possibly processed effect refuse explicitly. Only a proven `not_processed` effect permits a fresh dispatch.
- Before dispatch the executor checks current attempt authority and running Run state. No new worker, table, in-memory job state or direct provider client is introduced.
- RunProgress mounts a self-contained review widget preserving the incoming layout. It shows status, coverage, sources, lazy actual crop previews, norm candidates, provisional model quote review and unreviewed blocks. Norm candidates link to the existing norm document viewer. It uses generated read transport and the existing shared crop-address seam.

## Changed files

- `src/auditmanager/analysis/extended/{__init__,core}.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/jobs/extended_review.py`, `src/auditmanager/jobs/public.py`
- `src/auditmanager/runs/extended_review.py`, `src/auditmanager/runs/executor.py`
- `web/src/widgets/extended-review/index.ts`, `web/src/widgets/extended-review/ui/extended-review.tsx`
- `web/src/widgets/run-progress/ui/run-progress.tsx`
- `tests/unit/analysis_extended/{test_core,test_runtime,recorded_sql_smoke}.py`
- This report and the task handoff addendum.

## Focused validation

- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/analysis_extended`: **19 passed**. Covers frozen opt-in, real two-by-eight-image requests plus merge, explicit 16/18 coverage, closed source/merge bindings, bounded parser, saved-reply reuse, norm candidate lookup/window, genuine quote context before merge, forged/missing/changed normative quotes and preservation of original observations after an invalid merge.
- `PYTHONPATH=src .venv/bin/python tests/unit/analysis_extended/recorded_sql_smoke.py ../beta-cost-preflight-1030/.env`: **PASS** on assigned PostgreSQL 58050. Real durable call intent/receipt/completion, artifact custody, completed replay without resend, changed-source/request refusal, unknown-effect fence and saved result read. Synthetic metadata only, outer transaction rolled back; no S3 or provider connection.
- `npm run typecheck` from `web`: **PASS**.
- Scoped Python compile: **PASS**. `git diff --check`: **PASS**.
- No actual model calls, full gate, whole-suite execution, new stacks, deployment or Git mutation by this lane.

## Provenance and limits

Method provenance is original `pdf-proverka` at `3c99481719218b9cfa7560886529916646c61939`, notably its block/context/semantic-merge sequence in `backend/app/pipeline/manager.py`. This is a local adaptation against current immutable artifacts and public model APIs; it does not import the original filesystem runner or claim full original parity.

The review requires existing portal IMAGE blocks and product-created crops. A native PDF alone does not acquire OCR or artificial block identities through this hotfix; unavailable image inputs produce an explicit unavailable result. The initial 16-block window has no automatic paid continuation. Section depth is common, bounded preliminary review rather than full specialist checks. Corpus candidates remain unverified. Model quality and live-provider image delivery have not been exercised before dev publication.

Root should commit these owned files together with its accepted-policy/estimate, API/read adapter and image transport provider changes, run its bounded final build/checks, then publish the authorized dev candidate. Disabling the new policy for fresh estimates stops future extra calls; preserve accepted authority and saved historical results. No authority for `origin/main` is granted.
