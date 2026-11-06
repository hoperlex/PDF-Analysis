# HOTFIX-RUN-COMPLETE-1106

The supplied run `run_01M6R76M73Z8QKGJCN4D623PKB` was partial after all 30 local
Codex calls returned and their answers were accepted by the transport. The application
then refused one visual reply and one correction, selected only 8/86 passport pieces
and completed 8/719 eligible global pairs. Norm queries were absent even for explicit
standard designations. Aggregated dependency reasons hid the original refusal; report
generation retained a stale dependency reason after reaching completed.

Fresh consent now names source-complete processing: all passport pieces and all indexed
cross-window piece pairs, packed into bounded requests. Fixed historical limits remain
on historical consent. All actual calls retain monetary, cancellation and unknown-effect
fences. A received invalid reply can receive one separately journalled semantic repair;
original refusals and accepted records survive, and repaired records pass the same strict
source/quote/number validators. An unresolved refusal still prevents complete coverage.

Norm query planning records exact literal provenance, searches actual designations or
explicit normative claims, and distinguishes a valid negative lookup or no normative
question from an unavailable search. Neither is labelled a verified norm. Critic and
corrector requests in the new policy provide the whole selected text context within
the existing request-byte bound. A valid needs-context recommendation remains expert
advice; unread context and invalid proposals still make execution partial.

The host operator CLI prints only allowlisted IDs, hashes, counts and status/error codes.
It is not an HTTP endpoint. Its explicit re-audit command reuses the configured application
port and ordinary command/queue, requires a fresh unmetered estimate and a zero monetary
ceiling, and refuses all metered routes. The manual workflow uses the already pinned
deployment host and protected SSH secret. Diagnostics do not print document/model text.

Build evidence on this candidate's source tree:

- `NODE_OPTIONS=--max-old-space-size=2048 npm --prefix web run build`: exit 0, production
  bundle, type validity and prerendering complete; log `/tmp/hotfix-run-complete-1106-web-build.log`.
- Python 3.12 compileall of affected analysis/runs/composition modules: exit 0; imports of
  bootstrap, extended review, parameter worker, preflight and operator: `BACKEND BUILD OK`.
- Runner package 0.12.2: built, SHA256
  `380332f32608ddfe6d7d4e584f4160a71baf426edcd50aa3edfb71a8e860b82a`.
- `git diff --check`: clean. No behavioral suites, full gate or model calls were run as
  part of build verification, under the owner's explicit build-only instruction.

API 1.33.0, migrations and dependencies are unchanged. The only owned composition change
exposes the existing run adapter to host commands; no provider/model is rewired. Latest
dev/main changes were merged without dropping their release notes. Release 0.12.2 revision 2
includes this repair and the separately authored PDF word-spacing fix.

Publication/deployment/live-run evidence is recorded against the exact committed SHA in
`.local/handoff/HOTFIX-RUN-COMPLETE-1106-receipt.md`. Build success alone is not evidence
of a complete live run. Old partial results are never rewritten. Rollback is a forward
revert; no migration or tag is involved.
