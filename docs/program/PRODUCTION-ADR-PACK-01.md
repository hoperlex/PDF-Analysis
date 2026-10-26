# PRODUCTION-ADR-PACK-01 — the architecture decisions of the production version

**Task:** [PRODUCTION-ADR-PACK-01](tasks/PRODUCTION-ADR-PACK-01.md). **Frozen base:** `integration/ar-close-1026` at `4d7b7c38dc8239df6831b2587b71c0d74e8b1ec0`. **Publication target:** none from this lane
(the integrator may merge it into `origin/dev`); no tag, no `origin/main`, no stand.

## Result

The owner's decisions of `R-146` are now architecture that can be tested: [`ADR-0021`](../architecture/adr/ADR-0021-production-topology-and-operations.md) (one VPS, TLS and renewal in `infra/`, roles, limits, copies, the release
checklist), [`ADR-0022`](../architecture/adr/ADR-0022-production-data-governance.md) (what is kept, the operator project erase, the purge at 1.0, egress, the key ring),
[`ADR-0023`](../architecture/adr/ADR-0023-production-identity-and-access.md) (one organisation, the default credential closed by the deploy, audited access changes),
[`ADR-0024`](../architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md) (АР is v3 only, the exact scope of the v1/v2 removal, OpenRouter and `R-133`, the single worker, the quality bar, the priority).
[`PRODUCTION-READINESS-PLAN-01.md`](PRODUCTION-READINESS-PLAN-01.md) turns them into 19 items (`PROD-00`…`PROD-18`) with dependencies, hotspot owners, sizes, executors and checks, a wave list with non-overlapping hotspots,
the accepted-risk register `A-1`…`A-4`, the open decisions and what the plan does not establish. Nothing was built and nothing is claimed done: no pack installed, no gate run, no deploy, no stand touched.

## Changed files

| File | Change |
| --- | --- |
| `docs/architecture/adr/ADR-0021-production-topology-and-operations.md` | new |
| `docs/architecture/adr/ADR-0022-production-data-governance.md` | new |
| `docs/architecture/adr/ADR-0023-production-identity-and-access.md` | new |
| `docs/architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md` | new |
| `docs/architecture/adr/ADR-0014-authz-classification-retention.md` | status line updated; dated addendum "Partially accepted by R-146 (2026-10-26)"; the original text unchanged |
| `docs/architecture/ADR_INDEX.md` | four new rows, the `ADR-0014` row updated, one paragraph on the post-CP-00 production ADRs |
| `docs/program/PRODUCTION-READINESS-PLAN-01.md` | new |
| `docs/program/tasks/PRODUCTION-ADR-PACK-01.md` | new |
| `docs/program/PRODUCTION-ADR-PACK-01.md` | this report |

## The architect's implementation decisions awaiting the owner's confirmation

`R-146` is the only source of owner decisions in the pack. Everything below is the architect's, within `R-146`, labelled `AD-nn` in the ADRs and phrased here as the question to put to the owner.

| Id | Where | Question |
| --- | --- | --- |
| `AD-01` | `ADR-0021` section 2 | Terminate TLS in the stack with an ACME client container (HTTP-01), public port 80 for challenge and redirect only, the plain listener on loopback, and a 14-day certificate-expiry failure in `verify-deployed.sh`? Which DNS name (is the `sslip.io` one acceptable)? |
| `AD-02` | `ADR-0021` section 3 | Keep the current owner role as the migrator and add one restricted application role (no DDL, no `TRUNCATE`, `SELECT` and `INSERT` only on append-only tables), created by a deploy step and granted by a `0033` migration? |
| `AD-03` | `ADR-0021` section 5 | Enforce the manual pre-migration dump by a `deploy.sh` refusal (a new `dump-db.sh` and a receipt, the `R-93` pattern), or keep it a checklist line only? |
| `AD-04` | `ADR-0021` section 4 | Take memory and log limits from a measurement on the VPS, fixing no number now? What is the VPS size? |
| `AD-05` | `ADR-0021` section 7 | A manual-scan helper that prints an inventory, runs the scanners that are installed and never prints a pass when one is missing, plus the eight-line checklist in `RELEASE_PROCESS.md`? |
| `AD-06` | `ADR-0022` section 3 | Should erasing a project also delete its findings, evidence quotes and expert decisions (my default: yes, because they hold verbatim client text; only the erase tool, as table owner, may switch the append-only triggers off), and may the `blob` row of an erased document keep its SHA-256 and size as the frozen domain contract says? |
| `AD-07` | `ADR-0022` section 3 | The erase tool: dry run by default, a plan SHA-256, a closed list of reason codes, the `era_` identity, events `erasure.requested` and `erasure.completed`, four phases with a resume? |
| `AD-08` | `ADR-0022` section 6 | The key ring: one encrypted copy off the VPS, verified by the SHA-256 of the ring line on a second machine, redone after every rotation? |
| `AD-09` | `ADR-0022` section 4 | At 1.0, run the existing whole-product purge (it has no selector for v1/v2) after a rehearsal on a restored copy, then review and archive the test accounts? |
| `AD-10` | `ADR-0023` section 4 | Six `access.*` events, no IP address, a failed sign-in journalled only when it starts a cooling-off, and `access.role_revoked` added beside the owner's "role grant"? |
| `AD-11` | `ADR-0023` section 3 | A failing default-credential check ends `verify-deployed.sh` and `deploy.sh` non-zero naming the logins but stops no service; or should it also take the proxy down? A fresh host stays on loopback until the password is changed? |
| `AD-12` | `ADR-0024` section 2 | Remove АР v1/v2 in the order extract the shared v2 modules, re-base the live journey, then remove and reseal; `startRun` on АР answers `section_profile_unavailable`; the `FindingCategory` list stays as it is? |
| `AD-13` | `ADR-0024` section 3 | Pin the exact string OpenRouter reports, add no alias list to the run path, and replace `W56A-MODEL-PIN-01` by a paid probe task under `R-29`? |
| `AD-14` | `ADR-0024` section 4 | Set `allow_client_documents` true on the OpenRouter connection at the release as a recorded revision, and should the flag become a refusal (nothing reads it today)? |
| `AD-15` | `ADR-0024` section 7 | "Full version" of a section means a reviewed profile, at least one positive and one negative non-synthetic, non-client case, and an expert's acceptance? Who are the section experts? |
| `AD-16` | `ADR-0021` section 10, `ADR-0022` section 5 | The reopen triggers proposed for `A-2` (a client asks for terms), `A-3` (an advisory, or any release outside the owner's organisation) and `A-4` (as `A-1`, and any promise of a recovery time)? |

Open questions that are not `AD-` decisions (plan section 7): whether `R-146f` also waives the beta criteria B3, B5 and B10; how «бета 0.1.1» maps to `1.0.0-beta.N`; the VPS size; the DNS name. Still open after `R-146` and not asked: the legal-hold authority and classification labels
(`ADR-0014`), corpus licensing (`NORM-Q04`), internal or external beta users (`D-4.1`), off-host custody, a second operator.

## Facts that changed the design (each re-read in the tree on 2026-10-26)

- **`R-146i` narrows `R-46`.** `readiness.sh` is, by ruling `R-46`, a report that blocks nothing, and neither `deploy.sh` nor `verify-deployed.sh` runs `auditmanager.access.check` (task premise P-05). `ADR-0023` makes the default-credential check the one check that fails a deploy, without stopping services (`D-72`, `R-52`).
- **`deploy.sh` takes no dump.** `R-93` guards only an open, unattested copy record (P-04), and no non-destructive operator dump command exists (`reset.sh` and the purge destroy data afterwards; `copy-serve.sh` is the owner's forced-command key). `AD-03` and `PROD-03` follow.
- **The application connects as the database bootstrap user** (`POSTGRES_USER`), which the official image makes a superuser (assumption; the query to confirm is in `ADR-0021` row 7). `product_purge.py` needs the table owner, so the roles are keep-the-owner-as-migrator, not a re-ownership.
- **The erase has a frozen-contract problem.** The domain contract says erasing bytes "never deletes decision, finding or audit history", while `finding_observation`, `finding_evidence` and `expert_decision_event` hold verbatim client text and are immutable or append-only by trigger. `AD-06` states the choice and the fallback.
- **The only automatic retention runs inside a runner's claim call** (P-11), so it never runs without a polling runner.
- **`allow_client_documents` is stored, shown and never read** (P-07): the imported OpenRouter connection says «не отправляются» while analyses through it send document text.
- **v3 stands on v2** (P-06): six modules outside `ar_v2` import it; `AR_TEXT_PROFILE` is named in six source files; 65 test files name v2 or `AR_TEXT_PROFILE`. The live journey uploads an АР bundle (P-10), so the removal needs its prerequisite item.
- **The model comparison is exact and has no alias path** (P-08, P-12); the OpenRouter name must therefore be the observed reply string.
- **A new migration head touches 12 files that pin the current head** (`D-213`), which is why `PROD-04` is sized L.
- **`docker compose config` prints secrets** (`provider.env.example`); the check commands in the ADRs pipe it into a program that prints names only and pass `--no-env-resolution`.
- **`readiness.sh` `off-host-backup` always reports a finding** by design; it stays visible as `A-1` and `A-4` and must not be silenced.
- **Stale text confirmed:** the closing paragraph of the `ADR-0002` `R-143` addendum ("Nothing above exists in the tree yet…") is untrue now (`EXEC-SEAL-01`, `EXEC-HTTP-01`, `EXEC-PULL-01` are served); `D-203` lists the rest.

## Checks

All run on the committed tree of branch `agent/production-adr-pack-01` (venv: the shared runtime venv plus its `bootstrap` site-packages for `jsonschema`).

CHECKS_PLACEHOLDER

## Known limits

- Nothing here was executed against a stand, a container or a database. A check marked "no" in the ADR tables does not exist yet; a check marked "yes" was run here or is an existing test whose name was verified, not run.
- The existence check classifies every inline-code token and verifies it, but 106 commands in the documents need a stand or a lane and were not run; their path, operationId and module parts were checked.
- `AD-` decisions are unconfirmed by definition; the plan's sizes are counted from greps, not from lane experience; no calendar is given.
- The local tracking refs `origin/dev` and `origin/main` were not fetched.
- The `pytest` run covers `tests/contract/program` and the two prose tests named by the task; the whole contract battery, the web battery and the gate were not run (`R-135`).

## Instruction to the integrator

1. Merge the nine files (they touch no hotspot; the only shared file is `docs/architecture/ADR_INDEX.md`).
2. Put the `AD-` questions and the open questions to the owner by direct poll (`PROD-00`) and record the answers as a ruling.
3. Enter the proposed rows below into `DEBT_REGISTER.md` with their ids, and record the `A-4` risk beside `A-1`…`A-3`.
4. Dispatch no `PROD-` item that depends on an unconfirmed `AD-` decision. `PROD-14.0`, `PROD-09`, `PROD-12` (owner and expert work) and `PROD-13`'s preflight do not depend on one.
5. `ADR-0002`'s stale paragraph and the `D-203` documents are `PROD-16`; this lane did not edit them (not in its allowed paths).

## Forbidden hotspots

`git diff --name-only 4d7b7c38..HEAD` lists exactly the nine files of the table above and nothing else (output in Checks). `contracts/**`, `db/migrations/**`, root dependency and lock files, `Makefile`, `infra/**`, `.github/**`, `src/**`, `web/**`,
`scripts/**`, `tests/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md` and `OWNER_RULINGS_2026-09-17.md` are untouched.

## Proposed debt-register rows

For the integrator to enter (ids to be assigned; the register's own rule is that every row carries its own check). One row per `PROD-` epic of the plan.

| Proposed id | Row | Needs |
| --- | --- | --- |
| **PROD-00** | the architect's `AD-01`…`AD-16` and the plan's open questions are unconfirmed | the owner, by direct poll; check: `grep -n "PRODUCTION-ADR-PACK-01" docs/program/OWNER_RULINGS_2026-09-17.md` finds the ruling that answers them |
| **PROD-01** | the production TLS terminator, its renewal, HSTS and the `Secure` cookie are outside the repository (`D-191`) | a Sonnet infra lane and the owner (DNS, ports, first issuance); check: `curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' https://<name>/login` prints `200 0` and `pytest -q tests/integration/composition/test_proxy_tls_path.py` passes |
| **PROD-02** | a deployment does not fail while `admin`/`password` is valid (`R-146i`) | a Sonnet infra lane; check: `infra/deploy/verify-deployed.sh` exits non-zero on a database with the seeded account and `0` after the change |
| **PROD-03** | no dump precedes a migrating deploy (`R-146n` item 3) and no non-destructive dump command exists | a Sonnet infra lane; check: `test -x infra/deploy/dump-db.sh` and `grep -c "dump-receipt" infra/deploy/deploy.sh` prints at least 1 |
| **PROD-04** | the application connects as the database owner, a superuser by the image's behaviour (`R-146n` item 1) | a Sonnet lane that owns the migration head; check: `ls db/migrations/versions \| tail -1` names `0033` and the role query of `ADR-0021` row 7 prints `f\|f` |
| **PROD-05** | no container has a memory or log-size limit (`D-166`, `R-146n` item 2) | the owner's measurement on the VPS, then a Sonnet lane; check: `ADR-0021` row 8 |
| **PROD-06** | sign-in, role grant and password change are not journalled (`R-146n` item 6) | a Sonnet lane; check: `select event_type, count(*) from audit_event where event_type like 'access.%' group by 1` lists the six types after one of each |
| **PROD-07** | no operation erases one project (`R-146c`) | a Sonnet lane; check: `pytest -q tests/integration/recovery/test_project_erase.py` and `select count(*) from blob where state = 'erasure_pending'` prints `0` |
| **PROD-08** | the key ring is in no copy (`R-146n` item 7) | the owner; check: the SHA-256 of the ring line from `sed -n 's/^AUDITMANAGER_SECRETS_KEYS=//p' infra/deploy/env/provider.env \| sha256sum` equals the one recomputed from the decrypted copy |
| **PROD-09** | no manual dependency and image scan is part of a release (`R-146h`, `D-122`) | a Sonnet lane; check: `grep -n "manual_scan" docs/program/RELEASE_PROCESS.md` has a hit and `scripts/release/manual_scan.sh --check-tools` exits non-zero with a scanner missing |
| **PROD-10** | the live journey drives an АР v1 run and v3 imports v2 modules | a Sonnet lane; check: `grep -rn "profiles.ar_v2" src/auditmanager/analysis/profiles/ar_v3 src/auditmanager/analysis/recognised` prints nothing |
| **PROD-11** | АР v1 and v2 are still in the product (`R-146l`); after the removal five v2 finding categories stay declared in the contract and the `CHECK`s and no profile emits them | a Sonnet lane that owns the contract; check: `ADR-0024` rows 1 to 4 |
| **PROD-12** | АР v3 cannot run until the reviewed pack is installed (`D-204`) | the owner and a qualified expert; check: `python -m auditmanager.runs.v3_pack_cli verify --manifest infra/deploy/ar-v3-pack/<file>` exits 0 |
| **PROD-13** | the OpenRouter model identity is unproven (`W56A-MODEL-PIN-01` stopped) and `allow_client_documents` is false on the connection | the owner (credential, approval under `R-29`) and a Sonnet probe lane; check: `ADR-0024` rows 7 and 8 |
| **PROD-14** | all 14 non-АР profiles are `draft` (`D-178`, `D-183`) — the primary task until the beta (`R-146l`) | experts and the owner, then Sonnet lanes; check: `ADR-0024` row 9 prints fourteen `reviewed` |
| **PROD-15** | no exposure review covers the runner channel, the АР v3 routes and the production terminator (`D-217`) | a Sonnet read-only lane and the owner; check: `grep -c "getExecutorTaskImage\|getArV3BetaPackStatus" docs/program/EXPOSURE-REVIEW-01.md` is at least 2 in the new review |
| **PROD-16** | documents are behind the tree (`D-203`; the `ADR-0002` `R-143` addendum's closing paragraph) | the integrator; check: `pytest -q tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` |
| **PROD-17** | no release rehearsal, restore drill at the released head or purge rehearsal has been run for the production release (`D-216`) | the owner and the integrator; check: `ADR-0021` rows 1 to 6 and 15 on the live name |
| **PROD-18** | a complete gate cannot run on the development host (`D-205`) | the owner (environment) and the integrator; check: `make gate-preflight` passes and the gate log ends with `GATE OK` |
