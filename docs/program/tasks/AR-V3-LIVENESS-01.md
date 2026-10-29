# Task AR-V3-LIVENESS-01 — a model call lives as long as its session shows signs of life

task_id: AR-V3-LIVENESS-01
status: dispatched 2026-10-29 (two lanes, A and B, on the owner's direct decisions below; the integrator holds the exception to AGENTS section 7.1 for this task)

## Outcome

On the live stand the AR v3 Runs through the `ssh_command` connection `kzSonnet` (Claude Code headless on the development server) were cut after exactly 780 s without an answer and ended `dependency_unavailable` (premise P-01). Every limit on the path is a single short wall-clock deadline (P-02), so a model that is thinking is indistinguishable from one that hangs. The owner's rule (2026-10-29): **do not limit the model's thinking; check that the session is alive and extend the limits automatically.** After this task a call through a heartbeat-capable SSH command may run until the **absolute ceiling of 2 hours**, and is cut only after **10 minutes without a sign of life**. Nothing caps the model's effort, thinking or turns.

## Owner decisions (direct poll, 2026-10-29)

- absolute ceiling of one live attempt: **2 hours** (`ATTEMPT_HARD_CAP_SECONDS = 7200`);
- silence window: **10 minutes** (`ATTEMPT_STALL_SECONDS = 600`);
- no interim stop-gap release: the full mechanism ships in one deploy;
- effort is not capped: the effort of the sealed request (`output_config.effort`, `high` for AR v3) is passed to the command; nothing else is set.

## Depends on

- `AR-V3-WIRE-SCHEMA-01`, `D-284` (the call now reaches the model), `R-146be`.
- The development-server wrapper `tools/executor-runner/claude_answer.py` is installed by hand at `/opt/pdf-analysis/claude_answer.py` (byte-identical to the repo file at the time of writing); the integrator installs the new one after merge.

## Frozen inputs

- domain contract: unchanged; API contract: `1.10.0`, `131` paths / `148` operations / `432` schemas, unchanged (no operation, schema or error code moves; the revision's `timeout_seconds` range `1..3600` stays as it is: with a heartbeat-capable command the revision's timeout does not bound the call, the stall window and the hard cap do)
- migration head: `0039_comparison_core`, unchanged
- base commit: `origin/dev` `1fc24881`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the integrator read the live failure, the limits and the stream format before the design

### P-01 — the three SSH sessions of the live host on the development server (every one cut at exactly 13:00)

- captured_at: 2026-10-29
- command: `for p in 3787860 3853254 3936851; do journalctl _PID=$p --no-pager | grep -E 'Accepted|session (opened|closed)' | sed -E 's/ adm1.hlab.kz sshd\[[0-9]+\]//' | cut -c1-110; done`
- captured_output:
  ```text
  Oct 29 15:35:26: Accepted publickey for root from 135.106.164.147 port 53706 ssh2: ED25519 SHA256:ktr3lFK/dCC5
  Oct 29 15:35:26: pam_unix(sshd:session): session opened for user root(uid=0) by root(uid=0)
  Oct 29 15:48:26: pam_unix(sshd:session): session closed for user root
  Oct 29 15:49:26: Accepted publickey for root from 135.106.164.147 port 50680 ssh2: ED25519 SHA256:ktr3lFK/dCC5
  Oct 29 15:49:26: pam_unix(sshd:session): session opened for user root(uid=0) by root(uid=0)
  Oct 29 16:02:26: pam_unix(sshd:session): session closed for user root
  Oct 29 16:03:28: Accepted publickey for root from 135.106.164.147 port 55076 ssh2: ED25519 SHA256:ktr3lFK/dCC5
  Oct 29 16:03:28: pam_unix(sshd:session): session opened for user root(uid=0) by root(uid=0)
  Oct 29 16:16:27: pam_unix(sshd:session): session closed for user root
  ```
- interpretation: the sessions of F1, F2 and A1 each lasted exactly 780 s and were closed from the worker's side (no «disconnected by user»), then the next Run began 60 s later; the command was alive and Claude Code was working (a tiny call through the same flags took 2.8 s). The worker cut the call: the call's timeout is the connection's cut to what is left of the 900 s Attempt watchdog minus a 60 s margin.

### P-02 — the limits on the path of one call

- captured_at: 2026-10-29
- command: `grep -n -E 'ATTEMPT_WATCHDOG_SECONDS =|DEADLINE_MARGIN_SECONDS|SSH_TIMEOUT_SECONDS =|monotonic\(\) - started >= ATTEMPT_WATCHDOG_SECONDS|STALE_AFTER_SECONDS: Final' src/auditmanager/jobs/lease.py src/auditmanager/executors/http_adapter.py tools/executor-runner/claude_answer.py src/auditmanager/jobs/temporaries.py`
- captured_output:
  ```text
  src/auditmanager/jobs/lease.py:21:ATTEMPT_WATCHDOG_SECONDS = 900
  src/auditmanager/jobs/lease.py:80:                    if monotonic() - started >= ATTEMPT_WATCHDOG_SECONDS:
  src/auditmanager/executors/http_adapter.py:53:    "DEADLINE_MARGIN_SECONDS",
  src/auditmanager/executors/http_adapter.py:65:DEADLINE_MARGIN_SECONDS: Final[int] = 60
  src/auditmanager/executors/http_adapter.py:85:    revision_timeout_seconds: int, context: Any | None, *, margin: int = DEADLINE_MARGIN_SECONDS
  tools/executor-runner/claude_answer.py:40:SSH_TIMEOUT_SECONDS = 840  # below the stand's 900 s Attempt watchdog
  src/auditmanager/jobs/temporaries.py:73:STALE_AFTER_SECONDS: Final[float] = float(ATTEMPT_WATCHDOG_SECONDS + 60)
  ```
- interpretation: the Attempt watchdog is a fixed `900` counted from the claim, the heartbeat thread fences the Attempt at it, the call's timeout is cut to what remains of it, the temporary-file sweep keys off it, and the command's own deadline is `840`. Nothing reads a sign of life.

### P-03 — what Claude Code streams (version 2.1.310, flags as the command passes them plus `--output-format stream-json --verbose --include-partial-messages`)

- captured_at: 2026-10-29
- command: `printf '%s' '{"system":"Return the JSON object {\"ok\": true}.","user_text":"ping"}' | /root/.local/bin/claude -p --output-format stream-json --verbose --include-partial-messages --model claude-sonnet-5 --tools '' --strict-mcp-config --no-session-persistence --disable-slash-commands --setting-sources '' --system-prompt 'Return only the JSON object required by the output schema.' --json-schema '{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"],"additionalProperties":false}' | python3 -c "import sys,json;from collections import Counter;r=[json.loads(l) for l in sys.stdin if l.strip()];print(sorted(Counter((x['type'],x.get('subtype') or (x.get('event') or {}).get('type')) for x in r).items(), key=str));l=r[-1];print(l['type'],l['subtype'],l['is_error'],l['terminal_reason'],'structured_output' in l,'modelUsage' in l,'permission_denials' in l)"`
- captured_output:
  ```text
  [(('assistant', None), 2), (('rate_limit_event', None), 1), (('result', 'success'), 1), (('stream_event', 'content_block_delta'), 7), (('stream_event', 'content_block_start'), 2), (('stream_event', 'content_block_stop'), 2), (('stream_event', 'message_delta'), 1), (('stream_event', 'message_start'), 1), (('stream_event', 'message_stop'), 1), (('system', 'init'), 1), (('system', 'status'), 1), (('system', 'thinking_tokens'), 3), (('user', None), 1)]
  result success False completed True True True
  ```
- interpretation: the output is newline-delimited JSON; while the model generates (thinking included) `stream_event` lines (`content_block_delta` and others) arrive continuously, and the last line is the `result` object with the same keys the command reads today (`is_error`, `subtype`, `terminal_reason`, `permission_denials`, `modelUsage`, `structured_output`). A `rate_limit_event` line can appear too. Every line is a sign of life.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## The frozen interface between the two lanes

**Heartbeat line** (written by the command to **stderr**, one per `HEARTBEAT_SECONDS = 30` while it runs in `--ssh-envelope` mode, and once at the start): exactly
`pdf-analysis-forced-command: hb <elapsed_seconds> <events> <output_tokens>` with three non-negative decimal integers and nothing else; the stand recognises a sign of life only by the regular expression `^pdf-analysis-forced-command: hb [0-9]+ [0-9]+ [0-9]+$` on a whole stderr line. Never any task text, schema text, key or model output in it.

**`jobs/lease.py`** (lane B):
```python
ATTEMPT_WATCHDOG_SECONDS = 900          # unchanged: the deadline of an attempt that never shows a sign of life
ATTEMPT_HARD_CAP_SECONDS = 7200         # absolute ceiling of a LIVE attempt
ATTEMPT_STALL_SECONDS = 600             # silence window of a LIVE attempt
class AttemptContext:                   # existing fields and defaults keep their meaning; added:
    def progress(self, now: float | None = None) -> None   # records a sign of life; the first call makes the attempt live
    @property
    def live(self) -> bool
    def remaining_seconds(self, now=None) -> float   # not live: watchdog_seconds - elapsed (today); live: min(hard_cap - elapsed, stall - (now - last_progress)); never negative
    def hard_remaining_seconds(self, now=None) -> float  # hard_cap - elapsed; never negative
```
The heartbeat thread fences the Attempt when `context.remaining_seconds() <= 0` (it used the fixed 900).

**`executors/ssh_transport.run_command`** (lane B): new optional keyword parameters `live_hard_cap_s: float | None = None`, `live_stall_s: float | None = None`, `on_signal: Callable[[], None] | None = None`. Until the first recognised heartbeat line the call behaves exactly as today (`timeout_s` bounds it). When the first recognised line arrives and `live_hard_cap_s` is set, the deadline becomes `live_hard_cap_s` from the start of the call, silence longer than `live_stall_s` since the last recognised line ends the call as a **stall**, and every recognised line calls `on_signal()` (at most once per second). A stall and the hard cap are failures with `sent=True` (an uncertain effect, as a timeout is today) and distinct reasons.

## Lane A — the command (`AR-V3-LIVENESS-WRAPPER-01`)

Allowed paths: `tools/executor-runner/claude_answer.py`, `tools/executor-runner/README.md`, `tests/unit/executor_runner/**`, `tests/unit/executors/test_claude_answer_envelope.py`.

Deliverables:
1. `_run` reads Claude Code's **stream-json** (`--output-format stream-json --verbose --include-partial-messages`) from the temp file incrementally; the final `result` line is the report the existing `_report` checks accept (same checks, same errors); a stream without a `result` line, or a `result` that fails the checks, is the same `TaskError` family as today (add `claude_no_result`).
2. In `--ssh-envelope` mode: heartbeat lines to stderr as frozen above (first at start, then every 30 s while the process runs); `<events>` = lines read so far, `<output_tokens>` = the latest `usage.output_tokens` seen in a `message_delta` or `0`.
3. Own limits in SSH mode: **stall** = no new stream byte for `STALL_SECONDS = 600` -> `TaskError("claude_stalled")`; **hard cap** `SSH_HARD_CAP_SECONDS = 7140` (60 s below the stand's 7200) -> `TaskError("claude_timeout")`. The pull-mode path keeps `TIMEOUT_SECONDS = 510` and has no heartbeat. The old `SSH_TIMEOUT_SECONDS = 840` is removed.
4. The task may carry an optional string `effort` in `low medium high xhigh max`; when present it is passed as `--effort <value>`; any other value is `TaskError("invalid_effort")`; absent -> **no** `--effort` flag (the CLI default). The command sets no thinking cap, no turn cap and no `--max-budget-usd`.
5. The stream file may be large (partial thinking deltas): cap it at 64 MiB (`MAX_STREAM_BYTES`), the final `result` at the existing 8 MiB.
6. Tests with a fake `claude` that writes NDJSON over time (use tiny module-constant overrides for the stall, hard cap and heartbeat period): heartbeat lines appear on stderr with the exact format and contain no task text; a fake that streams slowly for longer than the old 840 s equivalent is NOT cut; a silent fake is cut as `claude_stalled`; the hard cap cuts a fake that streams forever; effort passthrough and `invalid_effort`; the final-result checks (model mismatch, tool denied, error turn) still refuse; the existing envelope test still passes against the new stream.
7. Mutation table in the report (heartbeat off, stall off, hard cap off, effort ignored, `result` checks weakened -> each red).

## Lane B — the stand (`AR-V3-LIVENESS-STAND-01`)

Allowed paths: `src/auditmanager/jobs/lease.py`, `src/auditmanager/jobs/temporaries.py`, `src/auditmanager/workers/service.py`, `src/auditmanager/executors/ssh_transport.py`, `src/auditmanager/executors/ssh_adapter.py`, `src/auditmanager/executors/http_adapter.py` (only `effective_timeout` if needed), `tests/unit/jobs/**`, `tests/unit/workers/**`, `tests/unit/executors/**` except `test_claude_answer_envelope.py`, `tests/integration/jobs/**`, `tests/integration/workers/**`, `tests/integration/executors/**`.

Deliverables:
1. `jobs/lease.py` as frozen above; the heartbeat thread uses `remaining_seconds()`.
2. `jobs/temporaries.py` `STALE_AFTER_SECONDS` and `workers/service.py` margin key off `ATTEMPT_HARD_CAP_SECONDS` (a live attempt may now hold temporary files for up to 2 h and must not have them swept); tests updated with the reason.
3. `ssh_transport.run_command` per the frozen interface: read stderr incrementally, recognise heartbeat lines only by the regex, scrub as today, no heartbeat text kept beyond what scrubbed stderr already keeps; stdout size cap unchanged.
4. `ssh_adapter`: pass `effort` from `body["output_config"]["effort"]` into the task when it is a string (otherwise omit it); call the transport with `live_hard_cap_s = max(0, context.hard_remaining_seconds() - DEADLINE_MARGIN_SECONDS)`, `live_stall_s = ATTEMPT_STALL_SECONDS`, `on_signal = context.progress` (no context -> no live parameters, today's behaviour); a stall and a hard-cap cut map to `ProxyDispatchError(DEPENDENCY_UNAVAILABLE, dispatch_class` as a timeout does today with `sent=True`, with details naming the reason `stalled` or `hard_cap`).
5. Tests: the Attempt context (not live: today's numbers; live: the min rule; progress extends it past 900 s; hard cap; stall) on a fake clock; the heartbeat thread fences a stalled live attempt and a hard-capped one and NOT a silent non-live attempt before 900 s, NOT a live attempt that keeps signalling past 900 s; the transport with a fake `ssh` that prints heartbeat lines on a schedule (extension past `timeout_s`, stall cut, hard-cap cut, lines that do not match the regex are not signs of life, a command that never signals is cut at `timeout_s` as today); the adapter passes effort and the live parameters; the sweep threshold.
6. `comparison/work/model.py` keeps its own `900.0` (the comparison module's mirror); if a guard test demands the two be equal, STOP and report.
7. Mutation table (each of: progress not recorded, stall off, hard cap off, regex loosened to any stderr byte, non-live path changed, sweep threshold left at the old value -> red).

## Forbidden hotspots (both lanes)

`contracts/**`, `db/migrations/**`, root dependency/lock files, `src/auditmanager/bootstrap/**`, `src/auditmanager/comparison/**`, `src/auditmanager/runs/**`, `src/auditmanager/analysis/**`, `web/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the rulings, ADRs, and the other lane's files.

## Non-goals

- a cap on thinking, effort or turns; an automatic effort choice; a UI for the signs of life; a change of the connection's `timeout_seconds` range; the HTTP/proxy path (it cannot stream: the proxy refuses `stream`); the pull channel; a live call.

## Required tests

- lane A: `BS=$(ls -d /root/projects/PDF-Analysis/.local/worktrees/cmp-seal-c0/.venv/bootstrap/lib/python3*/site-packages); PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.local/worktrees/cmp-seal-c0/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/executor_runner tests/unit/executors tests/contract/program`
- lane B: the same with `tests/unit/jobs tests/unit/workers tests/unit/executors tests/contract/program`; DB tests are not run by the lanes (the integrator runs `tests/integration/{jobs,workers,executors,runs}` on the merged tree).
- expected: all pass; `tests/unit/executors/test_runner_long_poll_cap.py` is a known flake (`D-254`).

## Integration contract

The integrator can rely on: (1) a call through a heartbeat-capable command lives until 2 h or 10 min of silence; (2) an attempt whose adapter never signals behaves exactly as before (900 s); (3) the old command (no heartbeat) keeps working against the new stand and the new command against the old stand (stderr lines are ignored there); (4) no log, journal row or error gains task text; (5) the sealed request, `request_sha256` and every digest are unchanged.

## Rollback / feature-flag policy

Not a flag. Reverting the stand commit restores the fixed 900 s; the command can be restored from `/opt/pdf-analysis/claude_answer.py.bak-*`.

## Handoff

Each lane returns: changed files, commands run with results, the mutation table, new constants, known limits. The integrator writes the report document from the two hand-backs (a lane cannot create `.md` files).
