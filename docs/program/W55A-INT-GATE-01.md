# W55A-INT-GATE-01 — the consolidated W54 + W55a validation and gate

**Integrator:** `pdf-analysis-29` (continuation of `pdf-analysis-62` after a restart), 2026-10-12/13.
**Authority:** `R-111` consolidates W54's DB-backed checks and gate after W55a. The owner's
window answer was "Запускать сейчас, по шагу": tests and the gate ran at the usual floors, one
heavy step at a time; the BGE build ran at ≥ 6 GiB available.

## Steps and results

1. **First DB run** on `9c635ee`, on lane `gate-w54-int` with a fresh migrate from `0017` to `0020`: 3259 passed, 15 failed, 2 errors, 3 skipped.
2. **`W55A-FIX-DB`** fixed all 17 cases (16 test defects and one product defect).
   - The product defect: the worker's `JobWakeup.connect` read `driver_connection` after `detach()`, which SQLAlchemy 2.0.52 returns as `None`. The worker never listened and ran on its poll alone. It is fixed.
   - The schema invariant inventory was resealed after a family-by-family review.
3. **BGE image** (W54 window steps):
   - Pins: 11 model SHA-256 values; `pytorch_model.bin` is the only weight file at `5617a9f`. The wheel lock carries 892 hashes.
   - Build: self-check OK; `image_id` `sha256:6e049f7a…`.
   - Real-tokenizer windows: 404 503 texts and 416 850 windows equal, and the recording is committed.
   - MRR reproduced exactly: 0.848611 (24 queries, 563 windows) under `--network none`, with a peak RSS of 3296 MiB.
   - The image and this build's cache records were then removed by exact id, with no shared prune.
4. **Judges:**
   - `W55A-JUDGE-X`: ACCEPT-WITH-FIXES, with six minor findings.
   - `W55A-JUDGE-Y`: one major finding about the plan text, which `W55A-FREEZE-01` amendment 1 settles, and four minor findings.
   - `W55A-FIX` closed X-M1 to M5, Y-3, Y-4, Y-5 and the two order-dependent lease tests. X-M6 is `D-158`.
5. **Full gate** on clean `23fd729dbb06c642be0588017f6b195305e2e53e`:
   - Preflight at 2026-10-12T20:49:58Z: clean tree, about 12 GB free and 7 GiB available.
   - `make gate` exited 0 with the literal `GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass`.
   - Python battery: **4765 passed / 7 skipped / 298 subtests** in 1018 s.
   - Foundation: **35 passed**.
   - Frontend: lint and typecheck clean, Vitest **1941 passed in 131 files**.
   - Logs are under `.local/gates/w55a-23fd729/` (ignored): `gate.log` SHA-256 `2e4523b7…`, `preflight.log` SHA-256 `840d8b8f…`.
   - The lane was stopped and its two volumes removed.

## Not covered by this gate (owned elsewhere)

- **The STAND-COPY fingerprint case** (`W54_STAND_COPY_WINDOW=1`) is skipped by the gate. It belongs to `W54-REHEARSAL-01` / `W55A-REHEARSAL-01`.
- **No live provider call; the corpus operations have not run.** That covers the paid repair, which needs the owner's proxy key on this host; the about 14 h embedding build in night windows; and the bundle export. All three are `W54-CORPUS-OPERATE-01` and `W55-PROMOTION-PRE-01`.
- **Not yet run:** the rehearsals of both waves, `W54-QA-01` / `W55A-QA-01`, the notes judges, and `W55A-D124-MEASURE`.
- **No `origin/main` publication** (P2+P3) has happened; it needs the owner's direct instruction naming the SHA.
