# ADR-0019: Decision-to-code navigation for human and AI agents

- Status: proposed
- Date: 2026-09-09; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: post-CP-00 prototype extension, not covered by the CP-00 disposition; to be accepted with the detailed P02–P05 plan; principle P-23 (`docs/architecture/ARCHITECTURE_BIBLE.md`)

## Context
Architecture decisions, owner rulings, frozen contracts, task ownership, implementation files and acceptance tests live in different repository areas. A capable agent can find them by broad search, but it cannot cheaply determine which record is current, which code implements it, or which test proves it. Re-reading the entire repository wastes context; guessing from filenames, line numbers or semantic search risks applying superseded policy. The layer must improve navigation without becoming another source of architectural truth or a shared file that every parallel task edits.

## Decision
Create a repository-native, rebuildable navigation layer with these rules:

1. ADRs, owner decisions, frozen contracts, accepted task records, code and tests retain their existing authority. Navigation entries point to them and never override them.
2. The machine source is a set of independently owned fragments under `docs/navigation/entries/<entry_id>.json`, validated by one versioned schema. One task or bounded-context owner writes one fragment; parallel tasks do not edit a shared map.
3. An entry records at least: stable entry ID, lifecycle status, bounded scope, owning task/context, decision references, contract references, implementation file paths and public symbols, runtime entrypoints, test/evidence references, supersession links and known gaps. Planned paths are labelled planned and cannot masquerade as implemented.
4. File paths plus public symbol names are stable locators. Line numbers may be shown for convenience but are never the sole identity of an implementation or decision.
5. A generated `docs/navigation/INDEX.md` provides both views: decision → implementation and implementation path/context → decisions/contracts/tests. Only the integration owner writes generated aggregate output.
6. Each implemented bounded context has one short code-adjacent README linking its navigation entry, public seam, active ADRs/contracts and focused verification command. Per-file architecture comments are not required.
7. Validation checks unique IDs, schema conformance, reference existence, lifecycle and supersession consistency, path ownership and deterministic regeneration. Production code added or materially changed by P02+ is incomplete without its owned navigation fragment or an explicit `navigation_not_applicable` reason reviewed by the integrator.
8. AI agents read `CURRENT_STATE.md`, then the generated navigation index and the entries relevant to their task before inspecting implementation. The index narrows discovery; it does not replace reading the task, dependencies or frozen contracts.
9. No entry embeds a commit SHA that would have to identify the commit containing itself. Exact accepted commits stay in task/checkpoint handoffs and Git history.
10. The base layer may be authored in parallel with P01, but it is not a foundation gate. It becomes blocking before P02 fan-out, when product code and decision-to-code drift first become material.

## Consequences
- Positive: agents receive a deterministic starting point and spend less context on repository-wide searches; reviewers can detect orphan decisions, unproved implementations and code with unknown architectural ownership; parallelism stays viable because source fragments have disjoint writers.
- Cost: every implementation task carries a small maintenance cost for its navigation fragment; the layer can become stale, so validation and integration ownership are mandatory.

## Alternatives considered
1. A single hand-maintained Markdown matrix — rejected: simple initially, but a shared hotspot and difficult to validate or reverse-resolve.
2. ADR IDs in every source-file comment — rejected: noisy, incomplete for generated/indirect code and expensive during refactoring.
3. An embeddings/vector database as authority — rejected: nondeterministic, external and unable to distinguish active decisions from superseded text. Semantic search may be additive later, but only over the validated repository-native index.

## Verification
Decision 7 (the validator); Rollout 4 (field validation of agent search/rework failures).

## Rollout
1. `P0-PLN-01` defines one agent-ready implementation task and its ownership.
2. Before P02, create the schema, entry fragments, deterministic generator/validator, agent onboarding link and mappings for the accepted foundation.
3. Every P02+ implementation task owns its fragment; integration regenerates and checks the aggregate index.
4. Field validation measures agent search/rework failures before any richer graph or semantic-search service is considered.

## Revisit trigger
A richer graph or semantic-search service is considered only after the field validation of Rollout 4 has measured agent search/rework failures; semantic search stays additive over the validated index (Alternatives considered, 3).

## History
- 2026-09-09 — added as a post-CP-00 prototype extension, status `proposed prototype extension; accept with the detailed P02–P05 plan` (not part of the CP-00 disposition of ADR-0001…0018).
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); `Rejected alternatives` renamed to `Alternatives considered`; meaning unchanged.
