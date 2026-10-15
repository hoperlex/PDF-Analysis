# Task W56A-PROBE-01 — verify model identity at the W56a gateways

task_id: W56A-PROBE-01

## Outcome

Record bounded, source-backed model identity and price evidence for each distinct W56a
gateway before `W56A-FREEZE-01` grants implementation. A gateway is accepted only when
its explicitly selected model and its default both answer with concrete identities and
the selected model's reported cost agrees with the locked rate.

## Depends on

- `W55B-INT-CLOSE` — complete on `origin/dev` `6d63802a`.
- `W56A-RULE-01` — complete on local `integration/w56a`; `R-133` and `R-134` govern this probe.
- `W56A-PLAN-PATH-FIX-01` — complete on local `integration/w56a`.

## Frozen inputs

- base: local `integration/w56a` `7bf6a816` before this task's documents.
- API 47 paths / 54 operations / 123 schemas; domain revision 12; 24 error codes.
- migration head `0021_portal_bundles`; provider lock SHA-256
  `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.
- `docs/program/dispatch/W56-PLAN.md` §A3.5 and §A3.8; owner spend ceiling $5
  under `R-29`/`R-134`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the stand has a configured gateway URL and token, while the local recording
  gateway is absent; the stand's current model setting is a stub.

### P-01 — sanitized gateway shape before the paid call

- captured_at: 2026-10-15
- command: `ssh <owner-host> 'python3 - <sanitized provider.env shape check>'`
- captured_output:
  ```text
  provider.env present
  PROXY_LLM_BASE_URL valid_host https path
  PROXY_LLM_TOKEN set
  PROXY_LLM_MODEL stub
  AUDITMANAGER_PROVIDER_MODE proxy
  ```
- interpretation: one stand gateway can be probed without copying its secret; this
  does not establish the requested model identity or a second gateway.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-PROBE-01.md`
- `docs/program/W56A-PROBE-01.md`
- `docs/program/reviews/W56A-SPEND.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and lockfiles, composition
  roots, global styles, product code and tests, provider credential files, release
  notes, `VERSION`, refs, tags and deployed application state.

## Non-goals

- Changing gateway or deployment configuration; a product run; model quality evaluation;
  storing prompts or tokens in Git; publishing `origin/main`; completing freeze without
  both distinct gateway results.

## Deliverables

- One spend ledger with a pre-call projection, one bounded result per call and total.
- A report showing each gateway's configured/default response identity and rate check,
  or an explicit stop if a gateway is absent or a signal fails.

## Required tests

- `git diff --check`: exit 0.
- Contract/governance prose checks for these documents: exit 0.
- For each gateway: two tiny synthetic chat-completions requests, maximum 16 output
  tokens each, one explicit locked model and one default/stub; verify response `model`,
  `usage.prompt_tokens`, `usage.completion_tokens`, `usage.cost` and the selected model's
  expected rate. Stop on missing or non-finite fields, mismatch, fallback, or projected
  total spend above $5.

## Integration contract

`W56A-FREEZE-01` may consume a gateway's PASS only from this report with both calls
and recorded cost. One gateway's PASS does not grant SEAL. The freeze owns final model
names and tolerance; this task does not edit `P02_LOCK.json`.

## Failure/idempotency/security cases

- Keep the token and endpoint on the host where the owner placed them; never print or
  copy either into this repository or the transcript. Record only gateway role,
  response model, counts, cost and a bounded classifier.
- Use unique request IDs. A repeated call is new spend and needs an updated projection.
- A timeout/unknown outcome is recorded as potentially charged and is not blindly retried.

## Rollback / feature flag

This is read-only against the application and changes only three documents. Revert
those files to discard the evidence; paid calls cannot be undone. No feature flag.

## Handoff

- Changed files: the three allowed documents only.
- Commands/results and limitations: `docs/program/W56A-PROBE-01.md`.
- Integration: freeze remains stopped until both distinct gateways pass.
