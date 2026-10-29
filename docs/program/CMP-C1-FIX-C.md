# CMP-C1-FIX-C — the third FIX lane of wave C1, backend: a plain-PDF upload is profiled, a version is built in bounded attempts, an identical version is not profiled again

- Task: `tasks/CMP-C1-FIX-C.md`. Work list: `compare/MEASURE-ENGINE-01.md` section 9 (FIX-1, FIX-3, FIX-4). FIX-2 (upload dialog) and FIX-5
  (claim cadence) are not backend code in this lane's paths and are not touched.
- Tree: branch `agent/cmp-c1-fix-c`, base `00afbc21` on `integration/compare-modules` (contract `1.10.0`, 131 paths / 148 operations / 432
  schemas, head `0039_comparison_core`, `cmp-engine/3`, `cmp-profile/3`; all unchanged and re-read before the first edit). No contract,
  migration, dependency, web, `jobs/`, `documents/` or composition-root file changed (`git diff --name-only 00afbc21..HEAD` lists 13 files, all
  in the task's allowed paths; the same listing restricted to `contracts`, `db/migrations`, `pyproject.toml`, `uv.lock`, `web`, `src/auditmanager/jobs`,
  `src/auditmanager/documents`, `src/auditmanager/bootstrap` is empty).
- Run on 2026-10-29 on the shared development host, the lane's own containers (instance `auditmanager-cmp-c1-fix-c`, ports 57930 / 61930 / 61931),
  the corpus `fixtures/comparison/` as the only data (the real measurement set is deleted).

## 1. Result

| Item | State | Test that shows it |
| --- | --- | --- |
| FIX-1 (blocking) | done | `tests/integration/comparison/test_upload_to_series_end_to_end.py::test_a_set_of_plain_pdfs_is_profiled_matrixed_compared_and_tiled_through_the_products_own_path`: **red on the base**, green after (25.5 s) |
| FIX-3 | done, by a bounded attempt that yields (`PAGES_PER_ATTEMPT = 30`) | `tests/integration/comparison/profile_queue/test_a_long_version_is_built_in_bounded_attempts.py` (five tests, a 14-page and a 31-page synthetic PDF through the real runner and children) |
| FIX-4 | done, keyed by the **source bytes** (not by the Merkle), within the project | `tests/integration/comparison/profile_queue/test_identical_versions_reuse_profiles.py` (six tests) and `tests/unit/comparison/profile/test_reuse_donors.py` (seven) |

## 2. FIX-1: a version the plain-PDF upload admitted is profiled, compared and tiled

**The defect, in one line.** `profile/source.py::load_source_version` took the manifest entry of role `source.document` only; `CMP-INGEST-01` binds a
plain PDF as `comparison.source_pdf` (so that a run refuses it, ADR-0025 decision 11). The page-profile builder, the engine
(`engine/service.py:243-244`) and the tile reader (`profile/reader.py:141`) all read a version through that one function.

**The change.** `load_source_version` selects the entries whose role is one of the two `documents.public` names
(`MANIFEST_ROLE_SOURCE_DOCUMENT`, `MANIFEST_ROLE_COMPARISON_PDF`) and nothing else:

* one entry (and `application/pdf`): that is the version's bytes;
* none, or a PDF role under another media type: `analysis_input_invalid`, reason `source_unreadable` (as before);
* two (a manifest that holds both roles): `analysis_input_invalid`, reason **`source_manifest_ambiguous`** (new constant `REASON_AMBIGUOUS`), never
  "whichever comes first". The page-profile handler ends such an item at once with the new reason `page_profile_source_ambiguous` and **no retry**
  (waiting does not make a manifest choose); an unreadable source keeps its retry.

**The other callers.** `grep` of `comparison/**` for a manifest selected by role (`manifest`, `.role`, `SOURCE_DOCUMENT`, `COMPARISON_PDF`,
`source.document`, `comparison.source_pdf`) finds this one place only: the engine inputs (`engine/inputs.py`) and the tile source (`tiles/source.py`) select
no manifest entry (they are handed a path and a profile). So the three readers are fixed by the one function and each is exercised below.

**The end-to-end test** (`tests/integration/comparison/test_upload_to_series_end_to_end.py`). Nothing is seeded: the composed application
(`create_app`) is driven over HTTP by an expert (`createProject`, `createComparisonUpload`, one `uploadComparisonUploadPart` per file,
`completeComparisonUploadFile`, `getComparisonUploadProposal`, `confirmComparisonUploadSet`) on `vs1` v1 to v3. It asserts what the upload made (three
`comparison_pdf` versions, the manifest role `comparison.source_pdf` and no other, three queued `page_profile` items), then the worker's own runner
(`composition.build_comparison_work`, the shipped handler tuple, real page children, real engine child) takes the items in the order the product chains
them: 3 `page_profile` items (all `succeeded`, 1 attempt, 18 profiles, none `RENDER_FAILED`), the `matrix_build` item of `prepareComparisonMatrix`
(matrix `ready`), the `series_drive` and `series_pair` items of `startComparisonSeries` (series `completed`, 2 transitions `completed`), the stored
`comparison_sheet_pair_result` of every compared pair, and **the answer key of the corpus sheet by sheet** (statuses and the verdict of each
transition). It ends with a `streamComparisonPairTile` read and a `streamVersionPageTile` read at level 0 (both render from the stored source).

**Red on the base** (the same test file against `00afbc21`, only the test added): the upload, the proposal and the confirmation pass, and the worker's
three items end

```text
[{'state': 'failed', 'attempt_count': 3, 'failure_reason': 'page_profile_source_unreadable'}, ... x3]
tests/integration/comparison/test_upload_to_series_end_to_end.py:206: AssertionError   (1 failed in 4.14 s)
```

and green with the change (`1 passed in 25.54 s`).

**Mutations.** (a) `roles = (MANIFEST_ROLE_SOURCE_DOCUMENT,)` in `load_source_version`: `test_a_comparison_version_is_read_through_its_comparison_pdf`
and the ambiguity test fail (`2 failed, 7 passed`), restored `9 passed`; (b) `if len(entries) > 1:` replaced by `if False:`: the ambiguity test fails
(`1 failed, 8 passed`), restored `9 passed`. The end-to-end test under (a) is the base run above.

## 3. FIX-3: a `page_profile` attempt is bounded

**Why the heartbeat is not the answer.** `profile_queue/handler.py` already extends the lease and checks the cancel after every page. What fences a long
item is not the lease: `comparison/work/heartbeat.py::ItemHeartbeat` fences its own attempt `watchdog_seconds` (900 s, `ATTEMPT_WATCHDOG_SECONDS`) after
the attempt started, whatever its progress, and that file is `work/**`, outside this lane. A per-page beat cannot move it.

**Why a yield and not more items.** Splitting a version into items of N pages would give one version several dedupe keys, but the callers that wait for
"the live item of version V" look for exactly `page_profile:<V>` and `page_profile:<V>:retry_failed` (`matrix/service.py` `live_work`, the overview's
`_page_profile_version`, the upload batch's live-item count): three places outside this lane's paths that would have to change together, and a pause
of the waiting would open between two items. The queue already has the right move: `Yielded` ("processed one step of a longer job") puts the **same item**
back, **spends no attempt** (`attempt_delta=-1`) and keeps its payload and dedupe key. So an attempt builds at most `PAGES_PER_ATTEMPT` pages and, when pages are left, answers
`Yielded()`; the next attempt skips the stored pages (the builder already resumed after the last stored page) and continues. Every continuation stores at
least one page, so the chain ends.

**N = 30**, from `MEASURE-ENGINE-01.md` section 4.2 (render plus extraction wall per page, host load 2.7 to 4.9):

| Rate | s per page | 30 pages | Against the 900 s watchdog |
| --- | ---: | ---: | --- |
| the whole real set (85 pages, 216.9 s of item time) | 2.55 | 77 s | |
| slowest size class, 1680 x 1190 mm (8 pages, 14.5 + 51.9 s) | 8.30 | 249 s | the aim ("under about 300 s at the worst measured rate"; 36 pages would be 299 s) |
| slowest single page (render max 2.6 s + extraction max 14.0 s, two different pages, an upper bound) | 16.6 | 498 s | still inside, with a margin for a loaded host |

A smaller N only adds claims (about 0.8 s each, `MEASURE-ENGINE-01.md` item 5) and one more stream of the source (14.9 MB at most here); a larger one
leaves the watchdog less than a loaded host needs. A 500-page version is now 17 attempts of at most 30 pages (about 77 s each on the real set's mix), where it was
one attempt of about 1 276 s. A Run that waits for the slot also waits for at most one such attempt, not for a whole version (the original ADR wording
"one page or one pair" is closer, not met). The number is a tuning constant of the handler (`PAGES_PER_ATTEMPT`, with the derivation next to it), not an ADR value.

**What changed in the code.** `builder.build_version_page_profiles(..., max_pages=None, retry_cutoff=None)`: `max_pages` bounds the pages the children are started
for; `VersionBuildReport.remaining` says how many were left; `complete` is false while any remain. `PageProfileHandler(..., pages_per_attempt=PAGES_PER_ATTEMPT)`
passes the bound and answers `Yielded()` on `report.remaining`.

**The one semantic that moves, and why.** A `retry_failed` item used to delete the failed rows (`needs_review` / `RENDER_FAILED`) at the start of *every*
attempt, so a page that failed again was built once more by the next attempt (bounded by the attempt budget). Under yields that would never end: each
continuation would delete the page the previous one had just failed to build and build it first again. A retry item now deletes only the failed rows that
existed **when it was asked for** (`PageProfileRepository.delete_failed(..., created_before=)`, the instant is the work item's own `created_at`, read through
`WorkDependencies.work.get`). The effect: a retry item builds each page that had failed once; a page that fails again while the item runs stays a stored
`needs_review` page, and an operator who frees the host asks again (a new item). The ordinary item, the dedupe key, the payload and the attempt budget are as before.

**Proof.** `test_a_version_of_more_pages_than_an_attempt_holds_is_built_completely_by_one_item_that_yields`: a 14-page synthetic PDF, the handler's bound set to 5
(real runner, real children behind a spy, PostgreSQL): the attempts end `queued`, `queued`, `succeeded`; the work row keeps `attempt_count` 0 after the first and
1 at the end; the attempts are `superseded, superseded, succeeded`; a request made while it waits returns the same live item (`created` false); the dedupe key
and payload are unchanged; rows 1 to 14 each once; the spy saw each page's render child exactly once. `test_yields_do_not_spend_the_attempt_budget...`: 10 pages in 5
attempts of 2 against `max_attempts` 3 succeeds. `test_the_shipped_bound_builds_...`: 31 pages through the runner `build_comparison_work` makes: 30 in the first attempt, the last
in the second. `test_a_retry_item_builds_the_page_that_failed_before_it_and_a_continuation_does_not_build_a_page_it_failed_itself_again`: page 1 failed before the item,
fails again inside it; nine pages in three attempts; page 1's render child started once. Unit: `test_page_profile_handler_unit.py` (the bound is told to the builder; yield
until the last attempt, then `Completed`; exactly one attempt's pages completes without a yield; a yield for the bound is not the retried incomplete build; the cutoff is the item's
`created_at`; a cancel still wins).

**Mutations** (restored, green after each): `if report.remaining:` replaced by `if False:` (the handler never gives the item back) - 3 unit and 2 integration tests fail
(`5 failed, 5 passed` of the selection); `max_pages=self._pages_per_attempt` replaced by `max_pages=None` (no bound) - 4 unit and 4 integration fail (`8 failed, 2 passed`);
`retry_cutoff=...` replaced by `None` - the cutoff unit test and the continuation integration test fail (the item needs a 4th attempt: `'queued' != 'succeeded'`).

## 4. FIX-4: an identical version is not profiled again

**The premise that did not hold.** The brief asked to key the reuse by the page content Merkle "if it already keys the stored archive". It does key the *row*
(`content_key` = SHA-256 of algorithm, page number, Merkle, annotation hashes), but the Merkle is a product of the extraction child, which is 150.4 s of the 203.2 s of child
CPU on the real set: it is known only after the work is done, so it cannot skip it. What is known beforehand is the **source bytes**, so the reuse is keyed by them.
No contract or migration is needed (no column, no table), so the item was built, not skipped.

**Rule** (`profile/reuse.py`). A version takes over the rows of another version when the other is **in the same project**, its source (either role) has the same SHA-256, size and
page count, and the row is of the current `ALGO_VERSION` (`cmp-profile/3`) and is not a page that ended without a result (`needs_review` / `RENDER_FAILED` is not evidence: it says
what a host could not do; the retry path rebuilds it). A taken row is a new row of this version with the same status, reason, content key, summary and blob references; nothing is rendered
or written to the object store (the blobs are content-addressed and already there). One transaction; the table's unique keys and `ON CONFLICT DO NOTHING` make a repeated or concurrent
take-over a no-op. The donors are found through `documents.public` (`DocumentRepository.versions_referencing` and `get_version`); no profile row of another project is read or copied.
Taken pages are reported with `timings["reused_from"]`, counted by `VersionBuildReport.reused`, passed to `on_page` like any page (the lease is still beaten), and **do not count against the
attempt bound** (twelve taken pages with a bound of five complete in one attempt).

**Proof.** Real children behind a spy: a copy of identical bytes in the same project (another role, as a re-sent file) is built by the queue item with `spy.calls == []`, rows equal to the
donor's in page, status, content key and the three blobs, distinct ids, the donor untouched; the same bytes in **another project** start every child; a donor page that failed is built here
(only that page's two children start); other bytes with the same page count reuse nothing; a portal version is a donor for a comparison version. Unit: the donor filter (project, page count, digest,
size, two sources, the version itself, a blob held under another role).

**Mutations** (restored, green after each): no donor ever found - 4 of 6 integration tests fail; the donor's project not checked - the cross-project test fails; `RENDER_FAILED` rows copied - the failed-page
test fails; digest and size not compared (unit) - 2 of 7 fail.

## 5. Checks (light acceptance, `AGENTS.md` section 8)

All on the lane's own containers (`.env` loaded), `--basetemp` under `/tmp/pytest-cmp-c1-fix-c/`, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`; `df -h /` before every run: 8.3 to 8.9 GiB free.

| Command | Result |
| --- | --- |
| `git diff --check 00afbc21..HEAD` | exit 0 |
| `pytest tests/unit/comparison` | 1248 passed (before the whitespace-only last commit) |
| `pytest tests/integration/comparison` (ONE process) | **566 passed** in 468 s (554 before this lane + 12 new) |
| `pytest tests/integration/ingest/comparison_pdf tests/integration/ingest/comparison_batch` | 298 passed in 210 s |
| `pytest tests/integration/composition` (the whole directory) | 1955 passed, 5 skipped in 1855 s |
| `pytest tests/unit` (after the last code commit) | 4985 passed, 76 skipped in 304 s |
| `pytest tests/contract` minus `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (`D-220`) | 1310 passed, 19283 subtests passed in 146 s |
| the task file against the governance guard (`tests/contract/program/test_wave_governance.py`) | 16 passed |

No `make gate` (AGENTS section 8: this lane changes no contract, migration, infrastructure, dependency, composition root or shared fixture; `Lane.runner` and `Lane.seed` gained an optional argument in
`tests/integration/comparison/profile_queue/conftest.py`, a `conftest.py` inside the directories the task owns).

## 6. Risks and known limits

- The attempt bound is a tuning constant derived from one real set (85 pages, four versions of one document); a set with a different mix moves the per-page rate, and the margin (498 s against 900 s at the slowest single page measured) is
  what covers it. It is not an environment variable. The cost of a yield is one claim (about 0.8 s) and one more stream of the source file.
- The retry-item semantic described in section 3 is narrower than before (a page that fails again inside the item is not built again by the same item). No test pinned the old behaviour; the integration test pins the new one.
- Reuse is per attempt and not coordinated between worker slots: two identical versions profiled at the same moment on two slots are both built (the first row to land wins, the other insert is a no-op). With the
  shipped one slot the second item always runs after the first.
- A taken page keeps the donor's `FRAME_MISMATCH` / `PAGE_TOO_LARGE` verdicts (deterministic functions of the bytes and `ALGO_VERSION`); a library bump that changes a result without a new `ALGO_VERSION` would be copied
  as well - the same hole the algorithm version already is for a rebuilt page.
- `matrix_build` (in the worker process, 8.2 s for 85 pages) and the worker's own footprint are not touched (`MEASURE-ENGINE-01.md` section 8.2 item 4).
- The end-to-end test uses v1 to v3 of `vs1` (18 pages, 12 pairs, 25 s); the two later versions add a split sheet whose answer is covered by `series/test_corpus_against_the_answer_keys.py`.

## 7. For the integrator

- New names: `profile.source.REASON_AMBIGUOUS` / `REASON_UNREADABLE` (the latter was private), the work failure reason `page_profile_source_ambiguous`, `profile_queue.handler.PAGES_PER_ATTEMPT`,
  `profile.builder.build_version_page_profiles(max_pages=, retry_cutoff=)`, `VersionBuildReport.remaining` / `.reused`, `profile.reuse`. None is on a wire or in a contract; no table, column or migration.
- A `page_profile` item can now be `queued` between two attempts of one version; every reader of the live item already treats `queued` as live (the matrix build's `_LIVE_STATES`, the upload batch's `LIVE_ITEM_STATES`, the overview's `_LIVE`). Attempt rows of a long version are `superseded` (one per yield), not `failed`.
- Merge: the commits are independent of the other C1 lanes' paths (`profile/**`, `profile_queue/**` and tests only).
- Not done here and worth a later look: the matrix build is not bounded the same way; the claim cadence (FIX-5) matters more now that a long version is several claims.
