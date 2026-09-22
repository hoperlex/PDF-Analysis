# Operating constraints on this host

Sixteen dispatched sessions have run in this programme. Several lost time to the same six
environment traps, each rediscovering them alone. They are recorded here once, as
instructions rather than as history, and every brief points at this file.

Each is reproducible on this host. None is a defect in the tree; do not open one against
the code.

## 1. Docker cannot see `/tmp`

Docker on this host is a snap package, so `/tmp` is not the `/tmp` the daemon sees. A
worktree or scratch tree under `/tmp` makes `make up` fail with a path error naming
`/var/lib/snapd/void/...`, which reads like a broken compose file and is not one.

Put your worktree, and any scratch directory that needs live services, outside `/tmp`.
`/root/<something>-scratch` works. Reported by `B-III`, which spent its first pass
debugging compose.

## 2. `pyproject.toml` overrides an exported `PYTHONPATH`

`[tool.pytest.ini_options]` sets `pythonpath = ["src"]`, relative to rootdir. An exported
`PYTHONPATH` does not displace it. A mutation applied to a scratch copy of `src/`
therefore never reaches the run: pytest imports the original tree and reports green, and
that green looks exactly like a guard that does not fire.

Point pytest at the copy explicitly:

```
.venv/bin/pytest -o pythonpath=<copy>/src <tests>
```

and **prove the copy was imported before believing any mutation result** — print the
loaded module's `__file__` and confirm it resolves under `<copy>`:

```
.venv/bin/python -c "import sys; sys.path.insert(0, '<copy>/src'); \
    import auditmanager.<module> as m; print(m.__file__)"
```

A mutation run without that proof is not evidence. Reported independently by `B6` and by
the integrator, who fell into it twice.

## 3. A copy of `src/` alone will not import

Two modules read repository data files resolved from their own location, four parents up
from the module — that is, from the directory that contains `src/`:

- `auditmanager.shared.errors.catalog` reads `contracts/domain/v1/error-codes.json`
- `auditmanager.analysis.text.lock` reads `docs/program/P02_LOCK.json`

A scratch tree holding only `src/` fails at import, well before any assertion runs.
Symlink **both** into the copy, beside `src/`:

```
ln -s "$REPO/contracts" "$COPY/contracts"
ln -s "$REPO/docs"      "$COPY/docs"
```

Reported by `B-III` and by the integrator.

## 4. The session scratchpad is not isolated between sessions

Concurrent sessions share it. `B1` and `B8` each had a mutation tree overwritten mid-run
by a peer working under the same name, and each first read the result as a failure of its
own guard.

Name your scratch directory for your session — `<session-id>-scratch`, never a shared
`mutation/` or `scratch/`.

**It happened again in wave 29, to log files rather than to mutation trees, and that is why
this section now names logs too.** Two live sessions wrote run logs to the same path within
the same minute; the second truncated the first, and the first session's reading of its own
run was gone before anyone read it. `D-47`.

The rule, stated so it covers both shapes: **every path a session writes outside its own
worktree carries that session's name.** Not the wave's, not the task's kind — the session's.
`/root/w30-logs/cert3-gate.log`, not `/root/w30-logs/gate.log`; `/root/w30lists-mut`, not
`/root/mut`. A brief that hands a session a logs directory hands it a **prefix** within that
directory, and this is now a line in every brief.

**And the same rule covers the gate lane, which is not a path and is the easier one to
forget.** `.env` is git-ignored, so a worktree made by `git worktree add` **has none**; a
session that reaches for `cp .env.example .env` takes the example's `FOUNDATION_INSTANCE`,
ports and database — and so does every other session that does the same thing, and so do the
containers already running under that name. §6 is what happens next.

The integrator dispatched both of wave 30's sessions with a private **log prefix** and no
lane at all, and caught it only while writing this paragraph, before either had run a gate.
So the checklist a brief satisfies is two items, not one: **a private prefix for everything
it writes, and the six lane values** — `FOUNDATION_INSTANCE`, `POSTGRES_PORT`, `S3_API_PORT`,
`S3_CONSOLE_PORT`, `POSTGRES_DB`, `S3_BUCKET`, with `DATABASE_URL` and `S3_ENDPOINT_URL`
carrying the same ports, which the `Makefile` checks and refuses.

The failure mode is what makes it worth a section rather than a convention. A clobbered log
does not announce itself. It reads exactly like a run that produced less output than you
expected, which is the same thing a silently truncated command looks like — and §12 is the
whole reason this programme does not accept that reading without a second measurement.

## 4.5 A permission is scoped to one session; a shared resource is not

**Recorded 2026-09-21, from a case where nobody did anything wrong and the decision did not
hold anyway.**

`W31-STYLE` could not gate: `make up` failed with `all predefined address pools have been
fully subnetted`. It measured 33 docker networks, 24 of them empty and belonging to dead
sessions from waves 3–24, and **was refused permission to remove them.** It did not work
around the refusal. It reported the blocker and handed the integrator the command.

The integrator **declined to run it**, because running an action on behalf of a session that
was refused it routes around the decision rather than respecting it.

**Twenty minutes later the networks were gone.** A second live session on the same host —
`pdf-analysis-84` — hit the *same* blocker in its *own* gate, measured the same 33 networks,
ran `docker network prune -f`, and gated green. It had not been asked, did not know a refusal
existed, and its own session permitted the command. **There was no request to route around and
no misconduct.** It then disclosed what it had done, unprompted, rather than letting the
attribution stand.

**The structural fact is the one to carry forward: permissions are scoped per session, and a
host-wide resource is not.** So a decision that one agent may not do something to a shared
resource does not prevent the thing from being done — it only decides *who does not do it*.
Nothing recorded the refusal anywhere the second session could read.

This will recur with anything host-wide — **disk, ports, images, containers, networks** —
because every one of them is reached by more than one lane. Three consequences worth acting on:

1. **A refusal is information other lanes need.** When a session reports being refused something
   host-wide, the integrator should say so to the other live sessions, not only to the owner.
   Wave 31's integrator did not, and learned of the prune from the peer's own disclosure.
2. **Declining to act on a peer's behalf is still right**, and this case does not weaken it. The
   integrator's refusal was correct and remains the rule; it was undone by coincidence, not by
   anyone circumventing it.
3. **Do not read "the blocker cleared itself".** The integrator's first reading of the drop from
   33 networks to 9 was that something on the host reclaims them. It does not. A live agent ran
   a command, and the only reason that is known is that it said so.

## 4.6 Two instrument failures that both produce a red you will misread

**Both reported by a peer session on 2026-09-22, and both were found by reading a log rather
than a status line.**

### A backgrounded gate reports the wrapper's exit code, not the gate's

A `make gate` run in the background reported **exit code 0 while the gate had failed**. The 0
belonged to the wrapper that launched it. It was caught only because someone read the log.

This programme already has the rule *"read the exit code from `$?` after a redirect, never
through a pipe"*, and this is the same defect one layer out: **a status line handed to you by a
harness is not the thing's exit code.** So the rule for briefs is the stronger one — **assert
on `GATE OK` appearing in the output**, which only the gate itself prints, and never on a
number some wrapper gives you.

### Contention produces a red that reads exactly like a broken guard

A full gate reported `1 failed` in `test_deploy_image_identity.py` — a test that builds and
deploys real images. Run alone: **23 passed in 48s**. The failing run took **643s against a
normal 277s**, with another lane's containers up alongside it for 23 minutes. Second run on the
same tree, quieter machine: 415s, `GATE OK`.

**Nothing was wrong with the tree or the guard.** The shape belongs beside §10.2's stale-bytecode
trap for the same reason: both hand you a red whose obvious reading is *"this guard is broken"*,
and the obvious next step — weakening it — damages a guard that was never at fault.

**Before believing a red from a test that builds, deploys or times anything: re-run it alone,
and compare the wall clock against a normal run.** A gate that took twice as long as usual is
evidence about the machine, not about the code.

## 5. `make bootstrap` needs an explicit base interpreter

When the ambient interpreter is an active virtualenv, run:

```
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
```

The bare form is refused, by design: the foundation is never built from an ambient
environment. **That refusal is the guard working.** Do not report it as a defect and do
not work around it.

## 6. The integration suites share one database

Some of them assert global state, so a suite can fail because of what another suite left
behind. Run only your own suite.

If you must run several, expect cross-suite interference and say so in your report rather
than filing a failure as a code defect. This is a known open item, not news.

## 7. There is one battery command, and it is this one

`GATE_C_DEFERRED.md` claims the backend suites run under "one battery command". No document
named it, so the three Gate W2 sessions each invented their own and reported three different
totals — 708, 718 and 729 — none of them comparable with another. Each said so in its report,
which is the only reason it was noticed.

The canonical command is:

```
.venv/bin/pytest tests --ignore=tests/checkpoint \
  --ignore=tests/contract/test_cp00_candidate.py \
  --ignore=tests/contract/test_cp00_final_state.py \
  --ignore=tests/contract/test_validate_bootstrap.py
```

**Narrowed in wave 11.** It used to read `--ignore=tests/contract --ignore=tests/checkpoint`,
and that is the form quoted in every dispatch brief up to wave 10. See §11.

**Since wave 7 it is also `make gate`, and that is the one to prefer.** The battery is one
of four things a wave must pass, and until wave 7 only `make foundation` was a target while
the other three lived here, as prose. The frontend suite went four waves without being run
because nothing named it. `make gate` runs all four and fails if any fails, so the
composition is reviewable in a diff rather than recalled from this paragraph.

The literal command above is kept for the case where one half is wanted alone — a session
whose brief covers only backend paths, say — and because a document that only says "run the
target" cannot be checked against the target. **If the two ever disagree, the Makefile is
the authority and this paragraph is the defect.**

Prefer the negative form over naming the suites positively. It picks up a directory a later wave adds, and
it excludes exactly the two quarantined trees named in `PROTOTYPE_PROFILE.md` §6.3 and
nothing else. A positive list silently stops covering whatever is created after it is
written.

Quote the count with the command that produced it and the commit it ran on. A bare test
count is not a measurement.

## 8. Freeze the tree before the battery, not during it

`tests/integration/foundation/conftest.py` carries an autouse session-scoped guard from
`P1-QA-00` that snapshots the tracked checkout before the suite and compares it afterwards,
failing if they differ — "a test that writes into the repository belongs in a `tmp_path`".

It does what it was built for, and it also fires when **you** edit a tracked file while a
run is in flight. `W2-PROV` lost two battery runs that way and both were green once re-run
against a committed tree. Commit first, then run. A red from this guard names the checkout
diff, so it is distinguishable from a real failure if you read it.

## 9. §6 is about residue, not about population

§6 tells you to report a cross-suite failure as interference rather than as a code defect.
That is right, and it is narrower than it looks.

The database is long-lived and the schema is append-only by design, so rows accumulate
across sessions and days: at the Gate W2 convergence the shared instance held 495 projects
that no suite in that run had created. A test that assumes a small table fails against that
population **on its own**, with nothing else running, and that is a defect in the test, not
interference.

The way to tell them apart costs one command: run your suite alone against the same
database. If it still fails, §6 does not cover it.

## 10. The mutation copy is a command, and the prose recipe was wrong

Every anti-vacuity proof here runs against a copy of `src/` outside the worktree, so that no
tracked file is ever edited to mutate. From wave 3 to wave 10 the recipe for building that
copy was carried as prose in dispatch briefs:

> symlink `contracts/`, `docs/` and `fixtures/` into that copy

**It was incomplete, and incompleteness here does not merely lose coverage — it manufactures
reds.** `db/` and `tools/` are also resolved from the copy's root, and a copy without
`tools/` fails four `tests/integration/p02_journey` tests **unmutated**. A sweep that went
straight to mutating would have filed four guards over a tree it never broke. Found by
`W10-FND` in wave 10 and reproduced independently by the integrator.

Since wave 10:

```
make mutation-copy MUT=/root/<name>-mut
```

It builds the copy, refuses a destination under `/tmp` (snap-confined docker cannot see it)
or inside the worktree, links all five directories, and **proves the copy is the tree that
will be imported** by printing `auditmanager.__file__` and asserting it resolves under the
copy. Shown to catch the old recipe: against a copy carrying only the three, it exits 1 with
`unreachable from the copy: ['db', 'tools']`.

Each link is derived from the tree, not from a brief:

| Directory | Why the copy needs it |
|---|---|
| `contracts/` | `exports/policy.py`, `documents/models.py`, `shared/errors/catalog.py`, `analysis/engine/registry.py` all resolve it from `parents[3]`/`[4]` |
| `docs/` | `analysis/text/lock.py` → `docs/program/P02_LOCK.json` |
| `fixtures/` | `analysis/text/recorded.py` → `fixtures/recorded/text_analysis` |
| `db/` | `shared/db/migrations.py` → `db/migrations/alembic.ini` |
| `tools/` | resolved **test-side** from `auditmanager.__file__` on purpose, so a mutation run gets the copy's ledger tool rather than silently reading the pristine one |

**The part that matters more than the list:** run your suites against the **unmutated** copy
and confirm they are green before you trust a single red. The target prints that instruction
and it is not decoration — a red from a copy you never baselined is not evidence. No list of
directories is safe against the next path someone resolves from the root; a baseline is.

### 10.2 A fast mutation sweep reads stale bytecode, and the symptom looks like a broken guard

**Found by `W33-CORPUS` 2026-09-22, reproduced in isolation.**

CPython validates a `.pyc` against its source by **mtime in whole seconds, plus size**. So two
mutations of **the same length** into **the same file** inside **one second** leave the first
one's bytecode live: the second case executes the *first* case's mutation.

**The symptom is what makes this worth a section.** The sweep reports a red naming a test from
the **previous** case. Case `G4` ran `G3`'s mutation and reddened `G3`'s test. That reads
exactly like *"this guard is too broad"* — a plausible, wrong, and expensive conclusion, since
the natural next step is to weaken a guard that was never at fault.

An automated sweep is precisely the thing that mutates fast enough to hit this. A person
editing by hand never will.

**The fix:** `PYTHONDONTWRITEBYTECODE=1`, and clear `__pycache__` between cases.

### 10.1 What no copy can mutate

`FULL=1` copies the five directories instead of symlinking them, so a mutation to a
contract, a fixture or the ledger tool takes effect for code that resolves them from
`auditmanager.__file__`.

**It does not make a migration mutable, and neither does any other copy.**
`tests/integration/db/conftest.py` derives `REPOSITORY_ROOT` from *its own file* and runs
`alembic` as a subprocess with that `cwd`, so the worktree's `db/migrations` is what applies
regardless of `pythonpath` or what the copy holds. Mutating a migration means copying the
**whole worktree, tests included**, and running pytest from there — `W10-RUN` did this for
its trigger sweep and it is the difference between measuring the migrations and appearing to.

The target says so on every run. It was written claiming the opposite for one commit, which
is the same false-affordance class this wave exists to find: a facility that looks like it
works, produces no error, and yields a no-op mutation indistinguishable from a covered rule.

## 11. The quarantine was by directory and should have been by file

`PROTOTYPE_PROFILE.md` §6.3 quarantines **CP-00 ratification mechanics**. Until wave 11 that
rule was implemented by excluding the whole `tests/contract` directory — which swept up five
subdirectories of contract tests over **live** rules: the error kernel, the identifier
catalog, the API v1 shapes, the P02 domain, the AR fixtures.

**`W10-API` found what that cost.** Those tests exercise five of the six forbidden shapes in
the error screen, and both identifier catalogs — rules its sweep reported as unguarded,
because the gate does not run them. They are findable by grep and they read as evidence, so a
reviewer asking "is this rule covered?" was told **yes** by tests that protect nothing. It
was the single largest systematic reason that surface yielded 36 unreddenable rules from 77.

Measured before narrowing, in a linked worktree:

| Path | Result |
|---|---|
| `tests/contract/shared_kernel/` | 16 passed, 25 subtests |
| `tests/contract/api_v1/` | 11 passed |
| `tests/contract/domain_p02/` | 110 passed |
| `tests/contract/analysis_packages/` | 35 passed |
| `tests/contract/fixtures_ar/` | 40 passed, 22 subtests |
| `tests/contract/test_cp00_candidate.py` | **33 failed**, 126 errors |
| `tests/contract/test_cp00_final_state.py` | **3 failed** |
| `tests/contract/test_validate_bootstrap.py` | **28 failed** |

The five subdirectories total **2.5 seconds** and need no dependency the runtime venv lacks.
The three files really are red, and they are the CP-00 and clean-clone-bootstrap material
§6.3 actually means. `W6-CERT`'s finding that `tests/contract` cannot run from a linked
worktree applies to those files; the five subdirectories run green in one, which is where the
figures above were taken.

So the ignore names the files. **§6.3 is unchanged and was never wrong** — the rule said
CP-00 mechanics, and only the implementation said *directory*. The battery goes 1264 → 1476
passed and 116 → 163 subtests, and none of those 212 tests is new.

**The general lesson is not about this directory.** An exclusion written as a path is a claim
about everything that will ever live under that path, and nothing re-checks it when something
new is added there. Where a quarantine must be broad, say in the same breath what it costs,
so the next reader can tell coverage from the appearance of it.

## 12. A query that shares an assumption with the thing it measures is not a measurement

Three instances, one shape, and the third was mine.

- **Wave 9.** Tests imported the module's own constants and built the expected value from
  them. Raising a limit moved both sides of the comparison, so the test passed against every
  mutation. Five green tests over three rules they could not check.
- **Wave 10.** A test derived its *input* from the constant it tested. Raising that constant
  made the test allocate 13 GiB and get killed — recorded as a red, and it was not one.
- **Wave 12, in a register row.** I wrote that `permission_denied` was "used nowhere in
  `src/`", having grepped the enum constant `PERMISSION_DENIED`. The storage layer carries the
  **string** `code = "permission_denied"` on a `ClassVar`. The codebase spells the same fact
  two ways and my query knew one of them.

The common part is not carelessness and it is not about tests. **The query and its subject
shared an assumption, so the query could not see the subject being wrong.** A green, a red and
a register row all came out of it, and all three read as evidence.

Two practical forms, and the first is cheap enough to have no excuse:

- **Search both spellings, or say which one you searched.** An enum constant and its value are
  different strings; so are a class name and the code it carries. `grep -rn "permission_denied"`
  would have found what `grep -rn "PERMISSION_DENIED"` did not.
- **Never build an expectation, or an input, out of the thing under test.** §7's battery figure
  and the literals every brief since wave 9 demands are the same rule applied to numbers.

And the standing one: **a row, a table or a report that says "measured" is worth exactly what
the query behind it is worth, so show the query.** Every row of `DEBT_REGISTER.md` carries one
for this reason.

### Three more shapes, found in waves 20–23

The first two were self-reported by the sessions that committed them, which is how they came
to be written down at all.

- **A correct query, read before it finished.** `W20-CODE` swept for stale count assertions
  with `grep -rn "== 21" tests/ | head -20`, and the first twenty hits were all
  `assert response.status == 201`. **The query was right; the truncation was read as the
  answer.** It cost a red gate. A pipe into `head` turns a search into a sample, and a sample
  cannot support "there are none".
- **An assertion aimed one field to the left of the thing that decides.** `proxy.py` wrote
  OpenAI's `length` into `stop_reason` as the string `"truncated"` — a word from the
  *call-status* vocabulary — while `adapter.py` decides truncation by comparing `stop_reason`
  to `"max_tokens"`. The guard asserted **the string** and never `response.truncated`, **the
  decision**. So on the live transport a report cut short at the output ceiling published as a
  complete one, and **the test pinned the defect in place** rather than catching it. `D-34`.
  *Assert the value the code branches on, not a value beside it.*
- **A document nobody reads cannot be checked by anyone reading.** `AGENTS.md` §1.1 makes
  `docs/program/CURRENT_STATE.md` the first thing every agent reads. It sat **nine waves out
  of date** because every dispatched session was oriented by its brief instead — so nothing
  ever reddened, and the gap was invisible *precisely because the stale thing was unread*.
  `D-23` is the same shape one level down: nothing checks prose against the surface it
  describes. **Both are cases where the absence of a reader is the absence of a check.**

### A sixth shape, found in wave 31: a correct reading of a file that is not the whole of its subject

**The most expensive one so far, because it reached a dispatched brief.**

Wave 31 exists because `R-18` requires the alpha to be shown in a finished interface. A session
compared our design tokens against the legacy front end's, read the `:root` block of its
stylesheet, saw light values, and reported *"legacy is a light theme with a teal accent
`#008f7e`"*. Every statement about that block was true.

`:root` is the **light** theme. The same stylesheet carries a second full token set under
`[data-theme="dark"]` — **11 `[data-theme]` blocks** — and the application's own script reads
`localStorage.getItem('theme') || 'dark'`. **Dark is the default.** The accent in the default
theme is `#00c2b8`. The comparison had omitted an entire second palette, a toggle and its
persistence, and it went into `W31-STYLE`'s brief as the target to build against.

**What makes it a §12 shape rather than ordinary carelessness:** the query shared an assumption
with its subject. Reading `:root` assumes a stylesheet has one theme, which is the very thing a
theming system contradicts — so the reading could not have revealed its own incompleteness. It
took **rendering the application** to see it, which the session eventually did with a plain file
server over the static assets plus empty JSON on `/api`, no legacy backend required.

**And the warning was in writing, in front of two people, and neither acted.** The session said
plainly, in the same message, that it had compared design systems only and **had not rendered
legacy**. The integrator read that sentence, repeated it to the stream as a caveat, and
dispatched anyway. **A stated non-measurement was passed along as a caveat instead of being
treated as a blocker.** That is the reusable part: when a report names something it did not
measure, the named gap is the first thing to close, not a footnote to carry forward.

Caught mid-flight; the brief was patched before the palette was built on it, and the decision
it turned out to hide — whether the alpha is dark by default — was taken out of the stream's
hands and put to the owner, because it is not a styling decision.

**Three sharper statements of it, from the session that produced the case and then wrote it
up**, which are better than the integrator's first pass and are kept in its words:

- **A caveat is not a control.** It records that nobody measured; it does not stop anyone
  acting as though somebody had.
- **Volume of measurement was read as thoroughness and hid a categorical error.** Twelve
  figures, every one real and reproducible, sitting around a wrong category.
- **`record-measured-figures-with-their-method` was fully satisfied and did not help.** The
  command was given and the tree was named. That rule makes a figure re-checkable; it does not
  ask whether the span the command covered is the whole subject.

**The check this adds.** Before reporting a property of an artefact, ask **what the artefact
does when run**, and whether the file you read is the only place that property is decided. For
anything with themes, modes, environments or feature flags: a `:root` block, a default branch,
a base config and a dev override are each *a* value and none of them is *the* value. Where the
artefact can be rendered or executed cheaply, do that once — it answers in one observation what
a file scan answers only if you already knew which files to read. Where it cannot, **say the
answer is unverified in the conclusion, not only in the method**: a caveat beside a confident
table reads as thoroughness rather than as a limit.

**A sibling case, same wave, same week.** `W31-UI` classified `credentialed-forward.ts` as
server-side and left its sentences in English; `W31-RUS` found six of them reaching a reviewer,
because `synthesizedEnvelope()` puts them into an envelope **body the browser decodes**. The
classification asked which process **executes** the module and never asked where its **output**
is read. *Which process executes a string is not the same question as who reads its output.*

**And a near-miss in the same report, which is the more dangerous shape.** The same session
classified `env.ts` as server-side too. That verdict **held** — those strings are unreachable —
but for a different reason than the one given: `getApiBaseUrl()` does run in the browser, and
what actually saves it is that `MissingConfigurationError extends Error` rather than
`ApiFailure`, so a Russian fallback masks them first. **A right answer from a wrong premise is
the thing that survives review and breaks later**, because nothing about the outcome invites a
second look.

**A claim of the integrator's that has now been repeated into three waves and is false.**
*"`web/src/app/**` is nine six-line delegations that never hold behaviour."* It came from
`W19-SHELL`'s true observation that the screens were not there, hardened into a reason to
exclude the directory from ownership, and was written into wave-31 briefs. Measured by
`W31-STYLE`: seven page files of 9–36 lines, `layout.tsx` at 28 **holding `<html lang>`**, and
`bff/v1/[...path]/route.ts` at **109 lines — the credentialed transport seam**. It matters
twice over: that route is the one place a credential is added server-side, and `layout.tsx` is
exactly where theme work would land. **A true observation about why a directory was empty
became a standing claim about what it contains, and nothing re-measured it for three waves.**

**And one about this file.** Its path is `docs/program/dispatch/OPERATING_CONSTRAINTS.md`. The
integrator cited it as `docs/program/OPERATING_CONSTRAINTS.md` in briefs for a week; the
repository never carried the wrong path, so only dispatched sessions met it. A session that
took the path literally would have found nothing — **§12 applied to §12's own location.**

