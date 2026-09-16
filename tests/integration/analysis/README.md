# `tests/integration/analysis`

Guards written by `W10-ANL` for rules in `src/auditmanager/analysis/**` that a mutation
sweep found no existing test could redden.

Every expected value in this directory is a **literal**. Nothing here imports a constant
from the module under test and builds the expected value out of it — that is how wave 9
produced five green tests over three rules they could not check, because both sides of the
comparison moved together under mutation.

Where an independent authority for a value exists it is read from that authority and
compared against the module, so a constant that drifts away from the authority is a red
test rather than a quiet agreement between a module and itself. The authorities used are
`db/migrations/versions/*` CHECK constraints, `contracts/analysis/v1/stage-registry.json`,
`docs/program/P02_LOCK.json` and `docs/program/P02_SEAMS.md`. None of them is in
`src/auditmanager/analysis/`.

Every refusal is asserted **by the rule that refused** — its `reason` or `constraint` detail
and its catalog code — never by "a `DomainError` was raised". A test that only asserts
something raised passes whichever of several checks fired, which is how a deleted check
survives a sweep.
