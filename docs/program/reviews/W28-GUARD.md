# W28-GUARD — yesterday's six proofs come under the gate, and `D-44` becomes impossible to break quietly

> **Opened before the first edit**, `AGENTS.md` §5. Branch `agent/w28-guard`, from
> `origin/dev` at `ca16a18`. Worktree `/root/w28guard`, lane `gate-w28b`.

## What this session was sent to do

Two things, and they turn out to share a number.

1. `W27-REFUSE` drove six negative fixtures through a browser and wrote the verdicts into
   `refusals.mjs`'s own source. Nothing re-runs it, so a renamed marker or a reworded
   sentence turns it red only when a person remembers to run it.
2. `D-44` — the browser's pre-check refuses at 25 MiB and `nginx.conf` allows 32m, and the
   gap is the only reason three refusal screens say something true. Nothing records it.

---

## 1. The three named additions were not the right three, and the measurement says why

`W27-REFUSE` named three things `manifest.json` would need:
**`requires_rendered`**, **`refused_by`**, and **letting a declared status be any status
the contract publishes for that operation**. The brief said to verify that list against the
files first. Measured, **one of the three was real**, and the thing actually missing was not
a field at all.

| named addition | measured | evidence |
|---|---|---|
| `requires_rendered` | **already there, under another name** | `manifest.json`'s write steps have carried **`expects_rendered`** since `W22-E2E` — `create-project` requires `"Created"`, `upload-document` requires `"This version"`. The field is not missing. |
| `refused_by` | **genuinely absent** | nothing in `manifest.json` could say *"refused, and by the client"*. This one was right. |
| statuses checked as **success** statuses | **false** | `responses_published_for()` returns **every digit response code** the operation publishes. `uploadDocument` publishes `201, 401, 403, 404, 409, 422, 500, 503`. A `422` declared in the manifest passes `test_every_status_the_write_half_declares_is_one_the_contract_publishes` **unchanged** — no widening was needed, and none was made. |

**What was actually missing, and nobody had named it: nothing read `expects_rendered`
except `write.mjs`.** The field existed, the journey asserted it at run time, and the
gate-time guard walked straight past it — so `"Created"` could be reworded to
`"Project made"` and `make gate` stayed green while the write half went quietly red. That
is the *same* defect `W27-REFUSE` reported for its own six cases, already present in the
half it held up as the model. It is closed here for both halves at once, by
`test_every_sentence_the_journey_requires_still_appears_in_the_application`.

So the additions this session actually made are: **`refused_by`** (the one that was right),
**a `refusals` section that reuses `expects_rendered`** rather than inventing a third name
for it, and **a guard that reads `expects_rendered`** — which was never a manifest problem.
`expect_status` needed nothing.

## 2. Which half moved to the gate, and which half did not

The brief was explicit that if declaring a refusal needs behaviour the guard cannot see,
this session says which half moves rather than widening the guard's claim. It does.

**Moved to `make gate`, with no stack, no browser and no origin:**

- the refusal half exists at all, declares an `api`, and declares refusals **at both
  sides** — a half that measured only client-side refusals would measure half a screen;
- every fixture is on disk and non-empty;
- the upload screen and its control module exist, the screen derives from its own
  `page_module`, and the read walk covers it;
- `refused_by` is `client` or `server`, and the case declares the fields that go with that
  side **and none that only the other side can produce** — a client refusal makes no
  request, so it has no status, no envelope and no server classification;
- `uploadDocument`'s `(method, path, operationId)` triple is a real contract operation;
- every declared status is one the contract publishes for that operation;
- every marker **attribute** and every marker **value** still appears in `web/src` —
  `data-precheck-problem` could survive a rename of `too_large`, and the case would then
  assert a word no screen can produce;
- every sentence in `expects_rendered` still appears in `web/src`, **for the write half
  too**;
- every `expects_rendered_from_envelope` string is part of the `constraint` beside it;
- no case declares a classification from `generic_kinds` — the cheapest way to make a
  failing drive pass is to declare defeat, and that would silently retire the measurement.

**Did not move, and is named in `manifest.json`'s own `$comment` rather than claimed:**
that the envelope really carries that `constraint`, that the screen really renders it, that
`Upload` really goes unpressable after a pre-check refusal, that nothing was published, and
that no request carried a credential. Those are behaviour. They stay with `refusals.mjs`
against a running stack, which is the same residue `W21-E2E` and `W22-E2E` both stated.

**The split forced a manifest decision worth recording.** `W27-REFUSE`'s `must_say` mixes
two kinds of string: the application's own words (`"not a PDF"`, `"Nothing was sent"`,
`"25 MiB"`, `"outside the accepted envelope"` — all in `web/src`) and words the **server**
supplies at run time (`not_encrypted`, `every_page_has_extractable_text`, `page_count` —
**none of which are in `web/src` at all**). A guard demanding all of `must_say` appear in
`web/src` would have been red on three of six cases the moment it ran. So the manifest
splits them: `expects_rendered` is checked against the application, and
`expects_rendered_from_envelope` is checked against the declared `constraint` instead —
which is data, and therefore guardable without a stack. `refusals.mjs` concatenates the two
back into one `must_say` and drives exactly what it drove before.

## 3. `D-44`'s guard

`tests/e2e/test_upload_limit_headroom.py`. **Both numbers are read from where they live**,
per `OPERATING_CONSTRAINTS.md` §12 and on `D-23`'s model — no literal limit appears in the
file, because a literal would need editing at the next change, which is the failure mode
itself.

- `precheck_max_bytes()` reads `maxBytes: 25 * 1024 * 1024` out of
  `web/src/entities/document-version/model/upload-envelope.ts` and evaluates the product.
  A value it cannot read as a product of integer literals **raises** rather than defaulting.
- `nginx_body_limit()` reads `client_max_body_size 32m;` out of
  `infra/deploy/proxy/nginx.conf` and applies nginx's binary suffixes. **This file reads
  that config and never writes it.**

Three real-tree checks: the pre-check is **strictly** below nginx's cap; the label the
screen shows is the limit the screen enforces (`maxBytesLabel` vs `maxBytes` — the refusal
half requires the words `25 MiB` on screen, and if the limit moved and the label did not,
the user would be told a rule the application does not enforce); and `oversize.pdf` sits in
the gap, above the pre-check and below nginx, which is what makes it a test of the
pre-check rather than a test of nginx.

**Why it lives in `tests/e2e/`** rather than `tests/contract/` or
`tests/integration/composition/`: the invariant is a claim of the PC-01 journey.
`manifest.json` declares `oversize.pdf` is `refused_by: client`, and that declaration is
true exactly while this headroom holds. The guard sits next to the claim it protects.

## 4. Mutations, run rather than reasoned about

### `prove_the_headroom_guard_can_fail.py` — and it never writes the tree

`D-44`'s guard reads two files this session is forbidden to edit, with another lane
deploying from the same checkout. So the harness builds a **throwaway tree** in `/tmp`: the
real test file at the same depth, the two real inputs with one number changed, and a sparse
stand-in for `oversize.pdf` at its true size. The guard resolves its repository root from
its own `__file__`, so it reads the copy. `pytest` then runs there and the exit status is
the verdict. The repository is byte-identical before and after.

**Eight mutations, eight reds, and the unmutated pair green** — `.venv/bin/python
tests/e2e/prove_the_headroom_guard_can_fail.py`, exit 0, `git status` clean before and
after:

| mutation | result |
|---|---|
| raise the pre-check to 32 MiB, nginx untouched — **`D-44`'s own sentence** | RED, 3 failed |
| raise the pre-check to 64 MiB | RED, 3 failed |
| lower nginx to `16m`, pre-check untouched | RED, 2 failed |
| make nginx exactly equal to the pre-check | RED, 2 failed |
| comment out `client_max_body_size` entirely | RED, 2 failed |
| move the limit behind a name the parser cannot read | RED, 3 failed |
| leave `maxBytesLabel` at `25 MiB` while `maxBytes` moves to 30 | RED, 2 failed |
| shrink `oversize.pdf` under the pre-check limit | RED, 1 failed |
| **unmutated** | **11 passed** |

**Running the controls found a real hole, exactly as the brief warned.** The first draft
anchored `client_max_body_size` to the start of a line. nginx accepts
`server { client_max_body_size 4m; }` on one line, and that second cap — the one that
would actually decide the effective limit — was **invisible to the parser**. The control
that was supposed to prove the guard refuses two caps went green, which is how it was
found. The fix strips `#` comments line by line and then searches unanchored, so a
commented-out directive is still not read as the cap and an inline one is. Both shapes are
now controls of their own. Reading the regex would not have found this.

### `prove_the_guard_can_fail.py` — thirteen more, against the real `manifest.json`

`.venv/bin/python tests/e2e/pc01/journey/prove_the_guard_can_fail.py`, exit 0.
**Twenty-three mutations, twenty-three reds**, and the restored file green at 47 tests.
Ten are `W22-E2E`'s, unchanged. The thirteen new ones: drop the refusal section; declare
every refusal happens at the server; rename `uploadDocument`; point a refusal at a fixture
that is not there; move the refusals off the read walk; call a client-side refusal a server
one; declare a status `uploadDocument` does not publish; rename the pre-check marker value;
drop the upload-failure marker; require a sentence no screen renders; **reword the write
half's own panel**; require an envelope sentence its own constraint contradicts; surrender
a named fault to the generic classification.

`manifest.json` is restored after each one and again at the end, and `git status` was clean
before and after the run.

## 5. What the guard now catches, and what it still cannot

**Catches, at gate time, with no stack** — each proved by a mutation that was run:

| rot | what reddens |
|---|---|
| a screen renames `data-upload-failure` or `data-precheck-problem` | the marker check |
| `too_large` becomes `over_the_limit` in `upload-envelope.ts` | the marker-**value** check |
| the pre-check panel is reworded | the sentence check |
| the *write* half's `"Created"` is reworded | the same check — previously unguarded |
| `uploadDocument` is renamed or re-mounted | the contract triple check |
| `422` is dropped from `uploadDocument`'s responses | the status check |
| a negative fixture is deleted or renamed | the fixture check |
| the upload screen moves, or leaves the read walk | the screen check |
| a case is edited to claim the wrong side of the seam | the coherence check |
| a case is "fixed" by declaring `server_error` | the generic-classification check |
| the pre-check limit is raised to nginx's | `D-44`'s guard |
| `client_max_body_size` is lowered, commented out, or joined by a second cap | `D-44`'s guard |
| `maxBytesLabel` stops matching `maxBytes` | `D-44`'s guard |
| `oversize.pdf` is replaced by a file under the pre-check limit | `D-44`'s guard |

**Still cannot**, and this is the line the brief asked to be drawn rather than blurred:

- that pressing anything *does* anything. The guard proves a handle and a sentence exist
  in `web/src`; it cannot prove the panel renders, that `Upload` goes unpressable, or that
  the `422` arrives. `refusals.mjs` against a live stack is the only instrument for that,
  and it is unchanged in every respect but where it reads its table from.
- that the server's envelope really carries the declared `constraint`. `not_encrypted` and
  `every_page_has_extractable_text` are literals in `src/auditmanager/ingest/envelope.py`,
  but `1 <= page_count <= 30` is an f-string built from `MIN_PAGES`/`MAX_PAGES` and has no
  literal anywhere. A guard demanding all three would have been red on the third the
  moment it ran, so the constraint is **not** checked against `src/`. What is checked is
  that each case's own `expects_rendered_from_envelope` agrees with its own `constraint`.
- **`D-44`'s guard reads the config in the tree, not the config nginx loaded.** A stack
  deployed before a change to `nginx.conf` still serves the old cap. The guard is about
  what the repository commits to, and `infra/deploy/verify-deployed.sh` is the instrument
  for what is running.
- the sentence check is a substring search over all of `web/src`, deliberately coarse for
  the same reason `application_source` is: a finer check would redden when a file moves.
  `"Run"` is a weak needle; `"Nothing was sent"` is a strong one. The check is worth what
  the sentence is specific.

## 6. Anything false in the task file

**Three things, and one of them is the premise section 1 is about.**

1. *"`manifest.json` … has `forbids_rendered` and no `requires_rendered`"* — true of the
   **name** and misleading about the **fact**. `expects_rendered` is exactly that field and
   has been there since `W22-E2E`. Inherited from `W27-REFUSE`'s review, which the brief
   correctly told this session to check.
2. *"its statuses are checked against the contract as **success** statuses"* — **false**.
   `responses_published_for()` has always returned every published code, so `422` needed no
   widening. Also inherited.
3. *"`tests/e2e/test_pc01_journey_conformance.py` … 30 tests"* — correct at `ca16a18`,
   measured. It is 47 now.

The brief's own base figures were right: battery **1970 / 5 / 169** (1998 − 28 = 1970,
and 28 is exactly the number of checks added here), foundation **35**, frontend **715 in
49 files**. `D-44`'s two numbers were right: pre-check **26 214 400**, nginx **33 554 432**.

**One instruction could not be followed exactly, and it is named as the brief asked.**
*"Stay out of `refusals.mjs`'s driving logic if you can."* The declaration table had to go,
and with it two one-line reads that are arguably driving: `GENERIC_KINDS` is now built from
`refusals.generic_kinds`, and the fixture directory is now `refusals.fixture_dir`. Both
were literals duplicating the manifest; leaving them would have meant the manifest
**declaring two things nothing read**, which is the defect this session exists to close.
Everything from `apiExchanges` down — every assertion, every finding message, the browser
driving, the envelope writing — is byte-identical. **`W28-LIVE` and this session both touch
`tests/e2e/`**, and the overlap on `refusals.mjs` is the file header, the table, and those
two lines.

**A provisioning observation worth passing on**, since the brief's own warning is about
exactly this class. `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` in this worktree
ran `uv sync` **twice** from one invocation and took **~23 minutes**, and for most of that
`.venv/bin` held only `pip` — the shape the brief warned about. It did resolve: `bootstrap
exit 0`, `npm ci exit 0`, and `.venv/bin/python -c "import boto3"` prints `1.43.90`. The
check the brief demanded is the one that settles it; the intermediate state is not
diagnostic, and a session that gives up on seeing it would be giving up too early.

## 7. The gate

`make gate` on lane `gate-w28b` (`POSTGRES_PORT=56030`, `S3_API_PORT=59630`,
`S3_CONSOLE_PORT=59631`, `POSTGRES_DB=audit_w28b`, bucket `auditmanager-gate-w28b`),
redirected to a file, **exit read from `$?`, never through `| tail`**:

```
GATE OK: battery, foundation, frontend and whitespace all pass
exit 0
```

| | base (`ca16a18`) | here |
|---|---|---|
| battery | 1970 passed / 5 skipped / 169 subtests | **1998 passed / 5 skipped / 169 subtests** (278.78 s) |
| foundation | 35 | **35** (28.51 s) |
| frontend | 715 in 49 files | **715 in 49 files** |

**+28 is the whole of the difference**, and it is exactly what was added: the conformance
guard goes 30 → 47 (+17) and `test_upload_limit_headroom.py` is 11. No existing test
changed its outcome, and the skip count and subtest count are untouched.

Provisioning: `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` exit 0,
`npm --prefix web ci` exit 0, and **`.venv/bin/python -c "import boto3"` → `1.43.90`**.

## 8. Handoff

**Files changed** (7, all inside `allowed_paths`):

| file | what |
|---|---|
| `tests/e2e/pc01/journey/manifest.json` | new `refusals` section, 6 cases. **Insertions only** — `routes` and `write` are byte-identical. |
| `tests/e2e/test_pc01_journey_conformance.py` | refusal half: 8 checks + 8 controls; `expects_rendered` check covers the write half too; `operations_claimed_by_manifest` widened; mutation-copy note de-counted. 30 → 47 tests. |
| `tests/e2e/test_upload_limit_headroom.py` | **new.** `D-44`'s guard, 3 real-tree checks + 8 controls. |
| `tests/e2e/prove_the_headroom_guard_can_fail.py` | **new.** 8 mutations against a throwaway tree; writes nothing. |
| `tests/e2e/pc01/journey/prove_the_guard_can_fail.py` | 10 → 23 mutations. |
| `tests/e2e/pc01/journey/refusals.mjs` | reads its table from the manifest. Driving logic unchanged. |
| `docs/program/reviews/W28-GUARD.md` | this. |

**Forbidden hotspots untouched**, by `git diff --name-only origin/dev..HEAD`: nothing under
`src/`, `web/`, `contracts/`, `infra/`, and no `Makefile`, `artifacts/`,
`DEBT_REGISTER.md` or `CURRENT_STATE.md`. `D-44`'s guard **reads** `nginx.conf` and never
writes it, and its mutation harness proves the reddening without writing either file.
No tag, no checkpoint, nothing pushed to `main`.

**Contracts:** none changed. `manifest.json` gains a section; `contracts/**` is untouched.
`manifest.json`'s format is now three halves, and its own `$comment` documents the new
one, including what it does **not** claim.

**For the integrator.**

- Branch `agent/w28-guard`, 9 commits on `origin/dev` at `ca16a18`. Merge as usual.
- **`D-44` can be closed**, and this session did not touch `DEBT_REGISTER.md` because it is
  a forbidden hotspot here. Its check command is now a test rather than a `grep`:
  `.venv/bin/pytest tests/e2e/test_upload_limit_headroom.py` → 11 passed, and
  `.venv/bin/python tests/e2e/prove_the_headroom_guard_can_fail.py` → 8 reds, exit 0.
- **`W27-REFUSE`'s stated residue is closed**: the six cases are in `manifest.json` and
  `make gate` reads them. What remains open is what it always was — the *behaviour* half,
  which needs a stack.
- If `W28-LIVE` also edited `tests/e2e/`, the only file both could have touched is
  `refusals.mjs`; the overlap is its header, its table and two constant reads.
- The lane's stack (`gate-w28b`) is left up; `make down` in `/root/w28guard` stops it.

**Risks and known limitations.** Section 5 is the list. The two worth repeating: the
sentence check is a substring search over `web/src` and is worth what each sentence is
specific; and `D-44`'s guard reads the config in the tree, not the config a running nginx
loaded.

**Elapsed, measured**: 14:31 to 15:00 local, **~1 h 29 min** wall clock, of which
**~23 minutes** was `make bootstrap` and **~7 minutes** was `make gate`.
