# Task W0-ARC-01 — architecture and ADR evidence reconciliation

## Outcome

Produce a CP-00 architecture review candidate that reconciles the greenfield Bible,
the immutable ADR-0001–ADR-0018 baseline and every newly indexed superseding ADR
with accepted behavioral evidence and the pinned refactoring architecture source.
Record each owner decision explicitly; do not mark product semantics approved
without repository-owner evidence.

## Ownership

- implementation owner: planned agent `/root/w0_architecture_ratification`
- program integrator / frozen-boundary governor: primary agent `/root`
- product/domain approval authority: repository owner/user
- independent reviewer: assigned by integrator and separate from the author

## Depends on

- Completed `W0-BHV-01`, accepted at
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`.
- Completed `W0-DEP-01`, accepted at
  `ab1cfdab0ec5c413b188a44ff82a99586ecd7994`.
- Completed `W0-EVD-01`, accepted at
  `134436502b7ee40ca9abb061e0080741a863ffda`.
- Completed `W0-QA-02`, accepted at
  `6c82004b35f49463c8e7fc8602fbced2f374167e`.

## Frozen inputs

- base commit: `6c82004b35f49463c8e7fc8602fbced2f374167e`
- behavioral inventory semantics at `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`,
  normalized evidence locators at `134436502b7ee40ca9abb061e0080741a863ffda`
- greenfield Bible, ADR index and ADR-0001–ADR-0018 baseline at the base commit
- refactoring architecture package:
  `0b937dc0e24d38fb98485a920152b83d2f19c982`
- refactoring Bible blob: `040a514dc37113d0712cde6757900d2c7d918c10`
- machine contracts: advisory/read-only; migration head: none

## Allowed paths

- `docs/architecture/**`

Avoid unrelated restyling. No other path is writable.

## Forbidden hotspots

- `contracts/**`, `fixtures/**`, `tests/**`, source/runtime code
- program/current-state/checkpoint/stage-plan files
- root dependency/lock files, migrations, composition root and global styles
- every legacy repository file/ref/worktree entry

## Non-goals

- No machine-contract or production implementation changes.
- No automatic acceptance of source ADR status or legacy decomposition.
- No tenant/IdP/retention/legal-hold values invented without owner support.
- No runtime Strangler dependency and no copying legacy services.

## Deliverables

1. `docs/architecture/CP00_ARCHITECTURE_REVIEW.md` containing each Bible principle
   and one disposition-table row for every current indexed ADR, including the
   ADR-0001–ADR-0018 baseline, with disposition `ratify`, `adapt`, `defer` or
   `supersede`, evidence, compatibility impact and unresolved decisions. Principle
   table rows begin with `| P-NN |`; ADR table rows begin with `| ADR-NNNN |`.
2. `docs/architecture/CP00_ARCHITECTURE_REVIEW.json` as the machine review matrix.
   Its `adrs[]` entries require unique `adr_id`, `disposition`, `evidence`,
   `compatibility_impact` and `owner_decisions`; its `principles[]` entries require
   stable `principle_id`, source anchor, disposition and evidence.
3. Minimal evidence-required updates to Bible/ADR index/domain model/catalog only
   where the review demonstrates drift.
4. Decision records presented for explicit owner approval:
   - `PD-01`: correction/revocation is a new append-only decision event/projection
     change, intentionally diverging from legacy overwrite/delete;
   - `PD-02`: one versioned target stage registry is authoritative;
   - `PD-03`: Run/Job/Attempt are distinct and attempt authority/fencing mandatory;
   - `PD-04`: graphic/vector comparison is future target scope and absent from
     legacy parity.
5. Legacy fail-soft cases mapped to explicit target failure/partial policy; never a
   silent success rule.
6. ADR-0014 remains proposed until tenant/IdP/TTL/legal-hold authority is approved.
7. A `supersede` disposition that requires a replacement creates the next unique
   ADR file and index row inside this task's architecture slot; it never rewrites or
   removes the superseded baseline ADR.

Task acceptance is blocked while `PD-01`–`PD-04` lack explicit owner disposition.

## Required tests

- Command: `git -C /root/projects/PDF-proverka/PDF-proverka cat-file -e 0b937dc0e24d38fb98485a920152b83d2f19c982^{commit}`.
  Expected: exit `0`.
- Command: `git -C /root/projects/PDF-proverka/PDF-proverka rev-parse 0b937dc0e24d38fb98485a920152b83d2f19c982:docs/architecture/ADR_BIBLE.md`.
  Expected: exact output `040a514dc37113d0712cde6757900d2c7d918c10`.
- Command: `python3 -c "import json,re; from pathlib import Path; baseline={f'ADR-{n:04d}' for n in range(1,19)}; expected_principles=[f'P-{n:02d}' for n in range(1,23)]; p=json.loads(Path('docs/architecture/CP00_ARCHITECTURE_REVIEW.json').read_text()); rows=p['adrs']; ids=[x['adr_id'] for x in rows]; assert baseline<=set(ids) and len(ids)==len(set(ids)); assert all(x['disposition'] in {'ratify','adapt','defer','supersede'} and x['evidence'] and 'compatibility_impact' in x and 'owner_decisions' in x for x in rows); principles=p['principles']; principle_ids=[x['principle_id'] for x in principles]; assert sorted(principle_ids)==expected_principles and len(principle_ids)==len(set(principle_ids))==22; assert all(x['source_anchor'] and x['evidence'] and x['disposition'] in {'ratify','adapt','defer','supersede'} for x in principles); markdown=Path('docs/architecture/CP00_ARCHITECTURE_REVIEW.md').read_text(); markdown_adrs=re.findall(r'^\|\s*(ADR-\d{4})\s*\|',markdown,re.MULTILINE); markdown_principles=re.findall(r'^\|\s*(P-\d{2})\s*\|',markdown,re.MULTILINE); files={re.match(r'(ADR-\d{4})',x.name).group(1) for x in Path('docs/architecture/adr').glob('ADR-*.md')}; index=Path('docs/architecture/ADR_INDEX.md').read_text(); indexed=set(re.findall(r'\[(ADR-\d{4})[^]]*\]\(adr/ADR-\d{4}[^)]*\.md\)',index)); assert set(ids)==set(markdown_adrs)==files==indexed and len(markdown_adrs)==len(set(markdown_adrs)); assert sorted(markdown_principles)==expected_principles and len(markdown_principles)==len(set(markdown_principles))==22"`.
  Expected: exit `0`; P-01–P-22 and the immutable ADR-0001–ADR-0018 baseline occur
  exactly once; any additional ADR is unique and occurs in the JSON matrix,
  Markdown matrix, ADR directory and index; every machine row carries the required
  review fields.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with standalone `PASS`.
- Command: `git diff --check -- docs/architecture`.
  Expected: exit `0` and no output.
- Command: `python3 -c "import re; from pathlib import Path; files=list(Path('docs/architecture').rglob('*.md')); bad=[]; [(bad.append((str(p),t)) if t and not re.match(r'^[a-z]+://',t) and not (p.parent/t.split('#',1)[0].strip('<>')).exists() else None) for p in files for t in re.findall(r'\[[^]]+\]\(([^)]+)\)',p.read_text()) if not t.startswith(('#','mailto:'))]; assert not bad,bad"`.
  Expected: exit `0`; every local Markdown link target under `docs/architecture`
  resolves.
- Independent reviewer samples evidence/disposition and repository owner records an
  explicit decision for every `PD-*` item.

## Integration contract

After acceptance, DOM/ANA owners may rely on approved `PD-*` meanings, authoritative
data ownership and architecture dispositions. They may not rely on legacy
implementation details, proposed source ADRs or unresolved owner values as frozen
contracts.

## Failure / idempotency / security

- Conflicting evidence is recorded and escalated; no semantic choice by the agent.
- Missing owner decision blocks acceptance/freeze, not documentation preparation.
- Re-running review updates one disposition per principle/ADR; it cannot duplicate
  or silently change an approved decision.
- No source may disclose credentials, payloads or mutable checkout evidence.

## Rollback / feature flag

Documentation-only task; no feature flag. Revert only this task's architecture-doc
commit before ratification. Accepted ADR history is superseded by a new ADR, never
silently rewritten after checkpoint acceptance.

## Handoff

- changed files and 18-ADR coverage
- commands/results and independent-review evidence
- exact owner disposition for `PD-01`–`PD-04`
- new/changed contracts: `none`
- known risks/deferred ADRs
- allowed-path proof and integrator notes for DOM/ANA reconciliation
