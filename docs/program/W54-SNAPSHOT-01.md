# W54-SNAPSHOT-01 — hand-back report

- Task: `docs/program/tasks/W54-SNAPSHOT-01.md`. Grant: `dispatch/W54-PLAN.md` §4 Stage B item 3,
  plus this file.
- Branch `agent/w54-snapshot-01`, worktree `.local/worktrees/w54-snapshot`. Base `2012d04`
  (`integration/w54`: SEAL, CUSTODY, REPAIR and WORKER merged). Implementation commits `b349e88`
  and `7b2564c`; this report is the next commit.
- Checks follow `R-102` (light acceptance). **No container was started and the corpus was not
  read or loaded.** Every database-backed step is listed in §5 for the owner's window.

## 1. Changed files

`git diff --name-only 2012d04..HEAD` lists 14 paths, plus this report:

- **Norms context:**
  - `src/auditmanager/norms/model.py`: `TextReliability`; `Paragraph.text_reliability`;
    `Chunk.paragraph_ordinal_first/last`.
  - `src/auditmanager/norms/segmentation.py`: `segment(..., unreliable_blocks=)` marks
    paragraphs; the `D-126` note on `SEGMENTATION_PROFILE_VERSION`.
  - `src/auditmanager/norms/chunking.py`: `characters-v2`, `chunk_paragraphs`,
    `verify_coverage`, `parse_chunking_profile` and `ChunkingRefused`.
  - `src/auditmanager/norms/snapshot.py`: `with_segmentation_profile` (`D-126`); the row types
    `SnapshotRow`, `DocumentRow`, `ParagraphRow` and `SnapshotRows`; `RowDigest`; `row_digest`.
  - `src/auditmanager/norms/corpus_source.py`: the projection carries `unreliable_count`, the
    unreliable blocks, the segmentation profile and the chunking version. It qualifies both
    keys and refuses `characters-v1`.
  - `src/auditmanager/norms/repository.py`: writes `unreliable_count` and `text_reliability`;
    the stored-count refusal; chunk builds from stored paragraphs; rows read back; the streamed
    row digest; `validate_snapshot_rows`; inserts with the ids the rows carry.
  - `src/auditmanager/norms/loader.py`: `load_corpus(..., chunking_version=)`, which now
    reports `unreliable_count` and `row_digest`; `import_snapshot`; the CLI flag
    `--chunking-version`.
- **Export lines:** `src/auditmanager/norms/__init__.py`; `src/auditmanager/norms/public.py`
  (lines marked `# W54-SNAPSHOT-01`).
- **Documents:** `src/auditmanager/norms/README.md`; `docs/program/NORM_CORPUS_PERSISTENCE.md`.
- **Tests:**
  - new, container-free: `tests/integration/norms/test_snapshot_reliability.py` (16) and
    `tests/integration/norms/test_snapshot_rows.py` (32);
  - DB-backed: `tests/integration/db/test_norms_corpus_migration.py`, with 9 new loader and
    import cases (20 in the file).

### What was built, case by case

| Required | Behaviour | Proved by |
| --- | --- | --- |
| **The REPAIR hand-back** | The loader writes `norms_snapshot.unreliable_count`, which is the ledger's count of blocks that did not end `REPAIRED`. It writes `norm_paragraph.text_reliability` for every paragraph. The repaired snapshot loads under `0018`'s `ck_norms_snapshot_raw_key`. | `test_the_paragraphs_of_an_unreliable_block_are_marked_and_nothing_else_moves`; `test_a_repaired_block_is_reliable_and_an_unrepaired_one_beside_it_is_not`; DB: `test_the_repaired_snapshot_loads_with_its_unreliable_count_and_marks` |
| **The reliability-aware profile and its invariant** | `characters-v2` skips unreliable paragraphs and **ends a chunk at each one**, so no quotation stitches the text either side of a gap. `verify_coverage` is checked before any chunk row is written: ordinals `0..n-1`; consecutive, disjoint, ascending spans; `paragraph_count` equal to the span; union exactly the reliable set. With nothing unreliable, v2 equals v1 chunk for chunk. v2 is the loader's default. | `test_characters_v2_skips_exactly_the_unreliable_set_and_breaks_at_it`; `test_the_coverage_invariant_refuses_every_way_a_chunk_set_can_be_wrong`; `test_characters_v2_equals_characters_v1_when_nothing_is_unreliable`; DB: the coverage SQL in the repaired-load case |
| **The `characters-v1` refusal** | `characters-v1` over a snapshot with `unreliable_count > 0` is refused in three places: in the projection, before any document is projected; in `import_snapshot`, before the session is touched; and by the repository on the **stored** count, before any chunk or build row. | `test_characters_v1_is_refused_over_a_snapshot_with_an_unreliable_block`; `…_even_when_the_unreliable_block_yields_no_paragraph`; `test_import_refuses_characters_v1_over_unreliable_rows_before_touching_the_session`; DB: `test_a_characters_v1_load_over_unreliable_text_is_refused_and_leaves_nothing`; `test_the_database_refuses_a_characters_v1_build_by_the_stored_count` |
| **`D-126`** | A segmentation profile other than the literal `markdown-v1` appends `+seg-<profile>` after the digest of **both** `content_key` and `base_content_key`, so the raw-key CHECK still holds. The constant is read at call time. `markdown-v1` keys are byte-identical. The profile must match TRANSPORT's ERE, read from `forced-command.sh`. | `test_markdown_v1_keeps_every_key_byte_identical`; `test_raising_the_segmentation_profile_yields_a_new_key_for_both_stored_keys`; `test_every_qualified_key_matches_the_transport_grammar`; DB: `test_raising_the_segmentation_profile_loads_a_second_snapshot_beside_the_first` |
| **`import_snapshot(rows with ids)`** | Inserts every row with its own id; private keys are minted and remapped. Builds the named chunk profiles from the inserted paragraphs and re-reads the row digest. One SAVEPOINT. | DB: `test_an_import_carries_every_id_and_rebuilds_identical_chunks_in_another_database` (load in one clone, import into another: equal ids, digest and chunk rows) |
| **Replay** | Exact replay is a no-op: same id, same key, equal stored digest and every named profile built. | the same test (table counts unchanged) |
| **Conflict** | Five cases are refused with nothing written: the same key under another id; the same id under another key; equal ids with other rows; a child id held by another snapshot; an unbuilt profile on replay. A database refusal midway rolls the whole import back. | DB: `test_import_conflicts_are_refused_and_write_nothing`; `test_an_import_the_database_refuses_midway_leaves_nothing_behind` |
| **The row digest** | Format `norm-snapshot-rows/1`: SHA-256 over a version line, then one line per row. Each line is a tag plus a compact JSON array of declared columns. Documents are ordered by id and paragraphs by `(document id, ordinal)`, in code-point order (`COLLATE "C"`). It covers ids, text and `text_reliability`. `RowDigest` refuses rows out of order, so a reader that forgets its `ORDER BY` cannot produce a plausible wrong digest. The repository streams it from the database. | `test_the_row_digest_is_the_documented_canonical_serialisation` (written out by hand); `…_does_not_depend_on_row_order`; `test_every_id_text_and_reliability_moves_the_digest`; `test_the_incremental_digest_refuses_rows_out_of_canonical_order`; DB: `test_the_row_digest_read_back_equals_the_digest_of_the_rows_read_back` |

## 2. Checks run, with commands and results

All of these ran on the committed tree. `git status --porcelain -uall` was empty.

| Command | Result |
| --- | --- |
| `git diff --check 2012d04..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/norms tests/integration/norms tests/integration/db/test_norms_corpus_migration.py` | exit 0 |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms -k "not postgres" --ignore=tests/integration/norms/custody/test_two_phase_custody.py --deselect tests/integration/norms/test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_resolves_to_the_exact_real_corpus` | **262 passed**, 38 deselected (the 37 `postgres` repair cases and the real-corpus read). This includes REPAIR's `test_repair_projection.py` and `test_rerecognition.py`, which are unchanged and green. |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/composition/test_bundle_transport_refusals.py tests/integration/analysis_text/test_proxy_adapter.py` | **194 passed** |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **558 passed**, 50 subtests. `test_alpha_acceptance_command.py` fails only while the tree is dirty, as SEAL recorded. |
| `pytest --collect-only tests/integration/db/test_norms_corpus_migration.py` (no database) | 20 collected |
| SQL, container-free: every `text()` statement in `repository.py`, plus the test's coverage query, parsed with `pglast` 8.5 (libpg_query) in a scratch virtualenv. A broken statement raises, so the check can fail. | all parse. This proves syntax only, not column names. |
| `ruff 0.17.0 check` over every changed Python file (scratch virtualenv) | Clean except two kinds of finding, both matching the base: `segmentation.py` `_Block.__slots__` RUF023 is pre-existing; SIM117 in the DB test is the file's established `with Session(...): with session.begin():` style, already present at `:416`. |
| Mutation check: 14 mutations, each applied in place, the two new files run, the file restored and `git diff --quiet` confirmed | **each made the suite red**: no `+seg-` term (2 failed); constant read at import (1); no unreliable mark (6); v2 not breaking at unreliable (5); projection v1 refusal removed (2); chunk v1 refusal removed (1); `unreliable_count` not carried (4); digest without `text_reliability` (2); digest order not enforced (1); expected digest ignored (1); import v1 pre-check removed (1); validation without the count rule (2); validation without the `D-126` key rule (2); coverage admitting unreliable (1) |

**Not run (heavy, window only):** the 9 new DB cases, and the file's 11 existing ones under
the changed loader. Also not run: the real-corpus key check. Commands are in §5.

## 3. Contracts

- **No contract, migration, error code or API change.** `0018`'s `text_reliability`,
  `unreliable_count` and replaced `ck_norms_snapshot_raw_key` were sufficient.
- **Content key (`D-126`):** `<base key>[+seg-<profile>]`, where the profile matches
  `[a-z0-9]+(-[a-z0-9]+)*` and is at most 100 characters. This is exactly the
  `(\+seg-[a-z0-9]+(-[a-z0-9]+)*)?` term of TRANSPORT's ERE. The repair ledger's
  `base_snapshot_id` stays the unqualified key of the corpus bytes.
- **Chunking profiles:** `characters-v1:<n>` is unchanged but refused over unreliable text.
  The new `characters-v2:<n>` is reliability-aware, and the loader now defaults to
  `characters-v2:1200` (it was `characters-v1:1200`).
- **Row digest format `norm-snapshot-rows/1`.** The `S`, `D` and `P` lines are in the column
  orders of `snapshot.py`; `NORM_CORPUS_PERSISTENCE.md` documents them.
- **Cross-context surface** (`norms.public`): `import_snapshot`, `load_corpus`,
  `CorpusLoadResult`, `SnapshotImportResult`, `SnapshotRows`, `SnapshotRow`, `DocumentRow`,
  `ParagraphRow`, `row_digest`, `ROW_DIGEST_VERSION`, `TextReliability`,
  `RELIABLE_CHUNKING_PROFILE_VERSION`, `ChunkingRefused`, `NormsProjectionConflict`,
  `SnapshotImportConflict`, `SnapshotRowsInvalid`.

### Readings where the plan was silent (conservative choices)

1. **The reliability-aware profile is `characters-v2`.** `chunking.py` already ruled that an
   algorithm change increments the version.
   - It *breaks* a chunk at an unreliable paragraph rather than only skipping it. The
     `norm_chunk` span CHECK needs consecutive spans. Stitching across a gap would also hand
     an expert a quotation whose middle is missing.
2. **`D-126` qualifies both stored keys.** Qualifying only `content_key` would violate the raw-key
   CHECK for an unrepaired snapshot under a new profile.
3. **Chunks are derived on import, not carried.** They are a deterministic function of the
   canonical rows. `import_snapshot` builds each named profile from the inserted paragraphs,
   and the DB test proves the chunk rows equal the origin's.
4. **The row digest covers the three canonical tables only.** It excludes chunks, builds,
   `created_at` and private keys. W55-PLAN calls this "declared columns only".
5. **A loader replay naming a profile the stored snapshot lacks builds it** from stored
   paragraphs, rather than failing on "no complete build". A snapshot loaded under `v1` before
   this lane can therefore gain `v2` by replay.
6. **Equal ids with other rows is a conflict**, detected by comparing the stored digest with
   the rows' digest.
7. **`segment_corpus`, the diagnostic projection, still joins every paragraph** under `v1`.
   REPAIR's `test_an_unapplied_repair_keeps_raw_text_under_an_unreliable_identity` pins that,
   and it is not a stored build. Its paragraphs are marked.

## 4. Risks and known limitations

- **No database ran.** The 9 new DB cases and the 11 existing ones under the changed loader are
  unexecuted. The SQL is checked for syntax only. A wrong column name would surface first in the
  window.
- **The CUSTODY DB test fails at import (pre-existing at the base).**
  `tests/integration/norms/custody/test_two_phase_custody.py` imports `BlobMetadataRepository`
  from `auditmanager.storage`, which does not export it at base `2012d04` either.
  `storage/public.py` does export it. The file is outside this grant (`custody/**`). It needs a
  one-line import fix by its owner or the integrator before the window run.
- **The loader's default profile changed** to `characters-v2:1200`. Its printed
  `chunking_profile` differs from before. Over a snapshot with nothing unreliable the chunk rows
  are identical, so the bake-off pins are unaffected (`markdown-v1` keys are unchanged; the
  runner and fixture are untouched).
- **`_INSERT_SNAPSHOT` now says `ON CONFLICT DO NOTHING` without a target**, so it covers the
  primary key as well as `content_key`. The loader's minted id cannot collide; an import's
  concurrent clash becomes `SnapshotImportConflict`.
- **Memory.**
  - `read_snapshot_rows` and `import_snapshot` hold one snapshot's rows in memory. For the full
    corpus this is about 320k paragraphs, a few hundred MB.
  - `stored_row_digest` streams, and the chunk rebuild reads one document at a time.
  - BUNDLE should export through the streamed path or by document if the host is tight.
- **`unreliable_count` counts ledger blocks** (SEAL's reading 6). A block whose only text is
  publisher noise counts, but marks no paragraph.

## 5. Integrator instructions

1. Read the diff and this report. Merge after REPAIR, before EMBED (plan §5). The shared paths
   handed on are the export lines of `norms/{public,__init__}.py` and `norms/README.md`, which
   EMBED edits next.
2. **Heavy step, owner window only.** Measure first: `free` ≥ 6 GiB available and `df` ≥ the
   increment + 3 GiB. Bring up the lane stack on PostgreSQL `57150` and S3 `60750/60751` with a
   lane `.env`. Then, from the worktree:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/db/test_norms_corpus_migration.py
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms \
       --ignore=tests/integration/norms/custody/test_two_phase_custody.py \
       --deselect tests/integration/norms/test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_resolves_to_the_exact_real_corpus
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/db/test_norm_custody_migration.py \
       tests/integration/db/test_norm_embeddings_migration.py
   ```

   - Expected: the first command gives **20 passed**.
   - The second gives **299 passed**: 262 container-free and 37 REPAIR `postgres` cases.
   - The third runs neighbours on the same tables, unchanged by this lane.
   - After the custody import fix, also run
     `tests/integration/norms/custody/test_two_phase_custody.py`.
3. **Real-corpus key check (read-only, no load).** Run it in the same window, because it reads
   the drop:
   `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_embedding_bakeoff_fixture.py::test_every_relevance_anchor_resolves_to_the_exact_real_corpus`.
   It must pass. That proves the `markdown-v1` base key on the drop is still
   `2026-07-23..2026-08-20+17d.4b74348debf7`.
4. Stop the lane stack by its own compose project; kill nothing by pattern.
5. **Operator step (3), loading the repaired snapshot, now works:**
   `PYTHONPATH=src .venv/bin/python -m auditmanager.norms.loader --corpus .local/norms/corpus --ledger .local/norms/repairs/ledger.json`.
   It builds `characters-v2:1200` by default and prints `unreliable_count` and `row_digest`.
   Passing `--chunking-version characters-v1` is refused when anything is unreliable.

### For `W54-EMBED-01`

- Embed over `characters-v2` chunks; W55's qualification needs reliability-aware chunks.
  `Chunk` now carries `paragraph_ordinal_first` and `paragraph_ordinal_last`; use them, not a
  running count.
- `D-127`'s computed key `content_key ‖ source_document_ref ‖ chunking_profile ‖ ordinal`
  may now see a `+seg-` term in `content_key`. Chunk ordinals are dense `0..n-1` per document
  under both profiles.
- `NormsRepository.build_chunks_from_stored` and `has_chunk_build` exist if the embedder
  needs a profile built.

### For `W54-BUNDLE-01`

- The row digest is in `norms.public`:
  - `row_digest(SnapshotRows)` computes it from rows;
  - `NormsRepository.stored_row_digest(id)` streams it from the database;
  - `read_snapshot_rows(id)` exports the rows.
- Import with `import_snapshot(session, rows, chunking_profiles=[…],
  expected_row_digest=<manifest>)`.
- `SnapshotRows` has no file format; the bundle owns its serialisation.

## 6. Containment

- `git diff --name-only 2012d04..HEAD` lists the 14 paths of §1 plus this report. All are
  inside the grant:
  - `norms/{corpus_source,model,loader,repository,snapshot,segmentation,chunking}.py`;
  - the export lines of `norms/{public,__init__}.py`;
  - `norms/README.md`;
  - two new files under `tests/integration/norms/`, outside `custody/`, `repair/`, `bundle/`
    and `embedding/`, and not REPAIR's three files;
  - `tests/integration/db/test_norms_corpus_migration.py`, appended loader cases only;
  - `docs/program/NORM_CORPUS_PERSISTENCE.md`;
  - this file.
- **Not touched:**
  - contracts and migrations;
  - `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md` and `PORT_REGISTRY.md`;
  - root dependency and lock files;
  - refs and tags;
  - the stand and other worktrees;
  - `.local/norms/**`, which was neither read nor written.
- The scratch virtualenv (`pglast`, `ruff`) lives in the session scratchpad, outside the
  repository.
- No container was started. There was no push, merge, tag or stash. `git status --porcelain -uall`
  is empty after this commit.
