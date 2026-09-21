# W30-CERT3 — PA-01 re-certified at `ac7c348`

Opened before the first measurement, as this programme requires.

- **Task:** `W30-CERT3`. Re-certify `PA-01` against the tree at `ac7c348`.
- **Supersedes:** `artifacts/checkpoints/PA-01/certification-16d3503.json`, taken at `16d3503`.
- **Worktree:** `/root/w30cert3`, branch `agent/w30-cert3`, head on arrival `ac7c348`.
- **Logs:** `/root/w30-logs/cert3-*`.

Sections are filled as each criterion is driven. Nothing below is written before it is measured.

## Interim record — drives completed before criterion 10

Committed mid-session so a session that dies does not lose the readings. Logs under
`/root/w30-logs/cert3-*`; browser journals under `/root/w30-logs/cert3-browser/`.

- Criterion 1, second clause: served schema over HTTP at `http://127.0.0.1:31500/api/v1/openapi.json`, frozen ops 15, served ops 15, **0 differences**; planted difference reddens it.
- Criterion 2, second clause: 15 of 15 declared operations answer `401 authentication_required` on both an absent and a wrong credential, typed envelope, and the identical refusal is reached with the proxy bypassed inside the api container.
- Criterion 3: `ver_01M31YAQJX25F716A74946A6TC`, sha256 matches the fixture and the bytes served back; anonymous LIST/GET on the bucket = 403 AccessDenied.
- Criteria 4-7: live journey `run_01M31YAXCQ0BWPFPJFTR9HCCRA` on the owner's stand; published, provider mode live, cost 0.037675 measured, 3 findings, three decisions in history, CSV 17 columns / BOM / 6 CRLF / 0 bare LF.
- Criterion 4 UI states, on this session's own stack: queued, running, published, partial, failed all read from `[data-run-state]`.
- Criterion 9: five typed refusals through HTTP, five distinct constraints, no version left behind; a real provider outage fails the run with `dependency_unavailable` after the retry ladder.
- Criterion 8: census before and after every container was destroyed and recreated — **identical, byte for byte**; five screens load 200 cold.
