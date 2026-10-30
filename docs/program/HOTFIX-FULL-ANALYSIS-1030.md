# HOTFIX-FULL-ANALYSIS-1030 — candidate result

## Behavior

Fresh ordinary section Runs freeze `extended-review-v2` with `max_blocks: "all"`. Old accepted v1/v2 Runs retain their sixteen-block window and existing request identities. The new path selects every admitted portal image crop, or renders every page of a text-only/native PDF, in eight-image calls. It passes every prepared page character to comprehensive review in repeatable requests, preserves all base observations and deterministic merge inputs, and searches/reviews every candidate-bearing observation in batches. Per-request schema/context limits remain finite; they no longer select the first sixteen blocks/pages or first forty observations for the *whole Run*. The read artifact marks `review_scope: full_document` and the UI says what was planned. Missing corpus, unusable source geometry, provider refusal and the two-hour Attempt hard cap still yield an explicit partial/unavailable result.

The preflight reads the immutable `source.structured_companion` member through the existing Blob store and verifies its recorded size and SHA before counting IMAGE blocks. This avoids pricing the 1,000-image ingest maximum for a 47-block bundle. If the member is absent, the preflight uses the ingest maximum for that page count; the cost estimate is deliberately conservative. Fresh metered Runs still require cost approval, and the pre-call meter enforces their accepted ceiling. Unmetered connections have no monetary cap. No existing accepted command acquires new paid calls.

## Checks

- `tests/unit/runs`, `tests/unit/analysis_extended`, and the Codex adapter test: **202 passed** using a local venv with NumPy.
- Focused extended/cost/Codex set: **87 passed**. Includes 47 blocks and 47 pages with six image plus six comprehensive calls, 109,002 page characters delivered without truncation, more than forty base observations, 41 normative observations across multiple calls, and the verified companion count.
- Frontend: typecheck and scoped ESLint passed; extended workflow Vitest **9 passed**.
- Python compile, `git diff --check`, direct task governance findings `[]`: passed.
- PostgreSQL integration test was attempted and could not start because `DATABASE_URL` is absent from this isolated worktree. The first broad unit attempt had two unrelated import failures because its venv lacked NumPy; the complete rerun with a NumPy-equipped venv passed. Full `make gate` and live-document/provider acceptance were not run on this candidate. The host has only 219 MiB free on `/` and the task's isolated PostgreSQL/S3 stack is not running; creating a fresh gate stack on this host is not safe at present.

## Integration and limits

Changed paths are the task and this report; the extended analysis core, native page renderer and workflow; Run extended review, preflight and cost reader; the one `RunAdapter` preflight construction line; their focused tests; and the extended review widget/test. The named composition slot only passes an existing Blob store. No contract, migration, lockfile, global style, model profile or prompt changed. This branch also includes the earlier Codex optional-schema repair, which the host currently runs as an operational hotfix.

Code candidate `854970b4` was published as a fast-forward to `origin/dev` after the focused checks. This is a development candidate, not a deployed application change. `origin/main` needs a full `make gate` with literal `GATE OK`, then a separate owner instruction naming the exact gated SHA, the main auto-deploy policy and host verification. Existing Runs are terminal and need a fresh cost estimate/consent and a new Run to use the full-document policy. `AUDITMANAGER_EXTENDED_ANALYSIS=0` stops offering the extended policy to new Runs; reverting this hotfix restores the previous default while old accepted authorities remain readable.

The accepted document ceiling is still 500 pages and, for portal bundles, 1,000 IMAGE blocks; those are source-ingest/resource limits, not an analysis selection window. Provider request/output bounds, source integrity checks, corpus availability, monetary approval and the Attempt deadline remain. A truly unlimited Run would require a separate durable multi-Attempt execution design and cannot be represented as one finite provider request or a silently unbounded charge.
