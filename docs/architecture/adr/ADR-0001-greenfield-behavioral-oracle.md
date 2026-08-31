# ADR-0001: Greenfield product; legacy is a behavioral oracle

- Status: accepted for bootstrap; ratify at CP-00
- Related principles: P-19

## Context
A working application exists, but its filesystem/JSON state, large frontend/orchestrator and duplicated stage semantics are precisely the technical debt the new product must avoid. The new repository starts empty.

## Decision
No runtime Strangler dependency is required. Legacy is read-only evidence source: characterization tests, anonymized fixtures, expected structural outputs and edge cases. New code may port an algorithm only after defining its contract and tests. Importing a large legacy service/router/pipeline manager as a shortcut is forbidden without a new ADR.

## Consequences
Business parity is proven deliberately rather than inherited accidentally. Initial discovery costs more, but architecture does not become coupled to old paths/state formats.
