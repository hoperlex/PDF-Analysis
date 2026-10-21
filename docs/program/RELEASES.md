# Product release ledger

Each row records one deployed and verified product release. The release
integration task fills it from the exact published SHA, image measurements,
full-gate log and host verification. No development candidate is entered as a
release. A row marked `not deployed` is a prepared record: it travels with the
release commit, every `pending` cell in it is replaced by the release
integration task from the exact published SHA, and the marker is removed only
after host verification.

| Tag | SHA | API `build_id` | Web `web_build_id` | `contract_version` | Migration head | Prompt bundle hash | Profile bundle hash | `GATE OK` evidence | Norms snapshot (from W55) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v0.4.0` | `2653dbf49e9f37fa891dd6e47b396650a215542d` | `be7bf8dae6d63d63c` | not measured (stand environment) | `1.0.0-draft.1` | `0017_execution_queue` | `934705c04a71…` | `30053740f569…` | none — waived by `R-87`; deploy run `38219064192` verified (`W53-INT-MAIN-01.md`) | — |
| `v0.5.0` | `23fd729dbb06c642be0588017f6b195305e2e53e` | `bf9407822414591b3` | not measured (stand environment) | `1.0.0-draft.1` | `0020_norms_search` | `934705c04a71…` | `30053740f569…` | `W55A-INT-GATE-01.md` (GATE OK on this SHA); deploy run `38356461757` | — |
| `v0.6.0` | `37393a979a430e490843d7f410e9eca9491a4ea1` | `bf03d913bde596a77` (computed from tagged tree) | not measured (stand environment) | `1.0.0-draft.1` | `0021_portal_bundles` | `934705c04a71…` | `30053740f569…` | `W55B-INT-MAIN-PREP-03.md` (R-125 same-SHA gate completion); deploy run `38897018419`, owner-run host verification in `W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`; five live checks waived in `W55B-INT-TAG-01.md` | — (not promoted) |
| `v0.7.0` — candidate, **not deployed**, not tagged | pending: the exact release commit, filled after the push and host verification | `b42b8bb12505a5e46` computed from the candidate tree `88ff0e4b` (`compute_build_id()`; recompute on the exact SHA) | not measured (stand environment) | `1.0.0-draft.1` | `0028_classification_corrections` | `934705c04a71…` (builtin AR profile, unchanged since `v0.6.0`) | `30053740f569…` (builtin AR profile, unchanged since `v0.6.0`) | **none on this tree.** The owner merged `829117d3` into `main` without a gate (`R-141e`); `NIGHT-1020-GATE-0-7-0-01.md` is an `R-125` completion of the predecessor lineage and does not cover the classification correction or the normative references; this record is accepted on light checks (`RELEASE-0-7-0-RECORD-01.md`) | none — the normative corpus is not imported on the stand |

## `v0.7.0` technical record (candidate, not deployed)

Written by `RELEASE-0-7-0-RECORD-01` on top of `origin/main` `829117d3`, which the owner
merged himself (pull request #2, `R-141e`) with `VERSION` still `0.6.0`; the deploy workflow
for that merge is recorded as run `39561204544`, success, 12:22 +05 (taken from the
integrator's report, not re-read by this task). The first deployed form of this tree therefore
reports `v0.6.0` and `build_id` `b60e02fff4f168d21`; the release commit adds only `VERSION`,
`release-notes/0.7.0.json`, the two pins that follow the new entry, two test repins and records,
and moves `build_id` to the value in the row. The user layer is `release-notes/0.7.0.json`
(revision 2, after the independent judge's edits); every claim in it is traced in `RELEASE-0-7-0-RECORD-01.md`.

- **Version.** `VERSION` moves `0.6.0` to `0.7.0`. The loader appends revision 2 of `0.7.0` at
  deploy; the highest non-archive entry equals `VERSION`. `VERSION` and `release-notes/` are
  `build_id` inputs, so publishing this record rebuilds the images and shows the update banner.
- **API surface.** 47 paths / 54 operations / 123 schemas in the `v0.6.0` tree become
  73 / 83 / 242 (29 added operations, none removed or moved; `contract_version` stays
  `1.0.0-draft.1`). `getRunNormVerification` answers a typed 503 until a verified reader exists
  and is claimed in no note. The error catalogue grows from 24 to 25 codes
  (`model_identity_mismatch`).
- **Migrations.** Head `0021_portal_bundles` becomes `0028_classification_corrections`; `0022`
  to `0028` were applied forward by the deploy of `829117d3`. `0022` has one data step: it sets
  `finding.canonical_observation_id` from each finding's only observation and aborts if a finding
  has not exactly one. `0023` adds nullable columns and empty tables and activates no v2/v3
  profile. `0024` creates the classification table empty: **every version that existed at deploy
  stays unclassified, and run start and re-audit refuse an unclassified version** until an
  expert confirms its stage and section. `0025`–`0027` create empty assignment, price-list,
  vendor-list and optimisation-proposal tables. `0028` adds the append-only correction table and
  the current-classification views and replaces one trigger function; it backfills nothing.
- **Read models and exports.** The dashboard's per-section counts follow the stage and section
  an expert confirmed (corrected or not) for each document's current version; documents without
  a confirmation fall in «Без раздела». The run CSV grows from 17 to 19 columns (`severity`,
  `severity_proposed`); the Excel export writes the screens' Russian labels.
- **Proxy.** The two upload locations are widened to admit `.../documents/{document_uid}/versions`
  in `infra/deploy/proxy/nginx.conf` and `tls-server.conf`; size, timeout and throttle lines are
  unchanged. Between the predecessor candidate and `829117d3` only comments in that tree changed.
- **Dependencies.** No dependency, lock or compose change since `v0.6.0`.
- **Not part of this release.** The recorded-only AR v2 profile, retrieval and citation
  preparations, the certified-source preparations and the restore drill are unserved
  (`CURRENT_STATE.md`). The 13 non-AR text profiles are drafts; recorded-mode proof exists for
  four of them with synthetic recordings only. **The normative corpus is not imported on the
  stand**: «Нормы» search, the catalogue and «Нормативные ссылки» answer a typed refusal until the
  import and the administrator's designation of a snapshot have run
  (`STAND-NORMS-IMPORT-RUNBOOK-01.md`); runs started before the designation pin no snapshot.
- **Verification still owed.** (1) A literal `GATE OK` does not exist for this tree or for
  `829117d3`. (2) The owner's separate instruction naming the exact SHA for `origin/main`
  (`AGENTS.md` section 6). (3) The workflow run and `infra/deploy/verify-deployed.sh` on the
  host for the same tree. (4) Live and manual acceptance of the new screens: not run; no
  credentialed journey has exercised them. (5) `tests/e2e/pc01/test_acceptance.py` needs real
  services and was not run by this task.
- **Rollback.** Revert through a reviewed forward commit with a fresh gate and host
  verification (`RELEASE_PROCESS.md`); never move `main` backward. The schema cannot be walked
  back by an image swap alone: the `0022` and `0023` downgrades refuse once findings exist, and
  the `0024`–`0028` downgrades drop the classification, correction, assignment, price-list and
  proposal tables with a logged row count. Restoring data means the host's pre-deploy database
  dump (`infra/deploy/reset.sh`; no off-host backup exists). The loader leaves a `0.7.0` row
  above a running `VERSION` untouched, so a `0.6.0` image hides it.
