# CMP-C2-GOV-01 — C2 task-record governance correction

The first complete gate on `adcac54f` passed frontend lint/typecheck and all 3651 Vitest tests, then stopped at `tests/contract/program/test_wave_governance.py`: 1309 contract tests passed and one rejected the new task records.

The repair gives the existing premise outputs fenced `text` blocks, as the executable task template requires, and writes `development_target: none` as a closed value in `CMP-C2-FIX-01`. The recorded API numbers, commit IDs, remote refs, task ownership and publication policy did not change. `CMP-WAVE-C2-INT` still alone owns `origin/dev`; no task owns `origin/main`.

Checks: `tests/contract/program/test_wave_governance.py` — **16 passed**; `git diff --check` — clean. The frozen API remains `1.11.0` (176 paths, 198 operations, 517 schemas), migration head `0040_comparison_ai_reports`. No runtime code, contract, migration, dependency, web, infrastructure or remote ref was changed.

Integrator: commit this documentation correction, then rerun the complete `make gate` on the next clean SHA. The earlier gate is not an acceptance result because it stopped before foundation and backend battery.
