# Golden journey selection — W0-BHV-02

## 1. Scope and status

This document reviews the selected golden set produced by task
[W0-BHV-02](../../docs/program/tasks/W0-BHV-02.md) inside wave
[W0.2](../../docs/program/waves/W0.2_architecture_domain_contract.md).

| Item | Frozen value |
|---|---|
| Status | Candidate; round-4 corrections applied after a second independent pass returned `REJECT` on the round-3 candidate |
| Base commit | `6c82004b35f49463c8e7fc8602fbced2f374167e` |
| Immutable legacy oracle | `32b9d903792b30506048a1d42b0e6b2d07aee403` |
| Accepted inventory | `docs/behavior/legacy_capability_inventory.md` at `667fb00fe3e45d1ce0bce7860725c1654b4cdeba` |
| Method | Read-only Git-object inspection of the pinned legacy commit plus the accepted inventory |
| Runtime execution | None: no legacy service, job, provider, migration or user flow was run |
| Data classification | Synthetic for all five journeys |

Nothing here freezes a contract. The four owner decisions `PD-01`–`PD-04` were
disposed of by the repository owner on 2026-09-01: `PD-01`, `PD-02` and `PD-03` are
approved with modification and `PD-04` is approved. The six expectations that
depended on them are now `greenfield_target`, each carrying the decision identifier
and the approved wording, and each keeping `parity_oracle: false`: an approved target
is still not legacy parity evidence. The disposition was received as a direct owner
instruction in the W0.2 integrator session. No other lane's uncommitted draft was read
as an approval, and this file ratifies no contract.

## 2. Selected set

| Selected journey | Title | Comparison mode | Inventory candidates |
|---|---|---|---|
| [GJ-01](GJ-01/manifest.json) | Precheck, ingest and version isolation | `exact` | `GJ-01` |
| [GJ-02](GJ-02/manifest.json) | Audit interruption, resume, retry, skip and export packaging | `replay` | `GJ-02`, `GJ-07` |
| [GJ-03](GJ-03/manifest.json) | Finding rerun, carryover under provider failure, expert correction and revocation | `replay` | `GJ-03`, `GJ-04` |
| [GJ-04](GJ-04/manifest.json) | Comparison links, reuse, stale invalidation, repair and undo | `semantic` | `GJ-05`, `GJ-06` |
| [GJ-05](GJ-05/manifest.json) | Worker reconnect, attempt authority, crash recovery and route exposure | `exact` | `GJ-08`, `GJ-09`, `GJ-10`, `GJ-11` |

The machine-readable form of this table, including the manifest checksums, is
[selection.json](selection.json).

## 3. Fan-in map and its rules

The inventory identifiers and the selected identifiers are different namespaces that
happen to share a prefix. Reading `GJ-04` in the inventory as `GJ-04` in the selected
set is a reviewer trap, so the map below is normative.

| Inventory candidate | Inventory subject | Folded into |
|---|---|---|
| `GJ-01` | Precheck and ingest as V1 and V2 | `GJ-01` |
| `GJ-02` | Interrupt after each stage and resume, retry or skip | `GJ-02` |
| `GJ-07` | Export once with Excel success and once with generator failure | `GJ-02` |
| `GJ-03` | Review a finding, rerun on the next version with provider failure | `GJ-03` |
| `GJ-04` | Revoke or correct an expert decision | `GJ-03` |
| `GJ-05` | Re-run comparison with identical signature, then change a source, exclusion or link | `GJ-04` |
| `GJ-06` | Apply and undo a high-confidence sheet-link repair | `GJ-04` |
| `GJ-08` | Worker disconnect, reconnect and chunk resume | `GJ-05` |
| `GJ-09` | Attempt declared lost, new attempt, late old result | `GJ-05` |
| `GJ-10` | Crash during result apply and restart | `GJ-05` |
| `GJ-11` | Disabled and enabled distributed route configurations | `GJ-05` |

Properties enforced mechanically by the third required test and by
`selection.schema.json`:

- all eleven inventory candidates appear;
- no candidate appears twice;
- the selected order is exactly `GJ-01`, `GJ-02`, `GJ-03`, `GJ-04`, `GJ-05`;
- each `manifest_path` is exactly `fixtures/golden/<journey_id>/manifest.json`.

Absence of graphic and vector comparison is recorded as target-scope annotation
`TSA-01` on `GJ-04`. It is additive, it is not a twelfth inventory candidate and it
takes no place in the fan-in map.

### 3.1 Assertion-level coverage

A candidate-to-journey edge is not sufficient for acceptance: five aggregate journeys
could otherwise absorb a candidate without asserting anything about it.
`inventory_assertion_coverage` in [selection.json](selection.json) is therefore the
machine-readable resolution of each inventory candidate down to the concrete
expectation and failure-case identifiers that characterize it.

| Inventory candidate | Journey | Count | Assertions |
|---|---|---|---|
| `GJ-01` | `GJ-01` | 15 | `GJ-01-EO-01`, `GJ-01-EO-02`, `GJ-01-EO-03`, `GJ-01-EO-04`, `GJ-01-EO-05`, `GJ-01-EO-06`, `GJ-01-EO-07`, `GJ-01-EO-08`, `GJ-01-FC-01`, `GJ-01-FC-02`, `GJ-01-FC-03`, `GJ-01-FC-04`, `GJ-01-FC-05`, `GJ-01-FC-06`, `GJ-01-FC-07` |
| `GJ-02` | `GJ-02` | 14 | `GJ-02-EO-01`, `GJ-02-EO-02`, `GJ-02-EO-03`, `GJ-02-EO-04`, `GJ-02-EO-05`, `GJ-02-EO-06`, `GJ-02-EO-07`, `GJ-02-EO-11`, `GJ-02-EO-12`, `GJ-02-EO-13`, `GJ-02-FC-01`, `GJ-02-FC-02`, `GJ-02-FC-03`, `GJ-02-FC-04` |
| `GJ-03` | `GJ-03` | 10 | `GJ-03-EO-01`, `GJ-03-EO-02`, `GJ-03-EO-03`, `GJ-03-EO-04`, `GJ-03-EO-05`, `GJ-03-EO-08`, `GJ-03-FC-01`, `GJ-03-FC-02`, `GJ-03-FC-03`, `GJ-03-FC-04` |
| `GJ-04` | `GJ-03` | 6 | `GJ-03-EO-06`, `GJ-03-EO-07`, `GJ-03-EO-09`, `GJ-03-EO-10`, `GJ-03-FC-05`, `GJ-03-FC-06` |
| `GJ-05` | `GJ-04` | 10 | `GJ-04-EO-01`, `GJ-04-EO-02`, `GJ-04-EO-03`, `GJ-04-EO-04`, `GJ-04-EO-05`, `GJ-04-EO-10`, `GJ-04-FC-01`, `GJ-04-FC-02`, `GJ-04-FC-03`, `GJ-04-FC-05` |
| `GJ-06` | `GJ-04` | 4 | `GJ-04-EO-06`, `GJ-04-EO-07`, `GJ-04-EO-08`, `GJ-04-FC-04` |
| `GJ-07` | `GJ-02` | 10 | `GJ-02-EO-08`, `GJ-02-EO-09`, `GJ-02-EO-10`, `GJ-02-FC-05`, `GJ-02-FC-06`, `GJ-02-FC-07`, `GJ-02-FC-08`, `GJ-02-FC-09`, `GJ-02-FC-10`, `GJ-02-FC-11` |
| `GJ-08` | `GJ-05` | 6 | `GJ-05-EO-01`, `GJ-05-EO-02`, `GJ-05-EO-06`, `GJ-05-FC-01`, `GJ-05-FC-02`, `GJ-05-FC-03` |
| `GJ-09` | `GJ-05` | 7 | `GJ-05-EO-03`, `GJ-05-EO-04`, `GJ-05-EO-05`, `GJ-05-EO-12`, `GJ-05-EO-13`, `GJ-05-FC-04`, `GJ-05-FC-09` |
| `GJ-10` | `GJ-05` | 7 | `GJ-05-EO-07`, `GJ-05-EO-08`, `GJ-05-EO-09`, `GJ-05-EO-14`, `GJ-05-FC-05`, `GJ-05-FC-06`, `GJ-05-FC-07` |
| `GJ-11` | `GJ-05` | 3 | `GJ-05-EO-10`, `GJ-05-EO-11`, `GJ-05-FC-08` |

The identifiers above are the complete assertion set of the five journeys minus the
three `TSA-01` graphic-scope items `GJ-04-EO-09`, `GJ-04-EO-11` and `GJ-04-FC-06`,
which belong to the additive annotation rather than to any inventory candidate.

### 3.2 Declared invariants and how the composition changed

The counts exist in exactly one place: `assertion_invariants` in
[selection.json](selection.json). This section quotes that record and states no
independent number. The gate in section 8 recomputes every field of it from the
manifests and pins the accepted totals as literals, so a count that drifts from the tree
fails the gate instead of surviving in prose, and a deliberate change has to be made in
the record, in this section and in the gate together.

| Invariant | Value |
|---|---|
| `total_assertions` | 95 |
| `inventory_mapped_assertions` | 92 |
| `target_scope_annotation_assertions` | 3 |
| Per journey | `GJ-01` 15, `GJ-02` 24, `GJ-03` 16, `GJ-04` 17, `GJ-05` 23 |

`total_assertions` counts every `expected_outputs` and `failure_cases` entry across the
five manifests. The eleven inventory lists and the `TSA-01` list partition that set, so
`inventory_mapped_assertions` plus `target_scope_annotation_assertions` equals
`total_assertions`.

The composition changed once, in round 3, and
`assertion_invariants.revision_history` records it:

| Round | Total | Inventory-mapped | `TSA-01` | Change |
|---|---|---|---|---|
| 2 | 91 | 88 | 3 | Composition the second independent pass worked from. |
| 3 | 95 | 92 | 3 | Four assertions added: `GJ-01-EO-08`, `GJ-02-EO-12`, `GJ-02-EO-13`, `GJ-02-FC-11`. Nothing removed, no candidate re-mapped. |
| 4 | 95 | 92 | 3 | No assertion added, removed or re-mapped; the invariants are restated officially and made machine-checked. |

Round 3 added those four to close defects the second pass had found, and their origin
is not uniform, so it is recorded per assertion rather than for the set. `GJ-01-EO-08`
records the two different ingest extension sets and the lowercased companion-suffix
rule, `GJ-02-EO-12` records that the legacy skip whitelist contains `findings_merge`,
and `GJ-02-FC-11` records the second archive-incompleteness path; these three are
derived from the frozen legacy commit and carry `legacy_evidence_refs` resolvable
there. `GJ-02-EO-13` is derived from no legacy commit at all: it keeps the target
skippability statement separate from the opposite observation in `GJ-02-EO-12`, and its
value comes from one field of the unfrozen analysis-lane stage registry that `PD-02`
makes authoritative, as section 6.1 records. They are kept rather than folded back
because each closes a real defect. What round 3 failed to do was restate the
invariants, which is the divergence the third pass rejected.

The one copy that sat outside this task's allowed paths is closed:
`docs/program/CURRENT_STATE.md` described this lane as `91 assertions`, and the program
integrator brought that line to `95 assertions (92 inventory-mapped plus 3 under
TSA-01)` on 2026-09-01, pointing at `assertion_invariants` here as the single source to
quote rather than to duplicate. No document is known to carry a stale count now. The
round-2 row of `revision_history` keeps the 91-to-95 history, which stays useful; it
records a past composition, not a live divergence.

The gate in section 8 enforces, mechanically:

- exactly the eleven inventory candidates, in inventory order;
- a non-empty assertion list for every one of them;
- every listed identifier actually declared in the manifest of the mapped journey;
- each row's journey identical to the fan-in map in `journeys[].inventory_candidates`;
- the eleven lists and the `TSA-01` list pairwise disjoint and jointly equal to every
  declared assertion, so no assertion is counted twice and none is orphaned.

## 4. Why these five groupings

- `GJ-01` stands alone because ingest identity, fingerprint duplication and version
  isolation are the entry invariants every later journey depends on.
- `GJ-02` folds export into the run because the observed export completeness risk is
  only reachable from a finished run, and both halves share one pipeline state.
- `GJ-03` folds decision correction and revocation into the carryover rerun because
  the legacy overwrite and delete behavior is what makes the rerun result ambiguous;
  splitting them would hide the contradiction that `PD-01` resolves.
- `GJ-04` folds repair and undo into the comparison reuse journey because repair
  changes exactly the signature inputs that drive stale invalidation and recompute.
- `GJ-05` folds all four distributed candidates because outbox sequence, attempt
  authority, crash recovery and route exposure are one protocol surface; asserting
  them separately would allow contradictory authority assumptions.

## 5. Provenance classes

| Class | Meaning | `parity_oracle` | Downstream use |
|---|---|---|---|
| `legacy_observed` | Source-observed behavior at the pinned legacy commit, backed by at least one resolvable evidence reference | `true` | Parity oracle evidence |
| `greenfield_target` | Intended target behavior justified by repository rules or principles, diverging from legacy | `false` | Design input; never parity |
| `pending_owner_decision` | Depends on an owner decision that is not approved | `false` | Blocked; never parity, never a frozen semantic |

After the 2026-09-01 disposition no item in this selection carries
`pending_owner_decision`; the class stays defined because a later decision may be
reopened or a new one raised, and a blocked expectation must never be parked in one of
the other two classes.

`legacy_observed` never means runtime-verified. It means observed in the immutable
committed source. Success, timing, rendering, provider availability and concurrency
outcomes remain unverified because nothing was executed.

### 5.1 Observation and target must not be substituted for one another

Two pairs in this selection state opposite things about the same subject on purpose, and
a correction to one must never be applied to the other:

- `GJ-02-EO-12` records that the legacy skip whitelist contains `findings_merge`, so
  legacy accepts a skip of the merge stage. It is `legacy_observed` with
  `parity_oracle: true`. `GJ-02-EO-13` reports the opposite target value from the
  authoritative stage registry, where
  `stages[stage_id=finding_merge].status_policy.skip_allowed` is `false`. It is
  `greenfield_target` with `parity_oracle: false`, it states no rule in this lane's own
  name and it claims no owner decision; its `authority` block names the registry, the
  contract version it was read at and the fact that the registry is an unfrozen
  candidate. Section 6.1 records why that is a registry value and not an owner
  decision.
- `GJ-05-EO-12` records the bounded legacy absence of a run entity and of a dedicated
  authority field. `GJ-05-EO-13` and `GJ-05-FC-09` state the target run/job/attempt
  separation and `execution_token` authority. The first is parity evidence, the others
  are not.

## 6. Owner decisions carried by this selection

Disposition recorded on 2026-09-01 by the repository owner, received as a direct owner
instruction in the W0.2 integrator session. The machine-readable record is
`owner_decisions` in [selection.json](selection.json), where every non-pending status
must carry the decision date, the authority, the source and the retagged assertions.

| Decision | Disposition | Retagged assertions |
|---|---|---|
| `PD-01` | `approved_with_modification` | `GJ-03-EO-09`, `GJ-03-FC-06` |
| `PD-02` | `approved_with_modification` | `GJ-02-EO-11` |
| `PD-03` | `approved_with_modification` | `GJ-05-EO-13`, `GJ-05-FC-09` |
| `PD-04` | `approved` | `GJ-04-EO-11` |

The three modifications, restated as this lane applied them:

- `PD-01`: decisions are append-only and a correction or a revocation each create a new
  decision identifier, so the history stays readable. A revocation moves the current
  projection to `pending`; it does not automatically restore the verdict that preceded
  the revoked decision, and no substitute verdict is derived.
- `PD-02`: the single versioned stage registry is authoritative, but it is accepted only
  together with a name-level alias map produced by the analysis lane. This lane
  therefore keeps the legacy public name `findings_merge` in
  [GJ-02/inputs/run_plan.json](GJ-02/inputs/run_plan.json) and marks every stage string
  there as a legacy public name under `stage_name_authority`. The fixture resolves no
  canonical stage identifier; renaming it here would pre-empt the alias map.
- `PD-03`: an audit run is created only when a top-level audit or re-audit command is
  accepted for a frozen set of inputs and configuration, and the same idempotency key
  with the same payload returns the existing run. Retry, resume, restart and worker
  failover create no run: they open a new attempt under the same job. A terminal run is
  never reopened.

All six retagged items are `greenfield_target` with `parity_oracle: false`. An approved
decision makes a target statement legitimate; it does not turn the target into legacy
evidence. The legacy observations these targets diverge from are unchanged and remain
`legacy_observed` with `parity_oracle: true`: `GJ-03-EO-06` and `GJ-03-EO-07` for the
in-place replacement and deletion behavior, `GJ-04-EO-09` for the observed absence of
graphic comparison, and `GJ-05-EO-12` for the bounded absence of a run entity and of any
dedicated attempt-authority field. `GJ-05-EO-12` describes what legacy actually carries —
the attempt disposition, an attempt-scoped execution token persisted only as its hash, and
the connection epoch — and names no target field. The canonical target name is fixed
separately by integration decision `ID-02` as `execution_token`, where fencing is a
property of the behavior and not a field name or a promise of a monotonic number; the
`greenfield_target` items `GJ-05-EO-13` and `GJ-05-FC-09` use that name and only that
name.

`PD-04` keeps every graphic and vector statement out of the fan-in map: its assertions
are carried by annotation `TSA-01`, whose first contractual inclusion is recorded as
`W7` with a separate golden graphic pair. Nothing graphic exists in this wave.

### 6.1 Values reported from the stage registry, not decided here

`GJ-02-EO-13` is a target statement whose value this lane does not own. The repository
owner disposed of `PD-02` — the single versioned stage registry is the authoritative
source of target stage semantics — and disposed of nothing about merge skippability. The
expectation therefore reports the registry field instead of asserting a rule:

| Field | Value |
|---|---|
| Source | [contracts/analysis/v1/stage-registry.json](../../contracts/analysis/v1/stage-registry.json) |
| Contract | `auditmanager.analysis.stage_registry` version `1.0.0-draft.1`, status `candidate` |
| Selector | `stages[stage_id=finding_merge].status_policy.skip_allowed` |
| Value | `false` |
| Freeze status | Unfrozen candidate owned by the analysis lane |

The manifest carries this as an `authority` block on the expectation, distinct from
`legacy_evidence_refs`, which only ever holds locators resolvable at the pinned legacy
commit, and distinct from `owner_decision_ref`, which this expectation does not set
because no owner decision about merge skippability exists. The file was read once, for
this reference only, under the program integrator's lane exception of 2026-09-01, which
lifted this lane's earlier no-cross-lane-draft rule for that single file precisely
because `PD-02` made the registry authoritative. Because the registry is not frozen, a
change to that field re-derives `GJ-02-EO-13`; the expectation is never defended against
its own source. The legacy observation `GJ-02-EO-12` is untouched by any of this and
keeps `parity_oracle: true`.

## 7. Sensitive-data exclusions

The same exclusion list is recorded in every manifest:

- legacy `.env`, `.env.example` and every credential-shaped file — never opened;
- `audit_worker/providers/openrouter_secret.py` — metadata-only and excluded by the
  accepted inventory; no value was accessed or copied here;
- production or customer PDF, Markdown, recognized-JSON and Excel payloads — replaced
  by declarative surrogates and text stand-ins;
- live provider prompts, model responses, endpoints and account identifiers — only
  outcome shapes are replayed;
- mutable legacy checkout files, untracked paths, databases and generated results —
  only immutable Git objects at the pinned commit are admissible.

## 8. Recompute and verification commands

Re-running selection rewrites the same stable files and recomputes the declared
checksums. Reviewers can verify the declared values without regenerating anything:

```bash
# manifest checksums declared in selection.json
python3 -c "import json,hashlib;from pathlib import Path;r=Path('fixtures/golden');s=json.loads((r/'selection.json').read_text());print(all(hashlib.sha256((r/x['journey_id']/'manifest.json').read_bytes()).hexdigest()==x['manifest_sha256'] for x in s['journeys']))"

# input artifact checksums and sizes declared in each manifest
python3 -c "import json,hashlib;from pathlib import Path;r=Path('fixtures/golden');ok=True
for j in ('GJ-01','GJ-02','GJ-03','GJ-04','GJ-05'):
    m=json.loads((r/j/'manifest.json').read_text())
    for a in m['input_manifest']['artifacts']:
        b=Path(a['path']).read_bytes()
        ok=ok and hashlib.sha256(b).hexdigest()==a['sha256'] and len(b)==a['size_bytes']
print(ok)"
```

Both commands print `True` when the tree is consistent.

The third command is the acceptance gate for the assertion-level coverage map of
section 3.1 and for the declared invariants of section 3.2. It fails if an inventory
candidate is missing, if any candidate maps to an empty list, if a listed identifier is
not declared in the mapped manifest, if a row disagrees with the fan-in map, if the
lists overlap or leave an assertion unmapped, or if any declared count disagrees with
the manifests or with the accepted totals:

```bash
# inventory candidate -> assertion coverage
python3 -c "import json;from pathlib import Path;r=Path('fixtures/golden')
s=json.loads((r/'selection.json').read_text())
rows=s['inventory_assertion_coverage']
assert [x['inventory_candidate'] for x in rows]==[f'GJ-{n:02d}' for n in range(1,12)]
fan={c:j['journey_id'] for j in s['journeys'] for c in j['inventory_candidates']}
declared={}
for j in [x['journey_id'] for x in s['journeys']]:
    m=json.loads((r/j/'manifest.json').read_text())
    declared[j]={e['id'] for e in m['expected_outputs']}|{f['id'] for f in m['failure_cases']}
seen=[]
for x in rows:
    a=x['assertion_ids']
    assert a and fan[x['inventory_candidate']]==x['selected_journey'], x['inventory_candidate']
    assert all(i in declared[x['selected_journey']] for i in a), x['inventory_candidate']
    seen+=a
for x in s['target_scope_annotations']:
    a=x['assertion_ids']
    assert a and all(i in declared[i[:5]] for i in a), x['annotation_id']
    seen+=a
assert len(seen)==len(set(seen)) and set(seen)==set().union(*declared.values())
inv=s['assertion_invariants']
per={j:len(v) for j,v in declared.items()}
mapped=sum(len(x['assertion_ids']) for x in rows)
tsa=sum(len(x['assertion_ids']) for x in s['target_scope_annotations'])
assert inv['per_journey_assertions']==per, per
assert inv['inventory_mapped_assertions']==mapped==92, mapped
assert inv['target_scope_annotation_assertions']==tsa==3, tsa
assert inv['total_assertions']==mapped+tsa==len(set(seen))==95, len(set(seen))
assert inv['revision_history'][-1]['total_assertions']==inv['total_assertions']
print('U-05 PASS:',len(rows),'inventory candidates mapped to',mapped,'assertions;',inv['total_assertions'],'declared in total')"
```

It prints one `U-05 PASS` line and exits `0` when the coverage map and the declared
invariants both hold.

## 9. Independent review checklist

1. Resolve each manifest's `provenance.evidence` entries against the immutable legacy
   commit. The locator grammar is the one accepted by `W0-EVD-01`: `symbol@line` names
   the literal symbol at its definition line, and `lines@start-end` and
   `module@start-end` identify an evidence region that must contain the claim.
2. Confirm every `legacy_observed` item has at least one such reference and that no
   `greenfield_target` or `pending_owner_decision` item claims parity.
3. Confirm the fan-in map is complete and injective against the accepted inventory, and
   run the coverage gate in section 8 so each inventory candidate resolves to existing
   assertions rather than to a journey identifier alone and every declared count in
   section 3.2 matches the manifests.
4. Confirm no committed byte in `fixtures/golden/` is production, customer, credential
   or provider-response material.
5. Confirm each owner decision carries the disposition recorded in section 6 with its
   date, authority and source, that the six retagged items are `greenfield_target` with
   `parity_oracle: false`, and that the legacy observations they diverge from are
   untouched.
6. Confirm that `GJ-02-EO-13` reports the stage-registry field named in section 6.1,
   that its `authority` block matches the registry as it stands, and that it claims no
   owner decision and no legacy evidence. Confirm the same separation on the download
   guard: `GJ-02-EO-08` and `GJ-02-FC-09` record the observed order — 404 before any
   containment check, 403 only for an existing path, and a string-prefix comparison —
   as `legacy_observed`, without proposing a fix.
