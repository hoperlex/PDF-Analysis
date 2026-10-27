# AR v3 beta — what the owner does on the live host (steps 10–12 of the activation plan)

Written 2026-10-27 by the integrator (`R-146ba`, `R-146bb`; accepted risks `A-10`, `A-11`; debt `D-247`); the commands of steps 10b and 11, the rollback and the numeric sentence were corrected 2026-10-28 by `AR-V3-JUDGE-FIXES-01` after an independent read. **Nothing in this file has been run on a live host.** Everything before it was done on this development host and is recorded in `AR-V3-ACTIVATION-FEASIBILITY-01.md`, `AR-V3-ACTIVATION-PREP-01.md`, `AR-V3-PROMOTE-REHEARSAL-01.md` and `AR-V3-PROMOTE-01.md`: the decision file, the 22 query vectors (made in a hash-checked environment, the first batch byte-identical to the image-built vectors), the six scope maps, an independent second AI check of every input (AI to AI; **no subject-matter expert took part**; the norms were **not** compared with the official edition by a human), six rehearsed promotions with replay, a sealed pack and an offline `verify` — all on the local custody lane `auditmanager-ar-beta-custody`, which is NOT the live database. The sealed manifest names sets in that lane's database, so it is **not** the file to install.

## What the owner needs

| Item | Where | Note |
| --- | --- | --- |
| The six bundles with the independent expected digests | `.local/ar-v3-draft/independent/bundle-{F1,F2,A1,A2,S1,S2}/` on the development host (`map.json`, `request.json`) | Copy the six directories to the live host (for example `tar -C .local/ar-v3-draft/independent -cf ar-v3-bundles.tar bundle-F1 bundle-F2 bundle-A1 bundle-A2 bundle-S1 bundle-S2`). They hold 22 query vectors and map ids, **no norm text**; keep mode 0700. |
| The set ids (never mint new ones) | `.local/ar-v3-draft/set-ids.json`: F1 `nrs_01M5YF1W4BG5260JTSCAZP3F58`, F2 `nrs_01M5YF1WVZYFD50K47BDYZM59D`, A1 `nrs_01M5YF1XMMCHT6F6K6HWZEJG4H`, A2 `nrs_01M5YF1Y8EBK2CBW9JGFADFK31`, S1 `nrs_01M5YF1YXN8WZTV8TFKZ0EWVTZ`, S2 `nrs_01M5YF1ZFPGBN4PMERTPN6GA27` | They are already inside each `request.json`. |
| The decision file and the seal values | `docs/program/ar-v3-beta/decisions.json`, `scopes.json`, and `AR-V3-PROMOTE-01.md` section 6a «Seal values for the live host» (the Russian values of the attestation) | `scopes.json` already holds the six `map_sha256`. Use the values of section **6a**, not the table of section 6 (that one is the record of the custody-lane seal). |
| The snapshot on the live database | snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff` | **Step 10a** below. |

## Where the commands of steps 10b and 11 run (read this first)

The Python tools are **not** run from a checkout with `PYTHONPATH=src` and the stand's `DATABASE_URL`: on the live host that URL and `S3_ENDPOINT_URL` use compose host names (`infra/deploy/env/alpha.env.example`: `…@postgres:5432`, `http://s3:9000`), `postgres` and `s3` publish no port (`compose.server.yml`: «NO `ports:`»), and the `api` image carries only `src/`, `db/`, `contracts/`, `fixtures/recorded/` and `docs/program/P02_LOCK.json` (`infra/deploy/Dockerfile.api`): no `docs/program/ar-v3-beta/`, no bundles, no `scopes.json`. So each tool runs in a **one-off `api` container** (`compose run`): it already has the stand's `DATABASE_URL` (the application role's) and `S3_*` in its environment, it sits on the compose network, and the bundles and `scopes.json` come in as a **read-only bind mount** from the host. The pattern is the one `deploy.sh` and `erase-project.sh` use (`compose run --rm --no-deps -T [--user …] [-v …] --entrypoint python api -m …`); the credentials stay in `alpha.env` and are never typed or pasted.

```bash
# On the live host, in the clone, at the tree that is deployed (compose.server.yml is run from the repository root).
DC="docker compose --env-file infra/deploy/env/alpha.env --file infra/deploy/compose.server.yml"
# Inside the clone and ABSOLUTE: a -v source is resolved by the docker daemon, not the shell, and a relative or missing
# source arrives as an EMPTY directory (DEPLOYMENT_RUNBOOK.md, «a mount arrives empty», D-37; keep files inside the clone).
WORK="$PWD/.local/ar-v3-activation"
mkdir -p "$WORK/out" && chmod 0700 "$WORK"
tar -C "$WORK" -xf ar-v3-bundles.tar                         # bundle-F1 … bundle-S2
cp docs/program/ar-v3-beta/scopes.json "$WORK/scopes.json"    # if this tree lacks the file, copy it from the development host
ls "$WORK"                                                    # six bundle-* directories, scopes.json, out; anything less: stop
cli() {   # one tool call, in a throw-away api container, as the operator's uid (so a 0700 directory is readable)
  $DC run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$WORK:/work:ro" --entrypoint python api "$@" </dev/null
}
cli -m auditmanager.norms.retrieval.promote_cli --help >/dev/null && cli -m auditmanager.runs.v3_pack_cli --help >/dev/null && echo TOOLS PRESENT
```

If the last line does not print `TOOLS PRESENT` (`No module named …`), the deployed image predates the two tools: stop and have the integrator deploy a tree that holds them; nothing below can be run another way. `docker compose config` prints every secret in clear (runbook): do not use it to debug.

## Step 10a — the snapshot on the live database (owner window)

Confirm that the live database holds the qualified snapshot (the local logs of 2026-10-21 say «full match», `CURRENT_STATE` said «not run»: not resolvable from the development host) and that it is designated current. If it is not there, follow `STAND-NORMS-IMPORT-RUNBOOK-01.md` first (the 674 documents, 28,920 object bindings). The expected proof digests are in every `request.json`: `snapshot.content_digest` `0a1bafe103ff…` and `build.embedding_set_sha256` `e7fac64c90b9…`.

## Step 10b — promote the six sets (live database, one scope at a time)

Environment: the `cli` function above (the stand's own `alpha.env` supplies the database and object-store settings inside the container).

Both loops run in a subshell with `set -euo pipefail`, so they **stop at the first refusal** (a non-zero exit of the tool: 2 refused, 3 uncertain) or at the first output that is not the expected line, and print their closing line only if all six passed.

```bash
PROMOTE="-m auditmanager.norms.retrieval.promote_cli"

# 1. plan (read only) for all six, before any promote
( set -euo pipefail
  for S in F1 F2 A1 A2 S1 S2; do
    cli $PROMOTE plan "/work/bundle-$S" | tee "$WORK/out/plan-$S.txt"
    grep -qx 'verdict: matched' "$WORK/out/plan-$S.txt"
  done
  echo "ALL SIX PLANS MATCHED" )

# 2. only after the line above: promote, then the replay
( set -euo pipefail
  for S in F1 F2 A1 A2 S1 S2; do
    cli $PROMOTE promote "/work/bundle-$S" | tee "$WORK/out/promote-$S.txt"
    grep -qx 'promote: verified' "$WORK/out/promote-$S.txt"     # 'replayed: false' on a first promotion
    cli $PROMOTE promote "/work/bundle-$S" | tee "$WORK/out/replay-$S.txt"
    grep -qx 'promote: verified' "$WORK/out/replay-$S.txt"
    grep -qx 'replayed: true' "$WORK/out/replay-$S.txt"         # the replay: nothing changes
  done
  echo "ALL SIX PROMOTED AND REPLAYED" )
```

`plan` must print `verdict: matched` for all six before any `promote` (the line is in the middle of the output, followed by the `item:` and `designation:` lines; that is why the loop greps it and does not trust the exit status alone — a bundle without expectations prints `not_compared` and exits 0). A differing digest prints `REFUSED [expected_digest_mismatch]` naming the artifact, exits 2 and writes nothing (the set id is not consumed). Exit 3 means «uncertain»: some admission may exist; stderr names the `set_id` and the exact command to run next, and re-running the same command is idempotent. **Stop on the first refusal and report it; do not edit a bundle.** If a first `promote` prints `replayed: true`, that scope was promoted by an earlier attempt: read its digests, do not mint another id, and continue. The rehearsal on the local lane took 2–5 s per promotion (1.7–2.0 s per `plan`).

Expected values (from the independent check; compare with `grep -E '^(catalogue_sha256|prompt_part_characters|set_sha256):' "$WORK"/out/plan-*.txt`): `catalogue_sha256` `4b201656…a555` identical in all six; `prompt_part_characters` F1 19,249 · F2 11,958 · A1 15,032 · A2 14,143 · S1 **21,921 (79 characters under the 22,000 cap)** · S2 18,930; `set_sha256` per scope in `AR-V3-PROMOTE-01.md` section 4. A different figure means a different snapshot or build.

## Step 11 — seal, install, restart

```bash
# Seal against the LIVE database (read only), as the operator's uid, writing to the out directory.
# --decision-ref and --scope-statement: the two values of AR-V3-PROMOTE-01.md section 6a, verbatim.
$DC run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$WORK:/work:ro" -v "$WORK/out:/out" \
    --entrypoint python api -m auditmanager.runs.v3_pack_cli seal --scopes /work/scopes.json \
    --reviewer "ИИ-интегратор (Claude Code), сессия integration/ar-close-1026" \
    --capacity "ИИ-интегратор по поручению владельца (R-146ba); не эксперт предметной области" \
    --reviewed-at "$(date -u +%F)" \
    --decision-ref "<as in AR-V3-PROMOTE-01.md section 6a>" --scope-statement "<as in AR-V3-PROMOTE-01.md section 6a>" \
    --out /out/pack.json </dev/null

# Offline verify (no database is read): exit 0 and one «v3-pack OK pack_sha256=…» line.
$DC run --rm --no-deps -T --user "$(id -u):$(id -g)" -v "$WORK/out:/out:ro" \
    --entrypoint python api -m auditmanager.runs.v3_pack_cli verify --manifest /out/pack.json </dev/null
```

Before sealing, recompute `sha256sum docs/program/ar-v3-beta/decisions.json`: it must equal the digest written in `--decision-ref` (section 6a gives it). `seal` refuses unless each of the six scopes selects exactly one verified set in the live database (`scope_unverified`) and writes nothing then.

Then install and apply:

```bash
install -m 0644 "$WORK/out/pack.json" infra/deploy/ar-v3-pack/pack.json   # readable by uid 10001; the directory is bind-mounted read-only at /run/ar-v3 in api AND worker
#   in infra/deploy/env/alpha.env:   AR_V3_BETA_PACK_MANIFEST=/run/ar-v3/pack.json
$DC up -d --no-deps api worker        # NOT «restart»: see below
$DC ps api worker                     # both running, freshly created
$DC exec -T api python -m auditmanager.runs.v3_pack_cli verify --manifest /run/ar-v3/pack.json
```

**`docker compose restart` re-reads no environment**: a container's environment is fixed when it is created, and `restart` re-creates nothing, so after editing `alpha.env` only `up -d` (which recreates a service whose configuration changed) applies the variable; the same holds for removing it in the rollback below. A manifest the server refuses stops the container with `ConfigurationError: AR_V3_BETA_PACK_MANIFEST names a reviewed-pack manifest the server refuses: <reason>` (`AR-V3-BETA-PACK-INSTALL-01.md` section «Operator runbook», step 5); read `$DC logs api worker`, correct the file, run `up -d` again. Then open «Настройки анализа»: the pack panel must show the six scopes and the attestation exactly as sealed (the system displays it verbatim and states that it does not check it).

### Rollback (withdraw the pack)

1. **Look before you act.** Open the group review (or «Очередь»): note every AR v3 Run that is `queued`, `running` or `validating`. Prefer to withdraw only when there is none.
2. **Remove `AR_V3_BETA_PACK_MANIFEST`** (a blank value counts as unset) from `infra/deploy/env/alpha.env` and apply it with `$DC up -d --no-deps api worker` — **not** `restart` (it would leave the old value in both containers). The file in `infra/deploy/ar-v3-pack/` may stay; nothing reads it without the variable.
3. **What this does:**
   - **(a) A Run that is queued or running at the restart dies.** With no pack installed the worker refuses to execute an AR v3 Run: `executor.py` raises `required_norm_unavailable` («the pinned AR v3 beta reviewed pack is not installed»), and the carrier's `_record_crash` closes the Run `failed` with that reason (`interrupted_reason: crashed`) and fails its Job, from whatever state it had reached, a Run resumed after the restart included. A provider call already paid for, and a CITE stage not yet written, are lost to that Run: its saved reply stays in storage, but the Run is not resumed and is not re-executed; a repeat needs a new group start, which needs the pack installed again. This is the caveat of `AR-V3-BETA-PACK-INSTALL-01.md` (Operator runbook, step 6: «its remaining members refuse execution while no pack is installed»).
   - **(b) Findings and verdicts already published stay**, stay readable and stay decidable. `listRunFindings`, `getFinding`, `getRunNormVerification`, the group review and the verdict history read the database and the sealed review artifact, not the installed pack (`v3_review_reader.py`, `v3_norm_report.py`, `v3_published_findings.py` and `v3_group_review.py` hold no reference to the registry; read from the code, not run with the pack removed); `appendDecision` is the ordinary expert-role, idempotency-keyed write and does not consult it either. What changes on screen is the pack panel: «Настройки анализа» reports the pack as not installed.
   - **(c) New group starts refuse** with `dependency_unavailable / ar_v3_trusted_pack`; a replay of an old start key returns its original rows.
4. **Re-installing** later needs only the same file (or a fresh `seal`) and `up -d --no-deps api worker`; the rollback changes nothing in the database, and the six set ids stay.

## Step 12 — acceptance

`AR-V3-BETA-ACCEPT-01`: the recorded cases run on the development host; the live provider call needs `PROXY_LLM_BASE_URL` and `PROXY_LLM_TOKEN` in the environment of the process that runs it (ceiling 0.50 USD); the complete `make gate` with the literal `GATE OK` on the exact tree belongs to a window. Only after that: `RELEASES.md` and any instruction about `origin/main` (a separate direct owner instruction naming the exact SHA, `AGENTS.md` section 6).

## What stays true whatever happens here

`C05 C06 C08 C09 C10 C15 C21 C22` are `context_only` (the tool refuses an upgrade) and, as mapped, **still reach the model as context**; the 14 provisional citations carry empty `edition_evidence` and editions stated as «редакция локального корпуса, изменения не сверены с официальной редакцией»; the numeric **fields** are not served — `required_value` and `stated_value` are stored but no API response, CSV or workbook carries them — while **the model's own sentences and the norm quote are served and may contain figures that nothing checks as numbers**; the user-visible label «предварительная цитата» is switched off during the beta by the owner's choice (`R-146ba`, `A-10`) once lane S1's switch lands. A citation counts as provisional only if its quote was grounded to a paragraph the labelled provisional topic itself sent (`AR-V3-JUDGE-FIXES-01`); a quote found in another paragraph is withheld, not re-attributed. The Excel export of a published AR v3 Run reads its certified citations since the same fix, but it labels sheets from the version's portal companion for every Run: a version without one (the synthetic bare PDFs) is refused, typed `storage_integrity_error` with `role: source.structured_companion`.

## What was not verified (the integrator and the owner should know)

- No command of this file has been run against a live host, a live compose project or the application role's grants. The rehearsals ran as the single database role of the custody lane. `apply-grants.sh` gives the application role `SELECT, INSERT` on `norm_retrieval_set` and `norm_custody_binding` and `SELECT, INSERT, UPDATE, DELETE` on `norm_custody_admission`; whether `promote_cli` needs any other privilege was not exercised with that role. A `permission denied` is a stop-and-report; do not substitute `MIGRATOR_DATABASE_URL` without the integrator.
- Whether the deployed image holds `promote_cli` and `v3_pack_cli` (the `TOOLS PRESENT` line decides), and whether the checkout holds `docs/program/ar-v3-beta/scopes.json`, depends on the released tree and was not checked.
- Compose project naming, the snap-docker path caveat and the operator's uid inside the container follow the runbook and the two scripts named above; none was run for these tools.
- Rollback (a) is read from `executor.py` and `carrier.py`; (b) from the readers' source and their tests with the pack installed; neither was run with the pack removed.
