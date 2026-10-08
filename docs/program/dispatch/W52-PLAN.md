# Wave 52 — quality of the identity block, and the versioning system

**Status:** revision 3 design, adopted onto the development line by `W52-INT-ENTRY-01`
from planning SHA `2b45a11` on 2026-10-08. The entry and execution amendment below
supersedes the older gate-dependent dispatch sentence. W52 is **not frozen or
dispatchable**: `W52-RULE-01` and `W52-FREEZE-01` remain due.
Round 2 (both judges ACCEPT-WITH-FIXES, all fixes
text or grant lines) is applied; no third round (`R-V4`). Revision 2 was rebuilt on the first judging round (design judge:
ACCEPT-WITH-FIXES, seven majors; grants judge: REJECT, seven majors; both verified against
`integration/w49`, where the W49 seal has landed). The second round was the
last planned round; `R-V4` has not yet been recorded as an owner ruling.
**Amended 2026-10-07** by the planning session at the integrator's request, not re-judged (grant
lines and one lane, no design change): `W52-TRANSLATE-01` in Stage C for the runbook translation
(owner poll 2026-10-07, `R-69`), and `D-133`'s code-only half in `W52-DEBT-CODE`. Paths measured
on `integration/w50` at `df120a8`; every pin is re-swept at `W52-FREEZE-01`.
**Author:** the planning session, on local branch `plan/roadmap-to-beta`; hand-over to the
integrator `pdf-analysis-48` after the second round.
**Controlling answers:** `ROADMAP-TO-BETA.md` §10 (V-1…V-10, P-1, P-2) and §10.10 (W-1…W-4).
`R-V1`…`R-V4` are placeholders; `W52-RULE-01` takes the next free numbers.
**Roles:** `IDENTITY-WAVES.md` §8. Task forms not spelled out are its §10 standard forms.
For W52 development only, the owner's later 2026-10-08 deferral overrides
§10's full-gate steps in `W52-FREEZE-01`, individual code lanes and
`W52-INT-CLOSE`; D-140 owns their replacement exact-candidate gate.
`W52-FREEZE-01` must state this exception in its own task file and cannot
claim the old freeze baseline or JUnit parity. All other freeze checks,
especially current-tree grants and frozen contracts, remain required.
**Development exit under the owner's 2026-10-08 code-first direction:** the
implementation candidate may advance on `origin/dev` with each lane's basic
checks, while D-137–D-140 record the deferred W51/W52 QA, attack, built-stand,
manual and complete-gate obligations. Neither a code merge nor development
closure is a release verdict. **Release exit:** a later validation/correction
stage supplies those checks and literal `GATE OK` on the exact candidate;
`origin/main`, live acceptance and the first release tag **`v0.3.0`** then
require the owner's separate direct instruction naming that SHA.

**Execution amendment, 2026-10-08:** W51 implementation closed on `origin/dev`
at `4159d4e` without a full gate by the owner's later direction. The plan's
original first entry row and serial gate measurements cannot be interpreted
as passed. `W52-RULE-01` still records the three owner confirmations named in
§4; `W52-FREEZE-01` still re-sweeps the current tree, grants and pins before
new W52 lanes are dispatched. Stage A audit/attack, Stage D QA/judging, live
acceptance and complete gates move to the separate validation stage tracked
by D-137–D-140. The implementation tasks below retain their design and
acceptance targets; each code-only task must state the focused checks actually
run and the deferred checks. Preparations already merged on dev are not a
substitute for the freeze.

## 1. Objective

- **Track Q — quality of W48–W51** (W-2 "аудит + атака + долги"): an independent audit of the
  tree after W51, a black-box attack on the identity surface of a built stand, the registered
  debts of W48–W51 closed or re-slotted, every upheld release-blocking finding repaired; the
  human runbooks in English (`R-69`).
- **Track V — versioning and tools** (V-9, P-2): one product version in `VERSION`; a content-derived
  build identifier; an authenticated version read; release notes authored in the repository,
  checked by a form test and a judge, loaded into PostgreSQL at deploy, shown as a history panel,
  an update banner and a one-time «Что нового»; the acceptance pack measuring the deployed build
  (`D-121`). Alongside: one expected-facts file for the contract pins, a faster gate, and the
  pin-sweep tool.

## 2. Entry conditions

| Condition | Evidence |
| --- | --- |
| `W51-INT-CLOSE` development implementation done; W51's deferred gate and QA remain D-137/D-138 | `docs/program/W51-INT-CLOSE.md`; `origin/dev` at `4159d4e` |
| screen registry and account menu exist (W50) | `web/src/shared/config/screen-registry.ts`; the account-menu island in `web/src/_app/` |
| role registers exist (W49) | `OPERATION_ROLES` and the profile/default-credential registers in `src/auditmanager/api/security.py`; `ACCOUNT_REFERENCES` in `src/auditmanager/access/references.py` |
| W49–W51 debts registered | rows above `D-128` in `DEBT_REGISTER.md` |
| `R-V1`…`R-V4` recorded, including the three owner confirmations of §4 `W52-RULE-01` | `W52-RULE-01` |
| current pins, grants, contract set and code-only validation boundary recorded | `W52-FREEZE-01.md`; full-gate timing moves to D-140 |

## 3. Design decisions bound by this plan

### 3.1 Version and build identifiers

- **`VERSION`** (root, one line, canonical SemVer 2.0, no build metadata) is the only source of
  the product version. **Rule, unconditional:** `VERSION` equals the highest non-archive version
  in `release-notes/`. `pyproject.toml` and `web/package.json` keep their placeholder versions and
  are not synchronised (they sit under `uv.lock`, `web/package-lock.json` and `FRONTEND_LOCK.json`);
  a guard asserts no code reads them as the product version.
- **A release** is an owner-instructed deploy to `main` with a user-visible change (V-3), tagged
  `v<VERSION>` by `*-INT-MAIN`. `alpha-wNN` ends at `alpha-w51`; the CP-series plan in
  `CHECKPOINT_REGISTRY.md` is retired (`R-V1`).
- **API `build_id` is computed by the API process at start-up over its own files**, not stamped by
  a build step: `"b" + sha256_hex[:16]` over the sorted lines `"<path>\t<sha256 of bytes>\n"` for
  every regular file under the roots `src/`, `db/`, `contracts/`, `fixtures/recorded/`,
  `release-notes/` and the files `VERSION`, `uv.lock`, `docs/program/P02_LOCK.json`, where `<path>`
  is the repository-relative path (identical at `/app` and in a checkout); files matching
  `__pycache__/`, `*.pyc` are skipped. `infra/deploy/serve.py` is excluded (its path differs).
  It is computed once, when the application is built, in `bootstrap/composition.py` through the
  `auditmanager.releases.public` function, with the root taken from `auditmanager.__file__`, never
  from the working directory. Each runtime `COPY` line names one source and an explicit `/app/…`
  destination (`verify-deployed.sh` parses only `NF == 3` lines).
  Consequences: no new layer, `ENV` or label, so `deploy.sh`'s image fingerprint is untouched; the
  same function gives a defined answer outside an image (no fallback); `Dockerfile.api` gains
  `COPY` lines only for `VERSION`, `release-notes/` and `uv.lock`, which `verify-deployed.sh`
  then verifies by content automatically. A guard asserts no tracked file under these roots
  matches a `.dockerignore` pattern, so a checkout and the image hash the same set.
  **Known limits, registered:** a change to `Dockerfile.api` alone (base digest, `ENV`, `CMD`) or to
  `infra/deploy/serve.py` alone does not move `build_id`.
- **Fail closed:** `VERSION` missing or not canonical → the API refuses to start with the existing
  `ConfigurationError`; `NEXT_PUBLIC_WEB_BUILD_ID` absent → `MissingConfigurationError`, as
  `env.ts` does for its other names.
- **Web `web_build_id`** is computed in the existing `npm run build` step of `Dockerfile.web`
  (no new `COPY`) over `web/src/**`, `web/public/**`, `web/package-lock.json`,
  `web/next.config.mjs`, `web/tsconfig.json` and the values of the `NEXT_PUBLIC_*` build
  arguments, and inlined as `NEXT_PUBLIC_WEB_BUILD_ID` for that build only. It is never in the
  contract.
- **`contract_version` does not move in W52.** It is shared by the API, domain, analysis and events
  families (`shared/errors/catalog.py`, `error-envelope.schema.json`, `test_cp00_candidate.py`'s
  one-version rule), appears in 142 tracked files (96 outside `docs/`; `git grep -l 1.0.0-draft.1
  integration/w49`), and was not an owner answer. `getProductVersion` reports the current value of
  `CONTRACT_VERSION` (equal to `info.version`); the move — which families, which files — is decided at the beta
  freeze (B9) as its own event, and `W52-PINSWEEP-01` already knows the event.

### 3.2 Operations (names are the seal's to confirm)

| Operation | Method / path | Access | Answer |
| --- | --- | --- | --- |
| `getProductVersion` | `GET /system/version` | any active account with a complete profile | `{product_version, build_id, contract_version}` |
| `listReleases` | `GET /releases` | same | `{items, whats_new}` — items with version ≤ the running `VERSION`, newest first, the highest revision of each, the archive entry last; each item `{version, revision, date, title, is_archive, range_label \| null, items: [{kind, screen, where, text}]}`; `whats_new` is the list of versions to show once, possibly empty (§3.5) |
| `markReleaseNotesRead` | `PUT /me/release-notes` with body `{read_through}` | same; the account's **own state**, like `updateMyProfile`, so an administrator without the expert role may call it (`R-60` concerns product data) | `204`; idempotent; a version above the running one or unknown → `validation` |

- **Releases have no public identity.** No operation addresses one release, so there is no path
  parameter and no `<prefix>_<ULID>`; the version string is data. (Precedent: retrieval chunks
  have no public identity.) Internally a release row has a surrogate key and a unique canonical
  `version`. `R-V2` records that a canonical SemVer is an immutable natural key here, not a display
  number (`AGENTS.md` §4): the append-only triggers and loader rule 4 enforce that it never changes
  meaning.
- **Nothing is opened to a guest.** `UNAUTHENTICATED_OPERATIONS` is unchanged; `/bff/version`
  requires a session as well.
- The migration head, profile-bundle hashes and norms snapshot are not served; they live in the
  technical record (§3.4).

### 3.3 Storage — migration `0016_release_notes`

- `release(pk, version UNIQUE, sort_key, is_archive)` — `sort_key` orders canonical SemVer
  including pre-releases (so `0.10.0` sorts after `0.9.0`); computed by one function, checked
  against a table of versions. **No `UPDATE` or `DELETE`, enforced by a trigger.**
- `release_revision(release_pk, revision, released_on, title, content jsonb, content_sha256,
  loaded_at)` — **append-only, enforced by a trigger** (precedent `trg_registration_request_guard`);
  title and date live here so a corrected title is a new revision, never an `UPDATE`;
  `content_sha256` is over canonical JSON, so a whitespace reformat is not a revision.
- `account_release_mark(user_uid PK → app_user ON DELETE CASCADE, read_through_release_pk →
  release, marked_at)` — one high-water mark per account, compared through `sort_key`, **only ever
  raised** (a lower value is a no-op). It is the account's own row: it joins `ACCOUNT_REFERENCES`
  in `access/references.py` as cascading and never blocks a purge (`R-61`).
- **Loader** `python -m auditmanager.releases.load`, a one-shot compose service `release-notes`
  between `migrate` and `api`:
  1. entries are exactly the files named `^<canonical semver>\.json$`; `schema.json` and
     `dictionary.json` are known non-entries; any other top-level file refuses. Each entry is
     validated against the **shape** schema only (prose rules stay in the gate, so a later
     dictionary word can never fail a deploy of history);
  2. each file carries an **authored integer `revision`** (V-6: edits only by a new revision).
     `revision` above the highest stored → append (content must differ); equal to a stored revision
     → the canonical hashes must match, otherwise refuse (an edit without a bump); below the
     highest → no-op, reported (the rollback case). The API serves the highest revision, so
     A→B→A is an explicit revision 3;
  3. a release in the database **above** the image's `VERSION` and absent from the image is left
     untouched and reported, exit 0 — the `≤ VERSION` filter hides it, so a rollback works;
  4. a release **≤ `VERSION`** present in the database and absent from the image refuses, exit
     non-zero, nothing changed. `RELEASE_PROCESS.md` therefore states that a file that reached
     `main` is never deleted; withdrawing or merging an entry is a new revision.
- The `release-notes` service sits after `migrate` in `compose.server.yml` (file order is pinned
  by `test_minio_image_contract.py`). `deploy.sh`: it joins the `services-healthy` loop;
  `reset.sh`: the wipe path runs it after `migrate`; the `--restore` path runs it so that appends
  still load and only rule 4 becomes a report (`reset.sh` reports, it does not refuse).

### 3.4 Release notes — form, judge, two layers

- **File** `release-notes/<version>.json`; the file name equals the `version` field, which is
  canonical SemVer. Shape: `{version, revision, date: "YYYY-MM-DD", title, items: [{kind, screen,
  where, text}]}`; `release-notes/schema.json` defines it, and a `W52-RELEASES-API` test asserts its
  item and `kind` definitions equal the served components SEAL froze; `kind ∈ {new, improved, fixed}` (Новое / Улучшено / Исправлено); `screen` is the
  `address` key of a screen-registry entry; `where` is the display path as it read **at release
  time** («Работа › Проекты › Замечания»), kept as history. The panel renders the stored `where`
  and never links by `screen`, so an address that later disappears is not a fault.
- **Archive:** `release-notes/0.2.0.json` with `is_archive: true` and `range_label: "0.1–0.2"` — one
  entry «прототип и альфа» (V-10).
- **Form rules** (Python test; Vitest only for `screen`): versions unique, canonical, strictly
  descending with dates; title 3–9 words, no final period; 1–7 items ordered new → improved →
  fixed; text ≤ 400 characters; no straight quotes; no code traces (snake_case, camelCase, file
  extensions, `/api/`); no dictionary word outside «ёлочки»; `VERSION` rule of §3.1. **Only the
  entry equal to `VERSION`** is checked against the live screen registry (`screen` exists, `where`
  starts with its current group and label) — history is not re-validated when navigation moves
  (A-6 moves «Оптимизация» in W59). **Self-test:** fixtures of bad entries fail each rule by name.
- **Judge** `W52-NOTES-JUDGE` checks every claim against the diff and the tree, and re-runs on the
  later release-validation candidate after `W52-FIX`; from W53 it is a step of every `*-INT-MAIN` that ships
  a release.
- **Technical layer** `docs/program/RELEASES.md` (English), one row per release: tag, SHA,
  `build_id`, `web_build_id`, `contract_version`, migration head, prompt/profile bundle hashes, the
  `GATE OK` line; the norms snapshot column from W55.
- **Process** `docs/program/RELEASE_PROCESS.md`: who writes, who judges, when `VERSION` moves,
  hotfix flow (branch from the tag, gate, instruction, fast-forward `main`, merge back to `dev`).

### 3.5 Interface

- «История версий» in the account menu opens a side panel: «Текущая версия: X», the legend from
  existing tokens (`--am-ok` Новое, `--am-accent` Улучшено, `--am-degraded` Исправлено), the feed,
  a collapsed «Архив (1)» collapsed again on each open; dates from the `YYYY-MM-DD` string, never
  through `Date`; an unknown `kind` is a typed fault.
- **Update banner** «Доступна новая версия — Обновить / Позже»: checked on shell mount, on window
  focus, on `visibilitychange` to visible and on route change — **no interval timer** — through a
  fetch helper in `web/src/shared/api/` reading `/bff/version` (session required) and comparing
  with the bundle's `NEXT_PUBLIC_WEB_BUILD_ID` read in `web/src/shared/config/`.
- **Fail closed in the banner:** `/bff/version` failing shows no banner and is retried on the next
  trigger; a 401 goes to sign-in; «Позже» hides the banner for that `web_build_id` only.
- **«Что нового» — the rule lives on the server** (`listReleases.whats_new`): every non-archive
  release ≤ the running version, above the account's mark, whose first load into this database
  happened after the account existed — measured as `app_user.created_at < min(loaded_at)` of the
  release's revisions, both on the database clock — newest first; empty otherwise. The shell
  shows them on mount **and re-reads `whats_new` on the banner's triggers** (an API-only release
  leaves the web build unchanged and tabs never re-mount); closing calls `markReleaseNotesRead`
  with the newest shown version, which raises the mark over all of them. A new account never walks
  back through old releases. The dialog is dismissible and never blocks navigation.
- Russian only; the panel's loading, empty and fault states are added to the matrix of
  `rendered-language.guard.test.ts`.

### 3.6 Expected-facts file (A5) — hand-written, with a fixed schema

The poll said "generated"; `CONTRACT_PIN_REGISTRY.md` forbids deriving an expected value from the
artifact it judges. So `tests/support/expected_facts.json` is **hand-written**, with this schema
fixed now so that `W52-PINSWEEP-01` can be built beside `W52-FACTS-01`:

```json
{
  "facts_version": 1,
  "surface": {
    "path_count": 0,
    "operations": [["GET", "/example", "exampleOperation"]],
    "schema_names": ["Example"]
  },
  "error_catalog": {"api_codes": 0, "stored_vocabulary": 0},
  "migration_head": "0000_example",
  "contract_version": "0.0.0-example"
}
```

- Explicit lists, never digests (a digest can only be computed from the artifact).
- The two error counts are separate facts (`test_openapi_document.py` vs
  `test_contract_vocabulary.py`; they differ since W49).
- Every registry pin and symbolic pin (`FROZEN_OPERATIONS`, `FROZEN_SCHEMA_NAMES`, `*_COUNT`,
  `SurfaceTriple(...)`, `toHaveLength(N)`, the counts in `FRONTEND_LOCK.json` read by
  `frontend-lock.guard.test.ts`) compares the artifact with this file.
- The inventory test in `test_doc_prose_facts.py` stops filtering by specific numbers
  (`==\s*(?:17|20|22|61|…)`) and turns red on **any** count literal compared with a surface,
  catalog or head value outside the facts file.
- One coincidental literal is exempted by name: `assert len(report) == 22` in
  `test_openapi_conformance.py` (a report length, not a catalog count); `tests/contract/tools/fixtures/**`
  is excluded from the inventory.
- What is given up: twenty-seven copies of one opinion become one. Independence from the artifact
  is kept. **Not delivered from the adopted A5:** live prose does not read the file — the seal
  still edits about ten prose sentences by hand, under the prose guards. **Owner confirmation
  required in `W52-RULE-01`** for both halves.

### 3.7 Gate speed (A6, partial)

Earlier measured gates put the battery at 93–95 % of the gate, 600–1122 s at
similar counts; contention explains the spread. The owner's later deferral
means `W52-FREEZE-01` records this as historical context, not a new baseline.
The integrator measures a fresh baseline and the corrected result, with
`--durations=50`, JUnit XML, command, tree and host load, at serial points in
the validation stage under D-140. No timing or outcome parity is claimed by
the code-only gate-preparation merges.

Lane changes (`W52-GATE-01`):
1. the battery stops re-running `tests/integration/foundation` (the gate's `foundation` target runs
   it);
2. `migrated_database` clones a template migrated **once per session** with the literal Alembic
   command, named by a digest of `db/migrations/` content and never reused across runs
   (`CREATE DATABASE … TEMPLATE`); tests whose subject is applying migrations keep `empty_database`
   and the literal command;
3. the parallel hazards are removed: `bucket_keys` fixtures scoped to their own prefix, the
   `AUDITMANAGER_PROVIDER_MODE` leak in `tests/e2e/pc01/conftest.py` restored, the throttle tests'
   shared `app_user` rows isolated.

**Deferred validation invariant:** the union of foundation and battery test ids
is identical before and after, and each id's outcome (pass, skip, xfail) is
identical — compared from JUnit XML, not from ids alone.
**Target:** battery ≤ 6 min when measured. **Deviation from the adopted A6, for owner confirmation:**
`pytest-xdist` (a `uv.lock` change) and impacted-test selection for lane gates are not in this
wave; if the target is missed, the integrator registers them with the measured shortfall.

## 4. Tasks

### `W52-RULE-01` (integrator)

Standard form. Records after the owner confirms the text:

- `R-V1` versioning (§3.1; V-1…V-3, V-9, V-10), including: `contract_version` unchanged in W52 and
  decided at the beta freeze.
- `R-V2` release notes (§3.2–§3.5; V-2, V-4…V-8), including: releases have no public identity and
  a canonical SemVer is their immutable natural key; authored revisions; `markReleaseNotesRead`
  is the account's own state.
- `R-V3` `D-120` accepted as a process rule (W-1): only the integrator pushes `main`, after literal
  `GATE OK` on the exact SHA and the owner's direct instruction; `D-120` closes as accepted risk.
- `R-V4` process (P-2): plan judging capped at two rounds; two cross-judges only for waves touching
  contract, migration, security or data custody, one judge otherwise.
- **Owner confirmations** asked in one message: the hand-written facts file, and live prose not
  reading it (§3.6); A6 without `pytest-xdist` and impacted-test selection in this wave (§3.7);
  `contract_version` unchanged until beta (§3.1, not an owner answer, asked for completeness).

### `W52-FREEZE-01` (integrator)

Exception to `IDENTITY-WAVES.md` §10: no full `make gate` at this code-only
freeze; D-140 owns that check. Otherwise standard form, plus: the deferred
timing boundary of §3.7 and the exact
W49–W51 rows for the two debt lanes. `pin_sweep.py` and the expected-facts
file now exist as code preparations on dev; the freeze runs the tool against
the **current** tree and widens each remaining task grant as needed. It
reconciles the already merged preparation and debt slices before assigning
remaining work. Ports are allocated only when an actual stand/lane needs
them. Neither earlier merge retroactively freezes Stage A.

### Stage A — code lanes from the freeze SHA; AUDIT/ATTACK at validation

**`W52-AUDIT-01`** (fresh context; report only): whole-tree audit at the freeze SHA in the form of
`docs/program/reviews/W48-AUDIT.md` — identity backend (W49), shell (W50), screens (W51), the W48
repairs and their seams; findings classified release-blocking / this-wave / register, with
path:line, consequence and reproduction. Allowed: `docs/program/reviews/W52-AUDIT-01.md`.

**`W52-ATTACK-01`** (fresh context; disposable built stand; report only): black-box first —
enumeration through sign-in, registration and status; flooding to the cap from the form and from
`/api/v1/`; role removal and archive effective on the next request; escalation between expert and
admin, including an admin-only account writing product data; IDOR on `user_uid` and request ids;
open redirect via `next`; session fixation and cookie flags; CSRF on the BFF form handlers; purge
of a referenced account; 780 × 900 with maximum-length names. No credential in evidence. Allowed:
`docs/program/reviews/W52-ATTACK-01.md`.

**`W52-FACTS-01`** (§3.6). Allowed: `tests/support/expected_facts.json` (new), the files of the 27
registry pins and of the symbolic pins, enumerated by the freeze from `CONTRACT_PIN_REGISTRY.md`
and `rg -n "FROZEN_OPERATION|FROZEN_SCHEMA|PATH_COUNT|OPERATION_COUNT|SCHEMA_COUNT|SurfaceTriple\(|toHaveLength\(" tests web/tests`,
`web/tests/guards/frontend-lock.guard.test.ts`, `docs/program/CONTRACT_PIN_REGISTRY.md`,
`tests/contract/api_v1/test_doc_prose_facts.py`, `docs/program/W52-FACTS-01.md`. The inventory
excludes `tests/contract/tools/fixtures/**` and exempts the one literal named in §3.6. Required: one
mutation per family using the **current** values (editing the facts file reddens the matching
pins; a new count literal compared with the operation count anywhere reddens the inventory).

**`W52-GATE-01`** (§3.7). Allowed: `Makefile` (battery recipe only),
`tests/integration/db/conftest.py`, `tests/integration/storage/conftest.py`,
`tests/integration/ingest/conftest.py`, `tests/e2e/pc01/conftest.py`, `tests/integration/auth/**`
(isolation of the throttle and revocation tests only), `docs/program/W52-GATE-01.md`.
Code-only delivery uses focused checks and lint. The JUnit invariant, literal
`GATE OK` and timing are D-140 validation obligations on the later exact candidate.

**`W52-PINSWEEP-01`** (A4). `tools/plan/pin_sweep.py <event>…` with events `reseal-surface`,
`error-code`, `migration`, `table`, `route`, `contract-version`: prints every file a task causing
that event must be granted, from `CONTRACT_PIN_REGISTRY.md`, the facts-file schema of §3.6 and a
pattern catalogue (count words and digits in live prose, `len(...)`, `toHaveLength`, operation
sets, mutating sets, input-less sets, paginated sets, table lists, service lists, head sentences);
`--check <task file>` reports grants missing from `allowed_paths`. The catalogue includes the
exact-set web guards (`server-credential.guard.test.ts` names, `dashboard-invalidation` map,
`contrast.test.ts` census with `styles/screens.ts`) and `tests/e2e/pc01/journey/manifest.json`.
Fixtures are non-`.py` data, and no surface-count phrase is written in `tools/plan/**`
(`tools/` is live for the prose guard). Allowed: `tools/plan/**`,
`tests/contract/tools/test_pin_sweep.py`, `tests/contract/tools/fixtures/pin_sweep/**`,
`docs/program/W52-PINSWEEP-01.md`. **Acceptance, from embedded fixtures (no git history read):**
the fixture lists the subset of files the W49 seal and migration commits (`e86bfbe`, `633a83a`,
`48099d9`, `220638d`, `0dbb418`) changed **because of a pin**, with a written reason for every
excluded file (for example the ledger default and the `access` context itself are not pins); run
as `reseal-surface error-code` and `migration table` against the W49 tree before its seal, the tool
prints that subset with no pin-caused file missing, plus every hole the identity plan's judging
rounds found. Held out, it is run on the Stage-B, C and C2 task files of this plan.

### Integrator between A and B

Reconcile the already merged FACTS and PINSWEEP preparations, then merge GATE
after its bounded code checks. At validation, measure the gate (§3.7) and
triage AUDIT and ATTACK into `W52-FIX-A`
(release-blocking, disjoint from SEAL's grant — a finding in `src/auditmanager/api/**` or the BFF
route goes into SEAL instead), the debt lanes or the register; run
`pin_sweep.py --check` on every Stage-B task file and widen grants before dispatch; repeat on the
Stage-C and C2 task files at the Stage-B merge.

### Stage B — from the Stage-A merge (executor; disjoint grants)

**`W52-SEAL-01`** — one slot, one gate, modelled on the final grant of `W49-SEAL-01`. Content: the
three operations of §3.2 and their schemas; the role and profile registers and their sweep tests;
router skeletons bound to a `ReleasesPort`; migration `0016_release_notes` (§3.3) with its
append-only trigger; `ACCOUNT_REFERENCES`; the facts file; the four-document reseal. Allowed:

- `contracts/api/v1/openapi.json`, `contracts/api/v1/README.md`, `contracts/domain/v1/README.md`
  (sentences naming the surface only);
- `web/openapi/openapi.json`, `web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json`;
- `src/auditmanager/api/**`, `src/auditmanager/bootstrap/adapters.py`,
  `src/auditmanager/bootstrap/composition.py`, `src/auditmanager/access/references.py`;
- `db/migrations/versions/<date>_0016_release_notes.py`;
- `tests/contract/**` except the four `W52-DEBT-GUARDS` files; `web/tests/contract/**`;
- `tests/integration/{api,auth,composition,db}/**`; `tests/integration/p02_journey/journey.py`
  (`P02_TABLES`); `tests/e2e/pc01/test_acceptance.py` (route count and the mutating-operation set);
- `tests/support/expected_facts.json`, `docs/program/CONTRACT_PIN_REGISTRY.md`;
- the count sentences in `web/src/app/bff/v1/[...path]/route.ts`, `web/src/shared/api/authorization.ts`,
  `infra/deploy/README.md`, `infra/deploy/serve.py`, `infra/deploy/proxy/nginx.conf`,
  `src/auditmanager/api/README.md`, `docs/program/P02_SEAMS.md` (§7: the operation rows, the count
  sentences and the idempotency rule, which names `markReleaseNotesRead` among the unkeyed writes) with
  `tests/contract/domain_p02/test_seam_register.py`;
- the head sentence in `docs/manual-tests/PC-01_prototype.md`; **the live surface-triple and head
  sentences in `docs/program/CURRENT_STATE.md` and `docs/program/ALPHA_ROADMAP.md`** (exact
  sentences, as `W49-SEAL-01`);
- every further path `pin_sweep.py reseal-surface migration table` prints at the Stage-A merge,
  added to the task file by the integrator before dispatch;
- `docs/program/W52-SEAL-01.md`.
Required: `pin_sweep.py --check` clean; `.venv/bin/python -m pytest tests/contract -q`;
`npm --prefix web run api:verify`; the full `make gate` and literal `GATE OK`
are deferred to D-140 under the development-only direction. A pin outside the grant is a stop,
not an edit (precedent: the two stops of `W49-SEAL-01`).

**`W52-DEBT-GUARDS`** — `D-128` F-1…F-6 and guard rows the freeze assigns. Allowed:
`web/tests/guards/screen-set.guard.test.ts`, `web/tests/guards/dashboard-invalidation.guard.test.ts`,
`tests/contract/program/test_wave_governance.py`, `tests/contract/test_alpha_acceptance_command.py`,
`tests/contract/test_deploy_auto_workflow.py`, `tests/contract/architecture/test_alr05_boundaries.py`,
`docs/program/W52-DEBT-GUARDS.md`. Required: each repaired guard red under the JUDGE-Z probe that
stayed green.

**`W52-DEBT-CODE`** — `D-128` F-7, F-10, F-11 and the code rows the freeze assigns from W49–W51
(candidate: a temporary password equal to the current one refused in `reset_password`). Allowed:
the files those rows name, enumerated by the freeze; **not** `access/references.py`, not
`src/auditmanager/api/**`. `docs/program/W52-DEBT-CODE.md`. Required: a test per row whose revert
is red.
Also **`D-133`'s code-only half** (slotted to this lane by the integrator, 2026-10-07):
- `_map_http_failure` (`src/auditmanager/analysis/text/proxy.py`) stops folding statuses at which no
  model answered — 402, 403, 404 and every 5xx it does not already map — into `analysis_failed`, and
  maps them onto **existing** catalog codes by one rule: an answer only an operator can change
  (credential, allowlist, key policy, credit, base path) is not retryable; a provably unprocessed one
  is retryable; anything else is not retryable. No new error code. 429, 503 and 504 keep today's
  mapping, because W53's dispatch classes (E-7, E-8: only the proxy's **own** 503 envelope is
  retried) own them.
- the proxy's error body is read for every status, bounded and redacted, and logged server-side;
  it is never stored where the API serves it.
- **Not here:** the stage's typed message in `RunStatus` (a contract change) and the start-up refusal
  of a stub `PROXY_LLM_MODEL` stay with `W56-PLAN.md` §A3.5; the refusal would stop the stand's
  deploy while the owner has not stated the stand's model (owner poll 2026-10-07, `D-133`).
Allowed adds: `src/auditmanager/analysis/text/proxy.py`,
`tests/integration/analysis_text/test_proxy_adapter.py` (its `TestFailuresMapToTheCatalog` table is
the only pin of the mapping at `df120a8`: `rg -n 'answered with status|_map_http_failure' tests src`).
Required: one parametrised case per newly mapped status, each red under the old mapping; a test that
a body containing a token-shaped string is logged redacted and never returned.

**`W52-FIX-A`** — later validation-stage repair of upheld release-blocking
findings of AUDIT and ATTACK outside SEAL's grant; explicit grant per finding.

### Stage C — from the Stage-B merge (executor; disjoint)

**`W52-RELEASES-API`** — the `auditmanager.releases` context with its `public` module (ALR-05):
`VERSION` (`0.3.0`), `release-notes/schema.json` (shape), a minimal valid
`release-notes/0.3.0.json` and `release-notes/0.2.0.json` placeholders, the shape validator, the
SemVer `sort_key` function, the `build_id` function (§3.1), repository, loader (§3.3),
`ReleasesPort` implementation and composition wiring; `Dockerfile.api` `COPY` of `VERSION`,
`release-notes/`, `uv.lock` (one source per line, explicit `/app/…` destination); the
`release-notes` service; `deploy.sh` and `reset.sh`. Allowed:
`VERSION`, `release-notes/**`, `src/auditmanager/releases/**`,
`src/auditmanager/api/routers/releases.py` (filling the skeleton),
`src/auditmanager/bootstrap/{adapters,composition}.py` (wiring only),
`infra/deploy/Dockerfile.api`, `infra/deploy/compose.server.yml`, `infra/deploy/deploy.sh`,
`infra/deploy/reset.sh`, `infra/deploy/README.md` (the services and restart paragraph),
`tests/integration/releases/**`,
`tests/integration/composition/{test_deploy_script_refusals,test_deploy_image_identity,test_deployed_stack_probe,test_session_register_volume,test_reset_script_refusals}.py`,
`docs/program/W52-RELEASES-API.md`. Required: the loader rules 1–4 each by a test; two runs → one
revision; rollback scenario (database ahead of the image) → exit 0 and hidden; `build_id` equal
for equal content, different for a one-byte change, equal between a checkout and the built image's
`/app`; the `.dockerignore` guard; `getProductVersion` and `listReleases` filtered by `VERSION`;
`whats_new` rules of §3.5 on the server, including "never for an account created after the
release's first load" and "the mark only rises"; loader rules with authored revisions (equal
revision with different content refuses; lower revision is a no-op).

**`W52-RELEASES-WEB`** — §3.5. Allowed: `web/src/entities/release/**`,
`web/src/widgets/version-history/**`, `web/src/features/mark-release-notes-read/**`,
`web/src/_app/**` (account-menu item, banner island, «Что нового» host only),
`web/src/shared/api/version-check.ts` (new) and `web/src/shared/api/index.ts`,
`web/src/shared/config/env.ts` (the build id read) and the one export line in
`web/src/shared/config/index.ts`, `web/.env.example` (one line), `web/src/app/bff/version/route.ts`
(it reads the session through `../session/store` only, never `@/shared/config/server-env`),
`web/tests/guards/server-credential.guard.test.ts` (the `NEXT_PUBLIC_*` name list only),
`web/tests/guards/dashboard-invalidation.guard.test.ts` (the one map entry for the mark-read hook),
`web/tests/unit/styles/screens.ts` (panel, archive and banner states for the contrast census; the
styles live in widget `*.module.css`, never `globals.css`), `tests/e2e/pc01/journey/manifest.json`
(`optional_api` `GET /releases` on every route, and `PUT /me/release-notes` on the first route, where
the journey dismisses «Что нового» once),
`infra/deploy/Dockerfile.web` (the build-id computation inside the existing build `RUN`; no new
`COPY`), `web/src/shared/api/query-keys.ts` (namespace `releases`) with
`web/tests/guards/query-key-shape.guard.test.ts`, `web/docs/PC01_UI_SEAM.md` (§6),
`web/tests/unit/api/configuration-and-cache-keys.test.ts` (namespaces),
`web/tests/contract/narrow-sets.contract.test.ts` (namespaces) — added 2026-10-06 after hand-over,
found by the W53 grants judge, `web/tests/guards/rendered-language.guard.test.ts`
(matrix and fixtures only), `web/tests/unit/release/**`, `docs/program/W52-RELEASES-WEB.md`.
Required: the panel at 780 px with a 400-character item; the banner on a changed build and not on
an equal one; «Позже» per build; the shell renders `whats_new` and marks it read on close; an
unknown `kind` a typed fault; lint and typecheck clean; the live journey's manifest check green.

**`W52-TRANSLATE-01`** (owner poll 2026-10-07, `R-69`) — the human runbooks `docs/manual-tests/*.md`
in English. In Stage C because `W52-SEAL-01` writes `tests/contract/**`, `journey.py` and the head
sentence of `PC-01_prototype.md` before it, and `W52-ACCEPT-01` writes `ALPHA_PUBLIC_ACCEPTANCE.md`
and `manual-alpha-check.sh` after it, so ACCEPT's new sentences are written in English.
**Measured at `df120a8`:** five of the 14 files hold Russian prose — `ALPHA_PUBLIC_ACCEPTANCE.md`
(271 lines, ≈ 70 % of the letters Cyrillic), `README.md` (≈ 45 %), `CP-00_architecture.md` (18 lines),
`CP-01_foundation.md` (6 step lines) and `CP-02_walking_skeleton.md` (3 step lines); the other nine
contain no Cyrillic. Rules:
- unchanged: file names; case and step ids (`MT00-NN`, `A01`…`A12`) — `test_cp00_candidate.py`
  reads `MT00-\d{2}` out of `CP-00` and the CP-00 manual reports under `artifacts/checkpoints/CP-00/`
  cite them; front-matter keys; table shapes; every figure, digest, path and command;
- what the product or a fixture says stays verbatim in Russian inside «…», glossed in English at its
  first use: screen and button labels, messages, seeded finding texts («два эвакуационных выхода» is
  also in `fixtures/recorded/text_analysis/**`, `fixtures/synthetic/ar/expected_issues.json` and
  characterization record 08) — the reviewer compares them with a Russian screen (`R-18`);
- English prose is visible to `test_doc_prose_facts.py`, which scans `docs/manual-tests/` with English
  patterns: every count, head or surface phrase the translation surfaces states the live value, and
  `KNOWN_OUTSTANDING_CLAIMS` stays empty;
- `scripts/manual-alpha-check.sh` keeps its Russian operator prompts (§8); its `RUNBOOK_REL` path does
  not change.

Allowed: `docs/manual-tests/**`; and, only for a change the translation itself forces, each named in
the report: `tests/contract/test_cp00_candidate.py`, `tests/contract/test_validate_bootstrap.py`,
`scripts/validate_bootstrap.py`, `tests/contract/api_v1/test_doc_prose_facts.py`,
`tests/integration/p02_journey/journey.py`, `tests/e2e/p02/test_journey_figures_pinned.py`;
`docs/program/W52-TRANSLATE-01.md`. The list is the integrator's sweep confirmed by two sweeps at
`df120a8`: by path (`rg -l 'docs/manual-tests|ALPHA_PUBLIC_ACCEPTANCE|PC-01_prototype|CP-[01][0-9]_'
--glob '!docs/**' --glob '!artifacts/**'`) and by content (every three-word Cyrillic window of the
runbooks searched in code, tests, fixtures and tools; the hits are product and fixture text the
runbooks quote, and none of the six files above pins a Russian sentence). **Re-sweep at
`W52-FREEZE-01`.** Required: `rg -n '[А-Яа-яЁё]' docs/manual-tests/` lists only quoted product text,
each remaining line accounted for in the report; the CP-00 case set and the count of 11 checkpoint
runbooks unchanged; `test_doc_prose_facts.py`, `test_surface_counts_in_prose.py` and
`test_cp00_candidate.py` green; `git diff --check`. The full gate is the integrator's at the
Stage-C merge.

### Stage C2 — from the Stage-C merge (executor; disjoint)

**`W52-RELNOTES-01`** — the prose rules and texts: `release-notes/dictionary.json`, bad-entry
fixtures, the final `0.3.0.json` and `0.2.0.json` drafts (W48–W52 user-visible changes only; every
sentence names the commit or test that shows it), `docs/program/RELEASE_PROCESS.md`,
`docs/program/RELEASES.md` (header and empty table). Allowed: `release-notes/**` except
`schema.json`, `tests/contract/release_notes/**`, `web/tests/unit/release-notes/**`,
`docs/program/RELEASE_PROCESS.md`, `docs/program/RELEASES.md`, `docs/program/W52-RELNOTES-01.md`.

**`W52-ACCEPT-01`** — closes `D-121`: the acceptance pack reads `getProductVersion` with its reviewer
credential, computes the candidate's `build_id` from the candidate tree by **its own**
implementation of §3.1, reading the root list from `Dockerfile.api`'s `COPY` lines at run time as
`verify-deployed.sh` does, and records the build as **measured**. Allowed:
`scripts/manual-alpha-check.sh`, `tests/e2e/pc01/journey/verify-acceptance.mjs`,
`tests/contract/test_alpha_acceptance_command.py`, `Makefile` (`alpha-acceptance` target only),
`docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`, `docs/program/ALPHA-MANUAL-01.md`,
`docs/program/W52-ACCEPT-01.md`. Its runbook sentences are written in English, on `W52-TRANSLATE-01`'s
merged text. Required: the two implementations agree on the merged tree; a
mismatching build fails the pack; `shellcheck`.

### Stage D — judging (fresh contexts), then FIX

Risk tier: contract, migration and deploy are touched → **two cross-judges**
under the proposed `R-V4`. Stage D is deferred to D-139/D-140; its checks
remain required for a release verdict and do not run as part of code-only close.

- `W52-QA-01`: standard form; `tests/integration/qa_w52/**`, `web/tests/unit/qa_w52/**`.
- `W52-JUDGE-X` (attacker, built stand): the three operations as every role set, a guest, an
  incomplete profile and an admin-only account (`markReleaseNotesRead` → 204); a lower mark after a
  higher one (no-op); a future or unknown
  `read_through`; the loader against tampered, missing, duplicated and newer-than-image files; a
  rollback deploy; an unchanged tree recreates nothing (real `deploy.sh` run twice on a disposable
  host, fingerprints recorded); the banner cannot loop; `/bff/version` without a session is 401.
- `W52-JUDGE-Y` (architecture and truth): ALR-05 for `releases`; no rule in a component
  (`whats_new` only on the server); the facts file is the only count literal; the gate measurement
  reproduces; every debt row closed by this wave is closed by its own check command.
- `W52-NOTES-JUDGE` (§3.4): every claim against the diff; re-run on the
  later release-validation candidate.
- `W52-FIX`: standard form.

### `W52-INT-CLOSE` (integrator)

Exception to `IDENTITY-WAVES.md` §10: development close records exact code
and focused-check evidence on `origin/dev`, with D-137–D-140 open and no
`GATE OK` claim. The following register work belongs to release validation/close and
requires its named re-measurements: close `D-66`, `D-72`, `D-78`,
`D-79`, `D-68` with their re-measured checks; repair the register's §2 owner table, §3 lag
sentence and header count; close `D-120` (`R-V3`) and `D-121` (`W52-ACCEPT-01`); re-slot `D-122` to
W63; slot `D-123` to W53 with the backup target (this machine until after beta); narrow `D-133` to
its remaining half (`RunStatus` message and the `PROXY_LLM_MODEL` refusal, `W56-PLAN.md` §A3.5)
with `W52-DEBT-CODE`'s check; register this
wave's own debts (at least: `Dockerfile.api`-only changes do not move `build_id`; no served
technical version view; the A6 shortfall if the target was missed).

### `W52-INT-MAIN-01` (integrator, on the owner's instruction naming the SHA)

Two-level gate of `W48-PLAN.md` §12 — release acceptance counts `provider_mode` `proxy` as live, never
`recorded` (owner ruling `R-65`, recorded after this plan was judged) — plus: the `release-notes` service ran on the host; the panel
shows `0.3.0` and the archive; «Что нового» opens once for an existing account; the acceptance pack
records a measured build equal to the candidate's; tag `v0.3.0`; the first row of `RELEASES.md`;
`W52-NOTES-JUDGE` passed on this SHA.

## 5. Integration order

1. `W52-RULE-01`, `W52-FREEZE-01` (current-tree sweep; gate timing deferred).
2. Stage A code: reconcile merged FACTS and PINSWEEP, then GATE; run
   `pin_sweep --check` on Stage-B task files. AUDIT/ATTACK and gate measurement
   run in the later validation stage.
3. Stage B code: SEAL ∥ DEBT-GUARDS ∥ DEBT-CODE; merge SEAL first.
4. Stage C: RELEASES-API ∥ RELEASES-WEB ∥ TRANSLATE; merge API, then WEB, then TRANSLATE.
5. Stage C2: RELNOTES ∥ ACCEPT; merge RELNOTES, then ACCEPT.
6. `W52-INT-CLOSE` may close development implementation with D-137–D-140 open.
7. Separate validation/correction: AUDIT, ATTACK, Stage D QA ∥ X ∥ Y ∥
   NOTES-JUDGE, cross-examination, FIX, NOTES-JUDGE re-run and full exact-candidate
   gate; then `W52-INT-MAIN-01` only on direct owner instruction.

## 6. Ownership matrix

| Hotspot / path family | Owner (stage) | Parallel writer |
| --- | --- | --- |
| `expected_facts.json`, the pin files, `CONTRACT_PIN_REGISTRY.md` | FACTS (A), then SEAL (B) | none |
| `Makefile` | GATE (A, battery recipe), ACCEPT (C2, `alpha-acceptance`) | none at the same time |
| `tests/integration/auth/**` | GATE (A), then SEAL (B) | none at the same time |
| `contracts/**`, migration `0016`, `src/auditmanager/api/**`, `bootstrap/{adapters,composition}.py`, `access/references.py`, generated client, `web/openapi/**`, `FRONTEND_LOCK.json`, `tests/contract/**` (but four), `web/tests/contract/**`, `tests/integration/{api,auth,composition,db}/**`, the live sentences of `CURRENT_STATE.md` and `ALPHA_ROADMAP.md` | SEAL (B) | DEBT-GUARDS on its four files only |
| `src/auditmanager/bootstrap/{adapters,composition}.py`, `src/auditmanager/api/routers/releases.py` | SEAL (B), then RELEASES-API (C, wiring and filling only) | none at the same time |
| `src/auditmanager/releases/**`, `VERSION`, `release-notes/schema.json`, `Dockerfile.api`, `compose.server.yml`, `deploy.sh`, `reset.sh`, `infra/deploy/README.md` (services paragraph), the five composition tests | RELEASES-API (C) | none |
| `web/tests/guards/dashboard-invalidation.guard.test.ts` | DEBT-GUARDS (B), then RELEASES-WEB (C, one map entry) | none at the same time |
| `web/src/_app/**`, `shared/api/version-check.ts`, `shared/config/{env,index}.ts`, `query-keys.ts`, `PC01_UI_SEAM.md` §6, `configuration-and-cache-keys.test.ts`, `narrow-sets.contract.test.ts`, `rendered-language.guard.test.ts`, `server-credential.guard.test.ts`, `styles/screens.ts`, `journey/manifest.json`, `Dockerfile.web`, `web/.env.example` | RELEASES-WEB (C) | none |
| `release-notes/**` (but `schema.json`), `RELEASE_PROCESS.md`, `RELEASES.md` until INT-MAIN | RELNOTES (C2) | none |
| acceptance pack files | DEBT-GUARDS (B, one test file), ACCEPT (C2) | none at the same time |
| `docs/manual-tests/**` | SEAL (B, the `PC-01_prototype.md` head sentence), then TRANSLATE (C), then ACCEPT (C2, `ALPHA_PUBLIC_ACCEPTANCE.md`) | none at the same time |
| `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_doc_prose_facts.py`, `journey.py`, `test_journey_figures_pinned.py`, `scripts/validate_bootstrap.py` | SEAL (B, within its grant), then TRANSLATE (C, only a change the translation forces) | none at the same time |
| `analysis/text/proxy.py`, `test_proxy_adapter.py` | DEBT-CODE (B) | none |
| `CURRENT_STATE.md` (other sentences), `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `origin/dev`, `origin/main`, tags | integrator | none |

## 7. Stop conditions

`W48-PLAN.md` §14, plus: a pin outside a lane's grant (stop and widen, never edit); the start-up
`build_id` differs between a checkout and the image; the loader would need to run inside `migrate`
or the API process; a release-notes claim cannot be evidenced; any operation would be open to a
guest; the `contract_version` would have to move.

## 8. Non-goals

Online scans (`D-122`, W63); a served technical version view; editing release notes in the
interface; SMTP; `pytest-xdist`; impacted-test selection; moving `contract_version`; any change to
how `main` deploys beyond `R-V3`; the operator prompts of `scripts/manual-alpha-check.sh` in English
(they are the tool's conversation with the operator, not a runbook; extending `R-69` to them adds
that script and `tests/contract/test_alpha_acceptance_command.py`, which pins its Russian refusals);
`D-133`'s `RunStatus` message and `PROXY_LLM_MODEL` refusal (W56a).

## 9. Estimate

This is the pre-deferral estimate for the whole original wave. The split
between code-only development and later validation has not been re-costed;
it is not an estimate for the current development close alone.

Critical path in active hours, from W48's measured lane, judge and gate times: freeze with
baseline 1.0; Stage A 1.5 + merge, measurement and triage 1.0; Stage B (SEAL, allowing one stop)
3.0 + merge 0.5; Stage C 2.0 + merge 0.5; Stage C2 1.5 + merge 0.5; Stage D 1.5 + FIX 1.5 + gate
0.5; INT-CLOSE 1.0 — **≈ 16 h**, plus **≈ 1.5 h** for `W52-TRANSLATE-01` (amendment of 2026-10-07)
when Stage C's lanes run one after another, as this host has run lanes since W53 was costed
(`ROADMAP-TO-BETA.md` §6.2) — **≈ 17.5 h**. At the measured overhead of W46–W48 (1.5–2.0) that is **3–4
working days**; **P50 ≈ 2.5–3 days assumes the A2 target overhead of 1.25–1.5**; P80 ≈ 4. Not the
2 days of revision 1. The owner's confirmation in `W52-RULE-01` and the `main` instruction are
outside it.
