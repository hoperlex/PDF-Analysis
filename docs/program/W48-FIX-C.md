# W48-FIX-C — completion report

## Result

**DONE.** The four refusals `W48-JUDGE-Z` found untested (F-8, F-9) each have a committed
regression that asserts the refusal's own reason and fails when the refusal is removed. No source
file changed; the judge had found the behaviour correct.

## Changed files

- `tests/integration/runs/test_durable_effect_boundaries.py` — four tests and three helpers
- `docs/program/W48-FIX-C.md`

`tests/integration/ingest/test_reconciliation.py` was granted and not needed: the Attempt-scoped
setup the refusals require lives in the run boundary tests.

## Tests

| Test | Finding | Refusal held |
| --- | --- | --- |
| `test_a_live_attempts_blob_is_refused_as_attempt_not_terminal_even_without_bytes` | F-8 | `reject_unpublished` → `attempt_not_terminal` |
| `test_a_fresh_terminal_publication_is_refused_as_publication_not_stale` | F-8 | `reject_unpublished` → `publication_not_stale`, then rejectable at threshold 0 |
| `test_the_sweep_leaves_a_live_attempts_provider_effect_alone` | F-9 | sweep's terminal Run/Job/Attempt conditions |
| `test_the_sweep_leaves_a_terminal_effect_younger_than_its_threshold` | F-9 | sweep's age condition, then settled at threshold 0 |

The existing tests asserted only `STATE_TRANSITION_NOT_ALLOWED`, which every refusal of
`reject_unpublished` shares, so a removed check was masked by the next one. The new tests read
`detail_fields["current_state"]`.

## Mutations (lane `gate-w48fixc`, ports 56530 / 60130–60131, base `28aab40`)

| Mutation | Result |
| --- | --- |
| remove `attempt_not_terminal` in `src/auditmanager/ingest/reconciliation.py` | red: `Failed: DID NOT RAISE DomainError` |
| remove `publication_not_stale` there | red: `Failed: DID NOT RAISE DomainError` |
| remove the three terminal-state conditions of `_SETTLE_TERMINAL_PROVIDER_EFFECTS` in `src/auditmanager/jobs/repository.py` | red: the live run's effect is in the settled set |
| remove the age condition there | red: the young effect is in the settled set |

Each mutation was restored with `git checkout --`; `git status --porcelain -- src` is empty.

## Checks

- `pytest tests/integration/runs/test_durable_effect_boundaries.py tests/integration/ingest/test_reconciliation.py`
  on the lane: **29 passed in 11.70s**
- `make foundation` on the lane: 35 passed
- the full gate is the integrator's, on the merged candidate

## Contracts

None changed.

## Risks and known limitations

None found. The sweep's three terminal conditions are held as one block, as the judge's grant
named them; a test per condition would need mixed Run/Job/Attempt states the executor cannot
produce without writing them directly.

## Forbidden-hotspot proof

`git diff --name-only 28aab40..HEAD` lists only the test file and this report.
