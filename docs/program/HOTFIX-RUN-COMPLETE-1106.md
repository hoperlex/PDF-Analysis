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

## Observed follow-up: local stdin and validation outcomes

The first live repeat `run_01M6RCQC0B0VJ8MFM0S58A61A5` read all 86 passport pieces,
30 pages and 165373 characters. It retained 261 strictly validated facts, but five batches
were partial after grounding refusals. Its later visual task then failed locally after
529.3 seconds with zero CLI events and zero answer bytes. Provider ambiguity was retained;
the task was not blindly retried and the run remains an immutable failure.

Both runner layers polled `communicate(input=payload if first else None, timeout=0.2)`.
The installed Python implementation registers a remaining stdin write only when its
current `input` argument is nonempty; after the first timeout the remaining bytes could
be stranded and the child waited for EOF. Both layers now stage the entire input in a
private temporary file before launch. The wrapper uses `wait`, and the agent collects
stdout with `communicate` without an input argument. Deadlines/cancellation still apply.
The reviewed local scripts were installed atomically and the idle service was restarted.

Passport v3 separately freezes `candidate_refusals=reject-unsupported-v1`. A schema-valid
unsupported candidate can receive an explicit terminal validator rejection after its
bounded repair. It never enters accepted facts and never counts as model-repaired.
Completed execution requires all source pieces and all candidate outcomes accounted for;
it does not assert a complete expert passport. Malformed/truncated answers, transport
failures, unresolved records and missing source coverage still prevent completion.
Historical v1/v2 consent and artifacts keep their original outcomes.

Full normative context also preserves exact per-input excerpt variants of one paragraph,
preventing a false identity conflict in the critic. Operator diagnostics now expose
controlled refusal counts and avoid applying the local schema to global replies.
Product 0.12.3 gives the changed runner package its own version. Build and exact SHA/live
evidence for this follow-up are in the same external task receipt.


## Visible preparation and delivery follow-up (0.12.5 candidate)

The owner observed all seven procedure rows queued in run_01M6RFHQS62S01NXXCHX1CQDV4
while its passport was executing. Saves and polling worked, but its panel was inside
closed plan details. An open activity indicator now shows completed preparatory batches
and saved initial/repair responses above the actual seven procedure statuses. No procedure
is falsely marked running. Publication waits for the active run to finish.

A separate deployment of 0730b6179 interrupted delivery of that earlier run's ready answer:
local logs show HTTP 502 from 13:52 to 13:56 UTC and the 120-second submit budget exhausted.
The old result and unknown-effect fence remain immutable. The owner started
run_01M6RJPRWTC1ER59JXJZN2C76H; read-only snapshots run from dev independently of deployment
and never admit a new analysis or hold the production deployment lock.

The runner now keeps the same ready answer, occupied slot and claim extender until its
server deadline, definitive rejection/claim loss or shutdown. Backoff is bounded by the
remaining deadline and interruptible. It makes no extra model call. Answer storage remains
in memory: this fixes transient delivery outages, not process-restart recovery. A request
already in flight retains the client's existing 30-second HTTP timeout.

Production candidate starts at main 0730b6179, preserving its calendar and prior release
notes. Later unpublished dev API 1.34 changes are not part of this hotfix. The main-based
candidate is merged into dev, then its exact checked production SHA is published to main
after the live run is terminal. Version 0.12.5 identifies the updated runner package.
Only deployment buildability checks run under the owner's explicit exception.


## Critic-specific repair after run RJPR

RJPR completed all47blocks and covered all30textpages. Its firstwindow critic retained
one actual quote refusal after the one authorizedrepair (the same input failed twice;
8/9records accepted). Central read-only diagnostic42237751294 distinguishes this from
an invalid replacement of an originally valid row. Otherwindow repairs succeeded.
The generic repair instruction included corrector action enums for critic replies.
The fix supplies critic-schema uncertainty fields when exact quote evidence cannot be
confirmed, retaining each input/source binding and strict source validation. Corrector
action instructions are limited to the corrector. This is a valid machine request for
expert review, never an accepted invented quote or automatic expert decision.

core.py participates in rules_sha256, so a fresh estimate/consent is required; RJPR and
its saved refusals remain immutable. After its terminal state the deployment follow-up
uses the ordinary unmetered re-audit of RJPR. The diagnostics workflow has an independent
concurrency group: observation does not own the deployment lock. Release0.12.5revision3
contains these repairs only; unpublished dev features remain outside this candidate.
