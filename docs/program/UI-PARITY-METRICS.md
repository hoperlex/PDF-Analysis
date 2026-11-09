# UI-PARITY-METRICS — the counters of documents, projects and sections

Contract `1.19.0` (`UI-PARITY-P0B`). This is the dictionary of the figures the P0b slice implements: what each counts, its
formula, the rule that picks the run it reads, its edge cases and the owner ruling that decided it. The rulings are
`R-150n` … `R-150u` (`OWNER_RULINGS_2026-09-17.md` §3.50; the lane resumed under `R-150v`). Where this file goes beyond a
ruling the sentence is marked **proposed, not ruled** and is open to the owner. The working analysis behind the rulings
(`Q-MD-1` … `Q-MD-21`) is a host-local draft and is not restated here; its unanswered questions stay in `D-303`.

The code is one read model, `src/auditmanager/dashboard/audit_state.py`: one SQL statement grouped in the database, one pure
function (`audit_state`) that classifies, and the tallies of it. `listProjects`, the section panel and the findings tile of
`getDashboardSummary` are all tallies of that statement, so the numbers agree by construction.

## 1. The counted object and the result run

| Term | Definition | Ruling |
| --- | --- | --- |
| Counted object | A document, through its **current version only** (`document.current_version_uid`). The join is the one `listProjects.document_count` counts through; a document with no current version is counted nowhere. An older version never counts: uploading V2 moves a fully checked V1 document to `not_run` until V2 is run. | `R-150p` |
| Run of a version | An `audit_run` row of that version, whatever its state. | — |
| Result run | The **latest** run of the version in state `published` or `partial`, ordered by `(created_at, run_id)` descending, the order `listRuns` returns. A newer run still in flight (`created`, `queued`, `running`, `validating`) does not displace it. | `R-150r`, `R-150s` |
| Not a result | `failed` and `cancelled` runs, and runs still in flight. A version with only such runs has no result run. | `R-150r` |
| Findings of a run | The distinct `finding_uid` of the run's grounded observations (`finding_observation` joined to `finding`): the set `listRunFindings` returns and the run status counts as `published_finding_count`. An ungrounded observation is not a finding. | — |
| Undecided finding | A finding whose current verdict (`finding_current_verdict`) is `pending` or `needs_manual_review`. A comment decides nothing; a revoked verdict is `pending` again. | `pending`: `R-150o`; `needs_manual_review`: **proposed, not ruled** (the database cannot produce it today; it is treated as undecided so that the day it can, it is not silently counted as decided) |

The statement reads the section of the current version from `version_classification_current` (the latest classification
revision) by a `LEFT JOIN`; a version no expert has classified is the one unclassified bucket. The legacy `document.section` is not read.

## 2. The audit state of a document

A document is in exactly one of four states, plus a flag.

| State | Rule | Counted as |
| --- | --- | --- |
| `not_run` | The current version has no result run (never run; only failed or cancelled; only in flight). | «не запускались» (`R-150r`, `R-150p`) |
| `clean` | A result run that published no finding. A state of its own: neither «проверено» nor «нет решений эксперта». | its own figure (`R-150n`) |
| `awaiting_decision` | A result run with at least one undecided finding. | the red badge «ждут решения» (`R-150o`) |
| `checked` | A result run with findings, every one of them decided (accepted or rejected). | «проверено экспертом» (`R-150u` fixes that it is computed on findings only) |
| flag `partial` | The result run is `partial`. It marks the document in any of the four states; it is not a fifth state. | `R-150s` |

Optimisation proposals are not part of any state; they are counted separately, and that count is not built in this slice
(`R-150u`). AR v3 six-run groups use the general per-run rule above for now (each run of a group is a run of its version; the
latest `published` or `partial` one is the result); the group rule is decided when AR v3 is switched on (`R-150t`, `Q-MD-9`,
still a debt). The function `audit_state(result_state, has_findings, has_undecided)` is the only place the rule is written; a
combination the database cannot produce (a state that is not a result, undecided findings without findings) is refused out loud.

## 3. The figures on the wire

### 3.1 `DocumentAuditCounts` (`listProjects`: `Project.audit_counts`; `SectionDocumentCount.audit_counts`)

| Field | Formula |
| --- | --- |
| `document_count` | documents with a current version in the set. Equals `not_run + clean + awaiting_decision + checked`. |
| `not_run`, `clean`, `awaiting_decision`, `checked` | documents in that state (§2). |
| `partial` | documents, in any state, whose result run is `partial`. A count of the flag, not a fifth state (the count is **proposed, not ruled**; the ruling asks for a marker on the document, which is a per-document field of a later slice). |
| `no_expert_decision` | `not_run + awaiting_decision`. The original's column «Нет решений эксперта»: everything not closed, documents never run included, **never `clean`**. Named for what it is (`R-150o`). |

`awaiting_decision` is the badge «ждут решения» and `no_expert_decision` is the column; the interface labels each with its meaning
(`R-150o`). `Project.audit_counts` is present on a `listProjects` item and absent from `createProject`'s answer (a created project
reads no documents and claims no count; the same reason `document_count` is optional). A project with no documents reports zeros,
a measurement and not an omission.

### 3.2 `SectionDocumentCount` (`getDashboardSummary.section_breakdown`)

`document_count` equals `audit_counts.document_count` (both come from the same groups). `finding_count` is the number of published
findings of the result runs of the section's documents (**proposed, not ruled**: the brief names the figure, the rulings do not
define it). Every one of the fifteen sections and the unclassified bucket is a row even at zero.

### 3.3 `DashboardSummary.awaiting_decision_findings`

The number of undecided findings in the result runs of current versions. It is the figure of the home tile «Находки, ожидающие
решения» (`R-150q`). It includes the findings of `partial` results (both are audit results, `R-150s`: **proposed, not ruled** for
this figure). It follows the optional `project_uid` of `getDashboardSummary` (`UI-PARITY-P0A`), as every panel does; an unknown
project is `404 not_found`, never a summary of zeros.

### 3.4 `findings_by_verdict` (unchanged, now defined)

It counts every finding of every run of every version, by its current verdict: history, «за всё время». The contract's description
of `VerdictCount` says so, the panel «Находки по вердикту» is labelled «за всё время», and it differs from
`awaiting_decision_findings` whenever a version has more than one run or a document more than one version (`R-150q`). It is not
restricted to current versions, because it answers another question than the tile.

## 4. Edge cases (each is a test)

`tests/unit/dashboard/test_audit_state.py` states the rule without a database; `tests/integration/dashboard/test_audit_state_counters.py`
seeds 21 single-document situations and a twelve-document world counted by hand on real PostgreSQL.

| Situation | Result |
| --- | --- |
| A result run with zero findings | `clean` (`R-150n`) |
| Only a failed run, only a cancelled run, only a queued or running run | `not_run` (`R-150r`) |
| A `partial` result | a result, with the flag (`R-150s`) |
| A newer run in flight over an older result | the older result stays the result |
| A newer failed or cancelled run over an older result | the older result stays the result |
| A newer published run over an older one with pending findings | the newer is the result; the older findings count nowhere in the new figures |
| Two results created in the same instant | the greater `run_id` is the latest (`listRuns` order) |
| V2 uploaded and never run, V1 fully checked | `not_run`, and V1's findings count in no new figure (`R-150p`) |
| V2 with its own result | read on its own |
| A finding accepted and then revoked | undecided again |
| A finding with only a comment | undecided |
| A set whose head was never published | counted nowhere |
| A document in an unclassified version | the unclassified section row |
| A project with no documents | zeros in `audit_counts` |

## 5. Freshness and consistency (**proposed, not ruled**)

The figures are computed at read time from the tables, with no cache and no stored counter. The interface polls them under the
polling policy (`R-150k`). `listProjects` reads its listing and its counters in two statements (as the panels of the dashboard are
separate statements): a document published between them is in one answer and not yet in the other until the next poll. The
statement is grouped in the database, so the number of rows it returns is bounded by projects × sections × a handful of states,
not by documents or findings.

## 6. Not in this slice

The header selector and the columns (waves 1 and 2); the «отказ» chip that shows why a document with only failed runs is
`not_run` (`R-150r`; the per-document state itself, with its `partial` flag, is `DocumentVersion.audit` of `listDocuments` since
contract `1.34.0`, `UI-PARITY-DOC-AUDIT`); the separate count of optimisation proposals
(`R-150u`); the AR v3 group rule (`R-150t`, `Q-MD-9`); the other open questions of `D-303` (`Q-MD-8`, `Q-MD-10` … `Q-MD-21`).
