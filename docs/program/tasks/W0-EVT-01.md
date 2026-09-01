# Contract task W0-EVT-01 — event envelope contract version key

> **Status: backlog draft. Not executable yet.**
> This task sits last in the `ID-01` chain. `W0-DOM-01` and `W0-ANA-01` are accepted
> candidates awaiting the W0.2 integration commit; `W0-QA-03` and `W0-DOM-02` remain
> backlog drafts. Its repository-wide sweep cannot pass until the whole chain lands.
> Pin the real commits below when they exist.

## Outcome

Bring `contracts/events/v1/**` onto the canonical contract-version key so that every
machine contract family declares its envelope version the same way before any freeze
is recorded.

## Problem

The repository owner fixed the canonical key as `contract_version` carrying a string
semver/draft value; `$schema` remains the JSON Schema dialect and `$id` remains
schema identity. The bare `version` key and the `schema_version` key are removed as
contract envelope versions before freeze.

The domain and analysis families are being brought onto `contract_version` by
`W0-DOM-01` and `W0-ANA-01`. The event family is the remaining divergence: at the
base commit `contracts/events/v1/event-envelope.schema.json` requires and pins
`"schema_version": {"const": 1}`, and `examples/event-envelope.example.json` carries
`"schema_version": 1` — an integer, which cannot express a draft candidate at all.

No wave lane owns `contracts/events/v1/**`, so the divergence cannot be closed inside
`W0.2`; the wave's non-goals forbid event-contract expansion, and the integrator does
not silently edit an unowned contract family. This task creates that ownership.

## Ownership

- provider/contract owner: assigned agent; single owner of `contracts/events/v1/**`
  for the duration of this task
- frozen-boundary governor: primary agent `/root`
- consumers: control plane, API, findings and operations tasks after freeze
- independent reviewer: assigned by the integrator; must not author the reviewed
  contract
- product/domain approval authority: repository owner/user; already exercised for the
  canonical-key decision, not required again for this mechanical alignment

## Depends on

- `W0-DOM-01` and `W0-ANA-01`, integrated at `<pending integration commits>`, so the
  exact string form used by the other two families is fixed before the event family
  copies it. Both candidates have passed independent review.
- `W0-QA-03` and `W0-DOM-02`, integrated at `<pending integration commits>`. Without
  both, the repository-wide sweep below cannot pass: `scripts/validate_bootstrap.py`
  hard-requires the bare `version` key on `contracts/domain/v1/error-codes.json`, so
  the domain family cannot drop its deprecated mirror and the sweep would fail on a
  file this task does not own.

## Origin

Opened by owner integration decision recorded in
`docs/architecture/CP00_OWNER_DECISIONS.md`: canonical machine-contract version key
is `contract_version` with a string semver/draft value; `version` and
`schema_version` are removed as contract envelope versions before freeze.

## Frozen inputs

- base commit: `337efcc4239912f323aa53fa747e9452edd25785`
- current event contract: `contracts/events/v1/**` at the base commit
- canonical key decision: `docs/architecture/CP00_OWNER_DECISIONS.md` at its accepted
  commit
- accepted domain and analysis candidates: read-only reference for the exact version
  string form only; no event semantics may be imported from them
- migration head: none

## Allowed paths

- `contracts/events/v1/**`

No other contract family or path is writable.

## Forbidden hotspots

- `contracts/domain/**`, `contracts/analysis/**`, API and comparison contracts
- architecture and program documents, fixtures, tests, source/runtime code
- `scripts/validate_bootstrap.py` and its tests
- root dependency/lock files, migrations, composition root, global styles and legacy

## Non-goals

- No new event type, aggregate type, field, payload schema or routing semantics. This
  is a version-key alignment, not an event-contract design task.
- No change to `$id` or to the `$schema` dialect.
- No cross-family `$ref` while both other families are drafts.
- No renaming of any field other than the envelope version key.
- No contract freeze by the task author; freeze remains the integrator's slot.

## Deliverables

- `event-envelope.schema.json`: `schema_version` replaced by `contract_version`,
  typed as a string and pinned to the declared candidate value. `$id` and `$schema`
  unchanged. `additionalProperties: false` retained, so a payload still carrying
  `schema_version` fails closed rather than being silently accepted.
- `examples/event-envelope.example.json`: updated to the new key and value; still
  validates.
- `examples/event-envelope.legacy-schema-version.invalid.json`: a negative fixture
  carrying the old `schema_version` integer, rejected specifically because the
  removed key is not permitted.
- `README.md`: records the canonical key, the candidate version, the rejected old
  form, and that the integer `1` had no draft-candidate expression.

## Compatibility

- backward compatible: no; the envelope version key is renamed and retyped
- version bump: bootstrap draft → `1.0.0-draft.1` candidate, matching the other two
  families
- safe before frozen consumers exist; after freeze this requires the formal
  freeze-break and version procedure

## Required tests

- Command: `.venv/bootstrap/bin/python -c "import json,glob; from jsonschema import Draft202012Validator as V; [V.check_schema(json.load(open(p))) for p in glob.glob('contracts/events/v1/*.schema.json')]"`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python -m jsonschema -i contracts/events/v1/examples/event-envelope.example.json contracts/events/v1/event-envelope.schema.json`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python -m jsonschema -i contracts/events/v1/examples/event-envelope.legacy-schema-version.invalid.json contracts/events/v1/event-envelope.schema.json`.
  Expected: non-zero, because the removed `schema_version` key is no longer permitted.
- Command: `.venv/bootstrap/bin/python -c "import json,glob; B={'version','schema_version'}
def scan(o,path,out):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='properties' and isinstance(v,dict): out += [f'{path}/properties/{pk}' for pk in v if pk in B]
            if k=='required' and isinstance(v,list): out += [f'{path}/required:{r}' for r in v if r in B]
            scan(v,f'{path}/{k}',out)
    elif isinstance(o,list):
        for i,v in enumerate(o): scan(v,f'{path}[{i}]',out)
bad=[]
for p in sorted(glob.glob('contracts/**/*.json',recursive=True)):
    d=json.load(open(p)); hits=[f'<top>/{k}' for k in B if isinstance(d,dict) and k in d]
    scan(d,'',hits)
    if hits: bad.append((p,hits))
assert not bad, bad"`.
  Expected: exit `0`; no machine contract declares a bare `version` or a
  `schema_version` envelope key anywhere under `contracts/` — as a top-level instance
  key, as a schema `properties` member, or as a `required` entry at any depth.

  The sweep must recurse into schemas, not only inspect top-level instance keys. A
  top-level-only check misses `event-envelope.schema.json` entirely, because there
  `schema_version` lives under `properties` and `required` — that is, it misses the
  very file this task exists to change. Verified before this task was written: the
  top-level form reports 2 files, the recursive form reports 4.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with a standalone `PASS`.
- Command: `git diff --check -- contracts/events/v1`.
  Expected: exit `0` and no output.
- Independent reviewer confirms no event semantics changed: the field set apart from
  the version key, `$id`, the dialect and every pattern are identical to the base
  commit.

## Integration contract

After acceptance, consumers read the event envelope version from `contract_version`
as a string. An envelope carrying the old `schema_version` key is rejected, not
coerced. The event family declares no dependency on the domain or analysis families.

## Failure/idempotency/security cases

- An envelope carrying both keys, or only the removed key, fails closed; there is no
  compatibility shim and no silent coercion.
- Re-running the task is idempotent: the same key, type and candidate value, with no
  duplicated field and no second negative fixture.
- Examples contain no credential, real identifier, customer payload or production
  correlation value; all values stay synthetic.
- Diagnostics from a rejected envelope must not echo payload content.

## Rollback / feature flag

Contract-only change; no bypass feature flag, because a contract-version gate must
not be skippable. Before freeze, revert this task's path. After freeze, stop
consumers and follow the freeze-break/version procedure.

## Handoff

- changed files and the final candidate version string
- commands/results, including the expected-non-zero negative fixture and the
  repository-wide key sweep
- new/changed contracts: events `1.0.0-draft.1` candidate only
- compatibility notes and confirmation that no event semantics changed
- integration notes for control-plane/API consumers
- proof that no other contract family, migration, runtime, legacy or forbidden
  hotspot changed
