# W59-SECTION-IDENTITY-DECISION-01 — section and stage identity before seal

**Decision basis:** `origin/dev` at
`08055ca094a9c3e4676a5907a0b3020f0bee4fb8`, roadmap S-1–S-6 and
C-1–C-4, the accepted domain glossary, and the completed W59 pure
suggestion/confirmation/route/version-pair preparations. This is a design
decision for the later W59 freeze, not a contract, migration or activated
route. W58-code has no close task at this base.

## Identity and ownership

| Fact | Identity and rule |
| --- | --- |
| Project | `ProjectUid` is the working container. A project name or filesystem location never joins versions or grants access. |
| Logical drawing set | `DocumentUid` is the stable set within its current `ProjectUid`; its versions share that UID. `document.section` is the old document-level classification, not an expert confirmation. No new section-set UID is created in W59. |
| Input revision | `VersionUid` names one immutable published PDF/input manifest. `version_ordinal` proves order only and is never a command key. Each run and comparison names its exact `VersionUid`; the current-head pointer cannot silently substitute a newer version. |
| Project stage | `P` or `R` is a separate, explicit **version-bound** classification, named `project_stage` at the future API boundary to distinguish it from analysis `stage_id`. It is absent for old or unclassified versions. Its logical key is `VersionUid`; it does not rewrite immutable PDF/version bytes. |
| Confirmed section | One expert-confirmed code from the complete 15-code catalogue is bound to one `VersionUid`, with confirming `UserUid` and auditable provenance. The same code on another version needs its own confirmation. No filename, text suggestion or legacy `document.section` is a confirmation. |
| Current head | `document.current_version_uid` selects a default for display. Moving it changes no older version's stage, section, run, finding, approval or comparison. A newly published version starts without inherited stage/confirmation. |

The stage and section can be submitted together in one authorized transaction,
but stage is validated as an explicit fact before the section-confirmation
policy runs. Once accepted, the first confirmer is retained on an exact
repeat. A conflicting stage or section cannot be overwritten by the ordinary
command; it needs a separately specified, append-only correction with actor,
reason and revision before it can affect later runs. The first W59 seal may
refuse corrections while that workflow is absent.

This logical version-bound classification should be stored outside the
immutable `document_version` input row, or by an equally strong mechanism
that preserves its no-UPDATE/no-DELETE guarantee. Its API projection is still
an attribute of `DocumentVersion`, satisfying S-1. The physical schema,
constraint names and endpoint names belong to the later SECTION-SEAL owner.
Existing versions remain unclassified after forward migration; no backfill
from legacy section, filename, current head or display ordinal is valid.

## Authorization and execution

The command service reads the authenticated actor's current role set, the
requested `VersionUid`, its `DocumentUid` and current `ProjectUid`, plus the
stored stage/confirmation under one transaction. Only an account with the
`expert` role may confirm; `admin` alone does not imply expert. The service
requires exact project/version membership and rejects a foreign version.
The current product has role-based access, not a per-project membership ACL;
W59 must not invent one from names, paths or client-provided roles. A later
project ACL reseal must add its own authoritative membership lookup.

Run start reads the **persisted** version stage and confirmation and resolves
the confirmed code through a sealed map of executable profiles. Missing stage,
missing confirmation, unknown code or unavailable profile refuses. A
suggestion or `document.section` never supplies AR as a fallback. The
client's section value, if displayed, cannot authorize a run. An existing
run remains pinned to the version/profile facts recorded at its start;
changing the document current head cannot reroute it.

## Comparison and later functions

- **W59 version comparison:** caller names `ProjectUid`, `DocumentUid` and two
  ordered `VersionUid` values. The source and target must belong to that same
  set and, for the version-comparison lane, have the same explicit `P` or `R`
  stage and confirmed section. A stage/section mismatch is not silently
  relabelled as an ordinary version pair; the user must choose the later
  stage-comparison lane or obtain an explicit correction. Raw differences
  remain separate from AI synthesis and expert decisions.
- **W62 П/Р comparison:** caller names two versions of the same `DocumentUid`,
  one classified `P` and one `R`, with a matching confirmed section. It never
  groups by filename, project name, page label or nearest upload date. The
  current schema has no `ObjectUid`; a cross-document comparison described as
  “one object” needs a separately frozen object identity and mapping. Until
  then, that broader case is explicitly unsupported.
- **W63 Form 7 / section optimization:** source evidence is addressed by
  exact project, set, version and confirmed section; a target project/set is
  also named explicitly and any cross-project relationship must be approved.
  The section code filters the workflow but is not an object, document or
  proposal identity. No automatic propagation by matching names or folders.

## Seal prerequisites and test contract

Before SECTION-SEAL, close W56b and W58-code under the code-first dependency
order. The existing W58 reports are offline preparations; they do not close
its debt/recovery work or prove an isolated application DB+Blob restore.
W54's verified corpus-base dump is a different operation. Freeze the W59
task from the then-current `origin/dev` with new API/domain/error/stage
digests, migration head, pin sweep and one named owner for contract, migration
and run-start integration. Do not preassign a migration number from today's
`0022_findings_v2` head.

The owner must preserve migration 0011's historical fourteen-code record,
add `PS` to the current 15-code API/Python/DB/dashboard vocabulary, and update
the old test that currently equates today's enum with legacy fourteen while
retaining a historical legacy control. The seal introduces explicit
version-stage and version-confirmation state, authenticated write/read APIs
and run-start refusal. Forward upgrade keeps old rows and historical runs
readable without fabricating classifications. Activation may leave old
versions ineligible for new analysis until an expert classifies them.

Addressable tests for that owner:

1. Enumerate all 15 codes and names across the public contract, Python
   registry, DB constraint and dashboard; distinguish `PS` from `PB`.
2. Upgrade a database with existing documents/versions/runs and assert NULL
   stage/confirmation, unchanged source digests, and intact old reads.
3. Assert expert-only insert, exact retry preserving first confirmer,
   concurrent uniqueness, foreign project/version refusal and conflicting
   choice refusal.
4. Start a run with missing stage, missing confirmation, unknown code and
   unavailable profile; each refuses without AR fallback. A filename
   suggestion and legacy `document.section` cannot bypass the guard.
5. Advance `current_version_uid` and prove old run pins and confirmation do
   not move; new version is unclassified. Compare explicit same-set/same-stage
   versions and reject mismatched stage or section in the W59 lane.
6. Recheck served OpenAPI against frozen contract, migration forward path,
   current pin registry and focused section/run/comparison tests. The full
   beta gate follows the final code candidate under R-135.

**Limits and rollback:** this document changes no executable path, contract,
schema, production data or remote ref. The later owner must specify rollout
and forward-repair policy for the new persistence and run guard. This two-file
decision can be removed or superseded before seal; no feature flag is needed
for it.

## Checks and handoff

- Program task governance: **16 passed**; direct findings for this task are
  empty.
- Document prose and surface-count guards: **77 passed**.
- The task's seven frozen SHA-256 values matched the exact base tree;
  migration head remained `0022_findings_v2`.
- `git diff --check` and exact changed-path proof: passed. Only this report
  and `docs/program/tasks/W59-SECTION-IDENTITY-DECISION-01.md` were added.
- No application runtime test, DB, Docker, provider, network or complete gate
  was run.

The integrator can use this as a frozen design input. It does not mark
W58-code complete or give SECTION-SEAL permission to edit any hotspot.
