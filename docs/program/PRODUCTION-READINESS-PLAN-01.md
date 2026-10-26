# PRODUCTION-READINESS-PLAN-01 — the road from `origin/dev` to the production release

Written 2026-10-26 by lane `production-adr-pack-01` ([task](tasks/PRODUCTION-ADR-PACK-01.md), [report](PRODUCTION-ADR-PACK-01.md)).
It plans; it builds nothing, claims no approval and changes no state of the stand. The owner's decisions are `R-146a`…`R-146n`
(`OWNER_RULINGS_2026-09-17.md` section 3.46) and are quoted only through those rows. The architecture is in
[`ADR-0021`](../architecture/adr/ADR-0021-production-topology-and-operations.md),
[`ADR-0022`](../architecture/adr/ADR-0022-production-data-governance.md),
[`ADR-0023`](../architecture/adr/ADR-0023-production-identity-and-access.md) and
[`ADR-0024`](../architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md); every `AD-nn` named below is the architect's
implementation decision within `R-146`, proposed and not yet confirmed (`PROD-00`).

**Baseline.** `integration/ar-close-1026` at `4d7b7c38`: `VERSION` `0.8.1`, shared contract `1.5.0`, 92 paths / 104 operations / 300 schemas,
migration head `0032_ar_v3_run_group`, 27 error codes. The local tracking ref `origin/dev` differs from it by two documents and `origin/main`
carries an older tree (neither ref was fetched for this plan). No complete `make gate` can run on the development host (`D-205`).

## 1. How to read the items

- **Size** counts the files an item touches and the hotspots it owns: **S** up to 5 files and no hotspot; **M** 6 to 15 files, or one file of
  a hotspot; **L** more than 15 files, or the contract, the migration head, or the core of `infra/deploy`. A size is a reason, not a forecast; this plan
  gives no calendar dates (see section 9).
- **Executor:** *Sonnet lane* (a code or document lane that returns the `AGENTS.md` section 5 hand-back), *owner* (only the owner can: a host, a
  credential, a payment, a decision), *expert* (a qualified person's review), *integrator* (merges, gates, rulings; `AGENTS.md` section 7.1).
- **Hotspots** are those of `AGENTS.md` section 3: the contract (`contracts/**`, `web/openapi/`, `web/FRONTEND_LOCK.json`, the generated client), the
  migration head (`db/migrations/**`), the composition root (`src/auditmanager/bootstrap/**`), `infra/**`, and, because several items edit it, the
  recovery tool `scripts/recovery/product_purge.py`. One owner per hotspot per wave.
- **Gate regime.** `R-135` defers the complete gate to one separate integration task after the planned code; each lane runs only the bounded tests
  it names. `R-70` and `AGENTS.md` section 8 still require a complete gate before `origin/main` (`PROD-18`). Lane count is bounded by the host condition
  of `CODE-FIRST-TO-BETA.md` section 2.2 (`R-143d`: at most one or two lanes while it holds).

## 2. Work items

### PROD-00 — The owner confirms or changes the architect's decisions and the open questions
- **Result:** a ruling record (its number assigned by the integrator) that, for every `AD-` decision of the pack and every open question of section 7, says
  confirmed, changed, or refused. No item below is dispatched on an unconfirmed `AD-` that it depends on.
- **depends_on:** — · **Hotspots:** `OWNER_RULINGS_*.md` (integrator) · **Size:** S (one document) · **Executor:** owner (by direct poll), integrator records.
- **Check:** `grep -n "PRODUCTION-ADR-PACK-01" docs/program/OWNER_RULINGS_2026-09-17.md` finds the ruling that answers the poll and names each `AD-` id.

### PROD-01 — The TLS terminator and certificate renewal in `infra/` (`R-146a`, `AD-01`)
- **Result:** the stack answers on the production name over a trusted chain with HSTS and a `Secure` session cookie; renewal runs inside the stack; port 80 serves
  only the challenge and a redirect; the plain listener stays on loopback; `verify-deployed.sh` fails on a certificate with fewer than 14 days left; `readiness.sh`
  `tls` and `plain-http` describe the new layout. `D-191` closes.
- **depends_on:** PROD-00 (the DNS name, `AD-01`) · **Hotspots:** `infra/**` owner of its wave · **Size:** L: `compose.server.yml`, five files under `infra/deploy/proxy/`,
  a new `infra/acme/`, `deploy.sh`, `verify-deployed.sh`, `readiness.sh`, `env/alpha.env.example`, the runbook, and the TLS and readiness composition tests.
- **Executor:** Sonnet lane, then owner (DNS record, inbound 80 and 443, the first issuance against the staging endpoint and then the real one).
- **Check:** `ADR-0021` rows 1 to 5; `pytest -q tests/integration/composition/test_proxy_tls_path.py tests/contract/test_proxy_security_headers.py tests/integration/composition/test_deploy_script_refusals.py tests/integration/composition/test_readiness_command.py`.

### PROD-02 — A deployment fails while `admin`/`password` is valid (`R-146i`, `AD-11`)
- **Result:** `verify-deployed.sh` and `deploy.sh` run `python -m auditmanager.access.check` in the `api` image and end non-zero naming the logins, without stopping a
  service; `readiness.sh` keeps `R-46` for its other checks. A fresh-host order (loopback until the password is changed) is in the runbook.
- **depends_on:** PROD-01 (same files: `verify-deployed.sh`, `deploy.sh`, `readiness.sh`) · **Hotspots:** `infra/**` · **Size:** M: three scripts, two composition tests, one new test, the runbook.
- **Executor:** Sonnet lane.
- **Check:** `ADR-0023` row 1; the new test drives a database with the seeded account and shows the exit non-zero, and a mutation (the marked block deleted) turns it green.

### PROD-03 — The dump before every migration (`R-146n` item 3, `AD-03`)
- **Result:** `infra/deploy/dump-db.sh` takes and reads back a dump and writes a receipt carrying the database head and the dump's SHA-256; `deploy.sh` refuses a deploy whose
  checkout carries a newer revision unless a receipt for the current head under 24 hours old exists. First step of the lane: re-read `deploy.sh` to confirm that `R-93` still
  only guards an open unattested copy record (this plan found it so on `4d7b7c38`).
- **depends_on:** PROD-01 (same file `deploy.sh`) · **Hotspots:** `infra/**` · **Size:** M: a new script, `deploy.sh`, two tests, the runbook.
- **Executor:** Sonnet lane; the owner runs the first real dump on the VPS.
- **Check:** `ADR-0021` row 9.

### PROD-04 — Database roles: migrator and application (`R-146n` item 1, `AD-02`)
- **Result:** `api` and `worker` connect as a role that cannot change the schema or truncate; the migrator keeps ownership; the grants are covered for future tables; the
  integration directories of the contexts pass as the application role. The head moves to `0033`.
- **depends_on:** PROD-03 (infra files), and a ruling on `AD-02` · **Hotspots:** migration head (sole owner), `infra/**` · **Size:** L: the new revision, twelve files that pin the head
  (`grep -rl "0032_ar_v3_run_group" scripts src tests infra web contracts | wc -l` prints 12, `D-213`), `compose.server.yml`, `deploy.sh`, `alpha.env.example`, a grant guard test and the
  application-role run of the integration suites.
- **Executor:** Sonnet lane; the owner supplies the second password on the host.
- **Check:** `ADR-0021` row 7; `pytest -q tests/integration/db/test_migration_lifecycle.py tests/integration/db/test_downgrade_chain_round_trip.py` plus the new grant test, on an isolated database.

### PROD-05 — Memory and log limits (`R-146n` item 2, `D-166`, `AD-04`)
- **Result:** every long-running service has a memory limit and rotated logs, with values taken from a measurement.
- **Step 05a (owner):** on the VPS, `infra/deploy/capacity-probe.sh --path root=/` and `docker stats --no-stream` during a 500-page analysis; the readings go
  to the lane. **Step 05b (Sonnet lane):** edits `compose.server.yml`, adds a test that no long-running service lacks the options.
- **depends_on:** PROD-04 (same files), 05a needs a deployed stack and the VPS size (open) · **Hotspots:** `infra/**` · **Size:** S (05b: one file, one test).
- **Check:** `ADR-0021` row 8.

### PROD-06 — Audit events for sign-in, role grant and password change (`R-146n` item 6, `AD-10`)
- **Result:** the six `access.*` event types of `ADR-0023` are appended in the transaction of the change, from the API, the registration approval and the host command; the purge tool keeps them.
- **depends_on:** — · **Hotspots:** `scripts/recovery/product_purge.py` (one prefix, owner of its wave); no contract, migration or composition-root change is expected (the writer is context-local; if
  injection is needed the lane's task file must name the composition-root owner) · **Size:** M: a new `src/auditmanager/access/audit.py`, `repository.py`, `accounts.py`, `registrations.py`,
  `grant.py`, `product_purge.py`, and their tests.
- **Executor:** Sonnet lane.
- **Check:** `ADR-0023` rows 5 and 6; `pytest -q tests/integration/access tests/integration/recovery/test_product_purge.py` on an isolated database.

### PROD-07 — The operator project erase (`R-146c`, `AD-06`, `AD-07`)
- **Result:** `infra/deploy/erase-project.sh` and `scripts/recovery/project_erase.py` as `ADR-0022` section 3 defines them: dry run by default, a plan SHA-256, journalled, idempotent, resumable.
- **depends_on:** PROD-06 (same file `product_purge.py`), PROD-04 (the owner role), PROD-00 (`AD-06`) · **Hotspots:** `infra/**` (one new file), `scripts/recovery/**` · **Size:** L: two new files, the
  classification declaration, and a test directory modelled on `tests/integration/recovery/test_product_purge.py` with a mutation proof per guard.
- **Executor:** Sonnet lane.
- **Check:** the verification list of `ADR-0022`; the two rest-state queries of that ADR print `0`.

### PROD-08 — The offline copy of the key ring (`R-146n` item 7, `AD-08`)
- **Result:** a runbook section (in `DEPLOYMENT_RUNBOOK.md`) with the procedure of `ADR-0022` section 6, and the first copy made and verified.
- **depends_on:** — · **Hotspots:** `DEPLOYMENT_RUNBOOK.md`, shared with the infra lane of its wave, so it is dispatched inside `PROD-07`'s lane · **Size:** S · **Executor:** Sonnet lane for the text; owner for the copy and the second machine.
- **Check:** `sed -n 's/^AUDITMANAGER_SECRETS_KEYS=//p' infra/deploy/env/provider.env | sha256sum` equals the digest recorded in the release record and re-computed from the decrypted copy.

### PROD-09 — The release checklist and the manual scan (`R-146h`, `R-146n` item 5, `AD-05`)
- **Result:** `scripts/release/manual_scan.sh` and the eight-line checklist of `ADR-0021` section 7 in `RELEASE_PROCESS.md`.
- **depends_on:** — · **Hotspots:** none · **Size:** S: a script, `RELEASE_PROCESS.md`, a test that the script refuses to pass with a scanner missing.
- **Executor:** Sonnet lane; the owner runs it from a machine with network access.
- **Check:** `ADR-0021` row 10.

### PROD-10 — Preparation for removing АР v1 and v2 (`AD-12`)
- **Result:** the live journey, `tests/e2e/pc01/` and the manual protocol run on a section that stays; `recognised_context`, `content`, `grounding` and `registered` live outside `ar_v2/`; nothing else changes.
- **depends_on:** — (every non-АР section already has a synthetic recording over the same text layer: `SECTION-RECORDINGS-01.md`) · **Hotspots:** none of the four (it edits `ar_v3/*`, `analysis/recognised/`, `fixtures/`, `tests/e2e/`) ·
  **Size:** L: five `ar_v3` modules, one `recognised` module, four moved modules, the journey (`journey.mjs`, `manifest.json`, fixtures), the manual protocol and about 15 test files that import the moved modules.
- **Executor:** Sonnet lane.
- **Check:** `grep -rn "profiles.ar_v2" src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised` prints nothing; the live journey in a lane stand (`npm --prefix web run e2e:pc01 -- --phase all`) is a task for `PROD-18`'s window.

### PROD-11 — Removal of АР v1 and v2 and the contract reseal (`R-146l`, `AD-12`)
- **Result:** the scope of `ADR-0024` section 2: `startRun` on an АР version answers `section_profile_unavailable`; `AnalysisProfileStatus` has no `builtin`; `AR_TEXT_PROFILE` and the v2 modules are gone;
  92/104/300 unchanged unless the reseal owner decides otherwise; the web start control sends an АР version to the v3 control.
- **depends_on:** PROD-10 · **Hotspots:** the contract (sole owner), the composition-root neighbour `runs/executor.py` and, if `bootstrap/**` changes, the composition root (sole owner) ·
  **Size:** L: 30 source files name v2, six name `AR_TEXT_PROFILE`, 65 test files, seven web files, the contract, the generated client and the frontend lock.
- **Executor:** Sonnet lane (the reseal needs the contract owner's slot); the integrator names the new contract version.
- **Check:** `ADR-0024` rows 1 to 4; `pytest -q tests/contract/api_v1` and the focused integration directories of `runs`, `findings`, `analysis`, `sections`; `npm --prefix web run api:verify`.

### PROD-12 — Activation of АР v3 (`D-204`, `R-146g`): the critical path of the production release for АР
- **Result:** a reviewed pack is installed (`v3_pack_cli verify` exits 0) and `startArV3BetaGroup` stops refusing. The sequence is `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`, steps 1 to 9, none of which code can supply.
- **Steps and owners:** (1) the stand imports the repaired norms bundle and designates snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` — owner window; (2) include/revise/exclude for each C01–C22 branch —
  qualified expert; (3) the missing official D1–D5 amendment pages, the C15 ГОСТ correction page and the D6 law text, hashed — owner; (4) BGE-M3 query vectors with reproducible provenance
  (the weights are not on the development host) — owner; (5) `map_pack build`/`validate`, (6) six `promote_cli` plan/promote runs against the reviewer's independent digests, (7) `v3_pack_cli seal` and `verify` — Sonnet lane under the reviewer;
  (8) install the manifest and restart `api` and `worker` — owner; (9) `AR-V3-BETA-ACCEPT-01`: recorded positive and negative cases, a controlled live and cost check, user review of source links.
- **depends_on:** PROD-01 for step 8 on the public stand; PROD-13 for step 9's live check · **Hotspots:** none · **Size:** L in elapsed work, little code.
- **Executor:** owner and expert; Sonnet lane for 5–7.
- **Check:** `python -m auditmanager.runs.v3_pack_cli verify --manifest infra/deploy/ar-v3-pack/<file>` exits 0 (`D-204`).

### PROD-13 — The OpenRouter production connection and the model pin (`R-146e`, `AD-13`, `AD-14`)
- **Result:** the connection is configured (`PROXY_LLM_*` in `provider.env`, source `database`, mode `live`), probed `ok` and selected; a probe records the requested slug and the reported `model` for each pinned model;
  `P02_LOCK.json` is written only by this task and only if the strings and rates match; `allow_client_documents` is set true by an administrator as a recorded revision.
- **depends_on:** PROD-00 · **Hotspots:** `docs/program/P02_LOCK.json` (sole writer, as `W56A-MODEL-PIN-01` was) · **Size:** M: a probe tool and report, the lock, the runbook.
- **Executor:** owner (credential, approval; paid calls above roughly $5 per wave stop for the owner, `R-29`), Sonnet lane for the probe tool. `W56A-MODEL-PIN-01` stays stopped with its evidence.
- **Check:** `ADR-0024` rows 5 to 8; `infra/deploy/readiness.sh` reports `provider-mode` and `executor-source` OK.

### PROD-14 — The other 14 sections to full versions (`R-146l`): the primary development task until the beta
Definition (`AD-15`, proposed): per section, a named expert has reviewed the profile and its status is `reviewed` in the registry (`D-178`); at least one positive and one negative case ran on a
document that is neither synthetic nor a client document (`R-141c`) and is recorded and replayable (`D-183`); an expert accepted those outputs.

- **PROD-14.0 (Sonnet lane, first):** make the status pins data-driven. `tests/unit/analysis/test_text_profile_registry.py` and
  `tests/integration/composition/test_analysis_profiles_over_http.py` assert `draft` for named sections and are shared by every section lane; one lane makes them read the package, so section lanes touch only their own directory.
  `web/tests/unit/analysis-settings/analysis-settings.test.ts` also carries statuses and is later edited by `PROD-11` (removal of `builtin`), so `PROD-14.0` must merge first. **Size:** S (two or three test files).
- **PROD-14.1 (Sonnet lane):** establish how a field case becomes a replayable recording. `python -m auditmanager.analysis.text` is replay-only and refuses live, `model_call` stores hashes only, and the section
  recordings are built by `fixtures/recorded/sections/build_fixtures.py` with authored replies; this plan did not find a tool that turns a live durable run into a recording. If none exists, the lane designs the smallest one. **Size:** M.
- **Per section (14.AI … 14.PB), in the registry's order `AI, PS, POS, TX, KJ, KM, OV, VK, PT, EOM, SS, ITP, GP, PB`:**
  (a) *expert:* read the section's record in `W59-SECTION-PROFILES-01.md` and the cross-section questions, and decide edits to `system_prompt.md` (for PB also answer `open_questions.md`);
  (b) *Sonnet lane:* apply them, bump `profile_version`, rebuild the section's recording with the builder (editing a prompt orphans its recording: `SECTION-RECORDINGS-01.md`), run
  `pytest -q tests/integration/sections/test_section_recordings.py tests/unit/analysis/test_text_profile_registry.py`; (c) *owner:* designate the field documents; (d) *owner and Sonnet lane:* run them live through the production
  connection and record them (paid; `R-29`); (e) *expert:* accept or reject the outputs; (f) *Sonnet lane:* flip `status` to `reviewed`. Each lane owns `src/auditmanager/analysis/text/profiles/<code>/**` and
  `fixtures/recorded/sections/<code>/**` only, which is disjoint across sections once 14.0 has merged.
- **Who reviews:** the discipline expert for the section; the tree names no one (`OD-18`, three to five named experts with committed slots, is open). Proposed grouping so that one expert pass covers several sections:
  architecture and general (AI, PS, POS, TX, GP), structures (KJ, KM), engineering systems (OV, VK, PT, EOM, SS, ITP), fire safety (PB, authored, with open questions).
- **Check:** `ADR-0024` row 9 prints fourteen `reviewed`; `PROD-18` repeats B1–B12 on the candidate.

### PROD-15 — The exposure re-review (`D-217`, `R-29` clause 2)
- **Result:** `EXPOSURE-REVIEW-01.md` is followed by a review of the public origin that names `getExecutorTaskImage` and `getArV3BetaPackStatus`, the runner channel and the TLS terminator; any finding that changes who can reach the
  system stops for the owner.
- **depends_on:** PROD-01, PROD-02, PROD-04, PROD-06, PROD-11 · **Hotspots:** none · **Size:** M (a read-only probe and a report) · **Executor:** Sonnet lane from a development host; owner decides.
- **Check:** `grep -c "getExecutorTaskImage\|getArV3BetaPackStatus" docs/program/EXPOSURE-REVIEW-01.md` is at least 2 in the new review document.

### PROD-16 — Documentation reconciliation
- **Result:** the stale `ADR-0002` closing paragraph of the `R-143` addendum ("Nothing above exists in the tree yet ... Until a slice merges, W54 behaviour stands") is superseded by a dated note; `CURRENT_STATE.md` and `RELEASES.md`
  carry what `D-203` lists; the debt rows proposed in the report are entered. `DEPLOYMENT_RUNBOOK.md` is edited by the infra-chain lane of each wave (it must describe the new TLS, dump, role, erase and key-ring procedures); this item only checks that it does.
- **depends_on:** the items it records · **Hotspots:** `CURRENT_STATE.md`, `DEBT_REGISTER.md` (integrator only) · **Size:** M · **Executor:** integrator, or a Sonnet docs lane under the integrator.
- **Check:** `pytest -q tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`.

### PROD-17 — The release rehearsal and the release
- **Result:** on a clean clone, a deploy on the VPS ends with `verify-deployed.sh` exit `0` (including the default-credential and certificate checks); a restore drill at the head being released with the time it took; an erase rehearsal on a restored
  copy; a rehearsal of the purge of the beta's data on a restored copy; the account review; then, on the owner's separate instruction naming the exact SHA (`AGENTS.md` section 6), the push, the workflow, the public probes, the purge (`R-146m`), the tag.
- **depends_on:** PROD-01 to PROD-16 as applicable, PROD-18 · **Hotspots:** `origin/main` (integrator, only on the owner's instruction) · **Size:** L · **Executor:** owner and integrator.
- **Check:** `ADR-0021` rows 1 to 6 and 15 on the live name; `ADR-0022` rest-state queries; `git ls-remote origin refs/heads/main` equals the instructed SHA.

### PROD-18 — The complete gate on the release candidate (`D-205`, `R-70`, `AGENTS.md` section 6)
- **Result:** a complete `make gate` with the literal `GATE OK` (or its `R-125` completion) on the exact candidate, in an environment with the disk the preflight needs.
- **depends_on:** the code items · **Hotspots:** none · **Size:** M · **Executor:** owner (the environment: free disk or a separate host, `D-205`), integrator (the run).
- **Check:** `make gate-preflight` passes; the gate log ends with `GATE OK`.

## 3. The critical paths

- **To the beta, with the other sections first (`R-146l`):** `PROD-00` → `PROD-14.0` → `PROD-14.1` → for each of 14 sections review, edit, re-record, field case, acceptance, status flip → `PROD-18` and the beta criteria B1–B12. Expert time is the binding resource; the code is small.
- **To the production release:** `PROD-12` (data and review that no code can shorten, `R-146g`) in parallel with `PROD-14` and with the code chain `PROD-01 → 02 → 03 → 04 → 05`, `PROD-06 → 07`, `PROD-10 → 11`, then `PROD-15 → 16 → 17`, with `PROD-18` and the owner's instruction naming the SHA.
- **Two chains are serial for hotspot reasons only:** the `infra/**` chain (PROD-01 to 05) and the `product_purge.py` chain (PROD-06 then 07).

## 4. Waves

A wave is a set of lanes whose hotspots do not overlap; the integrator dispatches within the host's lane limit.

| Wave | Lanes | Hotspot owners |
| --- | --- | --- |
| PW0 | PROD-00; owner/expert work that uses no lane: PROD-12 steps 1 to 4, PROD-14 expert reviews, PROD-05a, PROD-18's environment | — |
| PW1 | PROD-14.0 then PROD-14.* section lanes; PROD-01 | `infra/**`: PROD-01 |
| PW2 | PROD-02 and PROD-03 (one infra lane); PROD-06; PROD-09; PROD-13 (owner-gated); PROD-14.* continue | `infra/**`: PROD-02/03; `product_purge.py`: PROD-06 |
| PW3 | PROD-04; PROD-10; PROD-14.* continue | migration head and `infra/**`: PROD-04 |
| PW4 | PROD-11; PROD-05b; PROD-14.* continue | contract and composition root: PROD-11; `infra/**`: PROD-05b |
| PW5 | PROD-07; PROD-08; PROD-15; PROD-16 | `infra/**` (one file) and `product_purge.py`: PROD-07; `CURRENT_STATE.md`: PROD-16 |
| PW6 | PROD-18; PROD-17 | `origin/main`: the integrator, on the owner's instruction |

Rules: no lane starts in a wave that names its hotspot for another lane; no wave closes with an item half-merged (`AGENTS.md` section 7: a lane is committed with its runs green, then a new session).

## 5. The accepted-risk register

`A-1` to `A-3` are the owner's (`R-146b`, `R-146f`, `R-146h`); `A-4` is the architect's consequence of `R-146a` and `R-146b`. The reopen triggers of `A-2`, `A-3` and `A-4` are proposed and unconfirmed.

| Id | Risk, stated plainly | Owner's words | Reopen trigger |
| --- | --- | --- | --- |
| A-1 | Client data can be lost back to the last manual copy; a disk loss on the one host loses the copies too. No recovery point or time is committed. Compensation: a manual dump before every migration. | `R-146b` | the first real client upload that the owner cannot afford to lose (`R-146b`) |
| A-2 | The tree holds no provider terms, data-processing agreement, consent or data-handling policy; document text goes to OpenRouter and onward to whichever provider it routes to, which may retain or train on it; no ban on substitution (caught after the fact by `R-133`). | `R-146f`, `R-146n` item 4 not accepted | proposed: a client asks for data-handling terms; a contract promises confidentiality; the owner accepts `R-146n` item 4 |
| A-3 | No machine checks a push and no scan runs unless a person runs it before a release; `D-122` stays open. | `R-146h` | proposed: a published advisory for a component in `uv.lock`, `web/package-lock.json` or a pinned image; any release to users outside the owner's organisation |
| A-4 | One host, no failover, no copy of anything held off that host (dumps, key ring, bucket); a host loss ends the service and may end the data. | consequence of `R-146a`, `R-146b` | proposed: as `A-1`, and any promise of a recovery time or point to a client |

Not accepted and therefore not a risk register entry: `R-146n` item 4 (no restriction of routing or substitution); it is the cause of `A-2`.

## 6. What stays open

- The legal-hold authority and the classification labels (`ADR-0014`).
- The licensing review before any external corpus-backed release (`NORM-Q04`).
- Whether beta users are internal or external (`D-4.1`).
- The measured size of the VPS (`PROD-05`, `AD-04`).
- Off-host custody of anything (dumps, key ring, bucket): not asked.
- A second person to run the stand.

## 7. Decisions still needed from the owner (poll candidates)

1. The DNS name the certificate is issued for, and whether the temporary `sslip.io` name is acceptable (`AD-01`).
2. Whether the dump before a migration is enforced by a refusal in `deploy.sh` or is a checklist line (`AD-03`).
3. Whether erasing a project also deletes its findings and expert decisions, and whether the `blob` row of an erased document keeps its SHA-256 (`AD-06`).
4. Whether a failed default-credential check should also take the proxy down (`AD-11`).
5. What "full version" of a section means beyond expert review, field cases and acceptance (`AD-15`), and who the section experts are (`OD-18`).
6. Whether `R-146f` also waives the beta criteria B3, B5 and B10 for the production release (the ruling says no precondition of provider terms or expert acceptance).
7. How «бета 0.1.1» maps to the roadmap's `1.0.0-beta.N` tags (`R-146l`).
8. Whether `allow_client_documents` should become a refusal (`AD-14`).
9. The reopen triggers proposed for `A-2` to `A-4` (`AD-16`).

## 8. What this plan does not establish

- The live state of the stand: whether the host terminator sends HSTS or a `Secure` cookie today, whether the live `admin` password was changed (`D-75`, `D-217`), which SHA is deployed, how much data it holds, the VPS size.
- That any `AD-` decision works: none is implemented, and each check marked "no" in the ADR tables does not exist yet.
- That OpenRouter reports the requested slug for each pinned model, that its terms permit what `R-146f` allows, or that a per-key spending limit exists (assumptions).
- That experts exist, are named or have time, or that the data of `D-204` can be produced.
- A calendar: no estimate is given, and the tree holds no calibrated one for these items.
- That a complete gate can run (`D-205`) or would pass; no gate was run for this pack.
- Legal sufficiency of the production release for client data (`A-2`).
- That the item sizes are right: they are counted from greps on `4d7b7c38`, not from a lane's experience.
