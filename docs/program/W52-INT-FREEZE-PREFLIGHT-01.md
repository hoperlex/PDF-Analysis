# W52-INT-FREEZE-PREFLIGHT-01 — measurements before the ruling and freeze

**Date:** 2026-10-08. **Subject:** clean `origin/dev` / `integration/w51`
base `f2ea05b0053ae0cbb14b8f767c3e576d250931d2`. This is a read-only
preflight, not `W52-RULE-01`, `W52-FREEZE-01` or permission to dispatch.

## Frozen input measured on the subject

| Surface | Direct measurement |
| --- | --- |
| OpenAPI | 27 paths, 34 operations, 77 schemas; `info.version` `1.0.0-draft.1` |
| Domain identity catalog | candidate revision 9, 29 identifiers |
| API error catalog | 23 codes |
| Migration graph | `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini heads` → `0015_accounts_roles_registration (head)` |
| Expected facts | 27 / 34 / 77, 23 API codes, head `0015_accounts_roles_registration` |
| OpenAPI SHA-256 | `633a58a53baf6652625b59d3db9438ae01e8c4ac8da788160882f031123f2e37` |

The API counts came from `contracts/api/v1/openapi.json`; identity and error
counts came from the two domain JSON catalogs. The expected-facts file agrees
with those values. `git diff --name-only 75dd708..HEAD -- contracts
db/migrations` was empty: no contract or migration path changed since the
W50 development close. The first Alembic invocation without `PYTHONPATH=src`
could not import `auditmanager`; the corrected command above resolved the
head without connecting to a database.

## Current pin inventory

`python3 tools/plan/pin_sweep.py` completed successfully for each event on
this exact tree. It reported **39** paths for `reseal-surface`, **26** for
`migration`, **17** for `table` and **28** for `route`; the combined invocation
reported **87 unique advisory paths**. Separately, `error-code` reported 27
and `contract-version` 45. Counts are output lines, including `/**` families,
not proposed edits. The freeze must re-run the relevant events on its own
base and use `--check` against actual Stage-B/C task files after they exist.

The current combined output reaches beyond the old plan's named SEAL bullets:
for example `src/auditmanager/shared/db/migrations.py`,
`src/auditmanager/documents/refusals.py`,
`src/auditmanager/storage/check.py`,
`tests/integration/foundation/test_cross_provider_publication.py`,
`web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx` and several
screen/navigation guards. These are **sweep hits to classify**, not automatic
permission to edit. The SEAL grant's catch-all sentence requires the
integrator to reconcile each hit in the concrete task before dispatch;
a false positive needs an explicit tool/plan correction, not silent omission.
The freeze also has to reconcile the
already merged FACTS/PINSWEEP and individual debt preparations; it must not
dispatch their old plan descriptions a second time.

## Remaining boundary

`W52-RULE-01` still needs the owner's three explicit confirmations in W52
§4: hand-written expected facts with separately maintained live prose;
serial-only gate acceleration in W52; and unchanged `contract_version` until
beta freeze. `W52-FREEZE-01` has no task or report yet. The W52 plan expressly
defers the standard full gate at freeze and code-only close to D-140, but
keeps the current-tree grant and contract checks. D-137–D-140 retain all
release validation. A generic continuation does not settle the three
product/process choices.

## Checks, scope and handoff

The focused governance/prose/surface command passed **93 tests** on the
preflight tree; `git diff --check` passed. The exact committed tree is checked
again before publication. No full gate, service, QA or live acceptance was
run. The only tracked files in this task are
`docs/program/tasks/W52-INT-FREEZE-PREFLIGHT-01.md` and this report. No
contract, migration, dependency/lock, composition root, global style,
product code/test, plan, ruling, tag or deployment path is touched; no
contract changes. Revert the docs-only commit if a measurement is wrong.

After owner answers, write the rulings first. Re-measure from the then-current
`origin/dev`, create concrete freeze and lane tasks with exact allowed paths,
run `pin_sweep --check`, and publish the docs-only freeze only after its own
checks and remote-ref ancestry proof. This report is an input, not freeze
evidence for a later SHA.
