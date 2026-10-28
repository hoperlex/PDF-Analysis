/**
 * The words «Настройки анализа» says about the reviewed AR v3 beta pack.
 *
 * One place for the sentences the status panel prints, so the panel, the run list's reason for
 * a missing start control and the tests read the same string. The attestation sentence is the
 * one the design fixes: the pack carries a reviewer's record, the server does not check it,
 * and nothing the pack produces is more than a provisional citation for an expert to verify.
 */

export const PACK_TITLE = 'АР v3: пакет проверенных норм';

export const PACK_NOT_INSTALLED_SENTENCE =
  'Пакет проверенных норм АР v3 не установлен: запуск шести проверок недоступен.';

export const PACK_INSTALLED_SENTENCE =
  'Пакет проверенных норм АР v3 установлен: шесть проверок можно запустить из списка прогонов версии.';

export const PACK_READ_FAILED_TITLE = 'Не удалось прочитать статус пакета проверенных норм АР v3';

export const PACK_FAULT_TITLE = 'Статус пакета проверенных норм АР v3 не подтверждён';

export const PACK_FAULT_DETAIL =
  'Ответ сервера не соответствует контракту, поэтому пакет не показан ни установленным, ни ' +
  'отсутствующим, а запуск шести проверок недоступен.';

/**
 * The attestation record of the sealed pack, as «Настройки анализа» shows it: who prepared it and
 * that the system does not check it. It is NOT behind the review-indication switch (`R-146ba`, the
 * integrator's rule): the record states what the pack is, and stays whatever that switch says.
 * `web/tests/guards/review-indication.guard.test.ts` holds it out of the switch on purpose.
 */
export const ATTESTATION_SENTENCE =
  'Запись рецензента приложена при установке пакета; система её не проверяет, цитаты ' +
  'остаются предварительными и требуют проверки эксперта.';

/** How many leading hex characters of the pack digest the panel prints. */
export const PACK_DIGEST_SHOWN = 12;

/**
 * The leading characters of the sealed pack digest — all the panel shows, and the most of it any
 * markup may carry: no more than `PACK_DIGEST_SHOWN` characters of the digest appear in the DOM
 * for any role, so the full value is not in a `title`, a `data-` attribute or hidden text either.
 * The whole digest stays in memory, on the reading, for whatever must compare it.
 */
export function packDigestShown(packSha256: string): string {
  return `${packSha256.slice(0, PACK_DIGEST_SHOWN)}…`;
}
