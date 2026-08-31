# ADR-0003: Contract-first boundaries and single data owner

- Status: accepted for bootstrap; ratify at CP-00
- Related principles: P-04

## Decision
Every independently changing boundary is versioned by OpenAPI, JSON Schema, SQL migration or equivalent machine schema. One aggregate/entity has one authoritative writer. Parallel implementation starts only after shared contract freeze.

## Consequence
Agents can work concurrently against stable interfaces; integration conflicts become explicit contract changes rather than hidden drift.
