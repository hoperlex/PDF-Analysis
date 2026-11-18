# ADR-0027: Decision memory — the case content is a primary record that outlives its source

- Status: accepted
- Date: 2026-11-09; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: accepted in the autonomous window 2026-11-09 (phase M1); **revisable by the repository owner** (a dated addendum). The owner was unreachable: every answer in «Answers recorded in this window» is the design's recommendation (`docs/program/DECISION-MEMORY-01.md` section 9). The owner's goal of 2026-11-07 (`docs/program/ROADMAP.md`, «Owner goals of 2026-11-07», items 2 and 3); the polls `R-153q`…`R-153ar` of 2026-11-10 as built into `ADR-0029`.
- Amends (for the case content only): `ADR-0012` (the similar-case index is a rebuildable projection), owner ruling `R-16` («never a source of truth») and, for what an erase leaves, `R-146o` / `ADR-0022` section 3. · Amended by: `ADR-0029` (refines decisions 2, 3 and 6 and the answers to Q4 and Q8).
- Related: `ADR-0006`, `ADR-0012`, `ADR-0020`, `ADR-0022`, `ADR-0026`. Design: `docs/program/DECISION-MEMORY-01.md`.

## Context

The owner's goal of 2026-11-07: expert decisions are saved with the crops they concern, in a store that survives the deletion of projects and documents, for later fine-tuning data, dynamic prompts and hints in similar cases. Two rules pull against that: `ADR-0012` and `R-16` make every derived view rebuildable and «never a source of truth» (a copy that outlives its project has nothing to rebuild it from); `ADR-0022` section 3 and `R-146o` make the project erase remove findings, quotes, comments and decisions and keep only the record of the erasure.

## Decision

1. **Two parts, two standings.** The **case content** (the decision fact, the finding text, the evidence quotes with geometry, the normative references, the references to the crops the expert saw) is a **primary record from the moment of capture**: written in the decision's transaction, not rebuildable from anything later erased, read-only history once its source is gone. This amends `ADR-0012` / `R-16` for this content only. The **vectors and probes** stay rebuildable projections (`R-16`); re-embedding reads the memory's own content tables, never a source table, so it works after an erase.
2. **The project erase and the product purge leave the memory.** No foreign-key path leads from a memory table to a project, document, finding or ledger row, so the erase closure cannot reach it; every memory table is `KEEP` in `product_purge.py`, and a Blob any `KEEP` table references stays. The amendment to `R-146o`: an erase leaves the record of the erasure **and** the decision memory. Tables of **derived state** that the precedents programme adds (probes, precedent runs, advice) are `PRODUCT`: no case content, purged with the product; the content, the experts' comments, block evidence, embeddings and their intents stay `KEEP`, and capture and the forget protection cover the new content tables (`ADR-0029`). **Forget** is a separate, owner-permitted operator act (`DECISION-MEMORY-01` section 4.5, on the owner's permission reference): it deletes a case's content rows and the crop Blobs nothing else references and leaves the case, its decisions and a tombstone (the `forget` event with the digest of the forgotten content). It is not part of the project erase unless the operator asks (`Q2` open; `--forget-memory` is not built) and has no API operation (`Q5` open; operator-only is the design's recommendation, implemented).
3. **The memory is not a decision authority.** While the source finding exists the ledger decides what stands (`finding_current_verdict`); no product behaviour reads a verdict from the memory. A model never writes a memory decision: it exists only as the copy of a ledger event made in the ledger's own transaction, and that event has a human author. A precedent mark (`ADR-0029`) reads the verdicts of **other** cases and is advice for the expert and the AI critic, never a decision.
4. **Capture is in the decision's transaction, and loud.** `record_decision` calls a typed port after the insert; a capture failure propagates and the decision fails (`AGENTS.md` section 4: no silent fallback). Capture has no external effect, so it is not an outbox; where one exists (render, embedding, object deletion) the shape is an intent row with a dispatcher and a sweep. A sweep also captures ledger events that have no memory decision (backfill and repair); the guards G1 (`DECISION-MEMORY-01` section 4.4) make the erase and the purge refuse while a gap exists.
5. **Append-only.** The identity tables (case, decision, status event) are `am_immutable_row`; the five content tables (content, evidence, norm references, crops, the expert's comment) are protected by `am_guard_decision_memory_forget`: `UPDATE` is refused always, `DELETE` only beside a `forget` status event of the same case inserted by the same transaction, and the application role holds no `DELETE`. Nothing switches a trigger off to forget. A later decision on the same finding is a new row of the same case; there is no edit path. A forgotten case is terminal: a new decision on its observation is recorded without the expert's comment, and any further status event is `conflict` (`memory_case_forgotten`). Withdraw and restore are append-only status events (a closed reason, the acting admin's account under a `RESTRICT` key); a withdraw needs an active case and a restore a withdrawn one, enforced by a database trigger under an advisory lock per case.
6. **A bounded context.** `src/auditmanager/decision_memory/` imports `auditmanager.shared` and `auditmanager.storage.public` only and **does not import the precedents core**. The capture assembler lives in the composition root; `decisions` gains a typed port and imports nothing from the memory. The precedents core imports only the `public` module of others and reads the memory through `decision_memory.public`.

### Answers recorded in this window (revisable)

Decided 2026-11-09 by the design's own recommendations; the owner may revise any of them.

| Question | Answer in force |
| --- | --- |
| Q1 amend `R-16` / `ADR-0012` | Confirmed, as this ADR. |
| Q3(c) training use | `training_use` is off by default; no export is built. `data_class` and `training_use` are an installation setting (`D-390`, closed): an append-only journal read at every capture, `test` and `off` when nothing is journalled, written only by an operator tool naming an admin account (an `on` names the owner's permission); a captured case keeps its class. |
| Q6 crops | Existing portal image-block crops only; at most 4 per case. |
| Q7 author | An opaque `user_uid` without a foreign key, so `purgeUser` stays possible. |
| Q8 which decisions | `accept` and `reject` events; carried and imported decisions are kept with their `origin_kind`. **Revised 2026-11-10:** `comment` events are captured into their own table and carried over on a case's first ✓/✕ (`R-153ag`, `ADR-0029` decision 10); a comment never changes a vote. |
| Q12 retention | No automatic retention limit (`R-146c`). |
| Q13 hints | Not built in the memory; the hints are `ADR-0029` decision 5. |

Q4 (cross-client examples) is closed by the owner: any project's case may be shown to a model whole, with quotes; the risk is accepted in `ADR-0029` (`R-153z`).

Open and not decided here: Q2 (client erase), Q5 (who may forget), Q9 (normative material), Q10 (the embedder), Q11 (the fine-tuning target); `ADR-0029` (decision 13) answers Q9(b) and Q10 in part. The export is not built. Embeddings, hints and prompt use belong to `ADR-0029` (decisions 3, 4, 5, 8).

## Consequences

- Positive: a table added by the memory is a `KEEP` table; the purge and the erase stop on an unclassified table, which is the forcing function.
- Positive: a crop is a binding to an existing Blob, not a copy; backfill is by the sweep.
- Cost: the case content may hold personal data in quotes, comments and crops; v1 does no automatic redaction (the protection is who may read and what may leave, `DECISION-MEMORY-01` section 4.2); `data_class` marks test data apart from real.
- Cost: an account that withdrew, restored or forgot a case, or changed a setting, can no longer be purged (`R-61`, the `RESTRICT` key); the author of a decision still can (`Q7`).

## Alternatives considered

The original recorded none. Keeping the memory a rebuildable projection (`ADR-0012`, `R-16`) and letting the project erase remove it (`R-146o`) are rejected for the case content (decisions 1, 2); a silent fallback when capture fails is rejected by `AGENTS.md` section 4 (decision 4).

## Verification

The guards named above (unclassified-table and no-foreign-key-path tests, guards G1, the forget trigger) and `docs/program/DECISION-MEMORY-01.md` sections 4.3, 4.4 and 8.

## Revisit trigger

The owner revises any answer in the table (a dated addendum); one of the open questions Q2, Q5, Q9, Q10 or Q11 is answered; real client data is about to enter the memory (`D-291`).

## History

- 2026-11-09 — accepted in the autonomous window (phase M1); answers are the design's recommendations.
- 2026-11-09 — addendum of phase M2 (forget, withdraw and restore, the setting of Q3(c) / `D-390`) folded into decisions 2 and 5 and the answers table.
- 2026-11-10 — addendum `ADR-0029` (`R-153q`…`R-153ar`: core reads the memory, derived-state tables `PRODUCT`, comments captured, Q4 closed) folded into decisions 2, 3 and 6 and the answers table.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0027-decision-memory.md
- 2026-11-18 — status statements updated to dev fb6c2203e: `D-390` is closed (the `data_class` setting exists, `scripts/recovery/memory_setting.py`); the hints are delivered by `ADR-0029` (`src/auditmanager/precedents/hints.py`); the export is still not built (no `decision_memory_export` table or export tool in the tree).
- 2026-11-18 — Alternatives, Verification and Revisit trigger written from the decisions (the original had none).
