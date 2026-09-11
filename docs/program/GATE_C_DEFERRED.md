# Gate C — deferred pending a live provider credential

> **Owner decision, 2026-09-11: defer.** `C2` is written and dispatchable; it is not
> dispatched. Everything before it is complete and green.

## 1. Why

`PROTOTYPE_PROFILE.md` §8 criteria 4 and 5 require a **live** `text_analysis` run — "observe
at least two seeded issues in the live run". There is no `ANTHROPIC_API_KEY` on this host and
no provider profile. The call cannot be made, and no amount of test engineering substitutes
for it: the recorded path proves the machinery works, and cannot prove that the model, given
this prompt, finds the two seeded contradictions and leaves the six near-miss controls alone.

That is the product question the whole programme exists to answer, so answering it on a
recording would be answering a different question.

Running `C2` now would certify nine criteria and report the tenth as not exercised, then have
to run again when a credential arrives. The owner chose to wait rather than pay for the
certification twice.

## 2. What unblocks it

One value: `ANTHROPIC_API_KEY` in the process environment. Nothing else is missing.

The composition root already refuses to start in live mode without it — that refusal is
tested — so supplying it is the whole change. `OD-02` pins `claude-opus-5` with
`claude-sonnet-5` as the cheaper tier, and `OD-03`'s ceiling is still a $1.00 stand-in that
the owner has not ruled on; one run over the eight-page corpus costs cents against it.

If the owner instead names a different provider, that is a revision of `OD-02`: a new root
pin and a new adapter, which is a serial session **before** `C2`, not a variation of it.

## 3. State at the deferral

| | |
|---|---|
| Backend suites | 590 tests + 116 subtests, exit `0`, one battery command, order-independent |
| Frontend suites | 287 tests, exit `0` |
| `make foundation` | exit `0` |
| Sessions dispatched | 19, **zero returned for remediation** |
| Composed application | 12 operations wired; refuses to start on any missing dependency |
| All four PC-01 screens | mounted and carrying weight in the build |

`docs/program/dispatch/C2.md` is the dispatch text, base `e7965472`. It is written to run
criterion 5 live when a credential is present and to **report it by name as not exercised**
when it is not — never skipped silently, never passed on a recording.

## 4. What is still open, and who owns it

None of these blocks `C2`; all are recorded in `GATE_B1_CLOSURE.md` and `GATE_B2_CLOSURE.md`.

- `OD-03` has no owner-decided cost ceiling. **Needed before the first live run**, which
  makes it the one open item the deferral does not postpone.
- `ungrounded_reason` has no CHECK and is never written: the analysis stage drops
  unresolvable anchors before the gate can see one. `B-III` judged PC-01 can accept this and
  showed the gate is still load-bearing; the five-value vocabulary has no producer.
- `blob_id` is content-derived **and** the primary key, so a blob moved to `rejected`
  permanently bans those bytes. Needs an owner ruling, not a patch.
- `model_call.status` admits no `truncated`, which the provenance emits.
- No query surface accepts the cursor, limit, category or verdict parameters the contract
  declares.
- The CP-00 historical suites remain red by construction and quarantined by
  `PROTOTYPE_PROFILE.md` §6.3; every prototype file added widens that drift. Owned by the
  CP-00 line.

## 5. Measured throughput, for the forecast

Nineteen sessions, none returned for remediation. Authoring 16–56 minutes each; the two
waves of six and two ran in about two hours and one hour respectively including convergence.

The figure that did not exist when this programme was forecast — rounds-to-accept — is
**zero across nineteen implementation sessions**. Rework did not vanish; it moved into the
integration slot, where the integrator made twelve repairs the sessions could not, because
an executable gate can tell an integrator what a prose gate cannot.

Nine tests have been caught passing or failing without exercising what they named. The shape
was identical every time: the test asserted a property of the fixture rather than of the
code. That count is the most transferable thing this programme has produced.
