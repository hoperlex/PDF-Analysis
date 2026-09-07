# CP-00 manual acceptance — round 10

Runbook: `docs/manual-tests/CP-00_architecture.md`, executed as written.

## Start record

```text
candidate_commit:          2ea7b68b4c4455b03ed4f8437d12f5f35f56af58
tree_hash:                 ed5757cbd102232d4b4268aea2e4f27734af47e5
tested_candidate_digest:   00977a8704cbe381f02eaefccbb50ab5d32ee838f457f6f8873ba1cff6d8b3e5
                           recomputed independently over the 221 paths of the freeze
                           commit's own objects; MATCHES the manifest top-level field
                           and the round-10 acceptance_rounds entry.
                           Not a blocking criterion this round, by owner decision.
artifact_manifest_sha256:  39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08
                           recomputed independently over 100 files from the recipe;
                           MATCHES; artifact_count 100 confirmed; identical when
                           computed from the working tree, from HEAD's objects, and
                           from reviewed_candidate_commit's objects
reviewed_candidate_commit: 92e13fa496a723ed6e4c3adbf138c4f4e1d7c368 — resolves; the four
                           reviewed families are byte-identical to it at HEAD
qa_evidence_commit:        3da104e5d6fafb2a581bda377a07911183af803f — resolves
contract_manifest:         artifacts/checkpoints/CP-00/manifest.json
contract_versions:         domain 1.0.0-draft.1; analysis 1.0.0-draft.1; events
                           1.0.0-draft.1; golden_selection_schema 1. All three catalogs
                           carry status draft_candidate, frozen false, candidate_revision 5.
                           api and comparison are README-only areas, not versioned contracts.
migration_head:            none — db/migrations carries only README.md
backend_runtime:           not applicable - architecture-only checkpoint
frontend_runtime:          not applicable - architecture-only checkpoint
local_infra_versions:      not applicable - architecture-only checkpoint
tester:                    cp00_manual_tester, independent manual acceptance stream
started_at:                2026-09-07T11:42:59Z
finished_at:               2026-09-07T11:56:59Z
```

Every timestamp above was measured with `date -u` in this session.

### Independence

I authored none of the reviewed artifacts, none of `tests/contract/test_cp00_candidate.py`,
none of `docs/program/reviews/W0-QA-01.md`, none of the state documents,
none of `artifacts/checkpoints/CP-00/check_state_records.py`, and none of the
round-3, round-6, round-7 or round-8 reports. I carried no earlier verdict forward.
I read `manual-report-round-8.md` for the form of a start record and for the house
register, and I re-derived every finding and every pass below on this tree. Where a
round-8 finding bears on something I re-examined, I say so and I say what I measured
myself.

I wrote exactly one path in this repository: this report. I ran no command that moves
refs, the index or the working tree — no `add`, `commit`, `checkout`, `stash` or
`restore`. I did not clone or copy the repository at any point; the suite was run in
place, in a tree that was clean at the time, with nothing else of mine running.

### Working tree state, and a concurrent write during the round

At start the tree was clean: `git status --porcelain` empty, 221 tracked paths, zero
untracked non-ignored files.

At 11:54 — after my suite run and my digest measurements, before I finished the
document walks — a concurrent session modified
`artifacts/checkpoints/CP-00/manifest.json` in the working tree. I am not that writer
and I did not revert it. Measured:

- file mtime `2026-09-07 16:54:41 +0500`;
- the diff adds two `known_pre_ratification_items` entries
  (`stale_transcripts_in_the_qa_review_report`, `unreproducible_mutation_row`) and
  rewrites `recorded_limits.prefix_widening_unpinned` to withdraw an unverified count;
- recomputed from the **working tree**, `tested_candidate_digest` becomes
  `533691c43a517c16cef74325fc980d2418503e776d604b06cab7557d9cefe076` and no longer
  reproduces the frozen value;
- recomputed from the **freeze commit's objects** it still reproduces exactly:
  `00977a87…b3e5`;
- the four reviewed families are unaffected — `artifact_manifest_sha256` is unchanged
  at `39721aac…5e08` from the working tree, from HEAD's objects and from
  `reviewed_candidate_commit`'s objects, and
  `git status --porcelain -- contracts fixtures docs/architecture scripts` is empty.

This is recorded, not glossed. It does not change any verdict below, for three
reasons I checked rather than assumed: the semantic freeze is the four reviewed
families and they did not move; the whole-tree digest is not a blocking criterion this
round by owner decision; and the manifest is a `POST_FREEZE_DELTA_CEILING` path, so
the mechanism licenses it to move after a freeze. It is nevertheless a write into the
frozen candidate while an acceptance round is live, and it is listed as finding F-6.

### Digest confirmation and discrimination probes

I implemented `artifact_manifest_recipe` from the manifest text alone and did not call
the module's helper: `git ls-tree -r --name-only <commit> -- contracts fixtures
docs/architecture scripts`, sorted; sha256 over, for each path in order, the UTF-8
path bytes then the RAW 32-byte sha256 of the file content.

| Source of the 100 blobs | Digest | Result |
|---|---|---|
| working tree | `39721aac…5e08` | matches the manifest field |
| HEAD (`2ea7b68`) objects | `39721aac…5e08` | matches |
| `reviewed_candidate_commit` (`92e13fa`) objects | `39721aac…5e08` | matches |

The three agreeing is the byte-identity claim, confirmed independently of
`git diff` — which is also empty over those four paths between `92e13fa` and
`2ea7b68`.

A match is worth nothing unless the function discriminates. Six probes, each a single
deliberate deviation from the recipe:

| # | Perturbation | Digest | Result |
|---|---|---|---|
| P0 | none — baseline | `39721aac…5e08` | matches the frozen value |
| P1 | one byte appended to `contracts/README.md` | `5c33e79a…7b54` | DIFFERS |
| P2 | hex text hashed instead of raw digest bytes | `1be19d16…4fcf` | DIFFERS — the raw-bytes clause is load-bearing |
| P3 | one family path dropped (99 paths) | `a59d1cab…39a0` | DIFFERS |
| P4 | path order reversed | `85ed8189…7513` | DIFFERS — the sort is load-bearing |
| P5 | one non-family path (`README.md`) included | `df5fa6f9…4e8e` | DIFFERS — the family scope is load-bearing |
| P6 | `scripts` family omitted (98 paths) | `c227eb8e…bf50` | DIFFERS — all four families are load-bearing |

`tested_candidate_digest` was recomputed from `candidate_digest_recipe`, likewise
implemented from the manifest text: `git ls-files` plus `git ls-files --others
--exclude-standard`, sorted; the manifest contributes the sha256 of
`json.dumps(manifest, sort_keys=True, separators=(',',':'))` with only
`tested_candidate_digest` blanked, at the top level and in every `acceptance_rounds`
entry, `evidence_bundle_digest` keeping its value. Over the freeze commit's 221 paths
it reproduces `00977a87…b3e5` exactly. At the moment of my first measurement the
working tree carried no untracked non-ignored file, so the `--others` clause was inert
and the tracked-only variant gave the same value; after the concurrent write it no
longer reproduces from the working tree, as recorded above.

### Suite, run in place in a quiet tree

The documented command, run with nothing else of mine executing and the tree clean:

```text
$ .venv/bootstrap/bin/python -m unittest discover -s tests/contract
Ran 324 tests in 49.586s
OK
```
started 11:44:13Z, finished 11:45:02Z. Per module: `test_cp00_candidate.py` 298,
`test_validate_bootstrap.py` 26, 298 + 26 = 324. `scripts/validate_bootstrap.py`
standalone prints `PASS`. I ran the suite to establish on my own evidence, rather than
on the automated stream's, that nothing below is a contract, schema, fixture or test
defect.

### How I applied the narrowed bar

The owner narrowed the bar for this round: a procedural or documentation defect blocks
only when it changes product semantics, security or data integrity. I applied it in
both directions and I want the reader to be able to check that I did.

Downward: I did not fail a case over a stale round number or an out-of-date status
line. Several exist and they are findings F-1 to F-4 below.

Upward: I searched specifically for the classes the owner said do not get a pass —
a document misstating an identifier rule, a state machine, an error contract, an
evidence anchor or an architectural boundary — and I searched them as their own axes
rather than hoping to meet them. Identifier rules: the `finding_uid` /
`finding_observation_id` / `F-NNN` separation and the `run_id` / `job_id` /
`attempt_id` separation, checked at every site that states them. State machines: the
three execution machines read transition by transition against their guards and
terminals. Error contract: the 20-code catalog, the two `stale_authority` codes and
the envelope's forbidden detail keys. Evidence anchors: every `[L]` and `[S]` anchor
I could resolve, in both repositories, including `symbol@line`. Architectural
boundaries: the greenfield/legacy boundary, the comparison data-ownership boundary and
the AI/deterministic boundary. All five axes are clean, and the detail is in the cases.

## Test cases

### MT00-01 — Documentation navigation — **PASS**

**What I did.** I walked the route the package documents in `README.md`, in order:
`README.md` → `docs/PRODUCT_SYNOPSIS.md` → `docs/architecture/ARCHITECTURE_BIBLE.md`
→ `docs/architecture/ADR_INDEX.md` → `docs/program/ROADMAP.md` →
`docs/program/WAVE_EXECUTION_GUIDE.md` →
`docs/stages/S00_architecture_and_behavior_freeze.md`, reading each document rather
than checking that its file existed. From S00 I followed the onward pointers a reader
is actually given: the W0.3 wave plan, `docs/INDEX.md`, `docs/program/CURRENT_STATE.md`,
`docs/program/CHECKPOINT_REGISTRY.md`, the CP-00 manifest, the CP-00 acceptance record,
`docs/SOURCE_TRACEABILITY.md`, the `W0-INT-01` and `W0-QA-01` task files and
`docs/program/reviews/W0-QA-01.md`.

I then swept four axes mechanically, choosing them before reading what earlier rounds
had failed on: every markdown link and anchor; every repo-rooted path token in live
documents; every SHA-shaped token against both repositories; and every declared count
against the artifact that carries it.

**What resolves.** The chain is complete; all seven documents exist and every onward
pointer resolves.

- **Links.** 154 tracked markdown files, 264 inline links: **0 broken relative links
  and 0 broken anchor fragments.** My first pass reported five broken self-anchors in
  `CP00_OWNER_DECISIONS.md`; that was my slugifier collapsing runs of whitespace where
  GitHub does not. Corrected, the count is zero. I record the false positive because a
  later reader repeating my walk with a naive slugifier will hit it too.
- **Paths.** 1442 backticked path-like tokens; every non-resolving one in a live
  document is a declared future path (`contracts/optimization/v1/**`, gated behind
  `W5-OPT-01` and `U-06`), a glob or lint-rule illustration
  (`src/auditmanager/**`, `web/src/**`), or a legacy-snapshot path carrying the `[S]`
  notation. No live document sends a reader to a repository path that should exist and
  does not.
- **Evidence anchors — the axis the narrowed bar does not excuse.** Every one I tested
  resolves, and resolves to what it claims. In the legacy repository at
  `/root/projects/PDF-proverka/PDF-proverka`: `32b9d903…` (behavioral oracle),
  `0b937dc0…` (architecture source) and `71bac5f2…` are commits; `040a514d…` is a blob
  and `f9c537c4…` is a tree, and both are exactly what `SOURCE_TRACEABILITY.md` §1.2
  claims — `git rev-parse 0b937dc0:docs/architecture/ADR_BIBLE.md` returns `040a514d…`
  and `git rev-parse 0b937dc0:docs/architecture/adr` returns `f9c537c4…`. Every `[S]`
  path I sampled exists at `0b937dc0`, including the four the review cites that have no
  counterpart here (`ADR_BIBLE.md`, `ADR-0018-domain-contract-v1.md`,
  `ADR-0016-workspace-isolation.md`,
  `ADR-0014-data-classification-retention-and-erasure.md`). Every `[L]` path exists at
  `32b9d903…`, and the `symbol@line` anchors land on the named symbol at the named
  line: `migrated_findings_service.py:_stable_migrated_id@1436` and
  `knowledge_base_service.py:_append_to_decisions_log@683` and `revoke_decision@861`
  are all exact. Every local frozen input resolves here: `6c82004b…`, `134436502b…`,
  `667fb00f…`, `cf774047…`, `92e13fa4…`, `3da104e5…`.
- **Counts.** 100 reviewed artifacts (matching `artifact_count`); 33 architecture lint
  rules; 25 identifiers; 6 state machines; 20 error codes; 5 golden journeys; 95
  assertions; 18 ADR files and 18 ADR_INDEX rows; 11 manual runbooks; 298 + 26 = 324
  tests. All reproduce from the artifact that declares them, with one exception, F-4.
- **The superseded-evidence axis that killed rounds six and seven is closed, measured
  rather than assumed.** `check_state_records.py` on this tree reports axis one 0 and
  axis two 0, exit 0. I did not take that on trust: run with `--rev` it exits 1 at
  `bde3af3`, `a3eaf88` and `5b70ee4`, which is the claim the wave plan and the
  acceptance record make; at `5b70ee4` it names the two real superseded-evidence sites,
  and at `4bf2351` it names 17 stale round-accounting sites. `--selftest` runs 11 cases,
  0 failures. The guard discriminates, on my own measurement.
- **Round eight's F-2 is genuinely closed.** Round eight failed partly because a live
  document claimed an executable check that was not in the tree. The replacement,
  `artifacts/checkpoints/CP-00/check_state_records.py`, is tracked, is in the checkpoint
  package, runs, and does what the surrounding prose says it does on the three commits
  it names.

**Why this passes, and what it costs.** Four documentation defects are live on the
walked route. Every one of them is a stale status line or a stale count, and I could
not construct a reading in which any changes product semantics, security or data
integrity — the identifier rules, state machines, error contract, evidence anchors and
architectural boundaries are all clean on their own axes, checked directly in
MT00-02 to MT00-06. Under the bar the owner set for this round they are findings, not
blockers. They are F-1 to F-4 and they are stated as plainly as if they were blocking.

**Evidence reference.** Working-tree commands only, no credentials, no payloads; the
legacy repository was read through `git cat-file`, `git rev-parse` and `git show` at
the pinned commits and never checked out.

### MT00-02 — Greenfield boundary — **PASS**

**What I did.** I traced the main user journey as `PRODUCT_SYNOPSIS.md` §2 states it —
Object/Project → Document → Version → Ingest → Audit Run → Analysis Stages → Findings +
Evidence → Expert Review/Decision → Export/Knowledge/Comparison, and the critical first
path beneath it — and asked at each step whether any mandatory runtime step requires
running or importing legacy. I then swept `contracts/`, `src/`, `web/`, `infra/`,
`db/`, `scripts/`, `requirements/` and `tests/` for an import of, or call into, the
legacy application, and for any surviving Strangler runtime construct.

**What I observed.** No mandatory runtime step touches legacy, and the sweep returns
nothing: no import, no adapter, no proxy route, no shared database, no Strangler
phase. Legacy appears in exactly three roles, each stated where a reader meets it:
`README.md:3` — the repository "не предполагает runtime-зависимости от старого
приложения", with the four permitted roles enumerated as oracle, fixture source, edge-case
catalogue and parity reference; `ARCHITECTURE_BIBLE.md` P-19 "Legacy is a read-only
oracle"; `SOURCE_TRACEABILITY.md:90`, which says explicitly that the source Bible's
Strangler model, in which legacy stays production runtime, is **not** transferred and
that the repository is empty so no runtime Strangler is needed; and
`docs/behavior/legacy_capability_inventory.md:16` — "Runtime execution | None: no
legacy service, job, provider, migration or user flow was run".

The method is enforced structurally rather than promised. Legacy is read as immutable
Git objects at pinned commits — `[L]` anchors of the form
`32b9d903…:path:symbol@line`, `[S]` reads as `git show 0b937dc0…:<path>` — and
`CP00_ARCHITECTURE_REVIEW.md` §2 method rule 2 states that the mutable refactoring
checkout, its branch position and its worktree are not evidence. I verified that the
anchors resolve against those commits and not against a working copy, which is what
makes the boundary checkable rather than asserted. `SOURCE_TRACEABILITY.md` also
records that the local path is a discovery path of this workspace and not a
runtime/config contract, and that advancing legacy `main` does not move the baseline.

`ADR-0001` disposition in `CP00_ARCHITECTURE_REVIEW.md` §5 confirms the same
conclusion from the other side: the source ADR-0001 "hybrid Strangler" is `accepted`
in the source and **deliberately not transferred**, with the compatibility note "No
runtime Strangler dependency; algorithm ports require characterize → contract → tests
→ parity".

Verdict `PASS`. The final-checklist item "no hidden Strangler runtime dependency" is
met, and it is met by a boundary that is mechanically checkable, not only declared.

### MT00-03 — Identity walk — **PASS**

**What I did.** I took the legacy rerun-finding scenario the runbook asks for and
walked it on paper through `Finding` / `FindingObservation` / `ExpertDecision`, using
the contract catalogs as the normative source and the documents as the reader's route.
The two questions the case asks are whether `F-NNN` is ever needed as a foreign key,
and whether an expert decision survives a rerun only through the stable identity
policy.

**The walk.** `contracts/domain/v1/README.md` Walk 2 states it and the catalogs carry
it as data. Run `R1` publishes; `Finding fnd_…` carries observation `fobs_…₁`. The
expert accepts: `dec_…₁` is appended and `finding_current_verdict` projects to
`accepted`. Rerun `R2` allocates a new `run_id` and emits `fobs_…₂`; `R1`'s
observation is not rewritten, renumbered or deleted, and if the versioned matching
policy cannot justify carryover a **new** `finding_uid` is allocated rather than an old
one reused. Correction appends `dec_…₂` with a new `decision_id`, leaving `dec_…₁`
untouched. Revocation appends `dec_…₃` and moves the projection to `pending` — it does
not restore `dec_…₁` or `dec_…₂`. A request to edit or delete `dec_…₁` matches no
declared transition and is refused with `state_transition_not_allowed`; the catalog
deliberately declares no delete-decision or overwrite-decision code, and
`error-codes.json` records that as the approved `PD-01` position rather than an
omission.

**`F-NNN` is never needed as a foreign key, and I checked every site rather than
sampling.** The rule is stated in nine places and they agree: `ADR-0010:6,9` (legacy
display identifiers change after rerun and cannot carry expert history; display
ordinals are presentation only); `DOMAIN_MODEL.md:69` ("Display ordinal such as `F-014`
belongs to a run/read model and **never** serves as FK"); `GLOSSARY.md:16`;
`identifiers.json:21` and its `non_identity` list, which enumerate the display ordinal
beside paths, S3 keys, URLs and content checksums as things that are "addresses,
presentation values or verification values; none of them is an identity and none may
be used as a foreign key"; `contracts/domain/v1/README.md:146-149`;
`LEGACY_BEHAVIOR_BASELINE.md:18`; the runbook itself; and `ALR-14`
(`no-path-derived-identity`, static, error) plus `AGENTS.md` §4, which forbids
"path/filename/display number как identity". The only places `F-001`-style values
appear as data are the GJ-03 golden fixtures, where the back-pointer is named
`restated_from_hint` — a hint, explicitly not a key — and the single review row
`CP00_ARCHITECTURE_REVIEW.md:434` (DV-08), which records that legacy **did** use
`F-NNN` as a decision key and marks it an accepted greenfield divergence requiring
migration mapping. That is legacy characterization, and it is labelled as such.

**The decision survives the rerun only through stable identity.** `identifiers.json`
`distinct_identities.finding_identity` is the normative rule: "finding_uid is the
durable semantic issue identity that carries expert history across reruns.
finding_observation_id is immutable evidence emitted by exactly one run_id." The
projection is sourced from "the append-only ExpertDecision event stream for one
finding_uid", never from the observation and never from an ordinal. The failure
direction is fail-closed and explicit: an unjustifiable match allocates a new
`finding_uid` rather than inheriting a verdict, and `needs_manual_review` is declared
"an explicit visible outcome, not a silent fallback: a carryover or provider failure
must produce it instead of inventing or inheriting a verdict."

Identity shape is opaque throughout: `<prefix>_<ULID>`, pattern
`^[a-z][a-z0-9]{1,7}_[0-9A-HJKMNP-TV-Z]{26}$`, with rules forbidding decoding the ULID
body and forbidding any composite, derived or human-readable compound key.

**Two things I examined and decided are not defects.** First, `Finding` appears in
`identifiers.json` `entities` but in neither `machines` nor
`non_state_machine_aggregates`, and the README says the latter exists "so that 'no
machine' cannot be read as an oversight". I checked whether the registers claim to be
exhaustive: they do not, and 16 of the 25 bound entities are in neither — `Object`,
`Project`, `Document`, `DocumentVersion`, `Comparison`, `SheetLink`, `Worker`, `Lease`
and others alongside `Finding`. The catalog declares machines for the six aggregates
with durable lifecycles and explains four deliberate omissions; `Finding`'s state is
the `finding_current_verdict` projection, which is declared. Nothing misstates a state
machine. Recorded as an observation, not a finding. Second,
`CP00_ARCHITECTURE_REVIEW.md` cites `docs/architecture/adr/ADR-0018-domain-contract-v1.md`
while the local ADR-0018 is `ADR-0018-checkpoint-versioning.md`. That is not a
collision: the citation carries the `[S]` class, which the review defines as "read only
as `git show 0b937dc0…:<path>`", and the file exists at that commit — I checked. The
notation makes the citation unambiguous.

Verdict `PASS`. Both expectations the case states hold, and they hold in agreeing
documents with the machine-readable rule pinned in the identifier catalog.

### MT00-04 — Run/job/attempt walk — **PASS**

**What I did.** I modelled provider timeout → retry → stale worker result against the
three machines in `contracts/domain/v1/state-machines.json`, reading each transition
table, guard and terminal rather than the summary prose, and then asked the two
questions the case states: do Run, Job and Attempt stay unmixed, and is a stale
Attempt denied publication.

**The walk.** A top-level audit command is accepted for a frozen input and
configuration set; `run_id` is created; `audit_run created → queued → running`;
`job queued → leased → running`; Attempt `A1 created → leased → running` holding the
current execution token. The provider times out. Either branch is legal and both are
declared: `A1` reports a retryable class (`dependency_unavailable`, 503, retryable) and
`job running → retry_wait`; or the heartbeat deadline is missed and `A1 → lost` with
the Job releasing the lease in the same transaction. The bounded budget admits a retry:
`job retry_wait → queued → leased`, and creating `A2` and its token supersedes `A1`'s
token in the same transaction, so `A1 → superseded`. `A2` delivers; schema, checksum
and manifest validate; `A2 → succeeded`, `job → succeeded`, `audit_run validating →
published`. `A1`'s late result then arrives.

**Run, Job and Attempt do not mix, and the rule is data rather than prose.**
`identifiers.json` `distinct_identities.execution_identity` states that none
substitutes for another, none is derived from another and none may be reconstructed
from `project_uid`, `version_uid` or a worker task handle. `machines.audit_run.run_creation`
enumerates eight cases and declares itself complete — "Nothing else creates a Run" —
and case 7 is explicit that retry, resume, restart and worker failover create "no new
`run_id` and no new `job_id`; the same Job creates a new `attempt_id`". The three
`retry` blocks agree: AuditRun `in_place: false` creating a new `run_id` only for a new
top-level command; Job `in_place: true` creating a new Attempt; Attempt `in_place:
false` creating a new `attempt_id` under the same `job_id`. The analysis family carries
the same rule as nine machine-readable triggers `RC-01`–`RC-09`, and the one genuine
overlap — same idempotency key and payload on a terminal Run — is resolved by an owner
precedence ruling `RP-01` whose winner and loser are schema `const` pins, so the
reverse priority is unwritable. I checked that the owner record
(`CP00_OWNER_DECISIONS.md` PD-03 precedence clarification) and the contract agree; they
do.

**A stale Attempt cannot publish.** The rule is stated once, normatively:
`publication_authority` — "At most one Attempt per Job may publish at any instant: the
Attempt in `running` that presents the current execution token, checked inside the
publishing transaction", with late delivery "accepted for storage as immutable
evidence, never applied to project state, and answered with `stale_attempt`". Four of
the Attempt machine's five terminals are non-publishing (`failed`, `superseded`,
`lost`, `cancelled`), each carrying the store-only clause. Three independent guard
layers — attempt handler, job scheduler and run command handler — each require current
authority and each name `stale_attempt` on violation. `stale_attempt` is 409,
`retryable: false`, category `stale_authority`, so a stale worker is told not to
re-submit. There is no `running → published` edge on the Run machine; publication is
reachable only through `validating`.

The capability is `execution_token`: opaque, equality-only, refreshed on every new
Attempt, verified inside the guarded write's own transaction, never an entity identity,
secret-class and a forbidden detail key in the error envelope. The contract states
plainly that "Fencing is a property of behavior, not of the value or of the field name"
and promises no monotonic number — which is the honest form, given that the legacy
inventory records connection-epoch fencing and no domain-level fencing field.

**Deferred values are deferred, not invented.** `OQ-02` (lease duration, heartbeat
interval, grace window) and `OQ-04` (retry budget, backoff) are carried as open
questions in the catalogs with named later slots. My own numeric sweep across
`contracts/`, `fixtures/`, `db/` and `infra/` for any numeric binding of ttl,
retention, lease, heartbeat, grace, backoff, retry budget, max attempts or cost limit
returns nothing.

Verdict `PASS`. One naming residue is recorded as F-5; it is escalated in the tree
rather than hidden, and it does not touch the behaviour this case tests.

### MT00-05 — Comparison ownership — **PASS**

**What I did.** I modelled auto suggestion → user-approved sheet link → recompute → AI
review, and checked the two expectations separately: that recompute does not overwrite
an approved link, and that AI does not change raw deterministic evidence.

**Recompute does not overwrite an approved link.** Six independent statements agree,
and I read each in place rather than through a summary: `ADR-0013:6` — "User-approved
links are owned state and survive recomputation"; `ARCHITECTURE_BIBLE.md:215` —
"approved sheet links have explicit owner/revision and survive recomputation";
`DOMAIN_MODEL.md:114` — "Recompute suggestions cannot mutate approved SheetLink";
`GLOSSARY.md:25` — suggestions "cannot overwrite approved links";
`contracts/comparison/v1/README.md:5-6`, which separates "rebuildable automatic
matching suggestions" from "authoritative user-approved `SheetLink` / explicit unlinked
state"; and `ARCHITECTURE_BIBLE.md:52`, which puts the approved link in the canonical
column as "user-owned state/event" and the "latest automatic suggestion" in the
non-canonical column. The disposition is preserve, not flag and not overwrite: no
document offers a conflict or stale state for the approved link under recompute. The
one sanctioned path that may change an approved link is repair, and it is fenced —
"repair proposal/action/undo with proof and audit", with `ARCHITECTURE_BIBLE.md:218`
requiring proof, audit event and a reversible operation.

**AI does not change raw deterministic evidence, and this one is enforced.** The
prohibition is a root rule — `AGENTS.md` §4, tenth prohibition, "изменение raw
deterministic comparison evidence AI-слоем" — restated as principle P-17
("Deterministic/raw evidence не мутируется AI-слоем"), as `ARCHITECTURE_BIBLE.md:217`
("AI review refers to raw artifact checksums and cannot overwrite them"), as
`ADR-0013:6`, and as `GLOSSARY.md:28` ("additive, not authority"). Unlike most of what
this checkpoint freezes, it has a lint rule behind it: `ALR-22`
(`raw-evidence-write-once`, **static**, **error**) makes raw deterministic comparison
evidence write-once for the AI layer, scoped to `src/auditmanager/comparison/**` and
`src/auditmanager/analysis/**`, with the admissible shape named — creating a new
derived artifact that references the source checksum — and the carve-out stated: the
deterministic stage that produces the artifact is its writer and is not an AI module.
`ALR-23` (`ai-artifacts-stay-derived`, review, error) closes the re-publication route.
P-17's disposition in the review is `ratify` and it is described there as the strongest
legacy-supported principle in the package.

**Ownership.** `DOMAIN_MODEL.md:48` makes the Comparison context the authoritative
owner of `Comparison`, `SheetLink`, `SuggestionSet` and `ComparisonRevision`, under
the Bible's single-writer rule "Одна сущность — один authoritative writer". The
execution engine is explicitly denied canonical writes. The final-checklist item "all
key bounded contexts have a data owner" is met for this context.

**Scope caveat, checked and recorded as F-7 rather than treated as a gap.** The
comparison family is a README-only area; `CONTRACT_CATALOG.md` records it as
`not-active` and the README's own first line says it freezes in S06. CP-00 freezes the
conceptual separation, not the schema, so I did not treat the absence of schema files
as a defect. What I did record is that the README's "Freeze in S06" covers five items
of which three — graphic evidence, AI synthesis and repair/undo — are gated at S07 by
the stage plans' own contract gates. I also checked whether listing graphic evidence
breaches PD-04's stop condition and concluded it does not: PD-04 forbids a W0 fixture,
schema, golden journey or contract **asserting graphic comparison behavior**, and the
owner's own record names the Bible, ADR-0013 and the GLOSSARY as target documents that
name the layer, approving it as future scope. Naming the layer is not the stop
condition; asserting its behaviour is, and nothing does.

Verdict `PASS`. Both expectations hold.

### MT00-06 — Unresolved decisions — **PASS**

**What I did.** I reviewed the proposed ADRs and the owner decision records, and then
tested the expectation directly: that retention, tenant, IdP and other unconfirmed
values are explicitly unresolved rather than invented.

**What I observed.** Every open input carries a recorded disposition with a named owner
and, where deferred, a deadline. `CP00_ARCHITECTURE_REVIEW.md` §11 tabulates
`U-01`–`U-06`: `U-01` deferred with a deadline (numeric cost thresholds to `W3-C-01`,
required before the first paid-provider canary); `U-02` resolved; `U-03` assigned to
`W0-ARC-02`; `U-04` **open by explicit owner disposition**, with tenant/IdP required
before `W2-C-01` and TTL/legal hold before `W9-C-01`; `U-05` conditionally accepted;
`U-06` resolved on 2026-09-01 into a separate bounded context under `W5-OPT-01`, with
two machine-readable obligations — the capability stays disabled until that task is
accepted, and CP-00 explicitly excludes its runtime semantics. The section states what
`U-04` blocks, exactly and limitedly: ADR-0014 stays `proposed`; the retention and
legal-hold clauses of ADR-0015 are not ratified; the P-13 classification and retention
obligations are not ratified; and no tenant, IdP, TTL, retention or legal-hold value
enters any contract. ADR-0014 is the single architecture `defer` and its source
retention matrix is recorded as having every value unfilled.

The catalogs carry the same registers as data rather than prose: `open_questions`
holds `OQ-02` (identifiers) and `OQ-04` (state machines); `resolved_questions` retains
`OQ-01`, `OQ-03`, `OQ-05` and `OQ-06` so, in the schema's words, "a closed question
cannot silently reappear as an assumption"; and all three catalogs carry
`open_owner_decisions` with `PD-01`, `PD-03` and `OPEN-RETENTION`. The five owner
decisions `PD-01`–`PD-05` each carry a dated disposition and, where approved with
modification, the modification travels with the decision.

**The discriminating test.** A register of open items is worth nothing if a value was
quietly chosen anyway. I swept `contracts/`, `fixtures/`, `db/` and `infra/` for any
numeric binding of ttl, retention, lease duration, heartbeat interval, grace window,
backoff, retry budget, max attempts, timeout or cost limit. **Nothing.** The lease
block names its own gap rather than filling it — "No numeric value is invented here and
no lease implementation may proceed without that decision" — and the Job retry block
does the same for the budget and backoff.

**One gap I looked for and did not find, recorded as F-8.** No document states what
happens to a `Finding` that is not re-observed on a rerun, or that reappears on a later
one. It is not a silently defaulted value — the finding matcher is an explicit S03
deliverable, `W3-FND-01`, with the guardrail "Uncertain match creates new identity" and
the S03 exit item "Finding UID persists only when matcher policy permits", so the
direction is fail-closed and owned. But the case is not named in the deferred scope
either, and a reader modelling the rerun journey reaches a question the package does
not answer. That is a gap in the unresolved register rather than an invented value, so
it does not meet the bar.

Verdict `PASS`. Nothing is silently defaulted, and the things that are open are open by
decision.

## Final acceptance checklist

- [x] **Нет hidden Strangler runtime dependency.** MT00-02. No import, adapter, proxy
      route or shared store; legacy is read only as immutable Git objects at pinned
      commits, and the source Strangler model is recorded as deliberately not
      transferred. Verified by sweep, not by reading the claim.
- [x] **Все ключевые bounded contexts имеют владельца данных.** `DOMAIN_MODEL.md`
      "Aggregate ownership" assigns every context its authoritative aggregates; the
      Bible's §2 sources-of-truth table names the canonical and non-canonical side for
      each; `CONTRACT_CATALOG.md` names a contract owner per family; and the
      state-machine catalog names an `authoritative_writer` for each of the six
      machines. The execution engine is explicitly denied canonical writes. Checked
      end to end for the Jobs, Findings, Decisions and Comparison contexts in
      MT00-03 to MT00-05.
- [x] **Shared contract freeze/process понятен reviewer без устного пояснения.**
      `VERSIONING_AND_FREEZE_POLICY.md`, `INTEGRATION_POLICY.md` and
      `WAVE_EXECUTION_GUIDE.md` state the freeze and integration process; the W0.3
      wave plan states the gates, roles and stop conditions; the manifest states the
      three-measurement model — what identifies the input, what identifies the evidence
      tree, and what certifies the reviewed families — and each recipe reproduced for
      me from its written form alone, without reading the module that implements it.
      That is the operative test of "understandable without explanation" and it passed.

## Stop/cleanup

**"Stop the local stack using the documented command" cannot be executed as
documented, and I did not substitute my own.** No stack exists: this is an
architecture and behaviour freeze, production implementation is prohibited before
CP-01, `db/migrations` carries only a README, `src/` and `web/` carry only boundary
READMEs, and `backend_runtime`, `frontend_runtime` and `local_infra_versions` are
recorded as not applicable. The step is inapplicable at this checkpoint rather than
skipped, which is the disposition earlier testers reached and which I reached
independently by looking for the stack before looking for the report.

The remaining cleanup obligations are met. All evidence in this report is synthetic or
derived from the repository's own tracked contents and its two pinned legacy commits;
no production payload, screenshot or customer data was read or recorded. No temporary
credential or token was created or used. No fault-injection override was applied —
every perturbation in the probe tables above was computed in memory in a scratch
directory outside the repository, and none was written into the tree. My scratch
scripts live under the session scratchpad and not in the repository.

## Findings that do not block

Each is stated with its site, what I measured, its owning task, and why it does not
meet the narrowed bar.

**F-1 — the three state records say round ten is owed and not frozen; the manifest says
it is frozen.** `artifacts/checkpoints/CP-00/acceptance.md` ("round ten is owed and has
not been frozen", and the round-10 table row "not frozen; the freeze is the step after
the QA ceiling remediation"); `docs/program/CURRENT_STATE.md` ("Round ten is owed and
is not yet frozen", and "the round-ten freeze waits on the new acceptance");
`docs/program/CHECKPOINT_REGISTRY.md` ("round 10 owed and not yet frozen, blocked on
the QA post-freeze ceiling remediation"). The manifest at HEAD carries
`status: acceptance_round_10_frozen`, the round-10 entry `status: frozen`, and the
digest. Single cause, measured: the freeze commit `2ea7b68` changed **only**
`manifest.json`, five lines, and the state reconciliation `21ee92d` that set the other
three records preceded it. Owning task: `W0-INT-01` for the wave plan and task banner,
the integrator for the checkpoint records. **Does not block**: an out-of-date status
line, which the owner's narrowing names explicitly.

**F-2 — the manifest's own note contradicts the field it explains.**
`tested_candidate_digest_note` reads "null because round 10 has not been frozen … the
current round has no input identified yet: freezing is the step after this
reconciliation, not part of it", while `tested_candidate_digest` holds
`00977a87…b3e5`. The freeze commit changed the value and not the note. Owning task:
integrator. **Does not block**: it is a stale explanation of a value, not a
misstatement of the identifier rule. The rule itself — `candidate_digest_recipe` — is
correct and reproduced exactly for me from its written form.

**F-3 — `acceptance.md` describes the state sweep as it behaved before the same commit
changed it, and the sweep's own docstring omits a skip it acquired.** `acceptance.md`
says "it skips nothing by path except the dated primary acceptance reports and itself",
"Its exit code is still non-zero, and deliberately so. It names **nine findings across
three files**", and that the axis-one measurements at `bde3af3`, `a3eaf88` and
`5b70ee4` were "1, 1 and 4 findings"; it also says that "Narrowing the sweep until any
of them fell outside it would have been the round-eight defect committed a third time."
Measured on this tree: the sweep exits **0** with **0** findings on both axes; axis one
at those three commits is **0, 0 and 2**. The cause is visible in the code:
`EVIDENCE_PREFIXES` now contains a third entry, `docs/program/reviews/`, added by the
same commit `21ee92d` that added the paragraph — whose message says so openly ("Review
reports now join the acceptance evidence in the exclusion") and reports the measurement
that justifies it (17 stale sites still found at `4bf2351`, 0 here), which I reproduced
exactly. The module's own bullet three lines above that entry still reads "**Nothing is
skipped by path.** … Every tracked file is swept except the dated primary acceptance
reports … and this file", an enumeration that no longer lists everything it skips,
although the reasoning for the new exclusion is written in a comment beside it. This is
the largest documentation defect I found and I want it recorded at full strength: it is
the same shape — prose asserting a property of a guard that the guard no longer has —
that rounds six, seven and eight died on. Owning task: integrator for `acceptance.md`
and `check_state_records.py`. **Does not block**: it misdescribes the scope of a
checkpoint-mechanism tool. It changes no product semantics, no security property and no
data integrity property, and the guard's exclusion is of review reports only — files
that quote stale claims verbatim beside the records contradicting them, and that no
consumer reads for current state. The four records a consumer does read remain swept
and remain in `MUST_ACCOUNT`.

**F-4 — the QA review report does not record the round that produced the module now in
the tree, and its counts no longer reproduce.**
`docs/program/reviews/W0-QA-01.md` §9 is headed "Commands and their actual results" and
prints `Ran 284` / `Ran 26` / `Ran 310` as transcripts; §12.2 repeats them. The tree
runs **298 / 26 / 324**, measured. Sections run `11.2`–`11.19` for QA rounds two to
thirteen; there is no section for the round that followed. The `W0-QA-01` task banner
and the S00 task map both still say "accepted after twelve review rounds" and name
`3da104e5…` as the evidence commit, while `tests/contract/test_cp00_candidate.py` has
moved 9515 lines and the report 575 lines since that commit, in `49bdcee` and
`1ab8bac`. **On the honesty question this round was asked to judge**: the manifest's
round-10 note does state plainly that "The QA ceiling remediation was rejected by four
independent reviewers with fifteen blockers" and names the two closing commits, so the
rejection is disclosed and not buried — but that one sentence is the only tracked
record of it. It accounts for eight of the fifteen (mechanism `M1`–`M5`, licence
`L1`–`L3`); the disposition of the other seven is recorded nowhere I could find. A
reader who follows the documented route to the review report — the place every other
record sends them for the QA rounds — learns none of it. My assessment: honest in the
manifest, incomplete everywhere the reader is actually sent. Owning task: `W0-QA-01`,
which owns both the report and the module. **Does not block**: stale counts and a
missing round section in a review report change no product semantics, security or data
integrity, and I established the current counts on my own measurement rather than
relying on the record. I note that a concurrent session declared the §9 half of this
item in the manifest during my round (see F-6), reaching the same measurement I did.

**F-5 — ADR-0007's body still names the field the contracts forbid.** `ADR-0007:6`
says each Attempt carries "lease/heartbeat and fencing token", while
`identifiers.json:27` states that `execution_token` is canonical and that
`fencing_token` and `authority_token` are "legacy or cross-lane evidence names only; no
target field, payload key, database column or API parameter defined against this
contract carries them", and `ALR-25` makes the forbidden names a violation. The
conflict is **escalated in the tree, not hidden**: `ARCHITECTURE_LINT_RULES.md`
records it as `E-ARC02-02` with the reasoning "an implementer reading only ADR-0007
would write the forbidden name", routes it to the program integrator, and states that
the lane deliberately touched no ADR file. `ARCHITECTURE_BIBLE.md:184` carries the same
word and is dispositioned in the review; `GLOSSARY.md:14` carries it with no
disposition row I could find. Owning task: the integrator, to route to an ADR-owning
task; `W0-INT-01` at ratification for the GLOSSARY line. **Does not block**: the
behaviour is unambiguous and correctly specified in the contract that governs it, the
divergence is a name in an ADR body, and it is already visible at the rule rather than
concealed in it.

**F-6 — a concurrent session wrote into the frozen candidate while this round was
live.** Measured above in the start record: `artifacts/checkpoints/CP-00/manifest.json`
modified at 16:54:41 +0500 during my walks, adding two `known_pre_ratification_items`
and withdrawing an unverified count from `recorded_limits`. The content is a
correction in the right direction and one of the two entries independently reaches the
measurement I reached in F-4. The governance shape is nevertheless a write into the
tree an acceptance stream is judging, mid-round, by a party other than the stream. Its
consequence is bounded and I measured the bound rather than asserting it: the four
reviewed families are untouched, `artifact_manifest_sha256` is unchanged, the frozen
`tested_candidate_digest` still reproduces exactly from the freeze commit's objects,
and the manifest is a `POST_FREEZE_DELTA_CEILING` path that the mechanism licenses to
move after a freeze. Owning task: the integrator, as freeze governor. **Does not
block**: the whole-tree digest is not a blocking criterion this round by owner
decision, and the semantic freeze — the four reviewed families and their content — did
not move.

**F-7 — the comparison contract README's freeze line covers three items its own stage
plans gate one stage later.** `contracts/comparison/v1/README.md:3` says "Freeze in
S06" and lists five required separations, of which items 3 (graphic evidence), 4 (AI
review/synthesis) and 5 (repair/undo) appear in `S07_comparison_advanced.md`'s contract
gate, not `S06_comparison_core.md`'s. The S06 gate lists comparison identity/revision,
sheet descriptor, suggestion set, approved SheetLink, exclusion artifact, raw text diff
and preview/tile read contract — no graphic, no AI, no repair. Owning task: the CMP
contract owner at S06; recordable by `W0-INT-01`. **Does not block**: the file is a
conceptual area README in a `not-active` family; it asserts no graphic behaviour, so
PD-04's stop condition is not triggered — the owner's own PD-04 record names the Bible,
ADR-0013 and the GLOSSARY as documents that name the layer and approved it as future
scope.

**F-8 — the rerun model does not say what happens to a Finding that is not
re-observed, or that reappears later.** Searched directly across `contracts/`,
`docs/architecture/` and `fixtures/`: nothing addresses it. The `Finding` has no
lifecycle states, and the four `finding_current_verdict` values — `pending`,
`accepted`, `rejected`, `needs_manual_review` — express no "no longer observed"
outcome. The adjacent rules are all present and fail-closed (a rerun never rewrites or
deletes earlier observations; an unjustifiable match allocates a new `finding_uid`),
and the matcher is an owned S03 deliverable `W3-FND-01`. Owning task: `W3-FND-01`, or
the domain contract owner if the case should be named in the deferred scope now.
**Does not block**: it is an unnamed case in a deferred, owned policy, not an invented
value and not a contradiction.

**Observation, not a finding.** `Finding` is bound in `identifiers.json` `entities` but
appears in neither state-machine register. I checked before recording it as a defect
and it is not one: nothing claims the registers are exhaustive, and 16 of the 25 bound
entities are in neither. Recorded so the next reader does not spend the time I did.

**Already-disclosed items I re-encountered and did not re-raise as new.** The manifest's
`known_pre_ratification_items` records the PD-01–PD-04 enumeration omitting PD-05 in
`ARCHITECTURE_BIBLE.md:9`, `contracts/domain/v1/README.md:962`,
`fixtures/golden/SELECTION.md:19` and `ADR_INDEX.md` lines 31 and 41; the
`ARCHITECTURE_LINT_RULES.md:604` GATE-E probe prose; the PD-02 precondition text; and
the integrator edits into an accepted deliverable. I confirmed each is present as
described and each is disclosed with an owner. `E-06` — the Git spawn with an inherited
environment in `scripts/validate_bootstrap.py:116` and
`tests/contract/test_validate_bootstrap.py:32` — is carried as a blocking open
escalation owned by W1, correctly, since `scripts/` is a frozen reviewed family; it is
the one security item in the register and it is neither closed nor hidden.

## Known limitations

1. **This is reading and judgment, not exercise of a running system.** At an
   architecture freeze there is no product to drive, so MT00-03, MT00-04 and MT00-05
   are paper walks against contracts. Where a rule is carried by a schema `const` pin
   or a static lint rule I said so, because that is a stronger guarantee than prose;
   most of what this checkpoint freezes is prose, and prose is what I could check.
2. **An independent agent is the closest available analogue of a human tester, not a
   substitute for one.** I state this for the same reason `acceptance.md` does.
3. **My sweeps are mine.** The link, path, SHA and count sweeps are my own
   implementations; they found one false positive I caught and corrected (the anchor
   slugifier) and they may have blind spots I did not find. Where they returned zero I
   have said what the zero is over.
4. **The working tree moved under me.** Measurements taken after 11:54 were taken
   against a tree carrying a concurrent modification to the manifest, recorded as F-6.
   Every digest claim in this report is stated with the source of its bytes named —
   working tree, HEAD objects, or `reviewed_candidate_commit` objects — precisely so a
   later reader can tell which is which.
5. **I did not re-verify the fifteen blockers.** I established what the tree records
   about the four-reviewer rejection and what it does not (F-4). Whether the eight
   named blockers are genuinely closed is a QA-mechanism question outside these six
   cases, and I did not assess it beyond confirming the suite is green at 324 tests.
6. **The legacy repository was sampled, not exhausted.** I resolved every `[L]` and
   `[S]` anchor I tested and every SHA-shaped token in the tree, but I verified
   `symbol@line` correspondence on a sample rather than on all 293 declared locators.

## Overall verdict

**PASS 6/6.**

| Case | Verdict |
|---|---|
| MT00-01 Documentation navigation | **PASS** |
| MT00-02 Greenfield boundary | **PASS** |
| MT00-03 Identity walk | **PASS** |
| MT00-04 Run/job/attempt walk | **PASS** |
| MT00-05 Comparison ownership | **PASS** |
| MT00-06 Unresolved decisions | **PASS** |

No case is `FAIL` and no case is `BLOCKED`. Eight findings are recorded above; none
meets the bar the owner set for this round, and I have said of each why not rather than
asserting it. No contract, schema, fixture, state-machine, identifier, error-contract,
evidence-anchor or golden defect was found in any of the six walks — the tenth round in
a row to reach that result, and the first in which I checked those axes as the axes
that would block rather than as the axes that happened not to fail.

The semantic freeze holds: the four reviewed families are byte-identical to
`reviewed_candidate_commit` `92e13fa4…`, confirmed three ways, and
`artifact_manifest_sha256` `39721aac…5e08` reproduces from a recipe I implemented
myself and probed six ways for discrimination.

What remains wrong in this repository is, once more, the programme's record of itself
and not the thing it records.
