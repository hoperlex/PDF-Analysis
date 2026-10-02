# W48-FIX — Stage-A discovery false greens repaired

## 1. Result

Task `W48-FIX` is complete on core implementation commit
`78074f3644ed28bc7433629bd9a321a67b4e056f`. The three upheld `W48-JUDGE-A` findings assigned to
this slot are closed:

- `JA-01`: whole-surface statements no longer depend solely on a closed HTTP/API subject-synonym
  expression. A totality word plus an assertion verb identifies the structural claim even when
  both subject and counted noun are new.
- `JA-02`: live tracked text is default-allow. A new top-level live path or suffix enters from
  `git ls-files` without adding its parent to an include list; exclusions name non-live evidence,
  fixture, canonical-machine and immutable-migration roles.
- `JA-03`: independent pin discovery now reads Python, TypeScript and TSX tests. It sees literal
  symbolic frontend pins and the two already-present independent error-catalog length assertions,
  while comments, strings, templates, derived counts, HTTP statuses and fixture sizes remain out.

The focused suite is green at **67 passed**, up from the rejected Stage-A subject's 59. The full
hermetic gate is green with a literal final `GATE OK`.

No contract, migration, generated client, runtime behaviour, frontend behaviour, dependency,
composition root, global style, workflow, tag, deployment or remote ref changed.

## 2. Changed files

- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `tests/contract/api_v1/test_doc_prose_facts.py`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/W48-FIX.md`

## 3. Repair details

### 3.1 Tracked live prose is default-allow

The old scanner admitted exactly `src/auditmanager/api/`, `infra/deploy/`, `web/src/` and one
document. It now starts from every tracked path and excludes explicit roles:

- test/fixture/checkpoint evidence, which intentionally contains stale probes;
- contract/generated-contract machine artifacts, checked structurally elsewhere;
- documentation, checked by the live/history instrument, with maintained `P02_SEAMS.md`
  deliberately admitted;
- immutable migration source;
- the frontend machine lock.

That is a deny-by-role boundary, not another list of directories in which live code is allowed to
exist. `scripts/judge-surface.toml` and a future top-level operator/generator family are therefore
inside by default. The expanded current inventory has no binary, non-UTF-8 or unreadable entry in
its live role. True local counts newly exposed by this widening are path-qualified; an exception
for `three operations` in the access port cannot hide the same phrase in another file.

The explicitly past-tense pre-W15 statement in `web/.env.example` is registered by exact path and
phrase as historical evidence. It is not a global exemption.

### 3.2 New whole-surface wording is structural

An unknown counted noun still needs a value observed in the real contract/catalog history. It is
classified as a whole-surface statement by either the existing explicit surface grammar or by:

```text
<totality word> ... <assertion verb> <historical/current count> <new noun>
```

The second grammar does not list `HTTP`, `interface`, `endpoint`, `RPC`, `facade` or `facet`.
Consequently both the judge's exact sentence and a neighbouring independently invented sentence
are red:

```text
The complete HTTP interface exposes twelve endpoints.
The entire RPC facade exposes twelve facets.
```

The assertion verb is load-bearing. Bare non-surface facts such as `all 18 PASS` and `the full
run took ten minutes` do not become count claims merely because they use a totality word. This is
a conservative grammar, not a claim of natural-language understanding.

### 3.3 TypeScript pins join the registry inventory

The registry now has **27** entries rather than 25: the existing independent
`ERROR_CODE_VALUES` length assertions in the frontend contract test and failure-surface unit test
are explicit `error_catalog` pins. A small lexical pass masks TypeScript/TSX comments, quoted
strings and template bodies before matching executable candidates. It admits:

- literal symbolic assignments such as `const FROZEN_OPERATION_COUNT = 12`;
- the narrowly named generated error-catalog assertion
  `expect(ERROR_CODE_VALUES).toHaveLength(22)`.

It deliberately rejects `SCHEMA_COUNT = Object.keys(...).length` as derived rather than
independent. The two newly registered pins each have a mutation test that changes their needle in
memory and requires their exact `pin_id` to fail.

## 4. Mutation evidence

All filesystem mutations ran in a disposable shared clone at exact core SHA `78074f3` and were
removed before the green rerun.

| finding/control | mutation | result |
|---|---|---|
| `JA-02`, new path and suffix | stage `scripts/judge-surface.toml` containing `The API surface has twelve facets.` | exit `1`; `1 failed, 29 passed`; failure names the new path and `twelve facets` |
| `JA-01`, exact judge wording | same staged file changed to `The complete HTTP interface exposes twelve endpoints.` | exit `1`; `1 failed, 29 passed`; failure names `twelve endpoints` |
| `JA-01`, neighbouring vocabulary | in-memory `The entire RPC facade exposes twelve facets.` | focused guard red inside its committed mutation test |
| `JA-03`, unregistered TypeScript pin | stage `web/tests/contract/judge-independent-pin.contract.test.ts` with `const FROZEN_OPERATION_COUNT = 12` | exit `1`; registry reports that exact path outside `CONTRACT_PIN_REGISTRY.md` |
| TS comments/strings | put the same assignment in `//`, `/* */`, quoted and template text | committed lexical mutation test finds no candidates |
| two existing frontend pins | replace each registered needle independently in memory | two parametrised cases pass by observing the exact `pin_id` error |
| restored disposable clone | remove both staged files and rerun both focused modules | exit `0`; `67 passed` |

The staged source-path mutations are materially different from calling `_wrong_surface_claims`
directly: they prove the `git ls-files` inventory itself reaches the new tracked path.

## 5. Checks

```text
.venv/bin/python -m pytest \
  tests/contract/api_v1/test_surface_counts_in_prose.py \
  tests/contract/api_v1/test_doc_prose_facts.py -q
67 passed

git diff --check
exit 0

make gate                       # exact core SHA 78074f3, complete rerun
foundation: 35 passed
backend: 2663 passed, 5 skipped, 4 warnings, 169 subtests passed
frontend lint: passed
frontend typecheck: passed
frontend: 82 files, 1165 tests passed
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
```

The first `make gate` invocation completed foundation and the entire backend with the same backend
counts, then correctly refused before frontend because `web/node_modules` was absent in the linked
worktree. It did **not** print `GATE OK` and is not acceptance evidence. The locked
`web/node_modules` from the main checkout was then mounted read-only by symlink and the entire gate
was rerun from the beginning; only the second, complete result above is accepted.

The repository runtime does not contain a standalone Ruff module, so no separate Ruff claim is
made. The canonical gate's frontend lint/typecheck and Python collection/execution are the
recorded checks.

## 6. Contracts and forbidden-hotspot proof

Contracts remain API 17 paths / 20 operations / 61 schemas, error catalog 22, domain revision 8
and migration head `0013_norm_embeddings`. `git diff --name-only 53f41d4..HEAD` names only the
four files in section 2 after this report commit. In particular, no `contracts/**`, migration,
root dependency/lock, runtime source, frontend source, composition root, global style, workflow,
deployment configuration, judge report or owner ruling is touched.

## 7. Risks and known limitations

- The totality rule intentionally recognises a bounded grammar. It does not claim that arbitrary
  human prose is decidable; new semantic grammar requires a mutation, not a claim that this is NLP.
- The TypeScript lexer is deliberately limited to the candidate grammar it protects. It masks
  comments and string/template bodies but is not a general TypeScript parser; widening the pin
  grammar requires widening its lexical tests in the same change.
- `W48-AUDIT` `A-01` and `A-02` remain release-blocking. Both require a durable attempt/outbox or
  reconciliation design and likely migration ownership, which this task explicitly does not have.
  Therefore this repair can accept Stage A for continued development but cannot authorise
  `alpha-w48` release/tag closure.
- `A-03` remains an architecture-debt/owner decision; `A-04` is routed to `W48-WEB`; `A-05` is
  routed to governance/integration. None was silently claimed closed here.

## 8. Integrator handoff and rollback

Integrate the two local W48-FIX commits in order:

1. `78074f3644ed28bc7433629bd9a321a67b4e056f` — guard/registry repair;
2. the report-only commit containing this file.

Then rerun the two focused modules on the integrated SHA and accept Stage A only if its complete
`make gate` ends in literal `GATE OK`. Stage B may branch from that accepted local integration
SHA. Do not update `origin/dev` until `W48-INT-CLOSE`; do not update `origin/main` without a
separate direct owner instruction for the exact candidate.

Rollback is a revert of the repair and report commits. No feature flag, data rollback, host
operation or credential action applies.
