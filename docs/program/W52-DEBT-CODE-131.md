# W52-DEBT-CODE-131 — bounded browser navigation retry

## Result

The PC-01 CDP page retries only a `Page.navigate` response with
`net::ERR_NETWORK_CHANGED`. The fixed waits are 1, 3 and 6 seconds, for at most
four GET attempts. Other navigation errors and rejected CDP commands propagate
immediately. Write actions and API requests are outside this retry boundary.

Successful route and write-step records carry `navigationAttempts`; a failed
write-step record also retains the count if CDP returned a navigation result.
Each retry is printed in the operator log. Every route still uses its own cold
browser profile.

## Changed files

- `tests/e2e/pc01/journey/navigation-retry.mjs` — bounded retry helper.
- `tests/e2e/pc01/journey/navigation-retry.test.mjs` — four focused cases.
- `tests/e2e/pc01/journey/cdp.mjs` — use the helper at `Page.goto`.
- `tests/e2e/pc01/journey/journey.mjs`, `write.mjs` — record attempt counts.
- `tests/e2e/pc01/journey/README.md` — instrument behavior.
- `docs/program/W52-DEBT-CODE-131.md` — this handoff.

## Checks

- `node tests/e2e/pc01/journey/navigation-retry.test.mjs` — 4 passed.
- `node --check` on all changed `.mjs` files — passed.
- `npm run lint` in the integration worktree's `web` directory — passed.
- `git diff --check` — passed.

No browser stand, QA or full gate was run. Those remain D-139/D-140. The
specific host-network failure cannot be reproduced by the local pure test; the
test covers the CDP result sequence and retry budget.

## Contracts and integrator handoff

No wire, domain or migration contract changed. The only new emitted evidence is
`navigationAttempts` in the test instrument's record. Merge this clean executor
branch from its exact dispatch SHA; publish only to `origin/dev` after exact
remote-ref and fast-forward checks. Narrow D-131 to deferred live validation.
Rollback is one code-commit revert; no feature flag is needed.

Only task-allowed paths changed. Contracts, migration head, root dependencies,
composition root and global styles are untouched.
