# Edge-case matrix — W0-BHV-02

Companion to [SELECTION.md](SELECTION.md). Every row is realized by a
`failure_cases` or `expected_outputs` entry in the manifest named in the last
column, so this table is a review index and not a second source of truth.

Legend for the class column:

- `L` — `legacy_observed`, backed by an immutable evidence reference and usable as
  parity oracle evidence;
- `T` — `greenfield_target`, intended behavior that diverges from legacy and is not
  parity; a `PD-` reference next to it names the owner decision that approved the
  divergence on 2026-09-01. A `T` row without such a reference is not an owner decision:
  it follows from a repository rule, or it reports a value owned by an authoritative
  artifact through the manifest's `authority` block, as row 31 does;
- `P` — `pending_owner_decision`, blocked on an unapproved owner decision. No row
  carries this class after the 2026-09-01 disposition; the class stays in the legend
  because a reopened or newly raised decision must have somewhere honest to go.

## 1. Ingest, identity and versioning

| # | Edge case | Expected visible outcome | Class | Manifest entry |
|---|---|---|---|---|
| 1 | Clean bundle precheck | Verdict status `ready` with digest, fingerprint and suggested target | `L` | [GJ-01](GJ-01/manifest.json) `EO-01` |
| 2 | Bundle fingerprint already present in the object | Verdict status `duplicate`; `error` wins when a blocking code is present | `L` | GJ-01 `EO-02` |
| 3 | Empty upload | 400; nothing created | `L` | GJ-01 `FC-01` |
| 4 | Forbidden extension | 400; no partial version left behind | `L` | GJ-01 `FC-02` |
| 5 | Relative traversal or absolute member path | 400; nothing written outside the version root | `L` | GJ-01 `FC-03` |
| 6 | Companion member recognition | Folder ingest accepts `.pdf`, `.md`, `.json`, `.html`, `.htm` and `.zip` and recognizes companions by lowercased filename suffix: `_result.json` for the recognized JSON companion, `_blocks.json` for optional block geometry, `_ocr.html`/`_results.html`/`_results.htm` for OCR. Anything else lands in `ignored_files` with no block and no warning. The version-file upload has its own set `.pdf`, `.md`, `.txt`, `.json`, `.html` and no suffix rule at all | `L` | GJ-01 `EO-08` |
| 7 | Malformed recognized-JSON companion, uploaded beside the single PDF the folder rule requires | Accepted at ingest: the body is never parsed there, the bytes are stored verbatim and `has_result` is true. The malformed body raises no code of its own, because the closed precheck error-code set has none for JSON validity, so the verdict is the one the same folder would receive with a well-formed companion. The case carries the PDF deliberately: a folder with the companion alone has a pdf count of zero, which appends `no_pdf` and makes the verdict `error`, and the save path refuses it outright, so the missing PDF and not the malformed JSON would be characterized. The decode failure first appears one level down in the crop stage, where the entry point raises an unguarded decode error and the image-block iterator swallows it and skips the file | `L` | GJ-01 `FC-04` |
| 8 | Name conflict without the replace flag | 409; existing file preserved | `L` | GJ-01 `FC-05` |
| 9 | New version from a project whose output is not empty | 409 with `source_output_not_empty` and `needs_flag` | `L` | GJ-01 `FC-06` |
| 10 | Version creation during an active audit | 409; running audit undisturbed | `L` | GJ-01 `FC-07` |
| 11 | Identity of project, version and document | Opaque assigned identifier, never a path, filename or display label | `T` | GJ-01 `EO-06` |
| 12 | Duplicate detection substrate | Content digests on an immutable ingest manifest instead of a mutable folder scan | `T` | GJ-01 `EO-07` |

## 2. Run control, stage state and export

| # | Edge case | Expected visible outcome | Class | Manifest entry |
|---|---|---|---|---|
| 13 | Process restart with a stale running pipeline | Converted to `interrupted` and resumable | `L` | [GJ-02](GJ-02/manifest.json) `EO-01` |
| 14 | Resume entry point | Normalized stage name, declared continuation order; resume order differs from display order | `L` | GJ-02 `EO-02` |
| 15 | Text before block and block before text | Both are valid legacy shapes, selected by pipeline version | `L` | GJ-02 `EO-03` |
| 16 | Retry vocabulary versus skip vocabulary | Two different sets, neither derived from the other; an accepted skip executes nothing and only writes a `skipped` log entry | `L` | GJ-02 `EO-04` |
| 17 | Retry with an unknown stage name | 4xx; nothing restarted | `L` | GJ-02 `FC-01` |
| 18 | Skip of `decision_carryover`, a retryable name outside the skip whitelist | 400; the stage stays mandatory. Retryable does not imply skippable | `L` | GJ-02 `FC-02` |
| 19 | Skip of `findings_merge` | Accepted by legacy: `findings_merge` is a member of the skip whitelist, so the request answers `skipped` and writes that log entry for the stage | `L` | GJ-02 `EO-12` |
| 20 | Text or block artifact invalidated | The stage returns to incomplete on the next status computation | `L` | GJ-02 `EO-05` |
| 21 | Provider timeout in the block-analysis leg | Explicit not-ok result with timeout error and elapsed measurement | `L` | GJ-02 `EO-06`, `FC-03` |
| 22 | Missing norms found | Queue artifact plus warning with counts | `L` | GJ-02 `EO-07` |
| 23 | Missing-norm queue cannot be written | Warning log; run continues degraded and visibly | `L` | GJ-02 `FC-04` |
| 24 | Excel export with an unknown report kind | 400 | `L` | GJ-02 `FC-05` |
| 25 | Excel generator error on standalone export | 500 reported to the caller | `L` | GJ-02 `FC-06` |
| 26 | Package requested without merged findings | 404 | `L` | GJ-02 `FC-07` |
| 27 | Embedded Excel generator exits non-zero or leaves an empty workbook during packaging | The zero-exit and non-empty guard is not met, so `audit_report.xlsx` is skipped. Nothing is printed and nothing is logged; the archive is completed and streamed as an ordinary success | `L` | GJ-02 `EO-09`, `FC-08` |
| 28 | Embedded Excel generation raises during packaging | Caught by the broad handler, printed once to standard output and swallowed; `audit_report.xlsx` is skipped and the archive is still streamed as an ordinary success | `L` | GJ-02 `EO-09`, `FC-11` |
| 29 | Download requested for an escaping name that does not exist, for an existing file outside the base directory, and for an existing file in a sibling directory whose resolved path shares the base directory name as a string prefix | Existence is tested before containment, so the three end differently: 404 for the name that exists under neither lookup root, 403 only for the existing file whose resolved path fails the comparison, and a served response for the sibling, because the comparison is `str.startswith` on the resolved strings with no path-component boundary. Not a safe-path validation applied before resolution | `L` | GJ-02 `EO-08`, `FC-09` |
| 30 | Any declared package member unavailable | Degraded or failed result carrying the reason; never silent success | `T` | GJ-02 `EO-10`, `FC-10` |
| 31 | Skippability of the merge stage in the target | Not skippable, reported from the authoritative versioned stage registry: `stages[stage_id=finding_merge].status_policy.skip_allowed` is `false`. The journey reports that field through an `authority` block and decides nothing itself; the value is neither an owner decision nor a legacy observation, and the registry is an unfrozen candidate | `T` | GJ-02 `EO-13` |
| 32 | Conflicting legacy stage declarations | One authoritative versioned target registry; legacy lists become aliases resolved by a name-level alias map, and this journey renames nothing | `T` `PD-02` | GJ-02 `EO-11` |

## 3. Findings, carryover and expert decisions

| # | Edge case | Expected visible outcome | Class | Manifest entry |
|---|---|---|---|---|
| 33 | Finding traced to source context | Deterministic block map, version-aware listing | `L` | [GJ-03](GJ-03/manifest.json) `EO-01` |
| 34 | Carryover meets an existing human decision | Live entry untouched; auto-transfer skipped for that key | `L` | GJ-03 `EO-02`, `FC-04` |
| 35 | Carryover provider timeout | `needs_manual_review`, no verdict transferred | `L` | GJ-03 `EO-03`, `FC-01` |
| 36 | Carryover call budget exhausted | `needs_manual_review` with the exhaustion reason | `L` | GJ-03 `FC-02` |
| 37 | Match confidence below threshold | `needs_manual_review` with top score and candidate visible | `L` | GJ-03 `FC-03` |
| 38 | Carryover provenance | Carried-over marker, origin version and origin item stay visible | `L` | GJ-03 `EO-04` |
| 39 | Carryover rerun and migrated findings re-append | Merge by item identity; stable origin-derived identifier; no duplicates | `L` | GJ-03 `EO-05` |
| 40 | Expert decision corrected | Matching log entry replaced in place; previous value not retained | `L` | GJ-03 `EO-06` |
| 41 | Expert decision revoked | Deleted from the global log and the project review document | `L` | GJ-03 `EO-07` |
| 42 | Ambiguous revocation request | Refused and logged; nothing deleted | `L` | GJ-03 `FC-05` |
| 43 | Reviewer identity | Portal session identity; unmapped login is not substituted | `L` | GJ-03 `EO-08` |
| 44 | Decision typing | Closed enumeration with an explicit pending state | `T` | GJ-03 `EO-10` |
| 45 | Correction and revocation history | New decision identifier and appended event, earlier value readable; revocation leaves the projection `pending` and restores no previous verdict | `T` `PD-01` | GJ-03 `EO-09`, `FC-06` |

## 4. Stage comparison, reuse and repair

| # | Edge case | Expected visible outcome | Class | Manifest entry |
|---|---|---|---|---|
| 46 | Session created twice from the same sources | Existing session with the matching signature is reused | `L` | [GJ-04](GJ-04/manifest.json) `EO-01` |
| 47 | Sheet links saved | Prior explicit link set replaced; repair suggestions superseded | `L` | GJ-04 `EO-02` |
| 48 | Difference recomputed with an unchanged signature | Stored artifact returned, reported not stale | `L` | GJ-04 `EO-03` |
| 49 | Source, link or exclusion changed | Signature changes, downstream artifacts stale, gate refuses | `L` | GJ-04 `EO-04`, `FC-02` |
| 50 | Downstream stage without exclusion state | Explicit required-exclusions error | `L` | GJ-04 `FC-01` |
| 51 | Upstream comparison missing or mismatched | Explicit comparison-required error; no silent reuse | `L` | GJ-04 `FC-03` |
| 52 | AI group fails or is partial | Group stays failed or partial; raw evidence unchanged; summary falls back visibly | `L` | GJ-04 `EO-05`, `FC-05` |
| 53 | High-confidence repair applied | Confidence and current source validated, history recorded, downstream recomputed | `L` | GJ-04 `EO-06` |
| 54 | Repair below the bar or against a changed source | Refused with an explicit validation or race error | `L` | GJ-04 `FC-04` |
| 55 | Repair undone | Snapshot restored and downstream recomputed | `L` | GJ-04 `EO-07` |
| 56 | Stage input replaced | Temporary location, atomic switch, recoverable previous copy | `L` | GJ-04 `EO-08` |
| 57 | Graphic or vector difference requested | No artifact exists; graphics reported as not analyzed | `L` | GJ-04 `EO-09`, `FC-06` |
| 58 | AI layer versus raw evidence | AI may only add its own artifact, never edit the raw record | `T` | GJ-04 `EO-10` |
| 59 | Graphic and vector comparison as a capability | Future greenfield scope, absent from parity and from W0, first contractual inclusion in `W7` with a separate golden graphic pair | `T` `PD-04` | GJ-04 `EO-11` |

## 5. Distributed execution and recovery

| # | Edge case | Expected visible outcome | Class | Manifest entry |
|---|---|---|---|---|
| 60 | Reconnect with unacknowledged events | Deduplicated by job, attempt and sequence; acknowledged sequence advances; sequence never resets | `L` | [GJ-05](GJ-05/manifest.json) `EO-01` |
| 61 | Batch on a superseded connection epoch | Rejected; acknowledged sequence does not move | `L` | GJ-05 `EO-02`, `FC-01` |
| 62 | Sustained connectivity loss | Log lines thinned with an explicit truncation event | `L` | GJ-05 `FC-02` |
| 63 | Attempt declared lost, new attempt opened | At most one active attempt; history preserved | `L` | GJ-05 `EO-03` |
| 64 | Disposition versus execution state | Two orthogonal axes, never merged | `L` | GJ-05 `EO-04` |
| 65 | Result of a non-active attempt arrives late | Stored only, superseded storage class, not published | `L` | GJ-05 `EO-05`, `FC-04` |
| 66 | Chunk resent with the same hash | No-op | `L` | GJ-05 `EO-06` |
| 67 | Chunk resent with a different hash | Conflict; accepted chunk not replaced | `L` | GJ-05 `FC-03` |
| 68 | Crash during result apply | Journal rollback on restart; publication only after validation | `L` | GJ-05 `EO-07`, `FC-05` |
| 69 | Same package hash replayed | `already_applied`; nothing changes | `L` | GJ-05 `EO-08` |
| 70 | Different package hash for an applied attempt | Explicit conflict; no silent overwrite | `L` | GJ-05 `FC-06` |
| 71 | Package carries a source or centre-generated member | Package refused | `L` | GJ-05 `EO-09`, `FC-07` |
| 72 | Distributed feature disabled | Only the status route answers | `L` | GJ-05 `EO-10` |
| 73 | Enabled without portal auth and without the insecure acknowledgement | Administrative and bootstrap routes are not mounted | `L` | GJ-05 `FC-08` |
| 74 | Bootstrap repeated; worker update requested | No duplicate release, service or worker; update manifest is an explicit empty response | `L` | GJ-05 `EO-11` |
| 75 | Run identity and attempt authority in legacy | Bounded absence: no distinct run entity and no dedicated authority field under any name. Authority is the attempt disposition, an attempt-scoped execution token persisted only as its hash, and the connection epoch; fencing exists only as the behavior of those three, and none of them is relabelled | `L` | GJ-05 `EO-12` |
| 76 | Durability of job and attempt state | Persisted outside process memory; side effects paired with an outbox record | `T` | GJ-05 `EO-14` |
| 77 | Two workers each claiming the current attempt after failover | New attempt on the same job and the same run, no new run and no reopened terminal run; the stale holder is refused by an `execution_token` equality check inside the publishing transaction | `T` `PD-03` | GJ-05 `EO-13`, `FC-09` |

## 6. Coverage notes and known gaps

- No row asserts equality of live model text. Provider-dependent rows assert outcome
  shape and resulting state only, from the deterministic stubs declared under
  `determinism.replay_material` in [GJ-02](GJ-02/manifest.json) and
  [GJ-03](GJ-03/manifest.json).
- Rows 27, 28 and 30 deliberately sit next to each other: the two observed archive
  incompleteness paths are recorded as legacy behavior — one of them leaves no trace at
  all, the other leaves a printed line the caller never sees — and the intended
  visible-degradation rule is recorded separately as a target. They must not be merged.
- Rows 19 and 31 are the same kind of pair for the merge stage. Row 19 is what the
  legacy skip whitelist permits and is parity evidence; row 31 is the target value and
  is not. Neither may be substituted for the other, and correcting one never edits the
  other. Row 31 owns no rule: it reports `status_policy.skip_allowed` for the canonical
  `finding_merge` stage from the versioned stage registry named in
  [SELECTION.md](SELECTION.md) section 6.1, so a change in that registry re-derives the
  row rather than being argued against it.
- Row 29 is a characterization of a guard, not an endorsement of it. The prefix-collision
  branch is recorded because the pinned legacy source behaves that way; it carries no
  target status, and no fix or hardening rule is proposed anywhere in this matrix.
- This matrix declares no counts. The assertion invariants of the selected set and the
  history of every composition change live in `assertion_invariants` in
  [selection.json](selection.json) and are quoted in [SELECTION.md](SELECTION.md)
  section 3.2.
- Rows 57, 75 and the bounded-absence expectations are negative findings limited to
  the inspected committed tree and the recorded search scope. They do not prove
  universal absence. Row 75 in particular states the absence of a dedicated authority
  field; it does not name a target field, and the canonical target name is fixed
  separately by integration decision `ID-02` as `execution_token`.
- Rows 32, 45, 59 and 77 became `T` when the repository owner disposed of `PD-01`
  through `PD-04` on 2026-09-01. They are approved target behavior and still not parity:
  each keeps `parity_oracle: false`, and the legacy rows they diverge from — 40, 41, 57
  and 75 — are unchanged `L` rows. A rejected or reopened decision returns its row to
  `P` or withdraws it; no row silently becomes parity.
- Runtime, rendering, latency, concurrency timing and deployment behavior are outside
  this matrix because nothing was executed.
