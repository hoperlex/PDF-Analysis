# `comparison` boundary

Comparison revisions, sheet suggestions/approved links, deterministic evidence, derived AI/graphic layers.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.

Other contexts use `public.py` only. `W59-VERSION-COMPARE-01` serves a read-only comparison of
two versions of one set through `service.VersionComparisonService`: its two ports
(`VersionClassificationReader`, `VersionAnalysisReader`) are adapted by the composition root,
and its read model (`read_model.py`) holds proposals only — no SheetLink, finding match,
decision or AI artifact is written. The approved-link modules (`raw_text.diff_approved_pairs`,
`raw_evidence_seal`, `summary_input`, `decision_carryover`) stay for the later persisted
comparison.
