# Current state

**Reconciled 2026-10-15 on the W56a development line.** This file is the short entry point for
coding agents. The exact task base, frozen inputs and permitted paths come from the assigned task
file and freeze; verify them against Git. The complete earlier state is preserved verbatim in
[the 2026-10-15 archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md). Earlier wave reports,
rulings and evidence remain at their original paths.

## Current development boundary

W56a has integrated a recorded-only AR v2 contract and migration, a deterministic synthetic
corpus, a pure grounded merge core and an offline seeded matcher on `origin/dev`. Reviewed AR v2
profile content, a response schema and parser, marked uncitable OCR context, deterministic
prompt material, a one-call offline identity probe and OCR-only quote grounding are prepared. The matcher still has
no measured baseline or threshold. The gateway model identity and price have not been
verified; no runtime v2 execution or provider call is activated. The code-first work order and entry conditions are in
[`CODE-FIRST-TO-BETA.md`](dispatch/CODE-FIRST-TO-BETA.md); the next block needs its own exact
freeze and task files.

The development API surface is **47 paths / 54 operations / 124 schemas**. The error catalog
has **25** codes, the domain candidate is revision **13** with **32** opaque identities, and the
migration head is **`0022_findings_v2`**. `VERSION` is `0.6.0`. These are claims about this
checkout, checked against the frozen artifacts; they are not a deployment claim.

W55b is the latest closed development baseline. Its full gate completed under `R-125` on an
exact clean candidate after infrastructure failures, without printing the literal `GATE OK`;
see `W55B-INT-CLOSE.md` for the evidence and limitation. `v0.5.0` is the last published release
recorded in this tree. The deployed tree must be checked with
`infra/deploy/verify-deployed.sh`, not inferred from this file.

`R-135` moves the complete gate for development-only W56a–W63 to the end of the planned beta
code series. Each intermediate task runs its named focused checks and records what it deferred.
A development merge or `origin/dev` publication does not claim beta acceptance. A separate
owner instruction for the exact candidate, a complete gate and the auto-deploy policy still
govern any `origin/main` publication. See `AGENTS.md` §6–§8 and
`docs/program/MAIN_AUTODEPLOY_POLICY.md`.

## Open gates and pointers

- D-137–D-140 retain identity browser/QA and full-gate evidence that development closeouts did
  not supply. Later code-only work carries its own deferred checks under `R-135`.
- The gateway model identity and price block provider activation; no unverified provider or
  tariff may be silently substituted. The W56a probe and review reports carry the evidence.
- Normative corpus promotion and served retrieval still require their separate custody,
  corpus and validation tasks; storage plumbing alone is not a live normative claim.
- `docs/program/dispatch/CODE-FIRST-TO-BETA.md`, the applicable wave plan, the assigned task
  file, its completed `depends_on` and the frozen contract set determine the next action.
- `docs/program/DEBT_REGISTER.md` is the open-work register; dated reports in the archive are
  evidence of what was measured then, not instructions to replay old work.

## Previous release state — wave 48 (historical record)

The full previous state, including this wave-48 section and the older CP-00 history, is stored
verbatim in [the dated archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md). The archive is a
point-in-time record of the base tree; it is not the live development status.
