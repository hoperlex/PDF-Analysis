# AR-V3-PROMOTE-01 — independent second check, six promotions and the sealed pack

**Task:** [AR-V3-PROMOTE-01](tasks/AR-V3-PROMOTE-01.md). **Lane:** AR-B3 (part 3 of wave PW5). **Base:** `6fcbec57` (`integration/ar-close-1026`). **Run:** 2026-10-27 UTC. **Authority read:** `R-146ba` and `R-146bb` (the AR v3 activation is prepared by the AI integrator under the owner's delegation; no subject-matter expert takes part), accepted risks `A-10` and `A-11` (`PRODUCTION-READINESS-PLAN-01.md`).

**Honest state.** This is a second, separate AI check. It is not an expert review. No subject-matter expert took part, no human compared any norm with its official edition, and nothing here says that an edition is current or that a branch applies to a real project. The lane recomputed the inputs of the promotion (map bytes, proof digests, query vectors, query texts, target spans, designations) from sources other than the first lane's outputs, then ran its own `promote_cli plan`. The set and catalogue digests are computed by the same tool over the same lane database as in [AR-V3-PROMOTE-REHEARSAL-01](AR-V3-PROMOTE-REHEARSAL-01.md); what is independent is the invocation, the bundle copy and every input the reviewer is supposed to check, not the tool. The sealed `pack.json` carries a review record that says exactly this.

## 1. Result

Every comparison was equal; nothing differed. Then the six sets were promoted on the stopped custody lane, replayed, and sealed.

| Scope | Set id | Own `plan` (wall) | `plan` with expectations | `promote` (wall) | Replay (wall) |
| --- | --- | --- | --- | --- | --- |
| F1 | `nrs_01M5YF1W4BG5260JTSCAZP3F58` | exit 0 (2.0 s) | `matched`, exit 0 (1.6 s) | verified, `replayed: false`, exit 0 (3.9 s) | `replayed: true`, exit 0 (3.8 s) |
| F2 | `nrs_01M5YF1WVZYFD50K47BDYZM59D` | exit 0 (2.0 s) | `matched`, exit 0 (2.0 s) | verified, `replayed: false`, exit 0 (4.8 s) | `replayed: true`, exit 0 (4.7 s) |
| A1 | `nrs_01M5YF1XMMCHT6F6K6HWZEJG4H` | exit 0 (1.6 s) | `matched`, exit 0 (1.5 s) | verified, `replayed: false`, exit 0 (3.8 s) | `replayed: true`, exit 0 (3.6 s) |
| A2 | `nrs_01M5YF1Y8EBK2CBW9JGFADFK31` | exit 0 (1.8 s) | `matched`, exit 0 (1.7 s) | verified, `replayed: false`, exit 0 (4.1 s) | `replayed: true`, exit 0 (4.0 s) |
| S1 | `nrs_01M5YF1YXN8WZTV8TFKZ0EWVTZ` | exit 0 (1.6 s) | `matched`, exit 0 (1.6 s) | verified, `replayed: false`, exit 0 (3.6 s) | `replayed: true`, exit 0 (3.5 s) |
| S2 | `nrs_01M5YF1ZFPGBN4PMERTPN6GA27` | exit 0 (1.6 s) | `matched`, exit 0 (1.7 s) | verified, `replayed: false`, exit 0 (3.6 s) | `replayed: true`, exit 0 (3.6 s) |

- `seal` exit 0 in 1.3 s: `v3-pack SEALED pack_sha256=5d87c1ef52b09aaaab73325c0504c401b29a5af23a16162165ef5954de59251d`.
- `verify --manifest` (offline, `DATABASE_URL` unset) exit 0: `v3-pack OK pack_sha256=5d87c1ef52b09aaaab73325c0504c401b29a5af23a16162165ef5954de59251d`.
- No command refused. stderr of every run is empty (0 bytes in total).

## 2. Order of work (the independence rule)

1. Before any own result existed, the lane did **not** open `plan-<S>.txt` of the first lane or the digest tables of its report. It read the tool and install reports, the feasibility report (sections 2, 6, 7, 8), the tracked `ar-v3-beta/*.json`, the bundles' `map.json` and `request.json`, the vector request/response files, `paragraphs.json`, and the first lane's `run_plan.sh` (a command line, no digest).
2. It wrote its results to `.local/ar-v3-draft/independent/` (untracked): the check files of sections 3 to 5, six own `plan` outputs on its own copies of the bundles, `own-plan-summary.json`.
3. Only then it compared with `plan-<S>.txt` (section 5).

## 3. Checks (a) to (d): inputs recomputed from the verified bundle and the tracked records

A script written in the lane's scratch directory made **463 checks** (66 F1, 126 F2, 81 A1, 111 A2, 36 S1, 36 S2, 7 on the bundle itself). All 463 are `EQUAL`. The result file is `independent/checks-b-c-d.txt`; it holds digests, ordinals and truth values, no corpus text.

**(a) Map bytes.** For each scope `sha256sum` of `pack/scope-<S>.map.json` equals `sha256sum` of `bundle-<S>/map.json` (`cmp`: byte-identical) and equals `map_sha256` of `docs/program/ar-v3-beta/scopes.json`:

| Scope | `map_sha256` |
| --- | --- |
| F1 | `6ef3303ad6b336b57daf3256710e9ffdad8fa769e746a78ade9bc254fc6a0246` |
| F2 | `56ee1c26e79cfaebb742bf6bc39c1c09789270047a029f898c566c74e89597f6` |
| A1 | `4b7c2f9d490faf3acfffe3e5805a21b24d55be70cea731253b50d183aa2fcc29` |
| A2 | `5e97bcc69091e8e36d992088e361e06077f25f15f59829914a95e1053b85d0de` |
| S1 | `4502cb676a47d79d485076201a0ce16c5619fcf8c41b5200770820035f092f0e` |
| S2 | `547aea97e556928b4be79ddc389943badf32aed67cbf8f1492642ef3caa03793` |

**(b) The two proof digests from the verified W54 bundle** (`.local/norms/bundles/2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307...5245/`). Every file read was re-hashed against `SHA256SUMS` first: `manifest.json` (`cc0f5ee80ef4b2be43ff41789930ed8e5d14056cdfa6101f97ef582f138f21cf`), `rows/snapshot.json` (`929cacef6cb59c432ec1e7972f92832c83d6598313b96001bd7c5b097b28b124`), `rows/documents.jsonl` and `rows/paragraphs.jsonl`: all equal. The SHA-256 of `SHA256SUMS` equals the tail of the directory name (`7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245`). `rows/snapshot.json` carries the same `content_digest` as the manifest, and the content key ends with its first 12 hex.

| Proof | Value from the bundle | `request.json` field | Result |
| --- | --- | --- | --- |
| `snapshot.content_digest` | `0a1bafe103ff2df5d53108af602b7aa788d0831353228bfc92c9506a411a3b10` | `independently_checked_source_digest` | equal in all six requests |
| `build.embedding_set_sha256` | `e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df` | `independently_checked_embedding_digest` | equal in all six requests |

The request's `snapshot_id`, `reviewed_content_key`, `embedding_build` and `chunking_profile` also equal the manifest and `scopes.json` in all six requests. Not done: recomputing `build.embedding_set_sha256` from the 61,573 window vectors (`.local/norms/builds/`, 346 MB); the value is taken from the hash-chained manifest.

**(c) Query vectors and texts**, all 22 items. For each item the vector was decoded from the raw base64 of `embed-<S>.response.json`, re-encoded with `struct.pack('>1024f')` and hashed:

- the base64 decodes to 4096 bytes; it unpacks to 1024 big-endian float32 values, all finite; the re-encoded bytes equal the decoded bytes; the norm is within 1e-5 of 1 (float64 `fsum`);
- the SHA-256 of the re-encoded bytes equals `provenance.query_vector_sha256` of `request.json` and `vector_sha256` of the response, and the request's `query_vector_base64` equals the re-encoded response vector;
- the SHA-256 of the UTF-8 bytes of the query text (NFC confirmed) equals `query_text_sha256` of `ar-v3-beta/query-texts.json`, `provenance.query_text_sha256` of the request and `input_sha256` of the response, and the embed request text equals the tracked text;
- the item ids of each request equal `scope-definitions.json` and the map, in order; each text's `scope_id` is the scope that uses it.

The per-item vector digests are tracked in `ar-v3-beta/vectors-provenance.json` (`vector_sha256_by_item`); the 22 re-encoded digests equal them, and the six per-scope digests recomputed by the tracked rule (SHA-256 of one line `<item_id> <vector_sha256>` per item) equal `sha256_by_scope` of the provenance file and of `decisions.json`, and the `query_vectors.sha256` of each map (`independent/checks-vector-digests-tracked.txt`, all equal). The vectors were not re-derived from the frozen BGE-M3 image: the venv, the weights and the checkpoint were removed after use (`removed_after_use` in the provenance file; the directories no longer exist), so (c) proves that the request carries exactly the vectors that were produced, hashed, and recorded, not that they are the right embedding of the text.

**(d) Target spans and designations.** For each item the request's targets equal the map's targets and the approved `decisions.json` targets (document, first and last ordinal); the map's non-target fields (mode, branch, edition evidence) equal the decisions. Each mapped document has one designation in the map; the request's `designations` equal it and the decisions; `mapped_document_ids` equal the request designations and the target documents; every request `slug` equals the slug in the verified bundle's `documents.jsonl`; the map's `composition_sha256` equals `scope-definitions.json`. Against the verified bundle's `rows/paragraphs.jsonl`, for each of the 19 distinct spans every ordinal exists, is `reliable`, and the first and last `norm_paragraph_id` equal the map's.

**Reconciliation of 19 / 20 spans and 80 / 88 rows.** The six requests hold 19 distinct spans covering 80 distinct paragraph rows. The earlier export `paragraphs.json` (and the feasibility report) says 20 spans and 88 rows. The difference is exactly one span: document `ndoc_...08DE2HT` (D5), ordinals 301 to 308 (8 rows), the second alternative candidate span of C22 that `spans.proposal.json` lists and `decisions.json` does not choose (the chosen span is 289 to 300, used by C21 and C22). It is in no map and no request. 80 + 8 = 88.

## 4. Check (e): own `plan` on copies, then comparison

The lane copied `map.json` and `request.json` of each bundle to `independent/bundle-<S>/` (`cmp` equal to the originals) and ran `promote_cli plan` on the copies against the custody lane (`DATABASE_URL` built from `docker inspect` at run time). All six exited 0 with `verdict: not_compared` and printed values that match the independent inputs of section 3 (60 further comparisons, ten per scope: `independent/own-plan-checks.txt`, all `EQUAL`): `map_sha256`; the two proof digests; every `query_text_sha256`, `query_vector_sha256` and `targets=`; every `designation:` line.

Only then the lane opened the first lane's `plan-<S>.txt`. **The whole output of every scope is identical** (set id, snapshot, content key, build, profile, `map_sha256`, both proof digests, `set_sha256`, `set_size_bytes`, `catalogue_sha256`, `catalogue_size_bytes`, `prompt_part_characters`, `verdict`, every `item:` and `designation:` line); nothing differs (`independent/compare-with-ab2.txt`).

| Scope | `set_sha256` | `set_size_bytes` | `prompt_part_characters` | Headroom to the 22,000 cap |
| --- | --- | ---: | ---: | ---: |
| F1 | `6a5bef0d4cc8eb22bbb8415858a299961d7840cc4cdf12932b6a25b1b7d92750` | 673,252 | 19,249 | 2,751 |
| F2 | `3f052bb180e69a715f251039dc4572f57b3aee2df216161fdb29b9909121f798` | 2,406,127 | 11,958 | 10,042 |
| A1 | `71392ce04f9bb9b626d06a05975330c826eb448af5cd3a0b81c58fa70923c1a1` | 659,945 | 15,032 | 6,968 |
| A2 | `cba84246d599211a1b50ffe785db78a491a1c06f954712d4e7d37bafc98afa86` | 1,282,762 | 14,143 | 7,857 |
| S1 | `4f46c4452c00d077ba649fefc24291ca26eecccace1a806b9c646116036c0a15` | 694,276 | 21,921 | **79** |
| S2 | `7ea90c622af90df6ebdc8bda1f47f19703ce1e074224921349b80181c411c05d` | 690,089 | 18,930 | 3,070 |

All six `catalogue_sha256` are `4b20165647d5a1f9497c36726dc7074a83468994092e14bcc67fd9175f87a555` (240,015 bytes). The catalogue depends on the snapshot only, so the six sets share one catalogue Blob.

### The prompt-part figure explained from `ranking.select_prompt_part`

`plan` prints `len(candidate.selection.prompt_part)` of the real selection, not the target-only figure of `pack-summary.json` (basis `target_rows_only_zero_retrieved_windows`). `select_prompt_part` ranks, per item, the three windows of the target documents with the highest exact inner product against the item's query vector, and builds each item's rows as its target rows plus the paragraphs covered by those windows (`_rows_for_item`, a set per item; rows of different items are separate prompt rows). It then tries, in order, and returns the first whose serialised JSON has at most `char_cap = 22,000` characters: (3 windows, nothing dropped), then (3, 2, 1, 0 windows) with every window that lies wholly inside the targets dropped first. It refuses only if target rows alone exceed the cap.

The lane called the function read-only on the lane's own inputs (the same `prepare` as `plan`) with the cap lowered step by step. The strictly decreasing lengths of the attempts, with the windows per item and the number of prompt rows:

| Scope | 3 windows, none dropped | 2 windows | 1 window | 0 windows (target rows only) | Chosen |
| --- | --- | --- | --- | --- | --- |
| F1 | 24,956 (47 rows) | **19,249** (36 rows) | 12,428 | 5,728 (10 rows) | 2 windows, inside-target windows dropped |
| F2 | 81,358 | 58,483 | 30,879 | **11,958** (21 rows) | 0 windows |
| A1 | 46,213 | 40,443 | 27,674 | **15,032** (26 rows) | 0 windows |
| A2 | 72,113 | 53,567 | 32,172 | **14,143** (25 rows) | 0 windows |
| S1 | **21,921** (24 rows) | 18,957 | 16,396 | 14,078 | 3 windows, none dropped |
| S2 | **18,930** (19 rows) | same length | 16,622 | 14,078 | 3 windows, none dropped |

(An attempt that is not shorter than an earlier one is not listed: the "3 windows, inside-target windows dropped" attempt equals the first column for every scope, and for S2 the 2-window attempt equals the first column too. Dropping and limiting only remove rows, so an attempt can never be longer than the first.) So:

- F1, S1 and S2 are larger than the target-only figures (5,728, 14,078, 14,078) because retrieved windows stay in: F1 keeps two windows per item (+13,521 characters, 26 rows outside the targets), S1 three (+7,843, 12 rows outside) and S2 three (+4,852, 7 rows outside).
- F2, A1 and A2 equal the target-only figures **because the cap forced the selection down to zero windows**: even one retrieved window per item exceeds 22,000 (30,879; 27,674; 32,172). They are not equal because the retrieved windows lie inside the targets: their sets carry target rows only. This corrects the open question in the first lane's report. It is a property of the reviewed spans and the cap, not an error; it means retrieval adds nothing to those three scopes.
- **S1 has 79 characters of headroom**, which is the only tight value. The set is immutable once verified, so the headroom matters only if a set is ever rebuilt from changed inputs: a rebuild that adds 80 characters (a longer designation or a changed paragraph) would, by the documented reduction order, fall back to a two-window selection. The cap is enforced in `select_prompt_part`, `promotion.py` (`1 <= len <= 22_000`) and `artifact.py`.

## 5. Expected digests, promotion and replay

All checks equal, so the lane wrote `expected_set_sha256` and `expected_catalogue_sha256` (its own values from its own `plan`, section 4) into its copies `independent/bundle-<S>/request.json`. The file was re-serialised with the original style (the old file re-serialised byte-identically before the two keys were added). Each `plan` then ended `verdict: matched`, exit 0.

State of the custody lane before: migration head `0031_executor_pull_channel` (not migrated), `norm_retrieval_set` empty, 28,920 `norm_source` admissions and bindings (all confirmed), no pending admission, none of the six ids present. `promote` ran for the six bundles one at a time, in the order F1 F2 A1 A2 S1 S2; each printed `promote: verified`, `replayed: false`, the digests of section 4 and two Blob ids.

| Scope | Set Blob | Catalogue Blob |
| --- | --- | --- |
| F1 | `blob_29GJ3S9S9NWZRYJS5MAJDPQEYZ` | `blob_2RWDA0ERNYFCVMSK0S8YKV2D18` |
| F2 | `blob_48N8JKM7TPMC5DGB2S4SJN6BCF` | same |
| A1 | `blob_5TKJDHG2DRR542A5SD8MT4BMZC` | same |
| A2 | `blob_23BYK38WZA54KAF9J2759EXVDD` | same |
| S1 | `blob_3M077M9KE044GHQ26EM4Z6RKZ8` | same |
| S2 | `blob_0DHDPBCPMDCFJ44PGVGCSQKY66` | same |

A read-only SQL snapshot after the six promotions: `norm_retrieval_set` 6 rows, all `verified`, observed digests equal the expected ones, `prompt_part_characters` as in section 4; `norm_custody_admission` 6 `norm_catalogue` + 6 `norm_retrieval_set` confirmed (plus the 28,920 source ones); `norm_custody_binding` 6 + 6 (+ 28,920); `blob` 28,927 (28,920 + 1 shared catalogue + 6 sets); `audit_event` 86,796.

The replay of each bundle printed `promote: verified`, `replayed: true`, exit 0, the same set id, digests and Blob ids as the first run. A table-count and row snapshot taken before and after the six replays is **identical** (`independent/db-counts-*-replay.txt`, `db-state-*-replay.txt`, `cmp` equal): nothing was changed.

## 6. Seal and verify

`DATABASE_URL` from the custody lane (built at run time, never written), `seal` against `docs/program/ar-v3-beta/scopes.json`, `--out /root/projects/PDF-Analysis/.local/ar-v3-draft/pack.json` (untracked; `git check-ignore` names `.gitignore:20 .local/`). Values (Russian, because the settings screen shows them):

| Field | Value |
| --- | --- |
| `--reviewer` | `ИИ-интегратор (Claude Code), сессия integration/ar-close-1026` |
| `--capacity` | `ИИ-интегратор по поручению владельца (R-146ba); не эксперт предметной области` |
| `--reviewed-at` | `2026-10-27` |
| `--decision-ref` | `R-146ba (A-10, A-11); decisions sha256 f18168f037b768a672dc657e9b8cd6bb8e87a199043aee253c11ba24f064f0cb; map digests F1 6ef3303ad6b3, F2 56ee1c26e79c, A1 4b7c2f9d490f, A2 5e97bcc69091, S1 4502cb676a47, S2 547aea97e556` |
| `--scope-statement` | `Подготовлено ИИ-интегратором по поручению владельца; эксперт предметной области не участвовал; нормы не сверены с официальной редакцией человеком; независимая проверка карт, векторов и сводных значений выполнена вторым отдельным ИИ-сеансом (ИИ проверяет ИИ), это не экспертная проверка. Охват: шесть областей АР v3 (F1 F2 A1 A2 S1 S2), 22 темы C01-C22, 14 тем как предварительная цитата и 8 только как контекст (C05 C06 C08 C09 C10 C15 C21 C22); числовые выводы недоступны.` |

The `decisions.json` digest was computed from the tracked file; the 14 and 8 come from its `mode` counts (14 `provisional_citation`, 8 `context_only`: C05 C06 C08 C09 C10 C15 C21 C22). The scope statement adds one clause to the feasibility proposal: that the independent check was AI to AI.

**This table is the record of what was sealed on the custody lane (a file that is not installable). Two phrases of its `--scope-statement` say more than was done; the live seal uses the corrected text of section 6a, not this one.**

| Item | Value |
| --- | --- |
| `pack_sha256` (inside the manifest, printed by `seal` and `verify`) | `5d87c1ef52b09aaaab73325c0504c401b29a5af23a16162165ef5954de59251d` |
| SHA-256 of the file `pack.json` | `9c2cdc9d71402f80cef1e13da54ab3f15f06d833c30345fe3e240ad77ec8cd78` |
| File | 4,457 bytes, mode 0600, `/root/projects/PDF-Analysis/.local/ar-v3-draft/pack.json`, not in Git |
| Set ids and `set_sha256` in the manifest | equal to the own `plan` values for all six scopes (checked by script) |

`pack_sha256` is tamper evidence, not a signature (`D-212`); custody of the file is the control.

### 6a. Seal values for the live host (corrected 2026-10-28, `AR-V3-JUDGE-FIXES-01`) — the single source

The settings screen shows the statement verbatim, so each phrase is checked against what the system does and what this lane did:

- «числовые выводы недоступны» (section 6) is wrong as a description of the product: only the numeric **fields** `required_value` and `stated_value` are stored and not served (no API response, CSV or workbook carries them); the model's `finding_text` and `recommendation_text` and the norm quote **are** served and may contain figures that nothing checks. New wording: «числовые поля не отдаются; текст модели и цитата нормы могут содержать числа».
- «независимая проверка карт, векторов и сводных значений» (section 6) says more than sections 3(c) and 9 record: the vectors were **not** re-derived from the frozen model and the embedding-set digest was taken from the hash-chained manifest; what was checked is that the bytes and digests correspond. New wording: «проверено соответствие байтов и дайджестов; векторы заново не считались».

| Field | Value for the live seal |
| --- | --- |
| `--reviewer` | `ИИ-интегратор (Claude Code), сессия integration/ar-close-1026` (unchanged) |
| `--capacity` | `ИИ-интегратор по поручению владельца (R-146ba); не эксперт предметной области` (unchanged) |
| `--reviewed-at` | the day of the live seal, `YYYY-MM-DD` |
| `--decision-ref` | `R-146ba (A-10, A-11); decisions sha256 f18168f037b768a672dc657e9b8cd6bb8e87a199043aee253c11ba24f064f0cb; map digests F1 6ef3303ad6b3, F2 56ee1c26e79c, A1 4b7c2f9d490f, A2 5e97bcc69091, S1 4502cb676a47, S2 547aea97e556` — recompute `sha256sum docs/program/ar-v3-beta/decisions.json` first; it must equal the digest here |
| `--scope-statement` | `Подготовлено ИИ-интегратором по поручению владельца; эксперт предметной области не участвовал; нормы не сверены с официальной редакцией человеком; независимая проверка выполнена вторым отдельным ИИ-сеансом (ИИ проверяет ИИ): проверено соответствие байтов и дайджестов, векторы заново не считались; это не экспертная проверка. Охват: шесть областей АР v3 (F1 F2 A1 A2 S1 S2), 22 темы C01-C22, 14 тем как предварительная цитата и 8 только как контекст (C05 C06 C08 C09 C10 C15 C21 C22); числовые поля не отдаются; текст модели и цитата нормы могут содержать числа.` |

Before sealing, the counts (14 and 8) must still equal the frozen `decisions.json` (the shape test asserts them). `docs/program/ar-v3-beta/README.md` and `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md` point here; `AR-V3-ACTIVATION-FEASIBILITY-01.md` section 6 holds the original proposal, which is history and was not edited.

## 7. Commands (secrets not shown)

All from `/root/projects/PDF-Analysis/.local/worktrees/ar-v3-promote-01`, `PYTHONPATH=src:$BS`, `.venv/bin/python` (symlink to the main `.venv`, ignored); `DATABASE_URL` and the S3 settings were built from `docker inspect` of the lane's own containers at run time.

- `docker start auditmanager-ar-beta-custody-postgres-1` (for `plan`); `docker start auditmanager-ar-beta-custody-s3-1` (for `promote`); the S3 init container was not started; `docker stop` for each at the end.
- `python -m auditmanager.norms.retrieval.promote_cli plan independent/bundle-<S>` (twice per scope), `promote independent/bundle-<S>` (twice per scope: promotion and replay).
- `python -m auditmanager.runs.v3_pack_cli seal --scopes docs/program/ar-v3-beta/scopes.json --reviewer ... --capacity ... --reviewed-at 2026-10-27 --decision-ref ... --scope-statement ... --out .local/ar-v3-draft/pack.json`; `... verify --manifest .local/ar-v3-draft/pack.json`.
- The checks of section 3 and the read-only database queries were small Python scripts kept in the lane's scratch directory (the check output is in `independent/`).

## 8. Containers and disk

`docker ps -a --filter name=auditmanager-ar-beta-custody` at the end shows all three containers `Exited` (see the task file, P-05). The lane started PostgreSQL once for `plan`, the S3 container for `promote`, and PostgreSQL once more for the read-only attempt-length figures of section 4, and stopped each with `docker stop`.

`df -B1 /` (free bytes): 6,269,960,192 before (10:49 UTC); 6,203,060,224 after the six promotions and the seal (10:56 UTC), 66.9 MB less, which is the PostgreSQL and MinIO volume growth (about 6.4 MB of set Blobs and one 240 kB catalogue, plus WAL and logs); 6,094,589,952 at 11:00 UTC when the lane finished, after the last container stop. The further 108 MB between 10:56 and 11:00 is not explained by this lane (its scratch under `independent/` is 0.5 MB, and the last PostgreSQL start ran read-only queries); the host is shared, so the figure is reported, not attributed. Free space is 6.09 GB.

## 9. Observations and limits

1. **Independence is partial and the record says so.** The reviewer recomputed the inputs from other sources, but set and catalogue digests come from the same tool and the same database as in the first lane; their equality shows the tool is deterministic on those inputs, not that the sets are right. The reviewer did not re-derive the query vectors from the BGE-M3 image, did not recompute the embedding-set digest from the window vectors, and compared no norm text with an official edition.
2. **The 79-character S1 headroom** and **three scopes whose retrieval is switched off by the cap** (F2, A1, A2) are facts of the reviewed spans, not defects; an expert or the owner may want to know them before beta.
3. **Plan and promote are fast here:** 1.5 to 2.0 s and 3.5 to 4.8 s per scope on 61,573 windows, against the feasibility estimate of 10 to 20 minutes.
4. **A process slip, corrected:** the first six own `plan` outputs were written into the worktree root (the runner script changed directory before resolving a relative prefix). They were untracked, were moved to `.local/ar-v3-draft/independent/` before any commit, and `git status` was clean afterwards.
5. **Not done, by design:** no migration of the lane, no change to `decisions.json`, the maps or the vectors, no push, no tag, nothing under `src/`.

## 10. For the integrator

- The sealed pack is on this host only (`.local/ar-v3-draft/pack.json`, mode 0600, file SHA-256 `9c2cdc9d...cd78`, `pack_sha256` `5d87c1ef...9251d`). It names sets in the **custody lane's** database. For the live host (feasibility step 10) the same six bundles (`independent/bundle-<S>/`, now carrying the `expected_*` digests) are promoted there with the same `set_id`s and `plan` must end `verdict: matched` against the digests of section 4; then `seal` again against the live database with the values of section 6a (a pack sealed here names rows the live database does not hold, and its statement carries the two phrases that 6a corrects).
- The six set ids must be kept as long as any bundle is; a second id for a scope is never minted.
- The bundles hold query vectors; they stay out of Git.
