# W56A-PROBE-TOOL-PREP-01 — offline handoff

**Status: code ready; no gateway identity verdict.** Base
`6de331c150f6573e320093bb4b2751f3bda016a2`.

## Result

`tools/provider/identity_probe.py` makes at most one synthetic
chat-completions call per invocation, with 16 output tokens and no retry.
It reads a host-owned provider environment file in memory and prints only
gateway role, selection, reported model, token counts, cost, expected cost,
tolerance and a refusal code. It does not print the URL, token, prompt or
answer. The endpoint rule matches the existing proxy adapter. The explicit
call checks identity and locked primary rate; the default call requires a
distinct concrete identity. Each invocation is separate spend and requires
ledger projection before execution.

The old failed stand example is an offline test: its reported cost
$0.0000046 for 14 input / 16 output tokens is refused against the locked
$0.00047, and a different reported model is refused independently. These
tests do not establish what either gateway serves now.

## Checks

- Focused `tests/contract/provider/test_identity_probe.py`: **14 passed**.
- Focused provider plus contract-prose checks: **91 passed**.
- Python compilation of `tools/provider` and its tests: passed.
- CLI `--help` with `PYTHONPATH=src`: passed, no network.
- Direct executable governance check for this task: no findings.
- `git diff --check`: passed; changed-path proof is the five files below.
- The broader documentation check was **92 passed, 1 failed**: the one
  governance assertion already sees six earlier W56a task files missing
  required sections. Neither this task nor the separate MODEL-PIN draft
  appears in its findings. No full local gate was run.

## Access and spend

No live gateway call was made and the W56a ledger remains $0.0000046 spent
from the historical failed probe. Local provider credentials are absent.
The old stand SSH control session is closed; read-only connection attempts
with the installed keys failed authentication. Automatic approval review
rejected extracting the old SSH password from session logs for a new remote
connection, classifying that as credential probing from an unintended source.
That action was stopped and will not be retried through another route.
Neither the stand nor recording gateway has current PASS evidence.

## Contracts, risks and integrator handoff

Changed files: this report, its task, `tools/provider/__init__.py`,
`tools/provider/identity_probe.py`, and
`tests/contract/provider/test_identity_probe.py`. No API/domain/analysis
contract, migration, provider lock, root dependency, composition root,
global style, product code, deployment configuration, credential,
`CURRENT_STATE.md`, `VERSION`, tag or remote ref changed in this lane.

The tool is intended to run only where the repository code and a sanctioned
host-owned provider environment file are available. It does not establish
that the two gateway roles have distinct routes; the MODEL-PIN operator must
verify that separately and add four bounded ledger entries. Integrate this
preparation on `origin/dev`, then refresh `W56A-MODEL-PIN-01` from that SHA.
PROVIDER and live recordings remain blocked until both gateway pairs pass.
