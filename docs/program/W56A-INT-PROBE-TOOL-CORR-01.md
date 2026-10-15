# W56A-INT-PROBE-TOOL-CORR-01 — degenerate-evidence refusal

The published one-call tool now treats `unknown`, `none`, `null`, `stub`
and `model` as placeholder identities, alongside proxy/default/auto. A
nonempty answer requires positive prompt tokens, completion tokens and
reported cost. This closes two false-PASS shapes before any live probe.
The MODEL-PIN task names the corrected dev tip as its execution base.

Focused provider tests: **16 passed**. No gateway call was made. Contract
and migration bytes, `P02_LOCK.json`, spend ledger and previous failed
probe report remain unchanged. No full local gate, manual acceptance,
`origin/main`, deployment or tag was run.

Changed paths are the tool, its focused test, MODEL-PIN task, top
`CURRENT_STATE.md` entry, this report and its task definition. No root
dependency/lockfile, runtime adapter, composition root, global style,
credential or gateway configuration is touched. The integrator checks
contract prose, Python compilation, direct governance, exact paths and
whitespace, then fast-forwards `origin/dev` only from `7fd152c0` and reads
the remote ref back. Both distinct gateway probes remain pending; PROVIDER
and live recordings stay blocked.
