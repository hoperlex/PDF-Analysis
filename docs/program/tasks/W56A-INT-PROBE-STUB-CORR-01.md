# Task W56A-INT-PROBE-STUB-CORR-01 — refuse namespaced stub models before paid probes

## Outcome

The W56a identity probe refuses `stub/...` as a selected gateway model before
network use and as a default response identity, closing a concrete hole found
in the available local configuration. `W56A-MODEL-PIN-01` is refreshed to
consume the corrected development tip; no paid probe or lock pin occurs here.

## Depends on

- `W56A-INT-PROBE-TOOL-CORR-01` — complete at `ca8fcf61`;
- `W56A-INT-PROFILE-CONTENT-01` — complete at `d6d37e44`.

## Frozen inputs

- base `origin/dev=d6d37e44061cbcc0fa96907e59bb4319c4a72a5c`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`, W56 §A3.5, R-133–R-136.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the local host-owned provider configuration contains a namespaced
  stub model, while the published `_name` accepted it as a concrete name.

### P-01 — sanitized configuration shape

- captured_at: 2026-10-15
- command: `python3 -c "from pathlib import Path; rows=Path('/root/projects/PDF-Analysis/infra/deploy/env/provider.env').read_text().splitlines(); model=next(line.split('=',1)[1].strip() for line in rows if line.startswith('PROXY_LLM_MODEL=')); print('stub_prefix='+str(model.casefold().startswith('stub/')))"`
- captured_output:
  ```text
  stub_prefix=True
  ```
- interpretation: this local model selector is a stub family, not a verified
  model identity. It is not a gateway route or a paid probe result.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W56A-INT-PROBE-TOOL-CORR-01.md` (immutable earlier correction)
- addendum_path: `docs/program/W56A-INT-PROBE-STUB-CORR-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tools/provider/identity_probe.py` (`_name` refusal only);
- `tests/contract/provider/test_identity_probe.py` (focused examples);
- `docs/program/tasks/W56A-MODEL-PIN-01.md` (base/dependency only);
- this task file, `docs/program/W56A-INT-PROBE-STUB-CORR-01.md` (new report);
- `docs/program/CURRENT_STATE.md` (top development status only).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing application/provider
runtime, root dependencies/locks, composition roots, global styles,
`VERSION`, recordings, stand state, `origin/main` and tags.

## Non-goals

No gateway reconfiguration, credential access, paid call, selected-model
pin, cheaper-tier proof, v2 activation, full local gate, acceptance or beta
claim.

## Deliverables

Namespaced stub refusal, focused tests, refreshed MODEL-PIN task, correction
report with exact changed-path proof and dev ref read-back.

## Required tests

Run focused probe tests, module compilation, direct task governance,
`git diff --check`, exact changed-path proof. Do not run `make gate`.

## Integration contract

`W56A-MODEL-PIN-01` uses this corrected tool from the published SHA. A
`stub/...` configuration fails before opening a connection; a `stub/...`
response cannot satisfy the default signal. Other concrete model names keep
their existing handling. Two distinct gateway PASS results remain required
before the lock changes.

## Failure/idempotency/security cases

No network request on a stub configuration; no secret or private URL in
output. Repeated local validation has no charge. A transport-unknown outcome
on a later legitimate probe still counts as potentially charged and is not
blindly retried.

## Rollback / feature flag

Revert this bounded tool correction before paid calls, or correct forward
afterward. No runtime feature flag or data migration exists.

## Handoff

- changed files/checks/limits: correction report;
- contracts: none;
- next: MODEL-PIN only on corrected distinct routes with a fresh ledger
  projection; no `origin/main` authority.
