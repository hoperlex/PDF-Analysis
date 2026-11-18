# ADR-0011: LLM reproducibility and cost ledger

- Status: accepted
- Date: 2026-08-31; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: CP-00 (W0-ARC-01) disposition: ratify (`docs/architecture/CP00_ARCHITECTURE_REVIEW.md` §5; the review is not the ratification act); principles P-15, P-16; input `U-01`

## Context
The legacy application records token/cost/usage and budget (`AN-09`), but cost observability does not establish replayability; replay and cost accounting are only partly supported (CP-00 review §5).

## Decision
Published runs reference immutable AnalysisProfile, PromptBundle and NormsSnapshot. Every provider call creates ModelCallRecord with model/provider/params, request/response checksums, provider ID when available, token usage, latency, status and measured/estimated cost. Replay tests use recorded synthetic/anonymized responses; live quality is evaluated semantically.

## Consequences
- Positive: replay parity requires repository-approved synthetic recordings (CP-00 review §5).
- Cost: budget thresholds are separate and unset (`U-01`): numeric cost thresholds are deferred to `W3-C-01` and must be defined before the first paid-provider canary; CP-00 fixes the measurement, not the numbers.

## Verification
Replay tests against recorded synthetic/anonymized responses; live quality evaluated semantically (Decision).

## History
- 2026-08-31 — bootstrap baseline, status `accepted for bootstrap; ratify at CP-00`.
- 2026-09-01 — CP-00 disposition recorded: ratify (W0-ARC-01; status text unchanged); `U-01` deferred with a deadline.
- 2026-11-18 — unified to the template (`ADR-OPTIMISE-01`); meaning unchanged.
- 2026-09-07 — CP-00 ratified (acceptance round ten, tag `v0.0.0-architecture`); status `accepted` from then (`E-05` stays open).
