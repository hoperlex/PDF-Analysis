# SECTION-READ-MODEL-01 — the dashboard and the section Form-7 view read the confirmed classification

Task: `docs/program/tasks/SECTION-READ-MODEL-01.md`. Branch `agent/section-read-model-01`, base
`59f976fc` (`origin/dev` plus the task files). Code commit `84f5a5f3`. No wire, schema, migration,
contract or reseal change: the surface stays 71 paths / 81 operations / 235 schemas, 25 error codes,
migration head `0027_optimisation_proposals`.

## What changed

### 1. Dashboard section breakdown (`src/auditmanager/dashboard/repository.py`)

`_DOCUMENTS_BY_SECTION` now counts each document that has a published current version in the section
its **current version** is confirmed in:

```sql
SELECT c.section_code, count(*)
FROM document d JOIN document_version v ON v.version_uid = d.current_version_uid
LEFT JOIN document_version_classification c ON c.version_uid = v.version_uid
GROUP BY c.section_code
```

* `document.current_version_uid` selects the version (`W59-SECTION-IDENTITY-DECISION-01`); that
  version's own `document_version_classification` row is the confirmation.
* The `LEFT JOIN` is the unclassified rule: a current version nobody classified has no row, its
  `section_code` is NULL, and it falls into the existing NULL group, which the response already
  renders as the trailing «без раздела» bucket (`section` absent, `document_count` present).
* The legacy `document.section` is no longer read by the dashboard at all. An older version's
  classification never counts for a set whose head moved on.
* Every output key and shape is unchanged: fifteen section rows in `PROJECT_SECTIONS` order, then the
  unclassified bucket, always present, even at zero. `documents_by_project`, verdicts, run activity
  and spend are untouched.

**What the wire can carry (decision requested by the brief).** The wire already carries fifteen
sections. `api.schemas.models.ProjectSection` lists AR, AI, KM, KJ, OV, EOM, VK, PT, PB, SS, ITP, GP,
TX, POS and **PS** (`W59-SECTION-SEAL-01`); `SectionDocumentCount.section` is that enum; the dashboard
vocabulary `PROJECT_SECTIONS` already has PS as its fifteenth member; and the database admits exactly
those fifteen codes in `ck_document_version_classification_section_code`. A confirmed PS is therefore
counted in its own row and needs no folding. Prose in older documents that still says «fourteen» was
not edited (non-goal).

**A code the vocabulary does not list.** `_filled` only reads members of the vocabulary, so a code
outside it would have been dropped and the breakdown would quietly have added up to fewer documents
than exist. The database CHECK makes this unreachable today; it becomes reachable only if a sixteenth
code is added to the table's CHECK without being added to the dashboard. That case now raises
`DomainError(INTERNAL_ERROR)` instead of under-counting. No silent fallback (AGENTS.md section 4).

### 2. Documents context and `section_specification`

`src/auditmanager/documents/**` gains, on `DocumentRepository` and in `documents.public`:

* `CurrentVersionPlacementRecord` — project (uid, name), document, display title, version, ordinal,
  page count, and `project_stage` / `section_code` (both set, or both `None` while unclassified). No
  manifest, no blob handle, no filename.
* `list_current_versions_in_section(session, *, section_code, project_uid=None, after=None, limit)` —
  the document sets whose **current** version is confirmed in the section: one statement, inner join
  on `document_version_classification` of `current_version_uid`.
* `list_unclassified_current_versions(session, *, project_uid=None, after=None, limit)` — the
  complement (`LEFT JOIN ... WHERE c.version_uid IS NULL`). The module needs it because its answer
  also lists unclassified current versions under `excluded`; the brief named only the first query.
* `count_projects(session)` — `SELECT count(*) FROM project`, so the module keeps its
  `projects` cap without listing the projects.
* Both list queries are keyset-paged on `document_uid` (the primary key of `document`, one current
  version per document), at most `MAX_PLACEMENT_PAGE` = 1000 per page; `limit` outside `1..1000`, a
  bool or a non-int is `validation_failed` (field `limit`). The optional project and page filters are
  `CAST(:x AS text) IS NULL OR ...` in one statement, as `decisions` and `access` already do.

`src/auditmanager/optimisation/section_specification.py` now builds membership from these two queries
instead of one `list_documents` per project (up to 1000):

* members: pages of 500 until a short page; sorted in Python by `(project name casefold, project uid,
  title casefold, document uid)`, which is exactly the order the old per-project loop produced;
* exclusions: the unclassified walk counts every set (`excluded_count` stays complete) and keeps only
  the first `MAX_LISTED_EXCLUDED` in the same order, so memory is bounded however many sets are
  unclassified. The sort stays in Python because `casefold` is not PostgreSQL's `lower()`;
* every cap and every state is unchanged: `MAX_SCANNED_PROJECTS` (now `count_projects()` against it,
  unfiltered reads only), `MAX_SECTION_SOURCES`, `MAX_SECTION_ROWS`, `MAX_LISTED_EXCLUDED`,
  `MAX_QUERY_LENGTH`, the project filter (`not_found` `Project` for an unknown one), the answer order;
* the port contradicting itself is `internal_error`, as before: a "member" in another section or
  without a stage, a set of another project under a named project, an "unclassified" set that carries
  a classification, and a page that does not advance past its key (which would otherwise loop for
  ever).

Two integrity checks of the old loop are gone because the join makes them impossible: "a
classification is attached to another version" and, for the unfiltered case, "a listed version belongs
to another project".

### 3. Web (`web/src/features/upload-price-list/model/use-upload-price-list.ts`)

`onSuccess` gains one invalidation: `['optimisation', 'section-specification']`, the prefix of every
`queryKeys.optimisation.sectionSpecification(...)` key (all sections, project filters, searches,
pages). The key factory lives in `web/src/shared/api/query-keys.ts`, outside the allowed paths, and
offers no prefix, so the prefix is a module-private constant with a comment, and
`web/tests/unit/optimisation/commands.test.ts` pins both the invalidation list and that the constant is
a `partialMatchKey` prefix of keys built by the factory for three sections and filter shapes (and of
no price-list or vendor-list key). A renamed key can therefore not silently stop being invalidated.

## Tests added or changed

| File | What it holds |
| --- | --- |
| `tests/integration/documents/test_current_version_placement.py` (new, real PostgreSQL) | the join on rows: older-version confirmation ignored, legacy `document.section` ignored (also when it disagrees with the confirmation), headless set absent, head move moves membership, PS, project with several sets across sections, project filter and unknown project, keyset walk without repeats, page-size bounds, `count_projects` |
| `tests/integration/documents/seeding.py` (new) | row builder shared by the two new suites |
| `tests/integration/dashboard/test_section_breakdown.py` (new, real PostgreSQL + one container-free) | empty deployment (fifteen zeros plus the bucket last), counting by the current version, unclassified bucket whatever the legacy label or an older version says, head move, headless set, breakdown total equals `documents_by_project` total, unknown code refused (stub session) |
| `tests/unit/optimisation/test_section_specification.py` | stand-in rebuilt on the two new queries; two contradiction cases rewritten; new: project with several sets across sections, two-query membership with project filter, multi-page walk equals one page, exclusion listing keeps the first N across pages, non-advancing page refused |
| `tests/integration/optimisation/test_section_specification.py` | new: a project with several sets across sections on real rows, page-by-page membership equals one page |
| `web/tests/unit/optimisation/commands.test.ts` | the invalidation list and the prefix drift guard |

## Commands run and results

Lane: `foundation_instance auditmanager-section-read-model`, postgres 57640, s3 61240/61241, db
`auditmanager_section_read_model`, bucket `auditmanager-section-read-model`; `.env` from `.env.example`
with both sides agreeing; `make up` (0), `make migrate` to `0027_optimisation_proposals` (0). Available
memory was 4234 MiB and `/` had 7265 MiB free at launch; the stack was brought up only after the
unit and web work was done. Commands are `$PY -m pytest -c pyproject.toml --rootdir=. -q
-p no:cacheprovider <paths>` with `PY=.local/worktrees/w55b-main-candidate/.venv/bin/python`.

| # | Command (paths after the common prefix) | Result |
| --- | --- | --- |
| 1 | `tests/unit/optimisation/test_section_specification.py` (no containers) | 31 passed, exit 0 |
| 2 | `tests/integration/documents tests/integration/dashboard` (lane PostgreSQL) | 25 passed, exit 0 |
| 3 | `tests/integration/optimisation/test_section_specification.py tests/integration/composition/test_section_specification_over_http.py` (lane PostgreSQL + MinIO) | 22 passed, exit 0 |
| 4 | `tests/integration/ingest/test_project_document_count.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` | 15 passed, exit 0 |
| 5 | `tests/contract/domain_p02/test_project_section_catalog.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/api_v1/test_doc_prose_facts.py` | 85 passed, exit 0 |
| 6 | `tests/contract/program` | 28 passed, exit 0 |
| 7 | `npm --prefix web run lint -- --quiet` | exit 0 |
| 8 | `npm --prefix web run typecheck` | exit 0 |
| 9 | `npm --prefix web test -- --run tests/unit/optimisation tests/guards/dashboard-invalidation.guard.test.ts` | 9 files, 118 tests passed, exit 0 |
| 10 | `git diff --check 59f976fc` | exit 0 |
| 11 | `tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py` before the repair | 1 failed (`..._known_data_reports_the_exact_counts`), 3 passed — see Deferred |
| 12 | the same file with the quoted repair applied (then reverted) | 4 passed |
| 13 | `tests/integration/composition/test_every_port_implementation_is_whole.py` | 1 failed (`test_pre_decide_adapter...`); the same test fails on an extract of base `59f976fc` |

Runs 1–6 and 10 were made on the final tree with this report in place; only this results table was
added to the report afterwards, and run 5 (the prose guards) was repeated after that edit. After the
last run the stack was taken down with `make down` and the lane's volumes removed.

## Mutation proofs (each new guard shown failing)

Every mutation below was applied to the committed tree one at a time (exact text replacement, asserted
to match once), the named suite run, and the file restored; all were killed (the working tree was
clean afterwards). The quoted text is the mutated line.

| # | Mutation (old → new) | Killed by |
| --- | --- | --- |
| U1 | `if item.section_code != section or item.project_stage is None:` → `if False:` | `test_contradictory_answers_are_internal_errors` |
| U2 | the `_checked_member` project check removed | `test_contradictory_answers_are_internal_errors` |
| U3 | `if item.section_code is not None or item.project_stage is not None:` → `if False:` | `test_contradictory_answers_are_internal_errors` |
| U4 | `if after is not None and str(page[0].document_uid) <= str(after):` → `if False:` | `test_a_projection_that_ignores_its_page_key_is_an_internal_error` |
| U5 | `if len(page) < _MEMBERSHIP_PAGE: return` → unconditional `return` (walk stops after page one) | `test_a_walk_over_many_pages_answers_what_one_page_answers`, `test_the_exclusion_listing_keeps_the_first_in_answer_order_across_pages` |
| U6 | the exclusion `sorted(..., key=_listing_order)[:MAX_LISTED_EXCLUDED]` → unsorted slice | `test_the_exclusion_listing_keeps_the_first_in_answer_order_across_pages`, `test_the_exclusion_listing_is_capped_and_its_count_complete` |
| U7 | `unclassified_count += len(page)` → `= len(page)` | the same two walk tests |
| U8 | `project_uid=project_uid` → `project_uid=None` in the members query | `test_membership_is_two_documents_queries_and_names_the_project_filter` and five more |
| U9 | members grouped without sorting | `test_members_are_current_versions_confirmed_in_the_section_in_name_order` and five more |
| U10 | `elif documents.count_projects(session) > MAX_SCANNED_PROJECTS:` → `elif False:` | `test_too_many_projects_is_explicit_and_scans_nothing` |
| D1 | `WHERE c.section_code = :section_code` → `WHERE d.section = :section_code` | six tests in `test_current_version_placement.py` |
| D2 | classification joined on `IN (any version of the set)` instead of the current one | `test_an_older_versions_confirmation_never_makes_a_set_a_member` and five more |
| D3 | `WHERE c.version_uid IS NULL` → `WHERE true` | `test_the_unclassified_sets_are_the_complement` and two more |
| D4 | `d.document_uid > CAST(:after ...)` → `>=` | `test_pages_are_keyset_ordered_complete_and_never_repeat` |
| D5 | the `1 <= limit <= MAX_PLACEMENT_PAGE` check → `if False:` | `test_the_page_size_is_bounded[0/-1/1001]` |
| D6 | `"project_uid": ... str(project_uid)` → `None` | the project-filter tests |
| B1 | dashboard `SELECT c.section_code ... GROUP BY c.section_code` → `d.section` (the legacy label) | four tests in `test_section_breakdown.py` |
| B2 | dashboard `LEFT JOIN` → `JOIN` (unclassified dropped) | `test_unclassified_current_versions_go_to_the_bucket_...`, `test_the_breakdown_adds_up_to_...` |
| B3 | dashboard classification joined on any version of the set | three tests |
| B4 | the unknown-code guard → `if False:` | `test_a_confirmed_code_missing_from_the_vocabulary_is_refused_not_dropped` |
| O1 | integration: walk stops after one page | `test_reading_the_membership_page_by_page_answers_what_one_page_answers` |
| W1 | the `invalidateQueries({ queryKey: SECTION_SPECIFICATION_KEY_PREFIX })` line deleted | both new vitest cases |
| W2 | prefix literal `'section-specification'` → `'section-spec'` | both new vitest cases |

## Failure, idempotency and security cases

* **Read-only.** Every new statement is a SELECT; nothing is written, no new table, no lock. The
  existing `test_the_read_writes_nothing` still passes.
* **Failure.** A port that contradicts itself, or does not advance its page, is `internal_error`
  (U1–U4). A bad `limit` is `validation_failed` (D5). An unknown project filter is `not_found` in the
  module (unchanged) and an empty answer in the repository. An unrecognised section code matches
  nothing. A dashboard code outside the vocabulary is `internal_error` (B4).
* **Idempotency.** Both queries are deterministic for a given database state (`ORDER BY document_uid`).
  `test_the_answer_is_deterministic` still holds.
* **Security.** Roles are untouched: any one role still reads (`R-80`). The records carry no filename,
  bucket, key or blob handle. No dynamic SQL: the section code and the optional filters are bound
  parameters.

## Deferred checks and what this report does not claim

* No full `make gate`, no live journey, no whole contract battery (R-135).
* `tests/integration/composition/test_dashboard_summary_over_a_fresh_deployment.py` is **outside the
  allowed paths and now fails** on `test_a_deployment_with_known_data_reports_the_exact_counts`: its
  helper `_seed_published_document` writes only the legacy `document.section`, which the dashboard no
  longer reads, so the seeded 1..15 counts all land in the unclassified bucket. It was not edited.
  The minimal repair (verified: that file then gives 4 passed; reverted afterwards) is one block in
  `_seed_published_document`, after the `UPDATE document SET current_version_uid` statement:

  ```python
        if section is not None:
            connection.execute(
                text(
                    "INSERT INTO document_version_classification "
                    "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
                    "VALUES (:v, 'R', :sec, (SELECT user_uid FROM app_user ORDER BY user_uid LIMIT 1))"
                ),
                {"v": version_uid, "sec": section},
            )
  ```

  (the `token` fixture creates the expert before any seeding, so `app_user` has a row). The integrator
  needs a grant for that path, or applies it.
* `tests/integration/composition/test_every_port_implementation_is_whole.py` has one failing test
  (`test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it`, `DecisionAdapter(None)`
  `TypeError`) that fails identically on the base tree `59f976fc`; it does not touch this change.
* The stale `staleTime: 0` workaround in `web/src/entities/section-specification/api/use-section-specification.ts`
  and its comment in `query-keys.ts` were left as they are (outside the allowed paths). With the upload
  now invalidating the view they could be retired, together with a `sectionSpecificationAll` prefix
  factory that would replace the module-private constant here. Not done, not needed for correctness.
* The live browser journey was not run: the web change is one invalidation call.

## Risks and known limitations

1. **The dashboard's section panel will read «без раздела» for everything until experts classify.**
   `0024_version_classification` deliberately backfills nothing, so on a deployment that predates the
   classification table every existing document is unclassified under the new rule, however its legacy
   `document.section` reads. That is the intended effect of the task (the legacy label is not a
   confirmation), but it is visible to users the day this ships.
2. **Two statements, one request, no shared snapshot.** Members and the unclassified walk are separate
   queries under READ COMMITTED. A set classified between them can be absent from both lists for that
   one response. The old per-project loop had the same window per project; a repeatable-read session
   would close it and is not in this task.
3. **The unclassified walk reads every unclassified current version** (narrow rows, 500 per query) to
   count them and keep the first 200 in casefold order. Before it also loaded every manifest of every
   project; it is cheaper, but not constant. If the unclassified population grows into tens of
   thousands, count in SQL and fetch only the ordered head.
4. **`MAX_SCANNED_PROJECTS` is now a vestige.** It was set when membership cost one query per project.
   It is kept because `limit_reason: projects` is a frozen wire value and the brief says caps stay;
   retiring it is a wire decision for the owner.
5. **No index on `section_code`.** The members query filters `document_version_classification` by
   section (a small table, one row per classified version); the migration is out of scope and the
   planner uses the primary key for the join.

## Instructions to the integrator

1. Merge `agent/section-read-model-01` into `integration/night-1020` as a real merge; nothing else is
   needed from contracts, migrations or the composition root.
2. Decide the composition test above (grant the path or apply the quoted block) before any gate
   measures the dashboard.
3. Hotspot proof: the diff against `59f976fc` touches only the allowed paths of the task
   (`git diff --name-only 59f976fc..HEAD`), and none of `contracts/**`, `db/migrations/**`,
   `src/auditmanager/bootstrap/**`, `src/auditmanager/api/**`, other `src/**`, `tests/support/**`,
   dependency files, `CURRENT_STATE.md`, refs, tags or the stand.
