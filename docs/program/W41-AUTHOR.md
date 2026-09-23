# W41-AUTHOR — the author of a decision, and two ports

**task_id:** `W41-AUTHOR` · **wave:** 41 · **lane:** `gate-w41a`
**worktree:** `/root/w41author` · **branch:** `agent/w41-author` · **base:** `295ff04`

Opened before the first measurement, as the brief requires, and filled in as each figure was
taken. Every number carries the command that produced it and the commit it ran on.

---

## 0. Premises in the brief, checked before anything was built on them

The brief says a brief that names a file can be wrong, and names six. Every one was checked
against the tree before any of it was used.

| Premise | Verdict |
|---|---|
| `src/auditmanager/api/security.py:403` builds `Subject(user_uid=…, login=…, token_epoch=…)` | **true**, that exact line |
| `src/auditmanager/decisions/ledger.py:60` is `CONFIGURED_AUTHOR_LABEL` | **true**, that exact line |
| `src/auditmanager/analysis/text/proxy.py:61` is `ProxySettings.__post_init__` | **true**, that exact line |
| `src/auditmanager/api/routers/ports.py` is where a narrow existence method belongs | **true** |
| the port implementations are in `bootstrap/adapters.py` and `tests/integration/api/conftest.py` | **true**, and see §3.1 for what that count leaves out |
| `DecisionEvent.author_label` is in the API schema at `models.py:561,594`, `min_length=1, max_length=128` | **true** |

Two things in the brief are **false**, and one of them changes the shape of the work.

### 0.1 The base

The brief's own header says **base `6aeda82` (`alpha-w40`)**. The dispatch message, the
worktree and the branch are all **`295ff04`** — one commit later, and it is the commit that
*carries this brief*. Worked from `295ff04`, which is what every figure below was taken
against.

### 0.2 A1's diagnosis is stale, and the gap is not where the brief puts it

> `require_authorization` **returns `None`**, so no route can see it. That is the whole gap:
> the identity is established and then discarded.

**The identity is not discarded.** `require_authorization` is annotated `-> None`, but its
last statement is `request.state.subject = subject`, and `security.py` already publishes two
things over it:

```python
def current_subject(request: Request) -> Subject: ...
CurrentSubject = Annotated[Subject, Depends(current_subject)]
```

`changePassword` has read the verified subject through `CurrentSubject` since `W39-REVOKE`,
and `tests/integration/api/test_authorization.py` carries a guard asserting that **exactly
one** router module does.

So the mechanism the brief asks to be built was already there, and A1 is narrower than it
describes: the work was not to make the subject reachable but to have a second operation
reach for it, and to take the constant out of the ledger behind it. That is not a
simplification — it is the difference between "add a seam" and "walk into an existing guard
that counts the seam's readers", and §1.4 is what that guard cost.

### 0.3 `D-70`'s file is not in this repository

The brief says `infra/deploy/env/provider.env` "carries exactly that URL today". The tree
carries `infra/deploy/env/provider.env.example` and **no `provider.env`** — that file is
git-ignored and lives only on the owner's stand. So the claim is **unverifiable from inside
the repository** and is taken on the brief's word. What *is* verified from inside, and
measured in §2.1, is that the code accepts a host-less URL and reports the failure as
retryable.

---

## 1. A1 — `D-78`: a decision is attributed to the reviewer who made it

Commit **`14a0913`**, plus **`83751df`** for the record citation §1.5 explains.

### 1.1 What was measured before anything was changed

`CONFIGURED_AUTHOR_LABEL` was written into `expert_decision_event.author_label` for every
event, from both write paths, through both adapters. `OD-18` wants three to five named
experts in the alpha and `P04` exists to learn **whose** judgement was whose; one constant
makes that question unanswerable however many reviewers there are.

The command surface was measured for what it accepts before it was changed:
`AppendDecisionRequest` inherits `model_config = ConfigDict(extra="forbid")`, so a body
carrying `author_label` is a `422 validation_failed` with
`details.constraint == "additionalProperties"` — characterization record
`25-appendDecision.refusal.additionalProperties` pins exactly that. **The body could not
influence the label before this change and cannot now**, and that is asserted rather than
assumed (`TestTheBodyCannotNameAnAuthor`, both over the wire and at the handler's source).

### 1.2 What was built

`appendDecision` takes `subject: CurrentSubject` and passes `author_label=subject.login`
down through `DecisionPort.append_decision` into `append_decision_under_key` and
`record_decision`.

**Fail-closed, and by construction rather than by care.** `author_label` has **no default**
anywhere on the path: not on `record_decision`, not on `append_decision_under_key`, not on
`DecisionPort.append_decision`, and `DecisionAdapter.append_decision` no longer ends its
signature with `**_`. `CONFIGURED_AUTHOR_LABEL` is **deleted**, not repurposed — a default is
precisely what a caller with no authenticated subject falls into, and a row attributed to a
configuration constant reads like a decision somebody took. That is `D-66`'s shape and the
brief names it.

`appendDecision` is not in `UNAUTHENTICATED_OPERATIONS` (which holds `issueToken` and nothing
else), so there is always a subject to name. Requests with no credential, with a string this
deployment never minted, and with a **genuinely signed** credential naming an account the
deployment has not got all answer `401` and write **no row** — asserted by reading
`expert_decision_event` back, not by reading the response.

### 1.3 Why the login, and what it costs — the consequence, registered and not designed around

**The label is `subject.login`.** The argument, since the brief asks for one:

* `author_label` is rendered to a human. `web/src/widgets/decision-history/ui/decision-history.tsx:96`
  and `web/src/widgets/knowledge-base/ui/knowledge-base.tsx:105` put it on screen verbatim.
  `user_uid` is an opaque ULID and would be unreadable to the only audience the field has.
* It cannot be chosen by a client: it is a claim inside a credential this deployment signed,
  and the request body is closed.
* It is the same field `changePassword` treats as identity-not-permission, so the surface
  gains no new vocabulary.

**The consequence.** A reviewer's **login** becomes visible to every other reviewer on every
decision they read — in `listDecisionHistory`, in `listDecisions`, and on screen in the two
widgets above. It does **not** reach the CSV export: `author_label` appears nowhere in
`src/auditmanager/exports/` and is not among `P02_SEAMS.md` §6's seventeen columns.

Today there is **exactly one account**, so this exposes nothing to anybody. The question
arrives with the second account, and that is owner-blocked work. **Registered here and
deliberately not designed around**, per the integrator's instruction.

A second property worth the owner's attention when that day comes: the login is a **signed
claim carried in the credential**, not a column read at request time. If an account is ever
renamed, credentials minted before the rename keep writing the old login until they expire
(one hour). That is correct for attribution — the ledger records what the deployment
verified at the time — and it is a thing somebody will be surprised by, so it is written down.

### 1.4 Three guards in the tree had to move, and each is worth reading

1. **`tests/integration/decisions/test_decision_ledger.py::TestAuthorLabel` was vacuous, and
   `W12-DEC` said so at the time.** It imported `CONFIGURED_AUTHOR_LABEL` and compared both
   sides of its assertion to it — §12's form 1 — which is exactly why `M21` was recorded
   **deliberately green**. `W12-DEC`'s reasoning was right for its own tree: pinning the
   literal would have frozen what the module called a composition-root knob. It is no longer
   a knob, so the class now uses **literals it owns** and asserts that two authors are two
   labels.

2. **`tests/integration/api/test_authorization.py` asserted that exactly one router module
   depends on the seam's accessor — by grepping for the string `CurrentSubject`.** `ports.py`
   now names the accessor in a docstring, to say where `author_label` comes from, and depends
   on nothing; the substring check called that a dependency. The check now reads the module's
   **syntax tree for an import**, which is strictly narrower than the old one and answers the
   question the assertion's own prose asks. `test_the_subject_reader_check_can_fail` plants
   three import spellings and one prose-only module and requires the reader to separate them
   — because a guard I tightened to make my own change pass needs to be shown still biting.

   The expected set is now `["auth.py", "decisions.py"]`. **The count is the thing to
   defend**: a third module reaching for the subject is where an invented role model would
   start, and the assertion's job is to make that a decision somebody takes on purpose.

3. **Characterization records `10-appendDecision.success` and `11-listDecisionHistory.success`
   carry `author_label` and move with it.** Both are marked permitted exceptions under
   `D-78`. They cite **no owner ruling**, on the reading `D-20` was given: nothing in
   `contracts/**` moved, no property was added to any schema, and `DecisionEvent.author_label`
   is declared by the seal with the same type and the same `1..128` bounds. What changed is
   the *value* the server writes into a field it has always written.

   Record 11 was **not** anticipated — the brief and my own first reading named only record
   10. The byte comparison found it. This is the measurement doing its job rather than my
   plan doing it.

### 1.5 Why two commits

`exception.decided_by` names the commit that **decided** a change, not the one that edited the
record — record 06 cites `6398bcc`, the reseal, not the recapture. For `D-78` the deciding
commit is `14a0913`, which cannot name itself, so `83751df` fills it in. Both commits are
green; `pytest tests/characterization` is 60 passed before and after.

### 1.6 The mechanical half

60 call sites of `record_decision` / `append_decision_under_key` across 7 test files now pass
an explicit label. They were rewritten **through the AST**, not by string match, and the
rewriter re-parses every file before writing it. It was also wrong once in a way worth
recording: `ast` reports `col_offset` in **bytes**, these files carry Russian text, and the
first run inserted `, author_label="reviewer-1"reject = record_decision(`. Caught by the
re-parse, which is why the re-parse is in the script.

---

## 2. A2 — `D-72`: a URL with no host is not a retryable dependency failure

Commit **`b56d103`**.

### 2.1 Both halves proved before the change

Measured at `07ff54f`, against `src/` as it then stood:

```
ProxySettings(base_url="http://:59990", token="t")   -> constructs
ProxyAdapter(...).complete(...)                      -> dependency_unavailable
ProxySettings(base_url="http://127.0.0.1:59990", …)  -> dependency_unavailable
```

The second and third lines are the defect stated precisely: **a lane pointed at nothing and a
lane whose provider is down produce the identical code**, and
`contracts/domain/v1/error-codes.json` marks that code `"retryable": true`. So a run against a
misconfigured lane retries a ladder, pays for the waiting, and reports a transient outage.

### 2.2 What was built

`__post_init__` now refuses a URL whose `urlsplit().hostname` is empty, with
`DomainError(ErrorCode.INTERNAL_ERROR, message=…)` — the same shape as the two checks beside
it. **No error code was added and `contracts/**` was not touched.**

`urlsplit().hostname` rather than a second string test, because it is the same parse
`urllib.request` performs on the string a moment later, so what is refused here is what the
transport would have found missing. Its `ValueError` on a malformed authority is caught and
refused with it rather than escaping as an unclassified 500.

### 2.3 Already half-repaired elsewhere, and now redundant — reported, not touched

`W39-CORPUS` diagnosed this from the outside and put the check in the **one caller it owned**:
`src/auditmanager/norms/__main__.py:177–184`, whose refusal message still reads

> `…is accepted by ProxySettings, which checks only the scheme, and then fails at call time
> as a transport error that reads like a provider outage.`

That sentence is now false, and the module docstring at line 25 says the same thing. The
check itself remains correct and harmless — it refuses earlier, with a message naming the
environment variable, which `ProxySettings` cannot do. `src/auditmanager/norms/**` is outside
this task's `allowed_paths`, so it is **reported and not repaired**. See §6.

---

## 3. A3 — `D-74`: a parent-existence check no longer costs a full parent read

Commit **`8877d5d`**.

`RunPort.run_exists` and `FindingPort.finding_exists` answer the yes/no. They return `bool`
rather than raising: whether an absent parent is a `404` is the frozen contract's statement
about a particular operation, so the refusal stays in the router that declares it, which is
where `D-67` put it. `aggregate_type` is unchanged on both (`AuditRun`, `Finding`), so the
wire bytes are identical and the pinned `30-getRunStatus.not_found` record still matches.

### 3.1 The implementations, counted rather than taken from the brief

`build_router` is called **13 times in 13 files**, carrying **89 port arguments**. Enumerated
by parsing the tree, not by grepping for adapter names:

| wired as | classes that must carry the new method |
|---|---|
| `runs` | `RunAdapter` (`src/auditmanager/bootstrap/adapters.py`), `SeamRunAdapter` (`tests/integration/api/conftest.py`) |
| `findings` | `FindingAdapter` (`src/auditmanager/bootstrap/adapters.py`), `DatabaseFindingAdapter` (`tests/integration/api/conftest.py`) |

Everything else passed as one of these ports is `None` (nine wirings whose suites never drive
that operation) or `_Unused`, a stand-in whose `__getattr__` raises and which therefore
answers any method name.

**The brief's file count is right: two files.** The count that is *wrong* is in the register
itself — `DEBT_REGISTER.md` §D-74 says the change is "four implementations — one in
`bootstrap/` (a hotspot) and **three** in `tests/`". It is **two and two**: both shipped
adapters are in one `bootstrap/` file and both stand-ins are in one `tests/` file. The
register is the integrator's; reported in §6, not edited.

One thing the enumeration turned up that a name-grep would have missed: **`_Unused` is defined
twice in this tree**, in `tests/integration/api/test_listing_surface.py` and in
`tests/integration/analysis_text/test_provider_modes.py`, and a name-keyed index answered with
whichever file sorted first. The guard resolves a class against the file that wired it, and
that is why.

### 3.2 The two guards

* `tests/integration/composition/test_every_port_implementation_is_whole.py` derives the set
  above **by parsing the tree**, so it covers a wiring added after it was written, and it
  **reports rather than skips** a port argument it cannot resolve — a checker that cannot read
  a claim has not verified it, and a silent skip is indistinguishable from a pass.
* `tests/integration/api/test_existence_is_not_a_full_read.py` asserts the narrowing is real,
  off SQLAlchemy's own `before_cursor_execute`: `run_exists` names neither `stage_result` nor
  `model_call`; `finding_exists` names neither `expert_decision_event` nor `finding_evidence`.
  **Two controls** drive the full reads and require those tables to appear, so a recorder that
  saw nothing could not satisfy the first pair.

---

## 4. Anti-vacuity: every guard shown to fail

### 4.1 `M21`, in both states — the acceptance for A1

`W12-DEC` recorded `M21` (`CONFIGURED_AUTHOR_LABEL`, `"local-reviewer"` → `"someone-else"`) as
**deliberately green**. Both states were measured here rather than quoted.

**Before — `M21` verbatim, at base `295ff04`.** The base tree was reconstructed in
`/root/w41author-mutbase` by restoring every file of `git diff --name-only 295ff04..HEAD` to
its `295ff04` content and deleting the three files this branch adds; it baselines at
**42 passed, 4 subtests** on `tests/integration/decisions`.

```
CONFIGURED_AUTHOR_LABEL: Final[str] = "someone-else"
tests/integration/decisions  ->  42 passed, 4 subtests passed in 0.86s     GREEN
```

**Reproduced exactly as recorded.**

The wider scope is the more interesting reading, and it sharpens `W12-DEC`'s note rather than
contradicting it:

```
tests/integration/decisions + test_decision_journal.py + test_authorization.py + tests/characterization
  ->  3 failed, 142 passed
      test_decision_journal.py::test_a_record_carries_the_finding_context_it_was_recorded_against
      test_response_baseline.py::test_the_response_reproduces_the_record[10-appendDecision.success]
      test_response_baseline.py::test_the_response_reproduces_the_record[11-listDecisionHistory.success]
```

So the old tree **could** notice the string changing — three assertions elsewhere pinned the
literal. What nothing anywhere could notice is the **attribution being wrong**, because there
was only ever one attribution. `W12-DEC`'s green was green about the right thing: *whatever
the configured label is, it is written server-side with every event*. The defect was never an
unpinned constant. It was that the value was a constant at all.

**After — the same mutation, after the repair, against the sweep set:**

```
routers/decisions.py:  author_label=subject.login  ->  author_label="someone-else"
  ->  6 failed, 235 passed                                                  RED
```

```
>       assert first.json()["event"]["author_label"] == "anna.petrova"
E       AssertionError: assert 'someone-else' == 'anna.petrova'
E         - anna.petrova
E         + someone-else
tests/integration/api/test_decision_authorship.py:206: AssertionError
```

### 4.2 The sweep

Copy: `make mutation-copy MUT=/root/w41author-mut`, proved to be the tree that imports
(`auditmanager.decisions.ledger.__file__` resolves under the copy). `PYTHONDONTWRITEBYTECODE=1`
throughout and `__pycache__` cleared between every case (§10.2).

**Unmutated baseline of the sweep set on the copy: 241 passed, 4 subtests, 47.01s.** The sweep
set is the eleven paths listed in the log header; the rest of `tests/integration/composition`
is excluded because it baselines red **on the copy** for reasons that have nothing to do with
this work — see §6.4.

| # | mutation | result | failures |
|---|---|---|---|
| A1-M1 | `M21` after the repair: the label pinned back to a constant | **red** | 6 |
| A1-M2 | the label taken from the field beside it: `subject.user_uid` | **red** | 6 |
| A1-M3 | a fail-closed default grows back on `record_decision` | **red** | 2 |
| A1-M4 | `CONFIGURED_AUTHOR_LABEL` comes back as a module constant | **red** | 1 |
| A1-M5 | the shipped adapter accepts the author and writes a constant anyway | **red** | 5 |
| A1-M6 | the empty-label refusal is removed | **red** | 1 |
| A2-M1 | the host check is removed; a host-less URL constructs again | **red** | 6 |
| A2-M2 | the check reads the field beside it: `netloc` instead of `hostname` | **red** | 3 |
| A3-M1 | one implementation loses `run_exists` | **red** | 5 + 10 errors |
| A3-M2 | `run_exists` delegates to the full read it was added to avoid | **red** | 2 |
| A3-M3 | `finding_exists` always says yes | **red** | 4 |
| A3-M4 | `listRunFindings` stops proving its parent exists | **red** | 2 |
| A3-M5 | `listDecisionHistory` stops proving its parent exists | **red** | 2 |

**Thirteen of thirteen red. No mutation came back green, so there is no blind guard to report
from this sweep.** Full logs: `/root/w41author-mutlogs/`, one file per case.

Three of them are worth naming rather than counting:

* **A1-M2** is `D-34`'s shape — the assertion aimed one field to the left. `subject.user_uid`
  is a perfectly good identity and the wrong one, and the tests separate them because they
  assert the login literal rather than "some non-empty string".
* **A2-M2** is the same shape on the other repair. `urlsplit("http://:59990").netloc` is
  `':59990'`, which is truthy, so reading `netloc` instead of `hostname` silently stops the
  check firing. Red.
* **A3-M1** is the one `D-74` is a debt row about: renaming `run_exists` on the *test* stand-in
  produced 10 errors and 5 failures, and among them
  `test_every_wired_implementation_carries_the_whole_port[runs]` — so the completeness guard
  caught it and did not merely ride along behind the behaviour tests.

---

## 5. Gate figures

| | figure | command | commit |
|---|---|---|---|
| baseline battery | **2315 passed, 5 skipped, 169 subtests, 374.97s** | `OPERATING_CONSTRAINTS` §7's literal command | `07ff54f` |
| final battery | **2357 passed, 5 skipped, 169 subtests, 527.57s** | `make gate` | `83751df` |
| foundation | **35 passed, 29.55s** | `make gate` | `83751df` |
| frontend | **72 test files, 1014 tests passed** | `make gate` (typecheck then suite) | `83751df` |
| whitespace | pass | `make gate` | `83751df` |

```
$ grep -c 'GATE OK' /root/w41author-gate-final.log
1
$ grep -n 'GATE OK' /root/w41author-gate-final.log
214:GATE OK: battery, foundation, frontend and whitespace all pass
```

`gate_exit=0`, read from `$?` on the line after the redirect. **The verdict is taken from the
`GATE OK` line inside the log**, which only the gate prints (§4.62).

**+42 tests.** No test was deleted; `TestAuthorLabel`'s one vacuous case was replaced by three.

Two notes on the figures, because a number without its conditions is not a measurement:

* **527.57s against a 374.97s baseline** on the same lane. `W41-BLIND` was live in
  `/root/w41blind` throughout. §4.6 says a gate that took much longer than usual is evidence
  about the machine; nothing failed, so it is recorded rather than investigated.
* **The first baseline attempt is not in the table.** A `make gate` started at `07ff54f` was
  killed at ~74% when the session's host process exited, having shown 3 errors and 1 failure
  I never identified. The clean battery re-run on the same tree was **2357/2315 green with no
  errors at all**, so those four were contention, not a pre-existing red. I am naming the
  unexplained reading rather than dropping it, because "it went away on a re-run" is the
  sentence §4.6 exists to make somebody write down.

---

## 6. Found outside the grant — reported, not repaired

### 6.1 The frozen contract's description of `author_label` is now false

`contracts/api/v1/openapi.json` describes the field, in both `DecisionEvent` and
`DecisionRecord`, as:

> `"OD-12: one configured local reviewer label, persisted server-side. It is a label, not a
> subject identity, and it authorizes nothing."`

After `D-78` the first clause is wrong: it is not one configured label, and it *is* derived
from a subject identity (though it still authorizes nothing, which remains true and is the
load-bearing half). **The schema is untouched** — same type, same `1..128` bounds, no property
added or removed — so this task changed no contract in the sense the frozen set means. But the
prose is part of the sealed document, and correcting it is a reseal and the owner's.
**This is the single most important thing in this report for the integrator to route.**

`docs/program/P02_SEAMS.md:508` carries the same sentence and has the same problem.
`web/src/widgets/decision-history/ui/decision-history.tsx:13` carries it a third time.

All three are `§4.7`'s shape — a document outliving the code it describes — and all three are
outside `allowed_paths`.

### 6.2 `DEBT_REGISTER.md` §D-74 miscounts the implementations

It says "four implementations — one in `bootstrap/` (a hotspot) and three in `tests/`". Both
shipped adapters are in `bootstrap/adapters.py` and both stand-ins are in
`tests/integration/api/conftest.py`: **two and two**. The total of four is right. Measured in
§3.1 by parsing every `build_router` call in the tree; the register is the integrator's.

### 6.3 `norms/__main__.py` now carries a redundant check and a false sentence

§2.3. The check is correct and refuses earlier with a better message; only its explanation of
*why* it exists is now stale. Outside `allowed_paths`.

### 6.4 A test about the mutation copy cannot be collected inside a mutation copy

`tests/integration/composition/test_mutation_copy_serves_a_tests_only_stream.py` reads
`ROOT / "Makefile"` at import. `make mutation-copy` does not copy the `Makefile`, so running
that module from inside the copy is a **collection error**, which aborts the whole run:

```
FileNotFoundError: [Errno 2] No such file or directory: '/root/w41author-mut/Makefile'
!!!! Interrupted: 1 error during collection !!!!
```

It is not a failure of the copy or of the test — each is right about its own job — but a sweep
that points at `tests/integration/composition` gets no results at all until it is excluded,
and an import-time error interrupts collection rather than reporting one red module. Nine
other modules under that directory baseline red on the copy for the same family of reasons
(`web/`, `infra/` and deploy scripts are not carried): 125 failed / 14 errors, every one of
them a missing path. Named here so the next stream does not read them as its own doing.

### 6.5 `web/tests/**` carries `'local-reviewer'` as a fixture value

`web/tests/unit/review/fixtures.ts:161` and `web/tests/unit/api/transport-rules.test.ts:115`
use it. Nothing fails — they are fixtures, not claims about the server, and the frontend
battery is green — but they now describe a value the product no longer produces. `web/**` is a
forbidden hotspot here and `web/tests/**` is **`W41-BLIND`'s** grant this wave, so this is a
cross-lane note rather than a defect.

### 6.6 A method note, because it nearly cost a wrong sentence

While answering "where does `author_label` reach a reader", the first query was
`grep -rn 'author_label' web/ | head -5`. All five hits were under `web/tests/`, and the
obvious reading — *the alpha UI never renders it* — is **false**. Re-querying without the pipe
found two `web/src` widgets that put it on screen. This is `W20-CODE`'s exact case from §12:
a correct query read before it finished. It is recorded because the wrong sentence would have
gone into §1.3, which is the paragraph the owner is being asked to act on.

---

## 7. Risks and known limitations

1. **The contract prose (§6.1) is unresolved.** The implementation is green and the sealed
   schema is untouched, but the document now describes behaviour the code does not have. If
   the owner reseals the description, nothing here changes; if the owner decides the *value*
   should have stayed a configured label, `git revert 14a0913 83751df` is the whole of it.
2. **Two reviewers presenting one idempotency key now conflict rather than replay.**
   `author_label` was already inside `append_decision_under_key`'s payload fingerprint before
   this wave; it now carries a value that differs per caller, so the same key from a different
   reviewer is `idempotency_key_reuse` instead of a replay of the first reviewer's event. That
   is the correct answer — replaying would attribute a decision to somebody who did not take
   it — and it is a behaviour change nobody asked for, so it is written down. The suite's
   `LedgerDecisionAdapter` was given the same fingerprint so the two paths agree.
3. **A credential outlives a rename** (§1.3, second property). One hour.
4. **`test_existence_is_not_a_full_read.py` asserts table names, not round-trip counts.** A
   deliberate choice — a count would pin an implementation detail — but it means an
   implementation that asked `audit_run` five times would pass. The property `D-74` is about
   is what is *loaded*, and that is what is asserted.
5. **The port-completeness guard resolves a class syntactically.** It follows base classes
   within the wiring file and an unambiguous name across the tree, and it *fails* on anything
   it cannot resolve. A wiring that builds its port through a factory function would therefore
   redden the guard rather than escape it — correct, and it will read as a false alarm to
   whoever writes that factory. The message says what to do.
6. **No feature flag**, as the brief's rollback section specifies. Each change is either a
   refusal that did not exist (A1's fail-closed path, A2) or a narrowing of a read (A3).

---

## 8. Instruction to the integrator

**Merge `agent/w41-author` at `83751df` onto the wave-41 base. Five commits, in order:**

```
07ff54f  docs(W41-AUTHOR): open the report before the first measurement
b56d103  fix(A2):  D-72 -- a proxy URL with no host is refused at construction
8877d5d  feat(A3): D-74 -- a parent-existence check no longer costs a full parent read
14a0913  feat(A1): D-78 -- a decision is attributed to the reviewer who made it
83751df  chore(A1): cite the commit that moved characterization records 10 and 11
```

(plus this report's own commit, docs-only, on top.)

* **Nothing shared is owned here.** No contract, no migration, no lockfile, no
  composition-root signature another lane reads. `contracts/**`, `db/migrations/**`, `web/**`,
  `Makefile`, `pyproject.toml`, `uv.lock`, `package-lock.json`, `DEBT_REGISTER.md` and
  `docs/program/dispatch/**` are all untouched — §9 is the diffstat.
* **Do not squash `14a0913` and `83751df`.** The second exists because a characterization
  record has to name the commit that decided its change, and that commit cannot name itself.
  Squashing leaves the record citing a hash that does not exist.
* **`W41-BLIND` and this lane do not overlap.** `tests/e2e/**` and `web/tests/**` are theirs
  and neither appears in this diff. §6.5 is a note for them, not a change.
* **Route §6.1 to the owner.** It is the only item here that needs a decision rather than a
  merge.
* **Three register rows are ready to close** — `D-72`, `D-74`, `D-78` — and one row wants a
  correction, `D-74`'s implementation count (§6.2). The register is yours.
* Re-gate after the merge. This branch's gate was taken on its own tree and a merge is a
  different tree.

---

## 9. Proof that the forbidden hotspots were not touched

```
$ git diff --stat 295ff04..HEAD
 docs/program/W41-AUTHOR.md                                       |  39 +++
 src/auditmanager/analysis/text/proxy.py                          |  27 ++
 src/auditmanager/api/routers/decisions.py                        |  26 +-
 src/auditmanager/api/routers/findings.py                         |  15 +-
 src/auditmanager/api/routers/ports.py                            |  46 +++
 src/auditmanager/bootstrap/adapters.py                           |  39 ++-
 src/auditmanager/decisions/__init__.py                           |   2 -
 src/auditmanager/decisions/ledger.py                             |  39 ++-
 tests/characterization/w13_baseline/records/10-appendDecision…   |  16 +-
 tests/characterization/w13_baseline/records/11-listDecisionHi…   |  16 +-
 tests/characterization/w13_baseline/test_response_baseline.py    |  22 ++
 tests/integration/analysis_text/test_proxy_adapter.py            |  71 ++++
 tests/integration/api/conftest.py                                |  42 +++
 tests/integration/api/test_authorization.py                      |  84 ++++-
 tests/integration/api/test_database_refusals.py                  |   1 +
 tests/integration/api/test_decision_authorship.py                | 356 +++++
 tests/integration/api/test_decision_journal.py                   |   6 +-
 tests/integration/api/test_existence_is_not_a_full_read.py       | 166 ++++
 tests/integration/composition/test_every_port_implementation…    | 278 ++++
 tests/integration/decisions/test_decision_ledger.py              | 107 ++++-
 tests/integration/decisions/test_keyed_append.py                 |   5 +
 tests/integration/decisions/test_rules_are_load_bearing.py       |   9 +
 tests/integration/exports/test_verdict_columns.py                |   5 +
 tests/integration/p02_journey/test_journey_figures.py            |   9 +-
 tests/integration/p02_journey/test_query_surface_over_the_cor…   |   2 +
 25 files changed, 1379 insertions(+), 49 deletions(-)
```

(figures as of `83751df`; this report's own commit adds one more line to the first row.)

Every path is inside `allowed_paths`: `src/auditmanager/decisions/**`,
`src/auditmanager/api/**`, `src/auditmanager/bootstrap/**`,
`src/auditmanager/analysis/text/proxy.py`, `tests/**`, `docs/program/W41-AUTHOR.md`.

Not present, one by one: `contracts/**` · `db/migrations/**` · `web/**` · `Makefile` ·
`pyproject.toml` · `uv.lock` · `package-lock.json` · `docs/program/DEBT_REGISTER.md` ·
`docs/program/dispatch/**` · any `docs/` path but this file.

`.env` outside this worktree was never opened; this lane's own `.env` was read and not
written. Every container touched was `gate-w41a-*`, through `make gate`'s own `up`, and no
other container on the host was started, stopped or inspected for anything but the check in
§10 below.

```
$ docker ps --format '{{.Names}}' | grep -c '^gate-w41a'
3
```

Three, and nothing else on this host was touched — the other ten containers running on it
belong to other lanes and other projects and were listed once, to confirm that.
