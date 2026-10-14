# Task W56A-RULE-01 — record the W56a owner decisions and align its check and review rules

task_id: W56A-RULE-01

## Outcome

The six W56a decisions already answered by the owner have numbered rulings. The W56a plan and
`AGENTS.md` describe the one-judge close and the final-gate-only database checks that the owner
ordered on 2026-10-14. `W56A-FREEZE-01` can cite stable ruling numbers after W55b closes.

## Depends on

- `W55B-RULE-01` — completed; W55b inputs and owner authority are recorded.
- `W55B-FIX` — completed and merged into the exact base below.

`GATE-PKG-01` is merged into the base; its acceptance gate is still part of W55b's close and
is therefore not claimed as a completed dependency.

`W55B-INT-CLOSE` remains a dependency of `W56A-FREEZE-01` and implementation lanes, not of
recording already-given owner answers. The owner's 2026-10-14 instruction to start available
next-wave work while W55b acceptance runs authorises this earlier document-only slot.

## Frozen inputs

- domain contract: `contracts/domain/v1/error-codes.json` SHA-256 `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16`.
- API contract: `contracts/api/v1/openapi.json` SHA-256 `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`.
- analysis contract: `contracts/analysis/v1/stage-registry.json` SHA-256 `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`.
- migration head: `0021_portal_bundles`.
- base commit: `8c5a109bd98302b64fb47b364d4c639ff63c0eda` (`integration/w55b` candidate, not its acceptance verdict).
- owner answers: `dispatch/ROADMAP-TO-BETA.md` §10.14 H-1…H-10; `OWNER_RULINGS_2026-09-17.md` R-124, R-126; `dispatch/W56-PLAN.md` §A4.

## Enumerator ownership

- enumerated_set_changed: yes (owner ruling numbers)
- enumerator_path: `docs/program/OWNER_RULINGS_2026-09-17.md`
- enumerator_owner: `W56A-RULE-01`
- totality_query: `rg -o 'R-[0-9]+' docs/program/OWNER_RULINGS_2026-09-17.md | sort -Vu | tail -12`, plus a scan for the selected numbers in the plan.

## Captured premise evidence

### P-01 — the base and last ruling
- captured_at: 2026-10-14
- command: `git rev-parse HEAD` and `git show 8c5a109bd98302b64fb47b364d4c639ff63c0eda:docs/program/OWNER_RULINGS_2026-09-17.md | rg -n '^## 3\.3[0-9]|^### .*R-128' | tail -3`
- captured_output:
  ```text
  8c5a109bd98302b64fb47b364d4c639ff63c0eda
  1544:## 3.33 — `R-121` to `R-123`, closing W55b (owner's direct poll, 2026-10-14)
  1557:## 3.34 — `R-124` to `R-127`, review and gate economy (owner's direct polls, 2026-10-14)
  1571:### `R-128` — the gate package rides W55b's one full gate (owner, 2026-10-14)
  ```
- interpretation: R-129 is the next free number on this base. A later W55b acceptance ruling
  requires renumbering before integration; this task does not reserve numbers on other branches.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `AGENTS.md` §8 only
- `docs/program/OWNER_RULINGS_2026-09-17.md` (append W56a rulings only)
- `docs/program/dispatch/W56-PLAN.md` (the ruling placeholders and R-124/R-126 check/review amendments only)
- `docs/program/tasks/W56A-RULE-01.md`
- `docs/program/W56A-RULE-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependency/lock files, composition roots, global styles
- `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `PORT_REGISTRY.md`, any W55b worktree or publication ref
- code, fixtures, release notes, tags and the deployed stand

## Non-goals

- W56a freeze, seal or implementation; running a paid model probe; deciding unanswered owner questions.
- W55b acceptance or publication.

## Deliverables

- Six numbered rulings replacing R-Z1…R-Z6, the §8 check amendment, a W56a plan amendment,
  and `docs/program/W56A-RULE-01.md` with the six-item handoff.

## Required tests

- command: `git diff --check`
- expected: exit 0.
- command: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: exit 0 when the base's Python environment is available; otherwise record the precise environment blocker.
- command: `rg -n 'R-Z[1-6]|W56A-QA-01|W56A-JUDGE-[XY]|W56A-NOTES-JUDGE' docs/program/dispatch/W56-PLAN.md`
- expected: no live W56a scheduling reference remains.

## Integration contract

This branch records existing owner decisions and changes no contract or runtime byte. The
integrator rebases it after W55b closes, verifies the ruling numbers are still free, then uses
its rulings as inputs to `W56A-FREEZE-01`. No W56a implementation lane is dispatched from this
candidate before that freeze.

## Failure/idempotency/security cases

- If W55b adds a ruling at R-129 or later, renumber this branch and all its W56a references
  before merge. Never silently overwrite or duplicate a ruling number.
- No credential, corpus text, portal export or paid call is required.

## Rollback / feature flag

Revert the document commit before `W56A-FREEZE-01`; no data or runtime rollback is needed.

## Handoff

- changed files: see Allowed paths.
- commands/results: report §2.
- known limits: W55b close and W56a freeze remain pending.
- integration notes: report §4.
