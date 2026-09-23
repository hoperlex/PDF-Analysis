# `W40-GUARDS` — two absent guards, and nine operations that were never nine

Base `ccaeed8`, branch `agent/w40-guards`, worktree `/root/w40guards`, gate lane `gate-w40b`.
Logs under `/root/w40-logs/guards-*`.

`D-66` and `D-67`. Both are closed. Nothing in `contracts/**` moved and nothing needed to:
the rule `D-67` asked this session to choose turned out to be written in the frozen document
already, operation by operation, and two implementations were not conforming to it.

---

## 1. `D-66` / `W37CERT4-5` — the fail-closed default

### What was missing

`require_authorization` reads the route's `operationId`, and `_operation_of` answers `None`
when there is none. `None` is in no register, so the request is guarded. The module says so
twice, in `_operation_of`'s docstring — *"An unreadable route is a closed route"* — and in
`require_authorization`'s: *"Everything else — including a request whose route the seam could
not identify — must present a credential this deployment's key produced."*

Nothing held it. Every route on the built application carries an `operationId`, so the claim
is true today and would go on reading as true on the day a route is added without one.

### The guard

`tests/integration/api/test_the_seam_holds_what_it_states.py`. **Behavioural**, and nothing
about the source is read: a real `Router` carrying the suite's real credential port, one
route registered with no `operation_id`, driven through `create_asgi_app` — the same
middleware stack, the same exception handlers, the same dependency — and asserted three ways.

| case | what it establishes |
|---|---|
| `test_the_fixtures_route_really_carries_no_operation_id` | the anti-vacuity: FastAPI did **not** assign one, so the three cases below exercise the default rather than the ordinary guarded path |
| `..._is_refused_without_a_credential` | refused `401 authentication_required` |
| `..._refuses_another_deployments_credential` | refused again on a path that has to reach `verify`, so an exemption cannot hide behind the `credentials is None` arm |
| `..._is_reachable_with_a_credential_this_deployment_minted` | the control: **guarded** means refused without and served with, and only the pair says that |
| `test_an_operation_id_that_is_not_a_string_reads_as_unidentifiable` | the `isinstance` narrowing is part of the default and not incidental |

### The mutation, and the red it now produces

`W37-CERT4`'s **M5**, applied to a proved mutation copy (`/root/w40guards-mut`, built with
`make mutation-copy`; `auditmanager.api.security.__file__` printed from inside the pytest run
and confirmed to resolve under the copy before any result was believed):

```
-        if _operation_of(request) in UNAUTHENTICATED_OPERATIONS:
+        if _operation_of(request) is None or _operation_of(request) in UNAUTHENTICATED_OPERATIONS:
```

**The three suites `W37-CERT4` named are still entirely green under it** —
`/root/w40-logs/guards-mut-M5-three-suites.log`:

```
103 passed, 1 warning in 14.75s
```

**The new file is not** — `/root/w40-logs/guards-mut-M5-new-guard.log`, verbatim:

```
.FF....                                                                  [100%]
=================================== FAILURES ===================================
____ test_a_route_the_seam_cannot_identify_is_refused_without_a_credential _____
        surface = _a_surface_carrying_an_unidentifiable_route()
        answer = surface.send("GET", UNIDENTIFIABLE, credential=None)
>       assert answer.status == 401, answer.body
E       AssertionError: b'{"the seam let this through":true}'
E       assert 200 == 401
E        +  where 200 = Answer(status=200, ... body=b'{"the seam let this through":true}').status
_ test_a_route_the_seam_cannot_identify_refuses_another_deployments_credential _
>       assert answer.status == 401, answer.body
E       AssertionError: b'{"the seam let this through":true}'
E       assert 200 == 401
=========================== short test summary info ============================
FAILED tests/integration/api/test_the_seam_holds_what_it_states.py::test_a_route_the_seam_cannot_identify_is_refused_without_a_credential
FAILED tests/integration/api/test_the_seam_holds_what_it_states.py::test_a_route_the_seam_cannot_identify_refuses_another_deployments_credential
2 failed, 5 passed, 1 warning in 0.09s
```

**And the anti-vacuity assertion is itself proved able to fail.** Giving the fixture's route
an `operation_id` in the copy's own `tests/` — `/root/w40-logs/guards-mut-D66vac.log`:

```
E       AssertionError: the route under test carries an operationId, so it does not exercise the default
E       assert 'anOrdinaryGuardedOperation' is None
FAILED ...::test_the_fixtures_route_really_carries_no_operation_id
1 failed, 6 passed, 1 warning in 0.07s
```

The **6 passed** in that line is the point of the case: with an `operationId` present the
three behavioural cases go on passing, for the wrong reason, and only that assertion says so.

---

## 2. `D-66` / `W37CERT4-6` — the timing-safe comparison, and exactly what the guard proves

### What it proves — stated plainly, before the evidence

Two tests, both **run-time observations of the shipped code path**. Neither reads the source
and neither is a name match.

1. **The call site is on the live path.** While a genuine credential is verified,
   `hmac.compare_digest` is called, and one of the calls carries the presented tag.
2. **That call's answer is the value the seam branches on.** Made to answer *yes* for a tag
   this deployment did not produce, the credential is accepted.

**What it does not prove: that the comparison runs in constant time.** Nothing in a gate can.
A constant-time comparison and a short-circuiting one return the same answers — that is the
whole of the property — so no assertion over answers separates them, and a timing measurement
inside a battery is a flaky test rather than a guard. The constant-time property is `hmac`'s,
and this file takes it from the standard library rather than re-measuring it.

So: **stronger than a call site, weaker than the property.** It forecloses every
re-implementation in which the *decision* is taken by comparing the bytes directly — which is
the one `W37-CERT4` wrote — and it would not notice a `compare_digest` that had itself been
replaced by something leaky. It is not the source guard the brief said would be acceptable;
it is not a behavioural proof of the timing property either, and calling it one would be
`D-61` with better manners.

### The mutations

**M4**, `W37-CERT4`'s own — `/root/w40-logs/guards-mut-M4-new-guard.log`:

```
-        if not hmac.compare_digest(presented_tag, self._tag(signed)):
+        if presented_tag != self._tag(signed):
```

Three suites under it: `103 passed` (`guards-mut-M4-three-suites.log`). The new file:

```
.....FF                                                                  [100%]
>       assert seen, "verify() compared the tag without calling hmac.compare_digest"
E       AssertionError: verify() compared the tag without calling hmac.compare_digest
E       assert []
...
        monkeypatch.setattr(hmac, "compare_digest", lambda left, right: True)
>       assert signer.verify(forged) is not None, (
E       AssertionError: hmac.compare_digest answered yes and the credential was still refused, so something other than that call decides whether the tag matches
E       assert None is not None
2 failed, 5 passed, 1 warning in 0.09s
```

**M4b — the mutation that separates a call from a decision**, and the reason the second test
exists:

```
-        if not hmac.compare_digest(presented_tag, self._tag(signed)):
+        if not hmac.compare_digest(presented_tag, self._tag(signed)) or presented_tag != self._tag(signed):
```

The call is still there. A source grep for `compare_digest` stays green. `/root/w40-logs/guards-mut-M4b-new-guard.log`:

```
FAILED tests/integration/api/test_the_seam_holds_what_it_states.py::test_the_seam_branches_on_what_that_comparison_answers
1 failed, 6 passed, 1 warning in 0.08s
```

One test passes and one fails, which is exactly the split the two are for.

---

## 3. `D-67` — the rule, the argument, and what changed

### The measurement first, because the row names the wrong operation

Every `GET` of the application **the composition root builds** — real adapters, real
database — driven with a well-formed 26-character ULID of the right prefix for each path
parameter, the prefixes read from `contracts/domain/v1/identifiers.json` rather than written
out. `/root/w40-logs/guards-d67-table-before.log`:

| operation | path | path names a parent | answer |
|---|---|---|---|
| `exportRunCsv` | `/runs/{run_id}/export.csv` | yes | `404 not_found` |
| `getDocumentVersion` | `/versions/{version_uid}` | yes | `404 not_found` |
| `getFinding` | `/findings/{finding_uid}` | yes | `404 not_found` |
| `getRunStatus` | `/runs/{run_id}` | yes | `404 not_found` |
| **`listDecisionHistory`** | `/findings/{finding_uid}/decisions` | yes | **`200`, `items: []`** |
| `listDecisions` | `/decisions` | **no** | `200`, `items: 9` |
| `listDocuments` | `/projects/{project_uid}/documents` | yes | `404 not_found` |
| `listProjects` | `/projects` | **no** | `200`, `items: 38` |
| **`listRunFindings`** | `/runs/{run_id}/findings` | yes | **`200`, `items: []`** |
| `listRuns` | `/versions/{version_uid}/runs` | yes | `404 not_found` |
| `listVersions` | `/documents/{document_uid}/versions` | yes | `404 not_found` |
| `streamDocumentVersionContent` | `/versions/{version_uid}/content` | yes | `404 not_found` |

**Twelve `GET` operations. Ten address a parent identity. Two of the ten disagreed, and
neither of them is `listDecisions`.**

`D-67`, its one-line summary in `DEBT_REGISTER.md`, and this brief all name `listRunFindings`
and **`listDecisions`**. `listDecisions` is `GET /decisions`: it carries no parent identity,
declares no `404` in the frozen document, and answered `200` with nine items here. The
operation that disagreed is **`listDecisionHistory`**, `GET /findings/{finding_uid}/decisions`,
which does carry a parent. `W37-CERT4`'s own evidence table has the right *path* in it; the
row written from that table named the wrong *operation*, and three documents have repeated it
since.

### The rule

> **A collection whose path carries a parent identity answers `404 not_found` when that
> identity names nothing. A collection whose path carries none answers `200` with the page it
> has, which may be empty.**

### The argument — it is the contract's rule, not this session's

The frozen document already states it, operation by operation. Reading `responses` off
`contracts/api/v1/openapi.json`:

- every one of the six `GET` collections with a placeholder in its path — `listDocuments`,
  `listVersions`, `listRuns`, `listRunFindings`, `listDecisionHistory`, `exportRunCsv` —
  declares **`404`**;
- the two with no placeholder — `listProjects`, `listDecisions` — declare **none**.

So `listRunFindings` and `listDecisionHistory` were **declaring a `404` they had never
produced**. What changed here is conformance to a contract frozen at `a5f4001`; no contract
moved, and none needed to. Had the rule gone the other way — the majority changing to `200` —
it would have contradicted six declarations at once and needed the reseal this stream does not
own.

**`listDecisions` is not a reasoned exception. It is the rule applied to a path with no
parent.** `W38-KB`'s argument — recorded in `decisions.py` beside the operation, *"the path
addresses no parent identity, so there is no identity that could be missing"* — is not an
exception clause. It is the rule's second sentence, and `listProjects` is covered by the same
sentence without anyone ever having needed to argue it. The answer is therefore **not** "seven
are right, one changes, one is a reasoned exception". It is: **ten operations address a
parent, eight already agreed, two changed, and the two that address none were never in the
question.** The rule has no exceptions.

### What changed, and where

Two narrow router sites, and `build_router`'s two internal calls:

- `src/auditmanager/api/routers/findings.py` — `list_run_findings` proves the run exists
  through `RunPort.get_run_status` before reading the collection;
- `src/auditmanager/api/routers/decisions.py` — `list_decision_history` proves the finding
  exists through `FindingPort.get_finding`;
- `src/auditmanager/api/routers/__init__.py` — each builder is handed the port that owns its
  parent, positionally and required. A keyword with a `None` default would have been a silent
  fallback to the behaviour being closed.

`build_router`'s own signature is unchanged, so the ten `build_router` call sites in `tests/`
did not move.

**Why the router and not the adapter**, where `listRuns` proves its own parent. The statement
being honoured is the *frozen contract's*, about *this operation*, and the operation is the
router function. Put in an adapter, the rule holds for whichever implementation happens to be
wired; put here, it holds for the surface — and this router has three different wirings in
`tests/` alone, none of which found the defect. The counter-argument is real and is recorded
below as a limitation rather than argued away.

### Both halves are guarded, because one is satisfiable by a wrong implementation

A sweep that only looks for `404` is passed by an implementation that refuses **every** empty
collection, which destroys the distinction from the other side. So:

- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` — the sweep
  over the composed application: every `GET` addressing a parent refuses an absent one; the
  two addressing none answer a page; and the partition counts (10 / 2) are literals, so an
  operation added later cannot join the surface without somebody classifying it.
- `tests/integration/api/test_absent_and_empty_are_not_the_same_answer.py` — the other half
  over real rows: a run that published nothing, a finding nobody has decided on, a run
  filtered to a category it does not publish, and a project with no documents each answer
  `200` with an empty page — beside the refusals for the absent forms of the same three.

### The mutations

| case | mutation | result |
|---|---|---|
| `D67-M1` | delete `runs.get_run_status(run_id=run_id)` from `list_run_findings` | `2 failed, 8 passed` — the sweep names `listRunFindings`, and `test_a_run_that_does_not_exist_is_refused_by_its_findings_collection` fails |
| `D67-M2` | delete `findings.get_finding(...)` from `list_decision_history` | `2 failed, 8 passed` — the sweep names `listDecisionHistory`, and `test_a_finding_that_does_not_exist_is_refused` fails |
| `D67-M3` | **over-broad repair**: refuse every *empty* findings collection with `404` | `2 failed, 8 passed` — **the composition sweep stays green** and both empty-page cases fail. This is the case that proves the second half is not decoration |
| `D67-M4` | add an eleventh parented `GET` to `build_router` | `2 failed, 1 passed` — the partition guard reddens naming `listRunAnnexes`, and so does the sweep |

`D67-M1`, verbatim, from `/root/w40-logs/guards-mut-D67M1.log`:

```
E       AssertionError: these operations answered something other than 404 not_found for an identity that names nothing: [('listRunFindings', '/runs/run_01ARZ3NDEKTSV4RRFFQ69G5FAV/findings', 200, None)]
E       AssertionError: (200, b'{"items": [], "page": {"next_cursor": null}}')
E       assert 200 == 404
FAILED tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py::test_every_get_that_names_a_parent_refuses_an_identity_that_names_nothing
FAILED tests/integration/api/test_absent_and_empty_are_not_the_same_answer.py::test_a_run_that_does_not_exist_is_refused_by_its_findings_collection
2 failed, 8 passed, 1 warning in 1.36s
```

`D67-M3`, the one worth reading twice — the sweep passes and the distinction is gone:

```
E       AssertionError: (404, b'{"contract_version": "1.0.0-draft.1", "error_code": "not_found", ... "details": {"aggregate_type": "AuditRun"}}')
E       assert 404 == 200
FAILED tests/integration/api/test_absent_and_empty_are_not_the_same_answer.py::test_a_run_that_published_nothing_answers_an_empty_page
FAILED tests/integration/api/test_absent_and_empty_are_not_the_same_answer.py::test_a_run_that_exists_answers_an_empty_page_for_a_filter_nothing_matches
2 failed, 8 passed, 1 warning in 1.33s
```

`D67-M4`:

```
E       AssertionError: the surface now has 11 GET operations addressing a parent identity, not 10: (... ('listRunAnnexes', '/runs/{run_id}/annexes'), ...)
E       assert 11 == 10
FAILED ...::test_the_surface_partitions_into_the_two_halves_of_the_rule
FAILED ...::test_every_get_that_names_a_parent_refuses_an_identity_that_names_nothing
2 failed, 1 passed, 1 warning in 1.23s
```

### After

`/root/w40-logs/guards-d67-table-after.log`: **ten of ten** parented `GET`s answer
`404 not_found`; `listProjects` and `listDecisions` answer `200` with a page, unchanged.

---

## 4. The gate, case by case

Two full runs, both in lane `gate-w40b`, both read for `GATE OK` in the log rather than
believed from a status a harness handed back — `OPERATING_CONSTRAINTS.md` §4.62, and the
notification for **both** of these runs carried exit code 0, which on the baseline run was
true and is not evidence either way.

| case | tree | battery | foundation | frontend | whitespace |
|---|---|---|---|---|---|
| baseline | `ccaeed8`, clean | `2265 passed, 5 skipped, 169 subtests` in 326.84s | `35 passed` in 29.30s | `1013` in `72` files | pass |
| final | `HEAD`, clean | `2282 passed, 5 skipped, 169 subtests` in 335.02s | `35 passed` in 29.91s | `1013` in `72` files | pass |

**The brief's baseline figures are correct**, to the case: `2265 / 5 / 169`, `35`,
`1013 in 72`. Both logs are kept: `/root/w40-logs/guards-gate-baseline.log`,
`/root/w40-logs/guards-gate-final.log`.

**The delta is exactly the seventeen cases added here**: `2265 -> 2282` passed, `5 -> 5` skipped, `169 -> 169` subtests, foundation `35 -> 35`, frontend `1013 in 72 -> 1013 in 72`. No existing case changed status and no frontend case was added, which is right: nothing in `web/` moved.

Case by case, the seventeen are:

| file | cases | what they hold |
|---|---|---|
| `tests/integration/api/test_the_seam_holds_what_it_states.py` | 7 | `D-66`: the fail-closed default (4, one of them the anti-vacuity and one the control) and the tag comparison (2), plus the `isinstance` narrowing (1) |
| `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` | 3 | `D-67`: the partition and its two literal counts, the sweep over every parented `GET`, and the two parentless collections |
| `tests/integration/api/test_absent_and_empty_are_not_the_same_answer.py` | 7 | `D-67`'s second half: three present-but-childless parents answering `200`, beside the three absent ones refusing, and the control that a populated run still answers its findings |

Nothing existing changed status. The final run was taken with the peer lane `gate-w40a`
running its own gate alongside — `OPERATING_CONSTRAINTS.md` §4.6 — which is recorded because
the wall clock is evidence about the machine and this figure should not be compared with the
baseline's as if it were a measurement of the code.

---

## 5. Limitations and risks

1. **The parent check costs a parent read, and both reads build far more than a yes/no.**
   The shipped `RunAdapter.get_run_status` assembles the whole `RunStatus` — run row, stage
   rows, cost — and `FindingAdapter.get_finding` reads the finding's evidence, its current
   verdict **and its decision history**, which `listDecisionHistory` then reads again. A
   narrow existence method on `RunPort` and `FindingPort` is the right shape and is **not**
   this stream's to add: the port implementations live in `src/auditmanager/bootstrap/`, a
   forbidden hotspot here, and `test_every_adapter_accepts_every_parameter_its_port_declares`
   turns a port method nobody implements into a red gate. Worth a row.
2. **The repair is in the router and `listRuns`/`exportRunCsv` prove their parents in the
   adapter.** Two places now hold the same kind of rule. The argument for the router is in §3
   and in both source comments; the inconsistency is real and is recorded rather than hidden.
3. **`appendDecision` was not measured.** `D-67` is about collections and the sweep is over
   `GET`s. What `POST /findings/{finding_uid}/decisions` answers for an absent finding is
   unmeasured here.
4. **`W40-LIMIT` is live in `src/auditmanager/api/**`.** Three router files moved in this
   branch: `findings.py`, `decisions.py` and `__init__.py`. `__init__.py` is the likeliest
   collision if that stream added middleware or a dependency there; the change here is six
   lines inside `build_router`.
5. **The sweep's identities come from the catalog, and a wrong prefix would not show up in
   it.** Measured: `GET /documents/prj_01ARZ3NDEKTSV4RRFFQ69G5FAV/versions` — a project
   identity where a document identity belongs — answers **`404 not_found`**, the same answer
   a correct-prefix absent identity gets, so the sweep cannot tell a bad
   parameter-to-prefix mapping from a working guard. What defends it is that the mapping is
   read from `contracts/domain/v1/identifiers.json` at run time and an unresolvable path
   parameter raises rather than defaulting — the existing sweep in `test_router_answers.py`
   does default, to `prj`, which is why it probes `listVersions` with a malformed identity
   and has never noticed. And the second file closes the gap from the other side for
   `run_id`, `finding_uid` and `project_uid`: those three identities are proved to resolve,
   because a real one of each answers `200` on the same operation.
6. **The second file's run existence is measured through a stand-in.** `shipped_router`
   wires the real `FindingAdapter` and `DecisionAdapter` but the suite's own
   `SeamRunAdapter` for `RunPort`. The shipped `RunAdapter` is what the composition sweep
   drives. Said here rather than left to be assumed: neither file alone covers both.

---

## 6. Reported, not repaired

**The fail-closed default is scoped to the router, not to the application, and four routes
live outside it.** Measured (`/root/w40-logs/guards-routes-and-prefix.log`):

```
application.router.routes total = 18
  carrying an operation_id  = 18
  carrying NONE             = 0  []
served ASGI app routes total = 4
  carrying NONE = 4  [('/openapi.json', None), ('/docs', None), ('/docs/oauth2-redirect', None), ('/redoc', None)]
```

and, with no `Authorization` header at all:

```
/openapi.json 200 77744
/docs 200 1015
/redoc 200 897
```

`api/app.py` attaches the seam with `app.include_router(router, dependencies=[...])`, so the
dependency applies to the router's eighteen routes and to nothing else. FastAPI's own four
are on the **application**. They never reach `require_authorization`, `_operation_of` is
never asked about them, and **the fail-closed default cannot apply to them at all** — they
are not unidentifiable routes that are guarded, they are routes outside the guard.

Two consequences worth a row, and neither is repaired here because both are outside this
task:

1. `test_every_operation_but_the_register_is_behind_the_seam` is a true statement **about the
   router**. Nothing says it about the application, and a route registered on the app rather
   than through `build_router` is open whatever its `operationId` — which is the same class
   of gap `D-66` is, one level out.
2. The deployment serves its own OpenAPI document and a Swagger UI unauthenticated. The
   document is public in this repository and `create_documentation_app` exists to serve it,
   so this is probably intended; **it is nowhere stated and nowhere tested.**
   `test_served_document_and_health_plane.py` asserts only that the *health* app publishes
   no document. A decision nobody wrote down is not a decision a reviewer can check.

---

## 7. Every premise of this brief I measured and found false

Nine, and one of them changes what `D-67` is about.

1. **`D-67`'s minority is `listDecisionHistory`, not `listDecisions`.** The brief, the
   `DEBT_REGISTER.md` row, its one-line summary and `WAVE_PLAN_39_42.md` all name
   `listRunFindings` and **`listDecisions`**. Measured over the composed surface:
   `listDecisions` is `GET /decisions`, carries no parent identity, declares no `404`, and
   answered `200` with nine items. The operation that disagreed is **`listDecisionHistory`**
   (`GET /findings/{finding_uid}/decisions`). `W37-CERT4`'s evidence table has the right
   path; the row written from it named the wrong operation, and three documents have carried
   it since. Command: `/root/w40-logs/guards-d67-table-before.log`, at `ccaeed8`.

2. **There are not nine collection operations, and no partition of this surface gives
   nine.** Measured on the built application: **twelve** `GET` operations, **ten** of which
   carry a parent identity. Collection-shaped: **eight** (`listProjects`, `listDocuments`,
   `listVersions`, `listRuns`, `listRunFindings`, `listDecisionHistory`, `listDecisions`,
   `exportRunCsv`), of which **six** carry a parent. The brief's "the other seven collection
   operations" implies nine; `W37-CERT4`'s table, which is where the figure comes from, has
   **eight rows**. I checked all twelve, which is the superset.

3. **`listDecisions` does not need a stated exception, so the rule has none.** The brief
   offers "seven are right, one changes, one is a reasoned exception". `listDecisions` was
   never in the minority (premise 1), and the rule stated over *the path* covers it and
   `listProjects` without an exception clause. `W38-KB`'s argument is the rule's second
   sentence, not a carve-out from it.

4. **Nothing here is a contract change, and the rule did not have to be chosen.** The brief
   treats the rule as this stream's decision and warns that a contract change means stopping.
   The frozen document already states it operation by operation: all six parented `GET`
   collections declare `404`, both parentless ones declare none. `listRunFindings` and
   `listDecisionHistory` were declaring a `404` they never produced. The repair is
   conformance to a contract frozen at `a5f4001`.

5. **The mutation leaves the three suites at 103 green, not 77.** `W37-CERT4` measured 77;
   re-measured at `ccaeed8` with **M5** applied to a proved mutation copy:
   `103 passed, 1 warning in 14.75s` (`/root/w40-logs/guards-mut-M5-three-suites.log`). Waves
   38 and 39 added 26 cases to those three suites and **not one of them can see the
   fail-closed default either**, which is a sharper statement of the finding than the figure
   it replaces. The stale number is `OPERATING_CONSTRAINTS.md` §4.7's residue rule applied to
   a count: it was quoted forward rather than re-measured.

6. **Disk is at 91%, not 87%, and `make gate` builds no images.** `df -h /root` at the start
   of this session and again at the end: `119G total, 102G used, 11G available, 91%`. The
   instruction is unaffected — nothing here builds an image — but the tension the brief sets
   up is not real, and that matters: `OPERATING_CONSTRAINTS.md` §4.6 describes
   `test_deploy_image_identity.py` as *"a test that builds and deploys real images"*, and its
   own header says the opposite — *"the suite may not build an image, start a container or
   reach a daemon. The stub is a small image store"*. A session told *"disk is nearly full,
   do not build images"* could reasonably decline to run the gate at all on that description.
   §4.6's actual lesson — a contention red reads like a broken guard — stands.

7. **The worktree was not provisioned with a lane.** The brief says *"Provisioned; do not
   re-bootstrap"*, and `/root/w40-prov-g.log` shows `.venv` and `node_modules` really were
   built. **There was no `.env`**, so none of the six lane values existed and `make gate`
   would have been refused by `require_env_coherence` before touching a service. This is
   exactly what `OPERATING_CONSTRAINTS.md` §4 predicts of a `git worktree add`, and it is
   the second half of the checklist that section spells out: a private prefix *and the six
   lane values*. I wrote `.env` from `.env.example` with the registry's row for `gate-w40b`,
   `DATABASE_URL` and `S3_ENDPOINT_URL` carrying the same ports.

8. **`/root/w40-logs/` did not exist.** The brief names it as the place to write. Created.

9. **`PORT_REGISTRY.md` is at `docs/program/dispatch/PORT_REGISTRY.md`**, beside
   `OPERATING_CONSTRAINTS.md`, not under `docs/program/`. The brief is careful to say
   *"note that path, it is `dispatch/`"* for the constraints file and then lists the registry
   without one — the same trap §12 records against itself, one file over.

**Measured and found true**, recorded because a premise check that only reports failures is
not a check: the baseline gate figures (`2265 / 5 / 169`, `35`, `1013 in 72`); the lane row
in `PORT_REGISTRY.md`; `tests/**` being uncontested — `W40-LIMIT` has touched
`src/auditmanager/access/**`, `bootstrap/adapters.py`, `db/migrations/**`, `web/src/**` and
two new test files, and **no file in `src/auditmanager/api/routers/**`**; and the brief's
*"all eighteen routes carry one"* — measured, `application.router.routes` = **18**, all eighteen carrying one, none without (`/root/w40-logs/guards-routes-and-prefix.log`). The `DEBT_REGISTER.md` row's *sixteen* is the stale figure; the brief's eighteen is right. **With one correction, in §6**: eighteen is the count of routes **on the router**, and the served application carries four more that the seam never sees.

**Not re-measured, and so not claimed either way:** `W37-CERT4`'s statement that four of its
six mutations reddened. Only M4 and M5 were re-run here.

---

## 8. For the integrator

- Merge order does not matter for `contracts/**`, `db/**`, `web/**`, `infra/**` — none moved,
  and `git diff --stat ccaeed8..HEAD` is six files: three routers and three new test files.
- **`W40-LIMIT` and this stream do not overlap.** Measured against its worktree at the time
  of writing: it has touched `src/auditmanager/access/**`, `src/auditmanager/bootstrap/
  adapters.py`, `db/migrations/**`, `web/src/**`, two docs and two new test files, and **no
  file under `src/auditmanager/api/routers/**`**. Note that `adapters.py` is where `D-67`'s
  repair would have gone had the allowed paths permitted it, so the router choice avoided a
  collision as well as being argued for on its own terms.
- `D-66` and `D-67` can both be closed. **`D-67`'s row names the wrong operation** and should
  be corrected to `listDecisionHistory` as it is closed, because `WAVE_PLAN_39_42.md` and the
  wave-40 briefs quote it onward.
- New rows worth opening: the cost of the parent read (§5.1); the two findings in §6; and the
  stale figures listed in §7 — §4.6's description of `test_deploy_image_identity.py`, and the
  `77` that should now read `103`.
- Nothing was tagged, pushed or merged, and `main`/`dev` were not touched.
