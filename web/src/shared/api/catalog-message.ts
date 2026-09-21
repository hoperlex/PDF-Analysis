/**
 * What each catalog code means, in Russian, for the place a screen would otherwise print
 * `error.envelope.message`.
 *
 * **Why this exists.** `R-18` requires the alpha to be shown in a finished interface, in
 * Russian. `W31-UI` translated every sentence `web/src` owns and then reported a wall: a
 * failure `detail` is frequently `error.envelope.message` — the API's own text, rendered
 * by the backend from the `summary` fields of `contracts/domain/v1/error-codes.json`.
 * Measured on `ae2adf5`: the catalog carries 22 codes and **not one Cyrillic character**.
 * So the client cannot translate that string; it can only decide to say the same thing
 * itself, which is what this module is.
 *
 * **1. It is keyed on the whole catalog, and the reason is what constrains the field.**
 * `transport.ts`'s `decodeFailure` constructs an `ApiError` exactly when `isErrorCode()`
 * passes, and `isErrorCode` tests membership of `ERROR_CODE_VALUES` — the whole 22-code
 * catalog. It does **not** test `PC01_ERROR_CODES`. Every classifier that consumes this
 * map has a `default:` arm that fires for any code it has no branch for, and six catalog
 * codes are outside `PC01_ERROR_CODES` — `unsupported_contract_version`,
 * `required_norm_unavailable`, `partial_result_not_publishable`, `cost_budget_exceeded`,
 * `stale_attempt`, `execution_token_invalid`. A map keyed on the narrower list would leave
 * those six rendering nothing, or rendering English. `W29-SAY` was told to key
 * `terminal-reason.ts` on `PC01_ERROR_CODES` and refused for the same reason, measured the
 * same way; this is that argument applied to a different field, not copied from it.
 *
 * **2. A restatement stays a restatement.** The catalog is the authority for what a code
 * means. Every sentence below says what that code's own `summary` says and adds no cause
 * the catalog does not name. A Russian sentence that invented a cause would be worse than
 * the English one it replaced. `web/tests/contract/catalog-message.contract.test.ts` is
 * the runtime half of that claim; the `Record` rather than `Partial<Record>` is the
 * compile-time half, so a reseal that adds a twenty-third code stops this file
 * type-checking.
 *
 * **3. What is lost, said out loud rather than discovered.** `ErrorEnvelope.message`
 * carries the catalog summary *unless a call site supplied its own* —
 * `shared/errors/envelope.py:126` is `screen_message(message) if message is not None else
 * code.summary`. The envelope does not record which of the two it is, so this client
 * **cannot tell them apart** and substituting here replaces both. Measured: 122 call sites
 * in `src/auditmanager/**` pass a custom `message`. What the substitution does **not**
 * lose is the discriminating fact, because every classifier renders
 * `classifiers(error.details, [...])` beside this sentence, and the catalog's safe
 * classifier keys are where `constraint`, `field`, `dependency`, `command_type` and
 * `aggregate_type` live. `tests/e2e/pc01/journey/manifest.json` depends on exactly that:
 * its `expects_rendered_from_envelope` entries are `not_encrypted`,
 * `every_page_has_extractable_text` and `page_count` — all three are `details.constraint`
 * values, none is a word of the English sentence. What **is** lost is the English prose of
 * a custom message, e.g. `ingest/envelope.py`'s *"This prototype never substitutes OCR for
 * a text layer."* `docs/program/W31-RUS.md` §4 prices making the backend say that in
 * Russian; it is a `src/` change and is not this stream's to make.
 *
 * **4. This is not `terminal-reason.ts` and must not become a copy of it.** That module
 * reads `RunStatus.terminal_reason` on a **200**, and its sentences are written in the
 * register of a run that has already stopped — *"прогон остановился"*. This module is
 * consumed by four classifiers — a run, an upload, a project creation and a listing — so
 * its sentences say what the code means without naming a run. The contract test asserts
 * the two tables share no sentence, so a later editor cannot quietly collapse them.
 *
 * No string here contains an apostrophe: `renderToStaticMarkup` escapes one to `&#x27;`,
 * and a test that un-escapes before comparing can be made to pass by changing the
 * un-escaping.
 */

import type { ErrorCode } from './generated/types.gen';

/**
 * One sentence per catalog code, each a restatement of that code's own `summary` in
 * `contracts/domain/v1/error-codes.json`, in the register of a refused request.
 *
 * Declared `Record`, never `Partial<Record>`, for the reason in the header.
 */
const CATALOG_MESSAGES: Readonly<Record<ErrorCode, string>> = {
  validation_failed:
    'Запрос или его содержимое нарушают объявленную схему, перечисление, формат или ' +
    'инвариант. Ничего не создано и не изменено.',
  not_found:
    'Адресованный объект не существует либо не виден вызывающей стороне. Ответ никогда ' +
    'не раскрывает существование того, что вызывающей стороне видеть не положено.',
  authentication_required:
    'Действительный аутентифицированный субъект предъявлен не был. Ответ не несёт ' +
    'никаких сведений об адресованном ресурсе.',
  permission_denied:
    'Аутентифицированному субъекту не разрешена эта операция над этим ресурсом. ' +
    'Авторизация решается на стороне сервера.',
  conflict:
    'Параллельная запись проиграла проверку оптимистичной блокировки, либо был бы ' +
    'нарушен инвариант уникальности. Эта причина используется только там, где не ' +
    'подходит более точный код конфликта.',
  state_transition_not_allowed:
    'Запрошенный переход не объявлен в state-machines.json для текущего состояния ' +
    'объекта. Это отказ по умолчанию для любого необъявленного перехода, включая ' +
    'попытку открыть заново завершённый объект, перезаписать опубликованную версию или ' +
    'удалить событие решения.',
  idempotency_key_reuse:
    'Ключ идемпотентности уже использовался с другим отпечатком содержимого. Ничего не ' +
    'создано и не изменено, дубликата объекта не появилось.',
  idempotency_key_in_progress:
    'Команда с тем же ключом и тем же отпечатком содержимого ещё выполняется. ' +
    'Вызывающая сторона повторяет тот же запрос и никогда не выдаёт команду заново под ' +
    'новым ключом.',
  idempotency_key_stale:
    'Запись команды для этого ключа больше недоступна, либо её исход не удалось ' +
    'установить, поэтому записанный исход нельзя воспроизвести. Запрос отказывает, а не ' +
    'выполняется повторно наугад.',
  unsupported_contract_version:
    'Объявленная версия контракта или схемы неизвестна этому поставщику. ' +
    'Снисходительного отката нет, приблизительной трактовки тоже.',
  storage_integrity_error:
    'Объявленная контрольная сумма, размер в байтах или тип содержимого не совпали с ' +
    'сохранёнными или переданными байтами, либо отсутствует обязательная роль ' +
    'манифеста. Артефакт не публикуется.',
  dependency_unavailable:
    'Требуемый адаптер — хранилище метаданных, хранилище объектов, провайдер модели или ' +
    'транспорт исполнителя — временно недоступен. Сообщение не фиксирует, о каком из ' +
    'них идёт речь. Операция ничего не создала, и её можно повторить.',
  dependency_credential_refused:
    'Требуемая зависимость отвергла собственные учётные данные приложения. Это ' +
    'серверная ошибка настройки, в которой не участвует ни один аутентифицированный ' +
    'субъект этого API: ничего не создано, и повтор не изменит исхода, пока оператор не ' +
    'починит учётные данные.',
  staged_upload_lost:
    'Хранилище объектов больше не содержит байты, подготовленные этой загрузкой, ' +
    'поэтому загрузку нельзя завершить. Ничего не опубликовано и не изменено; средство — ' +
    'отправить ту же загрузку заново.',
  required_norm_unavailable:
    'Авторитетный источник, от которого зависит работа, — снимок норм, набор промптов ' +
    'или профиль анализа — не удаётся разрешить в неизменяемую версионированную запись. ' +
    'Неверсионированный, частичный или замещающий источник вместо него не используется.',
  analysis_input_invalid:
    'Переданный пакет анализа или объявленный вход этапа неприемлем. Семантика ' +
    'конкретных полей этапа принадлежит контракту анализа; этот код — её внешне видимое ' +
    'отображение.',
  analysis_failed:
    'Выполнение анализа завершилось в терминальном состоянии отказа. Отказ записан на ' +
    'прогоне, и никакой частичный результат не публикуется как полный.',
  partial_result_not_publishable:
    'Адресованная работа завершилась как частичная, а запрошенная операция требует ' +
    'полной. Частичный исход и список недостающего остаются видимыми, а не ' +
    'дополняются и не ухудшаются молча.',
  cost_budget_exceeded:
    'Объявленный бюджет стоимости или токенов исчерпан. Выполнение останавливается ' +
    'явно, а не начинает молча ухудшать качество.',
  stale_attempt:
    'Отправившая попытка больше не является публикующей инстанцией для своей задачи: ' +
    'она замещена, потеряна, отменена или провалена. Переданный результат сохраняется ' +
    'как неизменяемое свидетельство и никогда не применяется к состоянию проекта.',
  execution_token_invalid:
    'Предъявленное полномочие на исполнение отсутствует, искажено либо не является ' +
    'текущим для этой задачи. Само значение токена никогда не возвращается в ответе.',
  internal_error:
    'Неклассифицированная серверная неисправность. Ответ всё равно несёт устойчивый код ' +
    'и идентификатор корреляции; ни внутренний путь, ни содержимое запроса, ни запрос к ' +
    'базе, ни стек не раскрываются.',
};

/**
 * How a sentence for a code this client does not know starts.
 *
 * Exported so the test asserts the real string rather than a copy of it. The runtime
 * cannot currently reach this arm — `transport.ts` narrows with `isErrorCode` before it
 * constructs an `ApiError` — but the generated client casts response bodies rather than
 * validating them, and a caller may hand this function a raw string from anywhere.
 */
export const UNDESCRIBED_MESSAGE_PREFIX =
  'Сервер сообщил код ошибки, описания для которого у этого клиента нет.';

/**
 * The Russian sentence for a catalog code, for the place a screen would print
 * `error.envelope.message`.
 *
 * The parameter is `string` and not `ErrorCode` deliberately: see
 * `UNDESCRIBED_MESSAGE_PREFIX`. Membership is read from the table itself and never from a
 * second copy of the catalog — an earlier draft of `terminal-reason.ts` tested
 * `ERROR_CODE_VALUES.has()` and then indexed its table, so a code in the enum and absent
 * from the table rendered an empty paragraph. That is the hole this kind of module exists
 * to close, reintroduced by the check meant to close it.
 */
export function catalogMessage(code: string): string {
  if (Object.prototype.hasOwnProperty.call(CATALOG_MESSAGES, code)) {
    return CATALOG_MESSAGES[code as ErrorCode];
  }
  return `${UNDESCRIBED_MESSAGE_PREFIX} Код выше — то слово, которое прислал сервер. Ничего не додумывается взамен.`;
}
