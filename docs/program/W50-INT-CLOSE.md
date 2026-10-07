# W50-INT-CLOSE — development closure of the shell wave

**Date:** 2026-10-07. **Verdict:** W50 accepted for `origin/dev` after the exact clean close
candidate passes `make light-acceptance`. This report is part of that candidate and therefore
does not name its own SHA; the publication read-back and exact test result are the integrator's
handoff evidence. No release tag or `origin/main` publication is authorized here.

## Accepted lineage and result

| Stage | Accepted commit | Evidence |
| --- | --- | --- |
| W49 freeze base | `ead639f848b040491f1db7d4da3803216c82bd75` | `W50-FREEZE-01.md`: frozen 27/34/77 API, 23 errors, domain revision 9 / 29 identities, migration `0015` |
| W50 Stage A, B and C | `812a530`, `6b99901`, `99641bb`, `d8112cb`, `eb1539a` | Registry, primitives, home, lazy loading and frame merged on `integration/w50`; lane reports and Stage-C gate |
| QA | `92001f7852266f39ef1f9ab9dd4562c982823a7a` | `W50-QA-01.md`: independent route, keyboard, width and R-66 checks |
| Judges X and Y | `356bbea`, `256e24e1d1eff61dabd3a244cef0b89d12019b41` | `reviews/W50-JUDGE-X.md` ACCEPT and `W50-JUDGE-Y.md` PASS, followed by independent cross-examination; `256e24e` published and read back on `origin/dev` |
| W50-FIX | lane `d8ea61351489fcf08c7ebfe8ff90045b2127b559`; merged `347ad2654713ff3e027ad6d0bb501090df3d4608` | Full lane `make gate` and exact post-merge light acceptance, below |

W50 has one registry for **22** real screens, server guards and validated return paths, grouped
navigation, an account menu, a real home page, four honest placeholder routes, and five lazy
widget wrappers. The production build's 23rd page row is synthetic `/_not-found`, not a
registered screen. `W50-FIX` updated the accepted prose/fixtures and added the R-70 light
acceptance command. No W50 contract or migration edit was made.

## Judge disposition and open debt

Both judges found no release blocker. Their cross-examinations upheld three register-only
findings. They are open and deliberately not repaired by this documentation close:

- `D-134` (X R1, upheld by Y): invalid `next`/`from` remains escaped in raw Next Flight
  metadata, although absent from visible text, the hidden field and redirect target.
- `D-135` (Y JY-1, upheld by X): the registry menu comment claims all open screens appear;
  `/optimisation` is intentionally hidden from the menu but open by direct address.
- `D-136` (Y JY-2, independently rebuilt by X): W50-PLAN §3.4 says five first-load routes
  shrink; four shrink and `/review` grows within the permitted runtime bound.

Each row in `DEBT_REGISTER.md` gives evidence and a check. The correction in Judge Y's report
establishes **22** registered screens; its 23 measured build rows include `/_not-found`.
Historical judge reports and the controlling W50 plan were not rewritten here.

## Counts and checks

| Full-gate point | Backend battery | Frontend | Foundation |
| --- | ---: | ---: | ---: |
| W49 baseline, `W49-FIX` code `49187a4` | 3178 passed / 6 skipped | 1296 | 35 passed |
| W50-FIX exact lane `d8ea613` | 3201 passed / 6 skipped / 298 subtests | 1660 in 105 files | 35 passed |
| Net | **+23 passed / 0 skipped** | **+364** | unchanged |

The frontend increase comes from committed W50 registry, shell, home, lazy, QA and FIX tests;
the W50 diff contains the new `web/tests/guards/**` and `web/tests/unit/**` suites. The net
backend increase is grounded in the committed W50-line changes to
`tests/contract/test_alpha_acceptance_command.py`, the new
`tests/contract/test_light_acceptance_command.py`, and the merged W48.1 proxy tests in
`tests/integration/analysis_text/test_proxy_adapter.py`; the count is the full-gate result,
not a claim that each changed file contributed a fixed number. The W50 browser QA scripts
under `tests/e2e/pc01/qa_w50/**` add coverage outside pytest's battery count.

- The clean W50-FIX lane `d8ea613` ran complete `make gate`: exit 0, literal
  `GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass`.
  Log: `/tmp/w50fix-gate-corpushooked.log`.
- The clean FIX merge `347ad26` ran `make light-acceptance
  BASE=d8ea61351489fcf08c7ebfe8ff90045b2127b559`: exit 0, literal
  `LIGHT ACCEPTANCE OK`; frontend 1660/1660, canonical contract 486 with 50 subtests,
  static PC01/prose 148, lint/typecheck/whitespace all passed. Log:
  `/tmp/w50-fix-merge-light.log`.
- The close candidate changes only the five files granted by `tasks/W50-INT-CLOSE.md`.
  After committing this report, run the same light-acceptance command on that exact clean
  SHA and require `LIGHT ACCEPTANCE OK` before the fast-forward publication.

The older generic `IDENTITY-WAVES.md` §8 and `W50-PLAN.md` close form ask for a full gate on
the exact close SHA. Later direct owner ruling `R-70` (`OWNER_RULINGS_2026-09-17.md` §3.25,
`AGENTS.md` §8) supersedes that for merges and development publication outside named risk paths.
`W50-FIX` touched `Makefile`, so its exact lane tree received the required complete gate. The
subsequent merge and this docs-only close use light acceptance. A risk-path edit would require
another full gate; this close contains none.

## Contract, resource and publication boundary

The frozen API remains **27 paths / 34 operations / 77 schemas**, error catalog **23**,
domain candidate revision **9** with **29** opaque identities, and migration head
**`0015_accounts_roles_registration`**. `git diff --name-only ead639f..HEAD -- contracts
db/migrations pyproject.toml uv.lock web/package.json web/package-lock.json
web/FRONTEND_LOCK.json` returns no path. The five close files touch no contract, migration,
dependency/lock, composition root, global style, runtime or shared fixture.

Read-only `docker ps -a` and `docker volume ls` on 2026-10-07 showed no `gate-w50*` container or
volume; `ss -ltn` showed no W50 reserved listener. Thus the W50 rows in `PORT_REGISTRY.md` are
released. The planning worktrees and the older W48 acceptance worktrees remain outside this
task.

The integrator checks the exact committed close candidate, re-reads `origin/dev`, proves that
remote SHA is its ancestor, pushes only that candidate without force, and reads back the remote
ref. `origin/main` and tags stay unchanged. W51 begins from the verified `origin/dev` subject,
with its own presweep, freeze and grants. This section makes no deployment claim;
`infra/deploy/verify-deployed.sh` answers what is deployed.

## Risks, rollback and handoff

`D-134` … `D-136` remain open prose/metadata issues. W51 still owes preserved `next` through a
refused sign-in and forced password change, filter barrel re-exports, query-key plan consistency
and its planning-owned presweep; none is silently closed here. This close introduces no product
flag. If its documentary state is wrong, revert this close commit on the development line; a
product rollback or a publication to `origin/main` needs its own authority and checks.

**Changed files:** this report, its task, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, and
`dispatch/PORT_REGISTRY.md`. **New/changed contracts:** none. **Integrator instruction:**
publish only the exact clean light-accepted commit to `origin/dev`, then report its SHA and
read-back proof; start W51 only after that. **Forbidden-hotspot proof:** the close grant is a
five-path allowlist and the candidate's path diff must equal a subset of it.
