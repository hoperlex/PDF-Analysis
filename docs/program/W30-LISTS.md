# W30-LISTS — the hand-maintained-subset class, measured and closed

**Task:** `W30-LISTS`. **Base:** `ac7c348`. **Branch:** `agent/w30-lists`, worktree `/root/w30lists`.
**Contracts touched:** none. **Sets whose membership changed:** none.

The brief asked for a class to be closed, not a member repaired: *a hand-maintained subset
standing in for a set the contract or a catalog already defines, with nothing that fails when
the authority grows.* This is the census, the repairs, the one list that is wrong today, and
the places the brief's starting points turned out not to be members.

---

## 0. What the sweep actually found, in one paragraph

Thirty-one hand-maintained collections were examined across `src/auditmanager/**` and
`web/src/**`. Most were already derived or already proved — this tree is in better shape than
the brief's framing suggests. **Nine were unproved and are now guarded**, with eighteen
mutations run and every one of the eighteen new test cases watched to fail. **One is wrong
today** — `storage/errors.py`'s `SAFE_DETAIL_KEYS` — and per the brief it is reported and
*not* changed. **Five of the integrator's ten starting points are not members of the class**,
for five different reasons, and one of them already had the exact cross-check the brief asked
whether anything provided.

---

## 1. The census

Authority column names the artifact that decides. "Bucket" is the brief's three, plus **wrong**.

### 1.1 The repairs — legitimately narrower (or wider), and now proved

| Set | Site | Authority | Was | Now |
|---|---|---|---|---|
| `_TERMINAL_STATES` | `src/auditmanager/runs/carrier.py:319` | `state-machines.json` `machines.audit_run.terminal` | **unproved** — no test referenced it at all | `==` the machine's terminals, and `⊆` its states |
| `TERMINAL_RUN_STATES` / `NON_TERMINAL_RUN_STATES` | `web/src/shared/api/run-state.ts:18,21` | same | **partition proved, split unproved** (see §1.5) | `==` the machine's terminals / `==` the rest |
| `STAGE_STATUSES` | `src/auditmanager/findings/terminal.py:36` | `stage-result.schema.json` `properties.status.enum` | **unproved** — the grep that says otherwise finds the *migration's* same-named tuple | `==` the schema's enum |
| `PC01_STAGES` | `src/auditmanager/runs/repository.py:53` | `stage-registry.json` stage order | **unproved** — three suites use it, none checks it | ordered prefix of the registry, `⊆`, and a strict narrowing |
| `CATEGORIES` | `src/auditmanager/analysis/text/prompt.py:41` | `openapi.json` `FindingCategory` | **unproved** — a test pins its own literal copy | `==` the enum, in order |
| `_DECLARED_MODES` | `src/auditmanager/bootstrap/settings.py:52` | `openapi.json` `ProviderMode` | **unproved** | covers every contract mode, and the only extra is `proxy` |
| `AUTHORIZATION_ERROR_CODES` | `web/src/shared/api/authorization.ts:25` | `error-codes.json` `codes[*].category == "authorization"` | **half proved** — `⊆` catalog at compile time; the *category* claim unchecked | `==` the category, strictly narrower than the catalog |
| `QUERY_NAMESPACES` | `web/src/shared/api/query-keys.ts:25` | `web/docs/PC01_UI_SEAM.md` §6 | **unproved** — the existing test restates the four names as a literal | `==` the seam table's first segments, **and** `==` what every builder in `queryKeys` produces |
| `SQLSTATE_TO_CATALOG_CODE` | `src/auditmanager/shared/db/schema.py:50` | `error-codes.json` `codes` | **unproved** — values pinned to a literal, never to the catalog | values `⊆` the catalog |

### 1.2 Derived — generated from the authority, nothing to do

| Set | Site | How |
|---|---|---|
| `PC01_ERROR_CODES` | `web/src/shared/api/errors.ts:60` | derived by `web/tests/contract/pc01-error-codes.contract.test.ts` from the OpenAPI document and the catalog; `analysis_failed` carried as a registered blind spot with its reason. **Verified this wave: 9 tests, green.** |
| `CATALOG` (`errors.ts:88`) | same | `new Set(ERROR_CODE_VALUES)` |
| `CATALOG_SENTENCES` | `web/src/entities/audit-run/model/terminal-reason.ts:63` | `Readonly<Record<ErrorCode, string>>` — a twenty-third code stops the build |
| `UNGROUNDED_REASONS` | `src/auditmanager/findings/grounding.py:61` | `frozenset(r.value for r in UngroundedReason)`, and the enum is pinned to the migration CHECK by two suites |
| `_MEMBERS` | `src/auditmanager/shared/errors/codes.py:76` | built from the `ErrorCode` enum, itself built from the catalog |
| `PROVIDER_MODES` | `web/src/entities/audit-run/model/run-presentation.ts:34` | `new Set(PROVIDER_MODE_VALUES)` |
| `_ALPHABET_SET` | `src/auditmanager/shared/identity/ulid.py:29` | `frozenset(_ALPHABET)` |
| `SERVER_ONLY_VARIABLES` | `web/src/shared/config/server-env.ts:42` | built from the two variable-name constants |
| `REQUIRED_VARS` | `src/auditmanager/storage/settings.py:25` | built from the five `*_VAR` constants above it |
| `MANIFEST_ROLE_SOURCE_DOCUMENT` | `src/auditmanager/documents/models.py:79` | read out of `stage-registry.json` at import |
| `DECLARED_EVENT_TYPES` | `src/auditmanager/decisions/ledger.py:47` | `PC01_EVENT_TYPES \| {"revoke"}` |

### 1.3 Legitimately narrower, and already proved — nothing to do

| Set | Site | What proves it |
|---|---|---|
| `NON_TERMINAL_RUN_STATES` + `TERMINAL_RUN_STATES` as a **partition** | `web/src/shared/api/run-state.ts` | the two-direction compile-time proof. Left untouched, as instructed; §1.5 says what it does and does not prove |
| `CSV_COLUMNS` | `web/src/shared/api/csv-columns.ts:19` | `web/tests/contract/csv-columns.contract.test.ts` parses `P02_SEAMS.md` §6 **and** `tests/integration/exports/test_frozen_column_list.py` ties the seam table, `COLUMNS` and `CSV_COLUMNS` together |
| `COLUMNS`, `SORT_KEY` | `src/auditmanager/exports/serializer.py:37,59` | same file, including `_web_columns() == tuple(COLUMNS)` |
| `RETRYABLE_STAGE_ERRORS` | `src/auditmanager/runs/retry.py:80` | `RetryPolicy.__post_init__` reads `code.retryable` from the catalog and **refuses to construct** on a code the catalog does not mark retryable. Structural, at the only place it can be widened |
| `TERMINALS_FROM_VALIDATING` | `src/auditmanager/findings/terminal.py:41` | `test_terminal_rules_are_load_bearing.py` — `⊆ declared` and `declared - X == {"cancelled"}` |
| `STRANDED_STATES` | `src/auditmanager/runs/reconciliation.py:72` | checked against the machine, not asserted as a literal |
| `PC01_EVENT_TYPES`, `VERDICT_FOR_EVENT` | `src/auditmanager/decisions/ledger.py:44,51` | `DECLARED_EVENT_TYPES - PC01_EVENT_TYPES == {"revoke"}`, with a mutation test |
| `CALL_STATUSES`, `_STATUSES_THAT_ANSWERED` | `src/auditmanager/analysis/text/provenance.py:41,47` | `test_model_call_record_rules.py` reads `ck_model_call_status` out of migration `0005` |
| `IDENTITY_TYPES_BY_ENTITY`, `UNALLOCATED_IN_PC01` | `src/auditmanager/shared/identity/ids.py:265,275` | `tests/contract/domain_p02/test_identifier_catalog.py` |
| `PC01_STAGE_IDS` | `web/src/entities/audit-run/model/run-presentation.ts:162` | `STAGE_ID_VALUES.slice(0, 4)` plus `satisfies readonly StageId[]` |
| `UNEVALUATED_GUARDS` and the other three | `src/auditmanager/runs/scope.py` | the module is data on purpose and a test reads it; counts derived from the tuples |
| `_FORBIDDEN` | `src/auditmanager/shared/errors/envelope.py:39` | `test_envelope_screen_rules.py` holds the six to the docstring's enumeration |
| `_STATUS_CODES`, `_ENUM_VALUES`, `AGGREGATE_OF_PATH_PARAMETER` | `src/auditmanager/api/routers/handlers.py` | typed `Mapping[..., ErrorCode]`, so a code removed from the catalog fails type-checking |

### 1.4 Not members of the class

| Set | Site | Why not |
|---|---|---|
| `_NOT_FOUND_CODES`, `_NO_BUCKET_CODES`, `_DENIED_CODES` | `src/auditmanager/storage/s3.py:77-79` | **AWS's vocabulary, not this programme's.** No contract or catalog in this repository defines them, and no authority here can grow. Adding a guard would mean pinning them to a copy of themselves. Out. |
| `_RUN_COLUMNS`, `_COLUMNS` | `runs/repository.py:60`, `ingest/commands.py:70` | SQL projection lists. The authority is the DDL, and a wrong name fails the query loudly at the first call rather than silently. Out. |
| `FORWARDED_REQUEST_HEADERS` / `FORWARDED_RESPONSE_HEADERS` | `web/src/shared/api/credentialed-forward.ts:45,60` | HTTP header names. No contract set. |
| `MODEL_STUBS` | `src/auditmanager/analysis/text/proxy.py:47` | provider-side placeholder names. |
| `NAMING_CONVENTION` | `src/auditmanager/shared/db/schema.py:19` | SQLAlchemy configuration. |

### 1.5 One thing worth saying about the exemplar

`run-state.ts` was not touched and should not be. But the proof it carries is narrower than
it reads, and the distinction matters for the next session that copies the pattern:

```ts
const _partitionCoversContract: readonly RunState[] = [...NON_TERMINAL_RUN_STATES, ...TERMINAL_RUN_STATES];
const _contractCoversPartition: readonly (NonTerminalRunState | TerminalRunState)[] = RUN_STATE_VALUES;
```

This proves every contract state is **classified**. It cannot prove the classification is
**right**, because the generated enum carries no terminal flag. A twenty-third state filed
into the wrong half still compiles. The split is a reading of
`contracts/domain/v1/state-machines.json`, and nothing read that document. The new web
contract suite does, so the compile-time proof (every state classified) and the contract
proof (classified correctly) now sit side by side.

This also settles the brief's "two hand-written terminal splits on two sides of the wire is
its own question". It is a question, and the answer is not to delete one of them: they serve
different layers and neither can import the other. Both are now pinned to the same clause of
the same contract file, so they cannot drift apart without one of the two reddening.

---

## 2. The repairs, with the red output

Guards: `tests/contract/domain_p02/test_narrow_sets_against_contracts.py` (10 cases) and
`web/tests/contract/narrow-sets.contract.test.ts` (8 cases). Every assertion is about a
**relationship** — `==`, `⊆`, `<`, "the difference is exactly this" — and none is a
hard-coded count.

**Method.** Python mutations ran in `/root/w30lists-mut`, built with
`make mutation-copy MUT=/root/w30lists-mut FULL=1` so `contracts/` is a real copy and
mutable. The copy was baselined green before any mutation (9/9, then 10/10) and confirmed to
be the imported tree:

```
/root/w30lists-mut/src/auditmanager/runs/carrier.py
/root/w30lists-mut/src/auditmanager/findings/terminal.py
CONTRACTS = /root/w30lists-mut/contracts
```

The web guards read `contracts/` through a `REPO_ROOT` derived from the test file's own
location, so a `src`-only copy cannot reach them. A second tree, `/root/w30lists-webmut`,
holds a copy of `contracts/` and of `web/` with `node_modules` symlinked; it was baselined
green (6/6, then 8/8) before any mutation. Every mutation below was reverted and re-run green.

### M1 — the authority grows a terminal

`contracts/domain/v1/state-machines.json`: `machines.audit_run.terminal += "archived"`.

```
E       AssertionError: runs/carrier.py's _TERMINAL_STATES no longer matches contracts/domain/v1/state-machines.json machines.audit_run.terminal. A terminal the carrier does not know is a terminal it will overwrite.
E       assert {'cancelled',..., 'published'} == {'archived', ..., 'published'}
E         Extra items in the right set:
E         'archived'
```

### M2 — the narrow list shrinks

`_TERMINAL_STATES` drops `"cancelled"`.

```
E       AssertionError: runs/carrier.py's _TERMINAL_STATES no longer matches contracts/domain/v1/state-machines.json machines.audit_run.terminal. ...
E       assert {'failed', 'p..., 'published'} == {'cancelled',..., 'published'}
E         Extra items in the right set:
E         'cancelled'
```

### M9 — the narrow list gains a state the machine has never heard of

`_TERMINAL_STATES += "archived"`.

```
E       AssertionError: assert {'archived', ..., 'published'} <= {'cancelled',...'queued', ...}
E         Extra items in the left set:
E         'archived'
```

### M3 — the stage-result schema grows a status

```
E       AssertionError: findings/terminal.py's STAGE_STATUSES no longer matches contracts/analysis/v1/stage-result.schema.json properties.status.enum. select_terminal refuses any status outside this set, so a status the schema declares and this set omits fails a run that the contract says is well-formed.
E       assert {'failed', 'p..., 'succeeded'} == {'aborted', '..., 'succeeded'}
E         Extra items in the right set:
E         'aborted'
```

### M4 — the registry reorders its first two stages

```
E       AssertionError: runs/repository.py's PC01_STAGES is no longer a prefix of contracts/analysis/v1/stage-registry.json's stage order. ...
E       assert ['source_prep...ext_analysis'] == ['page_geomet...ext_analysis']
E         At index 0 diff: 'source_preparation' != 'page_geometry_extraction'
```

### M5 — `PC01_STAGES` widens to the whole registry plus an invented stage

Three cases red at once — ordering, membership, and strictness:

```
E       AssertionError: runs/repository.py's PC01_STAGES is no longer a prefix of ...
E         Left contains one more item: 'invented_stage'
E       AssertionError: assert {'block_analy...d_stage', ...} <= {'block_analy...ication', ...}
E         Extra items in the left set:
E         'invented_stage'
E       AssertionError: assert {'block_analys...d_stage', ...} < {'block_analys...ication', ...}
E         Extra items in the left set:
E         'invented_stage'
```

### M6 — `FindingCategory` grows a third category

```
E       AssertionError: analysis/text/prompt.py's CATEGORIES no longer matches the FindingCategory enum of contracts/api/v1/openapi.json. The prompt's response schema is built from this tuple, so a category the contract declares and the prompt omits is one no run can produce.
E       assert ['internal_co..._placeholder'] == ['internal_co...ss_reference']
E         Right contains one more item: 'missing_cross_reference'
```

### M7 — `ProviderMode` grows a mode the deployment cannot configure

```
E       AssertionError: bootstrap/settings.py refuses a provider mode the contract declares. A mode in ProviderMode that _DECLARED_MODES omits cannot be configured at all.
E       assert {'live', 'rec..., 'synthetic'} <= {'live', 'proxy', 'recorded'}
E         Extra items in the left set:
E         'synthetic'
```

### M8 — `_DECLARED_MODES` admits a mode that is neither a contract value nor the transport

```
E       AssertionError: bootstrap/settings.py accepts a configured mode that the contract's ProviderMode does not declare and that is not the proxy transport. A run's recorded provider_mode must be a contract value; `proxy` is exempt only because a proxied call is recorded as `live`.
E       assert {'proxy', 'stub'} == {'proxy'}
E         Extra items in the left set:
E         'stub'
```

### M10 — the catalog renames the code a SQLSTATE maps to

```
E       AssertionError: shared/db/schema.py maps a custom SQLSTATE to a code that is not in contracts/domain/v1/error-codes.json. The catalog's internal_mapping rule is that a code outside it is never emitted at the edge.
E       assert {'state_trans..._not_allowed'} <= {'analysis_fa...refused', ...}
E         Extra items in the left set:
E         'state_transition_not_allowed'
```

### W1 — the machine gains a terminal (frontend side)

```
AssertionError: expected [ 'cancelled', 'failed', …(2) ] to deeply equal [ 'archived', 'cancelled', …(3) ]
```

### W2 — the machine gains a **non**-terminal state `deferred`

Two cases red on one mutation: the non-terminal half, and the cross-check that the generated
enum is still the same machine the other two assertions are about.

```
AssertionError: expected [ Array(4) ] to deeply equal [ 'created', 'deferred', …(3) ]
AssertionError: expected [ 'cancelled', 'created', …(6) ] to deeply equal [ 'cancelled', 'created', …(7) ]
```

### W3 — a third code is filed under category `authorization`

This is the D-40 shape exactly, and it is the case the compile-time proof in
`authorization.ts` cannot see.

```
AssertionError: expected [ 'authentication_required', …(1) ] to deeply equal [ 'authentication_required', …(2) ]
```

### W4 — the catalog renames the category key

```
AssertionError: expected [ 'validation', 'not_found', …(8) ] to include 'authorization'
```

### W5 — `AUTHORIZATION_ERROR_CODES` drops `permission_denied`

```
AssertionError: expected [ 'authentication_required' ] to deeply equal [ 'authentication_required', …(1) ]
```

### W6 — `AUTHORIZATION_ERROR_CODES` stops narrowing and becomes the whole catalog

```
AssertionError: expected 22 to be less than 22
```

### W7 — the seam document declares a fifth namespace

```
AssertionError: expected [ Array(4) ] to deeply equal [ 'exports', 'findings', …(3) ]
```

### W8 — `queryKeys` gains an `exports` family and `QUERY_NAMESPACES` does not

```
AssertionError: expected [ 'exports', 'findings', …(3) ] to deeply equal [ Array(4) ]
```

---

## 3. The list that is wrong today — `SAFE_DETAIL_KEYS`

**Reported, not repaired**, per the brief: a case-4 list stops and checks back.

`src/auditmanager/storage/errors.py:35`. Its own comment states the derivation:

> The union of every `safe_detail_keys` entry the domain error-code catalog declares for the
> codes this package raises, plus the two byte-count keys the `storage_integrity_error`
> summary itself talks about.

Measured against the catalog and against the package's own classes:

```
SAFE_DETAIL_KEYS      = actual_sha256 actual_size blob_id constraint dependency
                        expected_sha256 expected_size field media_type role
catalog union         = actual_sha256 aggregate_type blob_id constraint dependency
                        expected_revision expected_sha256 field role
allowed_details union = actual_sha256 actual_size aggregate_type blob_id constraint
                        dependency expected_sha256 expected_size field media_type role

allowed_details NOT in SAFE_DETAIL_KEYS : ['aggregate_type']
SAFE_DETAIL_KEYS NOT in catalog+bytes   : ['media_type']
catalog+bytes NOT in SAFE_DETAIL_KEYS   : ['aggregate_type', 'expected_revision']
```

Three separate disagreements, and the first is the D-40 one:

1. **`aggregate_type` is missing while the package's own classes carry it.**
   `BlobAttributeConflictError.allowed_details` and `BlobNotFoundError.allowed_details` both
   declare it, and `BlobNotFoundError.__init__` **sets it by default on every instance**. The
   class docstring says subclasses declare "the subset of `SAFE_DETAIL_KEYS` they may carry",
   and two of them do not. The catalog licenses `aggregate_type` for three of the codes this
   package raises (`conflict`, `not_found`, `validation_failed`), so the list is narrower
   than both its authority and its own code.
2. **`media_type` is in the list and in no catalog entry for any code this package raises.**
   It belongs to the same exception class as the byte counts — `storage_integrity_error`'s
   summary names "checksum, byte size **or media type**" — so the comment's exception clause
   is under-stated by one, naming two keys where it means three.
3. **`expected_revision`** is in the catalog's union for `conflict` and no class uses it, so
   the stated union is wider than the list in a third, harmless direction.

**How bad is it.** Not a live leak. `src/auditmanager/ingest/failures.py:40` narrows details
to `code.safe_detail_keys` before building a `DomainError`, and `envelope.build` refuses an
undeclared key outright — so `media_type` and the byte counts are dropped at the mapping and
never reach an envelope. `failures.py`'s own docstring says as much.

**Which makes it the more interesting finding, not the less.** `SAFE_DETAIL_KEYS` has **no
functional consumer anywhere in `src/`** — it is exported from `storage/__init__.py`,
referenced in two docstrings, and read by nothing. It is a documentation constant that
disagrees with the code it documents and with the catalog it claims to derive from. It cannot
redden because nothing reads it; a reviewer checking "may this error carry `aggregate_type`?"
is told **no** by a constant that has been wrong since it was written.

**What I did not do.** I did not add the guard, because the guard is red on the current tree
and committing a red is not an option. I did not change the set, because the brief reserves
that. The comment block at the foot of the new Python guard file records why the guard is
absent and points here.

**The repair, when the owner rules.** One of:

- *If the constant is meant to bound the package's classes:* add `aggregate_type`, then guard
  `union(cls.allowed_details for every StorageError subclass) ⊆ SAFE_DETAIL_KEYS`.
- *If it is meant to be the catalog derivation:* replace the literal with the computed union
  plus the three summary keys, and guard it against the catalog.

They are different sets and the module claims both. That is the thing to decide, and it is a
one-line question for whoever owns `storage/`.

---

## 4. Where the brief was wrong

The brief said the integrator expected to be wrong about at least two of the ten starting
points. It is five, plus two framing premises.

| # | Starting point | Verdict |
|---|---|---|
| 1 | `authorization.ts:25` | **member** — but only half unproved; the `⊆`-catalog direction was already a compile-time proof. The unproved half was the *category* claim, which is the D-40 direction. |
| 2 | `query-keys.ts:25` | **not a member as briefed.** No contract defines a set of query-key namespaces — the closest contract set is OpenAPI's six `tags` (`projects, documents, runs, findings, decisions, export`), which is a **different set** from the four namespaces. Its authority is `web/docs/PC01_UI_SEAM.md` §6, a seam document. Same shape one level down, so I guarded it anyway. |
| 3 | `csv-columns.ts:19` | **not a member, and the follow-up question already had an answer.** The brief asks "whether anything proves it still matches `exports/serializer.py`'s `COLUMNS`". Yes: `tests/integration/exports/test_frozen_column_list.py:107` asserts `_web_columns() == tuple(COLUMNS)`, on top of both sides being pinned to `P02_SEAMS.md` §6. This is the best-defended list in the tree. |
| 4 | `retry.py:80` | **not a member — the narrowing is proved, structurally.** `RetryPolicy.__post_init__` reads `code.retryable` from the catalog and refuses to construct if any member is not catalog-retryable. That is a guard at the only place the set can be widened, which is stronger than a test. |
| 5 | `storage/errors.py:35` | **member, and case 4.** §3. The most valuable thing in the wave. |
| 6 | `findings/terminal.py:36,41` | **split verdict.** `TERMINALS_FROM_VALIDATING` (line 41) was already proved against the machine, including the `declared - X == {"cancelled"}` direction. `STAGE_STATUSES` (line 36) was **not** — and the reason it looks proved is §12's shape: `grep STAGE_STATUSES tests/` finds `test_contract_vocabulary.py:37`, which checks the **migration's** same-named tuple against the stage-result schema. Two constants, one name, and the query answered for the wrong one. |
| 7 | `carrier.py:319` | **member** — and the strongest one, with literally nothing referencing it. The "two sides of the wire" question is answered in §1.5. |
| 8 | `settings.py:52` | **member, and the brief's framing does not fit it.** `_DECLARED_MODES` is **wider** than `ProviderMode`, not narrower: `{live, recorded, proxy}` against `{live, recorded}`. The class is not "subsets"; it is "hand-maintained sets in a stated relationship to a contract set", and the relationship here is "plus exactly the transport". |
| 9 | `grounding.py:61` | **not a member.** Already derived — `frozenset(r.value for r in UngroundedReason)` — and the enum is pinned to the migration CHECK by `test_ungrounded_vocabulary_is_enforced.py` and `test_ungrounded_reason_vocabulary.py`. |
| 10 | `s3.py:77-79` | **not a member.** They mirror AWS's error vocabulary; no artifact in this repository defines them and no authority here can grow. Decided: outside the class, and I would not add a guard — a guard would pin them to a copy of themselves, which is §12's shape. |

### Two framing premises that did not survive measurement

**"The contract enum does not carry the terminal split."** `contracts/domain/v1/state-machines.json`
carries `machines.audit_run.terminal` explicitly. What does not carry it is the **generated
TypeScript enum**, which is a different artifact. The split was never unknowable; it was
unread. That distinction is what made the repair possible on both sides of the wire, and if
the premise had been taken literally the conclusion would have been "nothing can check this".

**`W26_W29_CLOSURE.md` §4: "Three instances, one shape."** The integrator's message asked me
to say so explicitly if my census contradicts it. It does. The three named instances are
**three different shapes**, and only one of them is the class this stream was sent to close:

- **`D-40`** — `PC01_ERROR_CODES` short by four while a screen rendered one of the missing
  codes. *This is the class:* a hand list that disagrees with its authority, with nothing that
  notices. `SAFE_DETAIL_KEYS` (§3) is its sibling.
- **`W29-SAY`** — **not a member of the class at all.** By the time W29-SAY was dispatched,
  `PC01_ERROR_CODES` had already been *derived* — the D-40 repair had landed, and the
  derivation was correct and is still green (verified this wave, 9/9). The defect W29-SAY
  avoided was not a stale list; it was a **consumer picking the wrong authority**:
  `terminal_reason` is constrained by the whole catalog and the session had been pointed at
  the envelope subset. A perfect guard on `PC01_ERROR_CODES` would not have caught it, because
  `PC01_ERROR_CODES` was not wrong. The failure mode is "the right set, read for the wrong
  question", and the defence is a different one — which is exactly what
  `terminal-reason.ts` built: `Record<ErrorCode, string>`, keyed on the *whole* catalog.
- **`D-18` / `W20-CODE`** — a hand-maintained **digest** (`web/FRONTEND_LOCK.json` records the
  contract's sha256 by hand), whose cost appears only at change time. Not a subset of a
  contract-defined set at all; a different class, about unbudgeted coupling.

The common thread across all three is real but it is one level up: **a second description of
something, maintained by hand, with no mechanism tying it to the first.** A subset is one
shape of that. A digest is another. A consumer that reads the wrong description is a third,
and it is the one no guard in this file can catch — the only defence against it is what
W29-SAY did, which is to measure before keying.

---

## 5. Is the class closed?

**For the class as the brief defines it — a hand-maintained set in a stated relationship to a
set a contract or catalog defines — yes, with one named exception.**

I can state: every hand-maintained collection found in `src/auditmanager/**` and `web/src/**`
that is a subset, partition, restatement or superset of a contract- or catalog-defined set is
now either derived from its authority, or carries a guard I have watched fail, **except
`SAFE_DETAIL_KEYS`**, which is wrong today, is owner-blocked by the brief's own rule, and is
recorded in §3 with both candidate repairs.

**What that statement does not cover, stated plainly rather than left implicit:**

1. **Authorities that are not contracts.** Several sets are pinned to a migration CHECK
   (`CALL_STATUSES`, `UNGROUNDED_REASONS`) or to a seam document (`CSV_COLUMNS`,
   `QUERY_NAMESPACES`). Those are proved, but the chain "contract → migration → constant" has
   links this wave did not audit end to end. A contract change that a migration never followed
   would leave all three green and all three wrong together.
2. **The sweep's reach.** The queries were
   `^\s*_?[A-Z][A-Z0-9_]{3,}\s*(:[^=]*)?=\s*(frozenset|set|tuple|\(|\[|\{)` over
   `src/auditmanager/**/*.py` (69 hits, all read, none truncated) and
   `^\s*(export )?const [A-Z][A-Z0-9_]{3,}\s*(:[^=]*)?=\s*(\[|new Set|\{)` over
   `web/src/**/*.{ts,tsx}` (36 hits, all read), plus a targeted pass for
   `Record<Enum, …>` and `satisfies`. **Both queries key on an upper-case name.** A
   hand-maintained set spelled as a lower-case local, built inside a function, or written as a
   `switch` with a `default` arm is invisible to them. The `switch`-with-`default` case is not
   hypothetical — `W15-AUTH` found five classifiers falling through to `server_error` — and it
   is the shape I would sweep for next.
3. **The Python half has no compile-time equivalent.** All nine backend guards are tests,
   which means they fail at test time, not at build time. That is the idiom of the side they
   live on; it is also strictly weaker than what `run-state.ts` gets for free.

**How I would find what is left.** Not another name-shaped grep. The productive query is the
inverse: enumerate the contract's own vocabularies — every `enum` in `openapi.json`, every
`machines.*.terminal`, every `categories` key, every `codes[*].safe_detail_keys` — and for
each one ask what in the tree consumes it and whether that consumer reads it or restates it.
That query starts from the authority, so it cannot share an assumption with the restatement,
which is the trap §12 exists for. It is also how `SAFE_DETAIL_KEYS` was found this wave: not
by grepping for a list, but by computing what the catalog licenses and comparing.

---

## 6. Rollback

Two files, both additive, both new. `git revert` of the two commits removes all eighteen
guards and nothing else; no production module was modified, so nothing depends on them.

If one guard proves too noisy to keep, the two most likely candidates and why:

- `test_pc01_stages_are_the_registrys_first_stages_in_its_order` asserts an **ordering**, not
  just membership. If a later wave legitimately reorders the registry while PC-01 keeps
  scheduling its four in the old order, this reddens correctly but inconveniently. It is one
  deletion and the two membership cases beside it survive.
- `the generated enum is the same machine` (web) reddens on a contract change *before* the
  client is regenerated, which is a real window during a reseal. That is arguably the point,
  but it is the one that will fire on a correct in-progress change.
