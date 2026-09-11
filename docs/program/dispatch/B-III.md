# `B-III` dispatch prompt — journey convergence QA

Base `92bece858d1e764ea75fb780e841be0126d78f24`. One session, serial, independent. Dispatch
text below, verbatim.

---

You are session `B-III`, the journey convergence QA for the PDF-Analysis prototype. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `92bece858d1e764ea75fb780e841be0126d78f24` on `planning/prototype-roadmap`. Branch `agent/gate-b3-conv`.

**Check your worktree's HEAD before doing anything else.** Every session in the last three waves arrived on `43a84d9`, a commit ~220 behind. Verify the SHA above exists and branch from it literally. A worktree pointing elsewhere is the known provisioning defect, not a signal to work from what you find.

## What you are for

Eight sessions built the backend in parallel, each against frozen seams, each verifying its own segment on its own fixture. Every one of them passed. **Nobody has yet proved they compose.**

You authored none of it and you may repair none of it. A defect you find goes back as a precise report — that separation is the whole reason you exist, and it is what made this programme's earlier repairs trustworthy.

## You own exactly these paths

- `tests/e2e/p02/**`
- `tests/integration/p02_journey/**`

Nothing else. Not `src/**`, not `db/migrations/**`, not `contracts/**`, not `web/**`, not the `Makefile`, not root locks, not another suite's tree. If a module's public surface does not let you drive the journey, **that is a finding**, not a licence to reach inside.

## The journey to prove

End to end, against real PostgreSQL and real MinIO, on the **recorded** provider adapter:

1. create a project, upload `fixtures/synthetic/ar/ar_baseline.pdf`, get one immutable `document_version` with its input manifest and a verified private object;
2. start a run; the four stages execute — `source_preparation`, `page_geometry_extraction`, `document_context_build`, `text_analysis`;
3. observations are published as findings **only** through the grounding gate;
4. accept one finding, reject another, append a later comment;
5. export the CSV and resolve every row back to the exact project, version, run, finding, observation and current verdict;
6. restart the application and execution process without losing canonical state;
7. repeat the same upload and run commands under the same idempotency keys without creating duplicate versions, runs, observations or decisions;
8. show unsupported input, checksum, unavailable-provider and ungrounded-model failures explicitly, with no filesystem fallback and no fake success.

Expected on the corpus, measured by the session before you: run state `published`, empty degradation set, **3 findings**, **5 CSV rows**, 17 columns, two exports byte-identical. Treat those as figures to reproduce independently, not as truths to assume.

## The four things most worth attacking

**1. `provider_mode` must be unfakeable.** A recorded run must never be presentable as a live one. Attack it: does anything in the chain let a recorded result reach a place that reports `live`?

**2. The diagnostic path is dead code as composed — decide whether that is acceptable.** `B3` resolves each quote against the text layer and drops what does not resolve **before** writing its artifact. `B4`'s grounding gate therefore never sees an unresolvable anchor, and **no `grounded = false` row is ever written**. Nothing ungrounded is published, so the safety property holds — but `P02_SEAMS.md` §5.1 declares a five-value `ungrounded_reason` vocabulary that records nothing, and *which* quotation a model invented survives only as a count. Two sessions each did the right thing locally and the composition made one unreachable. Your job is to determine whether PC-01 can accept that, and to say so either way with evidence.

**3. The extractor divergence.** `A4`'s manifest `page_text_sha256` values match its own reference extractor and differ from the pinned `pdfplumber` on **all eight pages**. `B5` reports that the chain is unaffected because it uses no manifest offset, and that the pinned extractor reproduces the committed text layer character for character. **Confirm that independently.** If it holds, the divergence is a trap for future sessions rather than a defect; if it does not, every evidence anchor in the system is suspect.

**4. Idempotency across the whole journey, not per module.** Each module proved its own. Nobody has repeated the entire sequence under the same keys and counted rows across every table afterwards.

## Anti-vacuity is your central obligation

**Eight tests in this programme have passed or failed without exercising what they named.** The pattern is identical in all eight: the test asserted a property of the fixture rather than of the code. Real examples, so you know the shapes:

- an immutability test called `session.rollback()` between its UPDATE and DELETE, discarding the row under test, so the DELETE matched zero rows and it reported that a database trigger had failed to fire;
- a timestamp comparison certified an adapter that was rewriting bytes, because MinIO's `LastModified` has one-second resolution and both writes landed in the same second;
- `content.startswith(BOM)` with `BOM` imported from the module under test is true when `BOM` is empty;
- four projects created in a loop all landed in one millisecond, so asserting their timestamps descended stayed green against a reversed `ORDER BY`;
- a mutation patched `routers.build_router` while the conftest had bound the name directly, so the patch reached nothing and the run came back green.

Therefore: **every guard you write must be shown to fail.** Mutate the thing it protects, confirm red, revert, confirm green, and report both. A mutation that produces a collection error or an import error rather than a guard failure proves nothing and must be redone. **Never edit a tracked file to mutate** — use a scratch copy in a session-unique directory, and note that `pyproject.toml` sets `pythonpath = ["src"]`, which overrides a `PYTHONPATH` you export; use `pytest -o pythonpath=<your copy>/src` and symlink `contracts/` into that copy, or your mutation will silently not apply.

## Known open items — report if they bite, do not rediscover

These are documented in `docs/program/GATE_B1_CLOSURE.md` and `GATE_B2_CLOSURE.md`. Say whether each touches the journey; do not spend the session re-deriving them.

- `finding_observation.ungrounded_reason` has no CHECK constraint and, per the item above, is never written;
- `model_call.status` admits `succeeded|failed`; the analysis provenance emits a third value `truncated`;
- `blob_id` is content-derived **and** the primary key, so a blob moved to `rejected` permanently bans those bytes; the partial unique index scoped `WHERE state = 'available'` cannot do what its comment claims;
- `OD-03` records no machine-readable cost ceiling; a $1.00 stand-in is in place and is explicitly not the owner's decision;
- no query surface accepts cursor, limit, category or verdict filters though the contract declares all four;
- `display_title` is declared optional and nothing returns it.

## Gate — run these, report exact exit codes

- `.venv/bin/pytest tests/e2e/p02` and `tests/integration/p02_journey` each exit `0` against real services
- the full corpus journey completes and you report: run state, finding count, CSV row count, CSV byte size, and whether two exports are byte-identical
- the whole sequence repeated under the same idempotency keys adds **zero** rows to every table — report the counts before and after
- a restart preserves the migrated state, the published object, the run, the findings and the decisions
- `make foundation` still exits `0`
- `git diff --check` exits `0`

Bootstrap with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; bare `make bootstrap` is correctly refused under an active virtualenv. Your instance: `FOUNDATION_INSTANCE=gate-b3conv`, `POSTGRES_PORT=55480`, `S3_API_PORT=59090`, `S3_CONSOLE_PORT=59091`, `POSTGRES_DB=audit_conv3`, `S3_BUCKET=audit-conv3`. Copy `.env.example` to `.env` and set exactly these; it is git-ignored and is never committed.

There is no `ANTHROPIC_API_KEY` on this host. Every automated test runs on the recorded adapter. **Do not fabricate a live transcript**; if you cannot make a live call, say so plainly.

## Rules

1. **Commit after every meaningful step.** An earlier dispatch here was killed mid-run and lost four sessions entirely, because each held its work uncommitted.
2. **Report defects, never repair.** You certify the provider commits, not your own edits to them.
3. **Never add a root dependency.** `docs/program/P02_LOCK.json` is the pinned set, and it contains no HTTP framework by design.
4. `tests/contract` and `tests/checkpoint` as wholes are CP-00 historical evidence and are **red before you start** — roughly 194 failures at this base. They are not your gate and not your problem. Run only your own suites plus `make foundation`.
5. **Use a session-unique scratch directory.** Two sessions in an earlier wave had their mutation trees overwritten by a peer mid-run.
6. Do not measure anything while another session is running against the same services.

## Report

Changed paths. Every command with its exit code. The journey figures, reproduced independently. Each guard you mutated, what went red, and what went green on revert. Your verdict on the dead diagnostic path, with evidence. Your independent confirmation or refutation of the extractor divergence. Any defect found, described precisely and left unrepaired, naming the tree that owns it. And your elapsed wall-clock from start to last commit — this programme's forecast is rebuilt from measurement and yours is the next input.
