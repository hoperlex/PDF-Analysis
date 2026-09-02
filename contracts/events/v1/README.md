# Event contract area

Events contain event ID, type, contract version, aggregate/entity IDs, occurred-at/actor/source and minimal payload needed by the consumer. They do not clone full aggregates.

Durable business/security audit events and integration outbox events have explicit schemas/owners; diagnostic log messages are not events.

## Envelope contract version

- Canonical key: `contract_version`, declared once in the root `properties` of `event-envelope.schema.json` and listed in the root `required`.
- Candidate value: the string `1.0.0-draft.1`, the same unreleased candidate the domain and analysis families declare. The key is typed `string` and pinned with `const`.
- Rejected old form: `"schema_version": 1`. The key is removed from the root `required` and from the root `properties`; the root keeps `additionalProperties: false`, so an envelope still carrying `schema_version` fails closed instead of being silently accepted. There is no alias, shim or coercion, and the old key is never read as a fallback.
- The old form could not express this candidate at all: `schema_version` was pinned to the integer `1`, and an integer has no representation for a draft-candidate version such as `1.0.0-draft.1`. Retyping the envelope version to a string is therefore part of the same change, not a separate one.
- Consumers read the envelope version from `contract_version` as a string. An envelope carrying `schema_version`, with or without a valid `contract_version`, is rejected.

Only the envelope version key changed. `$id`, the `$schema` dialect, every other field and every `pattern` are unchanged, and no event type, aggregate type, field or routing rule was added, removed or renamed.

## Files

- `event-envelope.schema.json` — the envelope schema.
- `examples/event-envelope.example.json` — positive example; validates.
- `examples/event-envelope.legacy-schema-version.invalid.json` — negative fixture. It carries a valid `contract_version` **and** the removed `schema_version` key, so it is rejected for exactly that key: deleting `schema_version` alone makes it validate.

## Reproducible checks

Run from the repository root with the pinned bootstrap interpreter.

Every owned schema is a valid Draft 2020-12 schema:

```bash
.venv/bootstrap/bin/python -c "import json,glob; from jsonschema import Draft202012Validator as V; [V.check_schema(json.load(open(p))) for p in glob.glob('contracts/events/v1/*.schema.json')]"
```

The positive example validates:

```bash
.venv/bootstrap/bin/python -m jsonschema -i contracts/events/v1/examples/event-envelope.example.json contracts/events/v1/event-envelope.schema.json
```

The negative fixture is rejected for the removed key alone. A bare non-zero exit proves nothing here, because any invalid document exits non-zero; this form asserts that the fixture carries a valid `contract_version`, that at least one error is attributable to `schema_version` by message or instance path, and that removing that single key leaves a document with no remaining errors:

```bash
.venv/bootstrap/bin/python -c "import json; from pathlib import Path; from jsonschema import Draft202012Validator as V; r=Path('contracts/events/v1'); s=json.loads((r/'event-envelope.schema.json').read_text()); d=json.loads((r/'examples/event-envelope.legacy-schema-version.invalid.json').read_text()); assert d.get('contract_version'), 'fixture must carry a valid contract_version'; errs=list(V(s).iter_errors(d)); assert errs, 'fixture was accepted'; blame=[e for e in errs if 'schema_version' in e.message or list(e.path)[:1]==['schema_version']]; assert blame, [e.message for e in errs]; clean=json.loads(json.dumps(d)); clean.pop('schema_version'); assert not list(V(s).iter_errors(clean)), 'fixture is rejected for some other reason too'; print('rejected for schema_version alone:', blame[0].message)"
```

No machine contract anywhere under `contracts/` **declares** a bare `version` or a `schema_version` envelope key — as a `properties` member or a `required` entry at any depth, or as a top-level key of an example that is meant to validate. The sweep must recurse; a top-level-only check does not see this family's schema at all. Deliberately invalid fixtures are excluded, because carrying the forbidden key is the whole point of one of them; exit `0`:

```bash
.venv/bootstrap/bin/python -c "import json,glob; B={'version','schema_version'}
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
assert not bad, bad"
```

The same sweep without that exclusion — the form written into the `W0-EVT-01` Required tests — reports exactly one file, `examples/event-envelope.legacy-schema-version.invalid.json`, and exits `1`. That is not a residual declaration: the fixture is required by the same task to carry a top-level `schema_version`, and the negative gate above requires that key to be poppable from the top level, so the two Required tests cannot both hold literally. Run it to see the residue is that one file and nothing else; expected exit `1`:

```bash
.venv/bootstrap/bin/python -c "import json,glob; B={'version','schema_version'}
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
assert not bad, bad"
```

The repository-wide bootstrap validator, which revalidates the envelope schema and its positive example, exits `0` and prints a standalone `PASS`:

```bash
.venv/bootstrap/bin/python scripts/validate_bootstrap.py
```
