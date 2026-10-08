# W52 plan — judging record (two rounds, the cap of `R-V4`)

Subject: `docs/program/dispatch/W52-PLAN.md` on `plan/roadmap-to-beta`. Judges ran in fresh
contexts, read-only, against `integration/w49` (W49 seal landed) and `integration/w48-close`. They
neither edited nor ran suites. Their full reports exist only in the planning session's transcript;
this file records the findings and what the plan did with each.

## Round 1 — subject `dd0f114`

| Judge | Verdict | Majors |
| --- | --- | --- |
| design and feasibility | ACCEPT-WITH-FIXES | 7 |
| grants and pins | REJECT | 7 |

| Finding | Resolution in revision 2 (`ebc4f8a`) |
| --- | --- |
| loader refused a release missing from the image, blocking rollback | rules 1–4 of §3.3; newer releases left and hidden |
| `build_id` scope underdetermined; stamped by a build step | computed by the API at start-up over its own files; limits registered |
| `{version}` as a path parameter breaks `test_openapi_document.py` (`_uid`/`_id`, pattern) and `AGENTS.md` §4 | releases have no public identity; `PUT /me/release-notes {read_through}` |
| `contract_version` bump touches ~45 files across four families and was not an owner answer | not moved in W52; decided at the beta freeze |
| Stage C internal dependency (`VERSION`, schema, placeholders) | RELEASES-API owns them; RELNOTES and ACCEPT moved to Stage C2 |
| SEAL grant narrower than W49's final grant | rebuilt on `W49-SEAL-01`'s final grant |
| RELEASES-API grant missed `test_deployed_stack_probe`, `test_session_register_volume`, `test_reset_script_refusals`; `infra/local` has no API | granted; `infra/local` dropped |
| RELEASES-WEB missed eslint raw-fetch, env-read and rendered-language guards | `shared/api/version-check.ts`, `shared/config/env.ts`, the matrix granted |
| facts file: digest is a tautology; two error counts; stale `toHaveLength(22)`; inventory filter number-specific | fixed schema, explicit lists, two counts, number-agnostic inventory |
| gate lane: idle-host timing impossible in parallel; id invariant contradicts its own step | timing by the integrator at serial points; JUnit outcome invariant |
| «Что нового» did not follow an update | shown on mount, rule on the server |

## Round 2 — subject `ebc4f8a`

| Judge | Verdict | Majors |
| --- | --- | --- |
| design and feasibility | ACCEPT-WITH-FIXES | 2 (text) |
| grants and pins | ACCEPT-WITH-FIXES | 5 (grant lines) |

Both judges stated that every fix is text or a grant line and that a third round is not needed.

| Finding | Resolution in revision 3 (`761b45e`) |
| --- | --- |
| "equal to any revision → no-op" shows B forever after A→B→A | authored integer `revision`; equal revision with other content refuses; lower is a rollback no-op |
| "released after account creation" undefined (authored date vs deploy time) | `app_user.created_at < min(release_revision.loaded_at)` |
| `server-credential.guard.test.ts` pins the `NEXT_PUBLIC_*` names | granted to RELEASES-WEB |
| `dashboard-invalidation.guard.test.ts` requires every mutation hook in its map | one map entry granted to RELEASES-WEB |
| contrast census fails on unreached colour rules | `web/tests/unit/styles/screens.ts` granted; styles in widget modules |
| live journey fails on an undeclared `/bff/v1` call; the dialog would block routes | `manifest.json` granted with `optional_api`; journey dismisses once; dialog non-blocking |
| PINSWEEP acceptance unmeetable (W49 commits changed non-pin files) | fixture lists pin-caused files with reasons for exclusions |
| minors: mark only rises and compares by `sort_key`; `release` row trigger; canonical-JSON hash; loader entry pattern; served shape pinned; fail-closed rules; `/bff/version` session-only and no `server-env`; `getVersion` renamed `getProductVersion`; `P02_SEAMS` idempotency rule; README services paragraph; one-source `COPY` lines; `shared/config/index.ts`; facts-inventory exemption; estimate stated against both overheads; roadmap §8.3 and A5/A6 rows resynchronised | applied |

## Open for the owner (asked in `W52-RULE-01`)

- A5 as implemented: hand-written facts file; live prose does not read it.
- A6 as implemented: the serial half only in W52.
- `contract_version` unchanged until the beta freeze.
