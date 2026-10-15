# Task W56A-MODEL-PIN-01 — verify two gateway identities and pin the selected model

## Outcome

The stand and a distinct recording gateway each pass a bounded explicit-model
identity/rate call and a default-model call. Only then the primary model's
verified, identical gateway name is added to `P02_LOCK.json`. A failed or
unavailable signal leaves the lock unchanged and PROVIDER blocked.

## Depends on

- `W56A-INT-SEAL-01` — complete on `origin/dev`;
- `W56A-INT-GENERATOR-01` — complete on `origin/dev`;
- `W56A-INT-MATCHER-CORE-01` — complete at `6de331c1`;
- `W56A-INT-PROBE-TOOL-01` — complete at `1a825fea`.
- `W56A-INT-PROBE-TOOL-CORR-01` — complete on the correction's published dev tip.
- `W56A-INT-PROBE-STUB-CORR-01` — complete on the namespaced-stub correction's published dev tip.

`W56A-PROBE-01` and `W56A-FREEZE-01` are stopped historical evidence, not
completed prerequisites. This task replaces neither report.

## Frozen inputs

- base: `origin/dev=d6d37e44061cbcc0fa96907e59bb4319c4a72a5c`;
  resolve the namespaced-stub correction tip before paid calls and recheck
  all frozen contract/lock bytes;
- API: 47 paths / 54 operations / 124 schemas, SHA-256
  `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256
  `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256
  `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head `0022_findings_v2`;
- provider lock SHA-256 before pin
  `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- locked primary `claude-opus-5`, input/output $5/$25 per million tokens;
  `cheaper_tier` remains unverified;
- `R-29`, `R-133`–`R-136`; `W56-PLAN.md` §A3.5;
  `reviews/W56A-SPEND.md` is the pre-call ledger.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the selected model has no verified gateway name and the earlier
  stand route returned a different model at a mismatched cost.

### P-01 — exact development base and lock

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && sha256sum docs/program/P02_LOCK.json`
- captured_output:
  ```text
  7fd152c0f1b2445cd1a5381cb9c3b579aa94f9e9
  7fd152c0f1b2445cd1a5381cb9c3b579aa94f9e9
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: the development tree matches the published ref and the
  lock is unchanged; this does not establish gateway identity.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/W56A-PROBE-01.md` (read-only failed result)
- addendum_path: not_applicable

That report requested `anthropic/claude-opus-5`, received
`meta/muse-spark-1.3-contributor` and reported $0.0000046 versus $0.00047
at the locked rate. It remains failed; this task measures a corrected route.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W56A-MODEL-PIN-01.md`;
- `docs/program/W56A-MODEL-PIN-01.md` (new report);
- `docs/program/reviews/W56A-SPEND.md`;
- `docs/program/P02_LOCK.json` — sole W56a writer, **only after both
  gateways pass**.

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies/lockfiles, composition roots,
  global styles, application and web code/tests, deployment configuration,
  credential files, `CURRENT_STATE.md`, `VERSION`, `origin/main` and tags;
- the stopped `W56A-PROBE-01` and `W56A-FREEZE-01` task/report files.

## Non-goals

- Gateway reconfiguration or a new exposure/security decision;
- proving the cheaper tier, producing recordings, activating proxy/v2,
  quality evaluation, manual acceptance, a full local gate or beta verdict.

## Deliverables

- A sanitized per-gateway report with route distinction, explicit and
  default response model, token counts, reported cost, calculated cost,
  tolerance and decision; no endpoint, credential, prompt or response body;
- updated spend ledger with pre-call projection, each actual/potential charge
  and remaining W56a ceiling;
- on two PASS results, one `models.primary.gateway_name` pin matching both
  reported names, without changing model IDs or rates;
- a precise PROVIDER grant after integration, or an explicit stop.

## Required tests

1. Before calls, verify the frozen hashes and migration head, ledger balance,
   distinct gateway roles/routes, selected model setting and credential
   presence without printing their values. Use the checked
   `tools.provider.identity_probe` from the published dev SHA. Each invocation
   uses synthetic text, at most 16 output tokens, fresh request/idempotency
   IDs, and the same chat-completions route the product adapter uses.
2. On each gateway, call the explicit locked primary. Require HTTP success,
   one answer, concrete response `model`, positive finite usage counts and
   `usage.cost`. Placeholder names such as `unknown` are not concrete. The
   response model must match the configured gateway name.
   Compare reported cost with
   `(input_tokens*5 + output_tokens*25)/1_000_000`; tolerance is the larger
   of 20% relative and $0.00002 absolute. Reject an unconfigured name, missing
   field or rate mismatch. If this fails, stop that gateway before default.
3. On each passing gateway, call the stub/default selection. Require a
   concrete response model distinct from the stub and selected name, plus
   usage and cost. An echo, refusal or missing signal fails the gateway.
4. Before every request, reproject total W56a spend against $5 and the
   $0.25 probe reserve. A timeout/unknown outcome counts as potentially
   charged and is never retried blindly.
5. On two PASS results only: JSON parse and lock-reader checks for the added
   field; `git diff --check`; exact changed-path proof; focused programme
   governance/prose checks. Do not run a full local gate.

## Integration contract

The two gateway roles must be demonstrably distinct yet report the same
selected gateway name. If names differ, the single-name lock schema is
insufficient and this task stops for a separately owned contract change.
`analysis/text/lock.py` remains the only runtime lock reader. A pin proves
only the selected primary; PROVIDER must refuse the cheaper tier until its
own budgeted identity/rate proof. A passing pin grants drafting and execution
of `W56A-PROVIDER-01` from a fresh dev base; it does not grant live recording.

## Failure/idempotency/security cases

- Never print, copy into Git, or relay private URL/token or response content.
  The host-owned credential is read in place and used only in memory.
- One mismatched identity, rate, default or gateway distinction is STOP, not
  fallback. A 200 response alone is insufficient.
- A call with uncertain billing is logged as potential spend and not repeated
  without a fresh projection. A repeated call uses a fresh ID and ledger row.

## Rollback / feature flag

Before two PASS results, revert this task/report/ledger candidate and leave
the lock untouched. After integration, reverting the pin restores the
recorded-only development state; no feature flag or database rollback exists.
Paid calls cannot be undone.

## Handoff

- changed files: only Allowed paths, as proved in the report;
- checks/results, new pin and spend: `docs/program/W56A-MODEL-PIN-01.md`;
- known limit: only the selected primary is verified;
- integrator: accept only both distinct PASS results, then issue the precise
  PROVIDER task on the read-back `origin/dev` SHA.
