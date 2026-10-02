# W48-LIVE — completion report

## Result

`W48-LIVE` is complete on local branch `agent/w48-live`.

The repository now owns a named, non-hermetic release command:

```text
make alpha-acceptance
```

It is intentionally outside `make gate`. It has no origin, SHA or credential default and cannot
print `ALPHA ACCEPTANCE PASS` unless one invocation proves all of the following:

- the checkout is clean and its exact full SHA equals both the declared candidate and deployed
  SHA;
- the five synthetic PDFs match their pinned sizes, hashes and PDF magic;
- the origin has the documented TLS/redirect/login/auth boundary;
- sign-in succeeds through the application screen;
- all 3/3 write steps and 16/16 cold routes execute under the declared 780 x 900 viewport;
- every route has `scrollWidth <= innerWidth`;
- the newly created run terminates as `published` or `partial` and reports
  `provider_mode=live`;
- all six refusal fixtures are driven and produce no finding.

The machine evidence is `automated-verdict.json`, schema `w48-alpha-acceptance/v1`. It records
`candidateSha` and `deployedSha` as separate facts, phase outcomes, process exit codes, findings
and the final `PASS` / `FAIL` / `BLOCKED` verdict. The human A01-A12 signature is explicitly
`PENDING`: the automated command cannot claim it.

## Changed files

- `Makefile` — adds the explicit `alpha-acceptance` target beside, never under, `gate`.
- `scripts/manual-alpha-check.sh` — adds the automated mode, SHA/clean-tree preflight, safe
  evidence paths, explicit phase execution and three-way verdict.
- `tests/e2e/pc01/journey/verify-acceptance.mjs` — validates completeness, width, live provider
  provenance and refusal evidence and writes the machine verdict.
- `tests/contract/test_alpha_acceptance_command.py` — command-surface and fail-closed controls.
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` — documents `origin/dev` candidate publication,
  separate direct authority for `origin/main`, the release command and evidence semantics.
- `docs/program/W48-LIVE.md` — this completion report.

Implementation commit before this report: `d67d817` (`feat(W48-LIVE): add external alpha
acceptance gate`).

## Checks

All commands were run from a clean checkout after `d67d817` unless noted.

| Check | Result |
| --- | --- |
| `bash -n scripts/manual-alpha-check.sh` | PASS |
| `shellcheck scripts/manual-alpha-check.sh` | PASS, no finding |
| `node --check tests/e2e/pc01/journey/verify-acceptance.mjs` | PASS |
| `scripts/manual-alpha-check.sh --files-only` | PASS; 5/5 pinned PDFs; `FILES OK` |
| `.venv/bin/python -m pytest tests/contract/test_alpha_acceptance_command.py tests/e2e/test_pc01_journey_conformance.py -q` | PASS; 82 passed in 8.23 s |
| stubbed command: complete live evidence | exit 0 and `ALPHA ACCEPTANCE PASS` |
| stubbed command: `phase=read` | exit 1; no PASS |
| stubbed command: terminal `provider_mode=recorded` | exit 1; no PASS |
| stubbed command: current-run `dependency_unavailable` | exit 2 / BLOCKED; no PASS |
| missing origin / SHA / credential controls | non-zero; no PASS |
| secret sentinel in stdout and `report.md` | absent |
| `make -n alpha-acceptance` | PASS; explicit forwarded inputs, no value/default |
| `git diff --check` | PASS |

`tests/contract/test_alpha_acceptance_command.py` also holds the deterministic composition:
`gate: foundation` remains literal and does not depend on `alpha-acceptance`. No public origin was
contacted and no alpha data was created while testing this command surface.

## Contracts

No API/domain contract, error catalog, generated client, migration, dependency/lock file,
composition root or runtime production module changed. `w48-alpha-acceptance/v1` is a release
evidence document owned by this command, not an application API contract.

## Risks and known limitations

- A real public-origin run was deliberately not performed in this lane. It would mutate alpha
  data and requires deployment evidence plus an authorised reviewer credential. It belongs to
  closeout after the WEB lane is integrated.
- Human A01-A12 remains separately required. Automated PASS alone is not release acceptance.
- `dependency_unavailable` is classified as BLOCKED only when the browser envelope structurally
  reports it for the run created by this invocation; arbitrary log text cannot manufacture that
  classification.
- Wave audit blockers A01 (durable ModelCall/Attempt provenance before provider contact) and A02
  (blob/metadata reconciliation) are not owned or repaired here and still prevent W48 closeout.

## Integrator instruction

1. Integrate `d67d817` and this report after `W48-WEB`; resolve no shared hotspot by taking an
   older copy of the PC-01 files.
2. Run the focused checks above, then the wave-wide local gate on the exact integrated SHA.
3. For actual external acceptance, supply explicit `ALPHA_ORIGIN`, `ALPHA_CANDIDATE_SHA`,
   `ALPHA_DEPLOYED_SHA`, `E2E_PC01_LOGIN` and `E2E_PC01_PASSWORD`; retain the machine evidence
   and obtain the separate human A01-A12 signature.
4. Publish a completed W48 candidate to `origin/dev` only under `W48-INT-CLOSE`. This task grants
   no push authority. Do not update `origin/main` without a separate direct owner instruction for
   the exact candidate and the complete auto-deploy policy procedure.

## Forbidden-hotspot proof

Against the Stage-B dispatch base `7ad7cfe`, the implementation changed only:

```text
Makefile
docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
scripts/manual-alpha-check.sh
tests/contract/test_alpha_acceptance_command.py
tests/e2e/pc01/journey/verify-acceptance.mjs
docs/program/W48-LIVE.md
```

Every path is in `W48-LIVE.allowed_paths`; this task is the wave's sole `Makefile` owner. No
workflow, `infra/deploy/**`, contract, generated file, migration, production backend/frontend
code, dependency/lock, programme state/register/history, ref, tag, host or secret store changed.
