# Wave 46's cross-judges: two in parallel on the merged sub-stage B, then each on the other

Written 2026-09-28 by the integrator. They run **after** `W46-SPEND` and `W46-WIRE` are merged
and **before** the final gate. That order is wave 43's correction: judging first means the final
testing measures what ships. The integrator names the merged tip in each dispatch.

**Every judge repairs nothing.** Each one owns exactly one report file, reverts anything it
touched to measure, and shows `git diff --name-only <tip>..HEAD` proving that its branch carries
that one file. **The owner's stand `auditmanager-w19a` at `127.0.0.1:31500` is read-only.**

**Why the probes are named rather than left to opinion:** wave 44's cross-judges found five false
greens inside the integrator's own repairs. In wave 46, `W46-JUDGE-A` found three promises with
no guard that could fail, all in a stream report that said they were guarded. **A judge that
finds nothing looks exactly like a judge with nothing to find.**

---

## `W46-JUDGE-X` — the contract, the instruments and the integrator's own changes

**worktree** `/root/w46j` · **branch** `agent/w46-judge-x` · **lane** `gate-w46j`
(PostgreSQL `56390`, S3 `59990/59991`, API `56391`, Next `56393`)
**report** `docs/program/reviews/W46-JUDGE-X.md`

- **X1 — take the whole gate on the merged tip.** Run `make gate > /root/w46x-gate.log 2>&1`,
  literally, and take the verdict from the `GATE OK` line. Quote the counts. Compare them with
  `W46-JUDGE-A`'s on `130200d` and account for every difference by name.
- **X2 — `F-1` re-driven.** On a fresh database: sign in, call `GET /dashboard`, and confirm
  `run_activity.spend` is **absent**, not zero. Then record one run and confirm `spend` appears
  with a count of at least 1. Check that no layer turns absence back into zeros: record, view,
  serializer, generated type.
- **X3 — the reseal, five documents or four?** `openapi.json`, the mirror, the generated client,
  the lock's digests and every moved pin must be in **one** commit. Recompute the digests
  yourself and run `npm --prefix web run api:verify`. The surface must still be 17 / 20 / 61,
  with 22 error codes and head `0011`. **Is the lock's `commit_note` true now?**
- **X4 — the three guards `W46-SPEND` claims, mutated by you.** Use `W46-JUDGE-A`'s mutations
  for `F-5a` and `F-5c`, and run `F-2`'s rule in both directions. A guard the stream showed
  failing under its own mutation proves only that mutation. **Invent one more per guard.**
- **X5 — the integrator's own changes, which no grant covers.** `8ad692f` repaired eight reds,
  partly by editing prose across `infra/deploy/serve.py`, `infra/deploy/README.md`,
  `web/src/shared/api/authorization.ts`, `web/src/app/bff/v1/[...path]/route.ts`,
  `docs/program/P02_SEAMS.md` and `docs/program/ALPHA_ROADMAP.md`. **Is each sentence true of the
  tree?** And `D-106` to `D-109`: run each row's check command. **Does it print what the row says
  it prints?**
- **X6 — did the merge lose a test?** Do not answer by counting: a renamed test keeps the count.
  Byte-compare every stream file against the merged tree, and do set algebra over test node ids.

## `W46-JUDGE-Y` — the product, the journey and the stream reports

**worktree** `/root/w46k` · **branch** `agent/w46-judge-y` · **lane** `gate-w46k`
(PostgreSQL `56400`, S3 `60000/60001`, API `56401`, Next `56403`)
**report** `docs/program/reviews/W46-JUDGE-Y.md`

- **Y1 — every number on `/dashboard` against the API's own answer.** On your own stack, drive
  four states: no projects; one project with no documents; one `KM` document plus one
  unclassified document; then one published run. For each state, put `GET /dashboard` beside
  the rendered screen, number by number. **One read and nothing else:** list the network calls
  the screen makes.
- **Y2 — the sentences.** Do the dashboard's captions and the project screen's section sentences
  now say what is true? A section is stored and checked when supplied, and the product's form
  cannot supply one. Is the unclassified row always shown? Does the verdict panel's caption
  match what the aggregate counts, where *pending* includes findings nobody has judged? Check
  that *контракт* and *операция* are gone from the dashboard.
- **Y3 — the journey, live.** Run `npm --prefix web run e2e:pc01 -- --origin <your Next> --phase
  all --out <dir>` and quote the summary. **Zero undeclared calls on every route**, including
  `blocks`. If `W46-WIRE` used `optional_api`, is the call really conditional?
- **Y4 — widths and palettes.** Use 780, 781, 360 and 1024 px, in both palettes, with data.
- **Y5 — `F-5b` mutated by you.** Use `W46-WIRE`'s three mutations and invent one more: a number
  that comes from the right field of the wrong panel.
- **Y6 — is any claim in either stream report false?** `docs/program/W46-SPEND.md` and
  `docs/program/W46-WIRE.md`. **Re-measure; do not re-read.**

## Both judges: off the trail

Go to **at least three places** this brief does not point at, and give each one a row in a
table: where you went, why the trail does not lead there, and what came back. **A place that
returned nothing still gets its row.** `W46-JUDGE-A` found `F-1`, `F-3` and `F-5` off the trail,
and the pre-existing `blocks` red as well. The trail is where the wave's own assumptions are.

## Then: cross-examination

When both reports are in, the integrator gives each judge the other's report. For every finding
in it, answer **upheld**, **narrowed** or **falsified**, each with a measurement the other did not
take. Then answer one question: **where does the other's method share an assumption with its
subject** (`OPERATING_CONSTRAINTS.md` §12)? Append the answers to your own report as a final
section. **A judge that only agrees has not cross-judged.**

## What a finding is

It names the file and line, states what is false or missing, gives **the command that reproduces
it**, and says what it would cost. **A finding without a reproduction is an opinion.** Say plainly
where a stream did the right thing, especially where it reported a weakness in its own work.
**Report which questions you could not answer, and why.**

## Discipline

Open the report before the first measurement and commit it. **Commit after each section.** A
session restart kills you, and only committed work survives it. When you finish, stop your API
and Next, and remove any disposable clone. Do not tag, push or merge.
