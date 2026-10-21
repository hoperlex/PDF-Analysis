# W57B-INT-REFERENCE-PIPELINE-PREP-01 — result

## Result

`run_reference_pipeline` composes the existing canonical catalogue adapter,
page-local extraction, five-outcome resolution and PDF-text observation plan.
The caller passes one tuple of `ReferencePage` objects. The pipeline derives
extraction pages from that same tuple, so the report and global evidence spans
cannot drift between two separately supplied text sources. It returns all
resolved references and only the newer-edition candidates.

The new test exercises `NEWER`, `PRESENT`, `OLDER`, `ABSENT` and `UNPARSED`
outcomes together, repeats a newer citation on a second page, and preserves
an unread page in the report. It checks exact global quote offsets and refusal
of wrong catalogue facts, an unreviewed slug listing, duplicate labels,
unordered page numbers, noncontiguous offsets and invalid text.

## Verification

- Focused pipeline/catalogue/resolution/observation suite: **47 passed**.
- Compilation of the two new Python files: passed.
- Direct task governance: `[]`.
- `git diff --check`: passed.
- Exact owned-path check: the four files below are the only files written by
  this lane; concurrent work in other paths belongs to other lanes.
- PostgreSQL/custody, PDF source authentication, full `make gate` and beta
  acceptance: deferred under R-135 and outside this pure task.

## Changed files

- `src/auditmanager/norms/references/pipeline.py`
- `tests/integration/norms/references/test_reference_pipeline.py`
- `docs/program/tasks/W57B-INT-REFERENCE-PIPELINE-PREP-01.md`
- `docs/program/W57B-INT-REFERENCE-PIPELINE-PREP-01.md`

## Contracts, risks and integration

No frozen contract, migration or public API changed. The additive internal
`ReferencePipelineResult` contains `report` and `newer_candidates`; its input
requires independently obtained `CatalogueExpectation` and a reviewed
`listed_unparsed_slugs` tuple. The function validates those supplied facts
against bytes but cannot establish their origin, a qualified snapshot, a
confirmed custody binding, or the authenticity of caller-supplied PDF text.

The runtime owner should call it only after the verified-set and catalogue
custody checks exist, supply one prepared text-layer page tuple, and attach
run provenance before persisting rule observations or exposing the report.
The local 57-slug candidate must not be used as a reviewed allowlist. This
lane touched no forbidden hotspot and made no Git publication.
