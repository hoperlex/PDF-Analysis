# Golden fixtures

Golden journeys characterize business semantics from legacy without copying production data. Each fixture must record the full `legacy_source_commit` from [docs/SOURCE_TRACEABILITY.md](../../docs/SOURCE_TRACEABILITY.md), source behavior, anonymization/synthesis method, expected structural result and whether comparison is exact, semantic or replay-based.

## Selected-set convention

`W0-BHV-02` fixes exactly one selected set. It is described by three machine-readable
artifacts and two review documents:

| Artifact | Role |
|---|---|
| [selection.json](selection.json) | The ordered selected set, the lossless inventory fan-in map, the inventory-candidate to assertion coverage map, the declared assertion invariants with their revision history, and the recorded owner decisions. |
| [selection.schema.json](selection.schema.json) | Structural schema of the selected set; it pins the order, the count and each fan-in list. |
| [journey-manifest.schema.json](journey-manifest.schema.json) | Structural schema of one journey manifest. |
| [SELECTION.md](SELECTION.md) | Human review of the selection, the fan-in rationale and the recompute commands. |
| [EDGE_CASE_MATRIX.md](EDGE_CASE_MATRIX.md) | Edge and failure coverage across the selected journeys. |

Rules of the convention:

1. **Two namespaces.** Inventory characterization candidates `GJ-01`…`GJ-11` in
   [docs/behavior/legacy_capability_inventory.md](../../docs/behavior/legacy_capability_inventory.md)
   are not the selected journey identifiers. `inventory_candidates` inside
   `selection.json` is the normative fan-in map: every inventory candidate appears
   exactly once and none is dropped. `inventory_assertion_coverage` resolves that map
   one level further, from each inventory candidate to the concrete `*-EO-NN` and
   `*-FC-NN` identifiers that characterize it, so an aggregate journey cannot absorb a
   candidate without asserting anything about it.
2. **Stable identifiers and layout.** The selected set is exactly `GJ-01`…`GJ-05`.
   Each one owns a directory `fixtures/golden/<journey_id>/` with a `manifest.json`
   and an `inputs/` directory. Re-running selection updates those same files and
   recomputes the declared checksums; it never adds a duplicate identifier or a
   duplicate directory.
3. **Provenance is immutable.** Every manifest carries the full legacy commit and at
   least one evidence item whose `source_ref` starts with that commit followed by
   `:`. A moving branch name is never an evidence anchor.
4. **Three provenance classes.** Every expectation and every failure case is tagged
   `legacy_observed`, `greenfield_target` or `pending_owner_decision`. Only
   `legacy_observed` items carry `parity_oracle: true` and may be used as parity
   evidence. A target divergence is never presented as parity, and an owner decision
   that approves a divergence promotes it from `pending_owner_decision` to
   `greenfield_target` only: it never turns it into legacy evidence and never rewrites
   the legacy observation it diverges from.
5. **Synthetic only.** No production or customer document, payload, model response,
   credential or environment value enters this tree. Binary source documents are
   represented by declarative surrogates and text stand-ins.
6. **Owner decisions are recorded, not inferred.** `owner_decisions` in
   `selection.json` carries an enumerated status. Any status other than
   `pending_owner_approval` must additionally carry the decision date, the deciding
   authority, the source of the disposition and the assertions it retags, so a
   disposition cannot be flipped silently or into a free-form state.
7. **Provider material is minimal.** Where a journey needs a provider interaction it
   uses a small deterministic stub recording outcome shapes only, declared under
   `determinism.replay_material` and marked as reviewed for sensitive content. Live
   model text is never asserted to be byte-stable.
8. **Counts are declared once.** `assertion_invariants` in `selection.json` is the only
   place where the assertion totals of the selected set exist. `SELECTION.md` and this
   file quote them and state no independent number, the coverage gate in `SELECTION.md`
   section 8 recomputes them from the manifests and pins the accepted totals, and
   `assertion_invariants.revision_history` records every round in which the composition
   changed, what was added or removed and why. A total that appears in two places with
   two values is a defect, not a rounding difference.
9. **A target value is reported, never invented.** When a `greenfield_target` statement
   carries a value that belongs to another authoritative artifact, the expectation adds
   an `authority` block naming that artifact, its contract version, the selector, the
   value and its freeze status, and it says explicitly that the value is neither an owner
   decision nor a legacy observation. `owner_decision_ref` is set only when an owner
   actually disposed of that rule, and `legacy_evidence_refs` stays reserved for locators
   resolvable at the pinned legacy commit.

## Directory layout

```text
fixtures/golden/
  README.md
  SELECTION.md
  EDGE_CASE_MATRIX.md
  selection.json
  selection.schema.json
  journey-manifest.schema.json
  GJ-01/ manifest.json  inputs/
  GJ-02/ manifest.json  inputs/
  GJ-03/ manifest.json  inputs/
  GJ-04/ manifest.json  inputs/
  GJ-05/ manifest.json  inputs/
```

Selected journeys: [GJ-01](GJ-01/manifest.json), [GJ-02](GJ-02/manifest.json),
[GJ-03](GJ-03/manifest.json), [GJ-04](GJ-04/manifest.json) and
[GJ-05](GJ-05/manifest.json).
