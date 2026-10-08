# Task W52-DEBT-CODE-131 — retry transient browser navigation

task_id: W52-DEBT-CODE-131

## Outcome

The PC-01 browser journey tolerates a short `net::ERR_NETWORK_CHANGED` event during
an initial GET navigation, while retaining a bounded refusal for persistent or
unrelated failures and never replaying form actions or API writes.

## Depends on

- `W52-INT-125-01` — published at
  `10013f8d8223e73abb6facb31204591d36d8cd5a`.

## Frozen inputs

- Exact base `10013f8d8223e73abb6facb31204591d36d8cd5a`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-131 in `docs/program/DEBT_REGISTER.md` records the 2026-10-06 transient failure.
- Owner direction 2026-10-08: basic tests and lint only; no temporary stand, QA or
  full gate (D-139/D-140).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `Page.goto` makes one navigation attempt and immediately throws on errorText.

### P-01 — exact base and browser navigation

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n 'async goto|Page.navigate|result.errorText|await page.goto\(url\)' tests/e2e/pc01/journey/cdp.mjs tests/e2e/pc01/journey/write.mjs tests/e2e/pc01/journey/journey.mjs`
- captured_output:
  ```text
  10013f8d8223e73abb6facb31204591d36d8cd5a
  tests/e2e/pc01/journey/journey.mjs:255:    await page.goto(url);
  tests/e2e/pc01/journey/write.mjs:123:        await page.goto(url);
  tests/e2e/pc01/journey/cdp.mjs:449:  async goto(url, { settleMs = 700, timeoutMs = SETTLE_TIMEOUT_MS } = {}) {
  tests/e2e/pc01/journey/cdp.mjs:454:    const result = await this.#send('Page.navigate', { url });
  tests/e2e/pc01/journey/cdp.mjs:455:    if (result.errorText) {
  tests/e2e/pc01/journey/cdp.mjs:457:      throw new Error(`navigation to ${url} failed: ${result.errorText}`);
  ```
- interpretation: a narrow retry can live at the GET navigation boundary;
  re-running a whole write step would risk replaying side effects.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/e2e/pc01/journey/cdp.mjs`
- `tests/e2e/pc01/journey/navigation-retry.mjs`
- `tests/e2e/pc01/journey/navigation-retry.test.mjs`
- `tests/e2e/pc01/journey/journey.mjs`
- `tests/e2e/pc01/journey/write.mjs`
- `tests/e2e/pc01/journey/README.md`
- `docs/program/W52-DEBT-CODE-131.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependency/lock files,
composition root and global styles.

## Non-goals

No retry of clicks, form submissions, API writes, all navigation failures,
browser acceptance run, temporary stand, QA, full gate, release, tag or
`origin/main` publication.

## Deliverables

- Retry `net::ERR_NETWORK_CHANGED` from `Page.navigate` with a small fixed budget
  and delays; preserve the final failure message when exhausted.
- Record the number of navigation attempts in the journey envelope and write-step
  record; surface retry attempts in the operator log.
- Basic tests for transient success, persistent failure and immediate refusal
  of other errors, plus lint and an executor report.

## Required tests

- Run the focused Node test, `node --check` on changed modules, frontend lint
  and `git diff --check`. No browser stand or full gate.

## Integration contract

Hand back a clean executor branch from the exact dispatch SHA with only allowed
paths. The integrator may publish to `origin/dev` after exact remote-ref and
fast-forward checks. Every route remains a cold browser; retries stay inside
the first navigation before actions.

## Failure/idempotency/security cases

Persistent `ERR_NETWORK_CHANGED` fails after the fixed budget. Any other
`errorText` fails on the first attempt. A rejected CDP command also propagates.
The page state is not silently reported as successful.

## Rollback / feature flag

Revert the code commit. No runtime feature flag; this is test-instrument behavior.

## Handoff

- changed files, commands/results, contracts, risks, integration notes and proof
  that forbidden hotspots were untouched.
