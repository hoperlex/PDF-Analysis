# W54→W57 corpus chain — review and revision directives (2026-10-12)

Written by session `pdf-analysis-4e [7bbea6]` on `plan/corpus-chain`.

**What was reviewed.**

- The committed plans at `2b45a11`: `W54-PLAN.md` revision 3, `W55-PLAN.md` revision 3 and
  `W57-PLAN.md` revision 2.
- They were checked against the development line `origin/dev` `8722660` (the W53 gated candidate,
  migration head `0017_execution_queue`).
- Owner rulings R-75…R-84 come from `04de50c` (`integration/w53-close`).

**Who reviewed and how.** Three fresh-context read-only reviewers, one per plan. They read git
objects only; no suite, gate or stand access was used. Findings marked **[checked]** were
re-verified by hand.

**What the review did not see.** The unadopted 2026-10-08 planning layer, preserved in `97127ac`
on this branch. That layer already resolves some findings below, which is noted per item.

**Verdict.** None of the three plans could be frozen as written.

- The code lanes are largely sound.
- The step that puts the corpus on the deployed stand had no named executor, no backup or rollback
  basis, no stand capacity measurement and no stand-side verification.
- W57 revision 2 was never judged.

## 1. Findings

### 1.1 Blockers

**W54-B1. The base is gone.**

- W54 requires `W53-INT-CLOSE`, which does not exist; R-84 inserted W53-CLOSE.
- `W53C-STORE-01` edits `storage/**` and `ingest/reconciliation.py`, the seams CUSTODY is granted.
- R-76 requires a seam re-check before any code grant.
- W53-CLOSE defers D-141, D-142, D-143, D-146, D-148 and D-150 to W54. D-142 needs a migration.

**W54-B2 [checked]. The importer order contradicts the frozen custody design.**

- `NORM_CORPUS_CUSTODY.md` step 1 validates the target snapshot and document inside the intent
  transaction, and the binding names `norms_snapshot_id` and `norm_document_id`.
- The importer requires every admission to be `confirmed` before those rows exist.

**W55-B1 [checked]. No executor for the stand import.**

- The forced-command key admits only `receive` and `status`.
- `deploy-auto.yml` runs only `deploy.sh` and `verify-deployed.sh`.
- `MAIN_AUTODEPLOY_POLICY.md` authorises a ref update, not a data write.
- No stand-side count or digest report exists.
- *Partly addressed by the layer:* `FAST-PATH-NORMS-SECTIONS.md` §4 names the authorised integration
  task, but not its mechanism.

**W55-B2 / W54-M1. Corpus written into an unbacked stand without rollback.**

- The write is about 28.9k objects (≈ 4.0–4.75 GiB) plus rows, into the MinIO and PostgreSQL that
  hold client data.
- R-83 waives the inventory only for the MinIO image swap.
- W54 refers to `infra/deploy/lib/dump.sh`, "W53's backup floor" and `backup.sh`, none of which
  exists.
- Migrations 0018–0020 make a revert deploy fail the migrations-at-head guard.
- *The layer* required "an accepted W53 backup with a fresh off-stand copy". After R-77 that
  no longer exists.

**W57-B1. Revision 2 was never judged.** The judging record holds round 1 only. Eight round-1
resolutions are incomplete: D-1, D-4, D-5, D-7, G-3, G-7, G-10 and m-12.

**W57-B2 [checked]. The stand build of the retrieval set has no publication path.**

- The run-artefact protocol (`analysis_artifact_publication`, `0014`) makes `run_id`, `job_id` and
  `attempt_id` NOT NULL; an operator build has none of them.
- The plan has no pre-push check that the stand's content key equals the reviewed key.
- It sets no order and no rollback.

### 1.2 Majors

**Release chain [checked].**

- `VERSION=0.3.0`, no `v0.3.0` tag, and `W53-RELNOTES-STOP-01` is open.
- The plans target `v0.5.0`…`v0.8.1`.
- *Addressed in principle by the layer's* `ROADMAP-TO-BETA.md` §8.4.

**First `main` push since `alpha-w48.1`.** It would bundle migrations 0015–0019(20), the worker
service and the R-83 MinIO recreate.

**Embedding build.**

- No lane owns a resumable build command.
- BGE-IMAGE is built before EMBED's code exists.
- W57's C2 batch entry point was never applied to W54.

**Disk [checked].**

- Here: the plan assumes ≈ 30 GB free. `df` shows 15 GB today, and the operator peak is ≈ 15 GB.
- On the stand: never measured (D-2.4).

**Rulings issued after the plans.**

- R-82 conflicts with W55a's "re-audit copies the source snapshot" and with the layer's W57
  "re-audit copies the source set".
- R-80 conflicts with W55a's "every active complete account".

**W54 repair.**

- `ProxyDispatchError` is not exported from `analysis/public.py`.
- The 503 retry conflicts with the open `W53-EXEC-STOP-01`.
- The ≤ $0.041/page sample gate probably stops against R-27's $0.033–0.040.
- The D-126 suffix rule recreates the collision.

**W57.**

- Corpus coverage [checked]: no insolation norm at all, and no СП 2.13130 or СП 4.13130.
- Output cap [checked]: `MAX_OUTPUT_TOKENS=16000` at ≈ 71 tok/s is ≈ 225 s, over the ≈ 190 s
  deadline.
- Spend is $3.8–5.1 against the $5 cap.
- `ProviderMode`+`deterministic` widens shared schemas.
- `setCurrentNormSnapshot` can disable v3. *Already addressed by the layer.*
- `norm_verification` cannot see the whole corpus.
- The quote/value tokeniser is unspecified.
- Live acceptance demands outcomes that cannot be forced.

### 1.3 Sound

- Custody outbox and reconciler.
- The repair journal (an `outcome_unknown` call is never re-paid).
- The promotion DB as the source of ids; opaque ids; content-derived bundle names.
- Transport guards.
- Typed refusals.
- pgvector 0.8.6 already in the stand image.
- Round-2 fixes are present in W54 and W55.

## 2. Owner answers, 2026-10-12 (direct poll)

These are recorded in `ROADMAP-TO-BETA.md` §10.16 as K-1…K-4.

## 3. Revision directives (technical; the owner may override)

**CD-1 Base.**

- Revisions are written against `origin/dev` `8722660` plus the rulings at `04de50c`.
- The final pin sweep runs against W53-CLOSE's published `origin/dev` SHA. The migration head
  stays `0017`.
- W53-CLOSE's moved pins are the operation-role register, the screen-registry roles, the nginx
  security headers and the BFF same-origin check.

**CD-2 Migrations.**

- `0018` custody absorbs D-142's settlement state, plus any D-148 trigger change.
- `0019` workers.
- `0020` W55a, `0021` W55b, `0022` W56a, `0023` W57a, `0024` W57b.
- Each literal is re-assigned at its freeze by `pin_sweep` if a predecessor changes.

**CD-3 The road to the stand.** Each step is a separate act that needs a direct owner instruction
naming its exact SHA or bundle:

- **P1.** R-83's MinIO image swap rides the next `origin/main` publication. It is verified by
  reading back a sample of existing client objects.
- **P2.** W54 code and migrations. No corpus bytes.
- **P3.** W55a code and migration. No corpus bytes.
- **P4.** `W55A-STAND-IMPORT-01`:
  - an owner-run, read-only stand capacity probe;
  - the one-off copy (K-1), pulled here and test-restored on a disposable stand here;
  - transfer;
  - import (the importer refuses without an attested copy record);
  - a stand-side report of counts and digests, reconciled against the bundle manifest;
  - an administrator sets the current snapshot.
  - Failure leaves the snapshot inactive. The recovery path is the one-off copy for the database;
    corpus objects stay unbound.
  - The executor is this host's integrator, working only through forced-command verbs on keys the
    owner installs. There is no interactive stand shell.
- **P5.** W57a's retrieval-set build on the stand follows the same pattern, after a pre-push
  check of the stand's content key.

**CD-4 Retrieval set.** It is published through R-76 custody bindings with a `norm_retrieval_set`
binding role added by W57a's migration. W54 keeps binding roles extensible.

**CD-5 v3 categories (K-2).**

- v3 = v2's seven + five normative categories: evacuation, fire safety, accessibility, thermal
  protection and sound insulation. Insolation moves after beta.
- *Amended after the judging round (W57 design M4).* Fire safety maps to every fire-safety clause
  the corpus holds, as K-2 says. That includes Федеральный закон N 123-ФЗ, СП 54.13330.2022 §6.2,
  СП 118.13330.2022's fire-safety sections, СП 1.13130 and the relevant parts of СП 3 and
  СП 7.13130. Clauses that defer to the absent СП 2.13130 or СП 4.13130 are excluded and listed.
  The earlier "only СП 1/3/7" list was too narrow and is withdrawn.

**CD-6 Re-audit (R-82).**

- A re-audit uses the current profile, bundle and mode, the current snapshot and the current
  retrieval set.
- It is refused with a typed error when any of them is unavailable.
- It records what it used.

**CD-7 Reads (R-80).**

- Norms reads require `expert` or `administrator`.
- Setting the current snapshot is administrator-only.

**CD-8 Backup (K-1, R-77).**

- The one-off copy replaces the layer's "accepted W53 backup".
- The full backup system stays in the beta wave.

**CD-9 Releases.**

- Version numbers are targets under the layer's §8.4.
- Nothing is invented while `W53-RELNOTES-STOP-01` awaits the owner.

**CD-10 Checks.** Each lane states its own level under R-70 and R-84: light acceptance by default;
the full gate for contract, migration and infra lanes and before `main`.

**CD-11 Embeddings.**

- EMBED owns a resumable `build`.
- The BGE image is rebuilt after EMBED.
- The build must finish before P4, in night windows.

**CD-12 Disk.**

- Freezes sum the disk peaks here and on the stand.
- Disk gets a stop rule, as memory already has.

**CD-13 W57 output cap.** The v3 output cap is chosen so that cap ÷ the measured rate stays under
170 s.

**CD-14 W57 spend.** The reserve question goes to the owner at `W57A-RULE-01`.

## 4. Judging round, 2026-10-12, and integrator decisions

Seven fresh-context judges read the plans at `33fe3f7`: design and grants for each plan, plus one
for cross-plan consistency. The verdicts and the dispositions are recorded in
`reviews/W54-W57-CHAIN-JUDGING.md`.

**State after the round.** W53 was released while the round ran:

- `origin/main` = `2653dbf`, tagged `v0.4.0`; `origin/dev` = `4fe7615`.
- The stand's migration head is `0017`, and MinIO was recreated under R-83.
- No client-object read-back was done.
- The owner waived the one-off copy for that publication only (K-12).
- R-85…R-87 are recorded; the next free ruling number is R-88.

These are the integrator's technical decisions for the fix round. The owner may override them.

**CD-15 Base.** The base moves to `origin/dev` `4fe7615`.

- P1 is done: the MinIO swap rode W53's publication. Its client-object read-back moves to P2,
  through W54's `verify-objects`.
- R-86 supersedes K-9's wording: 0.4.0 is released, and the 0.3.0 entry is kept as its own
  history row.
- Every provisional ruling label starts at R-88.

**CD-16 The exact stand sequence.** Every plan cites W54 §3.5's verbs instead of paraphrasing them.

- **A migrating publication (P2, P3, W55b, W56a, W57a, W57b):**
  1. The exact-SHA gate.
  2. Inside an agreed window (K-5): `dump-db` → `inventory-s3` → `fetch` → test restore here →
     `attest`.
  3. Push.
  4. Workflow and `verify-deployed.sh`.
  5. `resume`.

  On failure the order is: forward fix, or a policy-conformant revert (`MAIN_AUTODEPLOY_POLICY.md`),
  or the owner-ordered `restore-db <STAMP> <sha256>`; then `resume`.
- **P4:**
  1. `capacity`.
  2. `receive` and `status`, before the quiesce, to keep the window short.
  3. `dump-db` → `inventory-s3` → `fetch` → test restore here → `attest`.
  4. `import`.
  5. `report`.
  6. `resume`.
  7. Administrator designation.
  8. `verify-objects` and the live checks.

  The failure branches are `resume`, or `restore-db` then `resume`. A hung importer holding its
  lock is an owner act, and it is rehearsed.

**CD-17 Profile switch.** The analysis profile (v2 in W56a, v3 in W57a, and rollback) is switched
by an owner act: the host-owned `provider.env` entry, followed by an api restart. No new verb is
built. W56a's and W57a's INT-MAIN name the act, its check through `getProductVersion` or the run
status, and its rollback.

**CD-18 The W57 pre-push check and the build target.**

- P5a reads `listNormSnapshots` (W55a; admin) through an administrator account the owner names.
  No new verb reads the current key.
- The build takes an explicit `ns_` id, which must equal the map's reviewed snapshot and be
  qualified; it need not be current.
- Activation requires a *verified* set row. A row that failed verification never pins.

**CD-19 Shared refusals and interfaces.**

- A v3 start without a usable snapshot or set is refused with the existing
  `required_norm_unavailable`, not a new `no_current_norms_snapshot`.
- W54's custody binding target is generic: `publish_bindings(role, target)`. W57a adds two roles
  (`norm_retrieval_set`, `norm_catalogue`) and holds `norms/custody/roles.py` and the
  `NORM_CORPUS_CUSTODY.md` roles section.
- W54's `report` prints:
  - the counts, row digest and build digest;
  - the client-table counts and Blob totals;
  - the unreliable-paragraph count and the binding digest.

**CD-20 Size.** Revision tables, repeated release paragraphs and paraphrased verbs are cut, using
the judges' cut lists. Each plan's history lives in this judging record, not in the plan.

**CD-21 Disk.** This host has 15 GiB free. The W54 and W55 rehearsal peak (≈19–24 GiB with margin)
does not fit, so the plans state one temporary-peak formula per filesystem. Provisioning is an
owner question, asked after this round.
