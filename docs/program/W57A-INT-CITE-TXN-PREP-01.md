# W57A-INT-CITE-TXN-PREP-01 — unserved citation transaction adapter

**Base:** exact published dev32
`5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`.
**Status:** isolated source candidate, no service, provider, remote or stand
operation.

## Result

`findings/citation_publication.py` writes one normative finding, its immutable
observation, project evidence, 1–5 norm citations and canonical observation
link through one caller-owned SQLAlchemy transaction. It allocates fresh
finding and observation identities. The adapter commits nothing and returns
only allocated identities and the citation count. Migration 0023 verifies
the count, pinned Run, paragraph identity, reliable text and raw substring
at the outer commit; the caller must roll back on any exception.

Before the first write, the adapter locks the current Run, Job and Attempt
and checks the execution token, validating/running states, current Attempt,
completed matching text-analysis model-call effect and succeeded CITE stage
created no earlier than that Attempt. It requires the Run-pinned verified set,
available set Blob under confirmed custody, and exact SHA-256 and size of
the supplied retrieval-set bytes. It then checks that every citation's N
label, target document, rebound state and raw span belong to that set's
selected and full reliable paragraph rows. A corrupted or stale input is
refused before any INSERT.

The adapter uses a local DTO, so `findings` does not deep-import the AR v3
profile. A later caller maps the pure v3 gate result into this DTO only after
binding the model response and PDF evidence to the recorded call and reading
the exact set Blob through the custody-aware port. No route or executor calls
this adapter yet.

## Evidence

- Focused citation writer, existing v3 pure grounding, norm grounding and
  ALR-05 boundaries: **36 passed**.
- Programme governance suite: **16 passed**. Python compilation,
  `git diff --check`, and direct task governance: **passed**; governance
  findings `[]`.
- API/stage/domain/error/0023 frozen SHA-256 values match the task. No
  PostgreSQL, S3, Docker, paid call or full gate was started during W55b.
- Offline probes show no write on stale Attempt, foreign call Attempt,
  rejected set, failed CITE, wrong token, failed call, mismatched call/effect
  request digest, modified set bytes,
  foreign prompt label or incorrect raw span. The accepted synthetic case
  records one certified count and one exact raw citation row.

## Limits and integration

This is **not** real database acceptance. SQL locking, PostgreSQL constraints
and deferred commit must be exercised in an isolated DB lane after the W55b
gate. No qualified W54 set exists yet for a real corpus run. The caller still
must prove that the candidate came from the recorded model response and pure
PDF/norm gates; this adapter checks persisted call authority and set/quote
membership but cannot infer that provenance from a Python DTO. It writes
accepted normative findings only: withheld diagnostics, nonnormative certified
zero and the verified report reader remain separate CITE tasks. Repeated calls
require the later final Run/Attempt publication gate to prevent duplicates.

Changed paths: this report, its formal task, the new adapter and its offline
test. No `contracts/**`, migration, root dependency/lock, composition root,
analysis public facade, API route, v1/v2 publisher, UI/global style,
`CURRENT_STATE.md`, remote ref or tag changed. The integrator may cherry-pick
the exact source commit after dev32 and keep the adapter unserved. Rollback is
that bounded commit; no feature flag is needed before activation.
