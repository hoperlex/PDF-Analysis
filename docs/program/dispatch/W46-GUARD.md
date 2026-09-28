# W46-GUARD — four guards that could not fail, and the sentence the contract owes about absence

**task_id:** `W46-GUARD` · **wave:** 46, sub-stage C · **lane:** `gate-w46a`
**worktree:** `/root/w46seal` · **branch:** `agent/w46-guard`, based on the dispatch commit
**depends_on:** `W46-SPEND`, `W46-JUDGE-X`, `W46-JUDGE-Y`

Read `docs/program/dispatch/W46-STAGE-C.md` first. Then read
`git show agent/w46-judge-x:docs/program/reviews/W46-JUDGE-X.md` (findings X-1, X-2, X-4, X-7
and X-11, with their reproductions) and `git show
agent/w46-judge-y:docs/program/reviews/W46-JUDGE-Y.md` (its cross-examination section, if one is
there when you start). The findings are your premises. Where this brief and a report disagree,
say which one is wrong and why.

## G1 — the served document, compared with the frozen one (X-1)

No test in `make gate` compares `create_documentation_app().openapi()` with
`contracts/api/v1/openapi.json`. `W13-CONF.md` §11 recorded `test_openapi_conformance_live.py` as
*"deliberately not written"*, and it never was, although the programme's prose speaks as if the
comparison exists. X made `RunActivity.spend` required again in `api/schemas/models.py` only. The
conformance engine found the difference, and the whole battery still passed, 2504 of 2504. At
`f50e656` a real difference went unseen.

Write the test on the existing engine. **Run it on this tree first.** If it reddens on a
difference already there, **stop and report the difference.** Do not tune the test until it
passes: whether that difference is a defect or an accepted form is the integrator's call. Show
the test failing under X's mutation.

## G2 — `F-5a` can fail on a wrong count, not only on a missing row (X-2)

Two of X's mutations passed all 612 tests: every count forced to `0`, and `cost_basis` always
`"measured"`. Seed known data, so that the counts are known in advance for documents per project,
per section and unclassified, findings per verdict, runs per state, and spend with one estimated
call. **Assert the exact numbers.** Show both of X's mutations failing, plus one of your own.

## G3 — the historical-section control cannot be blinded by a code block (X-4)

`^#+.*historical record.*$` also matches a shell comment inside a fenced code block. X placed
such a block after the surface-triple paragraph and followed it with a stale head `0010`, and the
file still passed, 21 of 21. Make the boundary a real Markdown heading, outside code fences.
Close X's second hole as well: a boundary that falls **after** the first claim hides every claim
behind it. Show X's mutation failing. Then show judge A's mutation (`F-5`, a `###` heading placed
too early) still failing.

## G4 — a cookie is input (X-7)

`_takes_caller_input` in `test_openapi_document.py` ignores `in: cookie`. Count it as input, and
show the rule failing with a required cookie parameter added to `getDashboardSummary`.

## G5 — the contract says what an absent `spend` means (X-11): a description-only reseal

`RunStatus` describes the absence of its cost fields; `RunActivity.spend` does not. Add the
sentence: absent when the deployment has made no provider call. **This is a reseal:** one commit,
five documents, digests recomputed. The surface stays 17 / 20 / 61, with 22 error codes and head
`0011`, and the generated types must not change shape. In the same commit, correct the lock's
`commit_note` claim *"the reason every reseal note below gives"*. X measured it true for 3 notes
of 8.

## allowed_paths

```
contracts/api/v1/openapi.json · web/openapi/** · web/FRONTEND_LOCK.json
web/src/shared/api/generated/** · src/auditmanager/** · tests/** (NOT tests/e2e/**)
docs/program/W46-GUARD.md
```

## forbidden_hotspots

`web/src/**` except `shared/api/generated/**`, and `web/tests/**` and `tests/e2e/**`, belong to
`W46-CLIENT`, live in `/root/w46dash`. Also forbidden: `contracts/domain/v1/error-codes.json` ·
`db/migrations/**` · `infra/**` · `docs/program/CURRENT_STATE.md` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · `Makefile` · `package.json` · any container not named `gate-w46a*`.
**The owner's stand is read-only.**

## Verification

The worktree is provisioned. Baseline: `d5c9be5` gated `GATE OK` under `W46-JUDGE-X`, with
battery 2504. During development, run targeted suites. At the end run **one**
`make gate > /root/w46g-gate.log 2>&1`, and take the verdict from the `GATE OK` line. Before
starting it, check `free -g`, and confirm that no `make gate` whose cwd is under `/root/w46*` is
running. **Exit status 137 is the OOM killer, not a result.**

## Discipline

Open `docs/program/W46-GUARD.md` before your first measurement. **Commit after each step.** Show
every new guard failing under a quoted mutation, then revert. **Kill only by PID**, and only your
own descendants. Do not tag, push or merge, and do not keep working after you hand back.
