# W54–W57 chain judging (2026-10-12)

**Subject.** The plans at `33fe3f7` on `plan/corpus-chain`:

- `W54-PLAN.md` revision 4;
- `W55-PLAN.md` revision 4;
- `W57-PLAN.md` revision 3;
- `W56-PLAN.md` with its 2026-10-12 amendment;
- `FAST-PATH-NORMS-SECTIONS.md`;
- `ROADMAP-TO-BETA.md` §10.16.

**Judges and method.** Seven fresh-context, read-only subagents of session `pdf-analysis-4e`:
design and grants for each plan, plus one for cross-plan consistency.

- Tree: `origin/dev` `3aeb75a`, read through git objects or a `git archive` export.
- `pin_sweep.py` was run read-only by the grants judges.
- No suite was run.

**Round number.** This is W57's second and last round (`R-V4`). For W54 and W55 it is the first
round on their rewritten revisions. Fixes are applied by the authors and checked by the
integrator; there is no further judging round.

## Verdicts

| Judge | Verdict | Blockers | Majors |
| --- | --- | ---: | ---: |
| W54 design | ACCEPT-WITH-FIXES | 0 | 7 |
| W54 grants | ACCEPT-WITH-FIXES | 2 | 4 |
| W55 design | ACCEPT-WITH-FIXES | 1 | 6 |
| W55 grants | REJECT | 2 | 7 |
| W57 design (round 2) | ACCEPT-WITH-FIXES | 0 | 4 |
| W57 grants (round 2) | ACCEPT-WITH-FIXES | 0 | 5 |
| Chain consistency | CONSISTENT-WITH-FIXES | 0 | 4 |

## Findings (abridged; the authors received the full texts)

### W54 design (W54D)

- **M1. The disk budget does not close.**
  - The 13 GB already on disk is set against 16 GB free, and the stop rule is ambiguous.
  - Available RAM is 5 GiB, below the 6 GiB floor.
- **M2. The base moved.** R-85…R-87 are recorded and P1 rode W53's publication.
- **M3. The P2 bootstrap rehearsal does not name its stack.** The stand has no `worker` service.
- **M4. The rollback contradicts `MAIN_AUTODEPLOY_POLICY.md`.** Recovery after the deploy
  restarts the writers and is undefined. No rollback is stated per lane.
- **M5. The repair journal writes to the file and the database with no defined order.** The
  R-79 limits are missing.
- **M6. The client fingerprint counts shared tables the import writes.**
- **M7. The overrun trigger always fires** (day 4, against a 34 h Stage B).
- **Minors:**
  - custody document stale points;
  - D-143, D-152 and D-144 placement;
  - `capacity` fields;
  - requeue, `attest` binding, `receive` before `dump-db`, and the age of an open record;
  - `publish_bindings` should take a role target.

### W54 grants (W54G)

- **B1. SEAL's stub operations turn two composition sweeps red.**
  - `EXPECTED_UNADDRESSED`, the page-shape sweep and the 503 counter.
  - The files: `test_an_absent_parent_is_not_an_empty_page.py`, `test_router_answers.py` and
    `test_every_port_implementation_is_whole.py`.
- **B2. `test_w53c_exec_closure.py:267` goes red when `worker` leaves `AGGREGATES_NOT_INSTANTIATED`.**
- **M1. WORKERS-WEB is missing `_pages/queue/**`, the execution tests and the screen tests.**
- **M2. WORKER is missing `tests/integration/api/**` and `bootstrap/public.py`.**
- **M3. JUDGE-A has no feasible slot.** Split it in two.
- **M4. STAND-COPY is missing `test_bundle_transport_refusals.py` and `lib/forced-command.sh`.**
- **Minors:**
  - the SNAPSHOT `conftest.py` level;
  - the RELNOTES level;
  - `light_acceptance.py` contexts;
  - parallel writers to `infra/deploy/README.md`;
  - the probe directories;
  - identifiers written out in full;
  - exact paths;
  - EMBED and the image test;
  - D-142 against the `qa_w53` tests;
  - wrong caller lines;
  - the colliding R-86 and R-87 labels.

### W55 design (W55D)

- **B1. §A7 cannot run.**
  - `resume` is never called.
  - "No verb restores" is false.
  - There are no failure branches.
- **M1. The base moved.** P1 is done without a read-back, and the R labels collide.
- **M2. The disk sums mix resident and temporary usage.** The second bundle copy and the staged
  dump are missing.
- **M3. The rehearsal cannot size the stand window.**
  - `receive` should run before `dump-db`.
  - The copy record's 12 h limit is missing.
- **M4. Qualification ignores reconciliation.** "Never searchable" is only a procedural promise.
- **M5. Streaming has no grant.** `WireResponse` takes bytes only.
- **M6. The rehearsed SHA is not the published one.** `statement_timeout` is set after the rehearsal.
- **Minors:**
  - the refusal code;
  - G-11 precision;
  - an unobservable digest check;
  - the tag created by a non-INT task;
  - the end-of-file integrity check;
  - the maintenance-marker check;
  - two executors for the capacity probe;
  - the RAM figures.

### W55 grants (W55G), REJECT

- **B1. SEAL is missing the three composition guards.** The same files as W54G-B1, plus
  `{ndoc_id}`/`{portal_block_id}` in `identifiers.json`.
- **B2. STREAM is missing `tests/e2e/test_upload_limit_headroom.py` and its fail-proof.**
- **M1. The R-70 levels are wrong for the lanes that touch `bootstrap/**` or a `conftest.py`.** The
  screen lanes defer `e2e:pc01`.
- **M2. WEB-NORMS is missing `web/tests/unit/qa_w50/r66-navigation.test.ts`.**
- **M3. CONTENT cannot stream through `WireResponse`.**
- **M4. BUDGET is missing the settings and composition files and about 25 `start_audit_run` callers.**
- **M5. The base moved.**
- **M6. §C0's WORKER-01 is ambiguous.**
- **M7. The order is not feasible.** RELNOTES comes before P2, and PROMOTION-PRE comes after D124
  and the rehearsal.
- **Minors:**
  - pins;
  - missing ‡ marks;
  - the inherited "no new code or identifier" qualifiers;
  - double grants;
  - the setter actor;
  - STREAM's router and test files;
  - no explicit grants for STAND-IMPORT and INT-MAIN;
  - the rehearsal test.

### W57 design (W57D), round 2

All 18 round-1 findings are resolved in the text; m-12, M9 and the latency samples only partly.

- **M1. The activation guard contradicts the build precondition.** The build is limited to the
  current snapshot.
- **M2. A wrong set cannot be recovered.** Add the builder version to the identity, and pin
  verified rows only.
- **M3. The prompt part and the spend are understated.** It is ≈20–35k tokens; fix a token ceiling
  and a reduction order.
- **M4. The fire-safety scope is narrower than K-2.** Resolved by amending CD-5.
- **Minors:**
  - corpus formatting (LaTeX, `**`, `######`);
  - the refusal code;
  - the `report` current key;
  - two binding roles;
  - latency samples on the stand's gateway;
  - mutated fixtures;
  - the estimate is short by ≈8 h of stand acts;
  - stale rule numbers;
  - amendments mistaken for editions;
  - the spaced-hyphen range.

### W57 grants (W57G), round 2

Round 1's G-1…G-10 are all fixed.

- **M1. No lane holds the custody role registry.** `roles.py`, the custody document and the role tests.
- **M2. NORMREFS cannot pass a new observation role.** It is missing `findings/artifacts.py`.
- **M3. §B3.6 has no hand-written category list.** The `_ENUM_VALUES` and `CATEGORY_CHOICES` sites.
- **M4. PROFILE falsifies `UNEVALUATED_GUARDS`, `P02_SEAMS` §9.2/§9.4 and `test_seam_register.py`
  without holding them.**
- **M5. W57B-FREEZE needs a stand state that a code-first close cannot produce.**
- **Minors:**
  - `pin_sweep` rejects single-`*` grants;
  - SEAL's inherited `tests/contract/**`;
  - files that can be named now;
  - the §A5 and grant mismatch;
  - a `catalog-message.ts` sentence;
  - the refusal code;
  - stale rule numbers;
  - R-70 levels for CAP, REHEARSAL and RELNOTES;
  - the `nrs_` identifier files.

### Chain consistency (CH)

- **M1. W56A-INT-MAIN has no K-6 copy.** Its tag and grep ignore the release rule.
- **M2. W55 and W57 do not invoke W54's copy verbs as frozen.** `fetch`, `attest` and `resume` are
  missing.
- **M3. W57's pre-push check needs a verb nobody builds.**
- **M4. No profile-switch mechanism exists.**
- **Minors:**
  - stale §6.2 estimates: ≈99 h to P4 and ≈312 h to W57b, against the roadmap's 70 h and 290.5 h;
  - the refusal-code conflict;
  - W54 and W57 role and verb hooks;
  - the copy order in W57;
  - stale text in FAST-PATH, ROADMAP, W55, W56 and W57;
  - scope leakage of the unadopted W56B and beta-at-W63 text (mark it "unadopted, K-4");
  - W53's main publication as P1.

## Dispositions

The integrator's decisions are CD-5 (amended) and CD-15…CD-21 in
`reviews/W54-W57-CHAIN-REVIEW.md`. Each author applies its plan's findings and reports every
finding as fixed or not, with the reason. The integrator applies the chain findings in
`ROADMAP-TO-BETA.md`, `FAST-PATH-NORMS-SECTIONS.md` and `W56-PLAN.md`.

## Fix round and verification (2026-10-12)

**The fix round.** The authors applied every finding.

| Commit | Change |
| --- | --- |
| `58de8af` | W54 fix round |
| `ca33abb` | W54's deploy refusal (later corrected) |
| `7639a66` | W55 revision 5 |
| `e38d32b` | W57 fix round |
| `4d16018` | integrator fixes to W56 |
| `d1a6519` | integrator fixes to ROADMAP and FAST-PATH |
| `04ffb87` | integrator fixes to ROADMAP §6.2 |

**The verification.** Two fresh read-only verifiers checked every blocker and major against the
fixed text at `ca33abb`.

- All judged blockers and majors are FIXED, except three PARTIAL items in W55.
- 27 items were open in total. Among them:
  - one regression introduced by the integrator's own request: the deploy refusal on any open
    copy record would have refused every CD-16 publication;
  - a custody-target mismatch between W54 and W57;
  - missing verbs and arguments in W55;
  - five deleted requirements in W57 and two in W55;
  - stale text.

**Closing the open items.**

| Commit | Change |
| --- | --- |
| `297a05c` | W54: `attest … (publish <sha>\|import)`; deploy.sh accepts exactly the bound SHA and refuses under the importer lock, an import record or an unattested record; recovery is `restore-db` → reviewed revert → `resume` |
| `bc808a1` | W55 |
| `71f1ee2` | W57 |
| `90aa456`, `36b1018` | integrator |

The integrator's closing greps found no stale marker and found the `attest` forms consistent
across W54, W55, W56, W57 and FAST-PATH.

**Integrator choices recorded here.**

- The prompt-part ceiling is 10,000 tokens, where the judges suggested about 15k. With one
  re-record, 15k would break K-10's $8. The declared reduction order applies.
- `listWorkers` stays a SEAL stub until WORKER. The composition sweeps are granted to both.
- A new task, `W54-CORPUS-OPERATE-01`, carries the operator steps that sat inside W54's INT-CLOSE.

**Still open, for the owner.**

- Disk on this host: the W54/W55 peak is ≈ 28 GB against ≈ 14 GB free (CD-21).
- Installing the two forced-command keys and naming the administrator account.
- The P1 client-object read-back, which now runs at P2.

**Final sizes.** W54 43 KB, W55 65 KB, W57 58 KB. Against the judged revisions that is −21 %,
−23 % and −28 %.

## Approval (2026-10-12)

The owner approved the chain at `a49cf78` by direct poll (ROADMAP §10.16 K-13) and chose to free the ignored
caches of inactive worktrees for disk (K-14). A later owner answer relayed by `pdf-analysis-62` (K-15) replaces
the plans' per-lane full-gate levels with light acceptance per lane plus one full `make gate` on each wave's
final candidate before `origin/main`; it is a recorded deviation, not re-judged. Implementation is handed to
`pdf-analysis-62` as integrator from this branch.
