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
