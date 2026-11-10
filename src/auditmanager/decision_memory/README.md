# `decision_memory` boundary

The expert decision memory (`ADR-0027`, `docs/program/DECISION-MEMORY-01.md`). When an expert accepts or rejects a finding, the
decision is copied -- in the ledger's own transaction -- into a **case** holding what the expert saw and said: the finding text, the
evidence quotes with their page geometry, the certified normative references and references to the portal crop images of the pages the
evidence names. The case outlives the project and the document it came from.

Phase M1 is the capture core; phase M2 adds the standing of a case (withdraw, restore, forget), the read model and the installation
settings. There is still no web screen, no export and no embedding.

## What this package does and does not know

- It imports `auditmanager.shared` and `auditmanager.storage.public` and nothing else. It has no foreign key into a project, a
  document, a finding or the ledger, and no code that reads them.
- `models.py` holds the values of a capture and the content digest; `repository.py` holds the SQL (an idempotent insert, the
  digest and "which of these ledger events are captured" reads).
- The **assembler** that reads the finding, observation, evidence, certified citations, section and portal crop manifest through the
  other contexts' public modules lives in the composition root (`bootstrap/adapters.py`, `MemoryCaptureAssembler`), and so does the
  **sweep** (`MemoryCaptureSweep`) that captures ledger events with no memory decision. `decisions.public` offers the typed port
  `DecisionRecorded` and its registration; `record_decision` calls it after the insert and imports nothing from here.

## Rules

- Every table is append-only (`am_immutable_row`); there is no edit path. A later decision on a captured observation is a new
  `decision_memory_decision` row of the same case; the case, its content and its crop references are the first capture's.
- Idempotent by the database: `ON CONFLICT DO NOTHING` on `origin_observation_id` and on `source_decision_id`. A stored digest that
  differs from the captured one is `conflict`, never an overwrite. The digest covers the observation's immutable content only.
- A capture failure fails the decision that asked for it (no silent fallback); the sweep repairs a gap and reports each failure.
- Only `accept` and `reject` are captured. `origin_kind` is `carried` exactly when the ledger event has `carried_from_decision_id`.
- Every table is `KEEP` in `scripts/recovery/product_purge.py`; a crop's Blob is kept by the rule that a Blob a `KEEP` table references
  stays. Guard G1 makes the project erase and the purge refuse while a ledger event of the scope has no memory decision.

## Phase M2: standing, forget and settings

- **Standing** (`status.py`): a case is `active`, `withdrawn` or `forgotten`, by its latest **status event**. `withdraw` and `restore` are
  product writes (`service.py`, an admin's keyed command through the composition root's `DecisionMemoryAdapter`); `forget` is the operator's.
  The rule is stated once here and repeated by the database (`am_guard_decision_memory_status`, one advisory lock per case), so a writer that
  bypasses the service is refused with `AM003`.
- **Forget** removes a case's content, never its identity: `scripts/recovery/memory_forget.py` inserts the `forget` event and deletes the five
  content tables in one transaction; the guard `am_guard_decision_memory_forget` permits a `DELETE` only beside that event (same
  transaction, by `xmin`). The case, its decisions and the tombstone stay. A decision taken **after** a forget on the same observation is
  recorded (verdict, severity, time) **without** the expert's words, and the sweep and guard G1 see it as captured.
- **Settings** (`settings.py`): `data_class` and `training_use` are the append-only journal `decision_memory_setting_event`, read at every
  capture; nothing journalled means `test` and `off`. Only `scripts/recovery/memory_setting.py` writes it.
- **Reads** (`reads.py`): `MemoryReader` over the view `decision_memory_case_current` (list, one case, counts, settings). A forgotten case
  answers its tombstone only. The memory is not a decision authority; nothing here feeds a verdict into a product behaviour.
- Rules unchanged from M1: this package imports `auditmanager.shared` and `auditmanager.storage.public` only (the command claim is the
  composition root's), no foreign key leads into a project, a document, a finding or the ledger, and every table is `KEEP` in the purge.

## Comments (`ADR-0029` decision 10, `MEM-COMMENTS-01`)

The experts' `comment` ledger events are content of the memory, in a table of their own beside the decisions: `decision_memory_comment`
(KEEP, content side; `0064`). A comment is **not a decision**: it never makes a case, never adds a decision row and never changes a vote.

- **Capture** -- `MemoryRepository.capture_comment(session, observation_id=..., comment=CommentFact(...))`, for one `comment` event. One row per
  ledger event (`source_decision_id` is unique, `ON CONFLICT DO NOTHING`), so it is idempotent. Its outcome (`CommentCaptureResult.outcome`):
  `captured`, `already_captured`, `waits_for_case` (the observation has no case yet: nothing is written) or `case_forgotten` (a forgotten case
  takes no words back: nothing is written, and no error -- the database would refuse the row with `AM003`, and the expert's decision must not
  fail on it). Any other refusal of the database propagates: a capture that fails fails the decision (no silent fallback).
- **Carry-over** -- the memory reads no ledger. The assembler (composition root) reads the observation's `comment` events recorded before the
  ✓/✕ and puts them in `CaptureSnapshot.earlier_comments`; `MemoryRepository.capture` stores them in the case, each once, in the order the
  expert wrote them, and reports how many were new (`CaptureResult.comments_carried`). The first ✓/✕ carries the notes written before it; a
  replay, or a later decision handed the same comments, carries none; a forgotten case takes none.
- **Locks** -- two transaction-scoped advisory locks, both taken by `capture_comment`: the observation's
  (`decision_memory_comment_observation:<observation>`, also taken by `capture`) and the case's status lock (`decision_memory_status:<case>`,
  the key a forget and the status guard take). A caller that reads the ledger for the earlier comments **must call
  `MemoryRepository.lock_observation_comments` before that read**, so a comment and a first ✓/✕ that overlap in time cannot each miss the other.
- **Repair** -- `MemoryRepository.captured_comment_sources(session, ids)` answers which ledger `comment` events already have a row; the sweep's
  anti-join for comments of cases that exist, as `captured_sources` is for decisions.
- **Read** -- `MemoryReader.comments_for_cases(session, case_ids)` (`{case_id: ({comment_id, author_user_uid, comment, decided_at}, ...)}`,
  oldest first; hints read it through `decision_memory.public`) and `CaseDetail.comments`; a forgotten case answers none. The standing of a
  case is the caller's to read: a withdrawn case's comments are still stored.
- The 1.51.0 API contract has **no field** for a case's comments (`DecisionMemoryCase`), so the «Память решений» tab cannot show them until a
  later seal adds one.

