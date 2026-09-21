/**
 * What a `failed` run terminated for, as a sentence instead of a bare identifier.
 *
 * `W28-LIVE` drove a failed run through a browser and found the screen honest and
 * otherwise well built, with one hole: the outcome block reads
 *
 *   > The run terminated `failed`. Nothing was published.
 *   > Terminal reason: `dependency_unavailable`
 *
 * — an identifier on a screen where every neighbouring line is a sentence. This module
 * is the sentence, and the rules it is written under are narrower than they look.
 *
 * **1. A sentence here restates the catalog, it does not diagnose the run.** Every string
 * below is derived from the `summary` its code carries in
 * `contracts/domain/v1/error-codes.json`, the frozen catalog the database CHECK-constrains
 * `audit_run.terminal_reason` against. Nothing here reads a stage, a provider mode or a
 * document, because the reading does not carry the facts that would license it.
 *
 * **2. The load-bearing case is `dependency_unavailable`, and the point of its sentence is
 * what it refuses to say.** The catalog's dependency class covers the metadata store, blob
 * storage, a model provider *and* the worker transport, and `RunStatus` carries no
 * `details`, so the reading never says which one. `W28-LIVE` measured the case that makes
 * this matter: in `recorded` mode a document with no recording fails with this code while
 * the provider is perfectly healthy. A sentence reading "the provider is down" would be
 * the `W27-REFUSE` defect — nginx's `413` rendered as "The upload did not reach the API",
 * true of the transport and wrong about the cause. So the sentence names the class, says
 * out loud that the run does not record which member of it, and stops.
 *
 * **3. Retryability is a permission, never a prediction.** The catalog marks
 * `dependency_unavailable` retryable. `W28-LIVE` measured three of three `recorded`-mode
 * runs failing with it, where no number of retries can succeed, because the missing thing
 * is a local file. "You may start the run again" is true; "a second run will get further"
 * is not something this screen knows.
 *
 * **4. The code is kept, not replaced.** The sentence is added beside the identifier. An
 * operator quoting a code into a search or an issue needs the code; a person reading a
 * screen needs the sentence. `W12-WEB`'s U-01 mutation — the terminal reason replaced by
 * a constant — stays reddened by the existing `run-progress` test either way.
 *
 * **5. A reason this table does not know still says something true.** See
 * :data:`UNDESCRIBED_PREFIX`. The catalog has been resealed twice inside this programme,
 * and `W15-AUTH` found five classifiers collapsing into `server_error` for want of a
 * branch. A code from a newer contract than this client was built against renders as an
 * explicit "this screen has no description for it", never as silence and never as a
 * neighbouring code's sentence.
 *
 * No string here contains an apostrophe. `renderToStaticMarkup` escapes one to `&#x27;`,
 * and a test that has to un-escape a sentence before comparing it is a test that can be
 * made to pass by changing the un-escaping.
 */

import type { ErrorCode } from '@/shared/api';

/**
 * One sentence per catalog code, each a restatement of that code's own `summary` in
 * `contracts/domain/v1/error-codes.json`.
 *
 * Keyed by `ErrorCode` and declared `Record`, not `Partial<Record>`: a reseal that adds a
 * twenty-third code stops this file type-checking rather than silently routing the new
 * code to the undescribed branch. `web/tests/unit/run/terminal-reason.test.ts` is the
 * runtime half of the same claim.
 */
const CATALOG_SENTENCES: Readonly<Record<ErrorCode, string>> = {
  validation_failed:
    'Нарушены объявленная схема, перечисление, формат или инвариант, поэтому прогон ' +
    'остановился, а не записал несоответствующее. Причина не называет конкретное правило; ' +
    'таблица этапов ниже показывает, на каком этапе это произошло.',
  not_found:
    'То, к чему обращался прогон, не существует либо не видно вызывающей стороне. Причина ' +
    'не называет, что именно: каталог запрещает ответ, раскрывающий ресурс, который ' +
    'вызывающей стороне видеть не положено.',
  authentication_required:
    'Прогон остановился, потому что не был предъявлен действительный аутентифицированный ' +
    'субъект. Причина не содержит указаний на то, к чему обращались.',
  permission_denied:
    'Аутентифицированному субъекту не разрешено действие, которое требовалось прогону. ' +
    'Авторизация решается на сервере, и показание не фиксирует, какое именно право ' +
    'требовалось.',
  conflict:
    'Параллельная запись проиграла проверку оптимистичной блокировки, либо был бы нарушен ' +
    'инвариант уникальности. Каталог использует эту причину только там, где не подходит ' +
    'более точный конфликт, поэтому она не называет инвариант.',
  state_transition_not_allowed:
    'Прогон запросил переход, который зафиксированная машина состояний из его состояния ' +
    'не объявляет. Это отказ по умолчанию для любого необъявленного перехода, и ни один ' +
    'флаг его не отменяет.',
  idempotency_key_reuse:
    'Ключ идемпотентности был повторно использован с другим телом запроса. Ничего не ' +
    'создано и не изменено, дубликат под этим ключом не появился.',
  idempotency_key_in_progress:
    'Команда с тем же ключом и тем же телом ещё выполнялась. Средство — повторить запрос ' +
    'под тем же ключом; новый ключ означал бы вторую команду.',
  idempotency_key_stale:
    'Записанный результат для ключа идемпотентности больше не удалось установить, поэтому ' +
    'команда отказала, а не выполнилась второй раз наугад.',
  unsupported_contract_version:
    'Объявленная версия контракта или схемы неизвестна этому развёртыванию. Снисходительного ' +
    'отката нет, и приблизительной трактовки тоже.',
  storage_integrity_error:
    'Объявленная контрольная сумма, размер в байтах или тип содержимого не совпали с ' +
    'сохранёнными или переданными байтами, либо отсутствовала обязательная роль манифеста. ' +
    'Ничего не опубликовано.',
  dependency_unavailable:
    'Зависимость, нужная прогону, была недоступна. Каталог объединяет в эту одну причину ' +
    'хранилище метаданных, хранилище объектов, провайдера модели и транспорт исполнителя, а ' +
    'показание не фиксирует, о какой из них шла речь, — поэтому само по себе оно не ' +
    'свидетельствует о недоступности провайдера модели. Каталог помечает причину повторяемой: ' +
    'это разрешение запустить прогон снова, а не предсказание, что второй прогон продвинется ' +
    'дальше.',
  dependency_credential_refused:
    'Зависимость отвергла учётные данные этого развёртывания. Никто из пользователей API ' +
    'ничего не сделал неправильно, и повторный запуск не изменит исхода, пока оператор не ' +
    'починит учётные данные.',
  staged_upload_lost:
    'Хранилище объектов больше не содержало байты, подготовленные загрузкой. Ничего не ' +
    'опубликовано и не изменено; средство — отправить ту же загрузку заново.',
  required_norm_unavailable:
    'Нормативный источник, от которого зависит прогон, не удалось разрешить в неизменяемую ' +
    'версионированную запись. Неверсионированный, частичный или замещающий источник вместо ' +
    'него не использовался.',
  analysis_input_invalid:
    'Переданный пакет анализа или объявленный вход этапа оказались неприемлемыми. Показание ' +
    'не фиксирует конкретное поле; таблица этапов ниже показывает, на каком этапе это было.',
  analysis_failed:
    'Анализ завершился в терминальном состоянии отказа. Это общий сбой исполнения: он ' +
    'называет исход, а не одну причину, и если этапы записали собственные коды, эти коды ' +
    'есть в таблице этапов ниже.',
  partial_result_not_publishable:
    'У прогона, завершившегося с зафиксированной деградацией, запросили то, что требует ' +
    'прогона без неё. Деградировавший исход и список недостающего остаются видимыми, а не ' +
    'дополняются молча.',
  cost_budget_exceeded:
    'Объявленный бюджет стоимости или токенов для этого прогона исчерпан. Исполнение ' +
    'остановилось явно, а не стало молча ухудшать результат.',
  stale_attempt:
    'Попытка, отправившая эту работу, больше не является для неё публикующей инстанцией. ' +
    'Переданное сохраняется как неизменяемое свидетельство и никогда не применяется к ' +
    'состоянию проекта.',
  execution_token_invalid:
    'Предъявленный для этой работы токен исполнения отсутствовал, был искажён или не был ' +
    'текущим. Само значение никогда не возвращается обратно, поэтому причина его не ' +
    'показывает.',
  internal_error:
    'Прогон остановила неклассифицированная серверная неисправность. При этом прогон несёт ' +
    'устойчивый код и идентификатор корреляции; внутренние подробности остаются в защищённой ' +
    'диагностике, и ни путь, ни запрос, ни содержимое стека здесь не показываются.',
};

/**
 * How a sentence for an unknown reason starts.
 *
 * Exported so the test asserts the real string rather than a copy of it, and so the
 * assertion that no catalog sentence begins this way is a comparison against the same
 * bytes the screen renders.
 */
export const UNDESCRIBED_PREFIX =
  'У этого экрана нет описания для такой причины, и он его не выдумывает.';

/** The sentence a `failed` reading that carries no reason at all gets. */
export const ABSENT_SENTENCE =
  'Это показание не несёт терминальной причины. Отказавший прогон обязан её записать, ' +
  'поэтому показанию не хватает того, что контракт обязывает нести. Ничего не ' +
  'домысливается взамен.';

/** What the screen can say about the reason a `failed` run terminated with. */
export type TerminalReasonNote =
  /** The reading carried no `terminal_reason`, which a `failed` run is obliged to have. */
  | { readonly kind: 'absent'; readonly sentence: string }
  /** The reason is a catalog code and this screen states what that code means. */
  | { readonly kind: 'described'; readonly code: string; readonly sentence: string }
  /** The reason is outside the catalog this client was built from. */
  | { readonly kind: 'undescribed'; readonly code: string; readonly sentence: string };

/**
 * Turn a run reading's `terminal_reason` into something a person can read.
 *
 * The parameter is `string | null` and not `ErrorCode | null` on purpose. The contract
 * types the field as an `ErrorCode`, and the generated client casts the response body
 * rather than validating it, so a server one reseal ahead of this client puts a string
 * here that the type says cannot exist. That is the case the `undescribed` arm is for; a
 * signature that refused to model it would have decided the screen should crash or say
 * nothing.
 */
export function terminalReasonNote(reason: string | null | undefined): TerminalReasonNote {
  if (reason === null || reason === undefined || reason === '') {
    return { kind: 'absent', sentence: ABSENT_SENTENCE };
  }
  // Membership is read from the sentence table itself and never from a second copy of
  // the catalog. An earlier draft tested `ERROR_CODE_VALUES.has(reason)` and then indexed
  // the table, so a code present in the generated enum and absent from the table returned
  // `sentence: undefined` and the screen rendered an empty paragraph — the silent hole
  // this module exists to close, reintroduced by the check meant to close it. Mutation M5
  // is that case, run.
  if (Object.prototype.hasOwnProperty.call(CATALOG_SENTENCES, reason)) {
    return { kind: 'described', code: reason, sentence: CATALOG_SENTENCES[reason as ErrorCode] };
  }
  return {
    kind: 'undescribed',
    code: reason,
    sentence:
      `${UNDESCRIBED_PREFIX} Код выше — то слово, которое записал прогон, и описания ` +
      'для него у этого клиента нет. Ничего не опубликовано, а таблица этапов ниже ' +
      'показывает, на каком этапе это произошло.',
  };
}
