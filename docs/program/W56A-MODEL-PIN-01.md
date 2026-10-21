# W56A-MODEL-PIN-01 — preflight after the proxy client guide

**Status: STOP before any new paid request.** The task remains the sole
prospective writer of `P02_LOCK.json`; no name is pinned here.

The owner supplied the `connect-proxy-llm` client guide. It identifies the
agent endpoint as `/agent/v1/chat/completions` and explains that client
policy A ignores an explicit `model`, using its default instead. This is a
plausible explanation for the immutable failed stand probe in
`W56A-PROBE-01`: that probe requested `anthropic/claude-opus-5` but received
`meta/muse-spark-1.3-contributor` at a different rate. The guide does not
prove which policy the stand client currently has. A model-list response is
not evidence of explicit model selection on this proxy; the earlier catalog
inference is withdrawn. The failed paid response remains failed evidence.

The known stand configuration selects the `proxy` placeholder. It cannot
satisfy the selected-model call until it names the locked concrete model and
the client policy permits explicit selection. The guide also identifies a
portal `/api/v1/chat/completions` route. A no-token, no-body reachability
check from this environment returned 200 for `/healthz` and 401 for both
the portal and agent completion paths. Authentication therefore answered
on both paths without an LLM call. The portal route is a candidate for the
recording role, but no working recording credential/model configuration or
operator designation for that role was found. The local `provider.env` has
no URL host and selects a namespaced stub; it is not usable for a paid pin.
Reachability alone does not establish the distinct configured gateway
required by `W56-PLAN.md` §A3.5 and `R-136`.

The exact preflight needed for each role is: a route distinct from the other
role, a credential present in its own protected configuration, a concrete
configured model, and operator configuration evidence that the client policy
permits that model.
The paid proof remains one explicit and one default call per role, with
matching selected names and the pinned $5/$25 per million-token rate within
the task's fixed tolerance. Only two role PASS results permit the lock edit.
The proxy operator may need to change `allowedModels` to `['*']` or an exact
allowlist containing the locked slug and restart its service; this report
does not authorise or perform that change. A default that is the selected
model would also fail the task's distinct-default check.

No authenticated LLM request, charge, recording or configuration change was made. The
spend ledger remains at $0.0000046 actual and $4.9999954 remaining by its
existing record. No contract, migration, provider lock, product code,
credential, deployment file, `CURRENT_STATE.md`, tag or `origin/main` ref
changed. This report and its task clarification are the only changed paths.
Direct governance inspection of this task returned no findings, and
`git diff --check` passed. The focused governance file had 15 passes and
one failure in its repository-wide task enumeration: six older task files
still lack required sections; this edit does not own those files. No full
local gate or acceptance was run. Rollback is a revert of these two
documents; the historical probe and spend record remain intact.

Integrator handoff: keep PROVIDER/live activation blocked. Once the
independent recording route and both model-selection policies are verifiable,
run the budgeted four-call sequence from a fresh `origin/dev` SHA and amend
this report with sanitized measurements. Do not treat this preflight as a
MODEL-PIN PASS.
