# Task W0-ARC-02 — architecture lint rule specification

> **Status: ready for W0.3 assignment.**
> Its sole dependency is independently accepted and integrated at the commit pinned
> below. No contract or ADR write is authorized by this task.

## Outcome

Publish a machine-readable specification of the repository's architectural lint
rules, so that `S00` can record "architecture lint rules specified" as CP-00 exit
evidence and `W1-ARC-01` can implement enforcement against a fixed rule set rather
than against prose.

This task **specifies** rules. It does not implement, run or enforce them.

## Ownership

- implementation owner: assigned architecture agent; must not also own `W1-ARC-01`
  enforcement
- program integrator / frozen-boundary governor: primary agent `/root`
- independent reviewer: assigned by the integrator; must not author the reviewed
  specification
- product/domain approval authority: repository owner/user; not required for a
  specification-only change unless a rule encodes an unresolved product semantic

## Depends on

- `W0-ARC-01`, integrated at
  `cf7740474b1786163f54d93b013a0d526ef989e0`.

Independent review accepted `W0-ARC-01` as a candidate, not as ratification, and its
artifacts are now committed as W0.3 ratification inputs.

## Origin

Opened by owner disposition on `U-03` recorded in
`docs/architecture/CP00_OWNER_DECISIONS.md`: the specification is required before
CP-00, enforcement is deferred to `W1-ARC-01`.

## Frozen inputs

- base commit: `43a84d93fd544573226b82860ab24f924ed66d83`
- architectural prohibitions: `AGENTS.md` §4 at the base commit
- accepted CP-00 architecture review: `docs/architecture/CP00_ARCHITECTURE_REVIEW.md`
  and `.json` at their accepted commit
- `docs/architecture/ARCHITECTURE_BIBLE.md`, `ADR-0004`, `ADR-0016` at the base commit
- `docs/architecture/REPOSITORY_LAYOUT.md` at the base commit
- machine contracts: read-only; migration head: none

## Allowed paths

- `docs/architecture/ARCHITECTURE_LINT_RULES.md`
- `docs/architecture/ARCHITECTURE_LINT_RULES.json`

No other path is writable.

An earlier draft of this task also allowed an indexed row in `ADR_INDEX.md` for the
case where a rule supersedes an ADR statement. That slot was impossible to use:
authoring the superseding ADR requires `docs/architecture/adr/**`, which is not
writable here, and the validator rejects an index row whose target file does not
exist. A supersede finding is therefore **escalated, not executed** — record it under
deliverable 6 and let the integrator open an ADR task with the right owner.

## Forbidden hotspots

- `docs/architecture/ADR_INDEX.md` and `docs/architecture/adr/**`
- `contracts/**`, `fixtures/**`, `tests/**`, `scripts/**` and all source/runtime code
- program/current-state/checkpoint/stage-plan files
- root dependency/lock files, migrations, composition root and global styles
- every legacy repository file, ref and worktree entry

## Non-goals

- No linter implementation, configuration, CI wiring or dependency addition.
- No enforcement run and no claim that any rule currently passes.
- No new architectural prohibition invented beyond the frozen inputs; a rule either
  traces to `AGENTS.md` §4, the Bible, an accepted ADR or the CP-00 review.
- No tool or vendor selection: the specification states what must be detectable, not
  which linter detects it.
- No product-semantic decision and no resolution of open owner decisions.

## Deliverables

1. `ARCHITECTURE_LINT_RULES.json` — the machine rule set. Each entry requires:
   - `rule_id` (`ALR-NN`, unique, stable);
   - `statement` — the invariant in one sentence;
   - `source_anchor` — the frozen input it derives from;
   - `scope` — the path globs the rule applies to;
   - `enforcement` — `static`, `test` or `review`;
   - `severity` — `error` or `warning`;
   - `detection` — what a checker must observe to decide a violation;
   - `false_positive_notes` — known legitimate shapes that must not be flagged;
   - `waiver_policy` — whether a waiver exists and who may grant it.
2. `ARCHITECTURE_LINT_RULES.md` — the human document. Every `rule_id` appears exactly
   once in a table row beginning `| ALR-NN |`, with a positive and a negative example.
3. Full coverage of `AGENTS.md` §4: every listed prohibition maps to at least one
   rule, or is explicitly recorded as `review`-only with the reason it cannot be
   decided statically.
4. An explicit `review`-only subset. A rule that cannot be mechanically decided must
   say so rather than be dropped or weakened into a `warning`.
5. A handoff section naming exactly what `W1-ARC-01` must implement first: the
   `error`-severity `static` subset.
6. An escalation list: any rule whose statement contradicts an accepted ADR, recorded
   with the conflicting ADR id and the evidence, for the integrator to route to an
   ADR-owning task. This task never authors, supersedes or indexes an ADR.

## Required tests

- Command: `.venv/bootstrap/bin/python -c "import json,re; from pathlib import Path; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); rules=spec['rules']; ids=[r['rule_id'] for r in rules]; assert ids and len(ids)==len(set(ids)); assert all(re.fullmatch(r'ALR-\d{2}',i) for i in ids); required={'rule_id','statement','source_anchor','scope','enforcement','severity','detection','false_positive_notes','waiver_policy'}; assert all(required<=set(r) for r in rules); assert all(r['enforcement'] in {'static','test','review'} and r['severity'] in {'error','warning'} and r['scope'] and r['statement'] and r['source_anchor'] and r['detection'] for r in rules); md=Path('docs/architecture/ARCHITECTURE_LINT_RULES.md').read_text(); md_ids=re.findall(r'^\|\s*(ALR-\d{2})\s*\|',md,re.MULTILINE); assert sorted(md_ids)==sorted(ids) and len(md_ids)==len(set(md_ids))"`.
  Expected: exit `0`; the JSON rule set is well-formed and the Markdown table covers
  exactly the same rule IDs, each once.
- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; spec=json.loads(Path('docs/architecture/ARCHITECTURE_LINT_RULES.json').read_text()); covered={c for r in spec['rules'] for c in r.get('covers_prohibitions',[])}; declared=set(spec['agents_md_prohibitions']); assert declared and covered==declared, sorted(declared^covered)"`.
  Expected: exit `0`; every `AGENTS.md` §4 prohibition the specification declares is
  covered by at least one rule, with no orphan on either side.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0` with a standalone `PASS`.
- Command: `git diff --check -- docs/architecture`.
  Expected: exit `0` and no output.
- Command: `git status --porcelain -- docs/architecture`.
  Expected: exactly two lines, `?? docs/architecture/ARCHITECTURE_LINT_RULES.json` and
  `?? docs/architecture/ARCHITECTURE_LINT_RULES.md`, and nothing else under
  `docs/architecture`.

  This deliberately replaces `git diff --name-only <base> -- docs/architecture`, which
  was unusable here: both deliverables are new files, the task forbids `git add`, and
  `git diff` sees only tracked content — so the command returns empty output whether
  the author wrote both files or nothing at all, while the stated expectation of two
  paths can never be met. `git status --porcelain` reports untracked and modified paths
  alike and therefore discriminates. After the integrator stages the files, the
  `git diff` form becomes meaningful again and is worth re-running then.
- Independent reviewer confirms every `static` rule is genuinely decidable without
  running the application, and that no `review`-only rule was silently downgraded to
  a `warning` to appear enforceable.

## Integration contract

After acceptance, `W1-ARC-01` may rely on stable `rule_id` values, the `enforcement`
and `severity` fields, and the `detection` description as the implementation target.
It may not rely on any rule being currently satisfied by the repository: this task
makes no compliance claim. A rule's `statement` may be clarified later, but changing
its `rule_id`, `enforcement` or `severity` after acceptance requires the normal
freeze-break procedure.

## Failure/idempotency/security cases

- A prohibition that cannot be decided statically is recorded as `review` with the
  reason; it is never dropped, and never relabelled `static` to look enforceable.
- Re-running the specification updates one entry per `rule_id`; it cannot duplicate
  an ID or silently remove an accepted rule.
- Rules and examples contain no credential, production payload, customer data or
  legacy checkout content. Examples are synthetic.
- A waiver, where one exists, names an authority; no rule carries a self-service
  bypass.

## Rollback / feature flag

Documentation-only task; no feature flag applies, and a specification gate must not
have a bypass. Roll back by reverting this task's two architecture documents before
enforcement exists. After `W1-ARC-01` implements enforcement, a rule change follows
the versioning procedure.

## Handoff

- changed files and the rule count by `enforcement` and `severity`
- commands/results, including the two coverage gates
- new/changed contracts: `none`
- known limits: which prohibitions are `review`-only and why
- integration notes for `W1-ARC-01`: the exact `error`/`static` subset to implement
  first
- allowed-path proof that no contract, fixture, test, script, program document or
  legacy path changed
