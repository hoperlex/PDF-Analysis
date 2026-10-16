# Product release ledger

Each row records one deployed and verified product release. The release
integration task fills it from the exact published SHA, image measurements,
full-gate log and host verification. No development candidate is entered as a
release.

| Tag | SHA | API `build_id` | Web `web_build_id` | `contract_version` | Migration head | Prompt bundle hash | Profile bundle hash | `GATE OK` evidence | Norms snapshot (from W55) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v0.4.0` | `2653dbf49e9f37fa891dd6e47b396650a215542d` | `be7bf8dae6d63d63c` | not measured (stand environment) | `1.0.0-draft.1` | `0017_execution_queue` | `934705c04a71…` | `30053740f569…` | none — waived by `R-87`; deploy run `38219064192` verified (`W53-INT-MAIN-01.md`) | — |
| `v0.5.0` | `23fd729dbb06c642be0588017f6b195305e2e53e` | `bf9407822414591b3` | not measured (stand environment) | `1.0.0-draft.1` | `0020_norms_search` | `934705c04a71…` | `30053740f569…` | `W55A-INT-GATE-01.md` (GATE OK on this SHA); deploy run `38356461757` | — |
| `v0.6.0` | `37393a979a430e490843d7f410e9eca9491a4ea1` | `bf03d913bde596a77` (computed from tagged tree) | not measured (stand environment) | `1.0.0-draft.1` | `0021_portal_bundles` | `934705c04a71…` | `30053740f569…` | `W55B-INT-MAIN-PREP-03.md` (R-125 same-SHA gate completion); deploy run `38897018419`, owner-run host verification in `W55B-INT-MAIN-VERIFY-ADDENDUM-01.md`; five live checks waived in `W55B-INT-TAG-01.md` | — (not promoted) |
