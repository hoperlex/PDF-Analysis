# W56A-DEV-FREEZE-01 — recorded-only W56a dispatch

**Status:** COMPLETE on code base `d600fe69777c923e246d89bc4a9451c3974eaf53`.
The dispatch SHA is the `origin/dev` ref after this documentation change is
published and read back. This freeze grants only `W56A-SEAL-01` and
`W56A-GENERATOR-PREP-01`; it does not complete the stopped
`W56A-FREEZE-01` or the failed `W56A-PROBE-01`.

## Verified inputs

The base is the W55b code plus documentation-only merges and R-135/R-136.
SHA-256 on the exact base:

| File | Digest |
| --- | --- |
| `contracts/api/v1/openapi.json` | `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482` |
| `contracts/domain/v1/error-codes.json` | `b342671a10bc1b4009af1a7b225517bba4c4378b6662b8c4122349b45f59af16` |
| `contracts/analysis/v1/stage-registry.json` | `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5` |
| `docs/program/P02_LOCK.json` | `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` |

Migration head is `0021_portal_bundles` (`alembic heads`, exit 0).
`pin_sweep.py reseal-surface migration table error-code` returned 98 lines,
SHA-256 `dd6d025853316a6764b8c66856b6952408f1e43e72c01b664f01c30cd250c11b`,
the same as the complete list in `W56A-FREEZE-01.md` §4. The six clean
legacy-source files at `/root/projects/PDF-proverka` commit `16ba8e5d`
match `W56A-LEGACY-SOURCE-01.md`; their current digest output was checked
again on 2026-10-15. `CATEGORY_LABELS` is in
`web/src/entities/expert-decision/model/category-labels.ts`, while the
knowledge-base filter's `CATEGORY_CHOICES` is in its page module. SEAL owns
the former; a later WEB task owns the latter.

## Grants and order

| Task | Sole writable scope | Result and stop |
| --- | --- | --- |
| `W56A-SEAL-01` | Contract/API/analysis enumerators, new `0022` migration, generated client and direct pins, category/severity labels; precise families in its task file | Additive v2 contract and forward upgrade; no `P02_LOCK.json`, provider body, VERSION or beta claim. |
| `W56A-GENERATOR-PREP-01` | New `tools/fixtures/seeded/**`, `fixtures/evaluation/ar_v2/**` except `baseline.json`, `tests/contract/fixtures_seeded/**`, its report | Byte-stable synthetic portal corpus, at least 21 grounded positives and seven controls; no recording, baseline or live quality claim. |

Both may branch from the same published dispatch tip, but only one resource
intensive task runs at a time on this host. Integrate SEAL first and
GENERATOR second. Contract/migration/head/generated client are SEAL's sole
hotspots. `P02_LOCK.json` belongs solely to future `W56A-MODEL-PIN-01`,
which requires both distinct gateway passes; until then PROVIDER and live
recordings remain blocked. Later PROFILES → MERGE → DECIDE → HARNESS → WEB
receive new task files and bases after their preceding merges. W57a follows
W56a's code close; W58–W63 require their own freezes.

## Checks, limitations and integration

This freeze changes only its task/report and the two code task definitions.
On this candidate, the documentation/prose/governance suites passed **93
tests**; `git diff --check` passed before staging. The staged/committed diff
and remote-ref read-back are checked before the grant is dispatched. No full
local gate or paid probe is permitted by R-135. The code grants demand bounded
tests, forward migration checks and changed-path proof before integration.
The existing failed gateway probe is neither hidden nor retried here. No
contract, migration, dependency, composition root, global style, runtime/UI
or Git release ref changes in this freeze. `origin/main` is outside its
authority.
