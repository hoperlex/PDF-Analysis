#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, re, sys

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
notes: list[str] = []

# JSON parse + JSON Schema metaschema checks where applicable.
json_files = sorted(ROOT.rglob('*.json'))
try:
    from jsonschema import Draft202012Validator
    if not callable(Draft202012Validator):
        raise TypeError('Draft202012Validator is not callable')
    if not callable(getattr(Draft202012Validator, 'check_schema', None)):
        raise TypeError('Draft202012Validator.check_schema is not callable')
except Exception as exc:
    print('Bootstrap validation')
    print(
        "FAILED: required Python dependency 'jsonschema' is unavailable or "
        f"unusable ({type(exc).__name__})."
    )
    print(
        "Action: provision a compatible 'jsonschema' package in this command's "
        "Python environment, then rerun the validator."
    )
    sys.exit(2)
for p in json_files:
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'JSON parse: {p.relative_to(ROOT)}: {e}')
        continue
    if isinstance(data, dict) and data.get('$schema','').endswith('2020-12/schema'):
        try:
            Draft202012Validator.check_schema(data)
        except Exception as e:
            errors.append(f'JSON Schema invalid: {p.relative_to(ROOT)}: {e}')


# Validate shipped contract examples.
pairs = [
    ('contracts/analysis/v1/job-package.schema.json','contracts/analysis/v1/examples/job-package.example.json'),
    ('contracts/analysis/v1/stage-result.schema.json','contracts/analysis/v1/examples/stage-result.example.json'),
    ('contracts/analysis/v1/result-package.schema.json','contracts/analysis/v1/examples/result-package.example.json'),
    ('contracts/events/v1/event-envelope.schema.json','contracts/events/v1/examples/event-envelope.example.json'),
]
for schema_rel, example_rel in pairs:
    schema = json.loads((ROOT/schema_rel).read_text(encoding='utf-8'))
    example = json.loads((ROOT/example_rel).read_text(encoding='utf-8'))
    try:
        Draft202012Validator(schema).validate(example)
    except Exception as e:
        errors.append(f'Contract example invalid: {example_rel} vs {schema_rel}: {e}')

# Domain identifier prefix uniqueness.
ids = json.loads((ROOT/'contracts/domain/v1/identifiers.json').read_text(encoding='utf-8'))['identifiers']
prefixes = list(ids.values())
if len(prefixes) != len(set(prefixes)):
    errors.append('Duplicate domain identifier prefix')

# State machine closure + terminal transitions.
sm = json.loads((ROOT/'contracts/domain/v1/state-machines.json').read_text(encoding='utf-8'))['machines']
for name, m in sm.items():
    states = set(m.get('transitions',{})) | set(m.get('terminal',[]))
    if m.get('initial') not in states:
        errors.append(f'{name}: initial state missing from state set')
    for src, dsts in m.get('transitions',{}).items():
        for dst in dsts:
            if dst not in states:
                errors.append(f'{name}: transition {src}->{dst} points to unknown state')
    for term in m.get('terminal',[]):
        if m.get('transitions',{}).get(term):
            errors.append(f'{name}: terminal state {term} has outgoing transition')

# Internal Markdown links.
link_re = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
for p in sorted(ROOT.rglob('*.md')):
    text = p.read_text(encoding='utf-8')
    for target in link_re.findall(text):
        target = target.strip().split()[0].strip('<>')
        if not target or target.startswith(('#','http://','https://','mailto:','urn:')):
            continue
        target = target.split('#',1)[0]
        if not target or '<' in target or '>' in target:
            continue
        resolved = (p.parent/target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            continue
        if not resolved.exists():
            errors.append(f'Broken md link: {p.relative_to(ROOT)} -> {target}')

required = [
 'README.md','AGENTS.md','docs/architecture/ARCHITECTURE_BIBLE.md','docs/architecture/ADR_INDEX.md',
 'docs/program/ROADMAP.md','docs/program/WAVE_EXECUTION_GUIDE.md','docs/program/CHECKPOINT_REGISTRY.md',
 'docs/program/VERSIONING_AND_FREEZE_POLICY.md','docs/stages/S00_architecture_and_behavior_freeze.md',
 'docs/stages/S10_release_acceptance.md','docs/manual-tests/CP-00_architecture.md','docs/manual-tests/CP-10_release.md'
]
for rel in required:
    if not (ROOT/rel).is_file(): errors.append(f'Missing required file: {rel}')

stage_files = list((ROOT/'docs/stages').glob('S[0-9][0-9]_*.md'))
manual_files = list((ROOT/'docs/manual-tests').glob('CP-[0-9][0-9]_*.md'))
adr_files = list((ROOT/'docs/architecture/adr').glob('ADR-*.md'))
notes += [f'json_files={len(json_files)}',f'markdown_files={len(list(ROOT.rglob("*.md")))}',f'stages={len(stage_files)}',f'manual_runbooks={len(manual_files)}',f'adrs={len(adr_files)}']
if len(stage_files)!=11: errors.append(f'Expected 11 stage files, got {len(stage_files)}')
if len(manual_files)!=11: errors.append(f'Expected 11 checkpoint runbooks, got {len(manual_files)}')
if len(adr_files)!=18: errors.append(f'Expected 18 ADR files, got {len(adr_files)}')

print('Bootstrap validation')
for n in notes: print('  '+n)
if errors:
    print(f'FAILED: {len(errors)} problem(s)')
    for e in errors: print(' - '+e)
    sys.exit(1)
print('PASS')
