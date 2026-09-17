# Wave 12 plan — two stages, in order, and the order is the point

Written 2026-09-17 by the integrator. Base `38a973a`, published as `origin/dev`. Gate: 1492
passed / 5 skipped / 163 subtests.

## 1. What must be sequential, and what must not be

**Corrected 2026-09-17, after dispatch.** This section first read *"Why this wave is
sequential, and parallel would be wrong"* and listed one stage-A session. Three were
dispatched. The correction was written in a commit message and not here, which is the same
defect this programme keeps repairing in other people's comments — **a commit message is not
an amendment to a document**, and a reader of this file got the wrong picture. `W12-DEC`
found it and was right to.

The rule is narrower than the original sentence:

**Only a stream that changes `src/` must be serialized before the certification.** A
certification is a statement about *behaviour*. A stream that writes tests only cannot make
one stale, so it runs beside the repair and its work is inside the same certification.

`W12-CERT` certifies a tree; `W12-RCN` changes one. Run together, the certification would be
stale before it is written — which is precisely the debt `DEBT_REGISTER.md` D-1 records
against `W6-CERT`, whose certification of `c0d7daf` stopped describing the tree the moment
wave 11 merged. **That argument applies to `W12-RCN` and to nothing else in this wave.**

So stage A runs three ways and stage B follows it. One certification then covers waves 11 and
12 together and the debt stays one wave wide — the rule from `W5_CLOSURE.md` §4.

| Stage | Session | Writes | Instance | Starts |
|---|---|---|---|---|
| A | `W12-RCN` — reconciliation proves less than it promises | **`src/`** + its tests | `gate-w12a` 55650 / 59250 / 59251 | now |
| A | `W12-WEB` — the frontend has never been swept | `web/tests/**` only | `gate-w12c` 55670 / 59270 / 59271 | now |
| A | `W12-DEC` — the decision ledger, swept only by reading | `tests/integration/{decisions,findings}/**` only | `gate-w12d` 55680 / 59280 / 59281 | now |
| B | `W12-CERT` — re-certify PC-01 | checkpoint artifacts only | `gate-w12b` 55660 / 59260 / 59261 | **only after stage A is merged and published** |

## 2. Stage A carries a design call, not a fix

`DEBT_REGISTER.md` D-2. `verify_version` compares the object's **recorded metadata** against
the manifest — two declarations, with nothing having read the bytes. A replacement preserving
metadata and length reads as sound, while the read path repaired in wave 11 refuses it.
`W11-RD` measured that on real MinIO.

But `reconciliation.py` makes **"never lists, never reads bytes"** a deliberate property: it
is a cheap sweep. Converting it to a full-body read changes what it costs, and that is a real
objection.

The brief therefore lays out three defensible shapes — correct the promise, add an opt-in
deep check, or always hash — and **requires the session to argue for the one it picks**. A
repair with no argument is a preference. Pre-deciding it in the brief would make the session
a typist, and the argument is most of the value here.

## 3. Stage B certifies four files that carry behaviour, and three that carry none

`src/` has moved 126 lines across 8 files since `c0d7daf`, but only four carry code:
`exports/service.py` (a **public attribute removed** — the one source-compatible break),
`ingest/service.py`, `storage/s3.py`, `analysis/text/stage.py`. Three changed comments only.

**`checksum_mismatch` is the limit to look hardest at.** Waves 11 and 12 changed exactly the
code deciding when bytes and their declarations disagree. `W11-RD` reported finding no way to
induce its new faults through the twelve operations — and said plainly that this was an
observation by the session that wrote the code, not a certification. Stage B establishes it.

## 4. What both briefs carry from what the last three waves cost

- `make mutation-copy`, and **baseline the unmutated copy before trusting any red**.
- Pin literals; wave 10 found the third form of that failure, where raising the constant a
  test derives its input from produces an out-of-memory kill rather than a red test.
- Read the mutated line back for **meaning**; four wave-10 streams wrote mutations that did
  not mutate.
- **A test that scans source text resolves it from `auditmanager.__file__`, never from
  `Path(__file__)`** — `W11-FIX` wrote guards that read the pristine checkout under a
  mutation copy. Reading an *authority* from the test file's location is the opposite case
  and is correct.
- A session-unique log directory; commit as you go.
- The gate is 1492 and rose by 212 in wave 11 **without a single new test**, because a
  quarantine written as a directory had been excluding live contract tests.

## 5. After this wave

`DEBT_REGISTER.md` §3: `origin/main` has been five waves behind, and the window for advancing
it closed when wave 11 changed `src/`. **Stage B's verdict is what reopens that question** —
it will be the first certification in five waves describing a commit on this line.

D-3 (`_record`'s defaulted provenance field) stays open and latent, with one call site that
passes it explicitly. It is not worth a behaviour change with no defect behind it.

## 6. Still owner-blocked

`OD-18` (experts; `P4-BHV-01` waits on it alone), `OD-17` (the next corpus shape), the 21st
error code — which `W11-RD` deliberately avoided needing, and which stage A is told it may
not need either.
