# AR v3 beta — what the owner does on the live host (steps 10–12 of the activation plan)

Written 2026-10-27 by the integrator (`R-146ba`, `R-146bb`; accepted risks `A-10`, `A-11`; debt `D-247`). **Nothing in this file has been run on a live host.** Everything before it was done on this development host and is recorded in `AR-V3-ACTIVATION-FEASIBILITY-01.md`, `AR-V3-ACTIVATION-PREP-01.md`, `AR-V3-PROMOTE-REHEARSAL-01.md` and `AR-V3-PROMOTE-01.md`: the decision file, the 22 query vectors (made in a hash-checked environment, the first batch byte-identical to the image-built vectors), the six scope maps, an independent second AI check of every input (AI to AI; **no subject-matter expert took part**; the norms were **not** compared with the official edition by a human), six rehearsed promotions with replay, a sealed pack and an offline `verify` — all on the local custody lane `auditmanager-ar-beta-custody`, which is NOT the live database. The sealed manifest names sets in that lane's database, so it is **not** the file to install.

## What the owner needs

| Item | Where | Note |
| --- | --- | --- |
| The six bundles with the independent expected digests | `.local/ar-v3-draft/independent/bundle-{F1,F2,A1,A2,S1,S2}/` on the development host (`map.json`, `request.json`) | Copy the six directories to the live host (for example `tar -C .local/ar-v3-draft/independent -cf ar-v3-bundles.tar bundle-F1 bundle-F2 bundle-A1 bundle-A2 bundle-S1 bundle-S2`). They hold 22 query vectors and map ids, **no norm text**; keep mode 0700. |
| The set ids (never mint new ones) | `.local/ar-v3-draft/set-ids.json`: F1 `nrs_01M5YF1W4BG5260JTSCAZP3F58`, F2 `nrs_01M5YF1WVZYFD50K47BDYZM59D`, A1 `nrs_01M5YF1XMMCHT6F6K6HWZEJG4H`, A2 `nrs_01M5YF1Y8EBK2CBW9JGFADFK31`, S1 `nrs_01M5YF1YXN8WZTV8TFKZ0EWVTZ`, S2 `nrs_01M5YF1ZFPGBN4PMERTPN6GA27` | They are already inside each `request.json`. |
| The decision file and the seal values | `docs/program/ar-v3-beta/decisions.json`, `scopes.json`, and `AR-V3-PROMOTE-01.md` section «Seal» (the Russian values of the attestation) | `scopes.json` already holds the six `map_sha256`. |
| The snapshot on the live database | snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff` | **Step 10a** below. |

## Step 10a — the snapshot on the live database (owner window)

Confirm that the live database holds the qualified snapshot (the local logs of 2026-10-21 say «full match», `CURRENT_STATE` said «not run»: not resolvable from the development host) and that it is designated current. If it is not there, follow `STAND-NORMS-IMPORT-RUNBOOK-01.md` first (the 674 documents, 28,920 object bindings). The expected proof digests are in every `request.json`: `snapshot.content_digest` `0a1bafe103ff…` and `build.embedding_set_sha256` `e7fac64c90b9…`.

## Step 10b — promote the six sets (live database, one scope at a time)

Environment: the repository checkout at the released tree, `PYTHONPATH=src`, `DATABASE_URL` and the `S3_*` settings of the live stand (the stand's own `.env`; do not paste them anywhere).

```bash
CLI="python -m auditmanager.norms.retrieval.promote_cli"
for S in F1 F2 A1 A2 S1 S2; do
  $CLI plan bundle-$S            # must end: verdict: matched   (exit 0)
done
for S in F1 F2 A1 A2 S1 S2; do
  $CLI promote bundle-$S         # verified, replayed: false
  $CLI promote bundle-$S         # the replay: replayed: true, nothing changes
done
```

`plan` must print `verdict: matched` for all six before any `promote`; a differing digest prints `REFUSED [expected_digest_mismatch]` naming the artifact and writes nothing (the set id is not consumed). Stop on the first refusal and report it; do not edit a bundle. The rehearsal on the local lane took 2–5 s per promotion.

Expected values (from the independent check): `catalogue_sha256` `4b201656…a555` identical in all six; `prompt_part_characters` F1 19,249 · F2 11,958 · A1 15,032 · A2 14,143 · S1 **21,921 (79 characters under the 22,000 cap)** · S2 18,930. A different figure means a different snapshot or build.

## Step 11 — seal, install, restart

```bash
python -m auditmanager.runs.v3_pack_cli seal --scopes docs/program/ar-v3-beta/scopes.json \
  --reviewer "ИИ-интегратор (Claude Code), сессия integration/ar-close-1026" \
  --capacity "ИИ-интегратор по поручению владельца (R-146ba); не эксперт предметной области" \
  --reviewed-at <today YYYY-MM-DD> \
  --decision-ref "<as in AR-V3-PROMOTE-01.md>" --scope-statement "<as in AR-V3-PROMOTE-01.md>" \
  --out pack.json                # DATABASE_URL = the live database
python -m auditmanager.runs.v3_pack_cli verify --manifest pack.json     # offline, exit 0
```

Then: copy `pack.json` to `infra/deploy/ar-v3-pack/` on the host (readable by uid 10001; the directory is mounted read-only at `/run/ar-v3`); set `AR_V3_BETA_PACK_MANIFEST=/run/ar-v3/pack.json` in `alpha.env`; restart `api` and `worker`; open «Настройки анализа»: the pack panel must show the six scopes and the attestation exactly as sealed (the system displays it verbatim and states that it does not check it). Rollback: remove the variable and restart; the group start refuses again with `ar_v3_trusted_pack`.

## Step 12 — acceptance

`AR-V3-BETA-ACCEPT-01`: the recorded cases run on the development host; the live provider call needs `PROXY_LLM_BASE_URL` and `PROXY_LLM_TOKEN` in the environment of the process that runs it (ceiling 0.50 USD); the complete `make gate` with the literal `GATE OK` on the exact tree belongs to a window. Only after that: `RELEASES.md` and any instruction about `origin/main` (a separate direct owner instruction naming the exact SHA, `AGENTS.md` section 6).

## What stays true whatever happens here

`C05 C06 C08 C09 C10 C15 C21 C22` are `context_only` (the tool refuses an upgrade) and, as mapped, **still reach the model as context**; the 14 provisional citations carry empty `edition_evidence` and editions stated as «редакция локального корпуса, изменения не сверены с официальной редакцией»; numerical conclusions stay unavailable; the user-visible label «предварительная цитата» is switched off during the beta by the owner's choice (`R-146ba`, `A-10`) once lane S1's switch lands.
