# ADR-0027: Decision memory — the case content is a primary record that outlives its source

- Status: accepted
- Date: 2026-11-09; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: accepted in the autonomous window 2026-11-09 by the lane that built phase M1; **revisable by the repository owner** (a dated addendum). The owner was unreachable; every answer in «Answers recorded in this window» is the recommendation of the design (`docs/program/DECISION-MEMORY-01.md` section 9). The owner's goal of 2026-11-07 (`ROADMAP.md`, «Owner goals of 2026-11-07», items 2 and 3); the polls `R-153q`…`R-153ar` of 2026-11-10 as built into `ADR-0029`.
- Amends (for the case content only): `ADR-0012` (the similar-case index is a rebuildable projection), owner ruling `R-16` («never a source of truth») and, for what an erase leaves, `R-146o` / `ADR-0022` section 3. · Amended by: `ADR-0029` (refines decisions 2, 3 and 6 and the answers to Q4 and Q8; see the text below).
- Owners: repository owner / the integrator of the decision-memory programme
- Related ADRs: `ADR-0012` (the ledger), `ADR-0022` (the operator project erase and the product purge), `ADR-0020` (pgvector and the embedding producer), `ADR-0006` (private object storage), `ADR-0026` (the pull channel the later phases serve)
- Design: `docs/program/DECISION-MEMORY-01.md`

## Context

The owner's goal of 2026-11-07 asks for expert decisions to be saved together with the crops they concern, in a store that survives the deletion of projects and documents, to be used later for fine-tuning data, dynamic prompts and hints to experts in similar cases.

Two existing rules pull against that:

- `ADR-0012` and `R-16` make every derived view of the ledger rebuildable and «never a source of truth». A copy of a case that has to be readable after its project is gone is not rebuildable: nothing is left to rebuild it from.
- `ADR-0022` section 3 and `R-146o` make the operator project erase remove a project's findings, evidence quotes, comments and expert decisions and keep only the record of the erasure.

## Decision

1. **Two parts, two standings.** The memory is split on what can be rebuilt.
   - The **case content** — the decision fact, the finding text, the evidence quotes with their geometry, the normative references, the references to the crop images the expert saw — is a **primary record from the moment of capture**. It is written in the same transaction as the decision, it is not rebuildable from anything that is later erased, and it is read-only history once its source is gone. This amends `ADR-0012` / `R-16` for this content only.
   - The **vectors and probes** (phase M4) stay rebuildable projections of the case content, exactly as `R-16` says. Re-embedding reads the memory's own content tables and never a source table, so it works after an erase.
2. **The project erase and the product purge leave the memory.**
   - No foreign-key path leads from a memory table to a project, document, finding or ledger row, so the erase's foreign-key closure cannot reach it; every memory table is `KEEP` in `product_purge.py`; a crop's Blob is kept by the rule that a Blob any `KEEP` table references stays.
   - The amendment to `R-146o` is exactly this: an erase leaves the record of the erasure **and** the decision memory.
   - Tables of **derived state** that the precedents programme adds (`decision_memory_probe`, `decision_memory_precedent_run`, `decision_memory_precedent_advice`) are `PRODUCT`: they hold no case content and are purged with the product. The content, the experts' comments (`decision_memory_comment`), the block evidence, the embeddings and their intents stay `KEEP`; capture and the forget protection cover the new content tables (`ADR-0029`).
   - **Forget** is the separate, owner-permitted operator act (phase M2, `DECISION-MEMORY-01` section 4.5; `scripts/recovery/memory_forget.py`, on the owner's permission reference): it deletes a case's content rows and the crop Blobs nothing else references, and leaves the case, its decisions and a tombstone (the `forget` event with the digest of the content that was forgotten). It is not part of the project erase unless the operator asks (`Q2` stays open; `--forget-memory` is not built) and has no API operation (`Q5` stays open; the operator-only answer is the design's recommendation, implemented).
3. **The memory is not a decision authority.** While the source finding exists the ledger decides what stands (`finding_current_verdict`); no product behaviour reads a verdict from the memory. A model never writes a memory decision: a memory decision exists only as the copy of a ledger event made in the ledger's own transaction, and the ledger event has a human author. A precedent mark (`ADR-0029`) reads the verdicts of **other** cases; it is advice for the expert and for the AI critic, never a decision, and no model writes a mark or a memory decision.
4. **Capture is in the decision's transaction, and loud.** `record_decision` calls a typed port after the insert; a capture failure propagates and the decision fails (`AGENTS.md` section 4: no silent fallback). Capture reads immutable rows and published artifacts and inserts rows; it has no external side effect to reconcile, so it is not an outbox. Where an external effect exists (a render, an embedding, an object deletion — phases M3, M4, M2) the shape is an intent row with a dispatcher and a sweep. A sweep also captures ledger events that have no memory decision, which backfills the decisions that existed before the memory and repairs a gap; two guards (G1, `DECISION-MEMORY-01` section 4.4) make the erase and the purge refuse while a gap exists.
5. **Append-only.** The identity tables (case, decision, status event) are `am_immutable_row`; the five content tables (content, evidence, norm references, crops and the expert's comment) are protected by `am_guard_decision_memory_forget`: `UPDATE` is refused always, `DELETE` is permitted only beside a `forget` status event of the same case inserted by the same transaction (the event's `xmin`), and the application role holds no `DELETE`. Nothing switches a trigger off to forget. A later decision on the same finding is a new decision row of the same case; there is no edit path.
   - A forgotten case is terminal and takes no words back: a new decision on its observation is recorded without the expert's comment, and any further status event is `conflict` (`memory_case_forgotten`).
   - Withdraw and restore are append-only status events (a closed reason, the acting admin's account under a `RESTRICT` key, the command receipt for a keyed call); the rule that a withdraw needs an active case and a restore a withdrawn one is repeated by a database trigger under an advisory lock per case.
6. **A bounded context.** `src/auditmanager/decision_memory/` imports `auditmanager.shared` and `auditmanager.storage.public` only, and **does not import the precedents core**. The capture assembler lives in the composition root and reads the other contexts through their public modules; `decisions` gains a typed port and imports nothing from the memory. The precedents core (`src/auditmanager/precedents/`, a new context that imports only the `public` module of others) reads the memory through `decision_memory.public`; the wiring of the two is the composition root's.

### Answers recorded in this window (revisable)

Decided 2026-11-09 by the autonomous window, by the design's own recommendations. The owner may revise any of them.

| Question | Answer in force |
| --- | --- |
| Q1 amend `R-16` / `ADR-0012` | Confirmed, as this ADR. |
| Q3(c) training use | `training_use` is off by default; no export is built in this phase. `data_class` and `training_use` are an installation setting (`D-390`): an append-only journal read at every capture, `test` and `off` when nothing is journalled, written only by an operator tool naming an admin account (an `on` names the owner's permission). The class of a case already captured is not changed by a later switch. |
| Q6 crops | v1 references existing portal image-block crops only (no rendered regions of text evidence); at most 4 per case. |
| Q7 author | An opaque `user_uid` without a foreign key, so `purgeUser` stays possible. |
| Q8 which decisions | `accept` and `reject` events (the ledger has no `revise`); carried and imported decisions are kept with their `origin_kind`. **Revised 2026-11-10:** `comment` events are now captured, into their own table, and carried over on a case's first ✓/✕ (`R-153ag`, `ADR-0029` decision 10); a comment never changes a vote. |
| Q12 retention | No automatic retention limit, consistent with `R-146c`. |
| Q13 hints | Not built now. |

Q4 (cross-client examples) is closed by the owner: any project's case may be shown to a model whole, with quotes; the risk is accepted and recorded in `ADR-0029` (`R-153z`).

Open and not decided here: Q2 (client erase), Q5 (who may forget), Q9 (normative material), Q10 (the embedder), Q11 (the fine-tuning target). The export is not built; embeddings, hints and prompt use belong to `ADR-0029`.

## Consequences

- Positive: a table added by the memory is a `KEEP` table; the purge and the erase stop on an unclassified table, which is the forcing function.
- Positive: a crop is a binding to an existing Blob (a Blob's identity is derived from its bytes), not a copy; capture has no external effect.
- Positive: backfill is by the sweep; the guards G1 refuse an erase or a purge while a ledger event has no memory decision.
- Cost: the case content may hold personal data inside quotes, comments and crops. v1 does no automatic redaction; the protection is the control of who may read and what may leave (`DECISION-MEMORY-01` section 4.2), and `data_class` marks test data apart from real.
- Cost: every case written in the first phase is `data_class = test` (the closed beta runs on test data; the safe direction, because an export defaults to `real` only). The installation setting of Q3(c) makes it configurable and had to land before real client data does (`D-390`).
- Cost: an account that withdrew, restored or forgot a case, or changed a setting, can no longer be purged (`R-61`, the `RESTRICT` key); the author of a decision still can (`Q7`).
- Not changed by the first phase (M1): `JobPackage v1`, analysis results, comparison evidence, the API contract and the web client; that phase adds no operation.

## Alternatives considered

The options weighed are the two rules of Context. Keeping the memory a rebuildable projection (`ADR-0012`, `R-16`) and letting the project erase remove it (`ADR-0022` section 3, `R-146o`) are both rejected for the case content (decisions 1, 2); a silent fallback when capture fails is rejected by `AGENTS.md` section 4 (decision 4).

## Verification

Conformance is carried by the guards named above (unclassified-table and no-foreign-key-path tests, guards G1, the forget trigger) and by `docs/program/DECISION-MEMORY-01.md` sections 4.3, 4.4 and 8.

## Revisit trigger

The owner revises any answer in the table (a dated addendum); one of the open questions Q2, Q5, Q9, Q10 or Q11 is answered; real client data is about to enter the memory (`D-390`, `D-291`).

## History

- 2026-11-09 — accepted in the autonomous window (phase M1); answers are the design's recommendations.
- 2026-11-09 — addendum of phase M2 (migration `0061_decision_memory_m2`; forget, withdraw and restore, the setting of Q3(c) / `D-390`) folded into decisions 2 and 5 and the answers table.
- 2026-11-10 — addendum `ADR-0029` (lane `CRIT-ADR-29`; `R-153q`…`R-153ar`: core reads the memory, derived-state tables `PRODUCT`, comments captured, Q4 closed) folded into decisions 2, 3 and 6 and the answers table.
- 2026-11-18 — compressed under ADR-OPTIMISE-01; decisions 1–6 unchanged in number and subject.
