# W55A-JUDGE-X — adversarial review of W55a (static)

**Reviewer:** a fresh-context subagent of the integrator, 2026-10-13.
**Subject:** `9c635ee`; W55a range `2122cee..9c635ee`.
**Verdict: ACCEPT-WITH-FIXES.** No blocker and no major finding.

## Findings

| # | Severity | Finding | Where | Fix |
| --- | --- | --- | --- | --- |
| M1 | Minor, confirmed | A forged cursor answers `500 internal_error`. An `s1d` ordinal of 2³¹ fails the `integer` cast with 22003 (`DataError`, which is not mapped). An `n1`/`e1` instant at year 1 with a positive offset raises `OverflowError` in `astimezone`. The cursor binding is an unkeyed SHA-256, so anyone can mint one. | `norms/search/cursor.py:100-103, 194-208`, `service.py:280` | Bound the ordinal to ≤ 2³¹−1, catch `OverflowError`, test both forged tokens; optionally make the binding an HMAC |
| M2 | Minor, plausible | A NUL in `q` reaches psycopg, raises `DataError` and answers 500. | `norms/search/service.py:322-335`, `api/routers/norms.py:65` | Refuse control characters in `q` with `422 q/format` |
| M3 | Minor, confirmed | A `Range` number longer than 4300 digits raises `ValueError` from `int()` and answers 500. | `api/schemas/content.py:73` | Bound the digits in `_RANGE` (`\d{0,19}`), or map `ValueError` to `format` |
| M4 | Minor, confirmed (direct SQL only) | The history guard does not prove the event is new: an older event with the same from/to can be reused. `TRUNCATE` skips the row triggers, and `changed_at` can be backdated. The application path is correct. | `db/migrations/versions/20261012_0020_norms_search.py:192-210` | Require `NEW.event_id` to be the newest event and unreferenced; add `BEFORE TRUNCATE` refusals; optionally refuse an explicit `changed_at` |
| M5 | Minor, confirmed | A whitespace-only `q` runs an unfiltered sort of the whole snapshot. | `norms/search/query.py:148`, `service.py:254-291` | Refuse an empty parse with `422 q/format` |
| M6 | Minor, plausible | Search shares the API's 10-connection pool, so ten broad searches can hold every connection for the full timeout. | `shared/db/config.py:40-44`, `bootstrap/composition.py:285` | Cap concurrent searches, or accept and register the risk with the timeout figure |

## Refuted

- SQL injection: everything is bound, and the f-strings insert constant fragments only.
- Moving a cursor to another query or snapshot.
- Bypassing the window cap or the timeout.
- An existence oracle for never-current snapshots.
- Role gaps on any of the seven operations.
- Content readable without a session or without a binding.
- Range edge cases: multi-range, reversed, past the end, unknown id, a store that ignores `Range`.
- The held-back last chunk does withhold the bytes at the ASGI layer.
- Header injection; error-detail leaks.
- XSS on «Нормы»: no `dangerouslySetInnerHTML`; React text nodes; markers stripped.

## Notes

- A `206` is never hashed (`R-115`). The product viewer always does a full `200` fetch.
- Qualification is checked only at designation. A build deleted afterwards leaves the current snapshot unqualified (handed to JUDGE-Y).

## Needs a live stand

- M2: a 500 or truncation?
- M6: pool starvation under the rehearsal timeout.
- The short body end to end through nginx, the BFF and the browser.
- Next.js keeping a forwarded `content-length` on a streamed response.
- M1's 22003 arriving as an envelope.
