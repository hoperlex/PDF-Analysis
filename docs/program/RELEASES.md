# Product release ledger

Each row records one deployed and verified product release. The release
integration task fills it from the exact published SHA, image measurements,
full-gate log and host verification. No development candidate is entered as a
release.

| Tag | SHA | API `build_id` | Web `web_build_id` | `contract_version` | Migration head | Prompt bundle hash | Profile bundle hash | `GATE OK` evidence | Norms snapshot (from W55) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v0.4.0` | `2653dbf49e9f37fa891dd6e47b396650a215542d` | `be7bf8dae6d63d63c` | not measured (stand environment) | `1.0.0-draft.1` | `0017_execution_queue` | `934705c04a71…` | `30053740f569…` | none — waived by `R-87`; deploy run `38219064192` verified (`W53-INT-MAIN-01.md`) | — |
