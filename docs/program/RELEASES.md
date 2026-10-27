# Product release ledger

Each row records one deployed and verified product release. The release
integration task fills it from the exact published SHA, image measurements,
full-gate log and host verification. No development candidate is entered as a
release. A row marked `not deployed` or `host verification owed` is a prepared record: it travels with the
release commit, every `pending` cell in it is replaced by the release
integration task from the exact published SHA, and the marker is removed only
after host verification.

| Tag | SHA | API `build_id` | Web `web_build_id` | `contract_version` | Migration head | Prompt bundle hash | Profile bundle hash | `GATE OK` evidence | Norms snapshot (from W55) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v0.4.0` | `2653dbf49e9f37fa891dd6e47b396650a215542d` | `be7bf8dae6d63d63c` | not measured (stand environment) | `1.0.0-draft.1` | `0017_execution_queue` | `934705c04a71…` | `30053740f569…` | none — waived by `R-87`; deploy run `38219064192` verified (`W53-INT-MAIN-01.md`) | — |
| `v0.5.0` | `23fd729dbb06c642be0588017f6b195305e2e53e` | `bf9407822414591b3` | not measured (stand environment) | `1.0.0-draft.1` | `0020_norms_search` | `934705c04a71…` | `30053740f569…` | `W55A-INT-GATE-01.md` (GATE OK on this SHA); deploy run `38356461757` | — |
| `v0.6.0` | `37393a979a430e490843d7f410e9eca9491a4ea1` | `bf03d913bde596a77` (computed from tagged tree) | not measured (stand environment) | `1.0.0-draft.1` | `0021_portal_bundles` | `934705c04a71…` | `30053740f569…` | `W55B-INT-MAIN-PREP-03.md` (R-125 same-SHA gate completion); deploy run `38897018419`, owner-run host verification in `W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`; five live checks waived in `W55B-INT-TAG-01.md` | — (not promoted) |
| `v0.7.0` — on `origin/main`, **host verification owed**, not tagged | `48c8e34ccd08a58ae61cbd09ecdba49066a5ad46` (the owner's pull request #3) | `bbbab3c0dfb856a39` computed from `git archive` of that SHA (`compute_build_id()`) | not measured (stand environment) | `1.0.0-draft.1` | `0028_classification_corrections` | `934705c04a71…` (builtin AR profile, unchanged since `v0.6.0`) | `30053740f569…` (builtin AR profile, unchanged since `v0.6.0`) | **none on this tree.** The owner merged pull requests #2 and #3 into `main` without a gate (`R-141e`); `NIGHT-1020-GATE-0-7-0-01.md` is an `R-125` completion of an earlier lineage and covers neither the classification correction, the normative references nor the hardening slices; light checks only (`RELEASE-0-7-0-RECORD-01.md`). Deploy workflow run `39571427597`, success, reported by the integrator and not re-read here; `infra/deploy/verify-deployed.sh` on the host: **pending** | none — the normative corpus is not imported on the stand |

## `v0.9.0` development candidate — section analysis, large documents and sheet pairing

Prepared by `RELEASE-0-9-0-DEV-01` on `origin/dev` only: `VERSION=0.9.0` and `release-notes/0.9.0.json` (revision 1, 2026-10-28, seven items; dated the day after `0.8.2` because the form rule wants strictly descending dates and `0.8.2` carries 2026-10-27). The note describes what an expert can see on this tree and no more: the approval and withdrawal of a sheet pairing in the version comparison with the recomputed differences of the approved pairs, and a model summary of those pairs that in this build exists only for recorded cases; the 14 section profiles at `1.1.0` or `1.2.0`, status `reviewed` with no human review, and the same-document total-against-rows checks asked of 12 of them; whole-page windows for a text above one model call, each window analysed on its own under one cost ceiling; «Спецификация и цены» and «Предложения» for a version confirmed in any of the 15 sections; the removal of the ordinary АР start (only the six-check group remains); the corrected sentence about «Без раздела» on the dashboard; and an executor connection of the kind «Команда по SSH» that can now be routed and chosen, with the plain `http://` address rule of the connection settings. The note claims no measured quality for any prompt and no speed-up. `release-notes/0.8.2.json` is not edited. Every claim is traced to a commit and a test in `RELEASE-0-9-0-DEV-01.md`. There is no table row, no tag, no `origin/main` push, no complete gate (`D-205`), no independent note judge yet and no stand deployment.

## `v0.8.2` candidate — choosing the executor of a run

Prepared by the parallel-runs slices (`EXEC-PAR-START-01`, `EXEC-PAR-QUEUE-01`, `EXEC-PAR-WEB-01`): `VERSION=0.8.2` and `release-notes/0.8.2.json` (revision 1, 2026-10-27, five items; dated the day after `0.8.1` because the form rule wants strictly descending dates). The note describes what an expert sees and no more: the «Исполнитель» choice in the start control, the executor and its model on the run, the waiting label, the repeat that keeps the executor, and one run at a time per executor. It claims no parallel speed-up: the worker keeps one slot until an administrator sets `AUDITMANAGER_WORKER_SLOTS`, and a named executor needs the database provider source. There is no table row and no tag here; a row is entered only from the deployed and host-verified tree. The operator's check is `EXEC-PAR-OPERATOR-CHECK-01.md`.

## `v0.8.1` development candidate — pack status and the pack-gated six-check start

Prepared by `RELEASE-0-8-1-DEV-01` on `origin/dev` only: `VERSION=0.8.1` and `release-notes/0.8.1.json` (revision 1, 2026-10-26, seven items). The note describes what an expert can see on this tree and no more: «Настройки анализа» says whether the reviewed AR v3 pack is installed and prints the reviewer's attached record with the sentence that the system does not check it; the version's run list draws «Запустить шесть проверок АР v3» only when the pack is installed and opens the started group's review; that review panel and the run page of an AR v3 Run keep the result a provisional citation for expert verification, with no canonical finding and no numerical conclusion; the quotation caption names the page only (`R-43`, `D-50`); eight widget stylesheets stop drawing borders in the text colour; the classification history list has a gap. `release-notes/0.8.0.json` is not edited. Every claim is traced to a commit and a test in `RELEASE-0-8-1-DEV-01.md`.

No reviewed pack is installed on any stand, so on a deployed tree the note's start button is not drawn and the group review has no group to show; this candidate proves the screens, not a verified citation. There is no table row, no tag, no `origin/main` push, no complete gate (`D-205`), no stand deployment and no live or credentialed journey for the new screens. The `v0.7.0` host verification and tag stay owed as recorded below. To roll back, revert `VERSION`, the note file and the version pins in the two release tests and `CURRENT_STATE.md` together.

## `v0.8.0` development candidate — source-status preview only

The owner requested `VERSION=0.8.0` on `origin/dev` and will handle any later `main` publication. The authenticated «Настройки анализа» screen now shows the frozen Ф1.3 C01–C22 beta dispositions in six groups. Its source JSON is byte-identical to the server's policy and says explicitly that v3 Runs and numerical conclusions are unavailable. This candidate does **not** meet the previously planned W57a `v0.8.0` milestone of reviewed maps and verified citations. The independent [local corpus qualification](AR-BETA-LOCAL-CUSTODY-01.md) is only on a disposable lane; neither the production stand nor the served Run path has its six verified sets. The user-facing note `release-notes/0.8.0.json` describes this narrower capability and no more. There is no tag, `main` push, complete gate, stand deployment or verified v3 citation associated with this development candidate.

## `v0.7.0` technical record (on `origin/main`, host verification owed)

Written by `RELEASE-0-7-0-RECORD-01`. The owner merged `dev` into `main` twice on 2026-10-21: pull
request #2 (`829117d3`, `R-141e`, `VERSION` still `0.6.0`, workflow run `39561204544`) and pull request #3
(`48c8e34ccd08a58ae61cbd09ecdba49066a5ad46`, 11:43 +03, workflow run `39571427597`, success). Both run
ids come from the integrator's report and were not re-read here (`gh` is not installed on this host).
The second merge carried the record lane (`dfae803b`: `VERSION` `0.7.0`, `release-notes/0.7.0.json`,
this ledger) **and** four slices merged after it, so the tree on `main` is not the tree the record
was written on. The first deployed form of the tree reported `v0.6.0` and `build_id`
`b60e02fff4f168d21`; the release tree has `bbbab3c0dfb856a39` (`VERSION`, `release-notes/` and `src`
are inputs, so the images were rebuilt). The user layer is `release-notes/0.7.0.json` (revision 2,
after the independent judge's edits); every claim in it is traced in `RELEASE-0-7-0-RECORD-01.md`.
Between `dfae803b` and `48c8e34c` the contract, the migrations, the release notes and `VERSION`
are byte-identical.

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
  in `infra/deploy/proxy/nginx.conf` and `tls-server.conf`. The tree on `main` also changes the edge
  (`HARDEN-AUTH-EDGE-01`): `POST /api/v1/auth/token` is throttled per client address (6 requests a
  minute, burst 10), and both upload locations first ask the application who the caller is
  (`auth_request`), so a stranger is refused with a typed `401` before the upload body is read.
- **Also in the tree, not in the notes** (nothing in it is a user-facing claim; each has its own report):
  `ACCESS-STORAGE-HARDEN-01` (a queue lock for every login writer, a bulkhead for norms search, the
  order of the upload door's headers, a memory of revoked credentials at the seam), `SPEC-TABLE-RECORDING-01`
  and the specification reader (wrapped-above cells, continued pages and the manufacturer are read from
  the saved text; a vendor's legal form is optional when matching), `RECOVERY-REBASE-01` (the W58
  restore drill rebased onto head `0028`), `BETA-LIVE-JOURNEY-01` (the stand acceptance script and
  the end-to-end journey), and two web repairs (a double press sends one request; a carried decision
  stays shown after the re-read).
- **Dependencies.** No dependency or lock change since `v0.6.0`; `infra/deploy/compose.server.yml`, `deploy.sh` and `env/alpha.env.example` differ only in comments.
- **Not part of this release.** The recorded-only AR v2 profile, retrieval and citation
  preparations, the certified-source preparations and the restore drill are unserved
  (`CURRENT_STATE.md`). The 13 non-AR text profiles are drafts; recorded-mode proof exists for
  four of them with synthetic recordings only. **The normative corpus is not imported on the
  stand**: «Нормы» search, the catalogue and «Нормативные ссылки» answer a typed refusal until the
  import and the administrator's designation of a snapshot have run
  (`STAND-NORMS-IMPORT-RUNBOOK-01.md`); runs started before the designation pin no snapshot.
- **Verification still owed.** (1) A literal `GATE OK` does not exist for this tree or for `829117d3`.
  (2) The owner's instruction for `origin/main` was given by his own merge, not as a named-SHA
  instruction to an integrator. (3) `infra/deploy/verify-deployed.sh` on the host for the same tree:
  **pending**; the `v0.7.0` tag follows it and the owner's say-so. (4) Live and manual acceptance of the new screens: not run;
  no credentialed journey has exercised them. (5) `tests/e2e/pc01/test_acceptance.py` needs real
  services and was not run by this task.
- **Rollback.** Revert through a reviewed forward commit with a fresh gate and host
  verification (`RELEASE_PROCESS.md`); never move `main` backward. The schema cannot be walked
  back by an image swap alone: the `0022` and `0023` downgrades refuse once findings exist, and
  the `0024`–`0028` downgrades drop the classification, correction, assignment, price-list and
  proposal tables with a logged row count. Restoring data means the host's pre-deploy database
  dump (`infra/deploy/reset.sh`; no off-host backup exists). The loader leaves a `0.7.0` row
  above a running `VERSION` untouched, so a `0.6.0` image hides it.
