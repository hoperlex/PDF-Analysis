# CP-00 manual acceptance — round 7

Runbook: `docs/manual-tests/CP-00_architecture.md`, executed as written.

## Start record

```text
candidate_commit:          c1376e1cf0ca39d137c3f88f1a823757de839bef
tree_hash:                 edeefeb7e2cfd488d5fb08c159ad17b2f15a5421
tested_candidate_digest:   ad26b42fb99f9ccce7d0bd8ce3b6986e277a29b42d346adc454463aa489092b6
                           recomputed independently; MATCHES the manifest and the round-7 entry
artifact_manifest_sha256:  39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
                           recomputed independently over 100 files; MATCHES
contract_manifest:         artifacts/checkpoints/CP-00/manifest.json
contract_versions:         domain 1.0.0-draft.1; analysis 1.0.0-draft.1; events 1.0.0-draft.1;
                           golden_selection_schema 1; comparison not-active
migration_head:            none — db/migrations carries only README.md
backend_runtime:           not applicable - architecture-only checkpoint
frontend_runtime:          not applicable - architecture-only checkpoint
local_infra_versions:      not applicable - architecture-only checkpoint
tester:                    cp00_manual_tester, independent manual acceptance stream
started_at:                2026-09-04T11:29:20Z
finished_at:               2026-09-04T11:37:31Z
```

Working tree was clean at start (`git status --porcelain` empty) and clean at finish.
The parallel automated stream had not written its round-7 report at either point, so
every measurement below was taken over the frozen candidate with no untracked additions.

### Independence

I authored none of the reviewed artifacts, none of `tests/contract/test_cp00_candidate.py`,
none of `docs/program/reviews/W0-QA-01.md`, and neither round-6 report. I did not carry
forward any round-6 verdict; every judgement below was re-derived. I wrote exactly one
path in this repository: this report.

### Digest confirmation and discrimination probes

`candidate_digest_recipe` was implemented from the manifest text alone, without reading
the round-6 implementations: `git ls-files` plus `git ls-files --others --exclude-standard`,
sorted, 216 paths; sha256 over the UTF-8 path bytes followed by the raw 32-byte content
digest; the manifest's own contribution taken over
`json.dumps(manifest, sort_keys=True, separators=(',',':'))` with `tested_candidate_digest`
blanked at the top level and in every `acceptance_rounds` entry, `evidence_bundle_digest`
left at its real value.

A match is only worth something if a mismatch were possible. Eight probes:

| # | Perturbation | Digest changed | Expected | Result |
|---|---|---|---|---|
| P1 | one byte appended to `contracts/README.md` | yes | yes | OK |
| P2 | one byte appended to the manual runbook | yes | yes | OK |
| P3 | `tested_candidate_digest` rewritten to 64 zeroes | no | no | OK |
| P4 | per-round `tested_candidate_digest` rewritten | no | no | OK |
| P5 | `evidence_bundle_digest` set to a value | yes | yes | OK |
| P6 | `ratified` flipped to `true` | yes | yes | OK |
| P7 | `qa_evidence_commit` reverted to `e7f3989…` | yes | yes | OK |
| P8 | no-op mutation (canonicalisation stability) | no | no | OK |

P3 and P4 confirm the self-reference is the only thing blanked. P5 confirms the binding
the recipe claims: the evidence digest cannot float free of the tested digest. P7 is the
material one for this round — it shows the round-6 remediation genuinely changed the
tested input, so voiding round six was required and not discretionary.

## Test cases

### MT00-01 — Documentation navigation — **FAIL**

**What I did.** Walked the chain the README prescribes: `README.md` →
`docs/PRODUCT_SYNOPSIS.md` → `docs/architecture/ARCHITECTURE_BIBLE.md` →
`docs/architecture/ADR_INDEX.md` → `docs/program/ROADMAP.md` →
`docs/program/WAVE_EXECUTION_GUIDE.md` → `docs/stages/S00_architecture_and_behavior_freeze.md`.
Then checked every relative markdown link in the repository, then every backticked
path-like token, then verified the state layer against the contract manifest.

**What I observed — the parts that pass.**

Every document in the README chain exists. 150 tracked markdown files carry 252 relative
links; 0 are broken. 325 backticked path-like tokens resolve except 45, and all 45 are
legitimate: legacy-repository source paths carried under the `[S]` source-evidence
notation (`backend/app/main.py`, `docs/architecture/ADR_BIBLE.md`,
`docs/architecture/adr/ADR-0018-domain-contract-v1.md` and the rest are documents of the
refactoring source at its own pinned commit, not of this repository), and illustrative
placeholders in prose (`fixtures/f.json`, `scripts/s.py`, `GJ-01/manifest.json`).
`docs/architecture/REPOSITORY_LAYOUT.md`'s tree matches the real tree directory for
directory. The bootstrap package is self-sufficient in the sense the case asks about: no
mandatory document is absent.

I also re-derived the round-6 remediation independently rather than accepting it. All
five sites round six named now carry `3da104e5d6fafb2a581bda377a07911183af803f`:
`manifest.qa_evidence_commit`, `manifest.integrated_w03_tasks.W0-QA-01`,
`CURRENT_STATE.md:56` (now agreeing with line 48), `tasks/W0-INT-01.md:36`, and the `S00`
row at line 68, which also now reads "twelve review rounds" against the task layer's
twelve. `qa_evidence_history` carries both superseded values. Every surviving mention of
`e7f3989` in the tree is either round-six evidence documenting the defect or a row that
names it as superseded on purpose — with the two exceptions recorded as F-3 below. The
round-count arithmetic is consistent where it is stated: three reopenings plus eight
further reopenings is eleven, and eleven reopenings across twelve rounds is what the wave,
the task banner and `S00` all say.

**What I observed — the failures.**

**F-1. The round accounting is two rounds stale in three documents, and one of them
tells a reader to redo work that is already done.** `AGENTS.md:7` makes
`docs/program/CURRENT_STATE.md` the first document anyone reads. Its "Next integration
tasks" section says:

> `CURRENT_STATE.md:232-234` — "Five acceptance rounds are now in the record. Rounds one
> and two failed; round three passed and is **spent**; round four was voided before
> dispatch; round five is owed and cannot start until the reopened `W0-QA-01` is
> integrated."

Seven rounds are in the record. `manifest.current_round` is 7 and `acceptance_rounds` has
seven entries. Round five is `void`, not owed. Round six ran and returned `FAIL`. Round
seven is the frozen round. And `W0-QA-01` is integrated — at `3da104e5`, stated 185 lines
earlier in this same file at lines 46-48, in `manifest.integrated_w03_tasks`, in the wave
execution table and in the task's own banner. So line 234 contradicts line 48 of the file
it is in. That is the identical defect shape round six failed on, at a different site.

Two more statements in the same section inherit it: line 236 "Every blocker across all
five rounds", and lines 245-247 "Order from here: integrate the reopened `W0-QA-01` …
freeze `tested_candidate_digest` for round five".

The same staleness appears in two further documents:

| Path | Text | Reality |
|---|---|---|
| `docs/program/CHECKPOINT_REGISTRY.md:5` | "round-3 acceptance spent, round 5 owed" | round 5 void; round 7 owed |
| `artifacts/checkpoints/CP-00/acceptance.md:7-8` | "Round 5 is owed and neither earlier `PASS` transfers to it" | round 7 is owed |
| `artifacts/checkpoints/CP-00/acceptance.md:11` | "which round 5 must not repeat" | applies to round 7 |

All three statements entered at `ae59d8b`, the commit that voided round four, and were
true then. They have not moved through the void of round five, the failure of round six or
the freeze of round seven. `acceptance.md` is the mildest case because its header declares
itself history, but "Round 5 is owed" is a present-tense claim about the current state and
it is wrong.

The consequence for the reader this case is written for: an engineer following the
documented entry point cannot learn which acceptance round the program is in from the
state layer, and is directed to perform an integration that is already committed. They
must go to the manifest, which contradicts all three documents.

**Owning task: `W0-INT-01`.** All three paths are in its declared allowed paths
(`docs/program/CURRENT_STATE.md`, `docs/program/CHECKPOINT_REGISTRY.md`,
`artifacts/checkpoints/CP-00/**`), and the wave's hotspot table assigns
"current/checkpoint state and checkpoint evidence" to it.

**F-2. `W0-INT-01`'s own status banner asserts a condition its own dependency list
denies.** `docs/program/tasks/W0-INT-01.md:3-9`:

> "Every preceding W0.3 task is integrated and both acceptance streams returned `PASS` on
> the third round, but two conditions are unmet. `W0-QA-01` is reopened: its suite
> currently accepts a ratification that is declared and not performed."

`W0-QA-01` is not reopened. Line 36 of this same file — corrected by `afe1895` — says
"accepted and integrated at `3da104e5…`". The wave execution table says "**accepted**".
The task banner says "completed; accepted after twelve review rounds". The banner also
presents round three as the last acceptance event, omitting rounds four through seven.

This matters more than an ordinary stale line because the banner is the gate: it is what
tells a reader whether `W0-INT-01` may proceed, and it names a blocker that no longer
exists while omitting the one that does. The remediation commit edited line 36 of this
file and left line 5 contradicting it, so the file was internally inconsistent when the
round-7 candidate was frozen.

**Owning task: `W0-INT-01`.** Its allowed paths name `docs/program/tasks/W0-INT-01.md` —
"this task's own status banner and handoff, which no other task may close" — so this is
precisely the write it is authorized and obliged to make.

**F-3. The integrator's correction to the QA report left that file contradicting
itself.** Section 1 of `docs/program/reviews/W0-QA-01.md` now names `3da104e5` as the live
`qa_evidence_commit`. Two later passages in the same file still name the superseded value
as live:

- `:3246` (§12.1) — "the live `qa_evidence_commit` is `e7f39890211b52e10d2619c5ddcb85a3d8c7df22`, and the working tree carries the round-twelve rework on top of it";
- `:3281` (§12.5) — "update `qa_evidence_commit` in section 1 of this report after the new commit exists. It **currently names the live** `e7f39890211b…`".

§12.5 is self-refuting after the edit: it describes the state of §1 that the same commit
changed, and it routes the integrator to perform an action already performed. The report
itself names this defect family at line 3124 — "Routing work that is already done is a
small defect of the same family as the large ones in this report: a document asserting a
state of the world it has not re-measured."

I record this as a finding but weigh it below F-1 and F-2: §12 is explicitly a
point-in-time handoff written from inside an uncommitted working tree, and the report is
history. My judgement on the wider question the integrator asked is in the section below.

**F-4. The recorded exception is recorded only in a commit message.** `afe1895` states
that its edit to `docs/program/reviews/W0-QA-01.md` "is raised for the stage-closing
review alongside the wave's earlier recorded exception". That raising has not been
performed in any tracked file. `docs/program/waves/W0.3_ratification_integration.md:151`,
"Recorded exception — integrator edits inside three task commits", still names only
`3ca8e25`, `854a682` and `92e13fa`. The manifest's `open_escalations` holds only `E-05`
and `known_pre_ratification_items` holds only the three pre-existing items. A commit
message is not in the reviewed tree — my own digest recipe hashes file content, not commit
messages — and a reader arriving by the documented chain never sees it.

**Owning task: `W0-INT-01`**, which holds `docs/program/waves/W0.3_ratification_integration.md`
and `artifacts/checkpoints/CP-00/**` in its allowed paths.

**Verdict: FAIL.** Evidence: `docs/program/CURRENT_STATE.md:232-234,236,245-247`;
`docs/program/CHECKPOINT_REGISTRY.md:5`; `artifacts/checkpoints/CP-00/acceptance.md:7-8,11`;
`docs/program/tasks/W0-INT-01.md:3-9`; `docs/program/reviews/W0-QA-01.md:3246,3281`;
`docs/program/waves/W0.3_ratification_integration.md:151`.

### MT00-02 — Greenfield boundary — **PASS**

**What I did.** Traced the main user journey from `docs/PRODUCT_SYNOPSIS.md` §2 through
`docs/architecture/SYSTEM_ARCHITECTURE.md` and asked of each mandatory step whether it
requires starting or importing legacy. Then swept `src/`, `web/`, `contracts/`, `scripts/`
and `tests/` for any legacy import, path insertion or runtime reference.

**What I observed.** The journey is
`Object/Project → Document → Version → Ingest files → Audit Run → Analysis Stages →
Findings + Evidence → Expert Review/Decision → Export/Knowledge/Comparison`. The
architecture context diagram routes it Browser → Next.js UI → generated client → Control
Plane → PostgreSQL / private S3 / Analysis Port → Execution Engine. No step touches
legacy. The publication boundary is `JobPackage → attempt → stage results → ResultPackage
→ schema+checksum validation → transactional publish`; legacy appears nowhere in it.

The sweep found exactly one reference to a legacy path in an executable position:
`contracts/analysis/v1/README.md:757`, inside Gate B, which sets
`R='/root/projects/PDF-proverka/PDF-proverka'` and runs `git -C "$R" show <commit>:<path>`.
Its own preamble states the constraint: "Reads only immutable Git objects at
`32b9d903792b30506048a1d42b0e6b2d07aee403`; the mutable legacy working checkout is never
opened." That is oracle use, which is what ADR-0001 permits, and it is an evidence gate,
not a runtime step. Every other legacy mention — `docs/behavior/legacy_capability_inventory.md`,
`docs/SOURCE_TRACEABILITY.md`, the `W0-ARC-01`/`W0-BHV-01` task gates — is a read-only
`git show`/`git grep` at a pinned commit. The absolute discovery path is declared rather
than hidden, at `docs/SOURCE_TRACEABILITY.md:11`.

I confirmed the oracle is reachable and the pinned commit resolves, so the gate is
executable rather than nominal.

`src/auditmanager/` and `web/src/` contain only boundary `README.md` files and one empty
`__init__.py`. No production code exists at all, so no mandatory runtime step can depend
on legacy. ADR-0001 forbids importing a legacy service, router or pipeline manager without
a new ADR, and no such ADR exists.

**Verdict: PASS.** Legacy appears only as behavioral oracle and fixture source.

### MT00-03 — Identity walk — **PASS**

**What I did.** Took a legacy scenario in which a rerun re-emits a finding the expert has
already decided on, and walked it through `Finding` / `FindingObservation` /
`ExpertDecision` against `docs/architecture/DOMAIN_MODEL.md`, ADR-0010, ADR-0012 and
`contracts/domain/v1/identifiers.json`.

**What I observed.** The walk: run 1 emits `FindingObservation` `fobs_…` bound to
`AuditRun` `run_…`, matched by the versioned identity policy onto `Finding` `fnd_…`. The
expert records `ExpertDecision` `dec_…` referencing `fnd_…`. Run 2 emits a new
`fobs_…` with its own evidence and provenance. If the identity policy matches, it attaches
to the same `fnd_…` and the existing decision still references a live Finding; the
`CurrentVerdict` projection is unaffected because it is computed from the decision events
on `fnd_…`, not from observations. If the policy does not match at the confidence the
version requires, a new `Finding` is created — ADR-0010 says so explicitly — and the old
decision remains attached to the old Finding rather than silently migrating. Either way
the expert's decision survives the rerun through the stable identity, and never through
a display ordinal.

`F-NNN` is excluded as a foreign key in two independent places, one prose and one
machine-checkable. `DOMAIN_MODEL.md`: "Display ordinal such as `F-014` belongs to a
run/read model and **never** serves as FK." `contracts/domain/v1/identifiers.json` rule 3:
"A filesystem path, directory name, uploaded file name, S3 object key, URL, display
ordinal such as F-014, human sheet or document number and any content checksum are
addresses, presentation values or verification values; none of them is an identity and
none may be used as a foreign key." The catalog declares `finding_uid` → `fnd`,
`finding_observation_id` → `fobs`, `decision_id` → `dec` as distinct opaque
`<prefix>_<ULID>` identities, with rule 2 forbidding the ULID body from being decoded to
recover ordering or ownership.

The decision ledger is append-only: `PD-01` as approved with modification says a
correction and a revocation each create a new `decision_id`, and a revocation moves the
projection to `pending` without restoring the superseded verdict. So no rerun and no
revocation can silently resurrect an earlier verdict.

**Verdict: PASS.**

### MT00-04 — Run/job/attempt walk — **PASS**

**What I did.** Modelled provider timeout → retry → stale worker result against the three
machines in `contracts/domain/v1/state-machines.json`, the `PD-03` decision text and the
error catalog.

**What I observed.** Three machines, three identifiers, three writers, no overlap:

| Machine | Entity | Identifier | Terminal states |
|---|---|---|---|
| `audit_run` | AuditRun | `run_id` | published, partial, failed, cancelled |
| `job` | Job | `job_id` | succeeded, failed, cancelled, dead_letter |
| `attempt` | Attempt | `attempt_id` | succeeded, failed, superseded, lost, cancelled |

The walk. Provider timeout: Attempt is `running`; the guard `running → lost` fires on
"heartbeat deadline missed or operator marked the Attempt lost", with the Job releasing
the lease in the same transaction. Retry: the Job moves `running → retry_wait → queued →
leased`; a new Attempt is created, and its `created → leased` guard requires that "the
Lease and the new current execution token are created in the same transaction as the
Attempt". The `AuditRun` does not move. There is no transition that creates a Run on
retry, and no transition out of any terminal Run state, which is `PD-03`'s "retry, resume,
restart and worker failover create a new `Attempt` of the same `Job`, never a new Run" and
"a terminal Run is never reopened" enforced structurally rather than only asserted.

Stale worker result: the old Attempt is `superseded` or `lost`. Both carry
`publishes_result: false`. `superseded` reads: "A newer Attempt for the same Job took
authority. Any result this Attempt delivers afterwards is stored as immutable evidence, is
never applied to project state and is answered with `stale_attempt`." `lost` and
`cancelled` reference the same store-only rule. The publish path is guarded independently:
`running → succeeded` requires "the presented execution token is still the current one and
the result package passed schema, checksum and manifest validation inside the publishing
transaction", `on_violation: stale_attempt`. So a stale Attempt is refused twice — by its
own state and by the token check inside the publishing transaction — and its output is
retained as evidence rather than discarded.

`stale_attempt`, `execution_token_invalid`, `conflict`, `state_transition_not_allowed` and
`partial_result_not_publishable` are all declared in the 20-code error catalog, so the
`on_violation` outcomes name real codes.

The `PD-03` precedence clarification is carried in the domain model and the review: the
same idempotency key with the same payload always returns the original Run, and a repeat
of a terminal Run creates a new Run only under a new idempotency key. A sixth machine,
`command_idempotency`, exists to hold that, and the catalog declares
`idempotency_key_reuse`, `idempotency_key_in_progress` and `idempotency_key_stale`.

One observation, not a failure. `DOMAIN_MODEL.md` line 76 reads "A stale Attempt cannot
publish after fencing token changed", using the legacy phrasing where `ID-02` fixed
`execution_token` as canonical. The `identifiers.json` rule scopes the prohibition to
declared artifacts — "no target field, payload key, database column or API parameter
defined against this contract carries them" — and prose is not one of those. The same file
names `execution_token` correctly in the `PD-03` block above, the state machine uses
`execution_token` throughout, and `CP00_ARCHITECTURE_REVIEW.md` states the position
directly: "Fencing is a property of behavior, not a field name and not a monotonic
number." No contract artifact carries the legacy name. I record it so a later reader is
not surprised by it, and note that the file is inside a reviewed family whose byte
identity carries the `W0-QA-01` `ACCEPT`, so it should not be edited casually.

**Verdict: PASS.** Run, Job and Attempt are not conflated, and a stale Attempt has no
right to publish.

### MT00-05 — Comparison ownership — **PASS**

**What I did.** Modelled auto suggestion → user-approved sheet link → recompute → AI
review against `DOMAIN_MODEL.md` §"Comparison ownership", ADR-0013,
`contracts/comparison/v1/README.md` and `docs/architecture/CONTRACT_CATALOG.md`.

**What I observed.** The aggregate is `Comparison` over source Version A and target
Version B, holding `SuggestionSet` (marked rebuildable), `SheetLink` (marked
"user-approved state/revision") and `ComparisonRevision`, which itself separates
deterministic exclusions, raw text diff and raw graphic evidence from derived AI
synthesis. The ownership table records the invariant as the context's defining note:
"approved link ≠ suggestion".

The walk. Auto suggestion produces a `SuggestionSet`, which is rebuildable by
construction. The user approves a link; that link becomes owned state with its own
revision. Recompute regenerates the `SuggestionSet`: `DOMAIN_MODEL.md` states "Recompute
suggestions cannot mutate approved SheetLink", and ADR-0013 states "User-approved links
are owned state and survive recomputation". AI review then runs as an additive layer:
ADR-0013 says "AI review/synthesis is a derived artifact keyed by raw checksums", and the
comparison README requires "additive AI review/synthesis keyed to source checksums" over
"immutable deterministic exclusion/raw text/graphic evidence per revision". Keying the
derived layer by the checksum of the raw evidence is what makes overwriting the raw
evidence detectable rather than merely forbidden. Repairs are separately constrained:
"repair proposal/action/undo with proof and audit".

The two invariants the case asks for therefore hold, and they hold in three documents that
agree: recompute cannot overwrite an approved link, and AI is a derived layer keyed to raw
evidence rather than a writer of it.

Scope note, judged and not treated as an omission. `contracts/comparison/v1/` contains only
`README.md`. That is deliberate and consistently recorded: the README says "Freeze in S06",
`CONTRACT_CATALOG.md` shows `comparison: not-active` in the freeze manifest, the manifest's
`contract_versions` lists domain, analysis, events and the golden selection schema and no
comparison entry, and `PD-04` places graphic/vector comparison in W7. CP-00 freezes the
architecture and ownership of comparison, not its machine contract, and the documents say
so in the same terms in every place I checked.

**Verdict: PASS.**

### MT00-06 — Unresolved decisions — **PASS**

**What I did.** Reviewed the proposed ADR and the owner decisions, then swept the
contracts, fixtures and migrations for any value that would silently close an open
question.

**What I observed.** Eighteen ADRs. Seventeen carry "accepted for bootstrap; ratify at
CP-00". Exactly one, ADR-0014 (authz, classification, retention), carries `proposed`, and
`CP00_ARCHITECTURE_REVIEW.json` agrees: dispositions are 11 ratify, 6 adapt, 1 defer, the
single defer being ADR-0014. Principles are 17 ratify, 5 adapt.

`U-04` is recorded `open`, not resolved and not quietly narrowed. Its disposition names an
owner (repository owner with security and legal), two deadlines (tenant/IdP before
`W2-C-01`, TTL and legal hold before `W9-C-01`) and an explicit blocking scope of four
items, including "no tenant, identity-provider, TTL, retention or legal-hold value is
encoded in any contract". `blocks_cp00_freeze` is `false` with the reasoning stated rather
than assumed: requiring `U-04` to close before CP-00 would make its own deadlines
meaningless. `U-01` is `deferred_with_deadline` to `W3-C-01` before the first paid-provider
canary. `U-02`, `U-03`, `U-05` and `U-06` are resolved, assigned or conditionally accepted,
each with a named owner and date. `OQ-02` and `OQ-04` are carried in the manifest as
deferred to named slots. `E-05` is carried as an open integrator obligation.

The sweep is what makes this more than reading a status field. Across 66 tracked files
under `contracts/`, `fixtures/` and `db/`, there is not one numeric assignment to a TTL,
retention window, lease duration, heartbeat interval, grace period, backoff or retry
budget. Where the subject is unavoidable the contract names the hole instead of filling
it: `contracts/domain/v1/error-codes.json` declares an open decision `OPEN-RETENTION`
whose statement reads "idempotency_key_stale names the fail-closed outcome once a command
record is unavailable. The retention window, legal-hold and tenant or identity-provider
semantics that would decide when that happens are not declared by this contract", with a
gate pointing at `U-04` and the instruction that "No numeric retention, TTL or legal-hold
value may be declared by any lane before that input exists". `OPEN-RETENTION` is also an
enumerated value in `error-codes.schema.json`, so the open question is machine-checkable
rather than prose-only.

`db/migrations/` holds only `README.md`, consistent with `migration_head: none`.

**Verdict: PASS.** The unconfirmed values are explicitly unresolved. None is invented.

## Final acceptance checklist

- [x] **Нет hidden Strangler runtime dependency.** MT00-02. No production code exists in
  `src/` or `web/`; the journey and the publication boundary reach no legacy component;
  the single executable legacy reference reads immutable Git objects at a pinned commit
  and declares that it never opens the mutable checkout; ADR-0001 forbids importing a
  legacy service without a new ADR and no such ADR exists.
- [x] **Все ключевые bounded contexts имеют владельца данных.** `DOMAIN_MODEL.md`
  §"Aggregate ownership" assigns authoritative aggregates to all thirteen contexts —
  Access, Documents, Ingest, Storage, Jobs, Analysis, Findings, Decisions, Knowledge,
  Comparison, Export, Workers, Operations. I checked the one apparent gap: Knowledge has no
  module under `src/auditmanager/`, and that is deliberate rather than missing —
  `src/auditmanager/decisions/README.md` states "Knowledge views rebuild from events", and
  the ownership table already marks `KBProjection`/`SimilarityIndex` a rebuildable
  projection. `REPOSITORY_LAYOUT.md`'s fifteen modules match the filesystem exactly.
  `CONTRACT_CATALOG.md` additionally assigns an owner role to each of the six contract
  families and states that a lane does not write into another family even to fix its own
  build.
- [x] **Shared contract freeze/process понятен reviewer без устного пояснения.**
  `VERSIONING_AND_FREEZE_POLICY.md` defines three freeze levels (design, contract,
  checkpoint), a freeze-break procedure and dependency locks. `CONTRACT_CATALOG.md` gives
  the freeze manifest shape, the post-freeze rule that a consumer does not edit a shared
  contract, and five compatibility rules including that a semantic change without a schema
  change is breaking. `WAVE_EXECUTION_GUIDE.md` and the W0.3 wave document give ownership
  per hotspot and per allowed path. I was able to determine which families are frozen,
  which are not-active and who owns each without asking anyone.

The checklist passes. It is not sufficient for ratification: MT00-01 is a mandatory case
and it failed.

## Stop / cleanup

The runbook's cleanup step reads "Stop the local stack using the documented command."
**Not applicable at CP-00, and I did not substitute a command of my own.** No local stack
exists: `backend_runtime`, `frontend_runtime` and `local_infra_versions` are recorded as
"not applicable - architecture-only checkpoint", building a runtime is prohibited before
CP-01, and `W0-INT-01` §"CP-00 runtime fields are not applicable" records this disposition
for exactly this class of runbook field. This matches the round-6 tester's handling of the
same step. I record it as inapplicable rather than as passed or skipped.

The remaining cleanup obligations were met without needing a command. I created no
temporary credentials or tokens and installed no fault-injection overrides. My scratch
implementations of the two digest recipes and the link, path and numeric sweeps were
written outside the repository and no output of them is committed. All evidence cited in
this report is a path and line number inside the package or a recomputed digest; none of
it is a production payload, and there is nothing sensitive to anonymize because no
production data exists.

## Known limitations

1. **I am an independent agent, not a human tester.** For an architecture-only checkpoint
   the six cases are reading and judgment over documents rather than exercise of a running
   system, so this is the closest available analogue — not a substitute. Stated so a later
   reader weighs the evidence for what it is. This limitation is already recorded in
   `acceptance.md` and I repeat it rather than let it lapse.
2. **I did not run the automated suite, the documented gates or the validator.** That is
   the parallel stream's job and duplicating it would not be independent evidence. My
   digest and artifact-manifest recomputations are my own implementations written from the
   recipe text, not executions of `tests/contract/test_cp00_candidate.py`.
3. **The post-freeze delta ceiling is defined only in the test module.** The rule that
   voided round six — which paths may change after a freeze — lives in
   `tests/contract/test_cp00_candidate.py` (`_post_freeze_delta_problems`) and in commit
   messages. No program document states it. I could therefore confirm that round six's
   voiding was justified (probe P7 shows the corrected paths are inside the tested digest)
   but I could not check the ceiling itself as a reader, only as a reader of test code.
4. **I did not verify the legacy oracle's contents.** I confirmed the repository is present
   and that the pinned commit `32b9d903…` resolves, so Gate B is executable. I did not run
   the 293 evidence locators; that is a QA-suite obligation.
5. **F-3 rests on a judgement about scope.** I treat §12 of the QA report as a
   point-in-time handoff rather than a live claim, which is why I weigh it below F-1 and
   F-2. A reviewer who treats every sentence of an accepted report as current would rank it
   higher. I state the reasoning so the disagreement is visible rather than buried.
6. **I read the round-6 report for form only.** Its `PASS` results carry no weight here and
   its `FAIL` was re-derived from the tree rather than accepted. I did not read the
   automated round-6 report's findings before forming mine.

## On the integrator's edit to the QA report

The brief asks whether the handling is adequate or is itself a finding. My judgement: the
edit was justified and the disclosure was not completed. Three things count in its favour
and two against.

In its favour. First, the edit was not unilateral — the reviewed artifact asked for it.
`docs/program/reviews/W0-QA-01.md` §12.5 instructs the integrator to "update
`qa_evidence_commit` in section 1 of this report after the new commit exists", and explains
why the report could not do it itself. The integrator performed the edit the report
specified, in the section it named, after the event it named. That is following the
handoff, not overriding an accepted artifact. Second, the reasoning is sound and
unavoidable: a report cannot name the commit that contains it, so §1 was necessarily
correct when written and necessarily false once round twelve landed. Third, the edit is
self-disclosing in the text a reader actually reaches — the corrected row says "This row
was corrected by the integrator after acceptance" — and it changes no verification claim,
gate result, count or mutation outcome.

Against. First, the file is outside `W0-INT-01`'s declared allowed paths. The wave's
hotspot table assigns "cross-family test/report paths" to `W0-QA-01`, and
`docs/program/reviews/W0-QA-01.md` appears nowhere in `W0-INT-01`'s allowed-path list.
This is the same class as the three integrator edits already recorded as an exception in
the wave document, and the wave's own gate list requires each task's diff to be a subset of
its allowed paths. Being justified does not make it in-scope; it makes it an exception that
must be recorded as one. Second, and this is the part I call a finding: it has not been
recorded where exceptions of this class are recorded. `afe1895` says the edit "is raised
for the stage-closing review alongside the wave's earlier recorded exception", but nothing
in the tree raises it. The wave's exception section still names three commits.
`open_escalations` holds only `E-05`. `known_pre_ratification_items` holds only its three
pre-existing entries. The disclosure lives in a commit message, which is not in the
reviewed tree and which a reader arriving by the documented chain never sees. An exception
announced and not performed is the defect this program has spent rounds on, and `afe1895`'s
own message names it: "Announcing a correction and performing part of it is the defect this
program spends its rounds on."

So: the edit itself is adequate and I would not reopen `W0-QA-01` for it — doing so would
invalidate an independent `ACCEPT` over text its author did not write, for a correction its
author requested. The *handling* is incomplete in two respects, both `W0-INT-01`'s to close:
the exception must be written into `docs/program/waves/W0.3_ratification_integration.md`
(F-4), and the edit left §12.1 and §12.5 of the edited file contradicting its own §1 (F-3).

## Is the round-six remediation complete?

**Complete as scoped; the underlying condition is not closed.** I verified each of the five
sites and the history entry myself rather than taking the integrator's account. All five
now carry `3da104e5d6fafb2a581bda377a07911183af803f`. `qa_evidence_history` carries both
supersessions. The `S00` row's round count now reads twelve, matching the task layer. Every
surviving `e7f3989` in the tree is labelled superseded or is round-six evidence, except the
two passages at F-3. Probe P7 independently confirms the corrected values are inside the
tested digest, so voiding round six was required rather than optional.

But round six found one axis of state drift and the remediation swept that one axis. The
same layer is stale on a second axis nobody looked for: the acceptance round number is two
rounds behind in three documents (F-1), and `W0-INT-01`'s banner still names a blocker that
was cleared before the round-six freeze (F-2). Both were present at round six as well and
neither stream reported them. The defect that keeps voiding rounds here is not any
particular stale value; it is that the state layer is corrected by pursuing the specific
value a reviewer named, rather than by re-reading the state layer against the manifest.
Whatever closes F-1 and F-2 should close that, or round eight will find a third axis.

One structural note, offered as an observation rather than a finding.
`manifest.qa_evidence_history` records the first supersession with `"status": "superseded"`
and the second with no `status` key at all, carrying the fact in prose only. Both entries
are present, which is what the remediation owed. But a check that filters this list on
`status == "superseded"` sees one entry, not two. Given that this program's recurring defect
is a guarantee stated in prose beside a check that cannot fail on the thing the prose names,
the asymmetry is worth removing when the manifest is next written.

## Result

**FAIL — 5 of 6 cases pass. MT00-01 fails.**

| Case | Verdict |
|---|---|
| MT00-01 Documentation navigation | **FAIL** |
| MT00-02 Greenfield boundary | PASS |
| MT00-03 Identity walk | PASS |
| MT00-04 Run/job/attempt walk | PASS |
| MT00-05 Comparison ownership | PASS |
| MT00-06 Unresolved decisions | PASS |

CP-00 cannot be tagged. The runbook's result clause is unambiguous: a checkpoint cannot be
tagged if any mandatory case is `FAIL`.

**Blocking task to reopen: `W0-INT-01`.** All four findings sit in paths it owns:

| # | Finding | Paths |
|---|---|---|
| F-1 | Round accounting two rounds stale; one document routes work already done | `docs/program/CURRENT_STATE.md:232-234,236,245-247`; `docs/program/CHECKPOINT_REGISTRY.md:5`; `artifacts/checkpoints/CP-00/acceptance.md:7-8,11` |
| F-2 | `W0-INT-01` banner asserts `W0-QA-01` reopened, contradicting its own line 36 | `docs/program/tasks/W0-INT-01.md:3-9` |
| F-3 | QA report §12 still names the superseded commit live after §1 was corrected | `docs/program/reviews/W0-QA-01.md:3246,3281` |
| F-4 | The `afe1895` exception is raised only in a commit message | `docs/program/waves/W0.3_ratification_integration.md:151` |

As in the six previous rounds, no contract, schema, fixture, state-machine, identifier or
golden defect was found in any of the six walks. The four reviewed families reproduce
`artifact_manifest_sha256` exactly, so the `W0-QA-01` `ACCEPT` still holds and nothing here
requires re-running QA. Every failure is again in integrator-owned state metadata.

F-3 is the one that needs a decision rather than an edit, because the owning task is closed
and accepted. My recommendation is to correct §12.1 and §12.5 the same way §1 was corrected
— labelled in the text as the integrator's, in the same commit that records the exception
in the wave document — rather than to reopen `W0-QA-01`. Correcting §1 and leaving §12
contradicting it is the worse of the two states, and reopening an accepted task over text
its author was right to write is worse than either.
