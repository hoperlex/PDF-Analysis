# W27-WEB — the screen's code list stops being narrower than the surface, and stops being a literal

> **Opened before the first edit**, as the dispatch requires. Every figure below carries the
> command that produced it, run in this worktree.

`D-40` and `D-41`. Neither is a bug a user can see. Both are a **claim that stopped being
true with nothing reading it** — the same shape `W15-AUTH` found in this exact list in wave
15, corrected by hand, and left unguarded. The repair is therefore not four more entries: it
is a derivation and a widened tree, so the next divergence reddens instead of being found by
the session after next.

**Where the work was done.** Worktree `/root/w27web`, branch `agent/w27-web` from
`origin/dev` at `5b3a040`. Gate lane `gate-w27a`: `POSTGRES_PORT=56000`,
`S3_API_PORT=59600`, `S3_CONSOLE_PORT=59601`, `POSTGRES_DB=audit_w27a`, bucket
`auditmanager-gate-w27a`. **No image was built and `31500` was not touched.**

---

## 1. `D-40` — the list was short by four, not by one

### 1.1 Derived, and what the contract will not give

The dispatch asks for the set to come from the contract rather than from a literal. It
**can**, and it now does — but only through a rule that has to be stated, because the
document does not contain the mapping in the form the question assumes.

**`contracts/api/v1/openapi.json` pins a *status* per response, never a code per
operation.** All fifteen operations declare `401`, `403`, `500`, `503`; twelve declare
`404`, five `409`, eleven `422`. Deriving the subset from statuses alone gives **21 of the
22 catalog codes** — everything except `unsupported_contract_version`, whose `400` no
operation declares:

```
$ python3 - <<'EOF'   # statuses -> catalog codes at that status
...
21 ['analysis_failed', 'analysis_input_invalid', 'authentication_required', ...]
EOF
```

A subset that is 21/22 is not a subset; `409` alone carries eight codes, of which this
surface emits four. The only place the document says **which** of the codes at a status a
given response carries is that response component's own description, in backticks.

So the derivation, which is what `web/tests/contract/pc01-error-codes.contract.test.ts`
implements:

> for every non-2xx response an operation declares → the `components/responses` entry it
> `$ref`s → the catalog codes that entry's description names in backticks, plus the code
> whose name the entry itself is (`NotFound` → `not_found`) → keep those the catalog
> assigns to the status it was declared at.

Both halves are load-bearing and both are asserted to be:

* **the backtick scan**, because `UploadRejected`, `RunInputInvalid` and
  `IdempotencyConflict` are not named after a code and yield nothing without it;
* **the name match**, because `NotFound`, `ValidationFailed` and `StorageIntegrityError`
  name no code in their description at all;
* **the status filter**, because descriptions carry *cross references* —
  `PermissionDenied` names `dependency_credential_refused` in order to say the code is
  **not** this response, and `DependencyUnavailable` names `idempotency_key_in_progress`,
  a `409`, to say a caller reads `retryable` from the envelope. Without the filter both
  become false members.

### 1.2 What it derives, and the four the list was missing

Fifteen codes, against a hand-kept list of twelve:

| | |
|---|---|
| **derived and listed** | `validation_failed`, `not_found`, `authentication_required`, `permission_denied`, `conflict`, `state_transition_not_allowed`, `idempotency_key_reuse`, `idempotency_key_in_progress`, `idempotency_key_stale`, `dependency_unavailable`, `internal_error` |
| **derived and *not* listed** | `storage_integrity_error`, `analysis_input_invalid`, `staged_upload_lost`, `dependency_credential_refused` |
| **listed and not derivable** | `analysis_failed` |

**`D-40` names one missing code. There were four.** And two of them are not theoretical:

* `storage_integrity_error` — `upload-failure.ts:98` has rendered it with **its own
  sentence and its own classifiers** since `W12-WEB`, and `failure-surface.test.ts` asserted
  `isPc01ErrorCode('storage_integrity_error')` is **`false`**. A test was pinning the
  list's falsehood.
* `analysis_input_invalid` — `run-failure.ts:88`, a dedicated `unsupported` presentation,
  and the module's own docstring explains why it must not collapse into `validation_failed`.

So the list was not one reseal behind. It never described the screens it claimed to
describe, and the guard that would have said so did not exist.

`analysis_failed` is the one entry the derivation cannot see: `InternalError`'s description
names it in words — *"a declared run failure"* — and not as a code. It is registered in
`BLIND_SPOTS` **with that reason**, and a further test requires every registered blind spot
to still be a catalog code, still be listed, and still be invisible to the derivation, so a
register entry that outlived its reason reddens too. Correcting the description is a
`contracts/**` edit and outside this grant.

### 1.3 Behaviour: none, and that is the whole finding

`isPc01ErrorCode` and `PC01_ERROR_CODES` are exported and **read by nothing under
`web/src`** outside the module that defines them:

```
$ grep -rn "PC01_ERROR_CODES\|isPc01ErrorCode" web/src --include=*.ts --include=*.tsx
web/src/shared/api/errors.ts    (definition)
web/src/shared/api/index.ts     (re-export)
```

Every screen branches on the code itself, in the four classifiers, each of which ends in an
explicit `default` state that carries the envelope's own message. **Widening the list
changes nothing a user sees**, and no new branch was added: which of these codes deserves a
sentence of its own is what `W27-REFUSE` is measuring this wave, and inventing copy ahead of
that measurement is the non-goal the dispatch names. The repair is **structural**, and the
module now says so — membership is not a claim that a screen has bespoke wording.

The one change visible to a caller is the predicate: `isPc01ErrorCode` now answers `true`
for the four added codes. The test that asserted the opposite for `storage_integrity_error`
is corrected and says why.

---

## 2. `D-41` — two stale comments, and the tree that could not read them

`errors.ts:4` *"twenty-code catalog"* (stale since `R-3`) and `errors.ts:25` *"the full
twenty-one-code catalog"* (falsified by `W25-SEAL`) are corrected. But the row's own point
is the guard, and widening it found **two more of the same class plus one it still cannot
read**:

| where | said | truth |
|---|---|---|
| `errors.ts:4` | twenty-code catalog | **22** — `D-41` |
| `errors.ts:25` | twenty-one-code catalog | **22** — `D-41` |
| `errors.ts:33` | `R-3` put a credential in front of all **twelve operations** | **15** — *new* |
| `authorization.ts:24` | as the **twelve operations** can return it | **15** — *new* |
| `server-env.ts:96` | one refusal into **twelve confusing ones** | **15** — *new, and unreadable* |

The last one is the interesting one. `W22-WEB` learned that a claim the pattern cannot see
is a claim nobody is checking; this is the next layer of that. *"turn one clear refusal into
twelve confusing ones"* is a count of operations wearing the noun **"ones"**, and no
reasonable surface-noun list will ever contain it. Teaching the guard to read it would make
it redden on ordinary prose. It is corrected by **removing the number** — *"into a confusing
one per operation"* — which is the only durable repair for a sentence whose figure is a
restatement of the surface. Named here so the next session knows the class exists and that
the guard does not cover it.

### 2.1 The widening, and the two pattern gaps it exposed

`SCANNED_TREES` goes from `web/src/app/bff` to **the whole of `web/src`**. `W22-WEB` called
the BFF route *"the only place in `web/` that makes such a claim"*; that was false when it
was written — `errors.ts` carried two.

**`web/tests` is deliberately not scanned**, for the same reason this guard's own file is
not: a suite that proves a guard can fail has to write the stale spelling down on purpose.
`failure-surface.test.ts` and three others hold such spellings today.

Widening alone would have been wrong, exactly as `D-32` records. Two gaps, both found by
running it and neither by reading it:

1. **`PC-01`, `R-13`, `UTF-16`.** `\b` put the pattern's cursor *inside* a hyphenated
   identifier. *"the fifteen PC-01 operations"* was read as **"01 operations"** — one
   operation — and reddened against a surface of fifteen; `quotation.ts`'s *"counts UTF-16
   code units"* was read as sixteen codes. Fixed with a `(?<![\w-])` lookbehind.
2. **`code units` and `code points`** are units of text, not entries in a catalog. Fixed
   with a lookahead on the noun.

Both are **structural, not registered phrases**. A `LOCAL_COUNTS` entry would have
suppressed the exact numbers seen and let the next identifier through, which is the literal
this guard is a row about.

---

## 3. Mutations, each run rather than reasoned about

Every mutation was applied to a **committed** tree and reverted with
`git checkout HEAD -- <path>`; the guard was re-run green after each revert.

| # | mutation | what died |
|---|---|---|
| **M1** | restore the pre-repair prose in `web/src` (`git checkout 5b3a040 -- web/src/shared/…`) | `test_the_api_prose_states_the_surface_this_document_declares`, naming **all four** readable stale claims: `authorization.ts` twelve operations, `errors.ts` twenty-code, twenty-one-code and twelve operations |
| **M2** | `SCANNED_TREES` back to `web/src/app/bff` | `test_the_guard_reaches_the_shared_api_client` |
| **M3** | drop the `(?<![\w-])` lookbehind | `test_a_number_inside_a_hyphenated_token_is_not_a_count` **and** the main guard, which reported `errors.ts: '01 operations' states 1 operations` |
| **M4** | drop the `(?![ -](?:unit\|point)s?\b)` lookahead | `test_code_units_and_code_points_are_not_catalog_codes` |
| **M5** | remove `staged_upload_lost` from `PC01_ERROR_CODES` — **`D-40` itself** | the derivation guard's *never narrower* test, naming the code |
| **M6** | add `cost_budget_exceeded` to the list | the *never wider* test |
| **M7** | drop the backtick scan from the derivation | the anti-vacuity test, naming the components that empty |
| **M8** | drop the status filter from the derivation | the cross-reference test |
| **M9** | drop `analysis_failed` from `BLIND_SPOTS` | the *never wider* test |

---

## 4. The gate

*(filled below, after the run)*

---

## 5. Files changed

*(filled below)*
