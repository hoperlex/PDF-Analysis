# Wave `B-II` — closure

> **Status: accepted.** Both sessions landed. Full acceptance on the merged tree: 21 gate
> commands, **1062 tests**, every one exit `0`.

## 1. Measured

| Session | Wall-clock | Rounds to accept |
|---|---:|---:|
| `B5` run executor and CSV export | 46 min | **0** |
| `B6` the twelve frozen operations | 38 min | **0** |

Two in parallel, bounded by `B5`. **Zero returned, now across fifteen implementation
sessions.** Wave elapsed with convergence: about one hour, against `PROTOTYPE_WAVE_PLAN.md`
§4's 1–1.5 hours.

## 2. The chain composes — closure item 3 is answered

`B5` is the first session to drive the whole path, and it settled the question wave `B-I`
left open. The pinned `pdfplumber` reproduces the committed text layer **character for
character**, so `B3`'s request checksum matches its recording and the replay succeeds rather
than failing closed. Asserted directly, not inferred from a passing run.

The manifest's `page_text_sha256` values still differ from `pdfplumber` on all eight pages
and match `A4`'s reference extractor on all eight. That divergence is real and is now
understood to be harmless here: the chain uses no manifest offset. It remains a trap for any
future session that asserts those hashes against the pinned extractor.

**Corpus run, recorded adapter:** state `published`, empty degradation set, four stages
`succeeded`, **3 findings**, **5 CSV rows**, 4251 bytes, 17 columns, two exports
byte-identical, the same idempotency key creating no second run, and an interrupted `running`
run reconciling to `failed` with a reason.

## 3. Both sessions refused to widen a hotspot, and both were right

`B6` found **no HTTP framework in the lock**. It checked before writing code, then supplied
`Request`/`Response`/`Route`/`Router` in about a hundred stdlib lines and read the one
multipart operation with `email.parser`. It also found that the inherited `api/README.md`
promised "FastAPI transport adapters only", contradicting the lock, and **rewrote the README
rather than the lock** — the correct direction, since the lock has one writer and the README
is its own.

`B5` found seven of the seventeen CSV columns projected by no public query. Rather than
substitute `audit_run` for four columns §6 pins to `finding`, it wrote one query in its own
tree matching `B4`'s join shape verbatim and cross-checks its count against
`published_finding_count`, so it cannot quietly widen.

## 4. Mutation discipline produced findings about method, not only about code

Twenty-one mutations this wave, twenty red. The four that were *not* simply red are the
interesting ones:

* `B5` M1 caught a **vacuous test of its own**: `content.startswith(BOM)` with `BOM` imported
  from the module under test is true when `BOM` is `b""`. Now asserts the literal bytes. That
  is the seventh vacuous test this programme has caught.
* `B5` M11/M12 aimed at guards the **database already covers**: removing `assert_transition`
  left the reopening tests green, because `AM001` refuses the same move and maps to the same
  typed code. Two new tests now isolate each mechanism rather than leaving the application
  guard untested behind the trigger.
* `B5` M4a is **deliberately left green and recorded**: excluding ungrounded rows is
  over-determined, since `document_version` is also joined through `finding`, so two joins
  would have to be wrong.
* `B6` had a mutation come back **green because the patch reached nothing** — it patched
  `routers.build_router` while the conftest had bound the name directly. It reported that as
  a finding about method rather than quietly redoing it.

`B6`'s own leakage walk — required to walk a real body rather than read code — caught a
defect it had introduced: the `additionalProperties` refusal echoed the caller's property
name into `details.field`, so a property named `/etc/passwd` came back inside the envelope.

## 5. Open items — reconciled 2026-09-14, all closed except one

> Every item in this section is **closed** unless marked otherwise, and the one exception is
> item 6 of the `B-I` closure: the catalog has no code for usable output over a strict subset
> of the input. The two Gate C blockers were closed by the seam repair, the dead diagnostic
> path was accepted by owner ruling, `model_call.status` admits `truncated` and `details`
> values are screened. The text below is left as the record of what was found and why.

### 5.0 Original text

### 5.1 Two Gate C blockers, both verified by the integrator

Both sit in a peer's public surface, not in the frozen contract.

1. **`DocumentVersion.version_ordinal` is required** and `B1`'s `DocumentVersionRecord` does
   not carry it, so `getDocumentVersion` and `uploadDocument` cannot emit a valid body. `B1`
   withheld it under the opacity rule, but foundation invariant 3 says a display ordinal is
   **not an identifier** — it does not say it may not be shown, and the contract requires it.
2. **`Finding` requires `project_uid`, `version_uid`, `run_id`** and `B4`'s `FindingRow`
   carries none of the three. Worse, there is **no by-`finding_uid` read path at all**, so
   `getFinding` has no query to call.

### 5.2 The diagnostic path is dead code in the chain as composed

`B3` resolves each quote against the text layer and drops what does not resolve **before**
writing its artifact. `B4`'s gate therefore never sees an unresolvable anchor, and no
`grounded = false` row is ever written. Nothing ungrounded is published, so the safety
property holds — but §5.1's five-value `ungrounded_reason` vocabulary records nothing, and
*which* quotation the model invented survives only as a count in `stage_result.metrics`.

Two sessions each did the right thing locally and the composition made one of them
unreachable. This is the clearest example so far of what only a chain test can show.

### 5.3 Carried forward

> **Reconciled 2026-09-15 and now empty: all six items below are closed.** Checked against
> the tree at `ea3c8f3`, item by item, not against any closure record. This block is kept
> as written, with the disposition beside each item, because a register that is silently
> deleted teaches nothing about how long it stayed wrong.
>
> It had been **entirely obsolete for some time** while still reading as the list of what
> is open. `W2_CLOSURE.md` §2 records two wave-2 briefs built from stale records; this is
> the register that class of mistake comes from, and the reconciliation commit `80ff9d8`
> did not reach it. The cheap defence is the one wave 2 named: check the premise against
> the tree before building on it.

* ~~`model_call.status` admits `succeeded|failed`; `B3`'s provenance emits a third value
  `truncated`, exactly the case that yields a `partial` stage. `B5` maps it to `succeeded`
  and keeps the stop reason in `parameters`; the contract supplies no mapping.~~
  **Closed by `W2-PROV`.** `truncated` is a first-class `model_call` status with migration
  `0005` and two invariants giving it content. Note the direction: the mapping was onto
  `succeeded`, not `failed` — the wave-2 brief had it backwards, so the ledger had been
  filing truncated answers as clean successes.
* ~~`details` **values** are not screened by `auditmanager.shared.errors`, only keys and
  types. `B6` closed all four of its own sites; the kernel hole is open.~~
  **Closed.** `shared/errors/envelope.py` screens detail *values* with the same `_FORBIDDEN`
  patterns as a message and raises a dedicated `UnsafeDetailValue`, distinct from
  `UnsafeDetailKey` because the remedies differ. The code comment records the `B6` case that
  motivated it — a property named `/etc/passwd` echoed back inside `details.field`.
* ~~Eight further seam mismatches tabled in `src/auditmanager/api/README.md` — query
  surface, `listProjects` ordering, `createProject` idempotency, `appendDecision`'s
  unclaimed key, and a wrong claim in the document about which codes are retryable.~~
  **Closed.** That table now has ten rows and every one reads **Closed**, five of them by
  `W2-API`. The retryable claim was corrected in `contracts/api/v1/openapi.json` and
  resealed in `web/FRONTEND_LOCK.json` on 2026-09-11.
* ~~From wave `B-I`, still open: `ungrounded_reason` has no CHECK (and per §5.2 is also
  never written); blob identity against `rejected`; `OD-03` has no machine-readable
  ceiling.~~ **All three closed.** `ungrounded_reason` got its CHECK in migration
  `0003_open_items` and is written and selected (`findings/queries.py`). Blob identity
  against `rejected` was ruled accept-the-consequence by the owner — `GATE_B1_CLOSURE.md`
  item 2 — with the index kept and only the false comment changed; the consequence is
  stated at `ingest/reconciliation.py:251`. `OD-03`'s ceiling is machine-readable as
  `AUDITMANAGER_RUN_COST_CEILING_USD`, parsed in `bootstrap/settings.py` with a
  `ConfigurationError` on anything unparseable or non-positive.

**Where the open items actually live now.** `W2_CLOSURE.md` §3 and `P4_CLOSURE.md` are the
current registers; the owner-blocked set is `OD-17`, `OD-18` and the 21st error code.

## 6. What comes next, and why the order matters

The seam repair must precede convergence QA. `B-III` exists to judge whether the chain
composes; dispatching it against surfaces that cannot satisfy the frozen contract would make
it report the same two blockers a second time instead of finding what nobody has seen yet.
