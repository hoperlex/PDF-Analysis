# AR-V3-ACTIVATION-FEASIBILITY-01 — what of the AR v3 beta activation can be done on this host

**Task:** [AR-V3-ACTIVATION-FEASIBILITY-01](tasks/AR-V3-ACTIVATION-FEASIBILITY-01.md). **Lane:** AR-F of wave PW5 (`dispatch/PRODUCTION-WAVE-PW5.md` section 3). **Base:** `9e42c18a`. **Measured:** 2026-10-27 on the development host (8 vCPU, 11.6 GiB RAM, one 119 GiB filesystem). **Authority read:** `R-146ba` (the activation decisions are the integrator's, no subject-matter expert takes part, accepted risks `A-10` and `A-11`) and `R-146bb` (the integrator may fetch the BGE-M3 weights of the pinned revision with a hash check, compute the query vectors with recorded provenance, remove the weights; free disk stays above 1.2 GiB).

This is a read-only report. Nothing was downloaded except HTTP `HEAD` answers and three metadata listings (the Hugging Face file headers, the PyPI JSON metadata of the 33 locked packages, the PyTorch CPU wheel index page, 414 KB, in `/tmp/ar-f/`); no docker command beyond listings (`docker ps -a`, `docker volume ls`, `docker system df`, `docker images`, `docker inspect` of ports); no database was opened; `git fetch` refreshed the remote-tracking refs only. Every number below carries the command that produced it; a number I could not measure says so.

## 1. Verdict per step of the activation runbook

Steps are those of `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`. DONE-HERE = already exists on this host. POSSIBLE-HERE = the integrator can do it on this host now or after the named precondition. NEEDS-OWNER-HOST = only a person with a shell or a token on the live host can do it. IMPOSSIBLE-HERE = cannot be done on this host under the current disk/network.

| # | Step | Verdict | Why, in one line |
| --- | --- | --- | --- |
| 1a | qualified snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` in a database, 674 PDF bindings | DONE-HERE | stopped local lane `auditmanager-ar-beta-custody` (volumes 1.9 GB + 5.2 GB), qualified 2026-10-23 |
| 1b | import into the integrator's lane stack `auditmanager-ar-close` | IMPOSSIBLE-HERE | needs +7.1 to +7.6 GB; free is 3.32 GiB. Not needed: the custody lane already holds the data (use it) |
| 1c | the snapshot imported and designated current on the live stand | NEEDS-OWNER-HOST | the repository says «not run»; local logs of 2026-10-21 say «full match»; contradiction, section 2.4 |
| 2 | decisions C01-C22 (include / revise / exclude, branch, edition label, query texts) | POSSIBLE-HERE | every field the tool reads can be proposed from the repository; the legal currency of the editions cannot be checked (accepted `A-11`) |
| 3 | official D1-D5, C15, D6 pages | partly POSSIBLE-HERE, mostly IMPOSSIBLE-HERE | 3 evidence PDFs (2.9 MB) answer `HEAD` 200; the amendment bodies, the base СП 50 and СП 51, the C15 correction and the 123-ФЗ acts are not anonymously fetchable. **Not blocking**: evidence is optional in the tool |
| 4 | BGE-M3 query vectors | POSSIBLE-HERE after the integrator frees at least 1.3 GB (IMPOSSIBLE-HERE today under the 1.2 GiB floor) | hash-checked virtualenv + 2.29 GB weights; peak 3.1 to 3.6 GB; bitwise equality with the image is testable, not provable by reading |
| 5 | `map_pack build` and `validate`, six maps | POSSIBLE-HERE | needs 2 and 4 plus a paragraph export from the custody lane DB |
| 6 | `promote_cli` six sets | POSSIBLE-HERE on the custody lane (rehearsal); NEEDS-OWNER-HOST on the live database | the pack names sets that must exist in the database the server reads |
| 7 | `v3_pack_cli seal` and `verify` | `verify` DONE-HERE-capable (offline); `seal` POSSIBLE-HERE against the custody lane, NEEDS-OWNER-HOST against the live database | `seal` asks a database which verified set each identity selects |
| 8 | install: file, `alpha.env`, restart `api` and `worker` | NEEDS-OWNER-HOST | the live host |
| 9 | `AR-V3-BETA-ACCEPT-01` (recorded cases, one controlled live call, gate) | NEEDS-OWNER-HOST for the live parts; recorded cases POSSIBLE-HERE | `R-146bb`: the owner sets the proxy variables |

## 2. Stand state (question 1)

### 2.1 Where the snapshot and its 674 documents live on this host

```text
$ ls -la /root/projects/PDF-Analysis/.local/norms | cut -c1-70      # trimmed
drwxr-xr-x   builds        bundles        corpus (676 entries)    corpus-sums
drwxr-xr-x   promotion-dumps-keep    promotion-records    repairs
$ du -sh corpus bundles builds promotion-dumps-keep           # hardlinks counted once
5.1G corpus   564M bundles   455M builds   55M promotion-dumps-keep
$ cd bundles/*/ && pwd | sed 's#.*/bundles/##'; sha256sum SHA256SUMS | cut -c1-64; sha256sum manifest.json | cut -c1-64
2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245
7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245      # equals the name's tail
cc0f5ee80ef4b2be43ff41789930ed8e5d14056cdfa6101f97ef582f138f21cf      # equals the runbook's manifest digest
$ stat -c '%h %s' objects/71/71d29803dd45a6b3093688fb0c92a0a97f2535fecc337c65fd3bbc0c5e80255f.pdf
2 145486        # two links: the bundle's objects are hardlinks of the corpus drop, no second copy on disk
$ python3 -c "...manifest.json counts..."
documents 674  paragraphs 350194  chunks 55855  windows 61573  objects 28920  object_bytes 5055102708
db_growth_bytes 1352054572 (the manifest's own estimate)   min_migration_head 0018_norm_custody
```

So the **verified bundle** (the recovery copy) is `.local/norms/bundles/<KEY>/` (manifest 12.4 MB, `rows/` 200 MB, `build/` 345 MB, `objects/` hardlinks), the **raw drop** is `.local/norms/corpus/`, and the **image-computed window vectors** of the build are `.local/norms/builds/<KEY>/vectors/` (438 batch files, 346 MB; used as a bitwise reference in section 5).

### 2.2 Which database holds it, and is anything running

```text
$ docker ps -a --format '{{.Names}}  {{.Status}}' | grep -E 'ar-close|ar-beta-custody|promotion'
auditmanager-ar-close-postgres-1       Up 34 minutes (healthy)   127.0.0.1:58640->5432/tcp
auditmanager-ar-close-s3-1             Up 34 minutes (healthy)   127.0.0.1:62140->9000/tcp
auditmanager-ar-beta-custody-postgres-1  Exited (0) 35 hours ago          # port 58490 (docker inspect)
auditmanager-ar-beta-custody-s3-1        Exited (255) 3 days ago
auditmanager-promotion-postgres-1        Exited (255) 3 days ago
$ du -sh /var/snap/docker/common/var-lib-docker/volumes/<volume>
1.9G auditmanager-ar-beta-custody-postgres-data    5.2G auditmanager-ar-beta-custody-s3-data
2.6G auditmanager-promotion-data                   139M auditmanager-ar-close-postgres-data   409M auditmanager-ar-close-s3-data
```

- **No running database holds the snapshot.** The two stopped lanes do: the **custody lane** (qualified: all 674 source PDFs bound, 28,920 confirmed admissions, `AR-BETA-LOCAL-CUSTODY-01`) and the original **promotion database** (snapshot and embeddings, but zero custody rows, so `promote_cli plan` cannot run on it). Its compose directory is `.local/worktrees/codex-ar-normative/infra/local` and its `.env` (not read here) is in that worktree.
- The custody lane is at migration `0031`; the tree is at `0035` (`0036` follows from lane AR-A). `promote_cli` and `v3_pack_cli` read the norm tables; migrations `0032` to `0035` do not alter them (`grep -c norm_` over the four files: `0032` mentions `norm_retrieval_set` as a reference, `0033` `norm_verification` once, `0034` and `0035` none). Only the importer checks the head (`norms/bundle/stand.py:292`). The lane can therefore serve the tools as it is; `make migrate` on that lane's own `.env` is the conservative alternative and writes only to a lane database.
- The lane stack `auditmanager-ar-close` is PostgreSQL 17.11 with **pgvector 0.8.6** (`docker images`: `auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9`), so it could hold the import functionally.

### 2.3 What an import into the lane stack would need and weigh

From the manifest above and the two measured imports (`STAND-NORMS-IMPORT-RUNBOOK-01.md` section 7; `AR-BETA-LOCAL-CUSTODY-01.md`):

| Quantity | Value | Source |
| --- | --- | --- |
| rows | 674 documents, 350,194 paragraphs, 55,855 chunks, 61,573 embedding windows (1024 float32 each), 28,920 custody slots/bindings | bundle `manifest.json` |
| object bytes into MinIO | 5,055,102,708 | bundle `manifest.json` |
| disk after import | +7.1 GB measured on the custody lane (PostgreSQL 1.9 GB, MinIO 5.2 GB); +7.57 GB measured on the 2026-10-20 rehearsal (PostgreSQL 2.50 GB of which WAL 1.06 GB, MinIO 5.07 GB) | `du` above; runbook section 7 |
| time | import 27 to 34 minutes, report 49 to 54 s | runbook section 7; custody report |
| memory | importer 0.79 GiB, PostgreSQL 538 MiB, MinIO 1.13 GiB | runbook section 7 |
| free disk now | 3.32 GiB (`df -B1 /`: 3,566,612,480 bytes available, 98 %) | below |

```text
$ df -B1 / | tail -1 ; free -m | head -2
/dev/vda3 126828056576 116807974912 3566612480  98% /
Mem: 11857  6554  412  101  5304  5303      # total used free shared buff/cache available (MiB)
$ docker system df
Images 20 5.47GB (583MB reclaimable)   Local Volumes 52 15.77GB (4.572GB reclaimable)   Build Cache 0B
```

Free disk fell from 3,670,753,280 bytes at the start of the lane to 3,566,612,480 and then 3,544,772,608 (other sessions write about 20 MB every ten minutes), so every figure of free space in this report is «about 3.3 GiB». The import needs more than twice the free disk and would end below the 1.2 GiB floor of `R-146bb`: **IMPOSSIBLE-HERE** as a copy. It is also pointless: the custody lane holds the same bytes. The cheap path is `docker start auditmanager-ar-beta-custody-postgres-1` for the paragraph export (PostgreSQL only) and the S3 container as well for `promote`/`seal`.

### 2.4 The live stand: a contradiction the integrator must settle at the stand

```text
$ cat .local/stand-import/last-status.txt | tail -6      # file dated 2026-10-21 15:09
bundle: 2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e3...  bytes: 5641048705  import: exited 0
  | custody_objects_checked: 28920   | custody_incidents: 0 match   | report: full match
$ grep -n -i "have not run" docs/program/CURRENT_STATE.md      # line 45-46
The stand import, its copy record and the admin's designation of a current snapshot have not run; they need an owner window.
```

The local logs (`.local/stand-import/{attest,import-start,report,resume}.log`, containers named `auditmanager-prod-*`, staging `/srv/auditmanager-bundles` with 37.5 GB free, which is not this host: `ls /srv` here is empty) record an import exiting 0 with `report: full match` and a `resumed` on 2026-10-21. `CURRENT_STATE.md`, `BETA-MATRIX-02.md` (B2) and the 2026-10-22 integrator handoff say the import has not run («blocked on stand keys»). **I cannot tell which is true from this host.** What decides it, read-only: on the stand `inbound status` and `copy status` (forced-command keys) and an administrator `GET /api/v1/norms/snapshots` (`build_state complete`, `qualified true`, `current` true/false). The designation (`PUT /norms/snapshots/current`) is a separate administrator act (runbook section 5); without it new runs pin no snapshot and a pack whose snapshot differs from the run's is refused.

### 2.5 `scripts/norms/export_paragraph_rows.py` prerequisites

Docstring of the script (read): a `DATABASE_URL` naming a database that holds the snapshot with the custody tables (only the custody lane qualifies), the repository virtualenv (`/root/projects/PDF-Analysis/.venv`, Python 3.12.3, SQLAlchemy 2.0.52 and psycopg 3.3.5 import), `PYTHONPATH=src`, a spans file (a JSON list of `{norm_document_id, ordinal_first, ordinal_last}`: the **20 distinct triples** of `docs/program/ar-v3-beta/spans.proposal.json`), `--snapshot ns_...`, and `--out` outside the repository tree or under the ignored `.local/` (it writes corpus text with `O_EXCL`, mode 0600). It runs in one `REPEATABLE READ READ ONLY` transaction checked before the first query and refuses gaps, unreliable rows and an existing output. `AR-V3-BETA-SPANS-MEASURE-01` ran it on the custody lane (88 rows, file SHA-256 `ca560dc93a074dae5328d8b50591743e52c9e893bdf4ad004fe8667bb0fd99dc`); the rows file did not survive (`ls .local/ar-v3-draft` does not exist), so the export is re-run, about one minute, +79 KB.

## 3. The decisions input (question 2)

### 3.1 The exact fields (the `map_pack` decision schema, `ar-beta-map-decisions-v1`)

Read from `src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.py` (constants `_DECISION_KEYS`, `_IDENTITY_KEYS`, `_TARGET_KEYS`, `_BRANCH_KEYS`, `_EVIDENCE_KEYS`, `_REVIEW_KEYS`) and `tests/fixtures/ar_v3_map_pack/synthetic-decisions.json`:

- File: `decision_version`, `synthetic` (false), `comment`, `identity` {`norms_snapshot_id`, `reviewed_content_key`, `embedding_build`, `scenario`}, `query_vectors` {`profile`, `model_revision`, `sha256_by_scope` {F1 F2 A1 A2 S1 S2}}, `items` (22), optional `review`.
- Every item: `id` (C01..C22, exactly once each), `mode` (`provisional_citation` or `context_only`), `targets` (non-empty list, sorted, unique). Every target: `norm_document_id`, `designation`, `edition`, `kind` (`clause`, `table` or `range`), `ordinal_first`, `ordinal_last`, `norm_paragraph_id_first`, `norm_paragraph_id_last`. All text is NFC, non-blank, at most 2,000 characters.
- A `provisional_citation` item additionally: `branch` {`id` (letters, digits, `_.-`, at most 32), `applicability`} and `edition_evidence` (list, may be **empty**; each entry {`source_id` from the policy list of that item, `pages`, `page_sha256`}; the source must be of kind `official_pdf`, `official_excerpt` or `public_copy`).
- A `context_only` item carries neither `branch` nor `edition_evidence`. The eight items of the beta policy (`C05 C06 C08 C09 C10 C15 C21 C22`, `beta_sources.json`) cannot be upgraded; a decision may only be stricter.
- **There is no «exclude» state.** The tool needs all 22 items and every item needs at least one target (`targets_missing`). The strictest available state is `context_only`, whose target text is still rendered into the prompt part. The owner's «include / revise / exclude» maps to: include = `provisional_citation` on the proposed span; revise = another span (ids from the database; the exporter's `--measure` prints them); exclude = `context_only`, which does **not** remove the text from the model's context. The integrator must record that mapping in the decision file's `comment` or the owner will read «exclude» as «not sent».
- What the decision file does **not** carry, and the set step needs: the 22 **query texts** (`provenance.query_text_sha256` and the vector in each item of `request.json`, `promote_cli`), and the definition of the per-scope vector digest (`sha256_by_scope`: recorded, never read; the tool states no rule for it).

### 3.2 What the integrator can propose from the repository alone

| Field | Proposal and evidence |
| --- | --- |
| `mode` of all 22 | the policy: 14 `provisional_citation`, 8 `context_only` (`beta_sources.json`; `python3 /tmp/ar-f/evidence_map.py`) |
| `identity` | snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff` (`manifest.json`), build `bge-m3-dense-v1:characters-v2:1200`, scenario `new_multi_apartment_residential_F1.3` (policy) |
| `targets`: documents and ordinals | `spans.proposal.json` (D1-D6 `ndoc_` ids and inclusive ordinals); **first/last `npar_` ids** and text digests in `AR-V3-BETA-SPANS-MEASURE-01.md` (two tables); all 22 spans exist, are dense and reliable |
| `kind` | clause for D1/D3/D4/D6 spans; table for C21/C22 (rows of D5 table 2 / table 3); C07 is a one-paragraph fragment of clause 4.2.1 («range») |
| `designation` | reviewed label per document: the family names of the sheet (`AR-NORM-MAP-APPROVAL-PREP-01.md` table «Source identity»: СП 1.13130.2020, СП 54.13330.2022, СП 59.13330.2020, СП 50.13330.2024, СП 51.13330.2011, 123-ФЗ). The reader's derived designation is only a default and is 61 characters for D6; the label is what a citation shows, so a wrong one attributes a citation to another norm (`SET-TOOL` check `request_designations_differ_from_map`) |
| `edition` | an honest local statement, e.g. «редакция локального корпуса (ConsultantPlus), изменения не сверены с официальной редакцией»; the local PDF SHA-256 is already in the policy (`D1_LOCAL ... D6_LOCAL`) |
| `branch` (14 items) | `id` `N`; `applicability` = scenario (new multi-apartment residential building F1.3, new construction) plus the sheet's «approval question» for that item; the project date is not set (the beta runs on synthetic documents, `R-146bb`) and is stated as such. R and P are outside the scenario and are not mapped |
| duplicated spans | keep C13 and C20 as separate items on the spans of C12 and C19 (the tool needs all 22 ids; cost 5,036 and 2,543 characters, all six scopes stay under 22,000: 5,728 / 11,958 / 15,032 / 14,143 / 14,078 / 14,078) |
| C22 | choose between 289-300 (14,078) and 301-308 (5,789); `context_only` either way. A judgement, not a legal fact (the sheet only says «direction, use, row and footnotes differ»); the smaller span costs 8,289 fewer characters of context |
| query texts | topic labels per item exist in `AR-NORM-MAP-DISCOVERY-01.md` section 2 (commit `281a5418`, side line `integration/ar-evidence-01`, «original line → scoped topic», numbers removed); the 22 texts are **authored** by the integrator, at most 512 inference tokens each (`embed-texts` refuses longer) |

### 3.3 What needs a legal-source fact

| Items | Fact missing | Where it matters |
| --- | --- | --- |
| C01-C04, C07 (D1) | the pages of changes №2 and №3 to СП 1.13130.2020 and a comparison with the local ordinals | `edition_evidence` and the truth of `edition` |
| C11-C14, C16-C18 (D3) | pages of changes №1-№4 to СП 59.13330.2020; for C15 also the ГОСТ 33652 correction (ИУС 5-2026) | same; C15 is `context_only`, no evidence allowed |
| C19, C20 (D4) | the 74-page base СП 50.13330.2024; the agency excerpt differs by one spelling («позэлементные» against «поэлементные») | same |
| C05, C08, C10 (D6), C09, C06, C21, C22 | the 123-ФЗ amendment chain, СП 54 changes, the table rows | none for the tool: these eight are `context_only` and cannot carry evidence |

The tool accepts an empty `edition_evidence` and lists it as `edition_evidence_missing` in `pack-summary.json`; no refusal follows. A missing legal-source fact therefore never stops the build. It is exactly the content of accepted risk `A-11` («the norms were not checked against the official edition by a human»). What the integrator must not do is write an `edition` or `applicability` sentence that asserts currency: the sentences above say «local corpus edition, not compared».

## 4. Official pages D1-D5, C15, D6 (question 3)

### 4.1 What `ar-official-mirrors-*` built

Nothing executable. `agent/ar-official-mirrors-d1-d3-01` (`2c61f5ac`) and `agent/ar-official-mirrors-d4-d6-01` (`82a118d8`) each changed two Markdown files (`git show --stat`): access audits of 2026-10-22, on the side line `integration/ar-evidence-01`, **not an ancestor of this tree** (`git merge-base --is-ancestor` is false for both). Their result: 0 of 8 amendment bodies (D1 №2-№3, D2 №1-№2, D3 №1-№4) obtained; for D4-D6 only metadata cards, an agency excerpt for D4 §5.1, and editorial copies of 123-ФЗ. The sibling audits `AR-C15-PUBLIC-SOURCE-01` (`e711cb0a`), `AR-LIFT-CORRECTION-01` (`70f7f0d5`) and the edition audits (`7bda60da`, `f1e7e8ed`) say the same for C15. No downloader, no hash recorder and no custody of fetched bytes exist.

### 4.2 HEAD results on this host, 2026-10-27

```text
$ curl -sI -m 20 <url> | grep -iE '^(HTTP|content-length|content-type)'     # evidence-capable sources of the policy
D1_MCHS_1  78.mchs.gov.ru/uploads/resource/2023-12-27/izmeneniya-1-k-svodu-pravil-sp-1-13130-2020-...pdf   200 application/pdf 1127404
D3_FAU_BASE  api.faufcc.ru/api/assets/032a3244-a958-4637-b396-dd141886e4ff                                    200 application/pdf  674288
D4_FAU_EXCERPT  api.faufcc.ru/api/assets/84a94ceb-75b9-4579-8c41-5929600b4e79                                 200 application/pdf 1089281
D1_PUBLIC_2, D1_PUBLIC_3  nav.tn.ru/cloud/iblock/.../SP-1.13130.2020-_Izmenenie-_2_.pdf and ..._-3_.pdf      403 text/html 1294 (with and without a browser user agent)
D3_PUBLIC_CONSOLIDATED  nav.tn.ru/documents/regulatory/ast_s_sp_59_13330_2020/                                403 text/html 1294
$ for u in <15 Rosstandart cards>; do curl -sI -m 15 https://protect.gost.ru/$u | head -1; done
200 OK for all 15: D1 №2, №3; D2 №1, №2; D3 №1-№4; D4 base; D5 base, №1-№4; the C15 correction (HTML cards, metadata only)
$ curl -sI -m 20 https://mchs.gov.ru/uploads/document/2026-08-27/443f0b240ae3ef4009019f2a0434e782.docx
200 ...wordprocessingml.document 173183     # D6 editorial copy, last-modified 2026-08-27; the audit of 2026-10-22 saw 169.1 kB
$ curl -sI -m 12 https://minstroyrf.gov.ru/ ; https://publication.pravo.gov.ru/        -> no answer (curl exit 28), twice
$ curl -sI http://publication.pravo.gov.ru/document/0001202507310080                  -> 405 (HEAD refused on port 80; port 443 times out)
```

- **Fetchable by a plain HTTPS download and hashable:** the three PDFs above, 2,890,973 bytes in total. They are comparators, not final editions: `D1_MCHS_1` is change №1 only, `D3_FAU_BASE` is the original base (file dated 2023-09-15; its §6.2.14 differs from the local consolidated text), `D4_FAU_EXCERPT` is a 45-page excerpt. Under the policy they cover **6 of the 14** provisional items (`C01 C02 C03 C11 C19 C20`); the other eight (`C04 C07 C12 C13 C14 C16 C17 C18`) list only `nav.tn.ru` copies, which answer 403 from this host (`python3 /tmp/ar-f/evidence_map.py`, source in Appendix A).
- **Not fetchable here:** amendment bodies on `protect.gost.ru` (the cards answer 200; the page viewer serves an authorization image, SHA-256 `e3a0159f7880cfaaa86820693af818b40db4b4230b641e1585cdfd26449e7057`, per the audits; not re-probed because that needs `GET`), Minstroy (connection timeout), `publication.pravo.gov.ru` (TLS times out; the originals of №304-ФЗ and №330-ФЗ, ids `0001202507310080` and `0001202608040075`), the C15 correction page (viewer denial), the СП 50 and СП 51 base documents (no public byte URL). A card's HTML is `official_metadata`, a kind the tool refuses as evidence.
- **Hash policy proposed:** record per fetched file the URL, retrieval time (UTC), `content-length`, the SHA-256 of the whole file, and the page range of the local comparator; use the whole-file SHA-256 as `page_sha256` and the range as `pages` (the tool records both and verifies neither). A whole-file digest is reproducible by anyone; a per-page extraction digest would need a second tool nobody wrote.
- **Where the hash is recorded:** today nowhere. `beta_sources.json` holds a SHA-256 only for the six `*_LOCAL` sources; the official and public entries have a URL and no digest. The place is the item's `edition_evidence` entry in the decision file (it goes into the map bytes and so into `map_sha256`), plus a plain record file under `docs/program/ar-v3-beta/` (lane AR-B owns that directory) with URL, time, size and digest.
- **Needed at all?** No for the build. Evidence is optional; the eight context-only items cannot carry it; D2, D5, D6 and C15 appear only in context-only items. Step 3 only decorates 6 of the 14 provisional items with comparator digests.

## 5. The query vectors (question 4)

### 5.1 The frozen profile and the image

`infra/norms-worker/Dockerfile` pins the base by digest, installs the lock with `pip install --require-hashes --no-deps --only-binary=:all:`, fetches the 11 files of revision `5617a9f61b028005a4858fdac845db406aefb181` by literal URLs with `ADD --checksum=sha256:...`, sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `TOKENIZERS_PARALLELISM=false`, `OMP_NUM_THREADS=8`, `MKL_NUM_THREADS=8`, `AUDITMANAGER_EMBEDDING_PROFILE=bge-m3-dense-v1`, and bakes `src/auditmanager/norms` in. `FOUNDATION_LOCK.json` `images.norms_worker` records `pending_pins: []`, the image built and verified 2026-10-13 (MRR 0.848611, 24 queries, 563 windows, peak RSS 3296 MiB), then pruned. `docker images` shows no norms-worker image now.

### 5.2 The weights: size and hash, from headers only

```text
$ curl -sI https://huggingface.co/BAAI/bge-m3/resolve/5617a9f61b028005a4858fdac845db406aefb181/pytorch_model.bin
HTTP/2 302 ... x-linked-size: 2271145830   x-linked-etag: "b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38"
# the Dockerfile's literal checksum for pytorch_model.bin is b5e0ce34...ad38: equal. Same for sentencepiece.bpe.model (cfc8146a...2865, 5069051 B)
# and tokenizer.json (21106b6d...dd08, 17098108 B). The other eight files are small and git-stored (git blob ids, not SHA-256).
all 11 files, summed x-linked-size / content-length: 2,293,331,623 bytes = 2.136 GiB
```

### 5.3 What a hash-checked virtualenv instead of the image takes

- **Wheels, sizes derived without downloading.** The lock has 33 pinned packages; the lock holds hashes only, so each hash was matched to its file through the PyPI JSON metadata (every one of the 33 matched: `python3 /tmp/ar-f/wheels.py`, source in Appendix A), and the torch wheel through the PyTorch CPU index (`torch-2.7.1+cpu-cp312-cp312-manylinux_2_28_x86_64.whl`, SHA-256 `8f8b3cfc...0947`, **in the lock**, `HEAD` content-length 175,833,687). Sum of the 32 PyPI wheels for CPython 3.12 on x86_64 Linux: 101,376,675 bytes; with torch **277,210,362 bytes (264 MiB)** to download. The installed size of the closure is **not derivable** from the lock or the indexes; my estimate is 1.0 GB (0.8 to 1.3 GB; torch alone about 0.6 GB unpacked). It is an estimate: step 6 of the plan measures it (`du -sb` of the venv right after the install).
- **Recipe, no deviation from the lock:** `python3 -m venv $S/venv`; `$S/venv/bin/pip install --require-hashes --no-deps --only-binary=:all: --no-cache-dir --report $S/pip-report.json -r infra/norms-worker/requirements.lock` (the lock carries `--index-url` and `--extra-index-url` lines itself); fetch the 11 files with `curl` into `$S/hf/hub/models--BAAI--bge-m3/snapshots/5617.../<path>` and `sha256sum -c` against the Dockerfile values; export the image's environment; run `python infra/norms-worker/self_check.py` (checks the file set, the five versions, a probe vector `(1,1024)`, norm 1), then `python -m auditmanager.norms.embedding embed-texts --in req.json --out resp.json` with `PYTHONPATH=src`.
- **Network at run time:** the venv run is offline by the same two variables as the image; only the fetches use the network.
- **Peak disk, three cases of the venv size (arithmetic in the checker output):** order matters. Install first: wheels 0.28 GB plus venv = 1.1 to 1.6 GB; delete the wheel temp; then fetch the weights: venv plus 2.29 GB = **3.1 / 3.3 / 3.6 GB** for 0.8 / 1.0 / 1.3 GB venvs. The floor of `R-146bb` is 1.2 GiB (1,288,490,188 bytes), so the free disk required before the step is **4.4 / 4.6 / 4.9 GB**. Free now is 3.57 GB: **short by 0.8 / 1.0 / 1.3 GB**. Putting the weights in `/dev/shm` (5.8 GB tmpfs) trades disk for RAM: 2.3 GB resident plus a 3.3 GiB model run against 5.3 GiB available now; it would swap and violates the 6 GiB floor of `W54-BGE-IMAGE.md`. Not recommended.
- **Time (estimates; the transfer rate was not measured, a download was forbidden):** wheels 0.28 GB and weights 2.29 GB at 6 / 30 / 100 MB/s take 7 min / 1.4 min / 26 s together; install 1 to 2 min; hash check of the weights 10 to 20 s; model load 20 to 60 s (a pickled `.bin`, not safetensors); 22 short texts: seconds (the recorded passage rate is 3.8 windows/s, `FOUNDATION_LOCK`: 563 windows in 148.666 s); self-check 1 min. Peak RSS 3.3 GiB. Whole step: 10 to 25 minutes once the disk is free.
- **After use, delete exactly:** `$S/hf` (2,293,331,623 bytes; the `R-146bb` removal), `$S/venv` (about 1.0 GB), any wheel directory, the differential-check checkpoint (< 2 MB). Keep: `req.json`, `resp.json`, `pip-report.json`, `provenance.json` (a few hundred KB) under the ignored `.local/ar-v3-draft/`. Prove the removal with `df -B1 /` returning to within 50 MB of the value before the step, and `ls $S` empty.

### 5.4 Would the venv reproduce the image's vectors bitwise?

By reading: **likely, not provable.** Identical: every wheel byte (the lock hashes), every model byte (the checksums), the CPU, if the 14-hour build ran on this machine (the location of `builds/` suggests it, no record states the CPU of that run; this host is `AMD EPYC 9655`, 8 vCPU), the thread settings (8), the repository code path (`norms/embedding`, same source). Different: Python 3.12.3 on glibc 2.39 against 3.12.x on glibc 2.36 (the bake-off itself ran on 3.12.3 and 2.39, `W54-BGE-IMAGE.md` section 4), the system `libm`/`libstdc++`, and pip's wheel choice if two tags qualify (the report file lists the chosen URL and hash of every wheel, so this is checkable). The way to turn «likely» into evidence is a differential run, no database needed: copy `plan.json` and `inputs/batch-00000.jsonl` (80 KB plus one batch file) from `.local/norms/builds/<KEY>/` into a scratch checkpoint directory, run `python -m auditmanager.norms.embedding build --snapshot ns_01M59N8QNBVN91ACA2HCE6VE74 --chunking-profile characters-v2:1200 --checkpoint $S/ck --max-batches 1` in the venv (273 windows, about 3.6 minutes at the recorded 1.25 windows/s), and compare the produced `vectors/batch-00000.jsonl` and its `.sha256` byte for byte with the stored `.local/norms/builds/<KEY>/vectors/batch-00000.jsonl` (header seen: format `auditmanager-embedding-batch/1`, 256 chunks, 273 windows, model revision `5617a9f6...`). Equal: the venv is the image for this purpose, and `provenance.json` says so with both digests. Different: the venv vectors are not the image's; STOP, and the alternative is to rebuild the image (about 6.5 GB of build space, `W54-BGE-IMAGE.md`), which this disk cannot hold.

## 6. The reviewer attestation (question 5)

**Two records exist and they are not the same.**

1. The map-level `review` block of the decision file (`map_pack`): `reviewer`, `capacity`, `date`, `decision_ref`, `map_sha256` {six digests}. If supplied, `pack-summary.json` says `review_state: attestation_recorded`; if absent, `pending_expert`. Nothing downstream reads it (`grep -rn "attestation_recorded\|pending_expert" src scripts`: only the constants). **Recommendation: leave it out.** The honest state is `pending_expert`: no expert reviewed the maps, and `attestation_recorded` would read as the opposite.
2. The manifest `review` of the sealed pack: exactly `reviewer`, `capacity`, `reviewed_at` (a calendar date `YYYY-MM-DD`), `decision_ref`, `scope_statement`, all non-empty text (`v3_pack_manifest.py` `_REVIEW_KEYS`, `_review`). The server shows these five fields verbatim in «Настройки анализа» with a fixed sentence that the record is attached at installation and is not checked by the system (`AR-V3-BETA-PACK-STATUS-WEB-01.md`).

`v3_pack_cli seal --scopes SCOPES.json --reviewer NAME --capacity TEXT --reviewed-at YYYY-MM-DD --decision-ref REF --scope-statement TEXT --out PATH [--database-url URL] [--force]`. `DATABASE_URL` from the environment is preferred. Refusals (exit 2, `v3-pack REFUSED <token>` on stderr): `out_exists` (without `--force`), `database_url_missing`, `scopes_file_unreadable`, `spec_not_json`, `spec_keys`, `spec_scopes` (not six, not in order `F1 F2 A1 A2 S1 S2`, duplicate map digests), `spec_value` (blank text, a map digest that is not lowercase SHA-256), `scope_unverified` (a scope that does not select exactly one verified retrieval set, or is answered with another identity), `manifest_value` (blank review field, `reviewed_at` not a date), `write_failed`. `verify --manifest PATH` is offline and prints `v3-pack OK pack_sha256=...`; its refusal tokens are `manifest_missing`, `manifest_not_regular_file`, `manifest_unreadable`, `manifest_too_large` (over 64 KiB), `manifest_not_json`, `manifest_keys`, `manifest_format`, `manifest_value`, `scope_count`, `scope_id_duplicate`, `scope_order`, `scope_map_duplicate`, `scope_set_duplicate`, `pack_digest_mismatch`, `pack_refused`.

**What the tool accepts, honestly.** The CLI help gives «expert or owner-delegate» as examples of `capacity`; the loader checks only that the text is non-empty. So the honest record is accepted as is. Proposed values (Russian for the five fields, because the screen shows them to users; the English meaning is the `R-146ba` sentence):

| Field | Value |
| --- | --- |
| `--reviewer` | `ИИ-интегратор (Claude Code), сессия integration/ar-close-1026` |
| `--capacity` | `ИИ-интегратор по поручению владельца (R-146ba); не эксперт предметной области` |
| `--reviewed-at` | the date the decision file is frozen |
| `--decision-ref` | `R-146ba (A-10, A-11); decisions sha256 <digest of the decision file>; map digests <first 12 hex of each of the six>` |
| `--scope-statement` | `Подготовлено ИИ-интегратором по поручению владельца; эксперт предметной области не участвовал; нормы не сверены с официальной редакцией человеком. Охват: шесть областей АР v3 (F1 F2 A1 A2 S1 S2), 22 темы C01-C22, 14 тем как предварительная цитата и 8 только как контекст (C05 C06 C08 C09 C10 C15 C21 C22); числовые выводы недоступны.` |

Meaning in English: prepared by the AI integrator on the owner's instruction; no subject-matter expert took part; the norms were not checked against the official edition by a human. The independent two-person check of `promote_cli` (section 7, step 8) is then also AI-to-AI and the scope statement must not call it expert review. Honest limit (`D-212`): neither `pack_sha256` nor the loader authenticates the record; file custody is the control.

## 7. Install on a host (question 6)

- **Server side (merged):** both composition roots read `AR_V3_BETA_PACK_MANIFEST`; unset or blank is the empty registry, a bad file stops the container with `ConfigurationError`. `infra/deploy/compose.server.yml` passes the variable to `api` and `worker` and mounts `./ar-v3-pack` read-only at `/run/ar-v3`; `infra/deploy/ar-v3-pack/README.md` and `infra/deploy/env/alpha.env.example` describe it; `infra/deploy/ar-v3-pack/.gitignore` keeps the manifest out of git (`git check-ignore -v infra/deploy/ar-v3-pack/pack.json` confirms). `origin/main` (`94d3dc46`, `VERSION` 0.8.2) already has `v3_pack_cli.py`, migration `0033` (without it every Run fails, `D-225`) and the README (`git cat-file -e origin/main:<path>`), so the live code needs no deployment first.
- **What the owner must do on the live host, in order:** (1) confirm the snapshot is imported and designated current (section 2.4); (2) run `promote_cli plan` and `promote` six times against the live database, from a copy of the six bundles (`docker cp` into the `api` container, then `docker compose ... exec -T api python -m auditmanager.norms.retrieval.promote_cli ...`; the bundles hold ids, digests and vectors, no secret and no corpus text), with the same `set_id`s as the rehearsal (`promote` refuses while a foreign custody admission is pending, so run it in a quiet moment; `plan` may run while the stand is live); (3) `seal` against the live database (`DATABASE_URL` from the container); (4) copy `pack.json` to `/srv/auditmanager/infra/deploy/ar-v3-pack/` (readable by uid 10001); (5) set `AR_V3_BETA_PACK_MANIFEST=/run/ar-v3/pack.json` in `alpha.env`; (6) recreate `api` and `worker`; (7) `docker compose exec api python -m auditmanager.runs.v3_pack_cli verify --manifest /run/ar-v3/pack.json` exits 0; `getArV3BetaPackStatus` answers `installed`; the control "Запустить шесть проверок АР v3" appears. Withdrawal: unset the variable in both services and restart.
- **Why the sets cannot only be made here:** the manifest names `set_id` and `set_sha256`, and the server resolves them in its own database through `select_verified_retrieval_set`; the set and catalogue blobs are admitted to that database's object store. A pack sealed against the custody lane names rows the live database does not hold unless the same bundles are promoted there. The set digests are deterministic from map, snapshot rows and windows, so a second `plan` on the live database must end `verdict: matched` against the rehearsal's digests; that is the check that the rehearsal transfers.
- **Forced-command keys do not reach this:** the stand keys run `receive-bundle.sh` and `copy-serve.sh` verbs only; `promote_cli` and `seal` need a shell on the live host (the owner) or a new, reviewed forced-command verb.

## 8. Plan for the integrator

Units: wall-clock minutes of commands on this host unless marked «authoring» (agent time). Disk figures are the peak added by the step. Dependencies by step number.

| # | Who | Step | Disk peak | Time | Needs |
| --- | --- | --- | --- | --- | --- |
| 1 | integrator | **Make room**: free at least 1.3 GB and prefer 2.5 GB (candidates the integrator must judge: merged lane worktrees, 13.4 GB under `.local/worktrees` in 108 directories; docker volumes not referenced by any container, 4.57 GB reclaimable by `docker system df`; read each volume's database names before removal). Record `df -B1 /` before and after | frees | 15-40 | - |
| 2 | integrator | Capture premises again (`docker ps -a`, `df`, `free`, `git status`) and confirm nobody else started the custody lane | 0 | 5 | - |
| 3 | integrator or AR-B | **Authoring**: decision file for C01-C22 (section 3.2) with `synthetic: false`, query vectors placeholder until step 7; the 22 query texts; the six `scopes.json` skeleton; the mapping note for «exclude» | 0 | 1-2 h authoring | - |
| 4 | integrator | `docker start auditmanager-ar-beta-custody-postgres-1`; export paragraph rows (20 spans) with `export_paragraph_rows.py --out .local/ar-v3-draft/paragraphs.json`, compare to the recorded 88 rows and digest `ca560dc9...`; stop the container | +0.08 MB | 5-10 | 2 |
| 5 | integrator | Fetch the three fetchable PDFs, hash, write the source record; optional, skip if short of time (the other nine sources are not fetchable) | +2.9 MB | 10 | 3 |
| 6 | integrator | **Vectors**: venv, weights, `self_check.py`, differential batch check (section 5.4), `embed-texts` for the 22 texts (one request per scope), provenance file, then delete weights and venv | peak 3.1-3.6 GB | 25-45 | 1, 3 (texts) |
| 7 | integrator | Put the six vector digests into the decision file; `map_pack build` (no `review` block) and `validate` with the paragraph file; expect exit 0 and six distinct digests; commit the decision file and `pack-summary.json` (no corpus text) | < 1 MB | 10 | 4, 6 |
| 8 | integrator, then a **second, separate AI lane** | Rehearsal on the custody lane (start postgres and s3): per scope `new-id`, bundle, `plan`; a fresh read-only lane recomputes `sha256sum map.json`, the manifest digests (`snapshot.content_digest`, `build.embedding_set_sha256`) and its own `plan`, writes `expected_*` digests; then `promote`, then the replay (`replayed: true`) | tens of MB | 6 x 10-20, unmeasured (the tool authors say the cost grows with the corpus, 61,573 windows, three prepares per `promote`) | 7 |
| 9 | integrator | `seal` against the custody lane with the section 6 values, `verify` offline; keep `pack.json` under `.local/` (not git) | 0 | 5 | 8 |
| 10 | owner (or an admin token holder) | Live host: confirm and, if needed, import and designate the snapshot; repeat step 8's `promote` with the same bundles; `plan` must end `verdict: matched` | live host | one owner window | 7, 8 |
| 11 | owner | `seal` on the live database, install, restart, `verify`, check the status panel | live host | 30 | 10 |
| 12 | integrator and owner | `AR-V3-BETA-ACCEPT-01`: recorded positive and negative cases (here), controlled live call (the owner sets `PROXY_LLM_*`; ceiling 0.50 USD), the gate in a window | live host | per that task | 11 |

Critical path on this host: 1, 6, 7, 8, 9 (about 3 to 4 hours of commands plus the authoring). Steps 3, 4, 5 run before or beside 1 and need no free disk.

**Cannot be done on this host, and why:**

1. Import of the corpus into the lane stack `auditmanager-ar-close` (+7.1 to +7.6 GB against 3.32 GiB free; unnecessary because the custody lane holds the same snapshot).
2. The vectors step as things stand (peak 3.1 to 3.6 GB needs 4.4 to 4.9 GB free, 3.57 GB is free; the 1.2 GiB floor of `R-146bb` fails by 0.8 to 1.3 GB). It becomes possible after step 1.
3. Building the norms-worker image to compare against (about 6.5 GB of build space).
4. Fetching the amendment bodies of D1 №2-№3, D2 №1-№2, D3 №1-№4, the base СП 50 and СП 51 with their changes, the C15 correction, the 123-ФЗ originals №304-ФЗ and №330-ФЗ: the viewer serves an authorization image, Minstroy and `publication.pravo.gov.ru` do not answer, `nav.tn.ru` answers 403. None is blocking.
5. Anything that needs the live database or the live host: the stand state check and the designation, `promote` and `seal` against the live database, the file install, the restart, the status check, the live provider call.
6. A human or expert review: excluded by `R-146ba`; the honest attestation says so.
7. An independent check by a second person: only a second AI lane is available here; the report must call it that.

## 9. Not verified, and traps found

- The installed size of the locked closure (1.0 GB is an estimate), the download rates, the runtime of `promote_cli plan` on 61,573 windows, and bitwise equality with the image were **not measured**; each has its step.
- The PyPI size pick took the CPython 3.12 x86_64 Linux wheel per hash; pip may choose another tag where two qualify. The pip report in step 6 records the real choice.
- `docker volume`/`du` figures are for the stopped lanes as they are now; another session may start or remove them. The disk changed by 0.1 GB during this lane (3.67 GB at the start, 3.57 GB at the end).
- The contradiction between the 2026-10-21 local import logs and the repository prose (section 2.4) is not resolved here.
- `git fetch` updated the remote-tracking refs of the shared repository; no other repository state was touched.
- The scratch files of this lane are in `/tmp/ar-f/` (the torch index page of 414 KB, the wheel list, the two small scripts); they are not part of the deliverable.

## 10. Checker

`python3 /tmp/ar-f/check_refs.py` (scratch, not kept) extracts every inline-quoted file path, branch, commit, debt id, ruling id, accepted-risk id and task id cited in this report and its task file and checks it against the tree, the shared repository and `docs/program`; paths that are to be created or live on the owner's host are listed, not checked. Its result line is in the lane's final message.

## Appendix A — the two scripts the numbers come from

Scratch scripts of the lane, kept here because `/tmp` does not survive a restart. Both are read-only; the first makes one metadata request per locked package.

`wheels.py` — match every hash of `infra/norms-worker/requirements.lock` to a PyPI file and sum the CPython 3.12 x86_64 Linux wheel per package (torch comes from the PyTorch index, section 5.3):

```python
import json, re, sys, urllib.request, html
LOCK = "/root/projects/PDF-Analysis/.local/worktrees/ar-v3-activation-feasibility-01/infra/norms-worker/requirements.lock"
text = open(LOCK, encoding="utf-8").read()
pk = {}
cur = None
for line in text.splitlines():
    m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s\\]+)", line)
    if m:
        cur = (m.group(1), m.group(2)); pk[cur] = set(); continue
    h = re.search(r"--hash=sha256:([0-9a-f]{64})", line)
    if h and cur: pk[cur].add(h.group(1))
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ar-f-feasibility/1 (metadata read)"})
    return urllib.request.urlopen(req, timeout=30).read()
out = []
for (name, ver), hashes in pk.items():
    if name == "torch":
        out.append((name, ver, len(hashes), None, None, "see pytorch index")); continue
    try:
        d = json.loads(get(f"https://pypi.org/pypi/{name}/{ver}/json"))
    except Exception as e:
        out.append((name, ver, len(hashes), None, None, "ERR " + repr(e)[:60])); continue
    files = [f for f in d["urls"] if f["digests"]["sha256"] in hashes]
    # choose the file installable on CPython 3.12 linux x86_64 manylinux (glibc <= 2.39)
    def ok(f):
        n = f["filename"]
        if not n.endswith(".whl"): return False
        if "-none-any" in n: return True
        if "cp312" in n or "abi3" in n or "cp37-abi3" in n or "cp38-abi3" in n or "cp39-abi3" in n:
            return ("x86_64" in n) and ("manylinux" in n)
        return False
    cand = [f for f in files if ok(f)]
    cand.sort(key=lambda f: f["size"])
    pick = cand[0] if cand else None
    out.append((name, ver, len(hashes), pick["filename"] if pick else None, pick["size"] if pick else None, f"{len(files)} of {len(hashes)} hashes matched on PyPI"))
json.dump(out, open("/tmp/ar-f/wheels.json", "w"), indent=1)
tot = 0
for r in out:
    print(r)
    if r[4]: tot += r[4]
print("sum bytes (excluding torch):", tot)
```

`evidence_map.py` — which provisional items have an evidence-capable source that answered `HEAD` 200 (the `HEAD` table is the one of section 4.2):

```python
import json
P="/root/projects/PDF-Analysis/.local/worktrees/ar-v3-activation-feasibility-01/"
pol=json.load(open(P+"src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json",encoding="utf-8"))
sp=json.load(open(P+"docs/program/ar-v3-beta/spans.proposal.json",encoding="utf-8"))
EVID={"official_pdf","official_excerpt","public_copy"}
# HEAD results observed 2026-10-27 on this host (see report section 3)
HEAD={"D1_MCHS_1":"200 1127404","D1_PUBLIC_2":"403","D1_PUBLIC_3":"403","D3_FAU_BASE":"200 674288",
      "D3_PUBLIC_CONSOLIDATED":"403","D4_FAU_EXCERPT":"200 1089281"}
alias={v:k for k,v in sp["documents"].items()}
span={}
for it in sp["items"]:
    span[it["id"]]=[(alias[c["norm_document_id"]],c["ordinal_first"],c["ordinal_last"]) for c in it["candidates"]]
tot=0;withf=[];without=[]
for it in pol["items"]:
    cid=it["id"]; src=it["sources"]
    ev=[s for s in src if pol["sources"][s]["kind"] in EVID]
    fe=[s for s in ev if HEAD.get(s,"").startswith("200")]
    sps=";".join(f"{d}:{a}-{b}" for d,a,b in span[cid])
    print(cid, it["mode"][:4], sps, "evidence-kind:",ev or "-", "fetchable:",fe or "-")
    if it["mode"]=="provisional_citation":
        tot+=1
        (withf if fe else without).append(cid)
print("provisional",tot,"with>=1 fetchable evidence source",len(withf),withf)
print("without",len(without),without)
print("context_only",[i["id"] for i in pol["items"] if i["mode"]=="context_only"])
```
