# W56A-INT-PROBE-STUB-CORR-01 — namespaced stub refusal addendum

The prior `W56A-INT-PROBE-TOOL-CORR-01` rejected bare `stub`, `proxy`,
`default`, `auto`, `unknown`, `none`, `null` and `model` names. The local
host-owned configuration uses a `stub/...` selector, which the prior regular
expression accepted as a concrete name. A sanitized shape check returned
`stub_prefix=True`; no route or token was printed.

`identity_probe._name` now rejects the `stub/` namespace, so a selected
`stub/...` configuration fails before network use and a `stub/...` default
response cannot satisfy MODEL-PIN. All other explicit identity/rate and
default checks remain as published. The change is confined to the probe
tool; it does not edit the product adapter or the model lock.

Checks: 17 focused probe tests passed (including pre-network refusal and
default-response refusal for `stub/w37cert4`); compilation passed; direct
governance findings for this and the refreshed MODEL-PIN task were empty;
`git diff --check` and exact changed-path proof passed. No paid call, full
local gate, service acceptance or `origin/main` publication was run.

Changed paths: `tools/provider/identity_probe.py`, its focused test,
`tasks/W56A-MODEL-PIN-01.md` (base/dependency), this task/report and the
top of `CURRENT_STATE.md`. No contracts, migrations, provider lock,
application runtime, dependencies, composition root, global styles,
recordings, stand files, `VERSION` or release ref changed.

MODEL-PIN remains blocked by gateway evidence: the available stand config
still selects a stub, its known catalog does not expose the locked Opus
model, and the distinct recording route has not been identified. A correct
stand route and a separate recording route are required before the four
budgeted calls; a 200 response from the old route does not lift the stop.
Rollback is a revert of this additive correction before paid calls; after
the tool is used, correct forward and retain the resulting spend record.
