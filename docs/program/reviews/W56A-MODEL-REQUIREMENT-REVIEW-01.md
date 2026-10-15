# W56A-MODEL-REQUIREMENT-REVIEW-01 — when to verify model identity

**Decision status: pending owner selection.** This review answers the owner's
request to reconsider the W56a requirement separately. It does not amend
`R-133`, `W56-PLAN.md` or the stopped `W56A-FREEZE-01`.

## Evidence and boundary

`R-133` forbids publishing a live answer from another model and requires a
successful identity probe before live recordings. The stricter timing — two
calls on each of the recording and stand gateways *before SEAL* — is in
`W56-PLAN.md` §§A3.5, A4. The stand's one explicit-model call requested
`anthropic/claude-opus-5` and reported `meta/muse-spark-1.3-contributor`.
For 14 input and 16 output tokens it reported $0.0000046 versus $0.00047 at
the locked Opus rates. This is a failed model-selection and price signal;
the recording gateway is still unidentified. Neither the uncalled default
probe nor a second stand call can be counted as PASS. The $5 wave ceiling in
`R-134` remains in force.

The current proxy sends a configured model in the request, but its successful
response parser does not carry the returned `model` into `ModelResponse`.
The stage can then record the requested model. Therefore a code-only test of
synthetic wrong-model responses is needed, but cannot replace the live probe.
The gateway could echo a requested name while routing another model; the
separate default identity and rate signal remain necessary.

## Choices

| Choice | Development now | Model gate and consequence |
| --- | --- | --- |
| A. Keep the existing freeze | No W56a code lane | Correct the stand route, locate the recording gateway, run both calls on each, then complete `W56A-FREEZE-01` and SEAL. |
| **B. Split the freeze (recommended)** | A new recorded-only development freeze grants SEAL without a gateway pin and a disjoint synthetic GENERATOR preparation; merge the generator only after SEAL | Two-gateway probe and a sole-owner `MODEL-PIN` task still precede PROVIDER, live recordings, v2 activation, close and release. The failed stand route must be corrected. |
| C. Drop or relax model identity | Would permit wrong-model output or unverified provenance | Requires a separate explicit reversal of `R-133`; the failed probe supplies no evidence that this is safe. Not recommended. |

Choice B moves **only the placement of the gateway verification**. It does not
accept a different model, deem the stand check successful, change the locked
rates, or bypass the final gate. It offers useful offline work while gateway
access is resolved.

## Exact proposal if the owner chooses B

1. Record a new owner ruling authorising a *recorded-only development freeze*.
   Amend `W56-PLAN.md` §§A3.5, A4, A5 and A7. Keep the historical stopped
   freeze and failed probe unchanged; add an addendum that links the new grant.
2. `W56A-DEV-FREEZE-01` rechecks the non-live pins on the current tree and
   grants only `W56A-SEAL-01` and `W56A-GENERATOR-PREP-01`. SEAL owns its
   existing contract, schema and migration surfaces **except** `P02_LOCK.json`.
   The generator owns only new seeded fixture and corpus paths, based on
   W55b's sealed portal bundle and the seven `R-129` categories. The two
   lanes can work in separate worktrees; its corpus joins the integration
   line after SEAL. No v2 proxy mode is activated by these lanes.
3. `W56A-MODEL-PIN-01` is the sole W56a owner of `P02_LOCK.json`. It may
   write a concrete gateway name only after the corrected stand and distinct
   recording gateways each pass the selected-model identity/rate call and
   default-model call, within the precommitted tolerance and spend ledger.
   A gateway failure remains a stop; no name is inferred from `model_id`, a
   stub, or the failed response. PROVIDER starts after this task's merge.
4. PROVIDER must refuse proxy startup when the selected gateway name is
   missing, stub or inconsistent with the lock. A successful HTTP 200 with a
   missing or different reported model yields typed
   `model_identity_mismatch`, a failed stage, zero published findings and no
   automatic paid retry. The received effect and reported usage/cost must be
   durably recorded before rejecting content; a plain adapter `DomainError`
   currently loses that distinction. Keep v1 request, response hash and
   recording bytes unchanged.
5. All live recordings, live evaluation, stand acceptance, W56a close and
   release remain behind the two-gateway PASS and subsequent full gate.
   This review grants no push to `origin/dev` or `origin/main`.

The owner decision needed is precise: **permit recorded-only SEAL and
GENERATOR preparation before two-gateway PASS, and transfer sole
`P02_LOCK.json` ownership from SEAL to MODEL-PIN?** An affirmative decision
authorises drafting the ruling and grants; it is not itself a claim that any
gateway passed.

## Checks and handoff

Only this review and its task definition are changed. No contract, migration,
runtime code, fixture, deployment file or forbidden hotspot is touched.
The focused governance and prose suite passed **93 tests** on this review
candidate. The first run found a task-format issue in the captured command;
it was corrected before the passing run. The committed changed-path and
whitespace checks are recorded in the integration handoff. Until the
owner chooses B or supplies a passing gateway for A, `W56A-FREEZE-01`
remains STOPPED and the current plan grants no implementation lane.
