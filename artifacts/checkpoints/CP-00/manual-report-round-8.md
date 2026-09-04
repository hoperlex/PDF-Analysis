# CP-00 manual acceptance — round 8

Runbook: `docs/manual-tests/CP-00_architecture.md`, executed as written.

## Start record

```text
candidate_commit:          b21e727500287152f258f405333acb9e72c6b311
tree_hash:                 8cd81916b9e71f1ff87ba4a210e7196d6aad39aa
tested_candidate_digest:   959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f
                           recomputed independently over 218 paths; MATCHES the manifest
                           top-level field and the round-8 acceptance_rounds entry
artifact_manifest_sha256:  39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
                           recomputed independently over 100 files; MATCHES; artifact_count 100 confirmed
contract_manifest:         artifacts/checkpoints/CP-00/manifest.json
contract_versions:         domain 1.0.0-draft.1; analysis 1.0.0-draft.1; events 1.0.0-draft.1;
                           golden_selection_schema 1; api and comparison are README-only areas,
                           not yet versioned contracts
migration_head:            none — db/migrations carries only README.md
backend_runtime:           not applicable - architecture-only checkpoint
frontend_runtime:          not applicable - architecture-only checkpoint
local_infra_versions:      not applicable - architecture-only checkpoint
tester:                    cp00_manual_tester, independent manual acceptance stream
started_at:                2026-09-04T12:04:47Z
finished_at:               2026-09-04T12:15:04Z
```

Working tree was clean at start (`git status --porcelain` empty, 218 tracked files, zero
untracked non-ignored files). At finish one untracked file was present,
`artifacts/checkpoints/CP-00/automated-report-round-8.md`, written by the parallel
automated stream while I worked. It is outside the reviewed families and outside every
path I touched. Its arrival changes what the digest recipe computes; that is measured and
recorded under Finding F-7 rather than glossed.

### Independence

I authored none of the reviewed artifacts, none of `tests/contract/test_cp00_candidate.py`,
none of `docs/program/reviews/W0-QA-01.md`, none of the state documents, and none of the
round-6 or round-7 reports. I carried no round-6 or round-7 verdict forward: every finding
and every pass below was re-derived on this tree. I read the round-7 report for form and
for the disposition of one item I re-examined, and I say so where it bears on a judgement.
I wrote exactly one path in this repository: this report. I ran no command that moves
refs, the index or the working tree.

### Digest confirmation and discrimination probes

`candidate_digest_recipe` was implemented from the manifest text alone: `git ls-files` plus
`git ls-files --others --exclude-standard`, sorted; sha256 over, per path in order, the
UTF-8 path bytes then the raw 32-byte sha256 of the file content; the manifest contributes
the sha256 of `json.dumps(manifest, sort_keys=True, separators=(',',':'))` with only
`tested_candidate_digest` blanked, at the top level and in every `acceptance_rounds` entry,
`evidence_bundle_digest` keeping its value.

Result over 218 paths:
`959d5db2551360caf97951f067d551f2d2edb33a76b4ca21e3648f7fb305058f` — **matches**.

A match is worth nothing unless the function discriminates. Seven probes:

| # | Perturbation | Digest | Result |
|---|---|---|---|
| P0 | none — baseline | `959d5db2…058f` | matches the frozen value |
| P1 | one byte of manifest prose changed (`checkpoint` value) | `23341ee5…ad6f` | DIFFERS — the round-3 counterexample shape is closed |
| P2 | `evidence_bundle_digest` set to a value | `a13a85dd…f888` | DIFFERS — the other digest is load-bearing |
| P3 | one byte appended to `contracts/domain/v1/README.md` | `ab648090…68e3` | DIFFERS |
| P4 | one new untracked non-ignored file present | `c091b250…1dcb` | DIFFERS |
| P5 | both digest fields blanked — the rejected earlier recipe | `866609e8…c418` | DIFFERS — field selection is load-bearing |
| P6 | hex text hashed instead of raw digest bytes | `5d1950cc…e340` | DIFFERS — the raw-bytes clause is load-bearing |
| P7 | `git ls-files` only, `--others` omitted | `959d5db2…058f` | IDENTICAL at start |

P7 is not a defect and not a hole: at the moment of measurement the tree carried no
untracked non-ignored file, so the two path sets were equal. The clause is inert on the
frozen tree and becomes live the moment either stream writes a report — see F-7.

`artifact_manifest_sha256` was recomputed from its own recipe over
`git ls-tree -r --name-only HEAD -- contracts fixtures docs/architecture scripts`:
100 paths, `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08`, matching
both the manifest field and `artifact_count`.

The documented suite command `.venv/bootstrap/bin/python -m unittest discover -s tests/contract`
returns `Ran 281 tests in 35.730s / OK` on this tree. I ran it to establish, on my own
evidence rather than on the automated stream's, that nothing below is a contract, schema,
fixture or test defect.

## Test cases

### MT00-01 — Documentation navigation — **FAIL**

**What I did.** I walked the route the package itself documents, in order:
`README.md` → `docs/PRODUCT_SYNOPSIS.md` → `docs/architecture/ARCHITECTURE_BIBLE.md` →
`docs/architecture/ADR_INDEX.md` → `docs/program/ROADMAP.md` →
`docs/program/WAVE_EXECUTION_GUIDE.md` → `docs/stages/S00_architecture_and_behavior_freeze.md`,
reading each document rather than checking that its file existed. From S00 I followed the
onward pointers a reader is actually given: the W0.3 wave document, the checkpoint
registry, `CURRENT_STATE.md`, `docs/INDEX.md`, the CP-00 manifest, the CP-00 acceptance
record, the `W0-INT-01` and `W0-QA-01` task files, and `docs/program/reviews/W0-QA-01.md`.
I then swept, on axes chosen without reference to what failed in rounds six and seven:
every git-SHA-shaped token in every tracked file against `git cat-file`; every markdown
link and every backticked path-like token; every live statement about acceptance-round
state; and every declared count against the artifact it counts.

**What resolves.** The chain is complete: all seven documents exist and each onward
pointer resolves. A link check over 152 tracked markdown files found **0 broken relative
links, 0 broken anchor fragments and 0 phantom document references** across 264 inline
links and 510 path-like backticked tokens; the 94 non-resolving tokens are all deliberate
references to the two external snapshot repositories or to illustrative placeholders, each
carrying the `[L]`, `[S]` or `[D]` evidence notation the documents define. Every SHA in the
tree resolves either here or in the legacy repository at
`/root/projects/PDF-proverka/PDF-proverka`, and the six that do not resolve here are the
documented legacy-repository objects. Every declared count I could recompute reproduces:
100 reviewed artifacts, 33 lint rules, 9 registry stages, 62 name-map rows, 31
alias-bearing declarations, 25 identifiers, 20 error codes, 6 state machines, 5 golden
journeys, 95 assertions (15+24+16+17+23, matching `per_journey_assertions` exactly),
92 inventory-mapped plus 3 target-scope, 281 tests, 255+26=281.

**The e7f3989 axis that killed round six is closed.** I swept it myself rather than
accepting that it had been fixed. All 42 occurrence lines of the superseded evidence
commit are either labelled superseded or sit inside committed round-6/round-7 acceptance
evidence that documents the defect on purpose. The five sites round six named all now
carry `3da104e5…`. The current evidence commit is presented consistently at all 35 sites.

**Why this case fails anyway.** Two live plan-of-record documents on the walked route say
things this repository does not support, and both were inside the scope the round-eight
remediation declared complete.

**F-1 — the CP-00 acceptance record is three rounds stale, and it is the one document the
round-seven report named by path and line.**

`artifacts/checkpoints/CP-00/acceptance.md` is titled "CP-00 acceptance record" and is
where `docs/INDEX.md:51` sends a reader for CP-00 acceptance. It says:

- `:7-8` — "Round 5 is owed and neither earlier `PASS` transfers to it."
- `:11` — "No primary automated report exists for round 3 — that stream reported to the
  integrator only, which round 5 must not repeat."
- `:13-14` — "Three rounds ran. Rounds one and two returned `FAIL` from both streams;
  round three returned `PASS` from both. Every blocker across all three…"
- `:22-26` — a round table whose rows stop at 3.

Round 5 is void. Rounds 6 and 7 ran and failed, and both produced primary automated *and*
manual reports — four committed files sitting in the same directory as this document.
Round 8 is owed. Five rounds have run, not three.

This is not a newly discovered site. `manual-report-round-7.md:129-130` raised
`acceptance.md:7-8` and `:11` verbatim as its finding F-1, cross-referenced at `:202` and
`:581`. The manifest's own round-7 entry names the file: "the round accounting in
`CURRENT_STATE.md`, `CHECKPOINT_REGISTRY.md` and `acceptance.md` was two rounds behind".
The remediation commit `a3eaf88` touched eight files. `acceptance.md` is not among them:
`git log -1 -- artifacts/checkpoints/CP-00/acceptance.md` still returns `ae59d8b`, the
round-four commit. `CURRENT_STATE.md` and `CHECKPOINT_REGISTRY.md` were corrected and both
now read correctly; the third file named in the same sentence was not.

The path is inside `W0-INT-01`'s allowed paths (`artifacts/checkpoints/CP-00/**`), so
nothing prevented the correction. The round-8 manifest entry asserts the opposite of what
the tree shows: "the reconciliation was produced by an independent auditor reading every
state document end to end, and its completeness is shown by a check that fails on the
previous tree rather than asserted in prose."

**Owning task to reopen: `W0-INT-01`.**

**F-2 — a plan-of-record document asserts an executable check that does not exist.**

`docs/program/waves/W0.3_ratification_integration.md:200-204`, closing the recorded
exception about integrator writes into an accepted deliverable:

> "The round-eight remediation replaced that declaration with a check that can fail: a
> context-aware sweep over every tracked file requiring each occurrence of a superseded
> commit to be either committed acceptance evidence or labelled superseded within three
> lines."

No such check is in the tree. `git ls-files tests scripts` returns ten paths, of which two
are Python: `tests/contract/test_cp00_candidate.py` and
`tests/contract/test_validate_bootstrap.py`. Neither contains the string `supersed`,
neither contains `e7f3989`, `854a6820` or `3da104e5` as a checked constant, and the only
SHA constant in the module is `REVIEWED_CANDIDATE_COMMIT`. Nothing tracked mentions
`check_stale`. The commit message of `a3eaf88` names `scratchpad/check_stale.py`, which is
not tracked and is not in the working tree, so a reader of the frozen candidate cannot run
it, find it, or confirm what it reported. `manifest.json` round-8 note repeats the same
claim in the same terms.

This matters beyond bookkeeping. The defect shape `W0-QA-01` spent eleven reopenings
closing is, in that task file's own words, "a guarantee stated in prose beside a check that
could not fail on the thing the prose named". The sentence that records the closure of two
failed rounds is itself an instance of it. And the guarantee it claims is weaker than
advertised even as described: the "labelled superseded within three lines" rule passes
`docs/program/reviews/W0-QA-01.md:3130` (see F-4), where the nearby word "superseded"
refers to a different commit from the one the sentence calls live.

Two further stale statements live in the same file and the same class:
`waves/W0.3_ratification_integration.md:5` says the candidate is "awaiting the round-eight
freeze", which `b21e727` performed.

**Owning task to reopen: `W0-INT-01`.**

**Consequence for round 8.** `POST_FREEZE_DELTA_CEILING` in
`tests/contract/test_cp00_candidate.py:188` is the checkpoint manifest, the checkpoint
registry, `docs/program/CURRENT_STATE.md`, and the five `RATIFICATION_DELTA_CEILING`
architecture files, plus the round's own declared report paths under
`ACCEPTANCE_EVIDENCE_PREFIX`. `artifacts/checkpoints/CP-00/acceptance.md` is not a declared
report path for round 8 and `docs/program/waves/W0.3_ratification_integration.md` is not in
the ceiling at all and cannot be licensed as evidence. Correcting either voids this round.
That is the honest outcome and I state it plainly: **round 8 cannot be salvaged by
remediation; the corrections must land and a round 9 must be frozen and dispatched.**

**Record:** `FAIL`. Evidence: `artifacts/checkpoints/CP-00/acceptance.md:7-8,11,13-14,22-26`;
`docs/program/waves/W0.3_ratification_integration.md:5,200-204`; `git show --numstat a3eaf88`;
`git ls-files tests scripts`; `manifest.json` round-8 `note`.

### MT00-02 — Greenfield boundary — **PASS**

**What I did.** I took the main user journey as `docs/PRODUCT_SYNOPSIS.md` §2 states it —
Object/Project → Document → Version → Ingest → Audit Run → Analysis Stages → Findings +
Evidence → Expert Review/Decision → Export/Knowledge/Comparison, and the critical first
useful path beneath it — and asked, step by step, whether any mandatory runtime step
requires launching or importing legacy. I then checked the claim mechanically rather than
taking the prose for it.

**What I observed.** There is no runtime to depend on legacy: `src/` contains 17 files, 16
of them `README.md` boundary descriptions and one `__init__.py` whose entire content is a
docstring saying production implementation starts after the CP-00/CP-01 gates. `web/`
contains 8 `README.md` files and nothing else. A sweep for `PDF-proverka`, `pdf_proverka`,
`from legacy` and `import legacy` across every `.py`, `.ts`, `.tsx` and `.json` returns no
import anywhere. Every legacy reference in the repository is a `git -C
/root/projects/PDF-proverka/PDF-proverka show|grep|ls-tree|cat-file` invocation against a
pinned immutable commit, or a fixture provenance record. Each of the five golden journey
manifests declares its method as "Read-only inspection of the immutable legacy Git objects
at the pinned commit … No legacy service, job, provider, migration or user flow was
executed, and no mutable legacy checkout path was read as evidence."

The non-transfer is a recorded decision, not an accident.
`docs/SOURCE_TRACEABILITY.md:89-90` states it under its own heading: in the refactoring
Bible legacy remains production runtime under Strangler; "в этом пакете репозиторий пустой,
поэтому runtime Strangler не нужен. Legacy — read-only oracle/fixture source, не adapter по
умолчанию." `ADR-0001` says the same normatively and forbids importing a large legacy
service, router or pipeline manager without a new ADR. `CP00_ARCHITECTURE_REVIEW.md:174,186`
records the source ADR-0001 "hybrid Strangler" status as `accepted` and deliberately not
transferred, and `:432` records `DV-06` as an accepted greenfield divergence.
`SOURCE_TRACEABILITY.md:96` requires every algorithm port to go through
`characterize → define contract → isolate algorithm → port/rewrite → parity evidence`.

**Record:** `PASS`. Evidence: `README.md:5-11`; `docs/SOURCE_TRACEABILITY.md:88-96`;
`docs/architecture/adr/ADR-0001-greenfield-behavioral-oracle.md:10`;
`src/auditmanager/__init__.py`; `fixtures/golden/GJ-0*/manifest.json` `provenance.method`.

### MT00-03 — Identity walk — **PASS**

**What I did.** I used the golden journey that is precisely this scenario, `GJ-03` —
"Finding rerun, decision carryover under provider failure, and expert correction or
revocation" — and walked its synthetic inputs on paper through
`Finding` / `FindingObservation` / `ExpertDecision`, then checked whether the contracts
force the walk I had drawn.

**The walk.** `previous_version_findings.json` on `SYNTH-VER-01` carries `F-001`, `F-002`,
`F-003`. `expert_decisions_v1.json` records `F-001` accepted and `F-002` rejected. The
rerun on `SYNTH-VER-02` in `current_version_findings.json` produces `F-101`, `F-102`,
`F-103`, with `restated_from_hint` pointing back at `F-001` and `F-002` — a *hint*, not a
key, and `F-103` carries none. Every display ordinal changed across the rerun. If `F-NNN`
were the key, both expert decisions would be orphaned or, worse, silently reattached to
whatever ordinal now occupies the slot.

The contracts refuse that. `contracts/domain/v1/identifiers.json` `distinct_identities
.finding_identity` states: `finding_uid` is the durable semantic issue identity that
carries expert history across reruns; `finding_observation_id` is immutable evidence
emitted by exactly one `run_id`; a rerun creates new observations and never rewrites or
removes earlier ones; and "when the versioned matching policy cannot justify carryover it
allocates a new `finding_uid` instead of reusing one" — so carryover fails closed into a
new identity rather than into a wrong attachment. `decision_identity` states that every
verdict, correction and revocation allocates a new `decision_id` and appends an immutable
event, never reused, updated in place or removed, with the current verdict a rebuildable
projection.

`F-NNN` is not merely unused as a foreign key; it is named in the `non_identity` list —
"display ordinal such as F-014" — alongside paths, S3 keys, sheet numbers and checksums,
under the rule at `identifiers.json:21` that none of them "is an identity and none may be
used as a foreign key." `docs/architecture/DOMAIN_MODEL.md:69` repeats it: "Display ordinal
such as `F-014` belongs to a run/read model and **never** serves as FK."
`docs/architecture/GLOSSARY.md:16` and `docs/LEGACY_BEHAVIOR_BASELINE.md:18` carry the same
statement, the latter naming the legacy behaviour it replaces. `ADR-0010` is the authority
and is `accepted bootstrap`.

The revocation half of `GJ-03` matches `PD-01` as approved with modification: revocation
moves the projection to `pending` and restores no earlier verdict.
`ambiguous_revocation_request` in the fixture carries empty `project_id` and `item_id`,
which is the fail-closed case, and no error code exists for deleting or overwriting a
decision event — `error-codes.json` `open_owner_decisions[PD-01]` says so explicitly and
routes such a request to `state_transition_not_allowed`.

**Record:** `PASS`. Evidence: `fixtures/golden/GJ-03/inputs/*.json`;
`contracts/domain/v1/identifiers.json` `distinct_identities`, `non_identity`;
`docs/architecture/DOMAIN_MODEL.md:69`; `ADR-0010`.

### MT00-04 — Run/job/attempt walk — **PASS**

**What I did.** I modelled provider timeout → retry → stale worker result against
`contracts/domain/v1/state-machines.json`, and asked at each step whether the three
identities can be conflated and whether a stale Attempt can publish.

**The walk.** A top-level audit command is accepted, `machines.audit_run.run_creation`
freezes the input manifest, `analysis_profile_id`, `prompt_bundle_id` and
`norms_snapshot_id`, and one `run_id` is created. The Job is queued; Attempt A is created
and leased, and the guard requires "the Lease and the new current execution token are
created in the same transaction as the Attempt". Attempt A moves `leased → running` on
presenting the current execution token, on violation `execution_token_invalid`.

The provider times out. The heartbeat deadline is missed, so Attempt A goes
`running → lost`, guarded by "the Job releases the lease in the same transaction". The Job
goes `running → retry_wait`. `machines.job.retry` is explicit: `in_place: true`, creating
"a new `attempt_id` whose execution token supersedes the previous one; never a new `run_id`
and never a new `job_id`", and "Retry, resume, restart and worker failover reuse the same
Job and create a new Attempt. None of them creates, reopens or duplicates an AuditRun."
The Job returns to `queued` and Attempt B is leased.

Attempt A's worker then wakes and delivers its result. This is the case the runbook asks
about, and it is closed in three independent places. The `running → succeeded` guard
requires "the presented execution token is still the current one and the result package
passed schema, checksum and manifest validation inside the publishing transaction", on
violation `stale_attempt`. `terminal_semantics` gives `lost` and `superseded`
`publishes_result: false` with "the same store-only, never-publish rule". And
`publication_authority` states the invariant once: "At most one Attempt per Job may publish
at any instant: the Attempt in `running` that presents the current execution token, checked
inside the publishing transaction", with `late_delivery` — a result from an Attempt in
`superseded`, `lost`, `cancelled` or `failed` "is accepted for storage as immutable
evidence, is never applied to project state, and the delivery is answered with
`stale_attempt`." `stale_attempt` and `execution_token_invalid` are both in the 20-code
catalog and both in the error envelope enum.

The three identities do not collapse. `distinct_identities.execution_identity` states that
"None substitutes for another, none is derived from another and none may be reconstructed
from `project_uid`, `version_uid` or a worker task handle." `run_creation` enumerates eight
triggers, and the only one that produces a new Run under retry is none of them: "retry,
resume, restart or worker failover of work that already belongs to a run → no new `run_id`
and no new `job_id`". A repeat of a terminal Run under the same idempotency key and payload
returns the original Run; a different payload fingerprint yields `idempotency_key_reuse`
and changes nothing; any request that would move a terminal Run back to non-terminal is
refused with `state_transition_not_allowed`. That is the `PD-03` precedence clarification
of 2026-09-01 applied consistently in both the machine and the command-idempotency table.

The numeric parameters this walk needs — lease duration, heartbeat interval, grace window,
retry budget, backoff — are all absent and all recorded as deferred. That is MT00-06's
subject and it is clean there.

**Record:** `PASS`. Evidence: `contracts/domain/v1/state-machines.json` `machines.attempt`
(guards, `terminal_semantics`, `publication_authority`), `machines.job.retry`,
`machines.audit_run.run_creation`, `machines.command_idempotency.repeat_semantics`;
`contracts/domain/v1/error-codes.json`; `identifiers.json` `execution_identity`.

### MT00-05 — Comparison ownership — **PASS**

**What I did.** I modelled auto suggestion → user-approved sheet link → recompute → AI
review against `GJ-04` — "Stage comparison links, reuse, stale invalidation, repair and
undo" — `contracts/comparison/v1/README.md` and `ADR-0013`.

**The walk.** Automatic matching produces suggestions; `contracts/comparison/v1/README.md`
lists them as layer 1, "rebuildable automatic matching suggestions". The user approves a
sheet link; that is layer 2, "authoritative user-approved `SheetLink` / explicit unlinked
state", and `GJ-04` states it as an expectation: "Saved sheet links are the authoritative
decision: saving replaces the prior explicit link set and supersedes any outstanding repair
suggestion." Recompute runs: "Running the deterministic difference computation again with
an unchanged signature returns the stored artifact instead of recomputing it, and the
reused artifact is reported as not stale", and changing a source, a link or an exclusion
changes the signature so downstream artifacts become stale and "the mandatory gate refuses
to run further stages until the exclusion state is refreshed". The approved link is input
to the signature, not output of the recompute, so recompute cannot overwrite it — it can
only be invalidated by a change the user made.

The AI layer is additive and cannot touch raw evidence. `GJ-04` states it twice, once
positively — "The AI layer is additive over the current deterministic comparison and
difference artifacts; completed groups can be reused on an unchanged signature while failed
and partial groups stay failed and partial" — and once as a prohibition: "Raw deterministic
comparison evidence is immutable for the AI layer: an AI stage may only add its own
artifact and may never edit, delete or reinterpret the stored raw difference record."
`ADR-0013` is the authority: "Deterministic text exclusions/diff and raw graphic evidence
are immutable per comparison revision. AI review/synthesis is a derived artifact keyed by
raw checksums."

Repair is the one path that changes an approved link, and it is fenced: applying a
high-confidence repair "validates the confidence and the current source, records a durable
repair history entry and recomputes the downstream deterministic stages", and undo
"restores the snapshot captured before the repair … so the link set and the deterministic
artifacts return to their pre-repair values" — layer 5, "repair proposal/action/undo with
proof and audit".

Graphic/vector comparison is absent by decision, not by omission: `PD-04` approved, first
contractual inclusion in W7 with a dedicated golden graphic pair, and `GJ-04` records the
observed legacy absence without converting it into a capability claim. The comparison
contract family is a README-only area frozen in S06, which the README says on its first
line; I did not treat that as a gap because CP-00 freezes the conceptual separation, not
the schema.

**Record:** `PASS`. Evidence: `contracts/comparison/v1/README.md`; `ADR-0013`;
`fixtures/golden/GJ-04/manifest.json` `expected_outputs`.

### MT00-06 — Unresolved decisions — **PASS**

**What I did.** I read the proposed ADR and the owner decision ledger, then swept the
repository numerically for any value that would mean a deferred decision had been silently
answered.

**What I observed.** `ADR-0014` is the single `proposed` ADR and the single `defer` in the
architecture disposition. Its "Unresolved owner decisions" section names exactly the four
things: "Exact TTL/legal retention, tenant model, identity provider and legal-hold
authority are not supported by supplied sources and must be approved before CP-09
production gate. No arbitrary TTL is baked into code before that decision."

`CP00_OWNER_DECISIONS.md:677-696` carries the `U-01`–`U-06` table. `U-04` is the only input
still open, and it is open by explicit owner disposition with its own deadlines —
tenant/IdP before `W2-C-01`, TTL and legal hold before `W9-C-01` — and the document states
what that blocks with precision: `ADR-0014` stays `proposed`, the retention and legal-hold
clauses of `ADR-0015` and the `P-13` obligations are not ratified, "and no tenant model,
identity provider, TTL, retention or legal-hold value is encoded in any contract."
`U-01` is deferred with a deadline; `U-02`, `U-03`, `U-05`, `U-06` are disposed of.
`OQ-02` (lease/heartbeat/grace) and `OQ-04` (retry budget/backoff) sit inside the contracts
that would consume them, each with `status: deferred`, a named owning slot, and a gate
sentence forbidding a value before that task: "No numeric value is chosen before that task
and no lease implementation may proceed without it."

The sweep confirms the claim rather than trusting it. A search for any JSON field named
`ttl`, `retention*`, `lease_*`, `heartbeat*`, `grace*`, `backoff`, `retry_budget`,
`max_retries`, `max_attempts` or `timeout` bound to a number, across `contracts/`,
`fixtures/`, `db/`, `src/`, `web/` and `infra/`, returns **nothing**. A search for a
retention or legal-hold word within 60 characters of a duration in `contracts/` and
`docs/architecture/` returns **nothing**. No value is invented anywhere I can reach.

`ADR_INDEX.md:31,38,41` enumerates `PD-01`–`PD-04` while five decisions are recorded, and
`ARCHITECTURE_BIBLE.md:9`, `contracts/domain/v1/README.md:962` and
`fixtures/golden/SELECTION.md:19` carry the same stale enumeration. These are disclosed in
`manifest.known_pre_ratification_items` as `ADR_INDEX_decision_count` and
`stale_PD_enumeration_inside_the_frozen_candidate`, owned by `W0-INT-01`, with `ADR_INDEX.md`
inside `RATIFICATION_DELTA_CEILING` so ratification can fix it. I raise them only as noted
in F-6, because none of them invents a value or hides an unresolved decision — `PD-05` is
fully recorded in `CP00_OWNER_DECISIONS.md` and `CURRENT_STATE.md`, and
`W0-INT-01.md:77-78` states the defect correctly. This case asks whether unconfirmed values
are explicitly unresolved rather than fabricated. They are.

**Record:** `PASS`. Evidence: `docs/architecture/adr/ADR-0014-authz-classification-retention.md`;
`docs/architecture/CP00_OWNER_DECISIONS.md:660-696`; `contracts/domain/v1/identifiers.json`
`open_questions[OQ-02]`; `contracts/domain/v1/state-machines.json` `open_questions[OQ-04]`;
numeric sweep, empty.

## Final acceptance checklist

- [x] **Нет hidden Strangler runtime dependency.** No runtime exists; no legacy import
  exists anywhere in the tree; every legacy read is a pinned read-only Git-object command;
  the non-transfer of the source Strangler model is a recorded decision at
  `SOURCE_TRACEABILITY.md:89-90`, `ADR-0001`, and `CP00_ARCHITECTURE_REVIEW.md:174,186,432`.
  Verified in MT00-02, mechanically as well as by reading.

- [x] **Все ключевые bounded contexts имеют владельца данных.**
  `docs/architecture/CONTRACT_CATALOG.md:9-16` assigns an owner role and a consumer set to
  each of the six contract families, and states that the owner is a role rather than a
  standing appointment. `ADR-0003` fixes the rule — "One aggregate/entity has one
  authoritative writer" — and each of the six state machines in
  `contracts/domain/v1/state-machines.json` carries an explicit `authoritative_writer`
  field. `src/auditmanager/*/README.md` names the data each boundary owns.

- [x] **Shared contract freeze/process понятен reviewer без устного пояснения.**
  `docs/program/VERSIONING_AND_FREEZE_POLICY.md` defines the three freeze levels (design,
  contract, checkpoint), the version-bump rules, and a six-step freeze-break procedure.
  `docs/program/INTEGRATION_POLICY.md` defines branches, merge order and conflict
  ownership. `docs/program/WAVE_EXECUTION_GUIDE.md` and `ROADMAP.md:35-53` define the
  wave/lane/integration-slot model. I read these cold and needed no explanation. The
  process documents are not where this round fails; the records of what the process has
  *done* are.

The checklist passes in all three items. It does not lift the `MT00-01` `FAIL`, and it
should not be read as offsetting it: the checklist asks about the architecture, and the
architecture is sound.

## Stop / cleanup

The runbook says: "Stop the local stack using the documented command."

**Not applicable at CP-00, and recorded as such rather than substituted.** There is no
local stack. `manifest.runtime_fields` is "not applicable - architecture-only checkpoint";
`README.md` fixes exact tool versions at CP-01; `db/migrations/` contains only a
`README.md`, so there is no migration head to record; `src/` and `web/` contain only
boundary READMEs and one docstring. No documented start command exists, so no documented
stop command can. Earlier rounds reached the same conclusion and I reached it
independently, from the same artifacts.

The remaining two clauses were executed:

- **Preserve only synthetic/anonymized evidence.** This report contains no production
  payload and no sensitive data. Every fixture I cite is synthetic (`SYNTH-PRJ-03`,
  `SYNTH-VER-01/02`, `synthetic-reviewer-a/b`). Every legacy reference is a commit SHA
  already recorded in `docs/SOURCE_TRACEABILITY.md`.
- **Remove temporary credentials/tokens and local fault-injection overrides.** None were
  created. I injected no fault, set no environment variable, and used no credential. All
  probe scripts were written under the session scratchpad outside the repository; nothing
  temporary was written inside it. `git status --porcelain` shows the repository
  unmodified by me: the only working-tree entry at finish is the parallel automated
  stream's own untracked report.

## Findings

| # | Severity | Finding | Where | Owner |
|---|---|---|---|---|
| F-1 | **Blocking** | CP-00 acceptance record three rounds stale; skipped by the round-8 remediation though named by path and line in the round-7 report and in the manifest's own round-7 note | `artifacts/checkpoints/CP-00/acceptance.md:7-8,11,13-14,22-26` | `W0-INT-01` |
| F-2 | **Blocking** | Wave document asserts a fail-able completeness check over every tracked file; no such check exists in the tree, and the script named in the commit message is untracked. Same file, `:5`, still says the candidate awaits the round-eight freeze | `docs/program/waves/W0.3_ratification_integration.md:5,200-204`; repeated in `manifest.json` round-8 `note` | `W0-INT-01` |
| F-3 | Non-blocking | Freeze-already-done routing: `manifest.status` is `acceptance_round_8_pending_freeze` after `b21e727` froze it, contradicting `acceptance_rounds[8].status = "frozen"` in the same file; `ratification_blocked.remaining` and `CURRENT_STATE.md:249-250` both still route the freeze as the next action | `manifest.json` `status`, `ratification_blocked.remaining`; `docs/program/CURRENT_STATE.md:249-250` | `W0-INT-01` |
| F-4 | Non-blocking | Present-tense "The live value is `e7f39890211b…`" survives inside the §11 round narrative, contradicting §1 of the same document. Round 7's automated stream adjudicated this line as acceptable narrative; I record my disagreement without blocking on it | `docs/program/reviews/W0-QA-01.md:3128-3131` | `W0-INT-01` (stage-closing review) |
| F-5 | Non-blocking | Truncated sentence: the round-eleven banner breaks off at "and — stated once and pinned in code —" where the round-twelve banner was inserted; the completed sentence exists at `:63-65` | `docs/program/reviews/W0-QA-01.md:53-54` | `W0-INT-01` (stage-closing review) |
| F-6 | Observation | `REPOSITORY_TREE.txt` describes the delivered bootstrap package rooted at `auditmanager-greenfield-bootstrap/`, not this repository. It omits `artifacts/`, `docs/program/tasks|waves|reviews/`, `tests/contract/*.py` and `fixtures/golden/**`. It carries no "as of" label, is referenced by no other document, and is named by no task's allowed paths and no known-items entry | `REPOSITORY_TREE.txt` | `W0-INT-01` to disclose or retire |
| F-7 | Method | `candidate_digest_recipe` includes `git ls-files --others --exclude-standard`, so the frozen digest stops reproducing the moment either acceptance stream writes its report into the working tree. Two streams that must both confirm the digest race each other; the recipe does not say to exclude the round's own report paths | `manifest.candidate_digest_recipe` | `W0-INT-01`, or the next task touching the QA module |

F-7 is measured, not argued. At `2026-09-04T12:04:47Z` the recipe over 218 paths returned
the frozen value. At `2026-09-04T12:14:22Z`, with the automated stream's untracked
`automated-report-round-8.md` present, the same code over 219 paths returned
`4ad3c9381831830c122b7d3bec73baba56898d328c0862c1f139edfffd70ef49`. Removing that one path
from the set restores `959d5db2…058f` exactly. The frozen tree is intact; only the recipe's
literal path set moved. Round 7 recorded that the automated stream had not yet written its
report at either of its measurements, so this raced past unnoticed rather than being
absent. It is a scope limit of the recipe, adjacent to the recorded
`evidence_report_visibility` limit but distinct from it: that one is about a report hidden
by `.gitignore`, this one is about a report that is present.

## Is the round-eight state reconciliation complete?

**No.** I did not take the completeness claim on trust and I did not confine the search to
the axes that failed in rounds six and seven.

What `a3eaf88` did fix, I verified independently and it holds. The superseded evidence
commit `e7f3989` no longer appears as live anywhere in the plan-of-record layer: all 42
occurrence lines are labelled or are committed round-6/round-7 evidence, and the five sites
round six named now carry `3da104e5…`. `CURRENT_STATE.md` and `CHECKPOINT_REGISTRY.md` both
carry correct round-8 accounting. The `S00` column header, the `W0-INT-01` banner, the wave
document's task table and integration order, and QA report sections 1, 12.1 and 12.5 all
read correctly. The manifest's `ratification_blocked` object no longer names a test that
does not exist.

What it did not fix is the third file named in the same sentence of its own round-7 record.
`acceptance.md` was raised by line number by the previous round and by name in the
manifest, and it was passed over. That is the third consecutive round in which a
remediation was declared exhaustive and was not, and the second in which the surviving site
had already been named by the round before.

The mechanism the round used to demonstrate completeness is itself part of the problem.
The stated evidence — a sweep that fails on the previous tree — is not in the repository, so
no reader of the frozen candidate can run it or see what it covered. Its rule, as described
in the wave document, is a proximity heuristic on the word "superseded", and I found one
site where that heuristic passes text asserting the opposite (F-4). The rule also has no
purchase at all on the axis that actually failed here: round accounting is not an
occurrence of a superseded commit, so a sweep built for the round-six axis could not have
caught the round-seven axis, and did not.

The reconciliation is close. It is not complete, and it is not demonstrated to be complete.

## On the integrator's edits to the QA report

Asked to judge whether the handling is adequate. **In substance yes; in structure no; and
the record of it now overstates what was done.**

The necessity is real and correctly analysed. A review report structurally cannot name the
commit that contains it, so section 1 named its predecessor, and that became false the
moment round twelve was integrated. Section 12.5 of the report is itself a handoff
instructing the integrator to make exactly this correction after exactly this event, so the
edits follow the accepted handoff rather than overriding it. They change no verification
claim: I read sections 1, 12.1 and 12.5 and the change is confined to which SHA is named as
live and which are named superseded. Each is labelled as the integrator's in the text where
it appears — `:72` "This row was corrected by the integrator after acceptance", `:3246`
"Corrected by the integrator after acceptance, with section 1 and section 12.5, in the
round-eight remediation", `:3282` "Corrected by the integrator after acceptance, as this
handoff instructed". The disclosure is genuinely in three places: the in-text labels,
`manifest.known_pre_ratification_items.integrator_edit_to_an_accepted_deliverable`, and the
wave document's exception "Two". Both edits are named, both are attributed, and the shape
is correctly distinguished from the wave's three earlier exceptions. For an acceptance
reader, that is adequate: I could reconstruct exactly what was changed, by whom, why, and
under what authority, without being told.

Two things are not adequate.

**The structural hole is left open.** The path is in no task's `allowed_paths`,
`W0-INT-01`'s included — the exception record says so itself. So each edit is a bespoke
exception rather than an exercise of a declared licence, and the cheap fix was not taken:
adding the path to `W0-INT-01`'s allowed paths, narrowed to the evidence-commit rows, would
convert a recurring exception into a bounded permission. Because it was not taken, the
third edit that F-4 and F-5 now require has no home either, and will arrive as a fourth
undeclared write into the same accepted deliverable. Twice is a pattern; the record should
stop calling it an exception and start licensing it.

**The exception record now carries the defect it describes.** Its closing sentence claims
the round-eight remediation "replaced that declaration with a check that can fail". It did
not — that is F-2. So the paragraph that exists specifically to record two rounds lost to
an unverified exhaustiveness claim closes by making an unverified claim of its own, in the
same file, about the same remediation. That is not a cosmetic irony. It is the reason a
reader cannot tell, from the package alone, whether the sweep that is supposed to guarantee
completeness covered `acceptance.md` and reported clean, or never looked at it.

## Known limitations

- **What manual acceptance is here.** CP-00 is an architecture-and-behaviour freeze with no
  running product. All six cases are reading and judgment over documents and machine
  contracts, not exercise of a system. `MT00-04` and `MT00-05` are paper walks against
  state machines and expectation lists, as the runbook directs; nothing was executed, and
  no behaviour was observed. An independent agent is the closest available analogue of a
  human tester, not a substitute for one. This is stated so a later reader weighs the
  evidence for what it is.
- **What I could not judge.** Whether the frozen contracts are the *right* contracts for
  the product is an owner and domain-owner judgment; I judged internal consistency,
  navigability and whether stated guarantees are supported. Whether the two external
  snapshot repositories carry what the traceability document says they carry: I confirmed
  that six referenced objects resolve in `/root/projects/PDF-proverka/PDF-proverka` and did
  not audit their contents. The correctness of `W0-QA-01`'s 281 tests as *tests* is that
  task's accepted result and two reviewers' finding; I ran the suite and confirmed it is
  green on this tree, which is a weaker statement.
- **`GATE.sh` and `E-06`.** The QA report records that round ten's acceptance gate fails,
  and that the failure is a true report about `scripts/validate_bootstrap.py:116` and
  `tests/contract/test_validate_bootstrap.py:32` spawning Git with an inherited
  environment. Both paths sit under the frozen `scripts/` family and the escalation is
  routed to W1. I did not re-adjudicate it and did not attempt a repair; it is recorded as
  open in `manifest.open_escalations` and I confirm it is still open and still correctly
  described.
- **The parallel automated stream.** It wrote `automated-report-round-8.md` while I worked.
  I did not read it and reached every conclusion above independently. Its arrival is what
  made F-7 measurable.
- **`docs/INDEX.md`** has no entry for `docs/program/reviews/W0-QA-01.md`, the only W0.3
  deliverable absent from the index. I did not raise it as a finding because the review is
  reachable from the wave document, the task file and `W0-INT-01`; a reader is not stranded.
  Noted so it is not re-discovered as new.

## Result

Per case:

| Case | Verdict |
|---|---|
| MT00-01 Documentation navigation | **FAIL** |
| MT00-02 Greenfield boundary | PASS |
| MT00-03 Identity walk | PASS |
| MT00-04 Run/job/attempt walk | PASS |
| MT00-05 Comparison ownership | PASS |
| MT00-06 Unresolved decisions | PASS |

**Overall: FAIL — 5/6, with `MT00-01` failing.**

Two blocking findings, F-1 and F-2, both in integrator-owned state and process records,
both inside the scope the round-eight remediation declared complete, and both in files
outside `POST_FREEZE_DELTA_CEILING` — so correcting either voids this round. Round 8 cannot
be recovered by remediation. The corrections must land and round 9 must be frozen and
dispatched on the corrected tree.

For the third round running, **no contract, schema, fixture, state-machine, identifier or
golden defect was found in any of the six walks.** The four reviewed families remain
byte-identical to `reviewed_candidate_commit` — `artifact_manifest_sha256` reproduces over
100 files — the suite is `Ran 281 tests … OK`, every declared count reproduces from the
artifact it counts, and 152 markdown files carry zero broken links. The architecture is
sound and the `W0-QA-01` `ACCEPT` still holds. What fails is the checkpoint procedure's
record of itself, in the same shape as rounds six and seven: a remediation declared
complete, over a scope that was named for it, that did not cover the scope.
