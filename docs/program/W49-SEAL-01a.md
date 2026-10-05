# W49-SEAL-01 — STOPPED before implementation (stop report, part a)

**Task:** `docs/program/tasks/W49-SEAL-01.md` (as amended at `7912504`).
**Base:** `7912504` (`integration/w49`). **Branch:** `agent/w49-seal-01`.
**Lane:** `FOUNDATION_INSTANCE=gate-w49seal`, Postgres `56570`, S3 `60170`/`60171`, database
`auditmanager_w49seal`, bucket `auditmanager-w49seal` (`PORT_REGISTRY.md` row for
`W49-SEAL-01`); the three ports had no listener (`ss -ltn`) before `make foundation`.

**Status: stopped on the plan's stop conditions before any code or contract change.** The
slot cannot reach a green gate inside its `allowed_paths`: adding `rate_limited`, adding the
fourteen operations and applying the §3.2 registers each make tests red whose repair lies in
files the task file does not grant, and three of them also need a decision the plan does not
take. Per `EXECUTOR-PROMPT.md` and `W49-PLAN.md` §7 this report records what was measured and
asks; nothing was widened. The only commit on the branch is this report.

## 1. Premise re-measured at `7912504`

| Fact | Command | Result |
| --- | --- | --- |
| surface triple | the task file's P-01 one-liner over `contracts/api/v1/openapi.json` | `17 20 61` |
| contract SHA-256 | `sha256sum contracts/api/v1/openapi.json web/openapi/openapi.json` | both `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585` |
| error catalog | `len(codes)` of `contracts/domain/v1/error-codes.json` | `22`, `candidate_revision` 8 |
| identities | `len(identifiers)` of `contracts/domain/v1/identifiers.json` | `27`, `candidate_revision` 8 |
| state machines | keys of `state-machines.json` `machines` | `import, blob, audit_run, job, attempt, command_idempotency` |
| lane head | `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini current` | `0015_accounts_roles_registration (head)` |
| contract battery | `.venv/bin/python -m pytest tests/contract -q -p no:cacheprovider --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | `440 passed, 49 subtests passed in 11.70s`, exit 0 |

Note: the bare `pytest tests/contract -q` the task names fails **at the base** on
`tests/contract/test_cp00_candidate.py::ACandidateIntegrityTests::test_the_reviewed_delta_is_exactly_what_is_declared`
(first failure under `-x`); `make gate` and `OPERATING_CONSTRAINTS.md` §7 exclude that file and
its two siblings, so the canonical form above is the one this lane would report.

## 2. How the findings were measured

Read-only sweeps of the worktree, plus one disposable probe tree that is not a worktree and
not a ref of this repository: `git archive 7912504` extracted to
`/root/w49seal-788b07cb-probe` (its own throwaway `git init`, `.venv` and `web/node_modules`
symlinked from the lane). Every mutation below was made **only in the probe**; the worktree
is unchanged apart from this file. The probe's Python runs used
`-o pythonpath=/root/w49seal-788b07cb-probe/src`, and the tracebacks name files under the
probe, which proves the probe's code was the code imported. The probe was deleted after the
measurements.

## 3. Findings — reds whose repair is outside `allowed_paths`

### F1 — the error kernel refuses to import with a 23rd catalog code

Probe step: `rate_limited` added to `error-codes.json` only, then
`PYTHONPATH=src .venv/bin/python -c "import auditmanager.shared.errors"`:

```text
  File "/root/w49seal-788b07cb-probe/src/auditmanager/shared/errors/codes.py", line 80, in <module>
    raise RuntimeError(
RuntimeError: auditmanager.shared.errors.codes is out of step with contracts/domain/v1/error-codes.json: missing=['rate_limited'] extra=[]
```

`src/auditmanager/shared/errors/codes.py` is an import-time guard that the `ErrorCode` enum
equals the catalog. Without a `RATE_LIMITED` member nothing that imports the error kernel
loads — the whole backend battery. The file is not granted. A code therefore lives in **five**
places, not the four `IDENTITY-WAVES.md` §5 and `W49-PLAN.md` §3.4 name.

### F2 — the frontend has two more exhaustive maps over `ErrorCode`

Probe step: F1's code also added to `codes.py`, to `components.schemas.ErrorCode.enum` and
to the envelope schema's enum, then `npm --prefix web run api:generate` (exit 0) and
`npm --prefix web run typecheck`:

```text
tsc exit=2
src/entities/audit-run/model/terminal-reason.ts(63,7): error TS2741: Property 'rate_limited' is missing in type '{ ... }' but required in type 'Readonly<Record<... | "rate_limited", string>>'.
src/shared/api/catalog-message.ts(70,7): error TS2741: Property 'rate_limited' is missing ...
tests/unit/screens/run-terminal-reason.test.ts(55,7): error TS2741: Property 'rate_limited' is missing ...
```

`catalog-message.ts` is granted (its one sentence); `terminal-reason.ts` and
`run-terminal-reason.test.ts` are not. With a probe sentence added to `catalog-message.ts`,
`npx --no-install vitest run tests/unit/api/failure-surface.test.ts tests/unit/screens/run-terminal-reason.test.ts tests/unit/run/terminal-reason.test.ts tests/contract`
(from `web/`) → `Test Files 5 failed | 5 passed (10)`, `Tests 8 failed | 157 passed (165)`.
The reds that the grant cannot repair:

```text
FAIL tests/unit/api/failure-surface.test.ts > a code outside the catalog is not a catalog code > is asked about a catalog the contract actually declares
FAIL tests/unit/screens/run-terminal-reason.test.ts > every catalog reason reaches the screen as a sentence > renders a sentence for rate_limited, beside the code
FAIL tests/contract/terminal-reason-sentences.contract.test.ts > ... > describes every code the catalog declares        (needs terminal-reason.ts)
FAIL tests/contract/terminal-reason-sentences.contract.test.ts > ... > gives no catalog code the undescribed default   (needs terminal-reason.ts)
```

`web/tests/unit/api/failure-surface.test.ts:78` is the registered pin
`error-frontend-failure-enum-count` (`toHaveLength(22)`); the registry lists it, the grant
does not.

### F3 — migration `0002`'s error vocabulary versus the catalog (a decision)

Same probe, `tests/contract` battery (canonical ignores): among the expected in-grant reds,
`tests/contract/domain_p02/test_contract_vocabulary.py::test_error_code_domain_equals_the_frozen_catalog`
fails because it asserts `set(migration 0002 ERROR_CODES) == set(catalog codes)`. Migration
`0002` (and `0014`, which restates the tuple) builds CHECK constraints on stored
`error_code`/`terminal_reason` columns from that tuple. The test file is granted, the
migrations are not and must not move. Either the rule changes (the stored vocabulary may be
narrower than the catalog by an explicit edge-only set `{rate_limited}`, which no column
ever stores), or a migration widens the CHECKs (the head is not this slot's). That is a
decision the plan did not take.

### F4 — count prose outside the grant

Probe step: F1–F2 plus fourteen stub operations at the ten §3.4 paths (the probe document
measured `27 34 61`), then `test_surface_counts_in_prose.py::test_the_api_prose_states_the_surface_this_document_declares`
and `::test_p02_seam_makes_a_current_claim_the_guard_reads` → `2 failed`. The ungranted lines:

```text
docs/program/P02_SEAMS.md: 'Twenty operations' states 20 for operations, expected 34
infra/deploy/README.md: 'twenty operations' states 20 for operations, expected 34   (three times)
infra/deploy/proxy/nginx.conf: 'seventeen paths' states 17 for paths, expected 27
infra/deploy/proxy/nginx.conf: 'twenty operations' states 20 for operations, expected 34
infra/deploy/serve.py: 'twenty operations' states 20 for operations, expected 34
src/auditmanager/shared/errors/codes.py: 'twenty-two codes' states 22 for codes, expected 23
web/src/shared/api/errors.ts: 'twenty-two-code' states 22 for codes, expected 23
web/src/shared/api/catalog-message.ts: '22 codes' states 22 for codes, expected 23   (granted: its rate_limited sentence only)
web/src/shared/api/catalog-message.ts: '22-code' states 22 for codes, expected 23    (granted: its rate_limited sentence only)
```

and `test_p02_seam_makes_a_current_claim_the_guard_reads` requires `P02_SEAMS.md` to state the
**current** operation count. Every other red line of that run lies in granted files
(`contracts/api/v1/openapi.json` info, `src/auditmanager/api/**`, the two one-line `web/src`
comments). The real schema count will also move the `61 schema(s)` phrases in `app.py` and
`declarations.py`, both granted.

### F5 — the suites' own accounts become incomplete, roleless accounts under §3.2

`tests/support/accounts.py` (`provisioned_record` → `UserRepository.create_user`) writes a
legacy login with `profile_completed_at` NULL and no role row. Measured on the lane, unmodified
worktree:

```text
$ PYTHONPATH=src .venv/bin/python <load tests/support/accounts.py; provisioned_record('pc01-acceptance'); AccountRepository().account_standing(...)>
login= pc01-acceptance display_label= pc01-acceptance
AccountStanding(token_epoch=1, is_default_credential=False, archived=False, profile_complete=False, roles=frozenset())
```

Under §3.2's order (incomplete profile → `permission_denied`, `required_capability:
profile_completed`, on everything but `getMe`, `updateMyProfile`, `changePassword`; then
`{expert}` for product mutations) every product call these suites make is refused. Callers
outside the grant (`git grep -n provisioned_credential -- tests`):

- `tests/support/accounts.py` (the helper itself)
- `tests/e2e/pc01/driver.py` (`pc01-acceptance`; the grant covers only the route-count line of `test_acceptance.py`)
- `tests/characterization/w13_baseline/journey.py` (`w13-baseline`), whose records
  `10-appendDecision.success.json` and `11-listDecisionHistory.success.json` pin
  `"author_label": "w13-baseline"` byte for byte — a complete profile changes that value to
  the name form, so the records need a re-capture with a recorded `permitted_change`
- `tests/integration/ingest/test_size_guard_boundary.py` (`size-guard-suite`)
- `tests/integration/p02_journey/test_truncated_end_to_end.py` (`p02-truncated-suite`)
- `tests/integration/p02_journey/test_query_surface_over_the_corpus.py` (`p02-query-suite`;
  granted for one ledger keyword per call only)

The four composition suites that use the helper are granted. `W49-PLAN.md` §4 `01c` names
only `tests/integration/api/driver.py`, `test_authorization.py`, `test_decision_authorship.py`
and `test_the_reviewer_name_is_visible.py`.

### F6 — the frontend pins the open set to one operation

`web/tests/unit/api/authorization-state.test.ts:235-251` (not granted) asserts every
generated operation declares `401`, and that the operations without a `403` are exactly
`['issueToken']`. `submitRegistration` and `readRegistrationStatus` are unauthenticated
(`security: []`); by the rule the contract applies to `issueToken` they have no subject to
deny and declare no `403`, and `submitRegistration` has no credential to refuse, so it
declares no `401` either. Either way this test goes red. Whether the two new open operations
declare `401`/`403` is itself a contract-shape question (Q3 below).

## 4. In-grant pins found beyond the plan's list (seen, not blockers)

`tests/contract/shared_kernel/test_error_kernel.py::TheEnumIsExactlyTheCatalog::test_there_are_twenty_two`;
`tests/integration/api/test_envelope_screen_rules.py:195` (`len(raw["codes"]) == 22`);
`tests/contract/domain_p02/test_contract_vocabulary.py:23` (`== 22`, see F3);
`_TS_ERROR_COUNT_ASSERTION` in `test_doc_prose_facts.py` matches only `toHaveLength(17|20|22|61)`,
so its value set must move with the counts or the inventory stops seeing the moved pins;
the served `ErrorCode` enum is a literal in `src/auditmanager/api/schemas/models.py`
(`test_openapi_conformance_live.py` red in the probe until it moves). The live sentence of
`CURRENT_STATE.md` (line 65) carries the catalog count (22), the revision (8) and the identity
count (27) beside the triple; the grant names "the live surface-triple sentence".

## 5. Questions for the integrator (one batch)

1. **Grant amendment for F1, F2, F4, F6** — the exact lines: `src/auditmanager/shared/errors/codes.py`
   (the `RATE_LIMITED` member and the docstring count); `web/src/entities/audit-run/model/terminal-reason.ts`
   (the `rate_limited` sentence); `web/tests/unit/screens/run-terminal-reason.test.ts` (its
   `MUST_SAY.rate_limited` phrase); `web/tests/unit/api/failure-surface.test.ts` (the length
   literal); `web/src/shared/api/errors.ts` and the two count phrases of `catalog-message.ts`;
   the count phrases of `docs/program/P02_SEAMS.md`, `infra/deploy/README.md`,
   `infra/deploy/serve.py` and `infra/deploy/proxy/nginx.conf` (nginx is `W49-EDGE-01`'s
   afterwards; the stages are sequential, so there is no parallel writer);
   `web/tests/unit/api/authorization-state.test.ts` (the open-set assertion). Granted or not?
2. **F3:** does the stored error vocabulary admit an explicit edge-only set
   (`{rate_limited}`, never stored) — the vocabulary test changes, no migration — or does a
   migration widen the CHECKs? The first keeps the head where ACCESS left it.
3. **F6 / contract shape:** confirm that `submitRegistration` declares neither `401` nor
   `403`, and `readRegistrationStatus` declares `401` (its generic refusal) but not `403` — the
   same reasoning `issueToken` carries.
4. **F5:** how do the suites get a complete account with `expert`? Option (a): the shared
   helper `tests/support/accounts.py` provisions every suite account complete (an e-mail login
   derived from the suite label, fixed names, role `expert`), the five ungranted callers keep
   their labels unchanged, and the W13 characterization records 10 and 11 are re-captured
   because `author_label` becomes the name form (a recorded `permitted_change`). Option (b):
   each suite changes on its own. Either needs paths outside the grant, and (a) also needs
   the characterization re-capture granted.
5. `CURRENT_STATE.md` line 65: may the seal move the catalog count, the revision and the
   identity count in the same sentence as the triple?
6. The task file's Handoff names `docs/program/W49-SEAL-01.md`, which is not in
   `allowed_paths`; the three reports `01a/b/c` are. Is the list of changed files to live in
   `01c`?

## 6. AGENTS.md §5 items

1. **Changed files:** `docs/program/W49-SEAL-01a.md` (this report) only.
2. **Checks:** §1's baseline (`440 passed`), §3's probe measurements; nothing else ran on the
   worktree.
3. **Contracts:** none changed.
4. **Risks/limitations:** none introduced; the probe tree was disposable and removed.
5. **Integrator:** answer §5; on an amended task file the slot resumes from this branch.
6. **Forbidden hotspots:** `git diff --name-only 7912504..HEAD` lists this report only; no
   contract, source, test, lock, ref, tag or push.
