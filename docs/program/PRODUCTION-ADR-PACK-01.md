# PRODUCTION-ADR-PACK-01 — the architecture decisions of the production version

**Task:** [PRODUCTION-ADR-PACK-01](tasks/PRODUCTION-ADR-PACK-01.md). **Frozen base:** `integration/ar-close-1026` at `4d7b7c38dc8239df6831b2587b71c0d74e8b1ec0`; round 2 merged the same branch at `1a7f6f65` (`R-146o`…`R-146v`). **Publication target:** none from this lane
(the integrator may merge it into `origin/dev`); no tag, no `origin/main`, no stand.


## Result

The owner's decisions of `R-146` are now architecture that can be tested: [`ADR-0021`](../architecture/adr/ADR-0021-production-topology-and-operations.md) (one VPS, TLS and renewal in `infra/`, roles, limits, copies, the release
checklist), [`ADR-0022`](../architecture/adr/ADR-0022-production-data-governance.md) (what is kept, the operator project erase, the purge at 1.0, egress, the key ring),
[`ADR-0023`](../architecture/adr/ADR-0023-production-identity-and-access.md) (one organisation, the default credential closed by the deploy, audited access changes),
[`ADR-0024`](../architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md) (АР is v3 only, the exact scope of the v1/v2 removal, OpenRouter and `R-133`, the single worker, the quality bar, the priority).
[`PRODUCTION-READINESS-PLAN-01.md`](PRODUCTION-READINESS-PLAN-01.md) turns them into 23 items (`PROD-00`…`PROD-22`) with dependencies, hotspot owners, sizes, executors and checks, a wave list with non-overlapping hotspots,
the accepted-risk register `A-1`…`A-5`, the open decisions and what the plan does not establish. Nothing was built and nothing is claimed done: no pack installed, no gate run, no deploy, no stand touched.

## Changed files

| File | Change |
| --- | --- |
| `docs/architecture/adr/ADR-0021-production-topology-and-operations.md` | new |
| `docs/architecture/adr/ADR-0022-production-data-governance.md` | new |
| `docs/architecture/adr/ADR-0023-production-identity-and-access.md` | new |
| `docs/architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md` | new |
| `docs/architecture/adr/ADR-0014-authz-classification-retention.md` | status line updated; dated addendum "Partially accepted by R-146 (2026-10-26)"; the original text unchanged |
| `docs/architecture/adr/ADR-0012-expert-decision-ledger-and-kb-projection.md` | round 2: dated addendum "amended by R-146o for the operator project erase only"; the original text unchanged |
| `docs/architecture/ADR_INDEX.md` | four new rows, the `ADR-0014` row updated, one paragraph on the post-CP-00 production ADRs |
| `docs/program/PRODUCTION-READINESS-PLAN-01.md` | new |
| `docs/program/tasks/PRODUCTION-ADR-PACK-01.md` | new |
| `docs/program/PRODUCTION-ADR-PACK-01.md` | this report |

## The architect's implementation decisions: confirmed and still awaiting the owner

`R-146` is the only source of owner decisions in the pack. Everything labelled `AD-nn` in the ADRs is the architect's choice within it. After the second poll round (`R-146o`…`R-146v`):

**Confirmed (the ADR status lines say "confirmed by" and the ruling id)**

| Id | Ruling | What it settled |
| --- | --- | --- |
| `AD-01` | `R-146p` | the server name is a deploy variable the owner names before `PROD-01`; no provider or name is decided. The ACME-in-compose mechanism and the 14-day expiry check stay as written in `ADR-0021` section 2; `R-146p` reads as confirming the name rule only, and the mechanism is the design the lane follows (if the coordinator reads `R-146p` as narrower, re-poll the mechanism) |
| `AD-03` | `R-146t` | `deploy.sh` refuses `migrate` without a fresh receipt (file, SHA-256, time); the limit 24 hours is set in `ADR-0021` |
| `AD-06` | `R-146o` | the erase removes findings, quotes, comments and expert decisions and keeps the record of the erasure; a deliberate exception to `ADR-0012` |
| `AD-11` | `R-146s` | the deploy ends non-zero and the public listener stays shut until the password is changed |
| `AD-14` | `R-146u` | `allow_client_documents` set true on the OpenRouter connection at the release; the flag stays a label |
| `AD-15` | `R-146v` | a section is full when an expert has reviewed its profile; no field case; accepted risk `A-5` |

**Still unconfirmed, as questions for the owner (the poll package)**

| Id | Where | Question |
| --- | --- | --- |
| `AD-02` | `ADR-0021` section 3 | Keep the current owner role as the migrator and add one restricted application role, with the grants applied by an idempotent step after every `migrate` and every restore (no migration)? |
| `AD-04` | `ADR-0021` section 4 | Take memory and log limits from a VPS measurement, fixing no number now? What is the VPS size? |
| `AD-05` | `ADR-0021` section 7 | A manual-scan helper that prints an inventory, runs the scanners that are installed and never prints a pass when one is missing, plus the eight-line release checklist and a manual pruning rule? |
| `AD-07` | `ADR-0022` section 3 | The erase tool: dry run by default, a plan SHA-256, a closed list of reason codes, the `era_` identity, `erasure.requested` and `erasure.completed`, four phases with a resume, erased `blob` rows deleted and a manifest file whose digest is in the event, and does the identity-only run journal of the erased project stay? |
| `AD-08` | `ADR-0022` section 6 | The key ring: one encrypted off-VPS copy verified by the SHA-256 of the ring line on a second machine, redone after every rotation? |
| `AD-09` | `ADR-0022` section 4 | At 1.0, run the existing whole-product purge (it has no v1/v2 selector) after a rehearsal on a restored copy, then review and archive the test accounts? |
| `AD-10` | `ADR-0023` section 4 | Six `access.*` events, no IP address, a failed sign-in journalled only when it starts a cooling-off, and `access.role_revoked` added beside the owner's "role grant"? |
| `AD-12` | `ADR-0024` section 2 | Remove АР v1/v2 in the order extract what v3 needs (three modules, six data files, two constants, `registered.py` split), re-base the live journey, then remove and reseal; `startRun` on АР gives `section_profile_unavailable`; the `FindingCategory` list stays? |
| `AD-13` | `ADR-0024` section 3 | Pin the exact string OpenRouter reports, add no alias list to the run path, and replace `W56A-MODEL-PIN-01` by a paid probe task under `R-29`? |
| `AD-16` | `ADR-0021` section 10, `ADR-0022` section 5 | The reopen triggers proposed for `A-2` (a client asks for terms), `A-3` (an advisory, or any release outside the owner's organisation) and `A-4` (as `A-1`, and any promise of a recovery time)? |
| `AD-17` (new) | `ADR-0021` section 5 | Keep the `R-93` attestation (fetch to the development host and restore test) for every release after 1.0, or relax the gate to the receipt only? |
| `AD-18` (new) | `ADR-0024` section 5 | Before the first real upload, raise the 900-second attempt watchdog (overall or per stage) or refuse above a page limit below the 500-page ceiling with `analysis_input_budget_exceeded`? |
| `AD-19` (new) | `ADR-0023` section 3 | Does the default-credential gate count every must-change account (the existing check also lists accounts whose password an administrator reset), or only the published seeded pair? |

Plus `PROD-19`: keep the source-built MinIO or qualify another S3 implementation (`D-119`, `D-123`). Still open after `R-146` and not asked: the legal-hold authority and classification labels
(`ADR-0014`), corpus licensing (`NORM-Q04`), internal or external beta users (`D-4.1`), off-host custody, a second operator, who the section experts are (`OD-18`), the VPS size and the server name.

## Facts that changed the design (each re-read in the tree on 2026-10-26)

- **`R-146i` narrows `R-46`.** `readiness.sh` is, by ruling `R-46`, a report that blocks nothing, and neither `deploy.sh` nor `verify-deployed.sh` runs `auditmanager.access.check` (task premise P-05). `ADR-0023` makes the default-credential check the one check that fails a deploy, without stopping services (`D-72`, `R-52`).
- **`deploy.sh` takes no dump.** `R-93` guards only an open, unattested copy record (P-04). The copy key's record already is a receipt (file, SHA-256, `quiesced_at`, attestation), so `AD-03` uses it instead of a new script; `R-93` continues to bind (round 2).
- **The application connects as the database bootstrap user** (`POSTGRES_USER`), which the official image makes a superuser (assumption; the query to confirm is in `ADR-0021` row 7). `product_purge.py` needs the table owner, so the roles are keep-the-owner-as-migrator, not a re-ownership.
- **The erase has a frozen-contract problem.** The domain contract says erasing bytes "never deletes decision, finding or audit history", while `finding_observation`, `finding_evidence` and `expert_decision_event` hold verbatim client text and are immutable or append-only by trigger. `R-146o` grants the exception; `ADR-0022` names it, `ADR-0012` carries an addendum and the frozen file is left to `PROD-22`.
- **The only automatic retention runs inside a runner's claim call** (P-11), so it never runs without a polling runner.
- **`allow_client_documents` is stored, shown and never read** (P-07): the imported OpenRouter connection says «не отправляются» while analyses through it send document text.
- **v3 stands on v2** (P-06): six modules outside `ar_v2` import it; `AR_TEXT_PROFILE` is named in six source files; 65 test files name v2 or `AR_TEXT_PROFILE`. The live journey uploads an АР bundle (P-10), so the removal needs its prerequisite item.
- **The model comparison is exact and has no alias path** (P-08, P-12); the OpenRouter name must therefore be the observed reply string.
- **Grants cannot live in a migration.** Every dump tool uses `--no-privileges` and `copy-serve.sh restore-db` drops and recreates `public`, so privileges from a revision would be lost by a restore (round 2). `PROD-04` is sized L for the infra core it edits, not for head pins: no migration is added.
- **`docker compose config` prints secrets** (`provider.env.example`); the check commands in the ADRs pipe it into a program that prints names only and pass `--no-env-resolution`.
- **`readiness.sh` `off-host-backup` always reports a finding** by design; it stays visible as `A-1` and `A-4` and must not be silenced.
- **Stale text confirmed:** the closing paragraph of the `ADR-0002` `R-143` addendum ("Nothing above exists in the tree yet…") is untrue now (`EXEC-SEAL-01`, `EXEC-HTTP-01`, `EXEC-PULL-01` are served); `D-203` lists the rest.

## Checks

All run on the committed tree of branch `agent/production-adr-pack-01` (venv: the shared runtime venv plus its `bootstrap` site-packages for `jsonschema`).

1. **Existence check** (kept outside git, in the session scratchpad: a script and its command registry): every inline-code token of the nine files is classified and verified against the tree,
   `contracts/api/v1/openapi.json`, `DEBT_REGISTER.md` and `OWNER_RULINGS_2026-09-17.md`: paths and patterns, operationIds, rulings (a lettered ruling must be a defined row), debt ids, ADR, migration, test-function, table,
   error-code, guard and image names, the `AD-` and `PROD-` ids against their definitions, the surface triple, the version, the contract version and the head against the real ones. Proposed things (paths, events, flags, the `0033` revision) are
   checked to be absent, so "new" is true. Commands that state a figure are run and compared; a figure command that is not registered is a failure, so an edited command cannot drop out silently. Last line:

   ```text
   1592 checked, 0 missing, 0 unclassified; 23 commands run here, 90 commands need a stand or a lane (their path/operationId/module parts were checked, the commands were not run); 318 further token occurrences accepted by class as literals, not verified
   ```

   The 90 commands that need a stand, a database or a lane were not run; their path, operationId and module parts were checked, the 23 that can run here were run and compared. Every unclassifiable token is a failure. The 318 token
   occurrences accepted as literals (section codes, status words, risk and criterion labels, external tool names, the proposed vocabulary of the new tools) fall in nine classes, each with a printed reason, and are not verified.
2. **Mutation proof of the checker** (on scratch copies, the real files untouched; "red" is a new `MISSING` or `UNCLASSIFIED` line): 14 of 14 mutations turned it red.

   | mutation | result |
   | --- | --- |
   | a script path misspelt (verify-deploy.sh) | red: MISSING path |
   | an operationId lengthened by one letter | red: MISSING operationId |
   | a ruling letter that does not exist (R-146z) | red: MISSING ruling |
   | a debt id that does not exist (D-9215) | red: MISSING debt |
   | a test function name lengthened | red: MISSING test-name |
   | the surface triple altered to 105 operations | red: MISSING figure-surface |
   | a figure command edited (src to srcs) | red: MISSING figure-command-registered |
   | a reference to a PROD id with no section (PROD-99) | red: MISSING prod-id |
   | a reference to an AD id no ADR defines (AD-77) | red: MISSING ad-id |
   | a migration name misspelt | red: MISSING migration |
   | a table name misspelt | red: MISSING identifier |
   | a quoted header value altered | red: UNCLASSIFIED |
   | an error code misspelt | red: MISSING identifier |
   | the head stated as 0031_executor_pull_channel | red: MISSING figure-head |
3. **Governance of the task file:** the one-liner of the task prints `[]`.
4. **`git diff --check 4d7b7c38..HEAD`:** exit 0, no output.
5. **`pytest -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`:** 105 passed in 19.80 s, exit 0.
6. **The ADR-index tests.** `tests/contract/test_validate_bootstrap.py` and `tests/contract/test_cp00_candidate.py` already fail in this environment on the base tree `4d7b7c38` (191 failures and errors, among them
   `tests/contract/test_cp00_candidate.py::ArchitectureCoverageTests::test_adr_files_index_and_review_agree`, which has been red since `ADR-0019` and `ADR-0020`). Run on the base tree and on this branch, the sets of failing test ids are identical (a `comm` of the two sorted lists
   prints nothing in either direction), so the pack adds and removes none. `scripts/validate_bootstrap.py` on the branch differs from the base only in two count lines (adrs 20 to 24, markdown_files 1736 to 1743); it reports no ADR or index error.
7. **Scope of the change:** `git diff --name-only 4d7b7c38..HEAD` lists the nine files of the table above and no other; `git status --short` is empty.


## Round 2 — the independent judge's findings and the owner's second poll round

Every finding was re-opened in the tree first. `fixed in` names the document and section; `refuted` and `corrected` give the evidence. Premises re-captured this round: `infra/deploy/reset.sh:236-243` (the `restore-complete` guard needs `database.dump`, `objects.attrs` and `objects`),
`infra/deploy/copy-serve.sh:631` and `:932` (`pg_dump` and `pg_restore` with `--no-owner --no-privileges`, the schema dropped and recreated), `infra/deploy/purge-product-data.sh:230-238` (`api_python` runs `product_purge` on the api service's `DATABASE_URL`), `src/auditmanager/storage/README.md` "Identity and idempotency" and `src/auditmanager/storage/blob_repository.py` `record_declared`,
`tests/unit/analysis/text_profiles/test_text_profile_packages.py:173-174` and `:197`, `src/auditmanager/analysis/profiles/ar_v2/registered.py`, `src/auditmanager/analysis/profiles/ar_v2/prompt_material.py`, `src/auditmanager/analysis/profiles/ar_v2/content.py` and the five `ar_v3` importers, `src/auditmanager/analysis/profiles/ar_v3/response_schema.py`, `src/auditmanager/analysis/profiles/ar_v3/prompt_material.py` and `src/auditmanager/runs/v3_review_artifact.py`, `src/auditmanager/access/accounts.py` (`reset_password`).

| # | Verdict | Where |
| --- | --- | --- |
| 1 (HIGH, restore consumes another format) | fixed | `ADR-0021` sections 5 and 6: the receipt is the copy record; the restore of that `db.dump` is `copy-serve.sh restore-db`, not `reset.sh --restore`, which accepts only its own directory format; the test is a restored-from-`--no-privileges`-dump integration test and a real `restore-db` drill in `PROD-17` (owner act) |
| 2 (MED, grants lost after restore) | fixed, differently from the suggestion | `ADR-0021` section 3: **no 0033 migration**; grants and the role are an idempotent step run by `deploy.sh`, `reset.sh --restore` and `copy-serve.sh restore-db`; `PROD-04` lists `reset.sh`, `copy-serve.sh`, `purge-product-data.sh` (the migrator URL) and drops the head pins. `product_purge.py` and `schema_coverage.py` are not touched because nothing pins a new head |
| 3 (MED, `R-93`) | fixed | `ADR-0021` section 5: `R-93` continues to bind, `R-146t` adds the refusal `stand-copy-fresh`, the receipt is the existing record, no second `dump-db`; new `AD-17`; plan section 7 item 11 |
| 4 (MED, first-boot binding) | fixed | `ADR-0021` section 2 (listener table, first boot, restore on a published host), `ADR-0023` section 3, `PROD-01`/`PROD-02`; the consequence of `R-146s` is stated |
| 5 (MED, re-upload after erase) | fixed, under `AD-07` | `ADR-0022` section 3: the `blob` row is deleted (a derived identity would meet a terminal `erased` row), a manifest keeps the hashes, a re-upload test is in `PROD-07` |
| 6 (MED, `PROD-14.0` files) | fixed | plan `PROD-14.0`: `test_text_profile_packages.py` lines 173-174 and 197 added, version included, one expectations file with one line per section |
| 7 (MED, import closure) | fixed, with a correction | `ADR-0024` section 2, `PROD-10`: the closure of `registered.py` as it stands is six modules plus six data files (the judge is right); splitting it (v3 uses only two constants) reduces what moves to three modules, six data files and two constants. Also the string search under-counts (`recorded_saved_plan.py`, `merge_publication_plan.py`, `finding_merge.py`) |
| 8 (MED, capacity) | fixed; path corrected | `ADR-0024` section 5, `ADR-0021` section 4, new `AD-18` and `PROD-20`. The watchdog is `src/auditmanager/jobs/lease.py:21` (the judge wrote runs/lease.py; the finding stands). The "better part of an hour" sentence was wrong |
| 9 (LOW, v3 and the old categories) | fixed | `ADR-0024` section 1 and the context: v3 is asked for all seven non-normative categories and its review artifact drops them; the user-visible claim holds; proposed debt row `PROD-D1` |
| 10 (LOW, "no copy off the host") | fixed | `ADR-0021` sections 9 and 10, plan `A-1`/`A-4`: three copies leave the host and none is a maintained backup; the latest pre-migration copy fetched for the `R-93` restore test is the exception to `A-1` |
| 11 (LOW) | fixed | the "single point of failure the owner asked to remove" clause is gone; `ADR-0021` section 8 reconciles `ADR-0015` with `R-146k`; the four index rows carry "mechanisms are unconfirmed AD-s" |
| 12 (LOW, sizes and hotspots) | fixed, one part refuted | `PROD-05b` is M; `PROD-07` stays L by an explicit new-tool rule (the purge it is modelled on is 1024 lines with 27 guard blocks and six test files); `PROD-04` lists the files; `PROD-13` no longer edits the runbook; `PROD-11` depends on `PROD-14.0`; the beta path includes `PROD-12` and `PROD-13` because `R-146q` keeps `B3`, `B5`, `B10` (not because of field cases, which `R-146v` dropped). Refuted: `schema_coverage.py` head pins for `PROD-04`, because it adds no migration. The wave table was re-checked for overlap |
| 13 (LOW, weak checks) | fixed | `ADR-0021` rows 8, 13, 15, `ADR-0023` row 4 (all three constants), the debt rows below; rows that can only show a record are labelled "documentation check only" |
| G1 (MinIO) | fixed | `PROD-19`, `ADR-0021` section 9, `A-3` |
| G2 (certificate 2026-12-30) | fixed | `PROD-01` deadline 2026-12-16 and `PROD-21` (owner, interim) |
| G3 (dumps never pruned) | fixed in part; the other part refuted | `ADR-0021` section 7 pruning rule and disk-free line, `PROD-09`. Refuted for the copy directory: `dump-db` removes older stamps, so only `infra/deploy/dumps/` grows |

The owner's answers `R-146o`…`R-146v` are applied as follows: `R-146o` in `ADR-0022` section 3, the `ADR-0012` addendum, `ADR-0022`'s "Amends" line and `PROD-22`; `R-146p` in `ADR-0021` section 2 (no provider or name is mentioned); `R-146q` and `R-146r` in `ADR-0024` sections 6 and 7 and out of the plan's open list;
`R-146s` in `ADR-0021` section 2 and `ADR-0023` section 3; `R-146t` in `ADR-0021` section 5 and `PROD-03`; `R-146u` in `ADR-0024` section 4 (no refusal is built); `R-146v` and the new `A-5` in `ADR-0024` sections 6 and 7 and `PROD-14`.

## Known limits

- Nothing here was executed against a stand, a container or a database. A check marked "no" in the ADR tables does not exist yet; a check marked "yes" was run here or is an existing test whose name was verified, not run.
- The existence check classifies every inline-code token and verifies it, but NOT_RUN_COUNT commands in the documents need a stand or a lane and were not run; their path, operationId and module parts were checked.
- Thirteen `AD-` decisions are unconfirmed; `AD-01` is read as confirmed by `R-146p` as to the name only; the plan's sizes are counted from greps, not from lane experience; the only date given is the `PROD-01` deadline.
- The local tracking refs `origin/dev` and `origin/main` were not fetched.
- The `pytest` run covers `tests/contract/program` and the two prose tests named by the task; the whole contract battery, the web battery and the gate were not run (`R-135`).

## Instruction to the integrator

1. Merge the ten files (they touch no hotspot; the only shared files are `docs/architecture/ADR_INDEX.md` and `docs/architecture/adr/ADR-0012-expert-decision-ledger-and-kb-projection.md`).
2. Put the unconfirmed `AD-` questions (the table above) and the open questions to the owner as one package (`PROD-00`) and record the answers as a ruling.
3. Enter the proposed rows below into `DEBT_REGISTER.md` with their ids, and record `A-4` and `A-5` beside `A-1`…`A-3`.
4. Dispatch no `PROD-` item that depends on an unconfirmed `AD-` decision. `PROD-14.0`, `PROD-09`, `PROD-12` (owner and expert work), `PROD-19`, `PROD-21` and `PROD-13`'s preflight do not depend on one. `PROD-01` waits for the server name (`R-146p`) and has a deadline of 2026-12-16.
5. `ADR-0002`'s stale paragraph and the `D-203` documents are `PROD-16`; this lane did not edit them (not in its allowed paths).

## Forbidden hotspots

`git diff --name-only 1a7f6f65 HEAD` (against the merged integration commit) lists exactly the ten files of the table above and nothing else (output in Checks). `contracts/**`, `db/migrations/**`, root dependency and lock files, `Makefile`, `infra/**`, `.github/**`, `src/**`, `web/**`,
`scripts/**`, `tests/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md` and `OWNER_RULINGS_2026-09-17.md` are untouched.

## Proposed debt-register rows

For the integrator to enter (ids to be assigned; the register's own rule is that every row carries its own check). One row per `PROD-` epic of the plan, plus `PROD-D1`, which is a debt without an item. A check labelled "documentation check only" proves that a record exists, not that the thing works.

| Proposed id | Row | Needs |
| --- | --- | --- |
| **PROD-00** | thirteen architect's `AD-` decisions and the plan's open questions are unconfirmed | the owner, as one poll package; check (documentation check only): `grep -n "PRODUCTION-ADR-PACK-01" docs/program/OWNER_RULINGS_2026-09-17.md` finds the ruling that answers them |
| **PROD-01** | the production TLS terminator, its renewal, HSTS, the `Secure` cookie and the conditional 443 listener are outside the repository (`D-191`); the live certificate expires on 2026-12-30 | a Sonnet infra lane and the owner (server name, DNS, ports, first issuance), deployed by 2026-12-16; check: `curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' https://<name>/login` prints `200 0`, `echo \| openssl s_client -connect <name>:443 -servername <name> 2>/dev/null \| openssl x509 -noout -checkend 1209600` exits 0, and `pytest -q tests/integration/composition/test_proxy_tls_path.py` passes |
| **PROD-02** | a deployment does not fail, and 443 is not kept shut, while `admin`/`password` is valid; `copy-serve.sh restore-db` does not revoke credentials (`R-146i`, `R-146s`) | a Sonnet infra lane; check: on a database with the seeded account `infra/deploy/verify-deployed.sh` exits non-zero and `$DC port proxy 8443` exits non-zero, and after the password change both succeed |
| **PROD-03** | `deploy.sh` does not refuse `migrate` without a fresh copy receipt once real data exists (`R-146t`; `R-93` binds meanwhile) | a Sonnet infra lane and the owner (copy key, first copy); check: `pytest -q tests/integration/composition/test_deploy_script_refusals.py -k stand_copy_fresh` passes with the guard present and the guard-deleted copy no longer refuses |
| **PROD-04** | the application connects as the database owner, a superuser by the image's behaviour; every restore loses grants because dumps use `--no-privileges` (`R-146n` item 1) | a Sonnet infra lane; check: the role query of `ADR-0021` row 7 prints `f\|f\|f\|t` before and after a `restore-db` rehearsal |
| **PROD-05** | no container has a memory or log-size limit (`D-166`, `R-146n` item 2) | the owner's measurement on the VPS, then a Sonnet lane; check: the command of `ADR-0021` row 8 prints `[]` |
| **PROD-06** | sign-in, role grant and password change are not journalled (`R-146n` item 6) | a Sonnet lane; check: `select event_type, count(*) from audit_event where event_type like 'access.%' group by 1` lists the six types after one of each |
| **PROD-07** | no operation erases one project (`R-146c`, `R-146o`) | a Sonnet lane; check: `pytest -q tests/integration/recovery/test_project_erase.py` (including the byte-identical re-upload test) and `select count(*) from blob where state = 'erasure_pending'` prints `0` |
| **PROD-08** | the key ring is in no copy (`R-146n` item 7) | the owner; check: the SHA-256 of the ring line from `sed -n 's/^AUDITMANAGER_SECRETS_KEYS=//p' infra/deploy/env/provider.env \| sha256sum` equals the one recomputed from the decrypted copy |
| **PROD-09** | no manual dependency and image scan, and no pruning of `infra/deploy/dumps/`, is part of a release (`R-146h`, `D-122`) | a Sonnet lane; check: `scripts/release/manual_scan.sh --check-tools` exits non-zero with a scanner missing; `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit (documentation check only) |
| **PROD-10** | the live journey drives an АР v1 run and v3 imports v2 modules | a Sonnet lane; check: `grep -rn "profiles.ar_v2" src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised` prints nothing and the live journey passes in a lane stand |
| **PROD-11** | АР v1 and v2 are still in the product (`R-146l`); after the removal the seven non-normative finding categories stay declared | a Sonnet lane that owns the contract; check: `grep -rn "AR_TEXT_PROFILE" src` and `grep -rn "profiles.ar_v2" src` print nothing, and `python3 -I -c "import json;print('builtin' in json.dumps(json.load(open('contracts/api/v1/openapi.json'))))"` prints `False` |
| **PROD-12** | АР v3 cannot run until the reviewed pack is installed (`D-204`) | the owner and a qualified expert; check: `python -m auditmanager.runs.v3_pack_cli verify --manifest infra/deploy/ar-v3-pack/<file>` exits 0 |
| **PROD-13** | the OpenRouter model identity is unproven (`W56A-MODEL-PIN-01` stopped) and `allow_client_documents` is false on the connection | the owner (credential, approval under `R-29`) and a Sonnet probe lane; check: `infra/deploy/readiness.sh \| grep -E 'readiness OK +(provider-mode\|executor-source)'` prints both lines; the probe report has a `reported_model:` line per pinned model (documentation check only) |
| **PROD-14** | all 14 non-АР profiles are `draft` (`D-178`) and, once reviewed, unmeasured on real text (`A-5`) — the primary task until the beta (`R-146l`, `R-146v`) | experts and the owner, then Sonnet lanes; check: `python3 -I -c "import json,glob;print(sorted(json.load(open(f))['status'] for f in glob.glob('src/auditmanager/analysis/text/profiles/*/profile.json')))"` prints fourteen `reviewed` |
| **PROD-15** | no exposure review covers the runner channel, the АР v3 routes and the production terminator (`D-217`) | a Sonnet read-only lane and the owner; check (documentation check only): `grep -c "getExecutorTaskImage\|getArV3BetaPackStatus" docs/program/EXPOSURE-REVIEW-01.md` is at least 2 in the new review |
| **PROD-16** | documents are behind the tree (`D-203`; the `ADR-0002` `R-143` addendum's closing paragraph) | the integrator; check: `pytest -q tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` |
| **PROD-17** | no release rehearsal, restore drill at the released head or purge rehearsal has been run for the production release (`D-216`) | the owner and the integrator; check: `ADR-0021` rows 1 to 6 on the live name, and the drill record carries `head:` and `result: pass` lines (row 15, documentation check only) |
| **PROD-18** | a complete gate cannot run on the development host (`D-205`) | the owner (environment) and the integrator; check: `make gate-preflight` passes and the gate log ends with `GATE OK` |
| **PROD-19** | the source-built MinIO has an archived upstream (`D-119`) and an uninventoried volume (`D-123`) and no scan covers it (`A-3`) | the owner's decision; check (documentation check only): the decision is in the release record; the inventory is `copy-serve.sh capacity` on the stand |
| **PROD-20** | an attempt is failed at 900 s, a large real document can exhaust its attempts (`D-171`, `D-175`) | the owner's measurement and decision, then a Sonnet lane; check: `python3 -I -c "import re;print(re.search(r'ATTEMPT_WATCHDOG_SECONDS = (\d+)',open('src/auditmanager/jobs/lease.py').read()).group(1))"` prints the decided value, or an input above the page limit is refused with `analysis_input_budget_exceeded` (test) |
| **PROD-21** | the live certificate expires on 2026-12-30 and its renewal is not in the tree (`D-191`) | the owner, before 2026-12-16; check: `echo \| openssl s_client -connect <name>:443 -servername <name> 2>/dev/null \| openssl x509 -noout -checkend 1209600` exits 0 |
| **PROD-22** | the frozen domain-contract sentence "never deletes decision, finding or audit history" contradicts the erase exception (`R-146o`) | the contract owner's slot; check: the sentence in `contracts/domain/v1/state-machines.json` names the exception and `pytest -q tests/contract` stays green |
| **PROD-D1** | the v3 prompt and schema solicit seven non-normative categories that the review artifact drops, so the model's output for them is paid for and never shown (`src/auditmanager/analysis/profiles/ar_v3/response_schema.py`, `src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`, `src/auditmanager/runs/v3_review_artifact.py`) | a later prompt decision (not an item of this plan); check (documentation check only): `grep -n "internal_contradiction" src/auditmanager/analysis/profiles/ar_v3/response_schema.py` stays a hit until the prompt changes |
