# ALPHA-MANUAL-01 — completion report

> Forward addendum: `W52-ACCEPT-01` adds an independently measured API build
> comparison to the automated pack. Its report carries the new checks; this
> historical W48 completion evidence remains as recorded.

## Result

**DONE.** Открытая альфа получила воспроизводимый операторский пакет: безопасный preflight,
интерактивный протокол A01–A12, точные ожидания UI/API и переносимый набор из пяти синтетических
PDF. На временном origin preflight прошёл; сам ручной пользовательский прогон не объявляется
выполненным — для него нужны разрешённая reviewer account и осознанные записи/модельные вызовы.

## Changed files

- `scripts/manual-alpha-check.sh` — read-only preflight и recorder `PASS / FAIL / BLOCKED`;
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` — полный ручной сценарий;
- `artifacts/manual-alpha/README.md` — состав и правила использования пакета;
- `artifacts/manual-alpha/SHA256SUMS` — SHA-256 пяти канонических PDF;
- `artifacts/manual-alpha/alpha-test-pdfs.tar.gz` — переносимый архив, 233 480 bytes,
  SHA-256 `a74038a5feac13116eba152a5238c061fa90b775743927985d71200edbfedb32`;
- `docs/program/tasks/ALPHA-MANUAL-01.md` — task contract;
- `docs/program/ALPHA-MANUAL-01.md` — этот отчёт.

## Checks performed

- `bash -n scripts/manual-alpha-check.sh` — PASS;
- `shellcheck scripts/manual-alpha-check.sh` — PASS, no findings;
- `./scripts/manual-alpha-check.sh --files-only` — `FILES OK`, all five PDF SHA/size/magic
  checks pass;
- `./scripts/manual-alpha-check.sh --origin https://audit.135.106.164.147.sslip.io/ --preflight-only`
  — `PREFLIGHT OK`: root `307 -> /projects`, login `200`, unauthenticated OpenAPI `401`;
- `sha256sum -c artifacts/manual-alpha/SHA256SUMS` — five `OK`;
- archive extracted into an empty temporary directory and checked by the same manifest — five
  `OK`; archive SHA matches the value above;
- `.venv/bin/pytest -q tests/contract/fixtures_ar tests/e2e/test_pc01_journey_conformance.py
  tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py` — **165 passed, 22 subtests passed**;
- `git diff --check` — PASS after final edits.

## Contracts

No API, domain, event, migration or UI contract changed. The operator package consumes the
existing 17-path / 20-operation / 61-schema API, migration head `0013_norm_embeddings`, PC-01
journey manifest and canonical synthetic fixture checksums. No new credential surface exists.

## Risks and known limitations

- The A01–A12 browser run remains to be executed by an authorised reviewer. A green preflight is
  availability/auth-boundary evidence, not product acceptance.
- The live model is nondeterministic. The frozen acceptance threshold is at least two of three
  seeded issues, exact grounded quotations and zero hits on six negative controls; this is not a
  quality claim for real documents.
- The hostname is temporary and deliberately supplied by `--origin`; no permanent deployment
  claim is encoded in the script.
- Deployment SHA cannot be learned honestly from an unauthenticated product page. A01 therefore
  requires workflow evidence plus `infra/deploy/verify-deployed.sh` from the deployment owner.
- The package does not cover backup/restore, load, tenant isolation, hostile security testing or
  OCR.

## Integrator instruction

1. Review this package independently and run the command from the runbook with the actual origin.
2. Execute A01–A12 with a non-default reviewer credential; keep the resulting report under the
   ignored `.local/manual-alpha/` and scrub it before sharing.
3. Treat `FAIL` and unexplained `BLOCKED` as release blockers; never convert them to a pass.
4. Before any publication to `origin/main`, run the complete `make gate` and follow
   `docs/program/MAIN_AUTODEPLOY_POLICY.md`; this task neither authorises nor performs a push.

## Forbidden-hotspot proof

Task-owned changes are limited to the seven paths listed above. They do not touch `contracts/**`,
`migrations/**`, root dependency/lock files, composition roots, deploy configuration, product UI,
global styles, tags or refs. The working tree also contains the pre-existing
`MAIN-AUTODEPLOY-01`/`AGENTS.md` documentation changes from the prior task; they are not changes of
`ALPHA-MANUAL-01` and were preserved.
