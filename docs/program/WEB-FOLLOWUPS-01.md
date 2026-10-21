# WEB-FOLLOWUPS-01 — upload edge refusals, one table of upload rule sentences (D-173), proposal decisions on a double press

**Base:** `origin/dev` `2affede8`. **Branch:** `agent/web-followups-01`, worktree `.local/worktrees/web-followups`.
**Scope:** `web/src/**`, `web/tests/**` and this file. Web only; no container, no stack, no push, no tag.
**Frozen and untouched:** `contracts/**`, `web/openapi/**`, `web/FRONTEND_LOCK.json`, `web/src/shared/api/generated/**` (contract 1.0.0).

## 1. An upload refused by the web server says so

A user on the deployed stand chose an 8.6 MiB bundle and read «Загрузка не дошла до API. HTTP 413: тело ответа не является конвертом ошибки по
контракту. Было ли что-нибудь опубликовано, неизвестно; повтор под тем же ключом безопасен.» The 413 came from the host's TLS terminator (nginx's
default 1 MiB), an HTML page and not an `ErrorEnvelope`. The sentence is produced in two places: `transport.ts` builds the operator's note
(`HTTP <status>: тело ответа не является конвертом…`, a `TransportError` carrying `status`), and `classifyUploadFailure` in
`web/src/entities/document-version/model/upload-failure.ts` appended the retry-safety sentence to every `TransportError`. The second half was false
for a 413: the file was refused before anything could be stored, and the same file is refused again.

`classifyUploadFailure` now reads `TransportError.status` (the transport is unchanged):

| status (non-envelope) | kind | title | detail |
| --- | --- | --- | --- |
| 413 | `edge_too_large` | Веб-сервер отклонил файл. | Сервер отклонил файл как слишком большой ещё до API (ограничение веб-сервера). Ничего не сохранено. Лимит продукта — `PC01_UPLOAD_ENVELOPE.maxBytesLabel`; обратитесь к администратору стенда. |
| 502 | `edge_unavailable` | Веб-сервер не получил ответа от API. | Веб-сервер не смог получить от API пригодный ответ (код 502). + retry-safety sentence |
| 503 | `edge_unavailable` | Веб-сервер не получил ответа от API. | Веб-сервер сообщил, что API сейчас недоступен (код 503). + retry-safety sentence |
| 504 | `edge_unavailable` | Веб-сервер не получил ответа от API. | Веб-сервер не дождался ответа API (код 504). + retry-safety sentence |

The 250 MiB is the existing constant, not typed again. The retry-safety sentence («Было ли что-нибудь опубликовано, неизвестно; повтор под тем же ключом
безопасен.») stays only where it is true: 502/503/504 (the request may have reached the API, and the form's key follows the chosen file, so «Загрузить»
again is the same command) and the generic transport state. Every other status, a network failure and an abort keep the old state unchanged. An
envelope 413 sent by the API itself is an `ApiError` and is untouched. `retryable` is still copied from the failure, never inferred from the status.

Tests (`web/tests/unit/projects/upload-failure.test.ts`, describe «a refusal from the web server in front of the API says so»): the 413 and the three
others, the absence of the operator's note and of the retry-safety sentence in a 413, three distinct wordings, every other transport failure unchanged,
an envelope 413 unchanged, and the chain `uploadDocument` over an HTML 413 page → `TransportError` → `edge_too_large`. The language guard
(`rendered-language.guard.test.ts`) now renders all four.

## 2. D-173: one table of upload rule sentences

`upload-envelope.ts` held 23 sentences; `upload-failure.ts` held six more (`non_empty`, `plain_base_name`, `blocks_count`, `pdf_page_content`,
`pdf_document_content`, `pdf_reader_limits`) because `W55B-FIX`'s grant did not reach the first file. The six moved into `UPLOAD_CONSTRAINT_SENTENCES`;
`uploadRuleSentence` and `UPLOAD_CONSTRAINTS_ADDED` are gone and the classifier calls `uploadConstraintSentence`. The sentences are byte-identical.

New test (`upload-envelope.test.ts`, describe «the upload rule sentences have one owner (D-173)») reads `web/src`, not the exports: every registered
constraint is keyed in exactly one file and it is the owner; no sentence literal occurs in a second file; the scan is shown to read the tree; and the one
exemption (`entities/price-list`, another operation whose `non_empty` is «Файл пуст.») is itself asserted to exist and to say something else. Existing
tests that imported the two removed names (`upload-envelope.test.ts`, `upload-failure.test.ts`, `rendered-language.guard.test.ts`) read the single table
instead; one assertion, «adds nothing the envelope already states», described the two-table design and was replaced by «states exactly the constraints the
contract registers».

**The journey manifest is not in `web/`.** `tests/e2e/pc01/journey/manifest.json` (a `_note` near line 489–490) still quotes «Блоки портала появятся после
первого запуска анализа этой версии.»; the widget's sentence is «Блоки портала появятся после первого запуска анализа этой версии, который дойдёт до разметки
страниц.» (`portal-blocks.tsx`, pinned by `blocks-tabs.test.ts` and `portal-states.test.ts`), and a version with no bundle reads «У этой версии нет комплекта
портала.». Not changed here; the integrator corrects that prose.

## 3. A double press of a proposal decision sends one request

`useDecideOptimisationProposal` (`web/src/features/decide-optimisation-proposal/model/`) now keeps the request in flight with the intent it belongs to
(proposal, verdict, comment — `decisionSignature`) and a second `mutationFn` call for the same intent returns the first's promise, the guard
`carry-over-decision` and `upload-price-list` carry since `2750cd11`. It is cleared when the request settles, success or refusal, so a later press is a
new command (decisions are appended on purpose) and a retry after a lost answer still carries the same key. Another verdict or comment is another intent
and is not joined. `commands.test.ts` has, for each of accept, reject and revise, «sends ONE request, and both presses get its answer», «opens the gate
again when the request settles» and «opens the gate after a refusal too, and the retry carries the same key», plus «does not join a request for another
intent».

## Evidence

Failing first, on `2affede8`'s source with the new tests in place (`npx vitest run` of the three files, exit `1`):
`Test Files 3 failed (3) · Tests 13 failed | 72 passed (85)`. Per task:

* 1 — `expected 'transport' to be 'edge_too_large'`; `expected 'HTTP 413: тело ответа не является кон…' not to contain 'тело ответа не является конвертом оши…'`
  (6 red: the 413 wording, the 413 without the operator's note, 502, 503, 504, and the `uploadDocument` chain).
* 2 — `keys every registered constraint in exactly one file…`: `AssertionError: expected [ …(6) ] to deeply equal []`, naming `blocks_count`, `non_empty`,
  `plain_base_name`, `pdf_page_content`, `pdf_document_content`, `pdf_reader_limits` in `upload-failure.ts` (re-run after scoping the exemption: 1 failed | 29 passed).
* 3 — `expected "spy" to be called 1 times, but got 2 times` (accept, reject, revise: 3) and `promise resolved "{}" instead of rejecting` (3).

Two mutations of the finished tree, each reddening the new test (`upload-envelope.test.ts`, exit `1`): a copy of the `pdf_reader_limits` sentence appended to
`upload-failure.ts` → «states every sentence once in all of web/src»; `blocks_count: 'x'` keyed in `upload-outcome.tsx` → «keys every registered constraint in
exactly one file». Both reverted (`cmp` identical).

Green, on the committed tip (`npm --prefix web ci` only; no container):

* the three touched files: 86 passed;
* `npm --prefix web run lint -- --quiet`: exit `0`; `npm --prefix web run typecheck`: exit `0`;
* `tests/guards`, `tests/unit/optimisation-proposals`, `tests/unit/projects`, `tests/unit/upload`, `tests/unit/optimisation`: 38 files, 510 tests passed;
* `npm --prefix web test -- --run`, full: **164 files, 2438 tests passed** (2414 before + 24 new), 2 min 20 s.

## Not done, and why

* `start-optimisation-pass` (a double press sends two `201`s and one pass), `assign-work`, `my-tasks-complete-the-work` and
  `norms-designate-the-current-snapshot` have the same benign duplicate (`BETA-LIVE-JOURNEY-01`); the brief named only the proposal decisions.
* The price-list upload has its own failure mapping and still shows a non-envelope 413 in the operator's wording; the 413 the user met was on the document upload.
* The host's TLS terminator limit itself (nginx default 1 MiB) is an operator setting, not a web change; the screen now tells the user to ask the administrator.
* Disk was 2.0–2.7 GB free on `/` when this lane ran, under the 3.5 GB the dispatch asked for; `web/node_modules` (576 MB) was installed from the warm npm cache
  and is deleted at the end.
