# ADR-0013: Comparison separates approved state, raw evidence and AI synthesis

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Automatic sheet matching produces rebuildable suggestions. User-approved links are owned state and survive recomputation. Deterministic text exclusions/diff and raw graphic evidence are immutable per comparison revision. AI review/synthesis is a derived artifact keyed by raw checksums. Repairs require proof, audit and undo.
