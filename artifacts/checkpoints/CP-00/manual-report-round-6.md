# CP-00 manual acceptance — primary report, round 6

## Start record

```text
candidate_commit:      5b70ee4e6c29931924f0ff56da499c5cfa0ef9a7 (integration/W0.3)
tested_candidate_digest: 2b3929be6de447bd1c3a92ff1a9a4fe72bc12d4ee919f3d21af2a979e861582c
                       recomputed from candidate_digest_recipe by this tester; MATCHES
                       the value frozen in manifest.json
tree:                  5356a3cbb99ffef2eb88c72aedb3bbf43de7ef58
contract_manifest:     domain/analysis/events 1.0.0-draft.1; golden_selection_schema 1;
                       artifact_manifest_sha256 39721aac…, 100 files (recomputed, matches)
migration_head:        none (db/migrations holds only README.md, 298 bytes)
backend_runtime:       not applicable - architecture-only checkpoint
frontend_runtime:      not applicable - architecture-only checkpoint
local_infra_versions:  not applicable - architecture-only checkpoint
tester:                cp00_manual_tester, independent agent; authored none of the
                       reviewed artifacts, none of the QA test module, none of the QA
                       report; wrote nothing in this repository but this file
started_at:            2026-09-04T15:49:35+05:00
finished_at:           2026-09-04T15:55:30+05:00
```

### Digest confirmation

The recipe in `manifest.json:candidate_digest_recipe` was implemented from its own text,
without reading any existing implementation: `git ls-files` plus
`git ls-files --others --exclude-standard`, sorted; sha256 over, per path in order, the
UTF-8 path bytes followed by the raw 32-byte sha256 of the content; this manifest
contributes the sha256 of `json.dumps(manifest, sort_keys=True, separators=(',',':'))`
with `tested_candidate_digest` alone blanked, at the top level and in every
`acceptance_rounds` entry. 214 tracked paths, 0 untracked-not-ignored. The result equals
the frozen value. The tree in front of this tester is the tree round six was frozen on.

Three discrimination probes, because a digest that matches is worth nothing until it is
shown to be capable of not matching:

| Perturbation | Result |
|---|---|
| one newline appended to `README.md` | `1b4953bf…` — differs |
| one space appended to `manifest.runtime_fields` (prose only) | `1c509f36…` — differs |
| `evidence_bundle_digest` set to a non-null value | `1f51a07a…` — differs |

The second probe closes round three's finding 1: manifest prose is now inside the digest.
The third confirms the recipe's central claim — only the field being computed is blanked,
so the evidence digest will depend on the tested digest rather than floating free of it.

`artifact_manifest_sha256` was recomputed independently over the same recipe:
`39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` over 100 git-tracked
files under `contracts`, `fixtures`, `docs/architecture`, `scripts`. Matches.

## Test cases

### MT00-01 — Documentation navigation — `FAIL`

**What I did.** Walked the chain the README prescribes: `README` →
`docs/PRODUCT_SYNOPSIS.md` → `docs/architecture/ARCHITECTURE_BIBLE.md` →
`docs/architecture/ADR_INDEX.md` → `docs/program/ROADMAP.md` →
`docs/program/WAVE_EXECUTION_GUIDE.md` → `docs/stages/S00_architecture_and_behavior_freeze.md`.
Then swept every markdown link target across all 148 tracked markdown files, and
separately swept every backticked repository path, because a document can send a reader
somewhere missing without using link syntax. Then cross-checked S00's W0.3 task table
against `manifest.json:integrated_w03_tasks`.

**What I observed.** Every document in the chain exists. 0 broken markdown links across
148 files. The backticked-path sweep raised 14 unresolved paths; all 14 are legitimate on
inspection and none is a missing mandatory document:

- 8 are `[S]`-class citations, which `CP00_ARCHITECTURE_REVIEW.md` §2 defines as paths in
  the *refactoring architecture source*, read as
  `git show 0b937dc0e24d38fb98485a920152b83d2f19c982:<path>`. I confirmed that repository
  is present at `/root/projects/PDF-proverka/PDF-proverka`, that both pinned commits and
  the pinned Bible blob `040a514d` resolve there, and that `ADR_BIBLE.md` reads at the
  source commit. `manifest.frozen_inputs_note` states these do not resolve locally and are
  not expected to. Correct as written.
- `docs/architecture/presentations/` is named in `SOURCE_TRACEABILITY.md:70` precisely as
  an untracked directory *excluded* from the source snapshot.
- `fixtures/f.json`, `scripts/s.py` and a `../..`-traversing path in the W0-QA-01 review
  are synthetic paths in a test-fixture repository the review constructs.
- `ARCHITECTURE_LINT_RULES.md:101` cites `tests/contract/test_stage_registry.py` and
  `src/auditmanager/jobs/test_lease.py` as the conforming and violating examples of rule
  ALR-27. Illustrative by construction.
- `src/app` in `web/README.md` resolves relative to `web/`; `web/src/app` exists.
- `fixtures/private` is gitignored by design; `contracts/optimization/v1` is the future
  family `U-06` creates and which `U-06-OB-1` declares "not a frozen family before then".

All six W0.3 task SHAs in S00 lines 63–68 are ancestors of HEAD and their subjects match
their claimed deliverables.

**The failure.** The terminal document of the navigation chain misstates the status of the
task the checkpoint's independent verification rests on.

`docs/stages/S00_architecture_and_behavior_freeze.md:68` reads:

> `| W0-QA-01 | QA | Independent cross-family verification | W0-ARC-02, W0-CLN-01 | Accepted after six review rounds; evidence at `e7f39890`. |`

Both halves are contradicted by other plan-of-record documents in this same tree:

| Claim | S00:68 | `docs/program/tasks/W0-QA-01.md:3-6` | `docs/program/waves/W0.3_ratification_integration.md:124` |
|---|---|---|---|
| round count | six review rounds | **twelve** review rounds | eleven reopenings |
| evidence commit | `e7f39890` | `3da104e5…`, with `e7f39890` named **superseded** | `3da104e5…`, with `e7f3989` named **superseded** |

`docs/program/reviews/W0-QA-01.md` heads its own banner "Rounds two to twelve". So S00
sends a reader to a commit two other layers declare superseded, and gives a round count no
other document supports.

This is not an isolated stale line. Commit `7a94d44` states its own intent plainly —
"The task banner, the current-state entry and the wave execution row all still described
the superseded evidence commit and an earlier round count. Both earlier evidence commits
are now named as superseded" — and touched three files. The sweep was incomplete. Five
sites still present `e7f39890` as the live evidence commit:

| Site | Text |
|---|---|
| `artifacts/checkpoints/CP-00/manifest.json:7` | `"qa_evidence_commit": "e7f39890…"` |
| `artifacts/checkpoints/CP-00/manifest.json:29` | `integrated_w03_tasks.W0-QA-01 = "e7f39890…"` |
| `docs/program/CURRENT_STATE.md:56` | `qa_evidence_commit e7f39890… — where its test and report live` |
| `docs/program/tasks/W0-INT-01.md:36` | `W0-QA-01, accepted and integrated at e7f39890…` |
| `docs/stages/S00_…:68` | `Accepted after six review rounds; evidence at e7f39890` |

`CURRENT_STATE.md` is internally contradictory across eight lines: line 48, rewritten by
`7a94d44`, names `3da104e5…`; line 56, in the same file and untouched, still names
`e7f39890`. And `manifest.qa_evidence_history` records only `854a6820` as superseded — it
omits `e7f39890`, the supersession the task and wave layers both assert.

The freeze commit `5b70ee4`, which is the tree under test, was made *after* `7a94d44` and
edited `manifest.json` alone without correcting either field. Nothing catches this: I
grepped `tests/` and `scripts/` and no check anywhere asserts `qa_evidence_commit` or
`integrated_w03_tasks`.

This matters beyond tidiness. It is a split source of truth about which bytes the
independent verification actually certified — the exact defect class this program states
it exists to prevent, and the class every prior failed round was failed on. A reader
arriving at this repository by the documented route is told the wrong answer.

**Owning task to reopen:** `W0-INT-01`. The W0.3 frozen-hotspots table assigns "CP-00
review ratification, current/checkpoint state and checkpoint evidence" to `W0-INT-01`, and
all five sites fall inside it. Note that `7a94d44`'s own message records that these paths
sit outside the post-freeze delta ceiling, so the correction cannot be made without voiding
round six; a new round is required.

### MT00-02 — Greenfield boundary — `PASS`

**What I did.** Traced the mandatory runtime path and looked for anything that would
require running or importing legacy: read `ADR-0001`, enumerated `src/`, and grepped
`src/`, `scripts/`, `tests/` and `web/` for legacy imports, then swept `contracts/`,
`requirements/`, `infra/`, `db/` and `web/src/` for legacy references on runtime surfaces.

**What I observed.** `src/` holds seventeen files: sixteen README stubs and one 97-byte
`__init__.py` reading "AuditManager greenfield package. Production implementation starts
after CP-00/CP-01 gates." There is no runtime to couple. No import of `backend.app`,
`pdf_proverka` or any legacy module exists anywhere in `src/`, `scripts/`, `tests/` or
`web/`. Grep for `legacy` across `contracts`, `requirements`, `infra`, `db` and `web/src`
returns hits only in `contracts/analysis/v1/README.md`, and every one is provenance
framing: the two legacy maps are labelled "Evidence-only", and the README states "No legacy
order is copied" and "the legacy names stay visible as evidence rather than as policy."

`ADR-0001` is unambiguous: "No runtime Strangler dependency is required. Legacy is
read-only evidence source… Importing a large legacy service/router/pipeline manager as a
shortcut is forbidden without a new ADR." Legacy appears only as oracle, fixture source,
edge-case catalogue and parity reference, which is exactly the README's stated role.

### MT00-03 — Identity walk — `PASS`

**What I did.** Took `GJ-03` from the accepted inventory — "Review a finding, rerun on V+1
with provider failure, then manually resolve" — and walked it on paper through
`Finding` / `FindingObservation` / `ExpertDecision`, then checked whether any step needs a
display ordinal as a foreign key.

**What I observed.** The legacy behaviour is `EX-08`: an expert carries a prior-version
judgment forward, "Existing non-empty human/auto verdict is preserved; wrapper is
fail-soft", anchored at
`32b9d903…:backend/app/services/findings/decision_carryover_service.py:run_decision_carryover@436`.

The target walk:

1. The V1 run emits a `FindingObservation` (`fobs`) carrying page/geometry/source
   artifacts, stage/version and confidence metadata, bound to exactly one `run_id`.
   `state-machines.json` states an observation "belongs to exactly one run_id and is never
   edited after the run publishes."
2. The expert appends an `ExpertDecision` against the `Finding` (`fnd`), not against the
   observation. `DOMAIN_MODEL.md:89-91` shows the ledger as an append-only event sequence
   with `CurrentVerdict = projection(last valid event according to rules)`.
3. The V+1 rerun is a new `AuditRun` and emits *new* observations. `identifiers.json:91`:
   "A rerun creates new observations and never rewrites or removes earlier ones."
4. Carryover happens only if the versioned matching policy justifies it. Same rule: "When
   the versioned matching policy cannot justify carryover it allocates a new `finding_uid`
   instead of reusing one." So the expert decision survives the rerun *through the stable
   identity policy and only through it* — which is the expected result stated verbatim.
5. Provider failure leaves the projection pending/`needs_manual_review` rather than
   inventing a verdict; the revocation rule at `identifiers.json:266` confirms the
   projection "never restores an earlier superseded verdict automatically."

`F-NNN` is never needed as a foreign key at any step. `identifiers.json:21` bars it
explicitly: "a display ordinal such as F-014… none of them is an identity and none may be
used as a foreign key", listed again at line 148. `DOMAIN_MODEL.md:67` agrees: "Display
ordinal such as `F-014` belongs to a run/read model and **never** serves as FK."
`ADR-0010` carries the same separation.

### MT00-04 — Run/job/attempt walk — `PASS`

**What I did.** Modelled provider timeout → retry → stale worker result against
`contracts/domain/v1/state-machines.json`, checking at each step that the three identities
stay distinct and that the stale attempt cannot publish.

**What I observed.** Three separate machines with three stated purposes: `audit_run` is
"the business history of one audit execution request", `job` is "the durable schedulable
work item that owns retry policy and the sequence of Attempts", `attempt` is "one concrete
leased execution of a Job by one Worker, **and the only place where publication authority
exists**."

The walk:

1. **Timeout.** `machines.job` `leased` → trigger "lease expiry or missed heartbeat", guard
   "the Attempt is moved to `lost` in the same transaction so it can no longer publish",
   `on_violation: stale_attempt`. Authority is withdrawn transactionally, not by timer
   convention.
2. **Retry.** `machines.job.retry` creates "a new `attempt_id` whose execution token
   supersedes the previous one; never a new `run_id` and never a new `job_id`", and
   "Retry, resume, restart and worker failover reuse the same Job and create a new Attempt.
   None of them creates, reopens or duplicates an AuditRun." The `audit_run` machine states
   the converse: "A rerun is a new top-level audit command and allocates a new `run_id`. It
   never reopens a terminal run."
3. **Stale result.** The old Attempt is `superseded`: "A newer Attempt for the same Job took
   authority. Any result this Attempt delivers afterwards is stored as immutable evidence,
   is never applied to project state and is answered with `stale_attempt`." The same
   store-only rule is restated for `lost` and `cancelled`. The exclusivity rule is explicit:
   "At most one Attempt per Job may publish at any instant: the Attempt in `running` that
   presents the current execution token, checked **inside the publishing transaction**",
   with `execution_token_invalid` and `stale_attempt` as the two violations.

The three identities never merge, and a stale Attempt has no path to publication —
its late result is evidence, never state. This matches `GJ-09` in the inventory ("Mark
attempt lost, create a new attempt, then deliver the old result late → New attempt
authority, old result stored-only, visible history and stale rejection") and `ADR-0007`.
The numeric lease/heartbeat/grace and retry-budget values are absent by declared defer
(`OQ-02`, `OQ-04`), not by omission — see MT00-06.

### MT00-05 — Comparison ownership — `PASS`

**What I did.** Modelled auto suggestion → user-approved sheet link → recompute → AI review
against `ADR-0013`, `contracts/comparison/v1/README.md`, the `DOMAIN_MODEL.md` comparison
diagram, and the legacy `CP-01`–`CP-06` rows and `GJ-05` journey in the inventory.

**What I observed.** The four layers are separated by construction. `ADR-0013`:
"Automatic sheet matching produces rebuildable suggestions. User-approved links are owned
state and survive recomputation. Deterministic text exclusions/diff and raw graphic
evidence are immutable per comparison revision. AI review/synthesis is a derived artifact
keyed by raw checksums." The contract README repeats the same five-way separation, and
`DOMAIN_MODEL.md` closes its comparison section with "Recompute suggestions cannot mutate
approved SheetLink."

Walking the scenario:

1. Auto suggestion produces a `SuggestionSet`, marked rebuildable.
2. The user approves a `SheetLink`. Legacy `CP-02` corroborates the direction — "Idempotent
   session/pair, disposable suggestions and **authoritative** saved link file… saving
   replaces the prior explicit decision and supersedes repair suggestions."
3. Recompute rebuilds suggestions. It cannot touch the approved link: suggestions are the
   rebuildable layer, the link is the owned layer. `GJ-05` asserts exactly this outcome —
   "Idempotent reuse, downstream stale invalidation, partial AI-group reuse, **raw
   deterministic evidence unchanged**."
4. AI review is additive and keyed to source checksums, downstream of the deterministic
   artifacts. Legacy `CP-04` is "Additive AI review/final/change-summary JSON" consuming
   "Current deterministic comparison/difference artifacts". The AI layer adds its own
   artifact; it does not edit the raw difference record.

Recompute does not overwrite the approved link, and AI does not change raw deterministic
evidence. Both expected results hold.

Where legacy is weaker than the target, the inventory says so rather than claiming parity:
row 243 records "Immutable/raw evidence artifacts | **partial** | CP-03/04 preserve
deterministic inputs from AI mutation; filesystem replacement/immutability guarantees are
not universal", and `CP-06` records graphic comparison as "not observed". Those are
recorded gaps, not silent ones.

### MT00-06 — Unresolved decisions — `PASS`

**What I did.** Read the proposed ADR and the owner decisions, enumerated the open set,
then ran a numeric sweep over `contracts/` and `fixtures/` for any invented
retention/tenant/IdP/lease/backoff value.

**What I observed.** `ADR-0014` carries `Status: proposed` in its own header and is the
sole entry in `manifest.architecture_defer`. `CP00_ARCHITECTURE_REVIEW.md` §11 records a
disposition for all six `U-*` inputs, with exactly one still open:

| Item | Status |
|---|---|
| `U-04` tenant model, IdP, TTL matrix, legal-hold authority | **open** by explicit owner disposition, deadlines `W2-C-01` and `W9-C-01` |
| `U-01` cost thresholds | deferred with deadline (`W3-C-01`, before first paid-provider canary) |
| `U-02` workspace isolation | resolved |
| `U-03` lint-rule owning task | assigned (`W0-ARC-02`) |
| `U-05` coverage policy | conditionally accepted |
| `U-06` optimization bounded context | resolved, with obligations `U-06-OB-1`/`U-06-OB-2` |
| `OQ-02` lease/heartbeat/grace | deferred to the jobs/operations slot, `W4-JOB-01` |
| `OQ-04` retry budget and backoff | deferred to `W4-C-01`/`W4-JOB-01` |
| `E-05` source-ADR proposed statuses not inherited | open escalation, carried forward |

§11 bounds what `U-04` blocks to four exact consequences and states "no tenant, IdP, TTL,
retention or legal-hold value enters any contract."

I tested that claim rather than accepting it. A regex sweep across `contracts/` and
`fixtures/` for `ttl|retention|lease|heartbeat|grace|backoff|retry_budget|budget|timeout`
followed by a numeric value returns nothing, and a sweep for bare duration literals
(`N days|hours|minutes|seconds|ms`) returns nothing. `identifiers.json:251` and
`contracts/domain/v1/README.md:687` state the deferral in the contract itself: "No numeric
value is invented here and no lease implementation may proceed without that decision."
`error-codes.json` carries `idempotency_key_stale` as the fail-closed answer once a command
record is gone, with the retention window explicitly named as the unresolved owner
decision.

Unconfirmed values are unresolved and labelled, not defaulted.

I also verified the three items `manifest.known_pre_ratification_items` self-discloses,
because a stale disclosure would itself be a defect. All three are accurate: the `PD-02`
precondition text does still read "not yet met" in the review documents while
`legacy-stage-name-map.json` does carry 62 name rows over 31 alias-bearing declaration IDs
(counted); `ARCHITECTURE_LINT_RULES.md:604` does still say the document's own JSON is
"still untracked"; and `ADR_INDEX.md:31,41` does still enumerate `PD-01`–`PD-04` while five
owner decisions are recorded. All three are disclosed rather than hidden, and all three are
assigned to `W0-INT-01`.

## Final acceptance checklist

- [x] **No hidden Strangler runtime dependency.** `src/` contains no executable code
      beyond a docstring; no legacy import exists in any tracked source path; every legacy
      reference on a contract surface is provenance-tagged; `ADR-0001` forbids the
      dependency outright. (MT00-02)
- [x] **All key bounded contexts have a data owner.** `CONTRACT_CATALOG.md:9-16` names an
      owner per contract family (ARC, API, integration, ENG, CMP, migration owner);
      `DOMAIN_MODEL.md:38-52` enumerates twelve contexts with their aggregates; `ADR-0003`
      fixes the rule as "One aggregate/entity has one authoritative writer." The W0.3
      frozen-hotspots table assigns a single owner to every writable path in the wave.
- [x] **Shared contract freeze/process is understandable to a reviewer without verbal
      explanation.** `VERSIONING_AND_FREEZE_POLICY.md` states three freeze levels, the
      version-bump rules and a seven-step freeze-break procedure. I reproduced both
      checkpoint digests from the written recipes alone, with no prior knowledge of either
      value and without reading any existing implementation. A process I could execute cold
      from its own prose is one a reviewer can follow unaided.

The checklist passes. It does not rescue MT00-01: the checklist asks whether the freeze
*process* is comprehensible, and it is; MT00-01 fails on a *value* that four documents and
the checkpoint manifest state incorrectly.

## Known limitations

1. **I am an agent, not a person.** For an architecture-only checkpoint the six cases are
   reading and judgment over documents rather than exercise of a running system, so an
   agent is the closest available analogue — not a substitute. Recorded so a later reader
   weighs this evidence for what it is.
2. **A runbook step could not be executed as documented.** Stop/cleanup says "Stop the
   local stack using the documented command." There is no local stack at CP-00 and no such
   command exists: `infra/` holds four README files and no compose or task-runner
   definition, and `docs/manual-tests/README.md` scopes `make stop` and its siblings to
   "Expected command surface **after CP-01**", fixed by `W1-INT-00`. I did not substitute a
   step. Nothing was started, so nothing was stopped; no credentials, tokens or
   fault-injection overrides were created. The step is inapplicable at CP-00 rather than
   failed, and the runbook does not say so. Minor, and owned by `W0-INT-01` if the CP-00
   runbook is to be made self-consistent.
3. **I did not run the automated suite.** That is the automated stream's verdict, not mine,
   and executing pytest would write bytecode caches into the tree I am certifying. My
   single allowed write is this report.
4. **I did not judge the four reviewed families for internal contract correctness.** That
   is `W0-QA-01`'s cross-family verification. I verified their digest invariance
   (`artifact_manifest_sha256` over 100 files) and read them as a consuming reader, which is
   what these six cases ask.
5. **Comparison is judged at architecture level only.** `contracts/comparison/v1/` is a
   nine-line README; the family freezes at S06 per the roadmap. MT00-05's ownership rules
   live in `ADR-0013` and `DOMAIN_MODEL.md`, which is the right altitude for CP-00, but no
   machine schema constrains them yet. Same for `contracts/api/v1/` (twelve lines).
6. **`tested_candidate_digest` is reproducible only while `evidence_bundle_digest` is
   null.** Probe three above shows the tested digest moves once the evidence digest is
   written. That is the recipe working as designed, and a later reader can still reproduce
   it by checking out `5b70ee4`. Recorded so nobody mistakes the expected change for
   tampering.

## Overall verdict

`FAIL — 5 of 6.`

`MT00-01` fails. `MT00-02` through `MT00-06` pass.

| Case | Result |
|---|---|
| MT00-01 Documentation navigation | **FAIL** |
| MT00-02 Greenfield boundary | PASS |
| MT00-03 Identity walk | PASS |
| MT00-04 Run/job/attempt walk | PASS |
| MT00-05 Comparison ownership | PASS |
| MT00-06 Unresolved decisions | PASS |

Per the runbook's Result clause, a checkpoint cannot be tagged while a mandatory case is
`FAIL`. One blocking task follows.

## Finding

**F-6.1 — the superseded QA evidence commit is still recorded as current in five places,
one of them the checkpoint manifest.** `W0-QA-01` was accepted at
`3da104e5d6fafb2a581bda377a07911183af803f` after twelve review rounds, and
`e7f39890211b52e10d2619c5ddcb85a3d8c7df22` was declared superseded by the task and wave
layers. Five sites disagree: `manifest.json:7`, `manifest.json:29`,
`CURRENT_STATE.md:56` (contradicting line 48 of the same file), `tasks/W0-INT-01.md:36`,
and `stages/S00_…:68` — the last also stating "six review rounds" against the task layer's
twelve. `manifest.qa_evidence_history` omits the `e7f39890` supersession entirely. No test
asserts either manifest field. The freeze commit `5b70ee4` edited the manifest after the
acceptance was recorded and did not correct it, so the drift is sealed into the tested
candidate.

**Owning task to reopen: `W0-INT-01`** (W0.3 frozen-hotspots: "CP-00 review ratification,
current/checkpoint state and checkpoint evidence"). All five sites are inside its allowed
paths. Because `7a94d44` records that these paths lie outside the post-freeze delta
ceiling, the correction voids round six and a round seven is required.

Secondary, and not counted as a separate finding because the document is explicitly a
point-in-time record owned by another task: `docs/program/reviews/W0-QA-01.md:72` still
calls `e7f39890` "the live value" and anticipates round twelve landing "in a later evidence
commit" that has since landed.

Nothing else was found. No contract, schema, fixture, state machine or identifier defect
appeared in any of the six walks. As in rounds one and two, the sole blocker is
integrator-owned metadata and state rather than a defect in the reviewed families — which
is itself worth recording, because it is now the third time the same layer has failed the
same way.
