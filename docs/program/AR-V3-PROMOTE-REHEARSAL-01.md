# AR-V3-PROMOTE-REHEARSAL-01 — six `promote_cli plan` runs on the custody lane

**Task:** [AR-V3-PROMOTE-REHEARSAL-01](tasks/AR-V3-PROMOTE-REHEARSAL-01.md). **Lane:** AR-B2, part 2 (bundles and plan). **Base:** `cb7a34d3` (`integration/ar-close-1026`). **Run:** 2026-10-27 UTC. **Authority read:** `R-146ba` and `R-146bb` (the AR v3 activation is prepared by the AI integrator under the owner's delegation; no subject-matter expert takes part), accepted risks `A-10` and `A-11` (`PRODUCTION-READINESS-PLAN-01.md`). This is step 8a of section 8 of [AR-V3-ACTIVATION-FEASIBILITY-01](AR-V3-ACTIVATION-FEASIBILITY-01.md).

**Honest state.** An AI lane built the six request bundles and ran the read-only `plan` of [AR-V3-BETA-SET-TOOL-01](AR-V3-BETA-SET-TOOL-01.md) against the stopped custody lane. No subject-matter expert took part, no human compared any norm with its official edition, and nothing here says that an edition is current or that a branch applies to a real project. The same lane built the bundles and ran `plan`, so this run is **not** the independent recomputation of the tool's two-person check: that is the next lane's job. No set was promoted, no `expected_*` digest was written, nothing was written to the database or the object store.

## 1. Result

All six `plan` runs exited **0**, printed `verdict: not_compared`, and wrote nothing to stderr. Each took **1.7 to 2.3 seconds** of wall time. The feasibility report estimated 10 to 20 minutes per scope and called it unmeasured; the measure is about two orders of magnitude shorter. The `plan` call hands the mapped document identities to the window reader (`promotion.py`, `read_retrieval_windows(..., mapped_document_ids=mapped)`); I did not profile it, so the reason for the difference is not established here.

| Scope | Set id | Items | Mapped documents | Exit | Wall time | `set_size_bytes` | `prompt_part_characters` |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| F1 | `nrs_01M5YF1W4BG5260JTSCAZP3F58` | 3 | 1 | 0 | 2.1 s (repeat 1.7 s) | 673,252 | 19,249 |
| F2 | `nrs_01M5YF1WVZYFD50K47BDYZM59D` | 7 | 3 | 0 | 2.3 s | 2,406,127 | 11,958 |
| A1 | `nrs_01M5YF1XMMCHT6F6K6HWZEJG4H` | 4 | 1 | 0 | 1.9 s | 659,945 | 15,032 |
| A2 | `nrs_01M5YF1Y8EBK2CBW9JGFADFK31` | 6 | 2 | 0 | 1.9 s | 1,282,762 | 14,143 |
| S1 | `nrs_01M5YF1YXN8WZTV8TFKZ0EWVTZ` | 1 | 1 | 0 | 1.8 s | 694,276 | 21,921 |
| S2 | `nrs_01M5YF1ZFPGBN4PMERTPN6GA27` | 1 | 1 | 0 | 1.7 s | 690,089 | 18,930 |

| Scope | `map_sha256` | `set_sha256` |
| --- | --- | --- |
| F1 | `6ef3303ad6b336b57daf3256710e9ffdad8fa769e746a78ade9bc254fc6a0246` | `6a5bef0d4cc8eb22bbb8415858a299961d7840cc4cdf12932b6a25b1b7d92750` |
| F2 | `56ee1c26e79cfaebb742bf6bc39c1c09789270047a029f898c566c74e89597f6` | `3f052bb180e69a715f251039dc4572f57b3aee2df216161fdb29b9909121f798` |
| A1 | `4b7c2f9d490faf3acfffe3e5805a21b24d55be70cea731253b50d183aa2fcc29` | `71392ce04f9bb9b626d06a05975330c826eb448af5cd3a0b81c58fa70923c1a1` |
| A2 | `5e97bcc69091e8e36d992088e361e06077f25f15f59829914a95e1053b85d0de` | `cba84246d599211a1b50ffe785db78a491a1c06f954712d4e7d37bafc98afa86` |
| S1 | `4502cb676a47d79d485076201a0ce16c5619fcf8c41b5200770820035f092f0e` | `4f46c4452c00d077ba649fefc24291ca26eecccace1a806b9c646116036c0a15` |
| S2 | `547aea97e556928b4be79ddc389943badf32aed67cbf8f1492642ef3caa03793` | `7ea90c622af90df6ebdc8bda1f47f19703ce1e074224921349b80181c411c05d` |

Values equal in all six outputs:

| Field | Value |
| --- | --- |
| `source_proof_digest` | `0a1bafe103ff2df5d53108af602b7aa788d0831353228bfc92c9506a411a3b10` |
| `embedding_proof_digest` | `e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df` |
| `catalogue_sha256` | `4b20165647d5a1f9497c36726dc7074a83468994092e14bcc67fd9175f87a555` |
| `catalogue_size_bytes` | 240,015 |
| `verdict` | `not_compared` |

Each `map_sha256` equals the `map_sha256` of the same scope in the tracked `ar-v3-beta/scopes.json` and in `ar-v3-beta/pack-summary.json`. The `plan` output is stable: a second run of F1 printed a byte-identical stdout (`cmp` equal).

## 2. Where each field of `request.json` came from

The bundles are in `.local/ar-v3-draft/bundle-<S>/` (untracked, mode 700): `map.json` and `request.json`, nothing else. They hold query vectors, so they stay out of git.

| Field | Source |
| --- | --- |
| `map.json` | `.local/ar-v3-draft/pack/scope-<S>.map.json`, copied; checked byte-identical, and its SHA-256 equals the `map_sha256` printed by `plan` |
| `set_id` | `.local/ar-v3-draft/set-ids.json`: one `promote_cli new-id` per scope, minted once, never again |
| `snapshot_id`, `reviewed_content_key`, `embedding_build` | the map; `snapshot_id` and the content key were also checked against the verified bundle manifest |
| `chunking_profile` | the verified bundle manifest (`characters-v2:1200`) |
| `independently_checked_source_digest` | `snapshot.content_digest` of the verified W54 bundle `manifest.json` |
| `independently_checked_embedding_digest` | `build.embedding_set_sha256` of the same manifest (equal to the `build` digest in [AR-BETA-LOCAL-CUSTODY-01](AR-BETA-LOCAL-CUSTODY-01.md) and [W54-EMBED-BUILD-01](W54-EMBED-BUILD-01.md)) |
| `designations[].designation` | the map: every target of a document carries one label, equal for all its targets |
| `designations[].slug` | `slug` of the document in `rows/documents.jsonl` of the same verified bundle (the request needs the stored slug; it is not in the map) |
| `items[].query_vector_base64`, `provenance.query_vector_sha256` | the item's entry in `.local/ar-v3-draft/embed-<S>.response.json` (`vector`, `vector_sha256`); the bytes were decoded and hashed to the entry's digest |
| `items[].provenance.query_text_sha256` | `docs/program/ar-v3-beta/query-texts.json`; it also equals the entry's `input_sha256` |
| `items[].targets` | the map's targets: `norm_document_id`, `ordinal_first`, `ordinal_last` |
| `expected_set_sha256`, `expected_catalogue_sha256` | **absent**, as the task requires |

The two proof digests were **not** read from the database being qualified. Before use, `manifest.json`, `rows/documents.jsonl` and `rows/snapshot.json` of the bundle were re-hashed against the bundle's `SHA256SUMS` (all three equal), the manifest's content digest equals the one in `rows/snapshot.json`, and its first 12 hex characters are the suffix of the content key. The bundle itself was verified byte for byte by the earlier custody lane (28,979 files). Both proof digests also appear unchanged in the `plan` output, which means the lane's stored values agree with them (the library refuses otherwise with `source digest differs from independent proof`).

## 3. Commands

Working directory `/root/projects/PDF-Analysis/.local/worktrees/ar-v3-promote-rehearsal-01`, `PYTHONPATH=src`, `.venv` a symlink to the repository virtualenv (untracked, ignored). `CLI=.venv/bin/python -m auditmanager.norms.retrieval.promote_cli`.

```text
# 1. identities, once per scope in the order F1 F2 A1 A2 S1 S2 (written to .local/ar-v3-draft/set-ids.json)
$CLI new-id
# 2. bundles: .local/ar-v3-draft/make_bundles.py docs/program/ar-v3-beta/query-texts.json
#    (untracked; re-hashes the bundle files against SHA256SUMS, builds the six directories, refuses to overwrite one)
# 3. the only container started (permitted verbs only):
docker start auditmanager-ar-beta-custody-postgres-1        # 2026-10-27T10:39:59Z
# 4. per scope, one at a time, through .local/ar-v3-draft/run_plan.sh <S>:
DATABASE_URL=<built at run time from the container's POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB read by `docker inspect`; host 127.0.0.1 port 58490; never printed or stored>
$CLI plan .local/ar-v3-draft/bundle-<S>   > .local/ar-v3-draft/plan-<S>.txt  2> .local/ar-v3-draft/plan-<S>.err
# 5. the stop
docker stop auditmanager-ar-beta-custody-postgres-1         # 2026-10-27T10:41:36Z
```

The six runs started between 10:40:19Z and 10:40:48Z. `plan` builds its runner with no object store (`factory(False)` in `promote_cli.py`), so the settings it needs are `DATABASE_URL` only. I therefore started **only the PostgreSQL container**; `auditmanager-ar-beta-custody-s3-1` and `-s3-init-1` were never started. The task permitted all three; none of the commands needed the other two. The migration head of the lane (`0031`) was not touched, no `promote` was run, no other docker verb than `start`, `stop`, `ps` and `inspect` was used on the three named containers, and no process was killed.

One note on process: my first `docker start` was refused by the permission classifier because I had put a `docker exec` readiness probe in the same command, a verb outside the permitted set. Nothing ran. The command was re-issued with `docker start` alone, and readiness was probed with a plain TCP connect to `127.0.0.1:58490`.

## 4. Observations the next lane should know

1. **`plan` is fast here.** 1.7 to 2.3 s per scope on 61,573 windows in the snapshot, with the host load average near 4 and 2 to 3 GiB of memory available. The cost of `promote` (three prepares) should be of the same order; it was not run here.
2. **`prompt_part_characters` differs from `pack-summary.json` for three scopes.** The summary was built with the basis `target_rows_only_zero_retrieved_windows`; `plan` prints the length of the real `select_prompt_part` result, which also takes the three best-matching windows per item (`ranking.py`, `ranked[...][:3]`) under the cap of 22,000 characters. Equal: F2 (11,958), A1 (15,032), A2 (14,143). Larger: F1 19,249 against 5,728 (+13,521), S1 21,921 against 14,078 (+7,843), S2 18,930 against 14,078 (+4,852). All six are within the cap; **S1 has 79 characters of headroom**. The explanation of the three larger values is from reading the code; why the other three are equal to the target-only value was not traced.
3. **The catalogue is the same for all six sets** (one digest, 240,015 bytes), while the six `set_sha256` values differ. `promote` will admit the same bytes under six set identities; whether the custody layer is content-addressed so that this is one Blob is for the `promote` lane to watch; this task did not test it.
4. **`designation:` lines.** `plan` printed, per mapped document, the label of the map (five «СП» labels for D1 to D5 and the reader's label of the federal law for D6, the string that `map_pack validate` already compared with the exported paragraph rows). The independent lane should compare each label with the norm the approved map names for that document id, not with this report.
5. **Nothing was compared.** `verdict: not_compared` is correct: no `expected_*` key exists. The independent lane writes the two keys into **its own copy** of the bundles after it has recomputed.

## 5. Refusals

None. All six `plan` runs exited 0 with an empty stderr; no decision file, map or vector was changed.

## 6. For the independent lane (what to recompute)

Do not copy anything from the `plan-<S>.txt` files into a request. Re-derive from the verified W54 bundle manifest and a database of your own reading:

- `sha256sum map.json` equals the `map_sha256` above, and the map's items, mapped documents, target spans and branch decisions are the ones in `ar-v3-beta/decisions.json`;
- the two proof digests equal `snapshot.content_digest` and `build.embedding_set_sha256` of the bundle manifest;
- each `query_vector_sha256` equals the digest of the vector re-encoded from the frozen BGE-M3 image for the item's query text (`query-texts.json`); the vectors in this run were made in a hash-checked virtualenv, not in the image, and `vectors-provenance.json` records the differential check that supports equality;
- each `targets=` line equals the approved spans and each `designation:` line the approved label;
- your own build of the set and the catalogue from the same snapshot and map yields the `set_sha256`, `catalogue_sha256` and `prompt_part_characters` above.

Only then write `expected_set_sha256` and `expected_catalogue_sha256`. A second AI lane is not a subject-matter expert and the record of it must not be called expert review.

## 7. The containers are stopped

```text
$ docker ps -a --filter name=auditmanager-ar-beta-custody --format '{{.Names}}  {{.Status}}'
auditmanager-ar-beta-custody-s3-init-1  Exited (255) 3 days ago
auditmanager-ar-beta-custody-postgres-1  Exited (0) 1 second ago
auditmanager-ar-beta-custody-s3-1  Exited (255) 3 days ago
$ docker ps --filter name=auditmanager-ar-beta-custody --format '{{.Names}}'
$                                   # empty: none of the three is running
```

Before the run the same listing showed the PostgreSQL container `Exited (0) 5 minutes ago` (the integrator's earlier export) and the two S3 containers `Exited (255) 3 days ago`. Free disk before and after: 6,565,777,408 and 6,415,224,832 bytes (`df -B1 /`; other sessions write to the same filesystem, the draft files of this lane are under 1 MB).

## 8. Not verified

- No `promote` and no replay; the custody write path, the foreign-admission guard and the `slot_reuse` classifier were not exercised on this data.
- The proof digests were checked against the bundle files on disk and the lane's stored values (through `plan`), not against a second copy of the bundle.
- The vectors come from a hash-checked virtualenv; their bitwise equality with the norms-worker image was not proved here.
- No label, span or branch was reviewed by a person; nothing says an edition is current.

## 9. Files

Tracked (this task's allowed paths): this report and [the task file](tasks/AR-V3-PROMOTE-REHEARSAL-01.md). Untracked, under `.local/ar-v3-draft/`: `set-ids.json`, `bundle-{F1,F2,A1,A2,S1,S2}/`, `plan-<S>.txt` (stdout), `plan-<S>.err` (empty), `plan-<S>.time`, `make_bundles.py`, `run_plan.sh`. No corpus text and no vector is in git. The `plan-<S>.txt` files contain only ids, digests, ordinals and the designation labels.
