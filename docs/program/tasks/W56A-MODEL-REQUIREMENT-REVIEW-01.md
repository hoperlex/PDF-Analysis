# Task W56A-MODEL-REQUIREMENT-REVIEW-01 — review the model gate separately

task_id: W56A-MODEL-REQUIREMENT-REVIEW-01

## Outcome

Give the owner a decision-ready review of whether W56a's two-gateway identity
probe must precede SEAL, while preserving the failed probe and the existing
rule for live responses. This task makes no implementation grant.

## Depends on

- `W55B-INT-CLOSE` — complete on `origin/dev` at `6d63802a`.
- `W56A-RULE-01` — complete on this integration line.
- `W56A-PLAN-PATH-FIX-01` — complete on this integration line.

`W56A-PROBE-01` and the stopped `W56A-FREEZE-01` are evidence read by this
review, not prerequisites that this task claims to complete successfully.

## Frozen inputs

- base commit: `ac03e8fa1f5a62d45021234d74c4f177edfda381` on `integration/w56a`.
- domain contract revision 12; API 47 paths / 54 operations / 123 schemas;
  analysis contract unchanged; 24 domain error codes.
- migration head `0021_portal_bundles`; proposed W56a migration `0022_findings_v2`.
- `R-133`, `R-134`, `docs/program/dispatch/W56-PLAN.md` §§A3.5, A4, A5, A7;
  `docs/program/W56A-PROBE-01.md` and `docs/program/W56A-FREEZE-01.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the owner asked to review the W56a requirement separately after the
  stand's explicitly selected model returned a different identity.

### P-01 — binding language and recorded stop

- captured_at: 2026-10-15
- command: `rg -n 'Status: STOPPED|A3.5 Model identity|A live response that reports a model' docs/program/OWNER_RULINGS_2026-09-17.md docs/program/dispatch/W56-PLAN.md docs/program/W56A-PROBE-01.md`
- captured_output:
  ```text
  docs/program/W56A-PROBE-01.md:3:**Status: STOPPED after the first call.** Base `integration/w56a` `7bf6a816`;
  docs/program/dispatch/W56-PLAN.md:147:**A3.5 Model identity and provider errors (H-6).**
  docs/program/OWNER_RULINGS_2026-09-17.md:1592:| `R-133` | H-6 | A live response that reports a model other than the configured and pinned one is a typed stage failure; no finding is published from it and no silent substitution is allowed. Live recordings follow a successful identity probe. |
  ```
- interpretation: `R-133` binds live recordings to a successful identity probe;
  the plan places that probe in the earlier freeze. The probe report documents
  an actual failure; the owner request starts a review, not an override.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The stopped freeze and failed probe remain unchanged as historical evidence.
Any approved revision must use a new owner ruling and a separate freeze task.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-MODEL-REQUIREMENT-REVIEW-01.md`
- `docs/program/reviews/W56A-MODEL-REQUIREMENT-REVIEW-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, application code, tests, fixtures,
  `P02_LOCK.json`, root dependencies and lockfiles, composition roots, global
  styles, deployment environment and credentials.
- `OWNER_RULINGS_*.md`, wave plans, prior task and review records, refs and tags.

## Non-goals

- Ratifying a new rule, granting SEAL or another lane, accepting the stand's
  fallback model, making a live call, changing deployment or publishing a ref.

## Deliverables

- This task definition and a separate review with options, recommended owner
  decision, exact implementation boundary, contract owner and verification gate.

## Required tests

- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program/test_wave_governance.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`
- expected: exit 0.
- command: `git diff --check ac03e8fa..HEAD && git diff --name-only ac03e8fa..HEAD`
- expected: exit 0 and exactly the two allowed documents.

## Integration contract

The owner can select an option from the review. Until an explicit selection is
recorded and the plan is amended, `W56A-FREEZE-01` remains STOPPED and no W56a
implementation lane is dispatchable.

## Failure/idempotency/security cases

- Do not turn the observed wrong-model response into a lock pin or a quality
  baseline. No gateway URL, token, prompt or response body is copied here.
- A future retry is a separately projected paid call under the $5 ledger.

## Rollback / feature flag

Revert the two review documents to discard the proposal. No runtime change or
feature flag is involved.

## Handoff

- changed files: the two Allowed paths only.
- commands/results: review §Checks.
- known limits: owner decision, gateway routing and a second gateway remain open.
- integration notes: do not grant code from this review alone.
