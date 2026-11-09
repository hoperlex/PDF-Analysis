# ADR-0027: Decision memory — the case content is a primary record that outlives its source

- Status: accepted in the autonomous window 2026-11-09 by the lane that built phase M1; **revisable by the repository owner**. The
  owner was unreachable; every answer below is the recommendation of the design (`docs/program/DECISION-MEMORY-01.md` section 9) and is
  marked as such. A revision is a dated addendum.
- Date: 2026-11-09
- Owners: repository owner / the integrator of the decision-memory programme
- Amends (for the case content only): `ADR-0012` (the similar-case index is a rebuildable projection), owner ruling `R-16`
  («never a source of truth») and, for what an erase leaves, `R-146o` / `ADR-0022` section 3.
- Related ADRs: `ADR-0012` (the ledger), `ADR-0022` (the operator project erase and the product purge), `ADR-0020` (pgvector and the
  embedding producer), `ADR-0006` (private object storage), `ADR-0026` (the pull channel the later phases serve).
- Design: `docs/program/DECISION-MEMORY-01.md`

## Context

The owner's goal of 2026-11-07 (`ROADMAP.md`, «Owner goals of 2026-11-07», items 2 and 3) asks for expert decisions to be saved together
with the crops they concern, in a store that survives the deletion of projects and documents, to be used later for fine-tuning data,
dynamic prompts and hints to experts in similar cases.

Two existing rules pull against that:

- `ADR-0012` and `R-16` make every derived view of the ledger rebuildable and «never a source of truth». A copy of a case that has to
  be readable after its project is gone is not rebuildable: nothing is left to rebuild it from.
- `ADR-0022` section 3 and `R-146o` make the operator project erase remove a project's findings, evidence quotes, comments and expert
  decisions and keep only the record of the erasure.

## Decision

1. **Two parts, two standings.** The memory is split on what can be rebuilt.
   - The **case content** — the decision fact, the finding text, the evidence quotes with their geometry, the normative references, the
     references to the crop images the expert saw — is a **primary record from the moment of capture**. It is written in the same
     transaction as the decision, it is not rebuildable from anything that is later erased, and it is read-only history once its source
     is gone. This amends `ADR-0012` / `R-16` for this content only.
   - The **vectors and probes** (phase M4) stay rebuildable projections of the case content, exactly as `R-16` says. Re-embedding reads
     the memory's own content tables and never a source table, so it works after an erase.
2. **The project erase and the product purge leave the memory.** No foreign-key path leads from a memory table to a project, document,
   finding or ledger row, so the erase's foreign-key closure cannot reach it; every memory table is `KEEP` in `product_purge.py`; a
   crop's Blob is kept by the rule that a Blob any `KEEP` table references stays. The amendment to `R-146o` is exactly this: an erase
   leaves the record of the erasure **and** the decision memory. Erasing a client's memory is a separate, owner-permitted operator act
   (`forget`, phase M2, `DECISION-MEMORY-01` section 4.5); it is not part of the project erase unless the operator asks.
3. **The memory is not a decision authority.** While the source finding exists the ledger decides what stands
   (`finding_current_verdict`); no product behaviour reads a verdict from the memory. A model never writes a memory decision: a memory
   decision exists only as the copy of a ledger event made in the ledger's own transaction, and the ledger event has a human author.
4. **Capture is in the decision's transaction, and loud.** `record_decision` calls a typed port after the insert; a capture failure
   propagates and the decision fails (AGENTS section 4: no silent fallback). Capture reads immutable rows and published artifacts and
   inserts rows; it has no external side effect to reconcile, so it is not an outbox. Where an external effect exists (a render, an
   embedding, an object deletion — phases M3, M4, M2) the shape is an intent row with a dispatcher and a sweep. A sweep also captures
   ledger events that have no memory decision, which backfills the decisions that existed before the memory and repairs a gap; two
   guards (G1, `DECISION-MEMORY-01` section 4.4) make the erase and the purge refuse while a gap exists.
5. **Append-only.** The identity tables (case, decision, status event) and the content tables are append-only rows. A later decision
   on the same finding is a new decision row of the same case. There is no edit path.
6. **A bounded context.** `src/auditmanager/decision_memory/` imports `auditmanager.shared` and `auditmanager.storage.public` only; the
   capture assembler lives in the composition root and reads the other contexts through their public modules; `decisions` gains a
   typed port and imports nothing from the memory.

## Answers recorded in this window (revisable)

Decided 2026-11-09 by the autonomous window, by the design's own recommendations. The owner may revise any of them.

| Question | Answer in force |
| --- | --- |
| Q1 amend `R-16` / `ADR-0012` | Confirmed, as this ADR. |
| Q3(c) training use | `training_use` is off by default; no export is built in this phase. |
| Q6 crops | v1 references existing portal image-block crops only (no rendered regions of text evidence); at most 4 per case. |
| Q7 author | An opaque `user_uid` without a foreign key, so `purgeUser` stays possible. |
| Q8 which decisions | `accept` and `reject` events (the ledger has no `revise`); not `comment`. Carried and imported decisions are kept with their `origin_kind`. |
| Q12 retention | No automatic retention limit, consistent with `R-146c`. |
| Q13 hints | Not built now. |

Open and not decided here: Q2 (client erase), Q4 (cross-client examples), Q5 (who may forget), Q9 (normative material), Q10 (the
embedder), Q11 (the fine-tuning target).

## Consequences

- A table added by the memory is a `KEEP` table; the purge and the erase stop on an unclassified table, which is the forcing function.
- A crop is a binding to an existing Blob (a Blob's identity is derived from its bytes), not a copy; capture has no external effect.
- The case content may hold personal data inside quotes, comments and crops. v1 does no automatic redaction; the protection is the
  control of who may read and what may leave (`DECISION-MEMORY-01` section 4.2), and `data_class` marks test data apart from real.
- Every case written in this phase is `data_class = test` (the closed beta runs on test data; the safe direction, because an export
  defaults to `real` only). Phase M2 makes it an installation setting; that must land before real client data does (`D-390`).
- Backfill is by the sweep; the guards G1 refuse an erase or a purge while a ledger event has no memory decision.

## Not changed

`JobPackage v1`, analysis results, comparison evidence, the API contract and the web client. This phase adds no operation.

## Addendum 2026-11-09 (phase M2: standing, forget, settings)

Built by lane M2 (migration `0061_decision_memory_m2`; `DECISION-MEMORY-01` section 8, «Built 2026-11-09 (phase M2)»). Behaviour that changes or
sharpens the decisions above; the owner may revise any of it.

- **Decision 5 (append-only) is refined, not weakened.** The three identity tables (case, decision, status event) stay `am_immutable_row`. The
  five content tables (content, evidence, norm references, crops and the expert's comment) are protected by `am_guard_decision_memory_forget`:
  `UPDATE` is refused always, `DELETE` is permitted only beside a `forget` status event of the same case inserted by the same transaction
  (the event's `xmin`), and the application role holds no `DELETE`. Nothing switches a trigger off to forget.
- **Decision 2 (what a forget is).** `forget` is an operator act on the owner's permission reference (`scripts/recovery/memory_forget.py`): it
  deletes a case's content rows and the crop Blobs nothing else references, and leaves the case, its decisions and a tombstone (the `forget` event
  with the digest of the content that was forgotten). It is not part of the project erase (`Q2` stays open; `--forget-memory` is not built) and
  there is no API operation for it (`Q5` stays open; the operator-only answer is the design's recommendation, implemented).
- **A forgotten case is terminal and takes no words back.** A new decision on its observation is recorded without the expert's comment; any
  further status event is `conflict` (`memory_case_forgotten`).
- **Withdraw and restore** are append-only status events (a closed reason, the acting admin's account under a `RESTRICT` key, the command receipt
  for a keyed call). The rule that a withdraw needs an active case and a restore a withdrawn one is repeated by a database trigger under an
  advisory lock per case.
- **Q3(c) / D-390.** `data_class` and `training_use` are an installation setting: an append-only journal read at every capture, `test` and `off`
  when nothing is journalled, written only by an operator tool naming an admin account (an `on` names the owner's permission). The class of a
  case already captured is not changed by a later switch.
- **Consequence for accounts.** An account that withdrew, restored or forgot a case, or changed a setting, can no longer be purged
  (`R-61`, the `RESTRICT` key); the author of a decision still can (`Q7`).
- **Still not decided and not built:** `Q2`, `Q4`, `Q5`, `Q9`, `Q10`, `Q11`; the export, the embeddings, the hint and the prompt use.
