# Current state

**Program state:** CP-00 discovery wave W0.1 accepted; all four W0.2 lanes have
produced candidates, the repository owner has recorded an explicit disposition for
`PD-01`–`PD-05` plus integration decisions `ID-01`–`ID-03`, and every lane has passed
independent review. The accepted candidates are awaiting their W0.2 integration
commit. Nothing is frozen, nothing is ratified, and production implementation remains
locked.

## Active checkpoint

Target: `CP-00 / v0.0.0-architecture`.

## Active wave

`W0.2 — golden baseline and architecture/domain contracts`.

Completed inputs:

- `W0-QA-00` — fail-closed bootstrap validator, commit
  `c25ff4a5393595260384aaffea1fddc2382189e8`;
- `W0-BHV-01` — accepted legacy capability inventory, commit
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`;
- `W0-DEP-01` — hash-locked bootstrap-validation dependencies, commit
  `ab1cfdab0ec5c413b188a44ff82a99586ecd7994`;
- `W0-EVD-01` — mechanically resolvable immutable evidence anchors, commit
  `134436502b7ee40ca9abb061e0080741a863ffda`;
- `W0-QA-02` — Git-aware validator hardening and real-schema regressions, commit
  `6c82004b35f49463c8e7fc8602fbced2f374167e`;
- canonical behavioral oracle — `32b9d903792b30506048a1d42b0e6b2d07aee403`;
- refactoring architecture source — `0b937dc0e24d38fb98485a920152b83d2f19c982`.

Lane candidates produced and independently accepted, pending integration:

- `W0-BHV-02` — five golden journeys, 95 assertions (92 inventory-mapped plus 3 under
  `TSA-01`), `inventory_assertion_coverage` mapping all eleven inventory candidates to
  concrete assertion IDs. The count is declared once, in
  `fixtures/golden/selection.json` → `assertion_invariants`, with a revision history;
  quote it from there rather than restating it;
- `W0-ARC-01` — CP-00 architecture review, owner decisions recorded
  (`review_status = owner_decisions_recorded`, `ratified = false`);
- `W0-DOM-01` — domain `1.0.0-draft.1`. The candidate revision advances every
  remediation round and is deliberately not restated here; read it from
  `contracts/domain/v1/*.json` → `candidate_revision`, where the three catalogs and
  their schema `const` pins hold it as one value;
- `W0-ANA-01` — analysis `1.0.0-draft.1` with a name-level legacy alias map.

See `docs/program/waves/W0.2_architecture_domain_contract.md`.

## Owner decisions of record

Recorded 2026-09-01 by the repository owner in
`docs/architecture/CP00_OWNER_DECISIONS.md`:

- `PD-01` approved with modification — expert decisions are append-only; revocation
  moves the projection to `pending` and restores no earlier verdict. Closes `OQ-03`.
- `PD-02` approved with modification — one authoritative stage registry, conditional
  on a name-level alias map.
- `PD-03` approved with modification — `AuditRun`, `Job` and `Attempt` are distinct,
  with an explicit Run-creation rule; retry/resume/restart/failover create a new
  Attempt, never a new Run.
- `PD-04` approved — graphic/vector comparison is future scope, first contractual
  inclusion in W7.
- `ID-01` canonical machine-contract version key is `contract_version`.
- `ID-02` canonical token name is `execution_token`.
- `ID-03` the 25/2/3/1 declaration distribution was conditionally accepted; its
  condition is satisfied by the independent ANA review of all nine registry stages,
  all 31 alias-bearing sites and all 293 immutable evidence locators.
- `PD-05` approved — `optimization`, `optimization_critic`, `optimization_corrector`
  and `optimization_review` form a separate project-optimization sub-pipeline whose
  product is improvement proposals, not audit findings; section optimization is a
  downstream aggregation/replication pipeline, not the same one. The four names leave
  the nine-stage core registry. The capability is not orphaned: `U-06` assigned it to
  a separate Project Optimization bounded context — see the open-items section. The
  identifier `PD-05` was assigned by the analysis lane and confirmed by the program
  integrator on 2026-09-01; no renumbering is required.
- `PD-03` precedence, confirmed 2026-09-01 — the same idempotency key with the same
  payload always returns the original Run; a repeat of a terminal Run creates a new
  Run only under a new idempotency key. This resolves the overlap between the two
  rules without changing either, and both consuming families must reflect it.

- `U-06` resolved 2026-09-01 — Project Optimization is a separate bounded context
  under `contracts/optimization/v1/**`, owned by a dedicated OPT contract owner who is
  neither the ANA nor the DOM lane, planned as `W5-OPT-01` after the core audit and
  decision-contract freeze. Two binding obligations hold until that task is accepted:
  the capability stays disabled and no lane may model it, and CP-00 explicitly
  excludes its runtime semantics. `FS-04` is split three ways with a named owner for
  each part, so no part is left without an encoder.

## Independent review of record

| Pass | `W0-ARC-01` | `W0-DOM-01` | `W0-BHV-02` | `W0-ANA-01` |
|---|---|---|---|---|
| 1 | accept (candidate) | accept (candidate) | reject | reject |
| 2 | accept | accept | reject — 4 blockers | reject — 2 blockers |
| 3 | accept | reject — 1 blocker | reject — 1 blocker | reject — 3 blockers |
| 4 | **accept** | **accept** | **accept** | reject — 1 blocker |
| 5 | not re-run | not re-run | not re-run | **accept** |

Every blocker raised in passes 1–3 has been remediated. Pass 4 accepted three lanes
and raised one new machine blocker in `W0-ANA-01`: the schema pinned the full
outcome tuple of the nine run-lifecycle triggers but never pinned `rule_id` itself, so
`RC-02` and `RC-05` could be renamed, swapped or duplicated while
`trigger_precedence` kept naming them — a swap would have inverted the precedence
silently and left the contract valid. Pass 5 independently accepted the narrow ANA
remediation: the owning schema now rejects renaming either rule, swapping or
duplicating them, and rotating all nine `rule_id` values. The reviewer re-executed the
documented Gates A–D and confirmed the intended split between schema-level identity
checks and cross-artifact gates. The other three lanes were deliberately not re-run.

Alongside the lane work, three task-layer rounds corrected defects in the follow-up
task specifications themselves — an impossible ADR-supersede slot, a gate that
depended on the ambient interpreter lacking `jsonschema`, a repository sweep blind to
schema-declared keys, and a contradiction over `candidate_revision`.

Two verification lessons are worth carrying into later waves. A mutation probe proves
only what it mutates: the outcome tuple looked protected for a full round while
`creates_attempt` and then `rule_id` stayed unpinned underneath it. And a gate that
cannot be copied and executed as written proves nothing — one lane's Gate D died on
shell expansion of `$defs` inside `python -c "…"`, so its earlier reported passes
could not have been produced by the documented command.

No lane is accepted on the strength of its own remediation, and the integrator does
not review lanes it coordinated.

## Open before any freeze

- `U-04` — tenant/IdP boundary required before `W2-C-01`; TTL and legal hold before
  `W9-C-01`. Keeps `ADR-0014` at `proposed` and blocks every retention value.
- `OQ-02` lease/heartbeat/grace values; `OQ-04` retry budget and backoff.
- Several identity holes that predated the final ANA blocker were closed in the same
  round, but at the **gate** layer rather than the schema layer —
  swapping two `stage_id`s, renaming `XS-02`, swapping `XS-02` with `XS-03`. Verified:
  the schema accepts all three, Gate C rejects all three. Gate-layer defence is
  equivalent to schema-layer defence only while the gate runs as documented, which is
  why a gate that cannot be copied and executed is worth treating as absent.
- One residue is documented rather than closed: re-pointing a legacy stage name from
  one existing registry stage to another passes every check, because the reference
  resolves and the target's identity is pinned. That is mapping judgment, not
  referential integrity, and catching it would mean restating all 62 name-resolution
  decisions (29 canonical-stage mappings and 33 exclusions) inside the gate. The
  complete map is therefore part of the candidate contract set and any later remap is
  a semantic freeze-break requiring independent review.
- `GJ-02-EO-13` rests on an unfrozen candidate: `finding_merge.status_policy
  .skip_allowed` in the analysis registry. No owner decision exists on merge
  skippability, so the expectation carries no `owner_decision_ref`. If the analysis
  lane changes that field, the expectation is re-derived, never defended.
- A legacy defect is now recorded as observed fact and must not drift into a target
  rule: the export download guard compares resolved paths with `str.startswith` and
  no component boundary, so a sibling directory sharing the base prefix is served.
- `W0-QA-03` must teach the validator to read `contract_version` before the domain
  family can drop its deprecated bare `version` mirror; `W0-EVT-01` then follows.
- `W0-ARC-02` specifies architecture lint rules before CP-00.

## Allowed work before CP-00

- read-only legacy inventory;
- domain glossary/capability inventory;
- synthetic/anonymized fixture extraction;
- contract drafts/examples;
- Architecture Bible/ADR review;
- spikes that do not create irreversible production dependency.

## Prohibited before CP-00

- domain production implementation based on unresolved identity/state contracts;
- importing legacy services as new architecture;
- selecting irreversible vendor/retention/security policy without owner decision.

## Next integration tasks

Record the accepted W0.2 candidate set in one integration commit. Then open W0.3 and
run `W0-ARC-02` plus the serial `ID-01` chain `W0-QA-03` → `W0-DOM-02` →
`W0-EVT-01`, followed by the independent cross-family QA task and CP-00 integration
runbook. Do not record a contract or checkpoint freeze until those tasks and the
manual CP-00 acceptance are complete.

`U-04` does **not** block a CP-00 contract freeze. Its owner disposition sets its own
deadlines — tenant/IdP before `W2-C-01`, TTL and legal hold before `W9-C-01` — which
would be meaningless if CP-00 required it closed first. What `U-04` blocks is exact
and bounded: `ADR-0014` stays `proposed`, the retention and legal-hold clauses of
`ADR-0015` and the classification obligations of `P-13` stay unratified, and no
tenant, IdP, TTL, retention or legal-hold value may appear in any contract. A freeze
recorded while `U-04` is open must state that it excludes those.

Owner decisions being recorded is not ratification: CP-00 ratification remains W0.3.
