# Task W49-PLAN-01 — поставить в очередь проверенное продвижение нормативного корпуса

## Outcome

Следующая после `alpha-w48` волна имеет один исполнимый master-plan: от owner-решений по
хранилищу и identity до подтверждённых custody bindings, 121-страничного repair ledger,
транзакционно загруженного repaired snapshot и полного embedding build. Публичный поиск,
цитирование и использование snapshot в аудиторском прогоне не выдаются за готовые раньше
этого data-plane.

## Depends on

- `W48-PLAN-01` — завершённый план непосредственно предшествующей волны;
- `NORM-INT-01` — приняты persistence, identity и ledger seams;
- `NORM-CUSTODY-01` — принят custody/outbox handoff;
- `NORM-VECTOR-01` — принят pgvector persistence profile;
- `NORM-ADR-01` — принята alpha topology без внешней vector DB.

## Frozen inputs

- planning base: `deda5337565e67e09a881d3f03d5673966fcfb2a`;
- last tagged release: `alpha-w47`; W49 starts only from the future accepted `alpha-w48`;
- API: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`;
- domain: `1.0.0-draft.1`, candidate revision 8, 27 identities;
- error catalog: 22 codes;
- migration head: `0013_norm_embeddings`;
- base corpus projection: 674 documents / 348,777 canonical paragraphs / 55,702 chunks,
  content key `2026-07-23..2026-08-20+17d.4b74348debf7`;
- frozen embedding profile: `bge-m3-dense-v1`; the base projection yields 62,325 windows;
- normative decisions: `NORM-Q01` through `NORM-Q09`, ADR-0020, `R-34` and `R-35`;
- custody input inventory: 674 source PDFs and 28,246 crop objects;
- repair scope: 121 pages/blocks in 54 documents, with the `R-29` USD 5 ceiling.

The projection and window counts above describe the **unrepaired input**. They are not W49
output acceptance numbers.

## Allowed paths

- `docs/program/tasks/W49-PLAN-01.md`;
- `docs/program/dispatch/W49-PLAN.md`;
- `docs/program/dispatch/W49-JUDGES.md`;
- `docs/program/W49-PLAN-01.md`;
- `docs/program/CURRENT_STATE.md` — one queued-wave orientation paragraph only;
- `docs/program/dispatch/W48-PLAN.md` — successor paragraph only.

## Forbidden hotspots

- `contracts/**`, generated consumers and error catalog;
- `db/migrations/**` and migration head;
- root dependencies/locks, `Makefile`, composition roots and global styles;
- runtime, storage, corpus source, UI, deployment and workflow implementation;
- `docs/program/DEBT_REGISTER.md`, owner rulings, Git refs, tags and alpha state.

## Non-goals

- no W49 implementation or external mutation in this planning task;
- no claim that `W48-INT-CLOSE`, D-70, D-119 or the blob-identity conflict is closed;
- no search/citation API, UI, hybrid retrieval, reranker or run-snapshot behaviour;
- no public corpus-backed release while `NORM-Q04` says internal-use only;
- no dispatch from the planning checkout.

## Deliverables

- `W49-PLAN.md` with owner gates, stage graph, exclusive ownership, measurable gates,
  production sequence and rollback policy;
- `W49-JUDGES.md` with identity/crash-boundary, operational and data-integrity attacks;
- a completion report at `docs/program/W49-PLAN-01.md`;
- explicit successor boundary: W49 builds the data-plane; W50 may contract retrieval only after
  W49 evidence is accepted.

## Required tests

- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — green;
- every decision/debt needed for custody, repair, promotion and embedding is mapped to an owner,
  gate or explicit non-goal;
- every mutable hotspot has exactly one W49 owner and parallel lanes have disjoint writes;
- `git diff --check` — empty output.

## Integration contract

This plan authorizes only `W49-FREEZE-01` after `W48-INT-CLOSE` has produced and verified
`alpha-w48`. Freeze must create individual task files with exact paths and a measured base SHA.
`W49-DECIDE-01` must then resolve D-119 and the incompatible Blob identity statements before a
contract, migration or custody implementation task is dispatchable.

## Failure/idempotency/security cases

- missing `alpha-w48`, a dirty tree or unequal accepted refs blocks freeze;
- equal bytes must not be silently treated as both independently admitted and content-deduped;
- provider absence, cost-ceiling exhaustion or any unresolved one of the 121 repairs stops
  promotion without invalidating confirmed custody;
- no corpus text, provider response, object key, secret or model cache enters Git evidence;
- no partial snapshot/build/binding is made visible after a crash or retry.

## Rollback / feature flag

Documentation-only. Revert the six allowed documentation edits if the owner changes the wave
boundary. The implementation plan itself requires forward recovery and retained data after
promotion; it does not authorize deletion or TTL.

## Handoff

- changed files and checks are recorded in `docs/program/W49-PLAN-01.md`;
- the next W49 task is `W49-FREEZE-01`, but only after `alpha-w48` exists;
- the first implementation predecessor is `W49-DECIDE-01`, not a custody or provider run;
- forbidden hotspots remain byte-untouched by this planning task.
