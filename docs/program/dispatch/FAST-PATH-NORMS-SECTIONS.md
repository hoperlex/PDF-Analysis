# Fast path: normative corpus on the stand, then section implementation

**Status:** planning proposal, 2026-10-08. It accelerates preparation and
offline corpus promotion; it does not freeze a wave or authorize a production
write. Observed local `origin/dev` `3fcdb3e` has W52 Stage C2 grants, not
W52 close. Remeasure refs, contracts, migration head and host state at each
authorized freeze. The production import is `W55A-STAND-IMPORT-01` (P4, §4); the first four
non-АР profiles remain a W59 development exit. First beta at W63 is part of the unadopted
2026-10-08 layer (K-4).

*Amended 2026-10-12 (`plan/corpus-chain`, `reviews/W54-W57-CHAIN-REVIEW.md`; owner answers
`ROADMAP-TO-BETA.md` §10.16 K-1…K-12).* The corpus reaches the stand in four separately
instructed acts, P1–P4 below; the production import is `W55A-STAND-IMPORT-01` (P4), not
`W55A-INT-MAIN-01`, which publishes code only. W53's backup no longer exists as an input
(`R-77`): a one-off copy (K-1) precedes the import and every `origin/main` publication that
applies migrations on the stand (K-6). The rest of this proposal is unchanged and unreviewed.

## 1. The outcome and the two critical chains

**Corpus resident and usable on the production stand (W55a):** the verified
repaired snapshot, complete BGE build, PDF/crop custody, text search with
source citations, current-snapshot selection, ranged PDF opening and a new
run pinned to that snapshot all pass on one deployed SHA. Merely copying a
bundle or loading rows without a complete build is an intermediate state,
not this outcome.

```text
W53 + W53-CLOSE on origin/dev (durable dispatch; custody design R-76; backup deferred, R-77)
  → P1: done with W53's v0.4.0 publication (MinIO recreated, R-83; copy waived, K-12);
        its client-object read-back moves to P2 (`verify-objects`)
  → W54 SEAL → CUSTODY → REPAIR → SNAPSHOT → EMBED → BUNDLE; STAND-COPY, TRANSPORT verbs
  → real promotion: local journal (K-11) → paid repair (≤ $10, stop above, K-8)
                  → repaired snapshot → complete, resumable BGE build → verified bundle
  → P2: W54-INT-MAIN-01 (0018/0019, no corpus bytes) after a one-off copy (K-6)
  → W55a SEAL/SEARCH/PIN/CONTENT/WEB + rehearsal + exact-SHA gate
  → P3: W55A-INT-MAIN-01 (code + 0020, no corpus bytes) after a one-off copy (K-6)
  → P4: W55A-STAND-IMPORT-01 — capacity probe → one-off copy pulled and test-restored (K-1)
        → maintenance window (K-5) → transfer/import → `report` reconciled with the manifest
        → administrator selects current snapshot → live search/PDF/pinned run
  (release history: R-86 — 0.4.0 released with W53; 0.3.0 kept as its own row)
```

W54's BGE image and inbound transport can be prepared beside its SEAL once
their exact grants are disjoint. W54's worker service, worker UI and vision
probe are not input bytes for the bundle; they still have their own W54
acceptance, and a normal W54 release cannot omit a claim that its note makes.
The current W55a release also includes search, pinning and UI; a corpus-only
production import before them is **not** an existing task grant.

**Measured resource gate, 2026-10-08:** the workspace host initially had
1.1 GiB free on its 119 GB filesystem and 5.0 GiB available RAM, below
W54's heavy-step preconditions. `HOST-CAPACITY-CACHE-01` removed only
ignored caches from inactive W48–W51 worktrees; the next measurement showed
15 GiB free and ≈ 6.0 GiB available RAM. The disk floor still has to cover
the bundle ≈ 5 GB, BGE image ≈ 3 GB plus cache, promotion DB 2–3 GB,
rehearsal stand and the one-off copy (K-1) **at the same time**; the RAM reading is near
the ≥ 6 GiB floor and may move. Neither measurement authorizes a heavy step.
The operator reserves space for concurrent artifacts plus the one-off copy and records
fresh `df`/`free` proof immediately before each one. If RAM falls below
6 GiB, reschedule or increase capacity; swap does not satisfy that floor.

**Sections (W59–W63; unadopted 2026-10-08 route, K-4):** W55a makes norms available; W57a/W57b supply the
reviewed normative analysis path; W56b completes the АР stages/presets; W58
measures that АР baseline. W59 then seals the 15-code framework and implements
АИ, ПЗ, ПОС, ТХ; W60 adds КЖ, КМ, ОВ, ВК, ПТ; W61 independently checks the
ten-profile baseline; W62 adds ЭОМ, СС, ИТП, ГП, ПБ and П/Р comparison;
W63 completes the planned menu/optimization functions and judges beta.1.
W59–W62 are development-only on the current route. A profile source file or
synthetic fixture prepared early is not an accepted section route.

## 2. Start-now work with no unfinished implementation dependency

These are bounded preparation results, not execution grants. The integrator
may create exact task files under `TASK_TEMPLATE.md` with `depends_on: []`
only for work that reads existing artifacts or produces isolated private
evidence. No task below writes a frozen contract, migration, runtime route,
root lock, shared navigation or production data.

| Preparation | Owner/result before dispatch | Effect on the critical path |
| --- | --- | --- |
| Host capacity now | `HOST-CAPACITY-CACHE-01` reclaimed ignored inactive W48–W51 caches; the resource operator measures the **simultaneous** bundle, image/cache, promotion DB, rehearsal and one-off copy floor against the new 15 GiB free, then expands or frees more if needed. Record fresh `df -h` and `free -h` before each W54 heavy step. Reserve one ≈ 14 h idle night window for the complete BGE build, plus another if W55a carryover is needed. | Removes the measured disk emergency while preserving the per-step disk and ≥ 6 GiB available-RAM stop. |
| One-off copy readiness (K-1, K-6; replaces "W53 recovery readiness", withdrawn by `R-77`) | The owner installs the W54 copy key (`W54-STAND-COPY-01`'s verbs) and agrees the maintenance window (K-5). Before every `origin/main` publication that migrates the stand and before P4, the integrator pulls the quiesced dump and the S3 inventory here and test-restores the dump on a disposable stand; the attested record gates the publication or the importer. W54's own P2 bootstrap is resolved in `W54-PLAN.md`. The full backup system stays in the beta wave. | Prevents an unprotected forward-only migration or import without waiting for the beta backup wave. |
| W54 paid-promotion recovery | The paid-call journal is a local fsynced file on this machine (K-11); no off-host mirror. Every paid intent is written before dispatch and an `outcome_unknown` call is never re-paid. A sample projecting above $10 stops for the owner (K-8). | Opens the priced three-page sample and 121-page repair as soon as code is accepted. |
| Live provider and probe | The W54 operator confirms the existing live proxy endpoint/credential outside Git, the chosen repair model's rate card and observed price/refusal behavior. Run the bounded image-input/vision probe in its own approved slot. If the proxy is unreachable or refuses image parts, **both** paid repair and the vision probe stop because repair sends images too. Once repair image transport and its negative/refusal case pass, a missing AR vision-quality verdict can defer W55b/W56b without blocking corpus bytes. | Prevents a finished journal from waiting for the first usable provider call and keeps the distinct AR quality decision outside the corpus-import dependency. |
| BGE and transport | W54 BGE owner pins the model/revision and image inputs; transport owner prepares the forced-command inbound channel and a dry transfer with non-client test bytes. The owner/operator arranges the production inbound key privately before W55a release. | Avoids a model download or key installation after the repaired snapshot is ready. No model or key is placed in Git. |
| Release succession | `R-86` (superseding K-9's wording): 0.4.0 is released with W53 and 0.3.0 stays its own history row; later releases follow in order from it, and release notes resume. Integrators still inventory actual main SHAs, served versions and tags; deferred D-137–D-140 checks bind to the affected exact candidate. | Avoids a late stop at W55a `VERSION`/note or a fabricated v0.3–v0.5 release. |
| Audience and source rights | W55a owner names the internal corpus audience, licences/exposure decision and account set before first searchable/PDF publication; owner settles A-7's W55 versus W56b settings placement before W55a freeze. | Prevents a late menu or access ruling from blocking the import release. |
| Section evidence | W59 profile/data owner records hashes and licence of legacy AI/PS/POS/TX, KJ/KM/OV/VK/PT and EOM/SS/ITP/GP sources; PB gets a named expert author. For each new profile obtain a named reviewer, independent positive/negative field set, category/modality/stage denominators, norms availability and approved private storage. | Moves source and evaluation preparation outside the W59–W62 serial contract/runtime windows. Synthetic controls never substitute for field quality. |
| Section identity | W59 architecture owner prepares one reviewable decision on opaque project/section set and version membership, confirmed document sections, П/Р granularity, current-head semantics and ACL. It must explain W59 version comparison, W62 П/Р and W63 Form 7 using the same identities. | Prevents a late incompatible seal; no contract is edited before the authorized W59 SEAL. |

The section evidence lane may run while W53–W58 implementation proceeds.
It writes only freeze-named review/fixture inventories with permission and
no real project bytes in Git. If the owner later authorizes an early profile
candidate lane, it gets disjoint per-profile directories, a measured public
profile schema, no registry/route change, and a W59 rebase/acceptance step;
it cannot count as a W59 section implementation result by itself.

## 3. W54 schedule option to remove avoidable idle time

The default W54 order puts `BUNDLE` and the real promotion operator steps
after WORKER and WORKERS-WEB, and starts the complete BGE build only at
`W54-INT-CLOSE`. *Withdrawn 2026-10-12: W54 revision 4's fix round dropped its §5.1 corpus-first option; this section is history.* `W54-PLAN.md` §5.1 specified a **conditional corpus-first
internal order**; it becomes executable only if `W54-FREEZE-01` selects it,
creates the exact grants and changes the dependency graph:

1. Keep Stage A SEAL, BGE-IMAGE and TRANSPORT grants and the serial
   CUSTODY → REPAIR → SNAPSHOT → EMBED implementation chain.
2. Run `W54-BUNDLE-01` immediately after EMBED's accepted public-port handoff,
   with the sole `norms/public` writer; order runbook ownership TRANSPORT →
   BUNDLE → WORKER with rebases. Split corpus and worker rehearsals into
   disjoint grants and acceptance. A bundle built before the worker UI must
   not claim worker exit.
3. On that corpus candidate, repeat the focused checks and the full gate
   required by `R-70`; have independent custody/lineage judges accept it.
   Only then may a distinct, exactly granted `W54-CORPUS-OPERATE-01` perform
   the promotion DB load, journaled paid repairs (local file, K-11), snapshot load, complete
   BGE build and verified bundle export under W54's existing budget and
   custody rules. Freeze the gated corpus-candidate SHA and the manifest,
   content-key, row, chunk and build digests. Its operator writes and private
   evidence remain outside the release tree. Later migration,
   custody/repair or promotion-script semantics, loader,
   segmentation/chunking, BGE model/image/pin/tokenizer, embedder, manifest,
   public-port or bundle changes invalidate earlier corpus checks and judges:
   repeat them and the affected real build, then re-export/reverify against
   the final W54 tree before W55a accepts it. An inbound transport change
   repeats the final transfer rehearsal and security judge.
4. Worker service/UI editing and light checks may continue under disjoint
   grants; their memory-heavy builds/tests do not overlap BGE, promotion,
   repair or bundle operations on this host. G-1 directs the complete build
   here in a night window and a verified bundle with that build; reserve the
   window as soon as EMBED is
   accepted. If resources prevent W54's build, W55a's explicit carryover
   needs a fresh night window and a re-export/recheck before import. Final W54
   QA, gate, release note and any main publication still cover all claims.

This is a conditional schedule amendment, not permission to run paid repairs
on an unaccepted candidate. If moving BUNDLE or the operator run violates
an actual path/contract dependency measured at freeze, retain W54's serial
order and record the measured blocker. A separate production corpus-only
release is a different change and needs a full release/version replan; this
schedule option keeps the existing W55a production import boundary.

## 4. W55a production boundary

*Rewritten 2026-10-12 (`plan/corpus-chain`); `W55-PLAN.md` revision 5 §A7 is normative and prevails over this summary.*

**P3 — `W55A-INT-MAIN-01` publishes code only.** Its preconditions:

- P1 and P2 verified on the stand;
- the W55a candidate's exact-SHA full `make gate` with literal `GATE OK`;
- a one-off copy taken for this migrating publication (`0020`, K-6);
- the release succession of `R-86`;
- a separate direct owner instruction naming that SHA.

It writes no corpus bytes. Its release notes must be true at P3; the tag follows P4.

**P4 — `W55A-STAND-IMPORT-01` is the production import.** It is a separate act. A direct owner
instruction names the bundle's content key and digest. The executor is this host's integrator,
working only through W54's forced-command verbs; there is no interactive stand shell. The
owner's acts are installing the keys, naming the administrator account for designation, and
ordering any database restore; the integrator runs the `capacity` verb.

Its preconditions:

- W54's read-only `capacity` verb, run by the integrator, within the rehearsal's thresholds;
- an agreed maintenance window of several hours (K-5), with no `origin/main` push during it;
- the one-off copy (K-1) pulled here, test-restored and attested;
- the accepted W54 bundle, with unchanged opaque ids and every PDF and crop digest, and a
  complete BGE build;
- read access limited to experts and administrators (`R-80`).

The steps:

1. `receive` and `status` (transfer, before the quiesce).
2. `dump-db` → `inventory-s3` → `fetch` → test restore here → `attest … import`.
3. `import`. The importer refuses to run without the attested copy record.
4. `report`, which must reconcile counts, row digest and build digest with the manifest and
   the copy.
5. `resume`.
6. An administrator selects the current snapshot.
7. `verify-objects` and the live checks: search, a citation's PDF opening, and a newly pinned
   run, all on the same deployed tree.

**Failure.** A failed import or digest check leaves the snapshot inactive, and a never-current
snapshot is never searchable. The database is recovered from the one-off copy, as an owner
act. Corpus objects stay unbound. Migrations are forward-only.

## 5. Dispatch order and stop conditions

| Earliest point | Dispatchable result |
| --- | --- |
| Now, while W52 Stage C2 finishes | Resolve the measured host disk/RAM stop; prepare the one-off copy key and maintenance window (K-1, K-5), the local repair journal (K-11), BGE pin/transfer plan, inbound-key operator, audience and A-7 placement decision; start source/field-evidence inventory for all 14 non-АР sections. No production or contract write. |
| After actual W52 implementation close | W53 freeze and its exclusive contract/migration owner; backup/restore and durable execution, with focused checks recorded if the owner keeps the code-first branch. |
| After accepted W53 inputs | W54 freeze; run disjoint Stage A preparation and serial custody/repair/snapshot/embed. Review §3's corpus-first internal order, then build/export the real bundle under exact grants. |
| After W54 bundle and accepted predecessor | W55a freeze and implementation; rehearse the bundle on disposable stand and prepare exact release candidate. |
| After separate exact-SHA publication instruction | P3: W55a code publication, preceded by its one-off copy (K-6). No corpus bytes. Do not infer this instruction from a green gate or this plan. |
| After a separate owner instruction naming the bundle | P4: `W55A-STAND-IMPORT-01`. Capacity probe, one-off copy, maintenance window, import, `report` reconciliation, administrator activation and live evidence (§4). |
| While corpus/АР waves run | (*unadopted route, K-4*) Finish source/licence, PB author, experts, blinded sets and identity decision for W59–W63; hold contract/runtime/route integration for their authorized wave slots. |
| After W58 development acceptance | W59 seal and first four profile/routes, then W60/W61/W62/W63 under their own accepted predecessors; first beta only after complete W63 B1–B12 (*unadopted, K-4*). |

The quickest route is the one with early inputs and no rework: a failed
one-off copy, an unjournaled paid intent, missing BGE build, stale source identity,
uncertain section membership, unapproved audience or skipped exact-SHA
release evidence stops the affected transition. A faster-looking partial
upload or synthetic-only section score is recorded as incomplete, not as
corpus installation or section implementation.
