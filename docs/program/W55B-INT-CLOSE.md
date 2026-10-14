# W55B-INT-CLOSE — W55b development closeout

**Integrator:** Codex, 2026-10-14. **Authority:** the W55 plan Part B, `W55B-FREEZE-01`,
`R-121`–`R-128`, and the owner's instruction to close W55b on `origin/dev` only.
`origin/main` is outside this task and remains at `23fd729` (`v0.5.0`).

## Candidate and verification

- Base: `origin/dev` `9da3ea06` (0.5.1 polish). Gated candidate:
  `8c5a109bd98302b64fb47b364d4c639ff63c0eda`, clean `integration/w55b` after the
  `W55B-FIX` and FIX-2 merges, `GATE-PKG-01`, and revision-2 release notes.
- One full `make gate` was launched on that exact clean SHA and the same PostgreSQL/S3
  stand. Its static steps passed: frontend lint and typecheck, Vitest 137 files / 2,047
  tests, and contract 806 tests / 19,278 subtests. Foundation passed 35 tests. The
  first changed-context battery reached 4,296 passed, 3 skipped, 244 subtests passed,
  16 failed and 33 errors; most late errors were `StorageUnavailableError` in S3 fixture
  setup after host memory fell to 881 MiB. The command exited 2 before its remainder
  battery and did **not** print the literal `GATE OK` sentinel.
- Under owner ruling `R-125`, this infrastructure-voided gate was completed on the same
  clean SHA and stand. The entire failed `tests/integration/composition` and
  `tests/integration/runs` directories reran: 952 passed, 2 skipped. The exact unrun
  battery remainder ran: 938 passed, 5 skipped, 4 subtests passed, with one lease-timing
  failure in `tests/integration/jobs`. That entire directory then reran: 8 passed.
  All required gate components are now green and the gate counts as `GATE OK` under
  `R-125`; this is a completion by recorded reruns, not a literal sentinel from one
  command. The voided run's failures are at lines 3854–3903 of its log (including
  `StorageUnavailableError` around lines 3054–3834); the remainder failure is in its
  short test summary.
- Ignored evidence under `.local/gates/w55b-8c5a109b/`:
  `gate-void-2.log` SHA-256
  `caa4dacef00b90c5adb6afc71aa0cb3f130fa69c9f181f7757e74813fe75b258`;
  `r125-composition-runs-env.log` SHA-256
  `0afbc9aa1f6b8051c15f2185cffdfeb7dc1c876f7fce0f9dc47efbf4f0b7c48b`;
  `r125-battery-remainder.log` SHA-256
  `fa68abd156d605ba772a6c929806b50233f9b17e4f59106f26befe2950110467`;
  `r125-jobs.log` SHA-256
  `343e4082788e09820307bfdec46fec5f4a8b2f5d9c27f1391705ee937b9745af`.
  The memory samples are in
  `.git/gate-runs/2026-10-14T120539Z-8c5a109bd983.mem.tsv` (395 samples, 881 MiB
  minimum `MemAvailable`). The first voided static attempt, `gate-void-1.log`, SHA-256
  `c9e63d2e5d8f1ee82999cbc37333b92097b10bbfce221357b92b46ef6d3f6c28`,
  stopped in Vitest worker RPC after 28 passing assertions with host load about 52;
  it is not counted as acceptance.

## Acceptance and dispositions

| Review | Verdict and disposition |
| --- | --- |
| `W55B-QA-01` | ACCEPT-WITH-FIXES. Its only Major, QA-1 (an unauthenticated caller could consume an upload slot and have its body read), is repaired in `W55B-FIX`; the complete QA directory then passed 67 tests. O-1's busy message was also repaired. O-2's memory figures are below; O-3 remains an observation. |
| `W55B-JUDGE-X` | Initial REJECT on the executor tip `e1233e7a`; its recheck of FIX at `03042093` was ACCEPT, with no open Blocker or Major. FIX-2 closes the new X-11 false refusal under the frozen whole-member compression ratio, while retaining X-5's early declared-size stop and final ratio check. X-2's time residual and X-12 are D-175; X-3's revoked-credential window is D-176; X-4's crop-byte residual is D-177. |
| `W55B-JUDGE-Y` | No Blocker, one Major and six Minors. Y-1(a)'s integral-float mismatch is repaired; Y-1(b)'s degenerate IMAGE run failure is the owner's deliberate `R-121` decision (D-159); Y-1(c)/(d) remain D-160. Y-2 and Y-4 are repaired. Y-3, Y-5, Y-6 and Y-7 remain D-161, D-162, D-163 and D-164 respectively. |
| `W55B-NOTES-JUDGE` | ACCEPT-WITH-EDITS; revision 2 of the 0.6.0 notes resolves the required edits and is merged. The notes are dated 2026-10-15; this development close is not a release or a tag. |

The integrator accepts the out-of-grant `src/auditmanager/runs/executor.py` edits identified
by JUDGE-Y: they seed the bundle members by contract role into `source_preparation` and
`page_geometry_extraction`; without them the stages cannot consume those members. The edits
are minimal and correct; absent roles are not supplied, and the stamp audit is intentionally
not passed to either stage. The other out-of-grant edits and their justifications are in
`W55B-JUDGE-Y.md` under “Out-of-grant edits.”

## Memory evidence for A13 (G-12, W55 plan §C5)

These are measured peaks on specified trees and loads, not a production worker limit.

| Workload | Measurement |
| --- | --- |
| W55a BGE image/tokenizer work | The W55a gate record measured 3296 MiB peak RSS for the offline MRR reproduction under `--network none`; it is not a served-run measurement. |
| W55b text-rich 500-page bundle | Rehearsal §2.1: API upload scope peak 151.7 MiB; its 1,786,430 characters exceeded the 152,361-character budget and both start attempts returned 422 without creating a run. QA O-2 measured 465–505 MiB API VmHWM for a 40-page, 135,440-character run. |
| W55b raster low-text 500-page bundle | Rehearsal §2.2: 210 MiB upload, API scope peak 885.9 MiB; two deterministic runs peaked at 806.1 and 813.7 MB in their scopes, API RSS about 586 MiB. The browser's Chrome-plus-driver scope peaked at 1.72 GiB with all 500 crops loaded. |
| W55b 500-page vector drawing set | Before FIX, the worker was killed at page 126 under a 3 GiB cap. FIX §2.3 reran the same bytes: source preparation peaked at 174 MiB RSS; geometry at about 292 MiB, both stages succeeded in 307 + 415 s on a loaded host. Time against the 900 s watchdog remains D-171/D-175. |
| Owner's 30-page export (F-7, counts only) | Before FIX, rehearsal §2.4 measured 1003.3 MiB API RSS and 0.97 GiB scope peak over its run. FIX §2.3 measured isolated extraction at 220 MiB peak versus 794 MiB before; a complete post-FIX stand run is not claimed. |
| BFF 256 MiB body | FIX §2.4's isolated real-`fetch` probe measured +286 MiB VmHWM before the forward repair and +45 MiB after. This was not `next start` behind nginx; the stand measurement is D-174. |

The runtime memory-limit decision remains open under D-166 until the API and worker are
measured on the stand at the intended limit. The figures above bound representative inputs,
and they show why the pre-FIX drawing-set result cannot be used for A13 sizing.

## Frozen surface, debts and boundary

The wave's sealed surface is 47 paths / 54 operations / 123 schemas, 24 error codes,
domain candidate revision 12, and migration head `0021_portal_bundles`. `VERSION` is
`0.6.0`. FIX-2 changed no contract, migration, root dependency, composition root or
shared fixture. The closing commit changes only this record and `CURRENT_STATE.md`.

D-159–D-177 were opened by the owner ruling, judges, QA, rehearsal and FIX. In particular,
D-162 retains the real AR set's input-token measurement because this host has no proxy key;
D-165 and D-174 retain nginx and BFF stand measurements with a 250 MiB body; D-166 retains
the worker limit decision. W56 owns chunked analysis and region evidence. Anonymised real
fixtures (F-7), the portal API (F-9), PC-02's archive refusal and hybrid search remain
outside W55b. The gate's browser journey is automated evidence; the owner's credentialed
in-product check follows a separately authorised `origin/main` publication.

Development publication is a fast-forward of `origin/dev` after this close record and
`CURRENT_STATE.md` are committed and their contract checks pass. No push to `origin/main`,
no deployment claim and no release tag are made by `W55B-INT-CLOSE`. A future
`W55B-INT-MAIN-01` requires the owner's separate direct instruction naming the exact SHA,
the main auto-deploy policy, the stand cost-ceiling precondition, the exact-tree gate,
workflow and `verify-deployed.sh`, live acceptance and only then the `v0.6.0` tag.
