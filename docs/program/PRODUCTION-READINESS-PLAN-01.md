# PRODUCTION-READINESS-PLAN-01 — the road from `origin/dev` to the production release

Written 2026-10-26 by lane `production-adr-pack-01` ([task](tasks/PRODUCTION-ADR-PACK-01.md), [report](PRODUCTION-ADR-PACK-01.md)); revised the same day after the judge's findings and the owner's second poll round (`R-146o`…`R-146v`).
It plans; it builds nothing, claims no approval and changes no state of the stand. The owner's decisions are `R-146a`…`R-146v`
(`OWNER_RULINGS_2026-09-17.md` section 3.46) and are quoted only through those rows. The architecture is in
[`ADR-0021`](../architecture/adr/ADR-0021-production-topology-and-operations.md),
[`ADR-0022`](../architecture/adr/ADR-0022-production-data-governance.md),
[`ADR-0023`](../architecture/adr/ADR-0023-production-identity-and-access.md) and
[`ADR-0024`](../architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md). Every `AD-nn` named below is the architect's
implementation decision within `R-146`. After the polls (`R-146o`…`R-146z`) every one is confirmed except two: `AD-04` (memory and log limits from a VPS measurement) and the ACME mechanism of `AD-01`, which were not polled. The rest are confirmed as follows:
`AD-01` as to the server name only (`R-146p`), `AD-03` (`R-146t`), `AD-06` (`R-146o`), `AD-11` (`R-146s`), `AD-14` (`R-146u`), `AD-15` (`R-146v`), `AD-17` (`R-146x`), `AD-19` (`R-146z`), and `AD-02`, `AD-05`, `AD-07`, `AD-08`, `AD-09`, `AD-10`, `AD-12`, `AD-13`, `AD-16` by `R-146w` as written
at commit `83600aed` (the poll showed a one-line summary of each; the mechanisms are the ADRs). `AD-18` is settled by `R-146y` as to what stands until the measurement; the choice it leaves is open.

**Baseline.** The tree of `integration/ar-close-1026` including its commit `1a7f6f65` (`R-146o`…`R-146v`): `VERSION` `0.8.1`, shared contract `1.5.0`, 92 paths / 104 operations / 300 schemas,
migration head `0032_ar_v3_run_group`, 27 error codes. No item below adds a migration, so the head does not move. The local tracking refs `origin/dev` and `origin/main` were not fetched for this plan.
No complete `make gate` can run on the development host (`D-205`).

## 1. How to read the items

- **Size** counts the files an item touches and the hotspots it owns: **S** up to 5 files and no hotspot file; **M** 6 to 15 files, or any file of
  a hotspot (so any edit of `infra/**` is at least M); **L** more than 15 files, or a reseal of the contract's OpenAPI document with its generated client, or the core of `infra/deploy` (`compose.server.yml`, `deploy.sh`, `reset.sh`, `copy-serve.sh`), or a new tool the size of an existing
  one (`product_purge.py` is 1024 lines with 27 guard blocks). A size is a reason, not a forecast; this plan gives no calendar dates (see section 8), only one deadline (`PROD-01`).
- **Executor:** *Sonnet lane* (a code or document lane that returns the `AGENTS.md` section 5 hand-back), *owner* (only the owner can: a host, a
  credential, a payment, a decision), *expert* (a qualified person's review), *integrator* (merges, gates, rulings; `AGENTS.md` section 7.1).
- **Hotspots** are those of `AGENTS.md` section 3: the contract (`contracts/**`, `web/openapi/`, `web/FRONTEND_LOCK.json`, the generated client), the
  migration head (`db/migrations/**`, which no item here touches), the composition root (`src/auditmanager/bootstrap/**`), `infra/**`, and, because several items edit them, the
  recovery tool `scripts/recovery/product_purge.py` and `docs/program/DEPLOYMENT_RUNBOOK.md` (edited only by the infra-chain lane of each wave). One owner per hotspot per wave.
- **Gate regime.** `R-135` defers the complete gate to one separate integration task after the planned code; each lane runs only the bounded tests
  it names. `R-70` and `AGENTS.md` section 8 still require a complete gate before `origin/main` (`PROD-18`). Lane count is bounded by the host condition
  of `CODE-FIRST-TO-BETA.md` section 2.2 (`R-143d`: at most one or two lanes while it holds).

## 2. Work items

### PROD-00 — The owner decides what the polls left open
- **Result:** a ruling record (its number assigned by the integrator) on the items of section 7: `AD-04`, the ACME mechanism of `AD-01`, the `AD-18` choice after `PROD-20`'s measurement, `PROD-19`, and the VPS size. No item below is dispatched on an undecided point that it depends on:
  `PROD-05` waits for `AD-04`, `PROD-01` for the ACME mechanism, `PROD-20`'s implementation for the `AD-18` choice.
- **depends_on:** — · **Hotspots:** `docs/program/OWNER_RULINGS_*.md` (integrator) · **Size:** S (one document) · **Executor:** owner (by direct poll), integrator records.
- **Check (documentation check only: it proves the answer is recorded):** `grep -n "PRODUCTION-ADR-PACK-01" docs/program/OWNER_RULINGS_2026-09-17.md` finds the ruling that answers the poll and names each of those points.

### PROD-01 — The TLS terminator and certificate renewal in `infra/` (`R-146a`, `R-146p`, `R-146s`, `AD-01`)
- **Result:** the stack answers on the production name over a trusted chain with HSTS and a `Secure` session cookie; renewal runs inside the stack; the three listeners of `ADR-0021` section 2 exist (loopback application, public 80 for the challenge and a redirect only,
  public 443 published only when the default-credential check is clean); `verify-deployed.sh` fails on a certificate with fewer than 14 days left; `readiness.sh` `tls` and `plain-http` describe the new layout. `D-191` closes.
- **Deadline:** deployed, with the first real issuance, by **2026-12-16**, fourteen days before the live certificate expires on 2026-12-30 (`D-191`); the date is the architect's and uses the same margin as the expiry check. If it cannot be met, `PROD-21` covers the live stand.
- **depends_on:** the owner names the server name (a deploy variable) before the lane starts (`R-146p`); the ACME mechanism of `AD-01` was not polled, so the lane confirms it with the owner (PROD-00) before building it · **Hotspots:** `infra/**` owner of its wave, `DEPLOYMENT_RUNBOOK.md` · **Size:** L: `compose.server.yml`, five files under `infra/deploy/proxy/`,
  a new `infra/acme/`, `deploy.sh`, `verify-deployed.sh`, `readiness.sh`, `reset.sh`, `copy-serve.sh` (the shared listener function), `infra/deploy/env/alpha.env.example`, the runbook, and the TLS, readiness and refusal composition tests.
- **Executor:** Sonnet lane, then owner (DNS record, inbound 80 and 443, the first issuance against the staging endpoint and then the real one).
- **Check:** `ADR-0021` rows 1 to 6; `pytest -q tests/integration/composition/test_proxy_tls_path.py tests/contract/test_proxy_security_headers.py tests/integration/composition/test_deploy_script_refusals.py tests/integration/composition/test_readiness_command.py`.

### PROD-02 — A deployment fails, and the application port stays shut, while `admin`/`password` is valid (`R-146i`, `R-146s`, `R-146z`, `AD-11`, `AD-19`)
- **Result:** `verify-deployed.sh` and `deploy.sh` run the gate check in the `api` image, end non-zero naming the login and do not publish 443; `reset.sh --restore` and `copy-serve.sh restore-db` end with the same check and
  recreate the `proxy` without the 443 overlay on a finding; `copy-serve.sh restore-db` also raises every `token_epoch`, as `reset.sh --restore` does (`R-52`); `readiness.sh` keeps `R-46` for its other checks. **Only the published seeded pair fails the gate (`R-146z`)**: the gate is a narrower mode of `src/auditmanager/access/check.py` (the seeded `admin` still verifies against the published password), and temporary passwords an administrator issued stay a warning line; the lane edits `check.py` and its tests, not `repository.py`, which `PROD-06` edits in the same wave.
- **depends_on:** PROD-01 (same files and the shared listener function) · **Hotspots:** `infra/**` · **Size:** M: `deploy.sh`, `verify-deployed.sh`, `readiness.sh`, `reset.sh`, `copy-serve.sh`, the library function, `check.py`, four tests, the runbook; the owner repeats the copy key's install (`DEPLOYMENT_RUNBOOK.md` section 13) afterwards.
- **Executor:** Sonnet lane.
- **Check:** `ADR-0023` row 1 and `ADR-0021` row 6; the new tests drive a database with the seeded account and show the exit non-zero and `$DC port proxy 8443` failing, and a mutation (the marked block deleted) turns the refusal off; a test with a temporary password issued by an administrator shows a warning line and exit `0` (`R-146z`).

### PROD-03 — A fresh copy receipt before every migrating deploy (`R-146t`, `AD-03`, `AD-17`; `R-93` continues to bind)
- **Result:** `deploy.sh` has the guard `stand-copy-fresh` of `ADR-0021` section 5: with the `real_data` marker present and a migration pending, it refuses unless the copy record is open, has its dump, is attested for this commit and was quiesced at most 24 hours ago. **No new dump script**: the receipt is the record `copy-serve.sh dump-db`
  writes. The owner installs the copy key (`DEPLOYMENT_RUNBOOK.md` section 13), which `R-110` deferred, before the production release. `R-146x` keeps the full `R-93` attestation (dump, fetch, trial restore, attestation) for every migrating publication after 1.0; the receipt check sits on top of it.
- **depends_on:** PROD-02 (same file `deploy.sh`) · **Hotspots:** `infra/**` · **Size:** M: `deploy.sh`, `test_deploy_script_refusals.py`, the runbook; plus the owner's installation.
- **Executor:** Sonnet lane; the owner installs the key and takes the first real copy.
- **Check:** `pytest -q tests/integration/composition/test_deploy_script_refusals.py -k stand_copy_fresh` (new tests: no record, a record older than 24 hours, an unattested record, another commit's record, and the guard deleted); `ADR-0021` row 9.

### PROD-04 — Database roles: migrator and application, grants as an idempotent step (`R-146n` item 1, `AD-02`)
- **Result:** `api` and `worker` connect as a role that cannot change the schema or truncate; the migrator keeps ownership; the grants are re-applied by one idempotent step after every `migrate` and every restore, so `--no-privileges` dumps cannot leave the application without rights; the
  integration directories of the contexts pass as the application role. **No migration is added**; the head stays `0032_ar_v3_run_group`.
- **depends_on:** PROD-03 (infra files); `AD-02` is confirmed by `R-146w` · **Hotspots:** `infra/**` (no migration head) · **Size:** L: a new `infra/deploy/apply-grants.sh`, `compose.server.yml`, `deploy.sh`, `alpha.env.example`, **`reset.sh`** (`--restore`), **`copy-serve.sh`** (`restore-db`, which drops and recreates `public`),
  **`purge-product-data.sh`** (its `api_python` runs `product_purge` with the api's restricted `DATABASE_URL`, so the `owner-may-write` guard would refuse; it passes the migrator URL), a grant-classification guard test, a restored-from-`--no-privileges`-dump test, and the application-role run of the integration suites.
  `scripts/recovery/product_purge.py` changes only if the guard's message needs it.
- **Executor:** Sonnet lane; the owner supplies the second password on the host and repeats the copy key's install.
- **Check:** `ADR-0021` row 7, repeated after a restore; `pytest -q tests/integration/composition/test_deploy_script_refusals.py tests/integration/composition/test_purge_product_data_script.py tests/integration/recovery/test_product_purge_script.py` plus the new grant tests, on an isolated database.

### PROD-05 — Memory and log limits (`R-146n` item 2, `D-166`, `AD-04`)
- **Result:** every long-running service has a memory limit and rotated logs, with values taken from a measurement.
- **Step 05a (owner):** on the VPS, `infra/deploy/capacity-probe.sh --path root=/` and `docker stats --no-stream` during a 500-page analysis; the readings go
  to the lane. **Step 05b (Sonnet lane):** edits `compose.server.yml` and adds the test below.
- **depends_on:** PROD-04 (same files); 05a needs a deployed stack and the VPS size (open) · **Hotspots:** `infra/**` · **Size:** M (05b: `compose.server.yml` is a hotspot file, plus one test and the runbook).
- **Check:** `ADR-0021` row 8, the full command that prints `[]`.

### PROD-06 — Audit events for sign-in, role grant and password change (`R-146n` item 6, `AD-10`)
- **Result:** the six `access.*` event types of `ADR-0023` are appended in the transaction of the change, from the API, the registration approval and the host command; the purge tool keeps them.
- **depends_on:** — · **Hotspots:** `scripts/recovery/product_purge.py` (one prefix, owner of its wave); no contract, migration or composition-root change is expected (the writer is context-local; if
  injection is needed the lane's task file must name the composition-root owner) · **Size:** M: a new `src/auditmanager/access/audit.py`, `repository.py`, `accounts.py`, `registrations.py`,
  `grant.py`, `product_purge.py`, and their tests.
- **Executor:** Sonnet lane.
- **Check:** `ADR-0023` rows 5 and 6; `pytest -q tests/integration/access tests/integration/recovery/test_product_purge.py` on an isolated database.

### PROD-07 — The operator project erase (`R-146c`, `R-146o`, `AD-06`, `AD-07`)
- **Result:** `infra/deploy/erase-project.sh` and `scripts/recovery/project_erase.py` as `ADR-0022` section 3 defines them: findings and expert decisions removed with everything else of the project, dry run by default, a plan SHA-256, journalled, idempotent, resumable; erased `blob` rows are deleted and a manifest is written; **a byte-identical upload after an erase succeeds** (test).
- **depends_on:** PROD-06 (same file `product_purge.py`), PROD-04 (the owner role and the wrapper's migrator URL) · **Hotspots:** `infra/**` (one new file), `scripts/recovery/**`, `DEPLOYMENT_RUNBOOK.md` · **Size:** L by the new-tool rule: a module of the order of `product_purge.py` (1024 lines, 27 guard blocks), a wrapper of the order of
  `purge-product-data.sh` (16 guard blocks), the classification declaration, and tests with a mutation proof per guard, resume and re-upload cases, modelled on the purge's six test files.
- **Executor:** Sonnet lane.
- **Check:** the verification list of `ADR-0022`; its two rest-state queries print `0`.

### PROD-08 — The offline copy of the key ring (`R-146n` item 7, `AD-08`)
- **Result:** a runbook section (in `DEPLOYMENT_RUNBOOK.md`) with the procedure of `ADR-0022` section 6, and the first copy made and verified.
- **depends_on:** — · **Hotspots:** `DEPLOYMENT_RUNBOOK.md`, shared with the infra lane of its wave, so it is dispatched inside `PROD-07`'s lane · **Size:** S · **Executor:** Sonnet lane for the text; owner for the copy and the second machine.
- **Check:** `sed -n 's/^AUDITMANAGER_SECRETS_KEYS=//p' infra/deploy/env/provider.env | sha256sum` equals the digest recorded in the release record and re-computed from the decrypted copy.

### PROD-09 — The release checklist, the manual scan and the pruning rule (`R-146h`, `R-146n` item 5, `AD-05`)
- **Result:** `scripts/release/manual_scan.sh` and the eight-line checklist of `ADR-0021` section 7 in `RELEASE_PROCESS.md`, with the manual pruning rule for `infra/deploy/dumps/` and the disk-free line.
- **depends_on:** — · **Hotspots:** none · **Size:** S: a script, `RELEASE_PROCESS.md`, a test that the script refuses to pass with a scanner missing.
- **Executor:** Sonnet lane; the owner runs it from a machine with network access.
- **Check:** `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit and `scripts/release/manual_scan.sh --check-tools` exits non-zero when a scanner is missing (the second command fails for the right reason; the first is a documentation check).

### PROD-10 — Preparation for removing АР v1 and v2 (`AD-12`)
- **Result:** the live journey, `tests/e2e/pc01/` and the manual protocol run on a section that stays; what v3 needs from `ar_v2` has moved out of it and `registered.py` is split (`ADR-0024` section 2): three modules (`content`, `recognised_context`, `grounding`), the six `.md` data files `content.py` reads, and the two identity constants; nothing else changes. The first task of the lane is the import closure, because the
  string search under-counts (`src/auditmanager/findings/recorded_saved_plan.py`, `src/auditmanager/findings/merge_publication_plan.py` and `src/auditmanager/analysis/stages/finding_merge.py` do not carry the name).
- **depends_on:** — (every non-АР section already has a synthetic recording over the same text layer: `SECTION-RECORDINGS-01.md`) · **Hotspots:** none of the four (it edits `src/auditmanager/analysis/profiles/ar_v3/*`, `src/auditmanager/analysis/recognised/`, `fixtures/`, `tests/e2e/`) ·
  **Size:** L: five `ar_v3` importers, one `recognised` importer, the three moved modules and six data files, the split `registered.py`, the journey (`journey.mjs`, `manifest.json`, fixtures), the manual protocol and about 15 test files that import the moved modules.
- **Executor:** Sonnet lane.
- **Check:** `grep -rn "profiles.ar_v2" src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised` prints nothing; the live journey in a lane stand (`npm --prefix web run e2e:pc01 -- --phase all`) is a task for `PROD-18`'s window.

### PROD-11 — Removal of АР v1 and v2 and the contract reseal (`R-146l`, `AD-12`)
- **Result:** the scope of `ADR-0024` section 2: `startRun` on an АР version answers `section_profile_unavailable`; `AnalysisProfileStatus` has no `builtin`; `AR_TEXT_PROFILE` and the v2 modules are gone;
  92/104/300 unchanged unless the reseal owner decides otherwise; the web start control sends an АР version to the v3 control.
- **depends_on:** PROD-10, **PROD-14.0** (both edit `web/tests/unit/analysis-settings/analysis-settings.test.ts` and the profile-status tests) · **Hotspots:** the contract (sole owner), the composition-root neighbour `src/auditmanager/runs/executor.py` and, if `src/auditmanager/bootstrap/**` changes, the composition root (sole owner) ·
  **Size:** L: 30 source files name v2, six name `AR_TEXT_PROFILE`, 65 test files, seven web files, the contract, the generated client and the frontend lock.
- **Executor:** Sonnet lane (the reseal needs the contract owner's slot); the integrator names the new contract version.
- **Check:** `grep -rn "AR_TEXT_PROFILE" src` and `grep -rn "profiles.ar_v2" src` print nothing; `python3 -I -c "import json;print('builtin' in json.dumps(json.load(open('contracts/api/v1/openapi.json'))))"` prints `False`; `pytest -q tests/contract/api_v1`, the focused integration directories of `runs`, `findings`, `analysis`, `sections`; `npm --prefix web run api:verify`.

### PROD-12 — Activation of АР v3 (`D-204`, `R-146g`): the critical path of the production release for АР, and of `B3`, `B5`, `B10` for the beta (`R-146q`)
- **Result:** a reviewed pack is installed (`v3_pack_cli verify` exits 0) and `startArV3BetaGroup` stops refusing. The sequence is `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`, steps 1 to 9, none of which code can supply.
- **Steps and owners:** (1) the stand imports the repaired norms bundle and designates snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` — owner window; (2) include/revise/exclude for each C01–C22 branch —
  qualified expert; (3) the missing official D1–D5 amendment pages, the C15 ГОСТ correction page and the D6 law text, hashed — owner; (4) BGE-M3 query vectors with reproducible provenance
  (the weights are not on the development host) — owner; (5) `map_pack build`/`validate`, (6) six `promote_cli` plan/promote runs against the reviewer's independent digests, (7) `v3_pack_cli seal` and `verify` — Sonnet lane under the reviewer;
  (8) install the manifest and restart `api` and `worker` — owner; (9) `AR-V3-BETA-ACCEPT-01`: recorded positive and negative cases, a controlled live and cost check, user review of source links.
- **depends_on:** PROD-01 for step 8 on the public stand; PROD-13 for step 9's live check · **Hotspots:** none · **Size:** L in elapsed work, little code.
- **Executor:** owner and expert; Sonnet lane for 5–7.
- **Check:** `python -m auditmanager.runs.v3_pack_cli verify --manifest infra/deploy/ar-v3-pack/<file>` exits 0 (`D-204`).

### PROD-13 — The OpenRouter production connection and the model pin (`R-146e`, `R-146u`, `AD-13`, `AD-14`)
- **Result:** the connection is configured (`PROXY_LLM_*` in `provider.env`, source `database`, mode `live`), probed `ok` and selected; a probe records the requested slug and the reported `model` for each pinned model in its own report file;
  `P02_LOCK.json` is written only by this task and only if the strings and rates match; `allow_client_documents` is set true on the connection by an administrator as a recorded revision. **No code enforces the flag and no item builds a refusal** (`R-146u`).
- **depends_on:** — (`AD-13` is confirmed by `R-146w`) · **Hotspots:** `docs/program/P02_LOCK.json` (sole writer, as `W56A-MODEL-PIN-01` was); it edits **no** runbook (its report is its own file; the runbook cross-reference is added by the infra-chain lane) · **Size:** M: a probe tool and report, the lock.
- **Executor:** owner (credential, approval; paid calls above roughly $5 per wave stop for the owner, `R-29`), Sonnet lane for the probe tool. `W56A-MODEL-PIN-01` stays stopped with its evidence.
- **Check:** `infra/deploy/readiness.sh | grep -E 'readiness OK +(provider-mode|executor-source)'` prints both lines; the probe report carries one `reported_model:` line per pinned model (a documentation check: it proves the probe ran, not that the strings match).

### PROD-14 — The other 14 sections to full versions (`R-146l`, `R-146v`): the primary development task until the beta
Definition (`AD-15`, confirmed by `R-146v`, **not the recommended option**): a section is full when an expert has reviewed its profile and it has left `draft`. **No non-synthetic field case is required and the recorded cases stay synthetic.** The accepted risk is `A-5`.

- **PROD-14.0 (Sonnet lane, first):** make the status and version pins data-driven. Four shared files assert them: `tests/unit/analysis/test_text_profile_registry.py` (`draft` for named sections), `tests/unit/analysis/text_profiles/test_text_profile_packages.py` (**lines 173-174 and 197 assert
  `profile_version == "1.0.0"` and `status == "draft"` for every package, PB included**), `tests/integration/composition/test_analysis_profiles_over_http.py`, and `web/tests/unit/analysis-settings/analysis-settings.test.ts`. One lane makes them read an expectations file with one line per section (code, status, version), so a section lane changes one line of one file and its own
  directory. `PROD-11` edits the web test later (the removal of `builtin`), so `PROD-14.0` merges first. **Size:** S: four test files plus the expectations file, no hotspot.
- **Per section (14.AI … 14.PB), in the registry's order `AI, PS, POS, TX, KJ, KM, OV, VK, PT, EOM, SS, ITP, GP, PB`:**
  (a) *expert:* review the profile (the section's record in `W59-SECTION-PROFILES-01.md` and the cross-section questions) and decide edits to `system_prompt.md` (for PB also answer `open_questions.md`);
  (b) *Sonnet lane:* apply them, bump `profile_version`, rebuild the section's synthetic recording with the builder (editing a prompt orphans its recording: `SECTION-RECORDINGS-01.md`), change the section's `status` from `draft` in `profile.json`;
  (c) *Sonnet lane:* update the section's line of the expectations file (the guard test) and run `pytest -q tests/integration/sections/test_section_recordings.py tests/unit/analysis/test_text_profile_registry.py tests/unit/analysis/text_profiles/test_text_profile_packages.py`.
  Each lane owns `src/auditmanager/analysis/text/profiles/<code>/**`, `fixtures/recorded/sections/<code>/**` and its one line, which is disjoint across sections once 14.0 has merged.
- **Who reviews:** the discipline expert for the section; the tree names no one (`OD-18`, three to five named experts with committed slots, is open). Proposed grouping so that one expert pass covers several sections:
  architecture and general (AI, PS, POS, TX, GP), structures (KJ, KM), engineering systems (OV, VK, PT, EOM, SS, ITP), fire safety (PB, authored, with open questions).
- **depends_on:** PROD-14.0 for the section lanes; PROD-00 is not needed (`AD-15` is confirmed). The production connection (`PROD-13`) is **not** needed any more: the field-case steps are dropped by `R-146v` · **Hotspots:** the section's own directories and its line, after PROD-14.0;
  no contract, migration, composition root or `infra/**` · **Size:** M per section (one package, one fixture directory, one test run) and L for the epic: 14 sections, one preparation lane, four proposed expert passes ·
  **Executor:** expert (a), Sonnet lane (b, c, 14.0).
- **Check:** `python3 -I -c "import json,glob;print(sorted(json.load(open(f))['status'] for f in glob.glob('src/auditmanager/analysis/text/profiles/*/profile.json')))"` prints fourteen `reviewed` (today it prints fourteen `draft`); the expectations-file test fails when a package and its line disagree.

### PROD-15 — The exposure re-review (`D-217`, `R-29` clause 2)
- **Result:** `EXPOSURE-REVIEW-01.md` is followed by a review of the public origin that names `getExecutorTaskImage` and `getArV3BetaPackStatus`, the runner channel and the TLS terminator; any finding that changes who can reach the
  system stops for the owner.
- **depends_on:** PROD-01, PROD-02, PROD-04, PROD-06, PROD-11 · **Hotspots:** none · **Size:** M (a read-only probe and a report) · **Executor:** Sonnet lane from a development host; owner decides.
- **Check (documentation check only):** `grep -c "getExecutorTaskImage\|getArV3BetaPackStatus" docs/program/EXPOSURE-REVIEW-01.md` is at least 2 in the new review document.

### PROD-16 — Documentation reconciliation
- **Result:** the stale `ADR-0002` closing paragraph of the `R-143` addendum ("Nothing above exists in the tree yet ... Until a slice merges, W54 behaviour stands") is superseded by a dated note; `CURRENT_STATE.md` and `RELEASES.md`
  carry what `D-203` lists; the debt rows proposed in the report are entered. `DEPLOYMENT_RUNBOOK.md` is edited by the infra-chain lane of each wave (it must describe the new TLS, receipt, role, erase and key-ring procedures); this item only checks that it does.
- **depends_on:** the items it records · **Hotspots:** `CURRENT_STATE.md`, `DEBT_REGISTER.md` (integrator only) · **Size:** M · **Executor:** integrator, or a Sonnet docs lane under the integrator.
- **Check:** `pytest -q tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`.

### PROD-17 — The release rehearsal and the release
- **Result:** on a clean clone, a deploy on the VPS ends with `verify-deployed.sh` exit `0` (including the default-credential and certificate checks); the `R-93` order with a real `dump-db`, a `restore-db` drill on a copy at the head being released with the time it took (an owner act, recorded with `head:` and `result:` lines); an erase rehearsal on a restored
  copy; a rehearsal of the purge of the beta's data on a restored copy; the account review; then, on the owner's separate instruction naming the exact SHA (`AGENTS.md` section 6), the push, the workflow, the public probes, the purge (`R-146m`), the tag.
- **depends_on:** PROD-01 to PROD-16 and PROD-19 to PROD-22 as applicable, PROD-18 · **Hotspots:** `origin/main` (integrator, only on the owner's instruction) · **Size:** L · **Executor:** owner and integrator.
- **Check:** `ADR-0021` rows 1 to 6 and 15 on the live name; `ADR-0022` rest-state queries; `git ls-remote origin refs/heads/main` equals the instructed SHA.

### PROD-18 — The complete gate on the release candidate (`D-205`, `R-70`, `AGENTS.md` section 6)
- **Result:** a complete `make gate` with the literal `GATE OK` (or its `R-125` completion) on the exact candidate, in an environment with the disk the preflight needs.
- **depends_on:** the code items · **Hotspots:** none · **Size:** M · **Executor:** owner (the environment: free disk or a separate host, `D-205`), integrator (the run).
- **Check:** `make gate-preflight` passes; the gate log ends with `GATE OK`.

### PROD-19 — The object store: keep the source-built MinIO or qualify another (`D-119`, `D-123`)
- **Result:** the owner decides, and the decision is recorded: the live MinIO volume is inventoried (`D-123`), and upstream's archived repository (`D-119`) is either accepted for 1.0 with the pinned source build or replaced by another S3 implementation qualified under `ADR-0020`. **`A-3` means no scan covers this image**; the manual scan helper reports it as unscanned.
- **depends_on:** — · **Hotspots:** none for the decision; `infra/minio/**` and `compose.server.yml` if the answer is a replacement (then an `infra/**` lane of its own, not scheduled here) · **Size:** S for the decision and the inventory; L if replaced · **Executor:** owner (decision, inventory on the VPS), Sonnet lane if replaced.
- **Check (documentation check only):** `grep -n "D-119\|D-123" docs/program/RELEASE_PROCESS.md` finds the decision in the release record once it is made; the inventory is `copy-serve.sh capacity` run on the stand.

### PROD-20 — The capacity envelope and the 900-second watchdog (`D-171`, `D-175`, `AD-18`)
- **Result:** the owner has the measurements (pages per minute by document kind, the duration of each stage, on the VPS) (`R-146y`). Until the owner then chooses between raising the watchdog and a page limit, the watchdog stays 900 s and an input above the budget gets the typed refusal `analysis_input_budget_exceeded`; **that choice is an open decision after the measurement**, and its implementation is a follow-up lane.
- **depends_on:** PROD-05a (the VPS measurement); the implementation also waits for the owner's choice (PROD-00) · **Hotspots:** `src/auditmanager/jobs/lease.py` or the ingest limits; the contract only if the limit becomes a new field (it need not) · **Size:** M · **Executor:** owner (measurement, decision), Sonnet lane (change and test).
- **Check:** the measurement is recorded; after the owner's choice, a test that an attempt of the decided length is not failed by the watchdog, or that an input above the page limit is refused with `analysis_input_budget_exceeded` before any Job exists; today `python3 -I -c "import re;print(re.search(r'ATTEMPT_WATCHDOG_SECONDS = (\d+)',open('src/auditmanager/jobs/lease.py').read()).group(1))"` prints `900`.

### PROD-21 — Interim: renew the live stand's certificate before 2026-12-30 (`D-191`; owner action)
- **Result:** until `PROD-01` replaces the host terminator, the owner renews the certificate of the host nginx by its existing means so that it is valid for at least fourteen days beyond 2026-12-16. The tree cannot show how that nginx obtains its certificate.
- **depends_on:** — · **Hotspots:** none (a host, not the repository) · **Size:** S · **Executor:** owner.
- **Check:** `echo | openssl s_client -connect <name>:443 -servername <name> 2>/dev/null | openssl x509 -noout -checkend 1209600` exits 0 on the live name.

### PROD-22 — The frozen domain-contract note for the erase exception (`R-146o`)
- **Result:** the contract owner edits `contracts/domain/v1/state-machines.json` (line 167, the `erased` description) so that it states the exception granted for the operator project erase and still describes the Blob `erased` transition truthfully; this pack names the exception and does not edit the frozen file.
- **depends_on:** PROD-07 (the exception exists) · **Hotspots:** the contract (same slot as `PROD-11`, sequenced after it in the wave) · **Size:** M: one frozen contract file (a hotspot file) with its seal and the checks that pin it · **Executor:** Sonnet lane in the contract owner's slot.
- **Check:** `python3 -I -c "import json;print('never deletes decision' in json.dumps(json.load(open('contracts/domain/v1/state-machines.json'))))"` prints `True` today; after the edit the same sentence must carry the exception or the command must print `False`, and `pytest -q tests/contract` stays green.

## 3. The critical paths

- **To the beta (`1.0.0-beta.N`, `R-146r`):** `R-146q` keeps `B3`, `B5` and `B10`, so the beta needs the АР v3 pack and a live connection as well as the sections: `PROD-00` → `PROD-14.0` → the 14 section chains (expert review, edit and re-record, status switch, guard test) **in parallel with** `PROD-12` and `PROD-13`, then `PROD-18` and the repeat of B1–B12.
  "Sections first" (`R-146l`) orders the development lanes; the АР gates wait for `D-204` data, which no lane can shorten. Expert time is the binding resource for the sections; the code is small.
- **To the production release (`1.0.0`):** `PROD-12` (`R-146g`) in parallel with `PROD-14`, the code chain `PROD-01 → 02 → 03 → 04 → 05`, `PROD-06 → 07`, `PROD-10 → 11 → 22`, and the decisions `PROD-19` and `PROD-20`, then `PROD-15 → 16 → 17`, with `PROD-18` and the owner's instruction naming the SHA.
  `PROD-01` has a deadline (2026-12-16) and `PROD-21` covers the live stand if it slips.
- **Chains that are serial for hotspot reasons only:** the `infra/**` chain (PROD-01 to 05, then PROD-07) and the `product_purge.py` chain (PROD-06 then 07).

## 4. Waves

A wave is a set of lanes whose hotspots do not overlap; the integrator dispatches within the host's lane limit. `DEPLOYMENT_RUNBOOK.md` belongs to the infra lane of the wave.

| Wave | Lanes | Hotspot owners |
| --- | --- | --- |
| PW0 | PROD-00; owner and expert work that uses no lane: naming the server name (`R-146p`), PROD-12 steps 1 to 4, PROD-14 expert reviews, PROD-05a, PROD-18's environment, PROD-19's decision, PROD-20's measurement, PROD-21 | — |
| PW1 | PROD-14.0 then the PROD-14 section lanes; PROD-01 | `infra/**` and the runbook: PROD-01 |
| PW2 | PROD-02 and PROD-03 (one infra lane); PROD-06; PROD-09; PROD-13 (owner-gated, no infra, no runbook); the PROD-14 section lanes continue | `infra/**` and the runbook: PROD-02/03; `product_purge.py`: PROD-06; `P02_LOCK.json`: PROD-13 |
| PW3 | PROD-04; PROD-10; the PROD-14 section lanes continue | `infra/**` and the runbook: PROD-04 |
| PW4 | PROD-11 then PROD-22 (one contract slot); PROD-05b; the PROD-14 section lanes continue | contract and composition root: PROD-11/22; `infra/**` and the runbook: PROD-05b |
| PW5 | PROD-07 with PROD-08 inside it; PROD-20; PROD-15; PROD-16 | `infra/**`, the runbook and `product_purge.py`: PROD-07; `src/auditmanager/jobs/`: PROD-20; `CURRENT_STATE.md`: PROD-16 |
| PW6 | PROD-18; PROD-17 | `origin/main`: the integrator, on the owner's instruction |

Rules: no lane starts in a wave that names its hotspot for another lane; no wave closes with an item half-merged (`AGENTS.md` section 7: a lane is committed with its runs green, then a new session). Overlaps found and removed in this revision: `PROD-13` no longer edits the runbook in `PW2`; `PROD-07`'s wrapper sits in a wave with no other `infra/**` lane; `PROD-20` and `PROD-07` touch disjoint directories.

## 5. The accepted-risk register

`A-1` to `A-3` and `A-5` are the owner's (`R-146b`, `R-146f`, `R-146h`, `R-146v`); `A-4` is the architect's consequence of `R-146a` and `R-146b`. The reopen triggers of `A-2`, `A-3` and `A-4` are confirmed by `R-146w` (`AD-16`); the trigger of `A-5` is given with `R-146v`'s application.

| Id | Risk, stated plainly | Owner's words | Reopen trigger |
| --- | --- | --- | --- |
| A-1 | Client data can be lost back to the last manual copy; a disk loss on the one host loses the copies too (the one exception is the latest pre-migration copy fetched to the development host for the `R-93` restore test, which is not a scheduled backup). No recovery point or time is committed. Compensation: a fresh copy receipt before every migrating deploy. | `R-146b` | the first real client upload that the owner cannot afford to lose (`R-146b`) |
| A-2 | The tree holds no provider terms, data-processing agreement, consent or data-handling policy; document text goes to OpenRouter and onward to whichever provider it routes to, which may retain or train on it; no ban on substitution (caught after the fact by `R-133`). | `R-146f`, `R-146n` item 4 not accepted | confirmed (`R-146w`): a client asks for data-handling terms; a contract promises confidentiality; the owner accepts `R-146n` item 4 |
| A-3 | No machine checks a push and no scan runs unless a person runs it before a release; `D-122` stays open, and nothing scans the source-built MinIO image (`D-119`). | `R-146h` | confirmed (`R-146w`): a published advisory for a component in `uv.lock`, `web/package-lock.json` or a pinned image; any release to users outside the owner's organisation |
| A-4 | One host, no failover, no maintained copy of the database or the bucket off that host; a host loss ends the service and may end the data. | consequence of `R-146a`, `R-146b` | confirmed (`R-146w`): as `A-1`, and any promise of a recovery time or point to a client |
| A-5 | When the 14 sections become full, the quality of their output on real text is unmeasured: a section leaves `draft` when an expert has reviewed its profile, no non-synthetic field case is required, recorded cases stay synthetic. | `R-146v` (not the recommended option) | the first section whose real-text output an expert rejects, or the first client complaint |

Not accepted and therefore not a risk register entry: `R-146n` item 4 (no restriction of routing or substitution); it is the cause of `A-2`.

## 6. What the polls settled

| Ruling | Settles |
| --- | --- |
| `R-146o` | `AD-06`: the erase removes findings, quotes, comments and expert decisions |
| `R-146p` | `AD-01` as to the server name: a deploy variable the owner names before `PROD-01` |
| `R-146q`, `R-146r` | beta criteria `B3`, `B5`, `B10` remain; the beta is `1.0.0-beta.N`, production `1.0.0` |
| `R-146s` | `AD-11`: the deploy ends non-zero and the public listener stays shut |
| `R-146t` | `AD-03`: a fresh receipt before `migrate` |
| `R-146u` | `AD-14`: `allow_client_documents` true, a label only |
| `R-146v` | `AD-15`: a section is full when an expert has reviewed its profile; `A-5` |
| `R-146w` | `AD-02`, `AD-05`, `AD-07`, `AD-08`, `AD-09`, `AD-10`, `AD-12`, `AD-13`, `AD-16`, as written at commit `83600aed` |
| `R-146x` | `AD-17`: the full `R-93` attestation stays after 1.0 |
| `R-146y` | `AD-18`: measure first (`PROD-20`); the watchdog stays 900 s and the typed refusal applies until the owner chooses |
| `R-146z` | `AD-19`: only the published seeded pair fails the deploy |

## 7. Decisions still open

1. `AD-04`: memory and log limits from a VPS measurement, no number fixed now (not polled).
2. The ACME mechanism of `AD-01` (not polled): the ACME client container, the three listeners, the 14-day expiry check.
3. The `AD-18` choice after `PROD-20`'s measurement: raise the 900-second watchdog or a page limit.
4. `PROD-19`: the MinIO lifecycle (keep the source-built image or qualify another S3 implementation, `D-119`, `D-123`).
5. The legal-hold authority and the classification labels (`ADR-0014`).
6. The licensing review before any external corpus-backed release (`NORM-Q04`).
7. Whether beta users are internal or external (`D-4.1`).
8. The measured size of the VPS (`PROD-05`).
9. Off-host custody of anything (dumps, key ring, bucket): not asked.
10. A second person to run the stand.
11. Who the section experts are (`OD-18`).

## 8. What this plan does not establish

- The live state of the stand: whether the host terminator sends HSTS or a `Secure` cookie today, whether the live `admin` password was changed (`D-75`, `D-217`), which SHA is deployed, how much data it holds, the VPS size.
- That any `AD-` decision works: none is implemented, and each check marked "no" in the ADR tables does not exist yet.
- That OpenRouter reports the requested slug for each pinned model, that its terms permit what `R-146f` allows, or that a per-key spending limit exists (assumptions).
- That experts exist, are named or have time, or that the data of `D-204` can be produced.
- A calendar: no estimate is given, and the tree holds no calibrated one for these items; the only date is the `PROD-01` deadline derived from the certificate's expiry.
- That a complete gate can run (`D-205`) or would pass; no gate was run for this pack.
- Legal sufficiency of the production release for client data (`A-2`), or that the quality of the 14 sections on real text is anything better than unmeasured (`A-5`).
- That the item sizes are right: they are counted from greps on the tree above, not from a lane's experience.
