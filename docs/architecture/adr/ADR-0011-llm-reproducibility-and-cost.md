# ADR-0011: LLM reproducibility and cost ledger

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Published runs reference immutable AnalysisProfile, PromptBundle and NormsSnapshot. Every provider call creates ModelCallRecord with model/provider/params, request/response checksums, provider ID when available, token usage, latency, status and measured/estimated cost. Replay tests use recorded synthetic/anonymized responses; live quality is evaluated semantically.
