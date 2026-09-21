# `W27-REFUSE` — what a person actually sees when they drop the wrong file in

**Session** `W27-REFUSE`. **Base** `5b3a040` (`origin/dev` on arrival). **Branch**
`agent/w27-refuse`. **Worktree** `/root/w27refuse`. **Lane** `gate-w27b`.

This file was opened before the first edit, per the dispatch, and filled as each drive
produced its reading. Nothing below was written before the command that produced it had run.

## 0. Status

**Six fixtures driven through the browser. Six true, specific, actionable refusals. No
repair was needed and none was made.**

Not one of the six reached `server_error`, `unknown`, `unrecognized` or `transport`. Not
one rendered *"The upload failed on the server."* — the generic sentence
`upload-failure.ts:193` keeps for codes it cannot name. Every refusal named the rule the
file broke, in words, with the server's own `constraint` classifier beside it where a
server produced one, and no version was published in any of the six.

**This is the outcome the dispatch said to report plainly if it happened, and it happened.**
The deliverable is the measurement and the instrument. Two findings are recorded below and
**both are outside this session's grant** — they are reported, not repaired.

## 1. The stack, probed before it was trusted

The dispatch said to run the probe rather than take its word. Run:

```
$ ./infra/deploy/verify-deployed.sh ; echo "EXIT=$?"
verify-deployed.sh: instance   auditmanager-w19a
verify-deployed.sh: repository /root/projects/PDF-Analysis at 5b3a040
verify-deployed.sh: proxy      http://127.0.0.1:31500
  src/ 141 files, identical      contracts/ 34 files, identical
  db/    9 files, identical      fixtures/recorded/ 7 files, identical
  docs/program/P02_LOCK.json 1 file, identical
  infra/deploy/serve.py      1 file, identical
  web/ 218 files, identical
verify-deployed.sh: the deployed stack IS this tree (5b3a040).
EXIT=0
```

`5b3a040` is also `origin/dev`, which is this branch's base. **The screens measured below are
the screens this branch builds.** The stack was left answering; nothing was restarted, no
image was built, and no container belonging to another lane was touched.

## 2. The instrument: the committed journey sufficed, and needed no new primitive

The dispatch asked whether `tests/e2e/pc01/journey/` could do this. **It could, unchanged.**

`cdp.mjs` already exposes `withColdBrowser`, and its `Page` already has `goto`, `describe`,
`click`, `fill`, `attachFile`, `waitFor`, `evaluate`, `settle`, `location`, `exchanges`,
`consoleErrors` and `pageErrors`. That is the whole of what a refusal drive needs. **No line
of `cdp.mjs` was changed, no dependency was added, and `web/package.json` and
`web/package-lock.json` are untouched.** `W22-E2E`'s advice — *"price the primitives, which
now exist, and not the walk"* — is correct, and this is the second session to confirm it.

Three properties of `cdp.mjs` did real work here rather than merely being present:

* **`click` refuses a disabled control.** Three of the six fixtures disable `Upload`, so a
  harness that used `element.click()` would have pressed a dead button and recorded
  something. Here it is an assertion instead: the drive reads `submitDisabled` and does not
  press.
* **`settle()` collects response bodies after an action, not only after a navigation.** The
  `422` envelopes below are the bodies the *browser* received. Nothing in this review is a
  parallel `curl`.
* **`attachFile` uses `DOM.setFileInputFiles`**, so the browser reads the bytes and reports
  its own `type`. That is how `not_a_pdf.txt` arrives as `text/plain` and
  `companion_archive.zip` as `application/zip` — which is the input `precheckUploadFile`
  actually branches on. A harness that built a `File` in page script would have been
  measuring its own construction.

**What it lacked: nothing, at the primitive level. One thing, at the declaration level.**
`manifest.json`'s `write` section declares steps that *succeed*. It has `forbids_rendered`
and no `requires_rendered`, and the gate-time guard
`tests/e2e/test_pc01_journey_conformance.py` reads it on that understanding — every status
it checks is one the contract publishes for a success, and every marker it looks for is one
a working screen shows. Carrying a refusal needs a `requires_rendered`, a
`refused_by: client|server`, and a guard that knows a `422` is a declared status too.

So the six cases are declared in `tests/e2e/pc01/journey/refusals.mjs` itself, beside the
code that drives them, and **the cost is stated rather than hidden: that table is not read
by `make gate`**, so a renamed marker turns this script red only when someone runs it. That
is `W21-E2E`'s stated residue one notch worse, and it is named as the next session's work in
§7, not papered over here.

### The drive is shown able to fail

A refusal drive that cannot go red is a screenshot with an exit code.
`tests/e2e/pc01/journey/fixtures/redden-refusals.json` declares two cases that are **not
true of this application** — a client-side refusal claimed to happen at the server, a
constraint no envelope carries, a classification the screen does not use, and two sentences
no screen renders:

```
$ node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31500 \
    --cases tests/e2e/pc01/journey/fixtures/redden-refusals.json ; echo $?
-- not_a_pdf.txt (ENV-PDF) 4 FINDING(S)
   ! this file declares the refusal happens at the server, and the drive shows it at the client.
   ! the pre-check refused this file client-side ('not_pdf'), so the server's typed refusal
     never reaches a person.
   ! the browser made 0 upload request(s); exactly one was expected.
   ! the screen never rendered "the server examined this file".
-- encrypted.pdf (ENV-ENCRYPTED) 3 FINDING(S)
   ! the envelope carried details.constraint "not_encrypted" and this file declares
     "a_constraint_no_envelope_carries".
   ! the screen classified it 'unsupported_input' and this file declares 'checksum_mismatch'.
   ! the screen never rendered "Enter the document password to continue".
2 fixture(s) driven, 7 finding(s), 81636 ms
1
```

**Measured 2026-09-21: exit `1`, seven findings, one per wrong claim.** The fixture is read
by nothing else, so its deliberate wrongs redden nothing.

## 3. The six drives

```
$ node tests/e2e/pc01/journey/refusals.mjs --origin http://127.0.0.1:31500 ; echo $?
seeded project prj_01M31KA1NP2KR1NBK6QDSW9GS4 ("W27-REFUSE 2026-09-21T09-03-21-208Z")
6 fixture(s) driven, 0 finding(s), 151679 ms
0
```

One project, seeded through the app's own **Create** control, so nothing existing on the
shared stack was disturbed. Each fixture then got **its own cold browser process with its
own throwaway profile**, landing on `/projects/{project_uid}` and using the app's own file
input and **Upload** button. Two full passes were run (`prj_01M31JYZ2FHDYDKMB685WPNF9Y` and
`prj_01M31KA1NP2KR1NBK6QDSW9GS4`); the readings agree in every field, and the second was
driven from the committed, clean tree.

| | fixture | rule | who refused it | on the wire | screen classification |
|---|---|---|---|---|---|
| 1 | `not_a_pdf.txt` | `ENV-PDF` | **the browser** | *nothing was sent* | `[data-precheck-problem="not_pdf"]` |
| 2 | `companion_archive.zip` | `ENV-PDF` | **the browser** | *nothing was sent* | `[data-precheck-problem="not_pdf"]` |
| 3 | `oversize.pdf` | `ENV-SIZE` | **the browser** | *nothing was sent* | `[data-precheck-problem="too_large"]` |
| 4 | `encrypted.pdf` | `ENV-ENCRYPTED` | **the server** | `POST …/documents → 422` | `[data-upload-failure="unsupported_input"]` |
| 5 | `image_only.pdf` | `ENV-TEXT` | **the server** | `POST …/documents → 422` | `[data-upload-failure="unsupported_input"]` |
| 6 | `too_many_pages.pdf` | `ENV-PAGES` | **the server** | `POST …/documents → 422` | `[data-upload-failure="unsupported_input"]` |

**Three of the six never reach the server from a browser.** That is `W24-CERT2`'s stated
reason for using `curl`, now measured from the other side rather than predicted: the file
input is `accept="application/pdf"`, and behind it `precheckUploadFile` reads the browser's
declared media type and the byte size, refuses on either, and **disables the Upload button**.
`submitDisabled` is `true` in all three cases and `false` in the other three — the control's
own state agrees with the panel, which is the part a screenshot would not have shown.

### What every screen said, before a file was even chosen

All six screens carry the envelope up front, above the control, which is what makes the
later refusal recognisable rather than a surprise:

```
What this accepts

One PDF per upload. No archive, no companion file and no second document.
At most 25 MiB.
At most 30 pages.
Not password-protected and not encrypted.
Every page carries extractable embedded text. A scanned or image-only PDF is refused;
text is never recovered by optical recognition instead.
```

`UPLOAD_ENVELOPE_RULES` in `web/src/entities/document-version/model/upload-envelope.ts`
says it exists so *"the panel can show the envelope before the user picks a file"*. **That
claim is true and was checked on screen, not read in a comment.**

### The exact text the screen rendered, per fixture

Verbatim from `innerText`, with `⏎` for the line breaks inside the panel. Every one of these
is the panel `web/src` renders, read out of the live DOM.

**1. `not_a_pdf.txt`** — attached as `text/plain`, 489 B. `Chosen: not_a_pdf.txt · 489 B`.

> This file is outside the accepted envelope. ⏎ That file is not a PDF. PC-01 accepts one
> unencrypted PDF and nothing else. ⏎ Nothing was sent. Choose a different file.

**2. `companion_archive.zip`** — attached as `application/zip`, 779 B.
`Chosen: companion_archive.zip · 779 B`.

> This file is outside the accepted envelope. ⏎ That file is not a PDF. PC-01 accepts one
> unencrypted PDF and nothing else. ⏎ Nothing was sent. Choose a different file.

**3. `oversize.pdf`** — attached as `application/pdf`, 27 303 204 B.
`Chosen: oversize.pdf · 26.0 MiB`.

> This file is outside the accepted envelope. ⏎ That file is larger than 25 MiB. ⏎ Nothing
> was sent. Choose a different file.

**4. `encrypted.pdf`** — 40 514 B, sent, refused `422`.

> This file is outside the accepted envelope. ⏎ The document is encrypted. This prototype
> accepts unencrypted PDFs only. (constraint: not_encrypted, field: content) ⏎ Correlation
> id cid-89acc1455f41e7d35b2eb0a1cfccf525 ⏎ No version was published and no run was started.

**5. `image_only.pdf`** — 246 242 B, sent, refused `422`.

> This file is outside the accepted envelope. ⏎ At least one page carries no extractable
> embedded text. This prototype never substitutes OCR for a text layer. (constraint:
> every_page_has_extractable_text, field: page_text) ⏎ Correlation id
> cid-c756c9c9d275310eb4ae4d0011ac285c ⏎ No version was published and no run was started.

**6. `too_many_pages.pdf`** — 66 487 B, sent, refused `422`.

> This file is outside the accepted envelope. ⏎ The document carries more pages than the
> accepted envelope allows, or carries none at all. (constraint: 1 <= page_count <= 30,
> field: page_count) ⏎ Correlation id cid-91b0bb61e7cd483519374d57b8725688 ⏎ No version was
> published and no run was started.

### "Nothing was sent" and "No version was published", checked rather than believed

Two of these sentences are claims about the system, not descriptions of a file, and a screen
that made either of them falsely would be the exact defect this session was sent to look for.
Both were checked from the recorded traffic, not from the sentence:

* **"Nothing was sent."** For fixtures 1–3 the browser made **zero** `POST` to
  `…/documents`. The drive asserts the count, so the claim would redden if a request
  escaped.
* **"No version was published and no run was started."** For all six the browser ended on
  `/projects/prj_01M31KA1NP2KR1NBK6QDSW9GS4` — never on a `…/versions/ver_…` address — and
  no `POST` answered 2xx. The project's document list still reads *"No documents in this
  project yet."* on the same screen, underneath.

Also checked, because they are cheap and this is the only session that will look: **zero
console errors and zero uncaught exceptions** across all six drives, and **no browser request
carried an `Authorization` header** (`T-6`), including the three that carried a multipart
body.

### How fast a person learns

| fixture | from choosing the file to the refusal on screen |
|---|---|
| 1–3 (browser) | **inside the settle window, < 704 ms** — no request, no round trip |
| 4–6 (server) | first reading `null` at 1–8 ms, **`failure` at the next poll, 253–261 ms** |

The server figures are bounded by this drive's own 250 ms poll, not by the application: the
true latency is *at most* 253 ms and is not resolved finer than that. Stated rather than
rounded down, because `W19-RUN`'s finding was a formatter that printed a 374 ms run to the
second.

## 4. The six verdicts

The question the dispatch asked is not "did it refuse" but **"does the screen tell a person
something true and actionable"**.

| | fixture | true? | actionable? | verdict |
|---|---|---|---|---|
| 1 | `not_a_pdf.txt` | yes | yes | **holds** — names the rule (*not a PDF*), states the consequence (*nothing was sent*), gives the next action (*choose a different file*), offers no retry that cannot help |
| 2 | `companion_archive.zip` | yes | yes | **holds** — same panel, and the envelope above it says *"No archive, no companion file"* in so many words |
| 3 | `oversize.pdf` | yes | yes | **holds** — *"larger than 25 MiB"* beside `Chosen: … · 26.0 MiB`, so the number the user needs and the number the rule uses are on the same screen in the same unit |
| 4 | `encrypted.pdf` | yes | yes | **holds** — the server's own sentence, the `not_encrypted` constraint, a correlation id, and an explicit statement that nothing was published |
| 5 | `image_only.pdf` | yes | yes | **holds** — and it answers the question a user would ask next (*"can't you OCR it?"*) before they ask it: *"never substitutes OCR for a text layer"* |
| 6 | `too_many_pages.pdf` | yes | yes | **holds** — see the note below; it is weaker than the other five and it is still true |

**None said `server_error`. None said "The request failed on the server."** The generic
branches exist — `upload-failure.ts:193` — and no fixture reached one.

**The one that is weakest, and why it is not a repair.** Fixture 6 renders *"more pages than
the accepted envelope allows, **or carries none at all**"*. The disjunction is the server's
own sentence for a two-sided constraint, and it does not tell the user their document has 31
pages. But it is **not untrue**, the constraint `1 <= page_count <= 30` is printed beside it,
and the limit *"At most 30 pages."* is on the same screen four lines above. The dispatch is
explicit — *repairs only where the screen says something untrue*, and *do not find something
to rewrite*. **Recorded, not repaired.** If an owner later wants the actual page count on
screen, that is a change to the server's envelope `details`, which is `src/**` and not this
session's.

## 5. Repairs

**None. No file under `web/src/**` was changed.**

`git diff origin/dev --stat` for this branch touches exactly three paths, none of them
application code:

```
 docs/program/reviews/W27-REFUSE.md                          | new
 tests/e2e/pc01/journey/refusals.mjs                         | new
 tests/e2e/pc01/journey/fixtures/redden-refusals.json        | new
```

Two things were found that **do** want repair. Both land in
`web/src/shared/api/` — the hotspot the dispatch reserved for `W27-WEB` — so both are
reported here and left alone.

### Finding 1 — `PC01_ERROR_CODES` is narrower than `web/src`'s own rendering, by two more codes than `D-40` names

`errors.ts:40` states the list's meaning as *"these twelve are the ones a PC-01 screen has to
be able to render"*. `D-40` records that `staged_upload_lost` is in the catalog and not in
the list. **Measured here, independently, by reading which codes `web/src` itself branches
on:** the entity failure classifiers have `case` arms for **`storage_integrity_error`** and
**`analysis_input_invalid`**, neither of which is in the twelve.

```
$ grep -rho "case '[a-z_]*'" web/src/entities/*/model/*.ts | sort -u
… storage_integrity_error … analysis_input_invalid …
```

`storage_integrity_error` is the *upload* screen's checksum-failure state — the third of the
three states `upload-failure.ts`'s own header says the PC-01 acceptance criteria name
separately. So a PC-01 screen does not merely *have to be able to* render a thirteenth code;
one of them already does, deliberately, with a title and a detail written for it.

**Nothing is broken** — a code outside the subset is still an `ApiError` and the envelope
reaches the panel, exactly as `D-40` says. The defect is the sentence.
**`W27-WEB` owns this file and is widening the list; this is two more rows for it, and the
count in the prose is what wants fixing, not just the array.**

### Finding 2 — the browser's 25 MiB pre-check makes the server's `max_bytes` refusal unreachable from a browser, and that is load-bearing for the proxy

The dispatch asked for this one by name: *"if the pre-check refuses it client-side, say so —
that is a finding about where the limit is enforced."*

**It does.** `oversize.pdf` is 27 303 204 B and never leaves the browser. So:

* `PA-01` criterion 9's `max_bytes` refusal — `422 validation_failed`, `field: file`,
  `constraint: max_bytes`, which `W21-CERT` recorded through `curl` — **cannot be reached by
  a user of this application.** The criterion is about HTTP and still holds; the *screen*
  never renders that particular server refusal, and no fixture in the corpus can make it.
* `infra/deploy/proxy/nginx.conf:42` sets `client_max_body_size 32m`. The browser's limit is
  25 MiB ≈ 26.2 MB, comfortably **under** it. That ordering is what keeps a user from ever
  meeting nginx's `413`, which would arrive as an HTML error page, decode as no envelope, and
  render as `transport` — *"The upload did not reach the API."* — a true sentence that names
  the wrong cause.
* **This is not a defect and nothing was changed.** It is an invariant nobody has written
  down: *the browser pre-check limit must stay below `client_max_body_size`.* Raise the
  envelope to 32 MiB without touching nginx and three of the six screens above quietly become
  a generic transport failure. Worth a register row; it is not one today.

`proxy_read_timeout 300s` is not approached by anything a browser can send here, since the
one input large enough never crosses the wire.

## 6. Base gate

## 7. What the next session gets

**The refusal cases are not guarded by `make gate`.** `manifest.json` cannot carry them
today, for a reason that is specific and small: its `write` section has `forbids_rendered`
and no `requires_rendered`, its statuses are checked against the contract as *success*
statuses, and it has no way to say *"this step is refused, and by the client"*. Three
additions — `requires_rendered`, `refused_by`, and letting a declared status be any status
the contract publishes for that operation — would let these six live in `manifest.json` and
be checked by `test_pc01_journey_conformance.py` like the other three steps. **That is the
next session's work, and it is a guard change, not a harness change: `refusals.mjs` would
shrink to a reader.**

Until then the residue is stated in the script's own header: a renamed marker attribute turns
these six red only when someone runs them.

## 8. False premises in the dispatch, and limits

**Checked and true:** the six fixtures exist and each violates exactly one rule;
`fixtures/synthetic/ar/README.md` documents each; `uploadDocument` declares exactly
`201, 401, 403, 404, 409, 422, 500, 503`; `verify-deployed.sh` exits 0 against `31500` at
`5b3a040`; `W27-WEB` is live in `/root/w27web` on `agent/w27-web`; `D-40` says what the
dispatch says it says; `D-28` is real and is why every verdict here is read from
`innerText`; criterion 9 holds through HTTP and was not re-measured.

**Two small corrections, neither of which changed any verdict:**

1. **`oversize.pdf` is "26 MB" in the dispatch and 26.0 MiB on disk** — 27 303 204 bytes,
   i.e. 27.3 MB. The distinction matters here and only here, because the rule it breaks is
   stated in MiB and the screen renders `26.0 MiB` beside a limit of `25 MiB`. Both readings
   are over the limit; the dispatch's number is the one that would confuse a reader checking
   whether 26 > 25 in the same unit.
2. **`npm --prefix web ci` works; `npm --prefix /absolute/path/web ci` does not.** The
   prescribed relative form exits 0 (184 packages, 4 s). Passing the same directory as an
   absolute `--prefix` fails `EUSAGE` — *"can only install with an existing
   package-lock.json"* — because `ci` resolves the lockfile against the working directory.
   Not a dispatch error; recorded so the next session does not lose ten minutes to it.

**Limits of this measurement, stated:**

* **Six fixtures, not six classes of refusal.** Three of the six break `ENV-PDF`/`ENV-SIZE`
  in ways the browser can see, so they measure one code path — `precheckUploadFile` — twice
  over. The server-side panel is measured three times, always through `validation_failed`.
* **Nine of the twelve `PC01_ERROR_CODES` were not rendered by anything here**, and neither
  was `storage_integrity_error`, the thirteenth. `unsupported_input` is the only
  `UploadFailure` kind this session put on a screen. A screen that renders
  `dependency_unavailable` or `idempotency_key_reuse` truthfully is unproven by this review.
* **One browser.** Chromium headless, `DOM.setFileInputFiles`. A real file chooser applies
  the input's `accept="application/pdf"` filter, so a user picking `not_a_pdf.txt` would have
  to switch the chooser to *All files* first. The pre-check is what catches a drag-and-drop
  or an `accept`-ignoring platform, and this drive exercises exactly that path.
* **The two-pass agreement is not independence.** Both passes used the same script against
  the same stack; they rule out flake, not a wrong declaration.
* Every fixture is synthetic (`R-4`); no real client document was in play.

**Elapsed, measured:** wall clock from the first command of this session to the last.
