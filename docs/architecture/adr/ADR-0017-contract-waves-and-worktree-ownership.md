# ADR-0017: Contract waves and worktree-per-task ownership

- Status: accepted for bootstrap; ratify at CP-00

## Decision
Each wave: contract task → freeze → parallel provider/consumer/test/ops tasks → single integration slot → checkpoint evidence. Default isolation is one git worktree/branch per task. Shared hotspots have one owner. Dependencies reference completed task IDs, not unmerged branches.
