# Contract task W0-EVT-01 — event envelope contract version key

> **Status: completed, independently accepted and integrated.**
> Integration commit: `3ca8e25413426ff8efec41cd850c325331d181fc`.
> This task closed the `ID-01` chain: the repository-wide sweep now finds no bare
> `version` or `schema_version` declaration anywhere under `contracts/**`.

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

- `W0-DOM-01` and `W0-ANA-01`, integrated at
  `cf7740474b1786163f54d93b013a0d526ef989e0`, so the exact string form used by the
  other two families is fixed before the event family copies it.
- `W0-QA-03`, integrated at
  `23dddf99f833d12cd4cc22d11e224d4b278872bf`.
- `W0-DOM-02`, integrated at
  `478d32e90d1cbb2c691e0ac0b61b68dadcf0d397`. Its accepted sweep leaves only the
  event schema and example named below.

## Origin

Opened by owner integration decision recorded in
`docs/architecture/CP00_OWNER_DECISIONS.md`: canonical machine-contract version key
is `contract_version` with a string semver/draft value; `version` and
`schema_version` are removed as contract envelope versions before freeze.

## Frozen inputs

- base commit: `478d32e90d1cbb2c691e0ac0b61b68dadcf0d397`
- current event contract: `contracts/events/v1/**` at that base commit
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
- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator as V; r=Path('contracts/events/v1'); s=json.loads((r/'event-envelope.schema.json').read_text()); d=json.loads((r/'examples/event-envelope.legacy-schema-version.invalid.json').read_text()); assert d.get('contract_version'), 'fixture must carry a valid contract_version'; errs=list(V(s).iter_errors(d)); assert errs, 'fixture was accepted'; blame=[e for e in errs if 'schema_version' in e.message or list(e.path)[:1]==['schema_version']]; assert blame, [e.message for e in errs]; clean=json.loads(json.dumps(d)); clean.pop('schema_version'); assert not list(V(s).iter_errors(clean)), 'fixture is rejected for some other reason too'; print('rejected for schema_version alone:', blame[0].message)"`.
  Expected: exit `0`, printing the rejection message that names `schema_version`.

  A bare non-zero exit is not acceptable evidence here. `-m jsonschema` exits non-zero
  for any invalid document, so a fixture that was malformed, missing a required field
  or broken in some unrelated way would produce the same green result while proving
  nothing about the removed key. This form proves three things instead: the fixture
  carries a **valid** `contract_version`, so it is not rejected merely for lacking one;
  at least one error is attributable to `schema_version` by message or instance path;
  and removing that single key makes the document validate cleanly, so no other defect
  contributes to the rejection.
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
    if p.endswith('.invalid.json'): continue
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
- Command: `git status --porcelain -- contracts docs fixtures scripts tests requirements`.
  Expected: no path outside `contracts/events/v1/`. Assert the **path set**, never a
  status code, and accept an empty result: while the task is in flight the four
  deliverables appear as ` M`/`??`, and once integrated the tree is clean and the
  command prints nothing. Pinning `??` would make the gate unsatisfiable after its own
  integration, the defect already found and repaired in `W0-ARC-02`.

  `*.invalid.json` is excluded, and the exclusion is the point rather than a
  loophole. This task's own negative fixture is *required* to carry a top-level
  `schema_version` beside a valid `contract_version` — that is what the preceding gate
  proves. Without the exclusion the two gates are mutually unsatisfiable: every fixture
  that satisfies the negative gate fails the sweep, and there is no third option,
  because renaming the file breaks the negative gate's literal path and moving it
  outside `contracts/**` violates allowed paths. A negative fixture exists to hold the
  forbidden shape; sweeping it for forbidden shapes is a category error. The sweep's
  subject is what a contract *declares*, and an `*.invalid.json` file declares nothing.
  Verified after the exclusion: zero hits. Twenty-two of the twenty-seven JSON files
  under `contracts/**` are swept and five `*.invalid.json` fixtures are skipped; run
  without the exclusion, the only hit in the whole tree is this task's own fixture.

  Use `git status --porcelain`, not `git diff --name-only <base>`, for this proof. The
  negative fixture is a new file and this task forbids `git add`, so `git diff` cannot
  see it: the command would return only the modified paths and silently omit the one
  deliverable most worth checking. `git diff --check` above is blind to it for the same
  reason, so verify the fixture's whitespace and trailing newline directly.
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
