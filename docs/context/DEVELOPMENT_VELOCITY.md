# Shared development velocity guidance for Codex and Claude/Opus

The common working rules live in [AGENTS.md](../../AGENTS.md). This guide explains how to reach a deployable result faster with less tool and token overhead, without losing essential correctness or architectural consistency. It applies to both Codex and Claude/Opus; model selection, context windows, and reasoning controls remain tool-specific.

**Optimize in this order:** (1) end-to-end development and delivery time, (2) total token cost, and (3) quality and consistency. The third priority is a constraint, not permission to ignore known defects, security issues, or mandatory release requirements. Optimize the **whole task**, including research, edits, verification, rework, and deployment preparation—not the number of commands or tokens in isolation.

Numeric defaults below are heuristics, not acceptance gates. Do not introduce an approval step merely to decide whether a check is necessary.

## 1. Keep one instruction source

Codex reads the root `AGENTS.md`. Keep `CLAUDE.md` as `@AGENTS.md` so Claude loads the same shared rules, including in sessions without direct `AGENTS.md` support. Add tool-specific instructions only for genuine tool differences. Imported instructions still consume context.

Keep stable boundaries, architecture invariants, and useful commands in `AGENTS.md`. Put current SHAs, log excerpts, investigation notes, and task-specific plans in a task/handoff record. Keep occasional procedures behind links; do not automatically import the documentation archive or echo rules through hooks.

References: [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md) and [Claude memory imports](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools).

## 2. Use the fast path by default

For small, isolated changes, the default flow is **locate → edit → focused check → ready for delivery**. Avoid lengthy plans, independent reviews, full test suites, and infrastructure startup unless a concrete risk warrants them. Check enough to support the change; do not prove unrelated behavior again.

| Change profile | Default approach | Expand when |
| --- | --- | --- |
| Copy, docs, formatting, or isolated low-risk fix | Direct edit; diff review and the smallest relevant check | A behavioral dependency or conflicting evidence appears |
| Known behavior change | Short dependency check; targeted unit/component tests | The change crosses a contract, persistence, authorization, or external-effect boundary |
| Unclear defect | One explicit hypothesis and a discriminating check | Results disprove the hypothesis or reveal wider scope |
| Migration, shared architecture, security, data integrity, consequential release change | Analyze affected interfaces and recovery path; use targeted integration checks and independent review where valuable | Unresolved risk calls for broader validation |

Choose checks by **failure impact and affected boundary**, not by lines changed or the desire to achieve a universal green suite. Typical reasons to strengthen verification include schema/data migrations, authorization, destructive operations, concurrency, public API compatibility, and critical cross-module behavior.

**Release policy:** [MAIN_AUTODEPLOY_POLICY.md](../program/MAIN_AUTODEPLOY_POLICY.md) remains authoritative wherever it imposes mandatory checks. This guide does not silently waive them. If that policy requires heavyweight gates for low-risk changes, **revise that policy explicitly** to provide a risk-based fast path; otherwise the main delivery bottleneck will remain.

## 3. Build only the context needed to act

1. Start with the request/handoff, `git status`, current branch, and intended base. Read only relevant recent state.
2. Find paths before contents; locate the public symbol, its direct caller, and the closest relevant test. Begin with roughly 3–5 files and ~100-line sections; these are starting points, not limits.
3. Stop discovery once expected behavior, the edit location, important dependencies, and a proving check are clear. If a search fails, revise the path/symbol hypothesis before scanning broadly.
4. Reuse established source references. Reopen a source only if it changed, the excerpt lacked a material qualification, or new evidence contradicts it.

Examples from the repository root:

```bash
rg --files src/auditmanager/runs tests/integration/runs
rg -n -m 8 'def claim|claim_job' src/auditmanager/jobs
python3 scripts/docs_context.py search 'D-290' --path docs/program/CURRENT_STATE.md --limit 4
python3 scripts/docs_context.py show docs/program/CURRENT_STATE.md:3-4
```

Read a complete relevant definition when necessary; avoid repeatedly retrieving overlapping fragments. A source crop is enough only if it contains the relevant qualifications and its identity/status can be established. An index title or agent summary alone is not evidence.

## 4. Keep tool, test, and infrastructure overhead low

- Search for filenames, symbols, or counts before full matches. Narrow noisy results by path and symbol. Batch independent reads; serialize dependent edits.
- Run the **smallest useful check first**. Do not start containers, databases, or the full integration environment for documentation, static-only, or isolated unit-testable changes. Prefer existing compatible environments, mocks, and in-memory tests when they adequately exercise the affected behavior.
- Start expensive infrastructure only for a specific dependency or risk that lighter checks cannot cover. Reuse an already-running environment when safe; verify it points at this checkout and uses compatible dependencies/configuration.
- Before repeating a test, name the changed input or unresolved failure it will investigate. Reuse an earlier focused result only if code, dependencies, configuration, and environment relevant to that check have not changed; record the scope of reuse.
- For long checks, save the full log outside the conversation. Report the command, real exit code, short result, relevant failure, and log path. Output filtering must preserve the actual command exit status.
- Avoid busy polling and redundant status requests. Use completion notifications or moderate polling. Run resource-heavy suites sequentially on a shared host.

Do not confuse **avoiding duplicate checks** with **skipping newly relevant checks**.

## 5. Update documentation only when it changes meaningfully

Do not produce a new narrative or update multiple state files for every small fix. Update durable documentation when architecture, external contracts, deployment or operational procedures, or established project decisions actually change.

Keep task investigation details, temporary observations, current SHAs, and long logs in one concise working record. Link to authoritative evidence instead of copying it into several documents. Avoid duplicate summaries that can diverge.

## 6. Use agents and reasoning effort selectively

Prefer one agent for straightforward work. Delegate to one or two helpers only when **independent, substantial work can shorten wall-clock time after accounting for context transfer, overlap, and integration**. Give each helper a bounded question, allowed paths, existing source references, required evidence, and a short output format. Check for prior findings before assigning repeated research.

Use one owner for a shared editing hotspot. Parallelize independent investigation, not conflicting edits or heavy checks on a shared host.

Honor an explicitly selected Codex/Opus model. When the runtime permits it, start with sufficient reasoning effort for the uncertainty and increase it after a substantive unresolved failure. Avoid repeated model or session switches for tiny stages; do not assume vendor-specific model, pricing, or effort labels remain fixed.

Continue in a reliable session when possible. A handoff should be **short but complete**, typically covering goal, branch/SHA, diff owner, decisions and source links, checks already completed, next action, and open risks. After compaction, inspect the handoff and current diff before restarting research.

## 7. Finish with proportionate evidence, not ceremonial gates

A task is ready when the requested behavior has been implemented, the relevant diff has been reviewed, appropriate focused checks have passed, and known material risks or unverified boundaries are disclosed. Keep the completion note brief: **what changed; what was checked; what was not checked and why; any blocker or risk**.

Do not add a mandatory review meeting, checklist ceremony, or secondary agent approval for ordinary low-risk changes. Apply deeper review to concrete risks, not to every task by default. Mandatory release requirements still apply until formally changed.

## 8. Measure delivery speed and adjust

For the next **5–10 comparable tasks**, record data already exposed by the tools; treat this as a pilot, not proof of percentage savings:

- **Primary:** elapsed time from request to *ready for deployment* (and to actual deployment when measurable); separate coding time from waiting on checks and infrastructure.
- **Secondary:** total input/output tokens, cached tokens if available, helper usage, retries, and rework.
- **Quality guardrails:** escaped defects, rollbacks, missed requirements, and meaningful regressions.

Compare similar task types and mark missing counters as unknown; file size is not token usage. Retain an optimization when it reduces end-to-end time without unacceptable quality regressions. If a verification or documentation step repeatedly dominates the cycle without catching relevant problems, remove, narrow, defer, or redesign it **through the applicable policy**.

**Operating principle:** *The fastest sufficiently safe route to a deployable result is the default. Every expensive step needs a concrete reason; none should exist merely because it was required for a different class of change.*
