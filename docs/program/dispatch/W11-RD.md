# `W11-RD` dispatch prompt — the read path does not verify what the manifest promised

Base `30d129c` on `planning/prototype-roadmap`, published as `origin/dev`. Gate at that
commit: **1264 passed / 5 skipped / 116 subtests**, `make gate` → `GATE OK`.

One of three parallel streams repairing what wave 10's sweep found. The others work on
disjoint trees; you do not coordinate with them.

---

You are session `W11-RD`. Repository: /root/projects/PDF-Analysis.
Branch `agent/w11-rd`, worktree `/root/w11rd`.

## You own exactly these paths

- `src/auditmanager/ingest/service.py`, `src/auditmanager/storage/s3.py`
- `tests/integration/ingest/**`, `tests/integration/storage/**`
- `docs/program/reviews/W11-RD.md`

## The defect

`W10-RUN` found it and I verified it line by line.

`IngestService.read_source_bytes` resolves the manifest entry — which carries
`entry.sha256` — and then calls `self._store.read(entry.blob_id)` and returns the result.
**It never compares the bytes it got to the digest the manifest promised.**

`S3BlobStore.read` does re-hash, but against the **object's own** recorded digest from its S3
metadata, and the comparison is `if recorded is not None and recorded != actual` — so an
object carrying no digest metadata is returned unverified.

The consequence: for the exact fault `verify_version` exists to detect, the read path hands a
reviewer the wrong document with no error, while reconciliation over the same row raises
`storage_integrity_error`. Two paths over one row, two answers.

**What this is not.** It is still not inducible through the twelve operations — reaching it
needs an out-of-band replacement of the object — so PC-01's accepted `checksum_mismatch`
limit and both certifications stand. Do not write anything suggesting otherwise. This is
defence in depth that is missing, not a hole a caller can walk through.

`W10-RUN` pinned the behaviour **as it is**, with a comment naming its report, so it could
not be closed silently. Your repair replaces that pin; say so in your report and leave no
test asserting the old behaviour.

## What to decide, and to argue for

The shape of the repair is yours, and there is a real choice:

- verify in `read_source_bytes` against `entry.sha256` — the manifest is the promise, and
  this is the layer that holds it;
- or make `S3BlobStore.read` refuse an object with no digest metadata — closes the
  unverified-read hole for every caller, and changes behaviour for callers you do not own;
- or both, which is defence in depth but two failure modes to name.

**Argue for the one you pick in your report.** Whatever you choose, an operator must be able
to tell the two causes apart: bytes that disagree with the manifest is not the same fault as
an object the store cannot vouch for, and one typed code for both would repeat the
`analysis_failed` flattening wave 3 had to undo.

Check what `verify_version` already does before you write anything — it may already hold the
comparison you need, in which case the repair is smaller than it looks.

## Provisioning

```
cd /root/projects/PDF-Analysis && git fetch origin
git worktree add /root/w11rd -b agent/w11-rd origin/dev
cd /root/w11rd && git log --oneline -1
```

Base `30d129c` or later. **Not under `/tmp`** — docker is snap-confined. Say in your report
what your `HEAD` was on arrival.

**Commit as you go.** Wave 10's first attempt lost four sessions to a restart and only
committed work survived. Open `docs/program/reviews/W11-RD.md` early and append to it.

**Use a session-unique scratch directory for logs.** The five wave-10 streams shared one and
overwrote each other's gate output; one of them read another lane's failures as its own.

## What is different about this wave

Wave 10 swept and wrote tests. **You write product code.** That changes three things:

1. **Every repair needs a guard that reddens without it.** Not "a test that passes after" —
   a test you have mutated back to the defect and watched fail. A repair with a green test
   either way is a repair nobody can defend later.
2. **You may not certify your own repair.** Say what you changed and what you proved; a
   later session re-certifies PC-01 against it. Do not write a sentence claiming a criterion
   still holds.
3. **Behaviour changes carry re-certification debt.** Keep the change minimal and say what
   an operator or a stored row would observe differently.

## The method

```
make mutation-copy MUT=/root/w11rd-mut
```

New in wave 10 and it replaces the prose recipe every brief carried since wave 3 — which was
**wrong**, and not in a harmless way: it omitted `db/` and `tools/`, and a copy without
`tools/` fails four `p02_journey` tests **unmutated**. It manufactured reds. The target links
all five directories and proves the copy is the tree that will be imported.

`FULL=1` copies them instead of symlinking, which is how you mutate a contract or a fixture.
**No copy makes a migration mutable** — `tests/integration/db/conftest.py` derives the
repository root from its own file.

**Baseline the unmutated copy against your suites before trusting any red.** That instruction
matters more than the directory list: no list is safe against the next path someone resolves
from the root, and a baseline is.

**Pin expected values as literals.** Wave 9 lost five tests to importing the module's own
constants and building the expectation from them — both sides move together under mutation.
Wave 10 found the same failure in a third form: where a test derives its *input* from the
constant it tests, raising the constant is not a red test, it is an out-of-memory kill.

**Read your mutated line back for meaning**, not just for text. Four wave-10 streams wrote
mutations that did not mutate; `frozenset() or frozenset({...})` evaluates to the real set,
and `26 * 1024 * 1024` is a substring of `26 * 1024 * 1024 * 1024`.

## Rules

1. Stay inside your owned paths. A defect in another tree goes back as a report, unrepaired.
2. Never add a root dependency; `docs/program/P02_LOCK.json` is the pinned set.
3. Never add bytes to `fixtures/synthetic/ar/**` or `fixtures/validation/PC-02/**` — frozen
   evidence. Build the bytes your test needs inside the test.
4. No tag, no push, no merge to `main`.
5. **Check every premise in this brief against the tree.** Nine stale premises are on record
   in this programme, most of them in briefs written by the integrator who wrote this one —
   including, last wave, a count of forbidden shapes that was simply wrong. If something here
   is false, say so in your report.

## Your gate

```
make gate
```

Expect **1264 passed / 5 skipped / 116 subtests** before you change anything. A linked
worktree has no `web/node_modules`; run `npm --prefix web ci` once.

`tests/contract` and `tests/checkpoint` are quarantined by `PROTOTYPE_PROFILE.md` §6.3 and
are **not** your gate. Wave 10 found they cover rules the gate does not, which is why
grepping them for coverage misleads; the integrator is handling that separately.

## Environment

Instance `gate-w11a`, `POSTGRES_PORT=55630`, `S3_API_PORT=59230`, `S3_CONSOLE_PORT=59231`,
`POSTGRES_DB=audit_w11a`, bucket `auditmanager-gate-w11a`. Bootstrap with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`; copy `.env.example` to `.env` and set
exactly your instance. No live provider needed.

## Report

`docs/program/reviews/W11-RD.md`: your `HEAD` on arrival; every repair with the guard that
reddens without it, shown red and green; what an operator or a stored row observes
differently; anything you decided not to repair and why; anything false in this brief;
elapsed wall-clock.
