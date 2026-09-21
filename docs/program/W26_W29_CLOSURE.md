# Waves 26–29 closure: the product was measured as a product, and three of its sentences were wrong

Written 2026-09-21 by the integrator. **`make gate` → `GATE OK`, exit 0** at the wave-29 tip
`ac7c348`: battery **2001 passed / 5 skipped / 169 subtests**, foundation **35**, frontend
**764 in 52 files**. Read from `/root/w19-integrator-logs/gate-w29.log` with `EXIT=0` appended
by the shell that ran `make`.

Waves 21–25 made certification repeatable. These four waves asked a different question, and it
is the one the owner has been asking all along: **what does a person actually get?** Not what
passes — what a person sees, how long they wait, and what it costs.

Three of those four waves answered it by finding that a sentence the application says out loud
was wrong.

## 1. The result

| Wave | Stream | Row | Outcome |
|---|---|---|---|
| 26 | `W26-HOST` | `R-15`, `D-42`, `D-43` | everything a VPS needs, authored before the VPS exists |
| 26 | `W26-OPS` | `D-38`, `D-39` | the deploy stops sending an operator to the wrong file |
| 27 | `W27-REFUSE` | — | six wrong files dropped into a browser; **six true refusals, no repair** |
| 27 | `W27-WEB` | `D-40`, `D-41` | the screen's code list stops being narrower than its surface |
| 28 | `W28-GUARD` | `D-44` | `W27-REFUSE`'s six proofs come under the gate |
| 28 | `W28-LIVE` | — | **the first measurement of the product as a product** |
| 29 | `W29-RETRY` | — | a missing file stops being called an outage |
| 29 | `W29-SAY` | `D-45` | a failed run says a sentence instead of an identifier |

## 2. `W28-LIVE` is the most valuable single measurement this programme has taken

One session, one instance it brought up itself, one PDF the recorded corpus has never seen, and
a browser. Two modes, two readings:

| mode | what the person gets | how long | cost |
|---|---|---|---|
| `proxy` | `published`, **1 finding**, correct, grounded at its quotation, basis `measured` | **9.1 s** from pressing Start run | **USD 0.018305** for 3 pages |
| `recorded` | `failed`, nothing published, the screen printing a bare code | **16.1 s**, of which **10.0 s is a retry ladder waiting for a local file** | nothing |

Everything else in wave 29 comes out of the right-hand column of that table, and neither item
would have been found by a test. The programme had **1998 passing assertions** and not one of
them said *this takes sixteen seconds and ten of them are spent waiting for a file that is never
going to appear.*

That is the generalisation worth keeping: **a suite measures correctness; only a person measures
the experience.** The `recorded`-mode row is not a failing test. It is a correct outcome,
reported correctly, delivered ten seconds late in a sentence nobody can read.

## 3. Three sentences the application said that were not true

**`W29-RETRY` — "a dependency is unavailable" for a file that is simply absent.**
`RecordedAdapter.complete` read a file from a local directory and, when it was not there,
reported `dependency_unavailable` — a **transport** condition, marked `retryable: true` in the
frozen catalog — for a **local, deterministic** one. The retry policy was right to ladder it;
the adapter was wrong about itself. The argument that settles it is in the same file: **the same
module already reported `analysis_input_invalid` for key mismatch, for an unsupported version and
for a malformed body. Absence was the only one of four dressed as an outage.** Repaired, the run
takes **~6.1 s instead of 16.1 s**. The class was swept and closed at two members — `live.py:51`
did the same thing with an `ImportError`.

And it left something behind that matters more than the ten seconds. **Three test fixtures
induced "an unreachable provider" by pointing a `RecordedAdapter` at an empty directory.** They
were repaired rather than deleted, because deleting them would have quietly dropped the coverage
they claimed; and `p02_journey/test_explicit_failures.py` had been **really waiting `(2.0, 8.0)`
on every battery run** since the day it was written.

**`W29-SAY` — a screen printing an identifier where every neighbouring line is a sentence.**
Now a failed run renders the code *and* a sentence for every one of the twenty-two catalog
reasons, with an honest default for a twenty-third. Each sentence restates that code's own
`summary` from the frozen catalog and adds nothing; the one for `dependency_unavailable` earns
its place mostly by **what it refuses to say**, because the catalog groups four unrelated
dependencies into that one reason and the screen must not guess which.

**`W26-HOST` — a security claim this repository had carried since wave 14.** The provider
credential is kept out of `--env-file` *"and therefore never appears in `docker compose
config`"*. **It appears.** Compose v5.3.1 resolves `env_file:` into `environment:` and prints
the value in clear. What the channel genuinely buys is that those names never enter compose
**substitution** — real, and not what the sentence said. `config` output must be treated as a
secret: it also prints the API token and both passwords. By contrast the TLS private key
genuinely cannot appear there, because a bind mount is a path — sentinel test, zero hits.

## 4. The narrow-list class, which has now bitten three times

`W27-WEB` repaired `D-40`: `PC01_ERROR_CODES`, the frontend's list of codes it will name, **was
short by four, not by one** — and a test asserted `isPc01ErrorCode('storage_integrity_error')`
is `false` **while a screen rendered it**. The test agreed with the narrow list instead of with
the contract. The repair was not four more entries; it was a **derivation**, so the next
divergence reddens.

`W29-SAY` was then told to key its sentence table on that same list, measured instead, and found
it is **the wrong authority for that screen**: `PC01_ERROR_CODES` is the subset the operations
can put in an *error envelope*, while `terminal_reason` is a field on a **200** response
constrained by the **whole** catalog. Four catalog codes sit outside it and are legal there. In
the session's own words, keying on it *"would have shipped a list narrower than its surface for
the third time."*

**I wrote here, before wave 30 measured it, that these were three instances of one shape:
a hand-written subset standing in for a set the contract defines. `W30-LISTS` was asked to
say so if its census disagreed, and it disagreed. Corrected 2026-09-21; the paragraph above
is what I thought, and this is what is true.**

They are **three different shapes**, and only the first is the class a guard can close:

- **`D-40` is the class.** A hand-kept list disagreeing with its authority, with nothing
  reading either to notice.
- **`D-18` is a hand-maintained *digest*.** `FRONTEND_LOCK.json` records a sha256 by hand. It
  is not a subset of anything, and its cost appears only at change time.
- **`W29-SAY` is not a member at all**, and this is the correction that matters. By the time
  that session was dispatched, `PC01_ERROR_CODES` **had already been derived** — `W27-WEB`'s
  `D-40` repair had landed, and the derivation is still green. The list was not wrong. What
  `W29-SAY` avoided was a **consumer reading the wrong authority**, and a perfect guard on
  `PC01_ERROR_CODES` would have caught nothing. Its defence is a different thing entirely:
  `Record<ErrorCode, string>`, keyed on the whole catalog, so the type system will not let a
  reader address a narrower set.

The real common thread is one level up, and it is not something wave 30 could close: **a
second description of something, maintained by hand, with nothing tying it to the first.** A
subset is one shape; a digest is another; a consumer reading the wrong description is a third,
and no guard catches that one — only a session that measures which authority a field is
actually constrained by.

`web/src/shared/api/run-state.ts` remains the standard for the first shape, with one
qualification wave 30 added: its compile-time proof shows every state is **classified**, not
that the classification is **right**, because the generated enum carries no terminal flag. A
twenty-third state filed into the wrong half would still compile. `state-machines.json` has
carried `machines.audit_run.terminal` explicitly all along — the split was never unknowable,
only unread — and both sides of the wire are now pinned to that one clause.

## 5. The wave that found nothing, and why it is not a wasted wave

`W27-REFUSE` drove six wrong files into a browser: not a PDF, an encrypted PDF, an oversized
one, and three more. **Six true, specific, actionable refusals. No repair was needed and none
was made.** Not one reached `server_error`, `unknown` or `transport`; not one fell back to the
generic *"The upload failed on the server."*; no version was published in any of the six.

The dispatch had said in advance to report that plainly if it happened, and it happened. The
deliverable became the **measurement and the instrument** — and `W28-GUARD` then put that
instrument under the gate, so a renamed marker or a reworded sentence now reddens instead of
waiting for someone to remember. Its own first finding was that **the three additions
`W27-REFUSE` named were not the right three**, which is the shape of every wave in this
programme: the session after next measures the brief.

## 6. What the integrator got wrong

- **Passed on three of `W27-REFUSE`'s claims about manifest gaps without measuring them.** One
  of the three was right. `W28-GUARD` measured all three and said which.
- **Predicted a sentence no screen renders** — *"a required dependency is unavailable"*. It
  exists exactly once in the tree, as an OpenAPI 503 `description`.
- **Read a gate green off `tail`'s exit code**, and **merged before pushing**, leaving
  `origin/dev` eighteen commits behind while a dependent session provisioned. That session
  stopped at its stop line and was right to. The rule is merge → gate → push → dispatch.
- **Four ownership globs matched nothing**: `web/src/_pages/run-*/**` (the directory is `run/`),
  `web/src/features/run/**` (does not exist), and `web/src/app/**`, which is nine six-line
  delegations that could not have held the defect. **List the directories before writing an
  ownership line.**
- **Left `docs/program/CURRENT_STATE.md` four waves stale** — the file `AGENTS.md` §1.1 makes
  mandatory reading — and repeated *"eight criteria"* in briefs and reports for four waves when
  the certification record has **ten**. Both corrected on 2026-09-21 by counting rather than by
  re-reading the sentence.

## 7. What these waves hand forward

- **The stand is the tree.** `auditmanager-w19a` on 31500, `proxy` mode, redeployed from
  `ac7c348` and verified file by file. It is the only stand on this host; the two abandoned ones
  went under `R-6`.
- **`R-1` is the whole of what blocks `PA-01` criteria 1 and 2**, and `W26-HOST`'s claim is the
  narrow, checkable one: **nothing in this repository is now the reason they stay open.**
  Criterion 1 needs a machine; criterion 2 needs a certificate, and `infra/deploy/proxy/` is a
  TLS path that is inert until one appears.
- **`D-46`** — a failed run cannot say *which* dependency, because `safe_detail_keys` live on
  the error envelope and a 200 reading is not one. It needs the owner: a reseal either way.
- **`D-9`** — the norms corpus, waiting on `R-9`, which placed it after the owner's own manual
  testing. The stand being current is the last thing that was in the way of that.
