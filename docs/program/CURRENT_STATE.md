# Current state

> **Updated 2026-09-20 by the integrator, at `e2dc68f`.** `AGENTS.md` §1.1 makes this file
> the first thing every agent reads. It had not been touched since 2026-09-14 and still
> opened with the `P0-PLN-01` planning candidate — **nine waves out of date**. Every session
> dispatched in that window was oriented by its brief instead, which worked and is not the
> arrangement this file describes. The history below is kept; this block is what is true now.

## Where the programme is, 2026-09-22

**`origin/dev` = `b0e5c07`. `origin/main` = `f96c23a`, tagged `alpha-w30` — a gated tip, not
a certification.** `make gate` → `GATE OK`: battery **2193 passed / 5 skipped / 169
subtests**, foundation **35**, frontend **959 in 68 files**.

**The application has authorization.** Wave 34 added `POST /auth/token`, a sign-in screen and
migration `0006_app_user`, and resealed the contract: **12 paths / 15 operations / 46 schemas
→ 13 / 16 / 48**, with the contract, the generated client, the mirror, the migration and
`web/FRONTEND_LOCK.json` moving in one change — the three-document coupling `D-18` named and
the first wave to plan for it rather than discover it.

**Driven on the stand, not inferred:** `GET /bff/v1/projects` without a session answered `200`
**with write access** that morning and answers **`401`** now; zero `Authorization` headers
leave the BFF; a sign-in screen exists. That closes the operative half of `D-49`.

**The interface is Russian and finished enough to show.** Both palettes, a sun/moon theme
control, an icon set under `web/NOTICE`, the thirteen project sections, and a language guard
that renders the screens and fails on one English word a contract did not put there. Read from
`/root/w19-integrator-logs/gate-w29.log` with `EXIT=0` appended by the shell that ran `make`.

**The application is deployed, drivable by hand, and provably the tree.** One alpha stack
answers on `127.0.0.1:31500` — `auditmanager-w19a`, `AUDITMANAGER_PROVIDER_MODE=proxy`,
brought up by `infra/deploy/deploy.sh`. Redeployed from `ac7c348` on 2026-09-21;
`infra/deploy/verify-deployed.sh` exits 0 and prints *"the deployed stack IS this tree"*, file
by file: 141 in `src/`, 9 in `db/`, 34 in `contracts/`, 223 in `web/`, all identical. **The sha
that sentence prints is the repository's working tree at the moment you run it, not a property
of the stack** — this document quoted `(ac7c348)` as though it were fixed, and `W30-CERT3` read
`(2fdb12c)` a few commits later and correctly called the sentence false as stated. The script
is not at fault; it prints the sha *for the record*. **What the script actually certifies is
that the images and the working tree agree, whatever the sha is.** **It is the only stand on this host** — the two abandoned ones were removed on
2026-09-21 under ruling `R-6`, and with them the stale worktrees of sixteen merged waves
(13 GB; every branch kept, `BRANCH_INVENTORY.md` says which).
A browser creates a project, uploads a PDF, starts a run, watches it go `queued → running →
published`, opens a finding at its quotation, records an accept, a reject and a comment, and
downloads the CSV — all through one origin, with **no request carrying a credential**, which
a server-side route holds instead.

### `PA-01`, certified criterion by criterion

**The current record is `artifacts/checkpoints/PA-01/certification-ac7c348.json`**, written
by `W30-CERT3` on 2026-09-21 and superseding `16d3503`'s, which superseded `0f9989a`'s. **Ten
criteria driven to a verdict; eight hold, one of those with a named exception; two cannot be
established; none failed.** Every verdict was re-taken at this tree rather than inherited.
(*This document said "eight criteria" for four waves. The record has ten, and it also led with
the superseded `0f9989a` record. Both corrected 2026-09-21, the first by counting the keys
rather than trusting the sentence, the second because `W30-CERT3` read this file as
`AGENTS.md` §1.1 requires and found it did not survive contact with the tree.*)

| | |
|---|---|
| **criterion 1** | `deploy.sh` now exists and brings the stack up from a clean clone, cold cache, exit 0, served schema conforming with 0 differences. It stays *cannot be established* because **no host here has never run it and there is no previous version to roll back to** — `R-1` alone. |
| **criterion 2** | no TLS: no host name, no certificate, no DNS. `R-1` alone. The second clause — every operation refusing an absent or wrong credential — **is driven and holds.** |

**Re-certified 2026-09-21 at `ac7c348`.** Criterion 10's exception is **gone** — `W24CERT2-2`,
the wipe rehearsal's total counting a view, was repaired by `W26-OPS` **inside the range that
certification covers**, and the sixteen per-table counts now sum to exactly the printed total.
Criterion 8's exception survives, but its **reason was false and is replaced**: it said the
host carries three alpha stacks, and it carries one. The standing reason is structural —
**a certifying session runs on the host it would have to reboot** (`D-51`). Three findings
were recorded rather than repaired: **`D-49`** (the published origin, and the highest-severity
row in the register), `D-50`, `D-51`.

**Previously re-certified 2026-09-20 at `16d3503`** —
`artifacts/checkpoints/PA-01/certification-16d3503.json`. Criterion 4's exception is **gone**: `partial` was driven **in a browser on the deployed
path**, badge `queued → running → partial`. Criterion 5's is **gone**, checked with an
extractor the application does not use. Criterion 10's is **replaced by a smaller one** — the
rehearsal's per-table figures are exact and only its *total* counts a view, which over-reports
and is therefore safe in the direction that matters. Criterion 8's stands: a container restart
is not a host reboot.

### What is open

`DEBT_REGISTER.md` carries the live list with a check command per row. **`D-15`, `D-18` and
`D-35` closed on 2026-09-21** under rulings `R-12`, `R-13` and `R-14`. **One still needs the
owner: `D-9`**, the norms corpus, which `R-9` placed after manual testing. The rest are
`infra/` and `web/src` repairs with no ruling attached.
**`D-49` is open and is the register's highest-severity row**: the stand is published to every
interface and `/bff/v1` serves all fifteen operations, writes included, with no credential.
It needs a decision from the owner about how the stand is reached.

**`D-42`, `D-47` and `D-48` closed 2026-09-21.** `D-42`'s measurement always stood; its open half was
one review document still carrying the false sentence unqualified, and that document now
carries an **erratum** rather than a rewrite. `D-47` is now `OPERATING_CONSTRAINTS.md` §4.
**`D-36` closed 2026-09-20** — the one part of criterion 1's row that `R-1` did not block.
`deploy.sh` run twice now leaves every container ID unchanged, and the row's stated cause
turned out to be wrong: not a `created` timestamp, but BuildKit's **provenance attestation**
on the manifest.

### How work is dispatched

Waves of parallel sessions, each in its own `git worktree` and its own gate lane. The
integrator merges, gates, pushes and tags; **no dispatched session tags or pushes to `main`**
(`AGENTS.md` §5). Reviews land in `docs/program/reviews/`, one per session, and every wave
has a closure under `docs/program/`.

---

## History below this line

> **P0-PLN-01 candidate, revision 4, 2026-09-10.** On branch `agent/p0-pln-01`,
> `P0-PLN-01` has produced the detailed P02–P05 plan:
> `docs/program/PROTOTYPE_EXECUTION_PLAN.md` plus **30 agent-ready task files** — two
> navigation tasks, thirteen P02, eight P03, four P04 and three P05. It is a
> **candidate**: no P02–P05 task is dispatchable until the owner accepts it, and P01 is
> unaffected. The plan changes no contract, runtime, migration or foundation path, records
> 24 unresolved owner decisions, and marks its forecast calibration **pending** until
> measured P01 throughput exists.
>
> Revision 1 restores the fastest-prototype scope: PC-01 has no Job, Attempt, lease,
> fencing token, retry, resume, outbox or revocation UI, and the plan records that it
> therefore publishes no JobPackage or ResultPackage and claims no conformance to those two
> schemas, without editing any contract. It also gives the server-side CSV export a real
> owner, splits the navigation and P02 integration lifecycles so no task ID is reopened in
> two windows, and separates person-effort from calendar duration.
>
> Revision 2 is documentation-only and narrow. It makes the task dependency graph the
> single source of truth — the evidence gate now requires an accepted `P2-AI-01` with no
> synthetic-observation escape, verification follows wiring, and frontend authoring
> overlaps the P02 tail against the frozen API contract while end-to-end evidence waits for
> the accepted backend handoff. It gives every P02–P05 task its own navigation incident
> file and a mandatory incident status, clears the last export-resource wording, and records
> the PC-01 `AuditRun` conformance subset as `OD-24`, naming each unevaluated guard instead
> of implying full coverage. Owner decisions now number 24.
>
> Revision 3 is documentation-only and narrower still: the accepted PC-01 slice, the 30
> task files, the DAG and every estimate are unchanged. It settles the CSV export policy as
> one rule keyed on the contract's own `terminal_semantics.publishes_result` — a
> `published` or `partial` run exports with its state visible, anything that publishes no
> result is refused with the typed `state_transition_not_allowed`, and PC-01 raises
> `partial_result_not_publishable` nowhere. It corrects two frozen bases to the commits
> their own dependency blocks name, makes `OD-24` a dispatch prerequisite of `P2-DOM-01`
> and has `P2-RUN-01` enumerate the whole unevaluated guard subset instead of counting it.
> It records that PC-01 instantiates no `Import` aggregate, table or state machine, since
> ingest is a direct single-PDF upload. It repairs the P04 lifecycle so the pre-session
> preflight and the validation-period ledger are different artifacts with one writer each —
> `P4-OPS-01` builds and gates the tooling and the preflight, `P4-BHV-01` writes immutable
> sessions, and `P4-INT-01` alone produces the ledger after the sessions close. It makes
> navigation aggregation status-aware, so a complete set of reporting statuses over an empty
> incident directory is a measured zero rather than an absent metric, and gives `P5-INT-01`
> the narrow ADR authority its own deliverable requires: the `Status:` line of the new P05
> ADRs named in `P5-ARC-01`'s accepted handoff, and their index rows, and nothing else.
>
> One assumption remains for the owner to rule on, and it is now an explicit dispatch
> prerequisite of `P2-INT-00`: that accepting this plan, `PF-01` and the navigation gate is
> what lifts the production-code hold for the P02 paths, and that completing the CP-00
> supersession remains an independent obligation of that line rather than a P02
> predecessor. **The repository owner ruled it on 2026-09-10: `A1b` and `A5` are released,
> and completing the CP-00 supersession stays an independent obligation of that line.**
>
> **The four CP-00 commits have now been taken.** This planning line forked at `1220523`;
> `main` was merged into it on 2026-09-10, so `artifacts/checkpoints/CP-00/**` here is
> `main`'s record and no longer a stale copy.
> **`artifacts/checkpoints/CP-00/manifest.json` is the authority on checkpoint status, not
> the prose below it:** it reads `ratified: false` over twelve rounds, with round ten
> `void` although both its streams returned `PASS`, round eleven `void`, and round twelve
> `frozen` with neither stream reported.
>
> The CP-00 paragraphs below contradict that manifest — they still say CP-00 is ratified on
> round ten and that round eleven is owed. **That contradiction is inherited from `main`,
> where both readings sit in this same file, and this merge does not resolve it.**
> Reconciling them belongs to `W0-INT-03` and the `W0-*` owners, not to `P0-PLN-01` or to
> this merge, and another session is active on that line. Read the manifest, not the
> paragraphs. Section 9 C-4 of `PROTOTYPE_EXECUTION_PLAN.md` carries the comparison and
> what it does to `OD-14`.
>
> **PC-01 accepted, 2026-09-14.** The first working prototype passes at `6d3c0f3`. A live
> `text_analysis` run through the operated LLM proxy on `anthropic/claude-opus-5` found all
> three seeded issues in the synthetic AR corpus and flagged none of the six near-miss
> controls, with every published quotation verified present on its declared page. Measured
> spend USD 0.1147 against a USD 1.00 ceiling.
>
> Certified by a session that authored none of the slices and repaired none of them: it found
> four defects, all in the integrator's composition adapters, all answering HTTP 500, and
> proved they were the only thing between the tree and acceptance. They were repaired and its
> own suite is the proof.
>
> Two criterion-10 failures are **not inducible** through the twelve operations - a checksum
> mismatch, proved at the storage layer instead, and an ungrounded model item, which is
> unreachable by design and owner-accepted. Both are named in
> `artifacts/checkpoints/PC-01/report.json` rather than left to be discovered.
>
> **What PC-01 does not establish is whether the findings are professionally useful.** That is
> the question P04 asks, and nothing here answers it.
>
> **Prototype-planning overlay, 2026-09-09.** On branch
> `planning/prototype-roadmap`, the repository owner recorded `FF-01 ACCEPTED` without
> qualification and completed `P0-FND-00`. No product or infrastructure implementation
> has yet been dispatched. `P1-INT-00` and `P0-PLN-01` are dispatchable from the
> acceptance commit; provider tasks still wait for accepted `P1-INT-00`, and P02–P05
> remain unapproved. The CP-00 state below is retained as the factual baseline and
> historical record rather than rewritten during this planning change.

**Program state:** CP-00 discovery wave W0.1 accepted; all four W0.2 lanes have
produced candidates, the repository owner has recorded an explicit disposition for
`PD-01`–`PD-05` plus integration decisions `ID-01`–`ID-03`, and every lane has passed
independent review. The accepted W0.2 candidate set is integrated at
`cf7740474b1786163f54d93b013a0d526ef989e0`.

W0.3 is on `integration/W0.3`. All six of its contract and QA tasks are integrated, and
`W0-INT-01` is executed: CP-00 was ratified on acceptance round ten at
`39a3a6430bd97c38cb20bafc793fc9d077d0df8e` and tagged `v0.0.0-architecture`, locally and
unpublished. Both CP-00 acceptance streams returned `PASS` on
2026-09-02, on round three, and that `PASS` is **spent**: `W0-QA-01` was reopened
afterwards and took nine further rounds to accept, and the candidate digest model was
corrected in the same period. Rounds four and five were voided before either stream
reported. Rounds six, seven and eight each ran in full and failed on integrator-owned
state metadata, not on any contract. Round nine was frozen and then voided before
dispatch, because performing `W0-INT-01` would have voided the round authorising it.
Round ten was frozen at `2ea7b68` and returned `PASS` from both streams; that round is now void and acceptance round eleven is open. Nothing is ratified, nothing is tagged in the superseding series: `v0.0.1-architecture` does not exist and no round has been accepted for it. The superseded tag `v0.0.0-architecture` remains published and immutable, and is not this checkpoint's current identity. No earlier result transfers to round eleven.

CP-00 is ratified on acceptance round ten, both streams `PASS`, and tagged
`v0.0.0-architecture` — locally, and not published. **That ratification is bound to the
tree it judged and is being superseded.** On 2026-09-07 the repository owner decided a
formal superseding checkpoint (`docs/program/EXECUTION_PLAN.md` §3.3–§3.4): the recovery
work committed after the ratification lies outside acceptance round ten's post-freeze delta
ceiling, so round ten does not authorise ratifying the current tree. Acceptance round eleven
is owed, `W0-INT-03` performs the superseding ratification, and `v0.0.1-architecture` is the
tag it will carry. The old tag is never moved, re-pointed or deleted. Production
implementation outside the explicitly frozen P01 provider paths remains locked. After
`FF-01 ACCEPTED`, P01 may write only `infra/local/**`, `db/migrations/**`,
`src/auditmanager/shared/db/**` and `src/auditmanager/storage/**` through their named
owners; domain product code remains locked until the detailed P02–P05 plan is accepted
and its dependencies complete. This prototype authority supersedes the former blanket
CP-01 code hold without rewriting the historical checkpoint record.

## Active checkpoint

Target: `CP-00 / v0.0.0-architecture`.

## Active wave

`W0.3 — CP-00 ratification and integration` (six tasks accepted; `W0-INT-01` executed and
CP-00 ratified on round ten; the checkpoint is being superseded and round eleven is owed).
See `docs/program/waves/W0.3_ratification_integration.md`.

Stage one integrated:

- `W0-QA-03` — validator reads the canonical `contract_version` key, commit
  `23dddf99f833d12cd4cc22d11e224d4b278872bf`;
- `W0-ARC-02` — 33 architecture lint rules specified, independently accepted after
  narrow remediation, commit `a67ba31e7748c02974ae9ae93c7f30b6f141d417`.

Stage two progress:

- `W0-DOM-02` — deprecated domain `version`/`deprecated_fields` mirror removed,
  domain candidate revision advanced coherently to 5, independently accepted and
  integrated at `478d32e90d1cbb2c691e0ac0b61b68dadcf0d397`;
- `W0-EVT-01` — event envelope on `contract_version`, integrated at
  `3ca8e25413426ff8efec41cd850c325331d181fc`. `ID-01` is complete across every contract
  family: the recursive sweep finds no bare `version` or `schema_version` declaration
  anywhere under `contracts/**`;
- `W0-CLN-01` — notes overtaken by the `ID-01` chain retired, integrated at
  `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`;
- `W0-QA-01` — independent cross-family verification, 255 module tests after eleven
  reopenings, accepted by two independent reviewers on the same bytes, evidence at
  `3da104e5d6fafb2a581bda377a07911183af803f`. Reopened again after round nine was
  voided: the post-freeze delta ceiling had to be aligned with `W0-INT-01`'s actual
  deliverables. That remediation was independently accepted and integrated;
  `3da104e5d6fafb2a581bda377a07911183af803f` remains the accepted evidence commit, and
  round ten was frozen at `2ea7b68b4c4455b03ed4f8437d12f5f35f56af58` on the remediated
  tree. `W0-QA-04` then delivered the final-state contour,
  `tests/checkpoint/cp00_final_state.py`, integrated at
  `6135f17fb76758dc1ab3a7c1195f5421814ba2fb`; it is the gate that replaced
  `artifacts/checkpoints/CP-00/check_state_records.py`.

## CP-00 candidate

Three commits, deliberately distinct:

- `reviewed_candidate_commit` `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` — the
  contracts `W0-QA-01` certified;
- `qa_evidence_commit` `3da104e5d6fafb2a581bda377a07911183af803f` — where its test and
  report live; it certifies nothing by itself;
- the manual candidate — **identified by content, not by commit name.** A commit
  cannot record its own SHA, and two rebuilds were rejected for promising one anyway.

Three measurements with three different jobs, which earlier rebuilds conflated:

- `tested_candidate_digest` **identifies the input** the acceptance streams judge. It
  is frozen before they are dispatched and never edited afterwards; if it must change,
  the round is void and a new one opens.
- `evidence_bundle_digest` **identifies the tree carrying the results**, and is
  computed after they are written. It necessarily differs from the tested digest,
  because writing `PASS` into a tree changes it. Its recipe blanks only the field being
  computed, so it depends on `tested_candidate_digest` — that dependency is what stops
  evidence from one tree being presented as another's acceptance. An earlier recipe
  blanked both fields and so provided no such binding while the prose claimed one.
- `artifact_manifest_sha256` **certifies** the four reviewed families, and it is identical
  across every rebuild that leaves them alone, which is what carries the `W0-QA-01` `ACCEPT`
  forward and is also why it cannot identify anything. **It is only meaningful with a commit
  beside it.** The same recipe over three trees of this repository gives three values:
  `39721aac…` at the reviewed candidate `92e13fa4`, `f362647c…` at the tagged commit
  `39a3a643`, and `a7857228…` over the recovery tree. The bundle carried the first two under
  swapped labels for ten rounds; see `artifacts/checkpoints/CP-00/erratum.md`, E-1.

Completed inputs:

- `W0-QA-00` — fail-closed bootstrap validator, commit
  `c25ff4a5393595260384aaffea1fddc2382189e8`;
- `W0-BHV-01` — accepted legacy capability inventory, commit
  `667fb00fe3e45d1ce0bce7860725c1654b4cdeba`;
- `W0-DEP-01` — hash-locked bootstrap-validation dependencies, commit
  `ab1cfdab0ec5c413b188a44ff82a99586ecd7994`;
- `W0-EVD-01` — mechanically resolvable immutable evidence anchors, commit
  `134436502b7ee40ca9abb061e0080741a863ffda`;
- `W0-QA-02` — Git-aware validator hardening and real-schema regressions, commit
  `6c82004b35f49463c8e7fc8602fbced2f374167e`;
- canonical behavioral oracle — `32b9d903792b30506048a1d42b0e6b2d07aee403`;
- refactoring architecture source — `0b937dc0e24d38fb98485a920152b83d2f19c982`.

Lane candidates produced, independently accepted and integrated at
`cf7740474b1786163f54d93b013a0d526ef989e0`:

- `W0-BHV-02` — five golden journeys, 95 assertions (92 inventory-mapped plus 3 under
  `TSA-01`), `inventory_assertion_coverage` mapping all eleven inventory candidates to
  concrete assertion IDs. The count is declared once, in
  `fixtures/golden/selection.json` → `assertion_invariants`, with a revision history;
  quote it from there rather than restating it;
- `W0-ARC-01` — CP-00 architecture review, owner decisions recorded
  (`review_status = owner_decisions_recorded`, `ratified = false`);
- `W0-DOM-01` — domain `1.0.0-draft.1`. The candidate revision advances every
  remediation round and is deliberately not restated here; read it from
  `contracts/domain/v1/*.json` → `candidate_revision`, where the three catalogs and
  their schema `const` pins hold it as one value;
- `W0-ANA-01` — analysis `1.0.0-draft.1` with a name-level legacy alias map.

See `docs/program/waves/W0.2_architecture_domain_contract.md`.

## Owner decisions of record

Recorded 2026-09-01 by the repository owner in
`docs/architecture/CP00_OWNER_DECISIONS.md`:

- `PD-01` approved with modification — expert decisions are append-only; revocation
  moves the projection to `pending` and restores no earlier verdict. Closes `OQ-03`.
- `PD-02` approved with modification — one authoritative stage registry, conditional
  on a name-level alias map.
- `PD-03` approved with modification — `AuditRun`, `Job` and `Attempt` are distinct,
  with an explicit Run-creation rule; retry/resume/restart/failover create a new
  Attempt, never a new Run.
- `PD-04` approved — graphic/vector comparison is future scope, first contractual
  inclusion in W7.
- `ID-01` canonical machine-contract version key is `contract_version`.
- `ID-02` canonical token name is `execution_token`.
- `ID-03` the 25/2/3/1 declaration distribution was conditionally accepted; its
  condition is satisfied by the independent ANA review of all nine registry stages,
  all 31 alias-bearing sites and all 293 immutable evidence locators.
- `PD-05` approved — `optimization`, `optimization_critic`, `optimization_corrector`
  and `optimization_review` form a separate project-optimization sub-pipeline whose
  product is improvement proposals, not audit findings; section optimization is a
  downstream aggregation/replication pipeline, not the same one. The four names leave
  the nine-stage core registry. The capability is not orphaned: `U-06` assigned it to
  a separate Project Optimization bounded context — see the open-items section. The
  identifier `PD-05` was assigned by the analysis lane and confirmed by the program
  integrator on 2026-09-01; no renumbering is required.
- `PD-03` precedence, confirmed 2026-09-01 — the same idempotency key with the same
  payload always returns the original Run; a repeat of a terminal Run creates a new
  Run only under a new idempotency key. This resolves the overlap between the two
  rules without changing either, and both consuming families must reflect it.

- `U-06` resolved 2026-09-01 — Project Optimization is a separate bounded context
  under `contracts/optimization/v1/**`, owned by a dedicated OPT contract owner who is
  neither the ANA nor the DOM lane, planned as `W5-OPT-01` after the core audit and
  decision-contract freeze. Two binding obligations hold until that task is accepted:
  the capability stays disabled and no lane may model it, and CP-00 explicitly
  excludes its runtime semantics. `FS-04` is split three ways with a named owner for
  each part, so no part is left without an encoder.

## Independent review of record

| Pass | `W0-ARC-01` | `W0-DOM-01` | `W0-BHV-02` | `W0-ANA-01` |
|---|---|---|---|---|
| 1 | accept (candidate) | accept (candidate) | reject | reject |
| 2 | accept | accept | reject — 4 blockers | reject — 2 blockers |
| 3 | accept | reject — 1 blocker | reject — 1 blocker | reject — 3 blockers |
| 4 | **accept** | **accept** | **accept** | reject — 1 blocker |
| 5 | not re-run | not re-run | not re-run | **accept** |

Every blocker raised in passes 1–3 has been remediated. Pass 4 accepted three lanes
and raised one new machine blocker in `W0-ANA-01`: the schema pinned the full
outcome tuple of the nine run-lifecycle triggers but never pinned `rule_id` itself, so
`RC-02` and `RC-05` could be renamed, swapped or duplicated while
`trigger_precedence` kept naming them — a swap would have inverted the precedence
silently and left the contract valid. Pass 5 independently accepted the narrow ANA
remediation: the owning schema now rejects renaming either rule, swapping or
duplicating them, and rotating all nine `rule_id` values. The reviewer re-executed the
documented Gates A–D and confirmed the intended split between schema-level identity
checks and cross-artifact gates. The other three lanes were deliberately not re-run.

Alongside the lane work, three task-layer rounds corrected defects in the follow-up
task specifications themselves — an impossible ADR-supersede slot, a gate that
depended on the ambient interpreter lacking `jsonschema`, a repository sweep blind to
schema-declared keys, and a contradiction over `candidate_revision`.

Two verification lessons are worth carrying into later waves. A mutation probe proves
only what it mutates: the outcome tuple looked protected for a full round while
`creates_attempt` and then `rule_id` stayed unpinned underneath it. And a gate that
cannot be copied and executed as written proves nothing — one lane's Gate D died on
shell expansion of `$defs` inside `python -c "…"`, so its earlier reported passes
could not have been produced by the documented command.

No lane is accepted on the strength of its own remediation, and the integrator does
not review lanes it coordinated.

## Open before any freeze

- `U-04` — tenant/IdP boundary required before `W2-C-01`; TTL and legal hold before
  `W9-C-01`. Keeps `ADR-0014` at `proposed` and blocks every retention value.
- `OQ-02` lease/heartbeat/grace values; `OQ-04` retry budget and backoff.
- Several identity holes that predated the final ANA blocker were closed in the same
  round, but at the **gate** layer rather than the schema layer —
  swapping two `stage_id`s, renaming `XS-02`, swapping `XS-02` with `XS-03`. Verified:
  the schema accepts all three, Gate C rejects all three. Gate-layer defence is
  equivalent to schema-layer defence only while the gate runs as documented, which is
  why a gate that cannot be copied and executed is worth treating as absent.
- One residue is documented rather than closed: re-pointing a legacy stage name from
  one existing registry stage to another passes every check, because the reference
  resolves and the target's identity is pinned. That is mapping judgment, not
  referential integrity, and catching it would mean restating all 62 name-resolution
  decisions (29 canonical-stage mappings and 33 exclusions) inside the gate. The
  complete map is therefore part of the candidate contract set and any later remap is
  a semantic freeze-break requiring independent review.
- `GJ-02-EO-13` rests on an unfrozen candidate: `finding_merge.status_policy
  .skip_allowed` in the analysis registry. No owner decision exists on merge
  skippability, so the expectation carries no `owner_decision_ref`. If the analysis
  lane changes that field, the expectation is re-derived, never defended.
- A legacy defect is now recorded as observed fact and must not drift into a target
  rule: the export download guard compares resolved paths with `str.startswith` and
  no component boundary, so a sibling directory sharing the base prefix is served.
- (closed) The `ID-01` chain completed as `W0-QA-03` → `W0-DOM-02` → `W0-EVT-01`, and
  `W0-CLN-01` retired
  the two point-in-time ALR-24 records and the false committed-state clause retained
  inside two historical domain `revision_note` strings before `W0-QA-01` or freeze.

## Allowed work before CP-00

- read-only legacy inventory;
- domain glossary/capability inventory;
- synthetic/anonymized fixture extraction;
- contract drafts/examples;
- Architecture Bible/ADR review;
- spikes that do not create irreversible production dependency.

## Prohibited before CP-00

- domain production implementation based on unresolved identity/state contracts;
- importing legacy services as new architecture;
- selecting irreversible vendor/retention/security policy without owner decision.

## Next integration tasks

Ten acceptance rounds are now in the record. Rounds one and two failed; round three
passed and is **spent**; round four was voided before dispatch; round five was frozen at
`5207fb55`, dispatched, and voided before either stream reported; rounds six, seven and
eight each ran in full and failed — six on automated `PASS` with manual `FAIL` 5/6, seven
and eight on both streams — every time on integrator-owned state metadata; round nine was
frozen at `ec63e75` and voided at `4bf2351` before either stream was dispatched. Round
ten was frozen at `2ea7b68`, returned `PASS` from both streams, and CP-00 is ratified
on it.

Round nine was voided because the checkpoint mechanism had no executable final state.
`W0-INT-01`'s own required deliverables — the eight-file evidence bundle under
`artifacts/checkpoints/CP-00/`, the reconciliation of the W0.3 plan, the S00 checklist
and `docs/INDEX.md`, and the status banners of the seventeen completed task files — were
not licensed by the QA suite's post-freeze delta ceiling, so performing the ratification
would have voided the round that authorised it. That is a defect in the checkpoint
procedure, not in any contract, and the repair is owned by the QA suite.

Every blocker across all ten rounds sat in integrator-owned metadata, gate text, state
documents or the QA suite. None was a contract, fixture, schema or semantic defect: three of
the four reviewed families — `contracts/`, `fixtures/` and `scripts/` — have stayed
byte-identical to `reviewed_candidate_commit` throughout, the fourth moved only inside the
five files ratification declares, and the contract-level `ACCEPT` still holds. What repeatedly failed is the
checkpoint *procedure*, in the same shape each time, one layer deeper:
first a ratification could be declared with fewer paths than required, then declared in
full and not performed, then performed as a byte change that did not do the
reconciliation, then the programme's record of its own rounds went stale twice over, and
then the ratification turned out to have no licensed way to be performed at all.

**The paragraph that stood here was corrupted by a regex replacement at a previous
closeout.** It read "… the local PostgreSQL and S3 conventions.3 wave plan, the `W0-INT-01`
status banner, and the six dated rows …": the tail of a sentence about the S01 stage branch
spliced onto the middle of a sentence about the state records still owed before a freeze.
Both halves are restored below, each as its own statement, and the second is brought up to
date.

**Order from here.** `W0-INT-02` reconciles the live records and issues the checkpoint
erratum; the integrator freezes acceptance round eleven on the reconciled tree and dispatches
both streams, each producing a primary report file under
`artifacts/checkpoints/CP-00/`; and only on two `PASS` does `W0-INT-03` perform the
superseding ratification and cut `v0.0.1-architecture`. Publication is a separate, explicitly
authorised step after that. S01 follows: cut the stage branch from the superseding tag and
open `W1-INT-00`, which freezes the toolchain, the root command surface, the foundation
OpenAPI health/error contract and the local PostgreSQL and S3 conventions.

**What was owed before the round-ten freeze, and what is owed now.** The W0.3 wave plan at
two lines and the `W0-INT-01` status banner were corrected before that freeze. The six dated
rows in `docs/program/reviews/W0-QA-01.md` §11.19.8 that the sweep reads as live claims are
not owed to anybody in this graph: they are a dated historical measurement inside an accepted
and closed task's deliverable, and correcting them by edit would destroy the evidence. They
are corrected by erratum — `artifacts/checkpoints/CP-00/erratum.md`, E-8 — and owned by W1.

`artifacts/checkpoints/CP-00/check_state_records.py` was the runnable completeness check for
the two axes this record failed on — a superseded evidence commit presented as current, and
stale round accounting. **It is no longer a gate of this checkpoint**, and the checkpoint
manifest says so: it has no model of a ratified checkpoint, so it reads one as a defect and
tells the reader to open a round the mechanism module refuses to let anyone open. Measured on
this tree, `.venv/bootstrap/bin/python artifacts/checkpoints/CP-00/check_state_records.py`
exits 1 with axis one 0 and axis two 16 naming nine files — and 19 naming ten files once
`artifacts/checkpoints/CP-00/erratum.md` is tracked, which the integration commit does, since
the sweep enumerates with `git ls-files`. Those two figures are of the base tree `6135f17`
with this task's paths applied. On the integration tip `06be04e` with the same paths the same
command gives 17 naming ten files and 20 naming eleven files, the difference being
one path this task may not write. Four observations of two trees, not the claim: **axis one is
0, and every axis-two finding falls into one of four named classes.** Each site, by path and by
a stable anchor, is in `artifacts/checkpoints/CP-00/erratum.md`, E-12, which also records that
the figures this sentence carried in an earlier form — 16 across *eight* files, becoming *17* —
were wrong, and why a total is the wrong thing for a record to assert about a sweep that reads
the record asserting it. Run it as a diagnostic.

**What that invariant does not establish, and what in this document a reader must therefore
check by reading.** It was previously stated with a fourth clause, "none of which is a stale
record", and that clause is withdrawn: the classification cannot show a record is current,
because one of its four classes is *defined* as a record the checker cannot read. The two
sentences in this file that state the round this recovery owes — the paragraph beginning "That
ratification is bound to the tree it judged" and the **Active wave** entry — are in that class.
Rewriting them to name the wrong round leaves the sweep's finding list byte-identical and both
suites **unchanged** — not green: on the integration tree `discover -s tests/contract` is
`Ran 343 tests`, `FAILED (failures=4)`, exit 1 *before* any perturbation, so no perturbation
can leave it green, and "unchanged" is the word the sibling records use. Measured, in
`artifacts/checkpoints/CP-00/erratum.md`, `E-13`. Their truth rests on a reader checking them
against `manifest.json`'s `supersession` object, not on any gate of this checkpoint. A checker
that can read a claim carrying the word *superseding* as live rather than as dated history is
owned by W1.

The gate that replaced it is `tests/checkpoint/cp00_final_state.py`, delivered by `W0-QA-04`
and integrated at `6135f17fb76758dc1ab3a7c1195f5421814ba2fb`. It distinguishes an open round,
a closed accepted round and a terminal ratified checkpoint, and it names an owner for every
finding it reports. On this tree it reports four findings: three against the integrity of the
`v0.0.0-architecture` tag, which only a superseding checkpoint can close and which
`W0-INT-03` owns, and one that closes when the integrator commits
`artifacts/checkpoints/CP-00/erratum.md`.
