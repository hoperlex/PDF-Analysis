# W57B-INT-REFERENCE-RESOLUTION-PREP-01 — pure normative references

## Result

The new `norms/references` package mirrors migration 0020's designation
fold/token function, extracts raw occurrence spans from text-bearing pages,
parses the W57b designation families and resolves citations against a caller
supplied pinned catalogue. It reports five outcomes. A newer edition wins
over a same-edition match, and an amendment remains separate from its base
edition. Only the newer-edition outcome carries proposed rule text; no
expert severity is assigned. Unread pages are reported separately.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/references/test_reference_resolution.py`: **18 passed**.
- Python compilation: passed.
- Direct task governance: `[]`; `git diff --check`: passed.
- Full `make gate` deferred under R-135.

## Contracts and limits

No API/domain/analysis contract, migration, provider lock, composition root
or root dependency changed. The pure resolver trusts the caller to supply
the entire catalogue from the run's verified set, its stored SQL tokens and
the run's pinned snapshot. It does not prove corpus totality, legal edition
status or stage provenance. Catalogue slugs outside the parsed families must
be explicitly listed for review. A DB equality sweep over all 674 slugs and
generated designations remains for the later W57b gate; these tests compare
the Python fold tables to migration 0020 and exercise representative cases.

## Integration instruction

After W57a set publication, bind the catalogue read to the run's exact
snapshot and verified custody role, pass text-layer pages, then persist only
newer-edition observations with `rule_id`
`normative_refs.newer_edition/1` and at most ten occurrence spans. Report the
other outcomes and unread pages without producing a finding. The W57b seal
still owns category, stage, API and migration changes.

## Ownership proof

Only the new `src/auditmanager/norms/references/**`, new focused tests, this
report and its task file were written. Existing search/retrieval modules,
`contracts/**`, migrations, findings, public API, composition root, root
dependencies, global styles, corpus, stand and Git refs were untouched.
