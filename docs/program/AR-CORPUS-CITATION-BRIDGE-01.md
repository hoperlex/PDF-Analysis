# AR-CORPUS-CITATION-BRIDGE-01 — saved corpus to AR v3 citation plan

**Task:** [AR-CORPUS-CITATION-BRIDGE-01](tasks/AR-CORPUS-CITATION-BRIDGE-01.md).
**Base:** published `origin/dev=a955346aa2f30f004de66979acc2262d628ecd02`.

The AR v3 original-topic guide is already on the development branch. This
slice connects its draft request to the existing Attempt-fenced, custody-aware
reader for a Run-pinned verified normative retrieval set. The reader now
returns the reviewed map SHA-256 it already selected from the database. The
adapter refuses a Run, profile, bundle, map, snapshot or set mismatch. It
passes the saved set bytes to the v3 request builder, which sends only selected
labelled paragraphs to the model-facing draft. Local replay grounds a supplied
response against the same bytes and converts only accepted normative
observations into publication candidates. Rebinding a candidate to another
set refuses; an unknown label yields no publication candidate.

This is an **unserved code seam**. It makes no provider call and writes no
finding or CITE StageResult. It does not establish a legally reviewed map,
qualified production set, model provenance or expert decision. Activation
requires the separately owned AR v3 profile/runtime and citation transaction
integration described in `AR-ORIGINAL-CITATIONS-PLAN-01.md`. The current
production AR section still uses its existing profile.

## Checks

- Focused saved-set, bridge, v3 prompt/evaluation and program tests: **59 passed**.
- Python compilation and `git diff --check`: passed.
- No full gate or paid model call under the code-first R-135 cadence.

## Integration and rollback

The runtime owner should supply a registered v3 profile/bundle/map identity,
persist and pin a qualified set before dispatch, call the bridge for the
current Attempt, then bind an actual provider response and its saved model
call/effect to the local evaluation. Publication must recheck Attempt and
set authority, write the CITE StageResult and accepted citations in the
owned transaction, and commit before exposing results. No fallback to the
old AR profile is allowed for a v3 Run whose set is absent.

The new bridge is additive and unserved; a forward revert removes it and the
new public exports without data migration. The only existing DTO change adds
the map digest selected from the same immutable set row.

Changed paths are the two public exports, the set reader, the additive bridge,
two focused tests and this task/report. No `contracts/**`, migrations, root
dependencies/locks, composition root, router/UI, provider transport, v1/v2
prompt bytes, global styles or `origin/main` were touched.
