# Task ALPHA-MANUAL-01 — воспроизводимая ручная приёмка открытой альфы

## Outcome

Оператор одной командой проверяет доступность публичного origin и целостность безопасного
синтетического PDF-набора, затем проходит зафиксированный UI-сценарий и получает локальный
отчёт `PASS / FAIL / BLOCKED` без передачи логина, пароля или токена скрипту.

## Depends on

- `W47-INT-CLOSE`
- `NORM-INT-01`

## Frozen inputs

- domain contract: revision 8, 27 opaque identities;
- API contract: 17 paths / 20 operations / 61 schemas, SHA-256
  `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`;
- analysis/comparison/event contract: PC-01 manifest and synthetic AR oracle at base commit;
- migration head: `0013_norm_embeddings`;
- base commit: `4d9b9576d07c280562996596a9d553cc0136ecdc` (`origin/main` at task start);
- fixture contract: `fixtures/synthetic/ar/SHA256SUMS`.

## Allowed paths

- `scripts/manual-alpha-check.sh`
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- `artifacts/manual-alpha/**`
- `docs/program/tasks/ALPHA-MANUAL-01.md`
- `docs/program/ALPHA-MANUAL-01.md`

## Forbidden hotspots

- `contracts/**`;
- `migrations/**` and migration head;
- root dependency and lock files;
- API/application composition roots;
- `web/src/app/globals.css` and all product UI/runtime code;
- deploy composition, secrets, Git refs and the external stand.

## Non-goals

- no deploy, push, tag or external write performed by this task;
- no real/customer PDF and no credential in repository, arguments or evidence;
- no replacement for `make gate`, the PC-01 browser journey or deployment verification;
- no claim that the temporary hostname or a deployed SHA will remain current;
- no automated expert verdict over model output.

## Deliverables

- executable preflight and interactive recorder `scripts/manual-alpha-check.sh`;
- operator runbook `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`;
- synthetic PDF bundle, manifest and checksums under `artifacts/manual-alpha/`;
- completion report `docs/program/ALPHA-MANUAL-01.md`.

## Required tests

- `bash -n scripts/manual-alpha-check.sh` — exit 0;
- `scripts/manual-alpha-check.sh --files-only` — `FILES OK`, exit 0;
- `scripts/manual-alpha-check.sh --origin https://audit.135.106.164.147.sslip.io/ --preflight-only`
  — `PREFLIGHT OK`, exit 0 while that temporary stand is reachable;
- `sha256sum -c artifacts/manual-alpha/SHA256SUMS` — all five canonical PDF files `OK`;
- extract `artifacts/manual-alpha/alpha-test-pdfs.tar.gz` into a temporary directory and
  compare all five digests — all `OK`;
- focused documentation/prose guards — green;
- `git diff --check` — empty output.

## Integration contract

The integrator may rely on the script making only unauthenticated `GET` requests during
preflight. Interactive mode records operator-entered outcomes under `.local/manual-alpha/` and
does not receive or persist credentials. The canonical PDFs remain the files under
`fixtures/synthetic/ar/`; the archive is a convenience copy verified against those digests.
The acceptance verdict is `PASS` only when every mandatory manual checkpoint passes.

## Failure/idempotency/security cases

- a non-HTTPS remote origin is refused; HTTP is allowed only for loopback development;
- a checksum/size mismatch, unexpected redirect, unavailable login page or API that is readable
  without a session fails preflight;
- `BLOCKED` is not converted into a pass;
- repeated execution creates a new timestamped evidence report and never overwrites an old one;
- credentials stay in the browser/password manager and never enter the command line or report;
- refusal checks assert both the rule-specific reason and absence of a created document.

## Rollback / feature flag

Not applicable: this task changes documentation, a read-only/operator script and synthetic test
packaging only. Removing those files restores the previous tree; no runtime flag or data rollback
exists.

## Handoff

- changed files: filled by `docs/program/ALPHA-MANUAL-01.md`;
- commands/results: filled after validation;
- known limits: browser actions remain deliberately manual; live-provider quality is
  nondeterministic within the frozen PC-01 threshold;
- integration notes: do not push this task to `origin/main` outside an explicitly assigned
  integration slot and `docs/program/MAIN_AUTODEPLOY_POLICY.md`.
