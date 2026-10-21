# NORM-REFS-RUN-01 — the run page lists the project's cited norms against the corpus

**Status:** complete (phases A and B), on top of `origin/dev` `282dfaa7` which carries
`CLASSIFICATION-CORRECTION-01` (migration `0028`, surface 72/82/237). Not pushed.

## Result

Phase A builds the whole deterministic read, unserved and read-only:

- `norms/references/snapshot_catalogue.py` — `read_snapshot_catalogue(session, snapshot_id)` reads
  one snapshot's `norm_document` rows by keyset pages (500 per statement, at most 20 000
  documents), checks the snapshot's declared `document_count` against what is stored (fewer or
  more is refused, never cut) and returns the `PinnedCatalogue` the resolver already accepts. The
  unparsed-slug list is computed by the resolver's own `parse_designation`; it is not a reviewed
  list that could drift. The DB-generated `designation_tokens` are copied, and the resolver proves
  them equal to the Python twin (it refuses a difference).
- `norms/references/read_model.py` — `build_reference_read_model(pages, catalogue,
  pinned_snapshot_id)` runs `extract_references` and `resolve_references` unchanged and reshapes
  their report: items (cited designation, outcome code, true occurrence count, at most ten
  anchors `{page_number, char_start, char_end, quote}`, the matched norm document with the
  reader's designation and title), counts for all five outcomes (zeros written), the pages with no
  text layer and the catalogue's unrecognised documents. More than 1000 distinct citations is an
  explicit state, not a cut list.
- `runs/reference_pipeline.py` — `read_run_norm_references(session, run_id, reader, ...)` composes
  the Run row, its Version, the Run's saved page text (port `SavedRunTextReader`, implemented by
  the composition root over the comparison's `_AnalysisReader`) and the pinned snapshot's
  catalogue. Explicit states `ready`, `snapshot_not_pinned`, `text_unavailable`,
  `too_many_citations`; unknown run is `not_found` (`AuditRun`); a malformed id is
  `validation_failed`; any stored fact that contradicts its own constraints is `internal_error`;
  a storage error from the reader passes through unchanged.

**The five outcomes** are the resolver's (`W57-PLAN.md` B3.3, owner answer I-6) and were not
changed: `in_corpus`, `newer_edition`, `older_edition_only` («в корпусе только более ранняя
редакция»), `not_in_corpus`, `not_recognised`. The task text listed «ambiguous» as the fifth; the
integrator confirmed that was a slip and the resolver's set stands (no sixth outcome). The UI
explains `older_edition_only` as an out-of-date corpus, not a project error.

**Facade grant.** Two additive export-only commits touch `src/auditmanager/norms/public.py`
(`4c2b816e`) and `src/auditmanager/runs/public.py` (`073b3c0c`), which are not in the task's
`allowed_paths`; the integrator granted them by message for this task (ALR-05: `runs` reaches
`norms` only through `norms.public`).

## Phase A checks

| Command | Result |
| --- | --- |
| container-free: `tests/unit/norms`, the existing reference suites, `tests/integration/runs/test_reference_*`, `tests/contract/architecture` | 357 passed |
| DB integration, own containers (postgres 57680): `tests/integration/norms/references/test_snapshot_catalogue_db.py` | 14 passed (stack down again) |
| `git diff --check` | clean |

The DB test inserts the snapshot's documents in the reverse of their identity order (the identity
is time-ordered, so call order would hide an `ORDER BY` mutation), reads at page sizes
1, 2, 3, 7, 8, 9 and 500, proves the database's generated tokens equal the Python twin (including
a Latin `C` and `P` inside a Cyrillic word), refuses a count mismatch in both directions and an
absent snapshot, and runs the read in a `READ ONLY` transaction.

## Mutation proofs

Each row is one quoted mutation of a committed file, applied alone, the focused container-free
tests run, the file restored. 31 of 32 are killed; the survivor is equivalent (below).

| # | File | Mutation | Quoted change | Result | Killed by |
| --- | --- | --- | --- | --- | --- |
| 1 | `resolution.py` | newer edition no longer wins over the cited edition being present | `if newer: selected = min(newer, key=lambda pair: (-pair[0].edition, pair[1].document_id)) return NEWER, selec…` → `if newer and not any(d.edition == cited.edition for d, _ in candidates): selected = min(newer, key=lambda pai…` | killed | `test_the_recorded_text_resolves_to_all_five_outcomes_with_counts` |
| 2 | `resolution.py` | the OLDEST newer edition is chosen instead of the newest | `key=lambda pair: (-pair[0].edition, pair[1].document_id)) return NEWER` → `key=lambda pair: (pair[0].edition, pair[1].document_id)) return NEWER` | killed | `test_a_cited_amendment_is_answered_by_the_newest_newer_base_edition` |
| 3 | `resolution.py` | plain citation: oldest newer edition (second branch) | `if newer: selected = min(newer, key=lambda pair: (-pair[0].edition, pair[1].document_id))` → `if newer: selected = min(newer, key=lambda pair: (pair[0].edition, pair[1].document_id))` | killed | `test_the_recorded_text_resolves_to_all_five_outcomes_with_counts` |
| 4 | `families.py` | an amendment is parsed as an edition (amendment_number dropped) | `replace(base, amendment_number=int(amendment.group(1)), display=head.replace("_", " "))` → `replace(base, amendment_number=None, display=head.replace("_", " "))` | killed | `test_an_amendment_that_sorts_before_its_base_is_still_not_the_match` |
| 5 | `resolution.py` | amendment documents are offered to a plain citation (both amendment filters removed) | `if designation.amendment_number is None or cited.amendment_number is not None ] ⟶ candidates = [(designation,…` → `if True ] ⟶ if not candidates:` | killed | `test_an_amendment_that_sorts_before_its_base_is_still_not_the_match` |
| 6 | `resolution.py` | amendment documents compete as editions of the base (second filter removed) | `candidates = [(designation, doc) for designation, doc in candidates if designation.amendment_number is None] …` → `if not candidates:` | survived (equivalent) | `114 passed`; the first filter (#5) already removes amendments from a plain citation, so the second filter is defence in depth, and removing both is killed |
| 7 | `resolution.py` | the reverse word order of a federal law is not extracted | `r"(?:\d+[ _-]*фз|фз[ _-]*\d+)"` → `r"(?:\d+[ _-]*фз)"` | killed | `test_a_federal_law_in_every_word_order_is_one_citation_with_every_page` |
| 8 | `resolution.py` | the long form of a government act is not extracted | `(?:пп[ _]+рф|постановление[ _]+правительства[ _]+рф)` → `(?:пп[ _]+рф)` | killed | `test_a_government_act_in_both_forms_is_one_citation` |
| 9 | `resolution.py` | eleven occurrences are retained instead of ten | `MAX_EVIDENCE_OCCURRENCES = 10` → `MAX_EVIDENCE_OCCURRENCES = 11` | killed | `test_at_most_ten_anchors_are_kept_in_reading_order_and_the_count_is_true` |
| 10 | `read_model.py` | an empty page is read as empty text instead of unread | `TextPage(str(number), pages[number] or None)` → `TextPage(str(number), pages[number])` | killed | `test_the_recorded_text_resolves_to_all_five_outcomes_with_counts` |
| 11 | `read_model.py` | counts omit an outcome with no citation | `counts = {code: 0 for code in OUTCOME_ORDER}` → `counts = {code: 0 for code in OUTCOME_ORDER if code != 'older_edition_only'}` | killed | `test_the_recorded_text_resolves_to_all_five_outcomes_with_counts` |
| 12 | `read_model.py` | older_edition_only is reported as in_corpus | `OLDER: OLDER_EDITION_ONLY,` → `OLDER: IN_CORPUS,` | killed | `test_the_recorded_text_resolves_to_all_five_outcomes_with_counts` |
| 13 | `read_model.py` | the occurrence count is the number of kept anchors, not the true count | `occurrence_count=reference.total_occurrences,` → `occurrence_count=len(occurrences),` | killed | `test_at_most_ten_anchors_are_kept_in_reading_order_and_the_count_is_true` |
| 14 | `read_model.py` | the unrecognised list names the parseable documents | `if doc.slug in unparsed` → `if doc.slug not in unparsed` | killed | `test_the_unparsed_catalogue_slugs_are_listed_with_what_the_reader_sees` |
| 15 | `read_model.py` | the citation cap is off by one | `if len(report.references) > MAX_CITED_NORMS:` → `if len(report.references) >= MAX_CITED_NORMS:` | killed | `test_more_distinct_citations_than_the_cap_are_refused_not_cut` |
| 16 | `read_model.py` | the match/outcome consistency check is removed | `if (matched is None) != (reference.outcome in _NOT_MATCHED) or (` → `if False or (` | killed | `test_a_self_contradicting_resolver_answer_is_refused[absent-with-match]` |
| 17 | `read_model.py` | the unknown-outcome check is removed | `if code is None: raise ReferenceRefused("the resolver answered an unknown outcome")` → `if code is None: code = IN_CORPUS` | killed | `test_a_self_contradicting_resolver_answer_is_refused[unknown-outcome]` |
| 18 | `read_model.py` | the occurrence sanity check is removed | `if ( not occurrences or len(occurrences) > MAX_EVIDENCE_OCCURRENCES or reference.total_occurrences < len(occu…` → `if False:` | killed | `test_a_self_contradicting_resolver_answer_is_refused[no-occurrence]` |
| 19 | `snapshot_catalogue.py` | the keyset is inclusive | `norm_document_id COLLATE "C" > :after` → `norm_document_id COLLATE "C" >= :after` | killed | `test_the_statements_are_select_only_keyset_and_bounded` |
| 20 | `snapshot_catalogue.py` | a snapshot storing fewer documents than declared is accepted | `if len(entries) != declared_count:` → `if False:` | killed | `test_inconsistent_rows_are_refused_not_repaired[rows0-2-fewer]` |
| 21 | `snapshot_catalogue.py` | a snapshot storing more documents than declared is accepted | `if len(entries) >= declared_count:` → `if False:` | killed | `test_inconsistent_rows_are_refused_not_repaired[rows1-1-more]` |
| 22 | `snapshot_catalogue.py` | no slug is ever listed as unparsed | `if parse_designation(entry.slug) is None:` → `if False:` | killed | `test_the_recorded_text_resolves_to_all_five_outcomes_with_counts` |
| 23 | `snapshot_catalogue.py` | a duplicate document id passes the order check | `entry.document_id <= previous` → `entry.document_id < previous` | killed | `test_inconsistent_rows_are_refused_not_repaired[rows4-2-canonical order]` |
| 24 | `snapshot_catalogue.py` | the page-size bound is removed | `if type(page_size) is not int or not 1 <= page_size <= SNAPSHOT_PAGE_SIZE:` → `if False:` | killed | `test_an_unusable_page_size_is_refused_before_any_read[0]` |
| 25 | `snapshot_catalogue.py` | an absent snapshot is read as an empty one | `if declared is None: raise ReferenceRefused("pinned snapshot is absent")` → `if declared is None: declared = 1` | killed | `test_an_absent_snapshot_is_refused_before_any_document_is_read` |
| 26 | `reference_pipeline.py` | a run with no pinned snapshot reads on instead of saying so | `if run.norms_snapshot_id is None: return replace(answer, state=STATE_SNAPSHOT_NOT_PINNED)` → `` | killed | `test_a_run_that_pinned_no_snapshot_says_so_and_reads_neither_text_nor_snapshot` |
| 27 | `reference_pipeline.py` | a missing text layer is read as all-empty pages | `if supplied is None: return replace(answer, state=STATE_TEXT_UNAVAILABLE)` → `if supplied is None: supplied = SavedRunPageText(run.run_id, 'a' * 64, {n: '' for n in range(1, version.page_…` | killed | `test_a_run_without_a_saved_text_layer_says_so_and_reads_no_snapshot` |
| 28 | `reference_pipeline.py` | another run's text is accepted | `or text_layer.run_id != run_id` → `or False` | killed | `test_a_saved_text_that_does_not_match_the_run_is_an_internal_error[answer0]` |
| 29 | `reference_pipeline.py` | a refused catalogue becomes text_unavailable | `raise _integrity("the run's norm references cannot be bound to its pinned snapshot") from exc` → `return replace(answer, state=STATE_TEXT_UNAVAILABLE)` | killed | `test_a_pinned_snapshot_that_cannot_be_read_whole_is_an_internal_error[snapshot-absent]` |
| 30 | `reference_pipeline.py` | too many citations is no longer its own state | `except TooManyCitations:` → `except ZeroDivisionError:` | killed | `test_too_many_distinct_citations_is_an_explicit_state_not_a_cut_list` |
| 31 | `reference_pipeline.py` | a version of another project is accepted | `or str(version.project_uid) != run.project_uid` → `or False` | killed | `test_a_version_that_is_not_the_runs_is_an_internal_error[changes1]` |
| 32 | `reference_pipeline.py` | a storage error from the reader is reported as 'no text layer' | `supplied = reader.saved_page_text( session, run_id=run.run_id, version_uid=run.version_uid, page_count=versio…` → `try: supplied = reader.saved_page_text( session, run_id=run.run_id, version_uid=run.version_uid, page_count=v…` | killed | `test_a_storage_integrity_error_from_the_reader_passes_through_unchanged` |

Database-level mutations of `snapshot_catalogue.py`, run against the DB test: the keyset made
inclusive, the snapshot filter removed, the `ORDER BY` removed and the `LIMIT` removed are each
killed (`test_every_page_size_reads_the_same_snapshot_in_catalogue_order[1]`,
`test_the_read_runs_in_a_read_only_transaction_and_sends_selects_only`). Replacing `COLLATE "C"` by
the database collation survives, and is equivalent: a document id is `ndoc_` plus uppercase Crockford
base32, which every collation orders alike; the clause is kept because every other snapshot reader
uses it.

## Phase B

### The operation

`GET /runs/{run_id}/norm-references`, `getRunNormReferences`, tag `runs`, any one role
(`role:admin|expert`, like `getRunStatus`); responses 200 `RunNormReferences` and the 401, 403, 404,
500 and 503 envelope, no 422 (a malformed run identity is `404` by design). Surface: **73 paths / 83 operations / 242 schemas**, which is
`CLASSIFICATION-CORRECTION-01`'s 72/82/237 plus this task's +1 / +1 / +5. No error code, no
migration (`UPGRADE_SURFACE_DIGESTS[0028]` untouched), `contract_version` unchanged.

Five schemas: `RunNormReferences`, `NormReferenceCounts`, `NormReferenceItem`, `NormReferenceAnchor`,
`NormReferenceUnrecognised`. The state and the outcome are inline closed sets, not component schemas.
Optional properties are absent, never `null` (`exclude_unset` at the router). The page numbers are
bounded by the ingest envelope's 500 pages, a cited text by 300 characters, the list by 1000 distinct
citations; a text over a bound is the state `too_many_citations`, never a cut list.

### Changed files (phase B)

- API: `api/schemas/models.py` (five models), `api/routers/runs.py` (the route), `api/routers/ports.py`
  (`RunPort.get_run_norm_references`), `api/security.py` (role register), `bootstrap/adapters.py`
  (`RunAdapter.get_run_norm_references`, `_RunSavedText`, `_norm_references_view`).
- Contract: `contracts/api/v1/openapi.json` and `web/openapi/openapi.json` (byte-identical; the new
  entries are spliced into the existing text, not re-dumped, so no untouched byte moved),
  `web/src/shared/api/generated/*` (regenerated, `api:verify` OK), `web/FRONTEND_LOCK.json` (digests,
  counts, content commit `c90d52f3`), `tests/support/expected_facts.json`.
- Surface prose re-measured (the guard names each line): `ALPHA_ROADMAP.md`, `P02_SEAMS.md` (narrative,
  table row, count), `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`, `api/{README.md,app.py,
  health.py}`, `api/routers/{__init__,declarations,errors}.py`, the BFF route handler and
  `shared/api/authorization.ts`; the `_drop_the_422...` narrative gains the operation in the
  «cannot» group (fifteen). The mutation lines of `test_surface_counts_in_prose.py` moved with it.
- Tests: `test_openapi_conformance.py` (dangling references 56 -> 57), `test_openapi_document.py`
  (required operations), `test_authorization.py`, `test_role_register.py`, the absent-parent sweep
  (`EXPECTED_ADDRESSED` 30 -> 31), the stand-in `RunPort` in `tests/integration/api/conftest.py`, and
  new `tests/integration/api/test_norm_references_surface.py` (container-free: the operation and its
  role, the wire bodies evaluated by the real Draft 2020-12 validator, null/extra/sixth-outcome
  refusals shown to fail, the saved-text port).
- Web: `entities/norm-reference`, `widgets/norm-references`, the mount in `widgets/run-progress`
  (terminal runs only), `queryKeys.runs.normReferences`, `web/docs/PC01_UI_SEAM.md`, the
  rendered-language guard cases, the contrast-census screens, and `web/tests/unit/norm-references/*`.

### Web section

«Нормативные ссылки» ends the progress widget of a stopped run (`published`, `partial`, `failed`,
`cancelled`); an in-flight run does not carry it, because its text layer may not exist yet. It shows
the five counts, a table (citation as written, outcome, pages with «и ещё N» when the server kept ten
of more, the matched norm and «Открыть норму» pointing at `/norms/document?id=...`), the pages with no
text layer, a legend that explains «в корпусе только более ранняя редакция» as a stale corpus and not a
project error, and the corpus documents whose designation the parser cannot read. A state that stops
the list is one sentence.

### Not done in this lane, and why

- `docs/program/CURRENT_STATE.md` still states 71/81/235; it is the integrator's, and
  `test_doc_prose_facts.py::test_the_scanned_docs_state_the_contract_surface_this_tree_has` is red on
  exactly that line until it moves.
- No end-to-end run over HTTP with MinIO: `R-126` keeps database suites off the private lane, and a
  recorded pipeline run would need a designated snapshot, which cannot be unset. The composition is
  covered by the real-row PostgreSQL suite below, the port wrapper test and the wire-level validator
  test; the live journey does not call this operation.
- `tests/contract/test_cp00_candidate.py`, `test_cp00_final_state.py` and `test_validate_bootstrap.py`
  are ignored by every official target and are red in this lane for reasons that predate it (a frozen
  stage-registry digest; no `jsonschema` in the runtime interpreter).

## Re-derivation on top of the correction slice

`CLASSIFICATION-CORRECTION-01` merged first. The merge of `origin/dev` conflicted in the contract and
its mirror, the generated client, the frontend lock, three prose-bearing sources, the roadmap triple
and two contract tests. None was hand-merged:

- the contract, its mirror and the generated client took the correction slice's text; my five
  schemas and the path were spliced on top again (`73 / 242`, byte-identical copies), the client
  regenerated (`api:generate`, `api:verify` OK, 83 operations);
- the frontend lock's digests, counts and content commit (`c9469558`) were recomputed, and the
  expected facts re-derived (nothing to add: the auto-merge was right);
- every surface-count prose line was re-measured by the guard's own list (73 paths, 83 operations,
  242 schemas); the 422 narrative in `api/app.py` now names both slices (`Sixty-one` operations with
  their own 422, `Fifteen` that cannot); the two mutation lines of `test_surface_counts_in_prose.py`
  and the dangling-reference count (now 58: both slices add one) follow the new numbers;
- the host's disk reached 0 MiB during one `npm ci`; I deleted `web/node_modules` and installed again
  from scratch, regenerated, and confirmed the lock digests did not move.

## Final checks (on the merged, committed tree)

| Command | Result |
| --- | --- |
| `npm --prefix web ci` (twice, the first lost to the full disk), `api:verify` | OK, 83 operations |
| `typecheck`, `lint --quiet` | clean |
| `vitest run tests/unit/styles tests/unit/norm-references tests/unit/screens tests/unit/sections tests/guards tests/contract` | 925 passed in 53 files |
| `pytest tests/contract`, three official `--ignore` flags | 940 passed, 1 failed: `test_doc_prose_facts` reads `docs/program/CURRENT_STATE.md` at 72/82/237; that file is the integrator's and moves to 73/83/242 on integration |
| container-free: `test_norm_references_surface.py`, `tests/unit/norms/references`, `tests/integration/runs/test_reference_norm_references*.py` | 123 passed |
| PostgreSQL on my own containers at migration head `0028`: `test_reference_norm_references_db.py`, `test_snapshot_catalogue_db.py`, `test_role_register.py`, `test_authorization.py` | 81 passed |
| same containers: the absent-parent sweep, port completeness, router answers, served document and health plane | 61 passed, 1 skipped (the sweep drives the new route to `404 not_found` for an absent run; `EXPECTED_ADDRESSED` stays 31 because the correction operation is a write) |

The stack was brought up once, then `make down` and both lane volumes removed.

## Phase B mutation proofs

Each row is one quoted mutation of a committed file, applied alone, the focused tests run, the file
restored. All nine are killed.

| # | File | Mutation | Killed by |
| --- | --- | --- | --- |
| 1 | `api/routers/runs.py` | `answer.model_dump(mode="json", exclude_unset=True)` -> `answer.model_dump(mode="json")` | `test_norm_references_surface.py`: a non-ready answer would carry `null` properties |
| 2 | `bootstrap/adapters.py` | `if item.matched_title is not None: shown["matched_title"] = ...` -> unconditional assignment | `test_a_ready_answer_carries_every_property_and_validates` |
| 3 | `api/security.py` | `"getRunNormReferences": _ANY_ROLE` -> `_EXPERT` | `test_the_operation_is_served_for_any_one_role_and_declares_no_422` |
| 4 | `contracts/api/v1/openapi.json` | property `unread_pages` renamed in the contract only | `test_openapi_conformance_live.py`: the served document disagrees with the contract |
| 5 | `entities/norm-reference/model/presentation.ts` | `not_in_corpus: 'нет в корпусе'` -> `'not in the corpus'` | the rendered-language guard (R-18) and the labels test |
| 6 | `widgets/run-progress/ui/run-progress.tsx` | `isTerminalRunState(status.state) ? <NormReferencesSection/> : null` -> always | `run-progress-mount.test.ts`: a created run does not carry the section |
| 7 | `entities/norm-reference/model/presentation.ts` | `const hidden = occurrenceCount - anchors.length;` -> `0` | the places test («и ещё N») |
| 8 | `widgets/norm-references/ui/norm-references-answer.tsx` | `routes.normDocument(documentId)` -> a fixed id | the row test: the link points at the matched norm only |
| 9 | `tests/unit/styles/screens.ts` | the census no longer renders `NormReferencesAnswer` | `contrast.test.ts`: names the unreached colour-bearing rules |
