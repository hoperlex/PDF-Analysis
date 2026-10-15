# W56A-INT-MODEL-PIN-GRANT-01 — task grant on dev

The grant adds an exact `W56A-MODEL-PIN-01` task after the checked probe
tool. It is **ready for access, not complete**. The old stand probe remains
FAIL, the recording gateway has no result, and `P02_LOCK.json` retains
SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`.

The grant owns only its task file, this report and the MODEL-PIN task file.
No contract, migration, root dependency/lock, composition root, global
style, product code, deployment configuration, credential, spend ledger,
`CURRENT_STATE.md`, `VERSION`, tag or `origin/main` ref changes. No paid
call or full local gate was run.

The task requires both distinct gateways to return the configured model at
the locked rate and a different concrete model for default/stub selection.
The selected gateway name enters the lock only after all four bounded calls
pass. A missing identity, cost, route distinction or sanctioned credential
stops MODEL-PIN and leaves PROVIDER blocked. The unverified cheaper tier is
also refused.

The integrator checks the two new task files with the executable governance
function, runs focused contract-prose tests and `git diff --check`, then
publishes a normal fast-forward to `origin/dev` only after re-reading its
predecessor. The exact remote read-back SHA is reported in the handoff.
