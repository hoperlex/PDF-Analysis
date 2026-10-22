# EXTRACTION-GC-01 — the extraction stage's per-page collection stops scanning the process heap

Task: `docs/program/tasks/EXTRACTION-GC-01.md`. Debt `D-200` (opened by `GATE-REPAIR-02`). Branch
`agent/extraction-gc-01`, base `d087c101` (`origin/dev`). Lane `auditmanager-lane-e`; the host was running
another session's complete gate, so everything here is container-free: no `make`, no docker, one
process at a time under `nice -n 10`, `free -m` available >= 2.7 GiB and `df` free >= 4.9 GiB before each
run. The largest resident peak I measured was 209 MiB (`VmHWM`, the 16 MiB x 30 000-operator pages); the
2.1 M-object ballast child was capped at 1.5 GiB of address space and its own peak was not measured.

## Result

`extract_document` still runs a full `gc.collect()` after every page, and the memory bound it was added for
(`W55B-FIX` X-2) holds exactly as before, but the collection now costs what the **document** built, not what
the **process** holds. It reads the document inside `_document_heap()`: a counted, thread-safe `gc.freeze()` for
the duration of the read, which leaves a freeze made by other code alone and is lifted in a `finally`. Frozen
objects are in the permanent generation, which no collection walks, and `gc.freeze()` is a list splice.

| | base `d087c101` | this branch |
|---|---|---|
| 16 full collections while 16 pages are read, 2.1 M ballast objects (3 runs) | 4.04 / 4.16 / 4.22 s | 0.0006 / 0.0005 / 0.0006 s |
| the read of those 16 pages | 4.15 to 4.33 s | 0.10 to 0.11 s |
| longest gap of a ten-step heartbeat thread beside the read | 1.28 to 1.33 s | 0.06 s |
| a worker-sized heap, 120 pages of 16 MiB decoded streams: time in full collections / total read | 9.83 s / 31.6 s | 0.41 s / 22.4 s |
| a worker-sized heap, 100 pages of text: the 100 explicit `gc.collect()` calls | 8.38 s (84 ms each) | 0.41 s (4 ms each) |
| resident set after every page, 120 pages of 16 MiB decoded streams | 99 to 100 MiB | 99 to 101 MiB |
| extraction output of the 33 tracked PDFs | reference | byte-identical (sha256 of the canonical JSON), 33 of 33 |

## Who owns the per-page cycle

pdfminer's `PDFContentParser`. `PSBaseParser.reset()` sets `self._parse1 = self._parse_main`, a bound method of the
parser stored on the parser: a cycle of one object. `PDFPageInterpreter.execute()` creates the parser as a local
(`parser = PDFContentParser(valid_streams)`) and nothing outside `execute` ever holds it. The parser's `streams`
are the page's own `PDFStream` objects, whose `data` is the decoded content stream, so each page leaves one
cycle that owns the decoded stream. `execute` runs again for every Form XObject a page draws (`do_Do` ->
`render_contents` -> `execute`), so each form leaves a cycle of its own that owns the form's decoded stream.
Measured with `DEBUG_SAVEALL` on three pages read with the automatic collector off: a full collection frees 47
objects (about 16 a page: the parser, its bound method, its dict, lists, a few `PDFStream`s), and the only
bytes they own are the streams' decoded data (0.46 MiB for three 160 KB pages); the parser's own `fp` is `None`
and `buf` empty at EOF. Nothing else of the page is cyclic: `page.close()` and the emptied `contents` free the rest
by reference counting.

## Why the cycle is not broken explicitly, and why the collection stays a full one

The task prefers dropping the reference that closes the cycle. The stage cannot reach it: the parser is a local
of a pdfminer method. What it can reach is the page's own `PDFStream`s, so I tried the next best thing and
measured it (below): release the decoded data of the streams the page owns (resolve `page_obj.contents` first,
blank `data` after the page), with no collection. It frees the top-level streams and **not** the Form XObject
ones, whose streams only the nested parser holds. A generation-limited collection was measured too. The numbers
are the peak resident set (`VmHWM`, MiB) of a child process after 1 page and after 6 pages, `ulimit -v` 2.5 GB,
five release modes, same document; "full" is the base `_release`, "freeze" is this change.

| document (every page has its own 16 MiB decoded stream unless said) | full | `gc.collect(1)` | none | blank owned streams | freeze + full |
|---|---|---|---|---|---|
| plain padded stream | 134 -> 134 | 134 -> 134 | 134 -> **182** | 134 -> 134 | 134 -> 134 |
| each page draws its own 16 MiB Form XObject | 134 -> 134 | 134 -> 134 | 134 -> **166** | 134 -> **169** | 134 -> 134 |
| plus 2 000 path operators a page | 134 -> 140 | 134 -> **172** | 134 -> **172** | 134 -> 139 | 134 -> 139 |
| plus 7 500 path operators a page | 141 -> 151 | 141 -> **167** | 141 -> **167** | 141 -> 151 | 141 -> 151 |
| plus 30 000 path operators a page | 208 -> 209 | 209 -> 208 | 209 -> 209 | 208 -> 209 | 208 -> 209 |

* `gc.collect(1)` per page fails once a page allocates enough for the parser to be promoted past generation 1;
  at the end of a 7 500-operator page it is in generation 2 (checked directly: `gc.get_objects(generation=2)`).
  A page of 30 000 operators stays flat even with no collection at all, a page of 2 000 does not. So a
  generation-limited collection is a guess about page density.
* Blanking the owned streams is exact for top-level streams and leaves the Form XObject case growing
  (+35 MiB over 6 pages). It also needs pre-resolving the page's stream references and writing `PDFStream.data`,
  and it would need a safety-net collection anyway.
* "Every N pages with N derived": the stage cannot know the decoded size of a page before it has read it, so any
  N is a guess, and the heavy pages that matter are the ones for which N would have to be 1.

## The change

`src/auditmanager/analysis/stages/extraction.py`: `_document_heap()` (new), used in `extract_document` around
`pdfplumber.open(...)`; the `_release` docstring rewritten with the cycle's owner and the measured reasons;
`_release` itself is unchanged (`page.close()`, `page_obj.contents = []`, `gc.collect()`). No other `src` file.

* **Counted.** The first document read in the process freezes, the last to finish unfreezes (a lock and a counter),
  so two documents read at once never lift each other's freeze.
* **A freeze made by other code is left alone.** A bare CPython 3.12 on this host reports
  `gc.get_freeze_count() == 375` before anything is imported, so "frozen" cannot mean "count is not zero" (my
  first version did, and froze nothing). The stage records the count when the module is imported and treats
  more than that on entry as somebody else's freeze: it freezes nothing and unfreezes nothing. This is what keeps
  `tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py`'s own freeze in force through the run.
* **Unfrozen in a `finally`**: a document that fails midway gives the heap back, and `_release` already ran in
  a `finally` for the failing page.
* Cost of the machinery, 2.1 M tracked objects, one process: `gc.freeze()` 0.001 ms, `gc.unfreeze()` 0.001 ms,
  a full collection with everything frozen 0.006 ms (159 ms unfrozen, 168 ms after the unfreeze),
  `gc.get_freeze_count()` 0.035 ms at the baseline and 22 ms with 2.1 M objects frozen (read once per document,
  only when the permanent generation is large).

## Numbers and how they were measured

All on this host, `/root/projects/PDF-Analysis/.venv/bin/python` (CPython 3.12.3, pdfminer.six 20260107,
pdfplumber 0.11.10), under `nice -n 10`, while another session's gate ran (load average about 2.7 on 8 CPUs
at the start of the session).
"Base" is a copy of `src` at `d087c101`; "this branch" is the worktree `src`. The scratch scripts live in the
session scratchpad and are not committed; the committed test is the cost model's child verbatim.

**Cost model** (the child of `test_extraction_gc_scope.py`, run directly, three runs per tree, 1.5 GiB address
space): a list of 2.1 M one-element lists is the ballast, 16 tiny pages, a heartbeat thread that waits 0.05 s and
then makes ten `time.sleep(0.0001)` calls, and a `gc.callbacks` observer that adds up every generation-2
collection.

| tree | `t_full` of the ballast | full collections / their total | the read | longest beat gap | beats in the read |
|---|---|---|---|---|---|
| base | 0.222 / 0.232 / 0.238 s | 16 / 4.04, 4.16, 4.22 s | 4.15, 4.28, 4.33 s | 1.278, 1.325, 1.325 s | 5, 6, 6 |
| branch | 0.239 / 0.257 / 0.244 s | 16 / 0.0006, 0.0005, 0.0006 s | 0.109, 0.099, 0.107 s | 0.060, 0.056, 0.059 s | 2, 2, 2 |

The 16 collections still run on the branch; each walks only what the document built. The first red run of the
committed test on the base: 16 collections in 3.958 s against a bound of 0.717 s, and a longest gap of 1.244 s
against a limit of 0.539 s.

**Memory over many pages** (a scratch script that reads the document, records `VmRSS` after every `_release`, `ulimit -v`
2.5 GB; pages of 2 000 path operators plus a 16 MiB decoded stream, or a page that draws a 16 MiB form):

| document | tree | RSS after pages 1 / 10 / 60 / last | `VmHWM` | read | full collections: count / total |
|---|---|---|---|---|---|
| 120 pages, own streams | base | 99 / 100 / 100 / 100 MiB | 132 MiB | 31.6 s | 121 / 9.83 s |
| 120 pages, own streams | branch | 99 / 101 / 101 / 101 MiB | 133 MiB | 22.4 s | 121 / 0.41 s |
| 60 pages, each draws a form | base | 92 / 92 / 92 / 92 MiB | 124 MiB | 10.8 s | 61 / 4.81 s |
| 60 pages, each draws a form | branch | 93 / 92 / 92 / 92 MiB | 124 MiB | 6.0 s | 60 / 0.01 s |

The existing page-release test `test_extraction_releases_each_page.py` (three heavy documents, peak growth from
1 page to 5 must stay <= 24 MiB, and the text and lines unchanged): **4 passed** on the base copy (18.94 s) and
**4 passed** on this branch (18.81 s).

**Text-heavy documents** (the one place the frozen collection still grows with something: the document's own
result, 121 objects a page). 100 pages x 120 lines, `gc.collect` timed by a wrapper: base read 40.1 s, 100
explicit collections 8.38 s, all 201 full collections (explicit and natural) 19.85 s; branch read 23.1 s, 100
explicit collections 0.41 s, all 201 full 2.86 s. 300 pages x 120 lines: base 139.0 s with 601 full collections
in 71.8 s; branch 79.3 s with 601 in 15.78 s. Unfrozen tracked objects at pages 1 / 100 / 300: 5 905 / 17 884 /
42 084, next to 121 512 frozen. What remains is the natural collections that walk the page in flight and the
growing result, both independent of the process's heap.

**Output identity**: `extract_document` over all 33 tracked `*.pdf` (`git ls-files '*.pdf'`: ar_v2 bundles,
synthetic AR, PC-02 documents and negatives, the w28 own document; 166 pages, 47 856 characters), base and branch
in two processes, `sha256` of `json.dumps(asdict(document), sort_keys=True)` per file: 31 extracted, 2 refused
(`source_encrypted`, both trees), **33 of 33 identical**.

## Tests added

`tests/integration/analysis/test_extraction_gc_scope.py` (container-free, 6 cases, 5 s on the branch):

| case | what it pins |
|---|---|
| `test_the_pages_of_a_document_add_up_to_no_more_than_a_few_full_heap_scans` | in a child holding 2.1 M ballast objects, the full collections that run while 16 pages are read add up to <= 3 x `t_full` of that same process |
| `test_a_heartbeat_thread_keeps_its_pace_while_the_pages_are_released` | the same child: longest beat gap <= 0.05 s + `t_full` + 0.25 s |
| `test_the_heap_is_frozen_while_the_pages_are_read_and_given_back_after` | `gc.get_freeze_count()` is above its starting value at every page and back at it after |
| `test_a_page_that_fails_midway_is_still_released_and_the_heap_is_given_back` | page 2 raises: `_release` ran for pages 1 and 2 only, the refusal is `ANALYSIS_INPUT_INVALID / source_unreadable`, the heap is given back |
| `test_two_documents_read_at_once_keep_one_freeze_until_the_last_one_ends` | a second whole document read while the first is held mid-page does not lift the freeze |
| `test_a_freeze_made_by_other_code_is_left_in_force` | after a read, > 90 % of the caller's frozen objects are still frozen |

Both bounds are relative to `t_full` measured in the same child, so a loaded host moves the bound with the
measurement. Margins: the cost bound 0.72 s against 4.0 s before and 0.0006 s after; the heartbeat limit
about 0.53 s against 1.28 to 1.33 s before and 0.06 s after.

## Mutations (each on a fresh copy of the committed `src` under `.local/`, `pytest -o pythonpath=<copy>/src`)

For every copy the loaded module was printed with the documented `python -I -c` check and resolved under the
copy (`.../.local/lane-e-mut-<name>/src/...`). The unmutated copy under the same command: 6 passed.

| mutation | red |
|---|---|
| `gc.freeze()` replaced by `pass` | the cost case, the heartbeat case, the frozen-while-read case (3 failed, 3 passed) |
| the freeze is always treated as ours (`_heap_freeze_is_ours = True`) | the foreign-freeze case (1 failed) |
| unfreeze without the reader count (`if _heap_freeze_is_ours:`) | the two-documents case (1 failed) |
| baseline compared with `== 0` instead of the import-time count | the cost, heartbeat, frozen-while-read and two-documents cases (4 failed) |
| the unfreeze outside the `finally` | the fails-midway case: "a failed document left the heap frozen" (run with `-k fails_midway`) |
| `_release` called after `_extract_page` instead of in the `finally` | the fails-midway case (`-k fails_midway`) |
| `gc.collect()` removed from `_release` | the existing `test_extraction_releases_each_page.py` padded-streams case (1 failed, 2 passed, `-k 'padded or shared or drawing'`) |

## Decisions taken

1. **Freeze, not break, not generation-limit, not every-N.** The cycle is unreachable from the stage, the
   alternatives measured above either leak a documented case or are guesses, and the freeze keeps the memory
   semantics identical (every cycle of the page freed before the next one, including nested ones). Conservative
   default: change what the collection scans, not whether it runs.
2. **Baseline = the freeze count at import**, not zero (the interpreter reports 375). Limitation: a freeze made
   before this module was imported is indistinguishable from the interpreter's and is lifted with ours; a freeze
   started by other code *while* a document is being read is lifted at the end of that document. Both cost
   performance of that other code, not correctness. The stage is imported at module level by
   `analysis/public.py` and `analysis/stages/source_preparation.py`.
3. **No collection before the freeze.** A `gc.collect()` at entry would cost one process-heap scan per document
   (0.16 s on 2.1 M objects here, 0.32 s in `D-200`'s measurement, 2.5 to 3.6 s in the battery's process) and
   put the stall back. Consequence: a cyclic garbage
   object that already existed when the document started is frozen with the heap and is reclaimed when the
   freeze is lifted, at the end of the document, not during it. Garbage made after the freeze is collected per
   page as before.
4. **`threading.Lock`, not `RLock`**: a finalizer re-entering the stage from inside the critical section would
   deadlock loudly; with an `RLock` it would corrupt the counter silently.
5. **Test shape**: a child process, so the heap is the one the case builds and no other test's frozen state or
   natural collections reach it (the battery process is the very heap this debt is about); the ballast is 2.1 M
   (the figure `D-200` measured), the bounds relative to `t_full`. The heartbeat thread has ten GIL-reacquiring
   steps: with four the base's longest gap (0.74 to 0.97 s) was too close to any limit that leaves the fixed
   code room.
6. `tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py` and the seven 180 s waits of
   `tests/integration/workers/test_worker_service.py` (`GATE-REPAIR-03`) were sized for the old collector. They
   are outside this task's paths and were not touched; they remain correct.

## What was not run

* Everything that needs `DATABASE_URL` or an S3 service, for lack of containers on this host: the d141 test
  (it freezes the heap itself, which the baseline rule leaves in force: argued, not run), `workers/`, `runs/`,
  the `recognised/` bundle tests, and the DB-backed part of the geometry tests. `tests/integration/analysis` +
  `tests/unit/analysis` with `--ignore=tests/integration/analysis/recognised`: **655 passed, 41 errors**, all 41
  fixture-setup errors (19 `DATABASE_URL is not set`, 22 `needs a real S3-compatible service`), 0 failed.
  `analysis_text/test_input_budget_calibration.py`, `p02_journey/test_extractor_divergence.py`,
  `ingest/test_run_readers_agree.py`, `optimisation/test_ar_specification_journey.py`: 35 passed, 12 setup errors
  (`this suite needs the lane's .env`), 0 failed.
* No complete gate, no frontend, no live journey, no `make` target.
* The all-in-one process (`EXECUTION_ROLE=all`) was not run with a real API beside the stage; the child model
  stands in for its heap and its heartbeat.

## Risks and known limitations

* `gc.freeze()` is process-wide state used from library code. It is counted and scoped, but any code that
  freezes *during* a document read has its freeze lifted at the end of that read (decision 2).
* Cyclic garbage that existed before the document started is not collected until the document ends
  (decision 3). In an all-in-one process with a document that takes minutes this is a bounded delay of that
  garbage's reclamation, not growth.
* While a document is read, the full collection walks the document's own result so far (121 objects a page in
  the text experiments; the explicit collections averaged 4 ms over 100 pages against 84 ms before): quadratic
  in pages, with a much smaller constant than the old cost.
* The memory bound relies on the full collection still freeing the nested cycles, which the existing
  page-release test covers for top-level streams only; the Form XObject case is covered by the measurement above
  (134 -> 134 MiB, 60 pages 92 -> 92 MiB) and by no committed test.

## Instruction for the integrator

Merge `agent/extraction-gc-01` as a real merge (light acceptance, `AGENTS.md` section 8). Run on the final tree of
the branch, one process at a time under `nice -n 10`: `git diff --check d087c101..HEAD` rc 0;
`test_extraction_gc_scope.py` + `test_extraction_releases_each_page.py` **10 passed** (rc 0, 18.6 s);
`tests/contract` with the complete gate's three ignores (`test_cp00_candidate.py`, `test_cp00_final_state.py`,
`test_validate_bootstrap.py`) **983 passed, 19 283 subtests passed** (rc 0, 77 s; a first run with this report still
untracked failed `test_alpha_acceptance_command.py` on "checkout contains untracked files", which passes, 33 of 33,
on the committed tree). `D-200` can be closed on the merge: check `pytest
tests/integration/analysis/test_extraction_gc_scope.py tests/integration/analysis/test_extraction_releases_each_page.py`.
Suggested row text for `DEBT_REGISTER.md` (a forbidden hotspot for this lane): *closed by `EXTRACTION-GC-01`
(merge `<sha>`): the per-page collection runs with the heap frozen (`_document_heap`), 4.0 s -> 0.0006 s for 16
pages on a 2.1 M-object heap; the memory bound is unchanged.* No contract, migration, flag or dependency changed;
rollback is the revert of the merge.

## Commands

* Reproduction and scope tests: `cd <worktree> && nice -n 10 /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/analysis/test_extraction_gc_scope.py -rf`
* Memory test: the same with `tests/integration/analysis/test_extraction_releases_each_page.py`.
* Mutation: `... -o pythonpath=<copy>/src ...` on a copy of `src` with `contracts` and `docs` symlinked beside it
  (`docs/program/dispatch/OPERATING_CONSTRAINTS.md` sections 2 and 3).
