# HOTFIX-RUN-PARTIAL-1106 — release handoff

Owner instruction, 2026-11-06: repair the diagnosed partial Run, remove response-size
limits and UI mentions, publish through `origin/dev` to `origin/main`, and check only
deployment buildability. The exact candidate is the commit carrying this record plus
its generated-client seal metadata successor. No tests, standalone lint/typecheck,
model calls or complete gate were run.

## Result

- Parameter extraction validates each fact independently with unchanged source, literal,
  offset and number-sign checks. Correct facts and explicit rejected-fact receipts survive;
  a received bad reply does not prevent independently sourced later batches.
- Posttext analysis carries every saved visual window before processing the next window.
  A later unknown provider outcome stops only unfinished procedures; earlier observations,
  sources and visual coverage remain in the final result. No unknown-outcome retry is added.
- Window progress counts successful windows separately from failed, partial and skipped
  windows. The UI explains executor/quotation failures and rejected parameter records.
- Codex loses its independent 510-second cutoff and the 8 MiB event/answer ceiling. The
  command agent can use its clock-adjusted server task deadline (`timeout_seconds=0`),
  preserving a safe timeout classifier and payload-free diagnostic metadata.
- The runner's answer POST loses its 1 MiB client-body ceiling and the server's one-million
  character constraint. The local endpoint no longer sends a configured output-token cap.
  Codex's pull payload already sends no output-token cap; 16k/64k response promises and
  response ceilings are removed from the start/cost UI. Input/image/schema checks remain.
- Contract 1.33.0 reseals the shared API/analysis/event version and generated consumers.
  No path, operation, schema count, error code, migration or dependency changes.

## Build evidence

Integrated dev base: `ce08af3d20e2efdc6ee21d35317b097f7fdfb35d`; initial main:
`5e95269fa89886e1f4242aae8fef745c96a9ee59`.

- `NODE_OPTIONS=--max-old-space-size=2048 npm --prefix web run build` — passed,
  including Next's production type-validation and static page generation. Log:
  `/tmp/hotfix-run-partial-1106/web-build.log`. Old literal seal consumers discovered by
  the first build were synchronized before the successful final build.
- Python 3.12 `compileall` of `src` and `tools/executor-runner`, then imports of the changed
  API schemas, Run workflows and pull adapter — passed (`BACKEND BUILD OK`).
- `python3 tools/executor-runner/package.py --version 0.12.1 --out
  /tmp/hotfix-run-partial-1106/agent-package` — passed; this is the API image's package
  build step. Agent package SHA-256:
  `2adaaaaf65d8fbcef642d7d6f3fd68eb169ab7eb1f5ad748cae40e978ce99ec3`.
- `git diff --check` — passed. Full behavioral suites and live-model acceptance are
  intentionally unverified under the owner's fast-hotfix instruction.

The package digest above is diagnostic; the generated image always rebuilds its package
from the exact published source. The release task's candidate verification log records
the definitive final package digest when a source revision changes it.

## Publication and local agent

The integrator rechecks both remote refs, requires a clean fast-forward candidate and
publishes dev before main. The deployment workflow must succeed for that same SHA and
print its deployed-tree verifier/`DEPLOY OK`; a push alone is not deployment evidence.
The run/workflow IDs and final verification are recorded in the local release receipt.

The local runner is a separate installation in `/opt/pdf-analysis-codex-prod`, not the
API container. Its prepared install replaces the three changed runner scripts, supplies
the required unchanged `detect.py` and `VERSION`, sets command timeout to zero and
identifies the existing official CLI directory for health reporting. Credentials remain
unchanged. Automatic approval review requested explicit owner authorization before that
local systemd/configuration change; no local files or service were changed by the refused
attempt. Keep this distinction in the final delivery report.

Original Run evidence is immutable and no document rerun is started by this hotfix.
Rollback is a forward revert and deployment of this task, with the local script/config
backup available if the separately authorized runner installation needs reverting.
