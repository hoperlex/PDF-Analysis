# Wave 13 closure: the twelve operations serve HTTP, under the framework the ADR named

Written 2026-09-18 by the integrator. **`make gate` → `GATE OK`, exit 0.**

Five streams, one of which I ran myself. The programme had certified the same prototype four
times through an in-process router and had never served one HTTP request under the framework
`ADR-0002` names. That is now a transport, a contract and a conformance gate.

## 1. The result

**All 33 response-baseline records reproduce byte for byte** — status, every header, every
body byte — and no record's `response` section changed. The conformance comparison reports
**0 differences** between the frozen document and `app.openapi()`: 10 paths, 12 operations,
exactly the 43 schema names.

| Stage | Stream | Outcome |
|---|---|---|
| 0 | integrator | six pins, licences read from wheel METADATA, `uv.lock` regenerated |
| 0b | `W13-SEAL` | `bearerAuth` at the document root; `dependency_credential_refused`, the 21st code |
| 1 | `W13-BASE` | 33 records, the comparison shown able to fail |
| 2 | `W13-API` | the rewrite; ~1 800 lines replaced |
| 3 | `W13-CONF` | the conformance gate, 9 declared normalizations |
| — | `W13-ORD` | the baseline's order flake, measured over 191 journeys |

## 2. What the rewrite found that four certifications did not

Driving every case of the retired multipart reader through FastAPI:

- a `multipart/form-data` with **no boundary** → 500 `internal_error`;
- a part with **no name** → 500 `internal_error`;
- **`file` sent twice** → silently accepted, the second one published.

All three now answer 422 naming their rule. **Every one of these is on criterion 10's
surface**, and every one survived four certifications, because all four drove the router in
process where a malformed multipart envelope cannot be constructed.

## 3. The finding worth more than the three defects

`W13-API` believed Starlette mojibaked non-ASCII titles and wrote a latin-1 round trip to fix
it. **Mutating that function away reddened nothing** — which sent it back to look, and the
recovery was itself the defect: `"coûts"` is valid UTF-8, round-trips to bytes that are not,
and was therefore *refused*. Most titles in French, German or Spanish.

A session that trusted its own green would have shipped a refusal of half of Europe's
alphabets. The mutation discipline caught a bug in the fix, not in the code.

## 4. Six corrections to my own briefs, and one changes how the programme measures

- **`pytest-randomly` is not installed and is not in `uv.lock`.** I diagnosed three baseline
  failures as order-dependence from that plugin, leaned on it four times including in a
  brief's method, and `-p no:randomly` was a no-op. The real difference was **two samples of a
  5.6 % coin.** A session following me would have spent its time re-ordering tests.
- **I quoted my own struck-through text.** The M2 line — "dropping the tiebreaker makes the
  order unspecified rather than wrong" — sits inside `~~…~~` in `W3_CLOSURE.md` under "Wrong,
  and wrong in a way worth naming". `W5-ADV` reddened M2 and **I wrote that correction
  myself** in wave 9. Read straight, the standing position argues for the opposite repair.
- **I merged the reseal and did not push it**, then told stage 2 to cut from `origin/dev`. It
  caught the mismatch in ninety seconds and reset before writing a model.
- **I reported a gate green that had failed** — `make gate | tail -3` returns `tail`'s exit
  code, not `make`'s. The failure was environmental (each worktree has its own `.venv`), but
  the reading was not.
- **"21 coupled test files" was right by the wrong query**, and the right query returns a
  *different* set of 21, three of which my grep missed and all three needed work.
- **"639 kept, 1 872 replaced" undercounted the kept side**: the view dataclasses are the
  ports' declared return types. Measured: 2 511 → 3 655.

## 5. And one correction of theirs that was wrong

`W13-API` reported that `make gate` has no changed-during-the-run check, having grepped
`Makefile`, `scripts/` and `tools/`. **It exists**, at
`tests/integration/foundation/conftest.py:542`, `checkout_is_unchanged`, comparing
`git status --porcelain` before and after — which is why two other streams hit it.

Recorded because it is `OPERATING_CONSTRAINTS.md` §12 in its purest form: **a query scoped
away from its subject returns zero and reads as proof of absence.** Three sessions and I have
now each produced one this wave.

## 6. What `W13-ORD` established, and how

The baseline's order flake was real: `finding_uid` is a fresh ULID and
`shared/identity/ulid.py` says in terms that monotonicity inside one millisecond is
**deliberately** not promised. Measured over **191 journeys**: the second and third findings
tie 26 times, **12 of those 26 flipped** — a 46 % coin — and 12 of 191 journeys came back
permuted.

It pinned **the rule the system promises** (strictly ascending `finding_uid` under
`COLLATE "C"`) rather than the order, and numbered finding tokens by **document order**
instead of response position, without which no order-insensitive comparison is possible at
all. No captured byte moved, and the by-hand perturbation gives 6 failures against the
original 5: the record is **more** watched.

It also declined to call five green battery runs proof — they exclude a 5.6 % flake with
probability ≈25 % — and offered a 150-journey A/B instead.

## 7. Owed to wave 14, and one of them is load-bearing

- **`AUDITMANAGER_API_TOKEN` has no configuration channel.** `T-6` reads it fail-closed from
  the environ `create_app` already carries, but `.env.example` and `AppSettings` were outside
  stage 2's scope. **A deployment that forgets it gets a surface that refuses everything.**
- **The frontend has no branch for 401**, which is now reachable on every operation.
- `StorageBucketMissingError` still carries `validation_failed` for a server fault — noticed
  independently by two streams, repaired by neither.
- A second `D-7` in a second adapter: `analysis/text/proxy.py` maps a **401 from the model
  proxy** onto `dependency_unavailable`, which the catalog pins **retryable** — it tells a
  caller to retry a rejected credential.

## 8. Still owner-blocked

`R-1`'s host details (name, root, ports, whether the proxy is reachable, when access appears);
`R-4`'s "who uploads" and "what ends the pilot"; `OD-17`; `OD-18`; and whether `origin/main`
advances.
