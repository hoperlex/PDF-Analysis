# Task W49-FIX — the release-blocking findings of Stage E, two owner rulings, and one stale seam sentence

## Outcome

`contracts/domain/v1/identifiers.json` validates against its own schema inside `make gate`, the
deployed proxy serves the configuration of the checkout it was deployed from, and
`infra/deploy/verify-deployed.sh` refuses a deployment whose proxy does not. An archived account
cannot be changed until it is restored (`R-62`), and a pending applicant's sign-in costs one
attempt, not two (`R-63`). Release acceptance passes a run whose `provider_mode` is `live` or
`proxy` and never `recorded` (`R-65`).

## Depends on

- `W49-QA-01`, `W49-JUDGE-X`, `W49-JUDGE-Y` merged into `integration/w49` (this task file's
  commit is the base)

## Frozen inputs

- API contract: 34 operations / 77 schemas as sealed by `W49-SEAL-01` (`2a31edf`) — unchanged
- error catalog: 23 codes — unchanged
- domain contract: candidate revision 9, 29 opaque identities — the revision does not move; the
  two schema enums are brought up to the catalog that revision 9 already declares
- migration head: `0015_accounts_roles_registration` — unchanged
- controlling plan: `docs/program/dispatch/W49-PLAN.md` §5 item 7 ("upheld release-blocking
  findings only")
- findings: `docs/program/reviews/W49-JUDGE-Y.md` F-1 and `docs/program/reviews/W49-JUDGE-X.md`
  B-1, both upheld in cross-examination (`W49-JUDGE-X.md` §5, §7)
- owner rulings `R-62` (F-6) and `R-63` (QA Q-1), `OWNER_RULINGS_2026-09-17.md` §3.20, recorded
  in this task file's commit; `W49-PLAN.md` §3.3 amended by `R-63` in the same commit
- owner ruling `R-65` (§3.21): the model proxy counts as a live provider in release acceptance

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/domain/v1/identifiers.json` (`identifiers`, the authority for the two identifier-name enums of `identifiers.schema.json`)
- enumerator_owner: `W49-FIX`, under the integrator's contract-slot grant below
- totality_query: every name in `identifiers.json` `identifiers` is admitted by each identifier-name enum of `identifiers.schema.json`, and each such enum admits nothing `identifiers` does not declare

## Captured premise evidence

- premise: at the Stage-E merge the two identifier-name enums of `identifiers.schema.json` lack two names that `identifiers.json` declares, and no test inside `make gate` sees it

### P-01 — F-1 measured by the integrator on the Stage-E merge (`1e988c9`)

- captured_at: 2026-10-06
- command: `python3 -c '<walk identifiers.schema.json for string enums of more than 20 names; print each path, its size and the identifiers.json names it lacks>'`
- captured_output:
  ```text
  /properties/entities/additionalProperties 27 names; missing: ['request_id', 'user_uid']
  /properties/distinct_identities/items/properties/identifiers/items 27 names; missing: ['request_id', 'user_uid']
  ```
- interpretation: the only validation of this pair is `tests/contract/test_cp00_candidate.py`,
  which `make gate` ignores, and it needs `jsonschema`, which the gate's environment does not
  install; that is why the gate stayed green. `contracts/domain/v1/README.md` lines 8–10 and 753
  still say the family schemas pin revision 8; they pin 9 (`W49-JUDGE-X.md` M-X1).

### P-02 — B-1

- interpretation: measured by `W49-JUDGE-X` on 2026-10-06 on the pinned nginx image. The proxy
  bind-mounts `nginx.conf` as a single file; the deploy's `git checkout` replaces the file with a
  new inode (2132108 → 2132118 measured); the container keeps the old inode, so
  `reload-proxy.sh`'s `nginx -t` and `nginx -s reload` both read the old configuration until the
  container is restarted. Every `infra/deploy/proxy/**` change since the stand's proxy was
  created is therefore not served, including `W49-EDGE-01`'s rate limits.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W49-JUDGE-X.md`, `docs/program/reviews/W49-JUDGE-Y.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

Part A — F-1 (integrator's contract-slot grant, for exactly these edits):

- `contracts/domain/v1/identifiers.schema.json` — only the two identifier-name `enum` arrays
  (`/properties/entities/additionalProperties` and
  `/properties/distinct_identities/items/properties/identifiers/items`): add `user_uid` and
  `request_id`, following the arrays' existing order convention
- `contracts/domain/v1/README.md` — only the sentences at lines 8–10 and 753 that say the family
  schemas still pin revision 8; state what is true after this task
- `tests/contract/test_domain_identifiers_schema.py` (new) — asserts the totality query above
  and that the schema's `candidate_revision` pin equals the catalog's; it must be collected by
  `make gate` and must not import `jsonschema` or any package the root locks do not already
  provide (root locks are frozen): walk the schema as P-01 does

Part B — B-1:

- `infra/deploy/deploy.sh`, `infra/deploy/reload-proxy.sh`, `infra/deploy/verify-deployed.sh`
- `infra/deploy/compose.server.yml` — only the `proxy` service's mount lines, and only if the
  repair chooses a directory mount over a recreate
- `infra/deploy/README.md` — only the paragraphs describing proxy reload and verification
- `tests/integration/composition/test_deploy_script_refusals.py`,
  `tests/integration/composition/test_deployed_stack_probe.py`,
  `tests/integration/composition/test_proxy_config_follows_checkout.py` (new)

Part C — stale seam prose:

- `docs/program/P02_SEAMS.md` — only the §7 bullet beginning "every operation but `issueToken`
  requires a bearer credential" (lines 695–701 at `1b25955`): state, from the sealed contract,
  which operations declare `security: []`, and replace the `T-6` "no role vocabulary" clause with
  what `R-55`…`R-61` now establish. State counts by command or by name, never by a bare number.

Part D — `R-62` (archived account is not changed):

- `src/auditmanager/access/accounts.py` — only `update_names` and `set_roles`: an archived account
  answers `not_found` exactly as `reset_password` does; no other method changes
- `tests/integration/access/test_account_management.py`, `tests/integration/api/test_user_management.py`
  — regressions: `updateUser` (names and roles) on an archived account → 404 `not_found` and no
  row changes; after `restoreUser` the same call succeeds

Part E — `R-63` (a failed exchange does not count against a request):

- `src/auditmanager/access/repository.py` — only the `credential is None` branch of the exchange
  (stop executing `_NOTE_A_FAILED_REQUEST_ATTEMPT`; keep `spend_a_verification`), and the
  statement constant itself if it becomes unused
- `src/auditmanager/access/registrations.py` — only docstring sentences that `R-63` makes false
- `tests/integration/access/test_registrations.py`, `tests/integration/api/test_registration_flow.py`
  — regressions through the served path: a pending applicant signs in with the correct password
  more times in a row than `FAILED_SIGN_IN_ALLOWANCE` (refused exchange + status read, as the BFF
  does) and is never throttled; wrong passwords through `readRegistrationStatus` still throttle
  at the allowance; derivation counts per path unchanged (constant work)

Part F — `R-65` (proxy counts as live in release acceptance):

- `tests/e2e/pc01/journey/verify-acceptance.mjs` — the `providerLive` phase passes for
  `provider_mode` `live` or `proxy` and fails for `recorded`, `null` or any other value; the phase
  id and the `w48-alpha-acceptance/v1` evidence schema stay as they are
- `tests/contract/test_alpha_acceptance_command.py` — regressions: `proxy` passes, `recorded` and
  an unknown value fail
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` — only the sentences that name
  `provider_mode=live` (§3 and A04, A05's "live-провайдера"), in Russian like the rest of the file
- `scripts/manual-alpha-check.sh` — only the A04 prompt line that names `provider_mode=live`

Tests that assert behaviour `R-62` or `R-63` supersedes — in `tests/integration/access/test_roles.py`,
`tests/integration/api/qa_w49/**`, `tests/integration/access/qa_w49/**` or
`web/tests/unit/qa_w49/**` — may change only those assertions, each named in the report with the
ruling that supersedes it.

Report:

- `docs/program/W49-FIX.md`

## Forbidden hotspots

- every path not listed above; every other byte of `contracts/**`; `contracts/api/v1/openapi.json`;
  `infra/deploy/proxy/**` (the configuration itself is `W49-EDGE-01`'s and is not changed);
  `.github/**`; migrations; `src/**` and `web/**` outside the files Parts D and E name; root locks; refs, tags, `origin/*`;
  `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`
- a digest, pin or prose guard that turns red because of a Part A edit is a stop: report it, do
  not edit the pin

## Non-goals

- F-2 … F-5, F-7 and R-1 … R-5: they go to the register at `W49-INT-CLOSE`
- no request-burst probe in `verify-deployed.sh`: that script runs on every production deploy,
  and a 429 burst against the live stand is a side effect. A burst probe may exist in a test
  against a disposable stand only.
- no change to what the proxy serves, rate limits or TLS settings

## Deliverables

- Part A: the two enums and the two README sentences; the new gate-resident test
- Part B: after `deploy.sh`, the running proxy has loaded exactly the checkout's
  `infra/deploy/proxy/**` — by recreating the proxy container when any of those files differ
  from what the running container sees, or by a directory mount; the choice and why go in the
  report. `verify-deployed.sh` exits non-zero with a named reason when the SHA-256 of any
  configuration file as seen inside the running proxy differs from the checkout's file.
  `reload-proxy.sh` must no longer report success while the container reads a stale inode.
- Part C: the rewritten bullet
- Part D and Part E: the code changes above with their regressions; each regression red on the
  unrepaired code (two mutations: restore the old branch → red)
- Part F: the verifier change with its regressions; one mutation that drops `proxy` from the
  accepted set turns the `proxy` regression red

## Required tests

- Part A: the new test green at the task's head; red when either added name is removed from
  either enum (two mutations, both red, outputs in the report)
- Part B: reproduce `W49-JUDGE-X`'s two halves on a disposable stand (replace the mounted file
  by a new inode, then reload): the new probe is red on the unrepaired scripts and green after
  the repair; one mutation that removes the recreate/restart step turns the probe red
- the touched suites; `git diff --check`; a full `make gate` on the task's head with the literal
  `GATE OK`

## Integration contract

The integrator merges `agent/w49-fix` into `integration/w49`, runs the final gate on the merged
candidate and proceeds to `W49-INT-CLOSE`. B-1 is release-blocking for `origin/main` only: if
Part B cannot be completed, hand back Parts A and C and say so; the integrator then decides.

## Failure/idempotency/security cases

- lane `gate-w49fix`: ports `56630`, `60230/60231`, taken with `ss -ltn` and recorded; owned
  disposable services only; `make down` and remove the lane's own volumes by exact name at the end
- a repeated `deploy.sh` with unchanged proxy files must not restart the proxy (idempotence is
  `W24-IDEM`'s rule; prove it)
- never kill a process by pattern — only confirmed-own PIDs; no credential, cookie or
  `docker compose config` output in evidence

## Rollback / feature flag

Revert the commit. No flag: the deploy-script change has no runtime toggle.

## Handoff

- changed files: listed in `docs/program/W49-FIX.md` with `git diff --name-only <base>..<sha>`
  and `git status --porcelain -uall` empty
- commands/results: verbatim with exit status; every mutation with its red output
- known limits: listed, never decided silently
- integration notes: hand back branch `agent/w49-fix` at a recorded SHA
