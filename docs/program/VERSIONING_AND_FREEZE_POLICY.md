# Versioning and freeze policy

## Product tags

Before v1.0 checkpoint tags are capability milestones, not semantic-release promises to external consumers. Tag names are fixed by registry.

## Contract versions

Machine contracts use independent versions. Drafts may use `1.0.0-draft.N` before CP-00/CP-01. Once a major contract is consumed by released checkpoint:

- backward-compatible optional addition → minor;
- bugfix/clarification with no machine/semantic incompatibility → patch;
- required field/remove/rename/meaning/state-transition incompatibility → major or explicit compatibility bridge.

## Freeze levels

### Design freeze
Semantic glossary/invariants agreed; machine schema may still change inside contract task.

### Contract freeze
Exact schemas/enums/state machines and examples are fixed for the wave. Parallel consumer work starts here.

### Checkpoint freeze
Integration commit + migration head + dependency locks + contract manifest + evidence accepted. Tag points to this exact state.

## Freeze break procedure

1. stop dependent integration;
2. create blocking contract task;
3. document reason/compatibility impact;
4. update schema/examples/tests;
5. assign new contract version/freeze commit;
6. rebase/restart affected consumer tasks from new freeze;
7. do not merge mixed old/new consumers.

## Dependency locks

Root runtime/tool versions become part of checkpoint evidence at CP-01. An agent cannot update dependencies opportunistically inside a feature task.
