# CMP-STAGE-AI-RETIRE-01 — retire obsolete pending units

Task: [`CMP-STAGE-AI-RETIRE-01`](tasks/CMP-STAGE-AI-RETIRE-01.md), base `ceb7b508`, migration0043. No shared erasure service, contract or migration changes.

`StageAiRepository.cancel_pending_units` changes only queued/running unit state and update time, in the caller transaction. Source payload, saved response progress, frozen job pins, completed/failed units and immutable answers remain intact. Runtime invokes it on expert cancellation even when the shared job is already terminal or absent, after creating a replacement generation, on terminal zero-call continuation and on fatal failure while preserving the current failed unit.

The internal cancel command key now binds both run and job generation. Cancelling again after terminal recovery therefore does not reuse the previous generation's command key with a different job fingerprint.

Focused checks: **75 owned unit tests passed**, **8 recorded recovery/retirement SQL cases passed**, compile/whitespace passed. SQL verifies zero obsolete queued/running units after cancel/recovery/failure, terminal and zero-call early-return cleanup, retained source/progress, completed control units unchanged, saved-reply reuse without another provider call and cancellation of a replacement generation. No full gate, broad suite or live provider ran.

Root consumes this local commit after recovery `ceb7b508`. Its existing erase accounting can now observe cancelled scheduling state instead of obsolete live units. All authored files stay in the task allowlist; frozen data, shared hotspots and remote refs are untouched.
