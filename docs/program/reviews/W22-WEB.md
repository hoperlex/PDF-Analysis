# W22-WEB — the caption, the status code, and three instruments that lie

**Session:** `W22-WEB` · **Branch:** `agent/w22-web` · **Worktree:** `/root/w22web`
**HEAD on arrival:** `313e753` — *docs(register): three rows from the committed journey, and D-27 measured again*
**Started:** 2026-09-19 12:43:58 UTC

---

## 1. Base measurement (my own, before any edit)

`make gate` on `313e753`, lane `gate-w22b`, `POSTGRES_PORT=55900`, `S3_API_PORT=59500`,
`S3_CONSOLE_PORT=59501`, `POSTGRES_DB=audit_w22b`, bucket `auditmanager-gate-w22b`:

| component  | measured                                      |
| ---------- | --------------------------------------------- |
| battery    | 1817 passed, 5 skipped, 168 subtests, 220.82s |
| foundation | 35 passed                                     |
| frontend   | 681 passed, 47 files                          |
| exit code  | `0` — from `$?`, never through a pipe         |

Matches the brief's stated base exactly.

---

## 2. `D-25` — the caption that sends an expert to the wrong place

### What it said, and what it says now

Before, `quotation.ts:53`:

```
page 2, chars 712–746
```

After:

```
page 2, characters 712–746 of the whole document, not of page 2
```

**Screenshot-equivalent of the rendered text.** A cold browser (one process, throwaway
profile, no cache or storage) against `next build` + `next start` on `:31622`, upstream the
alpha API, navigating to the review screen of `run_01M2TB4QP6B784MQ7NN1TFFP79`. This is
`document.body.innerText`, unedited:

```
page 2page 6recorded
Quotations on page 2
Степень огнестойкости здания — II.

page 2, characters 712–746 of the whole document, not of page 2

Page-level navigation only: no highlight overlay and no bounding box. The quotation
above is the exact string the grounding gate verified at its anchor.
```

`document.querySelectorAll('.am-quotation__anchor')` returns exactly
`["page 2, characters 712–746 of the whole document, not of page 2"]`.

### The argument

The brief offered three options: page-local offsets, no offsets, or the global range
labelled as global. **The first is not available and the second costs a fact the screen
needs**, so the third is what I did.

**Page-local is not available, and the brief's reason for thinking it was is wrong.** The
brief says *"`pages.ts` already knows how to convert."* It does not, and it says so itself
at `pages.ts:10–12`: *"Nothing here re-derives a page from a character offset… only the
backend holds that layer."* A page-local offset is `char_start` minus the page's own start
in the prepared text layer. The frozen `Evidence` schema carries `page_number`,
`char_start`, `char_end`, `quote`, `evidence_ordinal` and an optional `block_id` — and
nothing else. There is no page-start offset anywhere on the wire, and no page-text
endpoint: I checked all twelve paths of the contract. The page pane is the PDF's own bytes
in an `<object>`, not extracted text. A client-side conversion would have to re-derive the
text layer, which is the one thing `P3-WEB-02` forbids as a non-goal. **What pages.ts knows
is the convention, not a conversion.**

**Dropping the range is worse than it looks.** `anchorMatchesQuotation` renders an alert
when the declared span disagrees with the string beside it — *"The declared span length
does not match this quotation."* An alert about numbers the reviewer cannot see is not
actionable. The anchor is also the thing the grounding gate verified; it is the claim being
checked.

**So the caption states its own convention.** The brief's test is that *"a reader must be
able to act on it without being told which convention it uses"*, and `of the whole
document, not of page 2` meets it in the only way I could find that needs no second
sentence anywhere: it names the convention positively **and** denies the wrong reading
explicitly, naming the same page a second time so the negation cannot be read as referring
to some other page. `chars` became `characters` because the abbreviation reads as a unit of
measure and the full word reads as a description.

### The figures in the brief are shifted by five

The brief says the quotation is at **707–746**, page-local **198–237**. The live anchor,
read back from `GET /v1/runs/{run_id}/findings` on the alpha stack, is **712–746**, span 34,
quote length 34 — checked against every evidence item in that run:

```
page 2 chars 712-746 span=34 len=34      page 6 chars 2623-2658 span=35 len=35
page 3 chars 1287-1352 span=65 len=65    page 7 chars 3026-3091 span=65 len=65
page 8 chars 3470-3512 span=42 len=42
```

There is no `707` in the run. The brief's two figures are internally consistent with each
other (both spans 39) and both sit five below the tree, so they look like one measurement
taken against something else. **The row's substance is untouched**: 712 is still past the
end of a 539-character page, which is the whole of the danger. I cited `539` rather than
re-measuring it — it is a backend figure from the prepared text layer and is not reachable
from the browser — and said so in the code, because the point does not depend on it being
exact.

Everything committed now cites **712–746**, measured.

---

## 3. `D-28` — the 200, and the network-idle finding beside it

### The two are **not** the same cause, and the second one is not what the brief says

I measured them separately and deliberately did not assume a relation.

**The 200.** Confirmed exactly as briefed, on the alpha stack at base:

```
307  /                       200  /projects/nonexistent-abc       404  /nosuchtoplevel
200  /projects               200  /projects/<real>/runs/zzz       404  /bff/v1/nope
```

Cause: a Next.js dynamic segment matches any string, so `/projects/<anything>` resolves to
the project route. The screen then checks the shape client-side and renders
`UnsupportedState` — *"That is not a project address… Nothing was requested."* The screen
says the right thing; the status code does not.

**The network-idle finding is false as stated.** The brief says *"no route here is ever
network-idle; at least one request per screen never emits `loadingFinished`."* Measured with
the committed journey's own CDP client, one **cold browser process per URL**, ten routes:

| route                                   | open requests | settle  |
| --------------------------------------- | ------------- | ------- |
| `/`                                     | 0             | 859 ms  |
| `/projects`                             | 0             | 857 ms  |
| `/projects/<real>`                      | 0             | 852 ms  |
| `/projects/<real>/documents/<real>`     | 0             | 857 ms  |
| `/projects/<real>/versions/<real>`      | 0             | 854 ms  |
| `/projects/<real>/runs/<real>`          | 0             | 859 ms  |
| `/projects/<real>/runs/<real>/review`   | **1**         | 1509 ms |
| `/projects/nonexistent-abc`             | 0             | 852 ms  |
| `/projects/<real>/runs/<absent>`        | 0             | 807 ms  |
| `/nosuchtoplevel`                       | 0             | 804 ms  |

Nine of ten routes reach `inFlight === 0`. The ~855 ms settle proves it: `#settle` returns
either on `inFlight === 0 && quietFor >= 700`, or on the 1200 ms quiet floor, or on the
10 s timeout. 855 ms is below 1200, so only the first branch can have produced it.

**One route has an open request, and its cause is not the application.** Every exchange of
the review screen, cold:

```
finished [Document] 200  /projects/<real>/runs/<real>/review
finished [Fetch   ] 200  /bff/v1/runs/<real>
finished [Fetch   ] 200  /bff/v1/runs/<real>/findings
finished [Fetch   ] 200  /bff/v1/findings/<fnd>
finished [Fetch   ] 200  /bff/v1/findings/<fnd>/decisions
finished [Fetch   ] 200  /bff/v1/versions/<ver>/content
finished [Document] 200  blob:/818e5f56-8404-4ba3-8286-0063705e91c2
OPEN     [Document] 200  chrome-extension://mhjfbmdgcfjbbpaeojofohoefgiehjai/index.html
```

Every application request finishes, including the PDF bytes and the `blob:` document. The
single open exchange is **Chrome's built-in PDF Viewer extension page** — not a request the
application makes, and not a request to this origin. It exists because the evidence viewer
embeds `<object type="application/pdf">`, which is the only such element in the tree
(`evidence-viewer.tsx:147`, one grep hit in `web/src`). `OD-09` is untaken, so the browser's
own viewer is the deliberate choice, and this is its cost.

**So: two unrelated causes.** The 200 is Next.js routing. The one non-idle route is a
browser component extension instantiated by an embedded PDF. Nothing links them beyond
having been found in the same sitting. The journey's `#settle` comment — *"a Next.js screen
on this origin leaves at least one request open after the page is fully rendered"* —
generalises one route to all of them; the quiet-based settle it justifies is still the right
design, for the right reason on one screen.

### An unrelated measurement worth keeping

`Page.navigate` costs **~25 000 ms on the first navigation of a fresh browser process** and
**10–13 ms on every one after it**, on every route including the static 404, while `curl` to
the same URL returns in 3.6 ms. It is a browser start-up cost, not a route property. The
journey opens one cold browser per route by design, so it pays this once per route. I did
not chase it — `tests/e2e/**` is `W22-E2E`'s — but a journey whose wall clock is dominated by
a constant nobody has named is worth someone naming.

### What I did, and the half I refused

**Done: the malformed-address half.** Each dynamic route now checks its segments against
the contract's own pattern and calls `notFound()`.

I did **not** stop at "this is a routing change with a blast radius", because I measured
that it is not. The decisive evidence was already in the tree: `app/page.tsx` calls
`redirect()` from a server component, and that produces a genuine **307 on the wire** — the
first line of every status table above. `notFound()` is the same Next.js navigation signal
at the same seam. There is no middleware, no `output: 'export'`, no rewrite; the check is a
pure synchronous regex over a contract constant, so it costs no request. `entities/audit-run`
gains `looksLikeRunId`, which three of the four segment types already had —
`/projects/<real>/runs/zzz` was the one malformed address that still reached the network.

Measured on the wire, `next build` + `next start`:

```
404  /projects/nonexistent-abc                      (was 200)
404  /projects/<real>/runs/zzz                      (was 200)
404  /projects/<real>/versions/bad                  (was 200)
404  /nosuchtoplevel                                unchanged
200  /projects/<real>                               unchanged
200  /projects/<real>/runs/<real>/review            unchanged
200  /projects/<real>/documents/<real>              unchanged
```

**Refused: the nonexistent-resource half.** `/projects/<real>/runs/run_0000…0` is a
*well-formed* address the server has never heard of. It still answers **200** and renders an
error state, and I left it that way on purpose. Answering 404 there requires the server's
answer, which requires a server-side fetch, on screens that fetch on the client — and that
client fetch is not an accident. It is `D-16`'s repair: before it, `project-detail` rendered
from React state left by the upload that had just happened, so a fresh tab made **zero** API
calls over a project whose data had all survived. Moving the first read back to the server
to recover a status code would touch the credential seam, React Query's cache, streaming and
every loading state, to fix a case that is already legible to a human reader. **That half is
larger than it looks, and this is why.** It is asserted as deliberate in
`routes.test.ts`, so it cannot be closed silently by accident.

A root `web/src/app/not-found.tsx` carries the message. The client components keep their own
`UnsupportedState` branch: it is now unreachable through routing, and it stays as the
component's own contract, tested where it lives.

---

## 4. `D-29`, and half of `D-26` — the lock and the guard

**`D-29`.** `npm run test:unit` forwarded to `reserved-forwarder.mjs` and exited **1** while
all **38** files under `web/tests/unit/` passed. They run under `npm test`, so `make gate`
covered them and nothing was unguarded — the named command simply lied. It now runs
`vitest run tests/unit`: **38 files, 567 tests, exit 0**.

**The lock.** `web/FRONTEND_LOCK.json` `reserved_scripts` still reserved `e2e:pc01` for
`P3-QA-01`, and `reserved-forwarder.mjs` carried a dead entry for it. **Changing it was
exactly removing a stale reservation, so I did not stop.** The lock's seal is its *digests* —
lockfile, OpenAPI bytes, generator script, generated files — every one recomputed by
`frontend-lock.guard.test.ts`. `reserved_scripts` is a plain declarative block, and **no test
in the repository referenced it**: I grepped `web/tests` and `tests` for `reserved` and found
nothing. That is why it could go stale. `package.json` already pointed `e2e:pc01` at
`W21-E2E`'s committed journey; only the other two thirds had not been told.

`csv:verify` stays reserved. `web/tests/contract/csv/` does not exist.

Releasing a name is a three-file edit and nothing required all three, so
`web/tests/guards/reserved-scripts.guard.test.ts` now does: a name the forwarder reserves
must be routed to the forwarder and listed in the lock; a name routed to a real command must
be reserved in neither.

**The `D-23` guard, and the brief's line number.** The brief says
`web/src/app/bff/v1/[...path]/route.ts:16` still says "twelve paths". **Line 16 is the one
line in that file that is correct** — the contract declares 12 paths, counted from
`openapi.json`. The stale claims were on **line 14** (*"the same twelve operations"*) and
**line 20** (*"not to twelve handlers"*), against fifteen operations.

Widening the guard to `web/src/app/bff/` took three changes, not one, and the second is the
one that mattered:

1. `SCANNED_TREES` gains the tree; the suffix set gains `.ts`/`.tsx`.
2. **A claim wrapped across a JSDoc continuation line was invisible to the pattern.** The
   file reads `the same twelve\n * operations`, and `_CLAIM` matches `<number>[ -]<noun>`,
   so it matched nothing there. Widening the scan *alone* would have added the file and
   reported only `twelve paths` — the correct figure — while staying silent on both stale
   ones. `_unwrap` now joins wrapped comment lines first, for `*` and `#` markers, and
   refuses to join across a blank line or a `*/`.
3. **`handlers` was not a surface noun**, so the line-20 claim carried the same stale figure
   past the check. It now maps to `operations`. It is the only `<n> handlers` phrase in any
   scanned tree.

Every count is still read out of the documents and nothing is written down. The guard also
**refuses a historical count**: my first draft of the replacement paragraph recalled the
pre-`R-5` figures, and it reddened. That is the right answer, so the sentence is gone rather
than registered in `LOCAL_COUNTS` — a file that narrates a surface the document no longer
declares is how the fifth of these was made.

---

## 5. Mutations — 27 applied, 27 killed, 0 survivors

Each was applied to the working tree **after a commit**, with the suite run against it, and
the file restored by `git checkout -- <one named path>`. Never `git checkout .`.

### The caption (`quotation.ts`) — suite `tests/unit/review`

| # | mutation | killed by |
|---|---|---|
| M1 | drop the convention clause entirely — **the `D-25` defect restored** | *the rendered anchor says the range is the document's, not the page's*; *is exactly this string, for the case D-25 was found on*; *names the convention…* |
| M2 | `of page N` instead of `of the whole document` | the same four |
| M3 | revert the noun to the ambiguous `chars` | *states the page and the character range beside the quotation*; *…never shows a bare "chars" range with no convention* |
| M4 | negate a different page than the one named | *denies the page-local reading explicitly, naming the same page again* |
| M5 | print `char_start` where `char_end` belongs | *states the page and the character range…*; *is exactly this string…* |
| M6 | swap the range ends | the same |
| M7 | off-by-one, "to make the offsets 1-based" | the same |
| M8 | en dash becomes a hyphen | *is exactly this string…*; *passes both offsets through unchanged…* |
| M9 | drop the page number, keep only the range | *states the page and the character range…* |

### The reserved-scripts guard — suite `tests/guards/reserved-scripts.guard.test.ts`

| # | mutation | killed by |
|---|---|---|
| M10 | `test:unit` points back at the forwarder — **`D-29` restored** | *every script routed to the forwarder is a name the forwarder reserves*; *test:unit runs the suite it is named after* |
| M11 | `test:unit` runs only a subset of the directory it names | *test:unit runs the suite it is named after, and not a subset of it* |
| M12 | the lock keeps a reservation the forwarder released — **`D-26` restored** | *the lock reserves exactly the names the forwarder reserves* |
| M13 | the lock drops a reservation the forwarder still holds | the same |
| M14 | the forwarder re-reserves a landed name, on one line | **SURVIVED** — see below; killed after the repair by four assertions |

### The `D-23` guard and its subject — suite `test_surface_counts_in_prose.py`

| # | mutation | killed by |
|---|---|---|
| M15 | a sixth stale count, wrapped across a JSDoc line | `test_the_api_prose_states_the_surface_this_document_declares` |
| M16 | a sixth stale count, as a handler figure | the same |
| M17 | the paths figure goes stale too | the same |
| M18 | the unwrapper stops joining continuation lines | `test_a_claim_wrapped_across_a_comment_line_is_still_one_claim`; `test_a_stale_count_is_caught[…]` |
| M19 | the bff tree is dropped from the scan | `test_the_guard_reaches_the_bff_route_handler` |
| M20 | `.ts` files are no longer read | the same |
| M21 | `handlers` stops being a surface noun | four tests, incl. `test_the_bff_handler_still_makes_a_claim_this_guard_can_read` |

### The 404 routing — suite `tests/unit/screens`

| # | mutation | killed by |
|---|---|---|
| M22 | the project shape check is removed — **`D-28` restored** | *a malformed project address 404s instead of rendering the project screen* |
| M23 | the run route trusts its parent segment | *a malformed PARENT 404s even when the child segment is well formed* |
| M24 | the review route trusts the run id | *a malformed run address 404s, for both the run screen and the review screen* |
| M25 | the check is inverted — only valid addresses 404 | three, incl. *a well-formed address is NOT a 404 — the guard is not simply always red* |
| M26 | `redirect('/projects')` instead of 404 — a **307** to an instrument | *a malformed project address 404s…* (the digest is asserted, not the throw) |
| M27 | `looksLikeRunId` accepts anything | *a malformed run address 404s…* |

### The survivor, and what it was

**M14 survived a green suite, and not because an assertion was weak.** Re-reserving a landed
name as `'test:unit': { owner: 'Gate B', … },` on a single line left `package.json` running
vitest and the lock silent — three-way drift, exactly what the guard exists to catch — and
all ten tests passed.

The cause was in my own detector. `forwarderReservations` matched `/^ {2}'([^']+)': \{$/m`,
requiring the entry to *open a block* at end of line. A single-line entry was not read at
all, so there was nothing for any assertion to disagree with. **A detector that depends on
the formatting of the thing it inspects is checking a spelling, not a fact.**

I did not argue it away. The reader now matches a key at the map's own indent however the
value is written, and stops at the map's closing brace; two new tests pin the single-line
spelling and the boundary. Re-run, M14 is killed by four assertions at once
(`d1ab0ea`… committed as its own change so the survivor and its repair are both in the
history). `W19-RUN`'s standard — constrain the rendered reason rather than argue the mutant
equivalent — applied to a guard rather than a screen.

---

## 6. The gate

Full `make gate` on the finished tree, lane `gate-w22b`. Exit code read from `$?`.

| component  | base (`313e753`)     | after                | delta                  |
| ---------- | -------------------- | -------------------- | ---------------------- |
| battery    | 1817 / 5 sk / 168 st | see §7               | +7 (`D-23` guard)      |
| foundation | 35                   | 35                   | —                      |
| frontend   | 681 (47 files)       | see §7               | +36 (2 files)          |
| exit code  | `0`                  | see §7               |                        |

---

## 7. What was false in this brief

Fourteen stale premises were expected. I found **four**, and one of them inverted the
instruction it carried.

1. **"`pages.ts` already knows how to convert."** It does not, and it says the opposite at
   `pages.ts:10–12`. It knows the *convention*. No page-start offset exists anywhere on the
   wire, so a page-local caption was never available to choose. This is the premise the whole
   of Step 1 turned on.
2. **"`route.ts:16` still says 'twelve paths'."** True textually, and **line 16 is the only
   count in that file that is correct**. The defects are on lines 14 and 20. Repairing what
   the brief named would have broken a true statement and left both false ones. This is the
   brief's own warned-about shape: *a file named for a defect it could not have held* — here,
   a line.
3. **"No route here is ever network-idle; at least one request per screen never emits
   `loadingFinished`."** Nine of ten routes are idle, with settle times that prove which
   branch returned. One route is not, and its open exchange is Chrome's bundled PDF viewer
   extension — not the application, not this origin, and not related to the 200.
4. **"page 2, chars 707–746 … page-local 198–237."** The live anchor is **712–746**. Both
   figures sit five below the tree. The row's substance is unaffected.

Two things in the brief I want to confirm as **true and load-bearing**: the `D-25` data
really is correct while the caption was wrong, and `/projects/<anything>` really did answer
200 while only top-level paths 404'd. Both measured before I touched anything.

---

## 8. Constraints observed

Touched: `web/**`, `docs/program/reviews/W22-WEB.md`, and
`tests/contract/api_v1/test_surface_counts_in_prose.py` (the guard I widened, as permitted).
No `src/`, no `contracts/`, no `infra/`, no `tests/e2e/**` — the journey there was **read and
driven** as an instrument, never edited. `DEBT_REGISTER.md` untouched. No tag, no push to
`main`, no merge.

One measurement at a time on this lane; no subagents dispatched. Every process stopped by
PID (`388692`, `388750`, `457344`), never by name — this host runs other sessions' browsers
and stacks. No image built: `next build` produces `.next/`, not an image. Disk 15 GB on
arrival, 12 GB at the end.
