# Finding the right project context

This page is a reading route, not a new source of product or architectural authority. Read
the task and its dependencies, the frozen contracts it names, and the relevant source
documents. A search result or crop never replaces those sources.

## Start with a small set

1. Read [the agent rules](../../AGENTS.md) and the beginning of
   [current state](../program/CURRENT_STATE.md). The state file is a dated development
   ledger: its recent entries describe candidates and their stated verification limits;
   they do not prove what is deployed. For deployment, use the command named there.
2. For a coordinated change, read its task file and completed `depends_on` records.
   For a routine change, use the request and a concise handoff (`AGENTS.md` §2).
   Check the relevant path boundary, contracts and verification before implementation.
3. For a decision, use the [ADR index](../architecture/ADR_INDEX.md), then the ADR and
   contract it cites. For a known implementation area, start with its code-adjacent README.
4. Read only the matching source sections. Keep the file path and line range when handing
   evidence to another session; recheck them against the current tree before relying on them.

## Where to look

| Need | Primary source | Related material |
| --- | --- | --- |
| Current development boundary | [Current state](../program/CURRENT_STATE.md) | assigned task, integration handoff |
| Ownership, allowed paths, checks | request or `docs/program/tasks/<TASK_ID>.md` | relevant dependencies |
| Product behavior | [Product synopsis](../PRODUCT_SYNOPSIS.md) | runbooks in `docs/manual-tests/` |
| Architecture decision | [ADR index](../architecture/ADR_INDEX.md) | accepted ADR and frozen `contracts/` |
| Current code seam | `src/auditmanager/*/README.md` or `web/src/*/README.md` | focused tests |
| Open issue or owner ruling | `docs/program/DEBT_REGISTER.md`, `OWNER_RULINGS_*.md` | cited task/review |
| Historical proof | `docs/program/reviews/`, `docs/program/history/`, `artifacts/checkpoints/` | exact cited commit |

Current process rules are in [AGENTS.md](../../AGENTS.md), the
[integration policy](../program/INTEGRATION_POLICY.md) and the
[main deployment policy](../program/MAIN_AUTODEPLOY_POLICY.md). Routine work uses focused
checks. An isolated branch is created when concurrent work or a dirty checkout makes it
useful; a delegated release integrator owns promotion and verification of `main`.

The long [documentation index](../INDEX.md) retains early programme links and status
claims needed by historical checks. Do not use those dated status labels to infer the
present wave. `README.md` at the repository root likewise preserves bootstrap history.

## Read virtual crops without copying documents

`scripts/docs_context.py` indexes the Markdown in the **current checkout**. It separates
ordinary documents at headings and long sections at bounded paragraph/line breaks.
`CURRENT_STATE.md` also separates its `Updated … by …` entries. Index rows contain source
paths and line ranges, not duplicated prose; they are rebuilt on demand, so there is no
shared generated file for parallel tasks to maintain.

```bash
python3 scripts/docs_context.py search 'normative corpus' --path docs/program/ --limit 8
python3 scripts/docs_context.py show docs/program/CURRENT_STATE.md:3-4
python3 scripts/docs_context.py index --output .local/docs-context-index.jsonl
```

The JSONL export is optional, ignored local scratch data. It includes `path`, `start`,
`end`, `title`, `kind` and `chars`, and can be consumed by search or retrieval tools.
Rebuild it after the checkout changes. A crop address is a convenient locator, not a
stable identity or a source citation by itself.

## Why the archive stays in place

Many old tasks, reviews and plans are cited by decisions, checkpoint evidence and
contract tests. Their volume is a discovery problem; moving or deleting them in bulk
would break those references. This route and the on-demand index reduce the amount an
agent needs to read without rewriting historical evidence.
