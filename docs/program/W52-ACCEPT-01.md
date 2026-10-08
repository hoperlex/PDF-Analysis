# W52-ACCEPT-01 — measured API build in alpha acceptance

**Base:** `origin/dev` read-back
`092466980912e3937ca794edd37cd22917e0b53f`.
**Lane:** `agent/w52-accept-01`. This is a local implementation candidate,
not a live acceptance or release verdict.

## 1. Result and changed files

The automated acceptance command now computes the candidate API build ID
from the clean checkout's runtime `Dockerfile.api` `COPY` inputs. Its Node
verifier independently computes the same manifest, exchanges the reviewer
login/password for an opaque bearer credential, calls the served
`getProductVersion`, and passes its `apiBuild` phase only when both local
measurements and the served `build_id` agree. It also compares the served
product and contract versions with the candidate and retains separate
operator-attested candidate/deployed SHAs. The machine verdict and
`report.md` record only safe identifiers.

Changed paths:

```text
scripts/manual-alpha-check.sh
tests/e2e/pc01/journey/verify-acceptance.mjs
tests/contract/test_alpha_acceptance_command.py
docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
docs/program/ALPHA-MANUAL-01.md
docs/program/W52-ACCEPT-01.md
```

The `Makefile` target already passed the required environment variables
without arguments or defaults and needed no edit. The old W48 machine
evidence schema name is retained; `phases.apiBuild` adds the measured
verdict and safe candidate/served fields.

## 2. Checks and results

- Full `tests/contract/test_alpha_acceptance_command.py` on the clean
  implementation commit: **25 passed**. Its local HTTP server exercises
  credential exchange and served version reading without a public stand.
  The clean-checkout success case proves that shell, Node and the API's
  build helper agree on `bb0ec71243a2c7404` for this lane's API input set.
  Deliberate served-build mismatch and shell/Node mismatch fail; a missing
  version response blocks; the output and both evidence files omit the
  reviewer password and bearer token.
- `bash -n scripts/manual-alpha-check.sh`, `shellcheck` on that script,
  and `node --check tests/e2e/pc01/journey/verify-acceptance.mjs`: passed.
- Wave-governance and documentation prose/count tests: **93 passed**.
  Exact base comparison preserved all three runbook command blocks,
  20 A01–A20 headings, 19 Russian UI quotations, 101 other numbered
  lines and the 45–70-minute estimate.
- `git diff --check` and exact allowed-path audit: passed before hand-back.
- Full `make gate`, automated checks against a deployed host and manual
  A01–A20 were not run. They remain D-139/D-140 and D-137/D-138 as
  applicable; this lane does not close a live acceptance item.

## 3. Contracts

No API/domain contract, generated client, migration, release-note entry,
`contract_version`, Makefile gate target or runtime service changed.
The existing `w48-alpha-acceptance/v1` verdict gains `apiBuild` with
`candidateMeasured`, `servedMeasured`, `productVersion` and
`contractVersion`. The root PASS requires this phase to PASS. Existing
journey route, refusal, SHA-attestation and provider-live conditions remain.

## 4. Risks and limitations

The build ID covers the W52 API content set, not every deployment input;
`Dockerfile.api` or `infra/deploy/serve.py` alone can change without moving
it. The operator-attested deployed SHA still requires workflow and host
verification under `MAIN_AUTODEPLOY_POLICY.md`; the served version call
measures API process content, not Git history. A reviewer account must be
active with a complete profile. Network or credential refusal yields a
blocked verdict, never a pass. The local HTTP fixture supplies no evidence
about an actual alpha host.

## 5. Integrator instruction

Review the six-path diff, run the required checks on the merged tree,
and merge this clean lane after RELNOTES. Publish only the accepted
development SHA to `origin/dev`. The later release-validation stage
must run this command on an authorized stand, inspect its measured
`apiBuild` phase alongside the host verification and human checklist,
and obtain separate owner authority before any `origin/main` update.

## 6. Forbidden-hotspot proof

The six paths in §1 are exactly within `tasks/W52-ACCEPT-01.md`'s
grant. The historical ALPHA-MANUAL record only gained a forward pointer.
The A01–A20 IDs, commands, routes, figure values and Russian UI quotes in
the runbook remain. `contracts/**`, migrations, API server, loader,
generated client, root dependencies/locks, composition root, global
styles, journey manifest, `origin/dev`, `origin/main`, tags and deployed
services are untouched.
