# `W10-FND` — mutation sweep of findings, decisions and exports

Session `W10-FND`, worktree `/root/w10fnd`, branch `agent/w10-fnd`.

**`HEAD` on arrival: `e08da85`** (`docs: the wave 10 dispatch — five parallel sweeps of the
rule surface`). The brief names the base as `fb30e96`; `e08da85` is one commit later on the
same line — the dispatch commit itself — so the base matched with a dispatch doc on top.

This is a **restart**. An earlier attempt was killed with nothing committed. This file is
appended to and committed after every batch of mutations, so a second kill loses one batch
rather than a wave.

## Method

Every mutation is applied to a copy of `src/` outside the worktree, with `contracts/`,
`docs/` and `fixtures/` symlinked in, and run with `pytest -o pythonpath=<copy>/src`. Every
run prints `auditmanager.__file__` and the result is discarded unless it resolves under the
copy. Every mutated line is read back after the edit and quoted in the table below, so a
mutation that does not mutate is visible rather than assumed.

## Sweep table

_(appended per batch)_

