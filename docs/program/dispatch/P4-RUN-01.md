# `P4-RUN-01` dispatch prompt — the PC-02 baseline run

Base `554e4d25d14bc05bb681449cecbcb4257c764257`. One session, independent. Dispatch text below,
verbatim.

---

You are session `P4-RUN-01` for the PDF-Analysis prototype: the PC-02 baseline run. Repository: /root/projects/PDF-Analysis.

BASE COMMIT: `554e4d25d14bc05bb681449cecbcb4257c764257` on `planning/prototype-roadmap`. Branch `agent/p4-run-01`.

**Check your worktree's HEAD before anything else.** Every dispatched session here arrived on `43a84d9`, ~300 commits behind. Verify the SHA exists and branch from it literally.

**Your working tree must not be under `/tmp`.** Docker here is a snap package that cannot see it and `make up` fails with a `/var/lib/snapd/void/...` error. Use `/root/p4run-scratch` for scratch.

## Why this task exists — it was missing from the graph

`P4-BHV-01` books domain experts to label **findings**. It depends on the corpus and the tooling, and it assumes the findings already exist. Nothing in the P04 graph produces them. That gap was found while reviewing the wave, before experts were booked rather than after.

So your job is the prerequisite, and it happens to be the more interesting measurement of the two.

## What you are measuring

PC-01 was accepted on 2026-09-14 on the strength of a live run over **one** eight-page document: three seeded issues found, none of six controls flagged. That is n=1, and a corpus built to be findable.

`P4-QA-01` built a harder corpus: 14 measurable documents carrying **9 seeded issues** and **64 control statements** across 12 archetypes, deliberately sharing no attribute with the PC-01 corpus, because a corpus reverse-engineered from findings the prompt already produces measures the prompt rather than the model. One seed is categorical rather than numeric; one placeholder carries no placeholder word at all.

**Your run is the first test of whether the PC-01 result generalises.** Report what happens. A poor result is a result — `PROTOTYPE_PROFILE.md` risk 1 names "grounded but professionally useless" in advance, and a low recall on a harder corpus redirects P04 rather than failing it.

## The rule that matters most

**Do not tune anything in response to what you see.** Not the prompt, not the profile, not the thresholds, not the matching rules. If recall is poor, that is the measurement. A prompt adjusted after seeing the corpus measures the adjustment, and every number after it is uncitable.

If you believe a change would help, **write it in your report as a recommendation** and leave the code alone. `src/**` is not yours.

## You own exactly these paths

- `artifacts/validation/PC-02/baseline/**`
- `docs/program/tasks/P4-RUN-01.md` — create it from `docs/templates/TASK_TEMPLATE.md`

Nothing else. Not `src/**`, not `fixtures/**`, not `tools/**`, not `contracts/**`, not `tests/**`, not the `Makefile`, not root locks.

## What to do

1. **Run the live pipeline over all 14 measurable documents**, one run each, through the composed application's router — `auditmanager.api.app.create_app()` and the `Router` it returns. Do not import modules directly to make a step work.

2. **Confirm the 4 negative-envelope documents are refused**, each by the rule its manifest entry names.

3. **Match findings to ground truth mechanically**, by the rule `docs/program/validation/PC-02_PROTOCOL.md` defines. Findings cannot be matched by `finding_uid` across runs — PC-01 allocates fresh ones and implements no cross-run matching — so matching is by content.

4. **Report three groups, and the third is the important one:** findings matching a seeded issue, findings matching a declared control statement, and **findings matching neither**. That third group is where the corpus's blind spot becomes visible instead of being averaged away. Do not discard it and do not call it noise.

5. **Verify grounding independently.** Every published quotation must exist at its declared page and offset. The corpus's own extractor and `pdfplumber` both work; using one that shares no code with the other is the point.

6. **Emit the baseline artifact** under `artifacts/validation/PC-02/baseline/` — per document and in aggregate: run id, state, stage statuses, findings with their match classification, measured cost and latency. This is what `P4-BHV-01` hands to experts and what `P4-INT-01` reports from, so its shape is frozen by your acceptance.

## Configuration, cost and honesty

```bash
set -a; . ./.env; . ./.env.provider; set +a
```

`OD-02` was revised to an operated LLM proxy; `AUDITMANAGER_PROVIDER_MODE=proxy` and the model is pinned explicitly to `anthropic/claude-opus-5`, because the proxy's own default is a small fast model and the prompt was written against Opus.

`tests/conftest.py` strips every provider-selecting variable for the whole test session so nothing makes a paid call by accident. Your run is not a test; set the variables explicitly and visibly.

**Cost.** `OD-03` sets USD 1.00 per run and the proxy reports the **measured** cost of each call, now recorded in `model_call.cost_basis` as `measured` rather than derived. One eight-page run costs roughly USD 0.04, so 14 documents is well under a dollar in total. **Report the total measured spend and the per-document figures.** If a run halts on the ceiling, that is a finding, not a failure to work around.

**Never fabricate a result.** If a run fails, report the failure, its cost and its error code. A previous session here declined to invent a transcript and said so plainly; that is the standard.

## Anti-vacuity

**Ten tests in this programme have passed or failed without exercising what they named**, always the same shape: asserting a property of the fixture rather than of the code. A measurement harness is exactly where that bites — a matcher that matches nothing reports perfect precision.

So: **prove your matcher can fail.** Feed it a finding you know matches a seeded issue and confirm it matches; feed it one you know does not and confirm it does not; and confirm that an empty finding set does **not** report success. Report all three.

Two traps that have cost sessions here: `pyproject.toml` sets `pythonpath = ["src"]` and overrides an exported `PYTHONPATH`; and `.venv` exists only in the main checkout, so say which interpreter you used.

## Gate — report exact exit codes

- all 14 measurable documents run to a terminal state; report the state of each
- all 4 negative documents refused by their own rule
- every published quotation verified present at its declared page and offset — report the count and any that failed
- `make foundation` still exits 0
- `git diff --check` exits 0
- `git diff --name-only 554e4d2..HEAD` lists only your owned paths

Bootstrap with `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`. Your instance: `FOUNDATION_INSTANCE=p4run`, `POSTGRES_PORT=55510`, `S3_API_PORT=59120`, `S3_CONSOLE_PORT=59121`, `POSTGRES_DB=audit_p4run`, `S3_BUCKET=audit-p4run`.

`tests/contract` and `tests/checkpoint` as wholes are CP-00 historical evidence, red before you start, and are not your gate.

## Rules

**Commit after every meaningful step** — a dispatch here was killed mid-run and lost four sessions because each held work uncommitted. **Report defects, never repair.** **Never add a dependency.**

## Report

Changed paths. Every command with its exit code and which interpreter.

**Recall:** how many of the 9 seeded issues were found, which, and which were missed — with the missed ones quoted, because *what* the model misses is more useful to P05 than how many.

**Precision:** how many of the 64 control statements were flagged, and which. A control that was flagged is the most informative single line in your report.

**The third group:** findings matching neither, quoted in full, with your judgement on whether each looks like a real issue the corpus failed to declare or a false positive of a kind the controls do not cover.

**Grounding:** the verified-quotation count and any failure.

**Cost:** total measured spend, per-document figures, and whether any run approached the ceiling.

**Your matcher's three proofs.** Any defect found, left unrepaired, naming the owning tree. And your elapsed wall-clock.
