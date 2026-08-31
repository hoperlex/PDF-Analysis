# ADR-0008: Execution engine is a package-contract boundary

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Engine consumes versioned `JobPackage` and produces validated `StageResult`/`ResultPackage`. It does not directly update canonical aggregates, switch current version or make expert/publication decisions. Local and remote engines implement the same contract.

A single versioned stage registry owns stage names, dependencies, contract versions and terminal semantics.
