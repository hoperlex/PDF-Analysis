/**
 * The estimate an AI start shows, and the consent it asks for (`Q-CMP-7`, ADR-0025 decisions 11 and 19; seal §3 decision 2).
 *
 * **Every AI start shows the estimate before it spends anything.** The reader sees what would be sent (calls, images with their
 * bytes, the size of the prompt), to which model, and what it would cost; the two ceilings; and one line of consent. The start then
 * carries `ComparisonAiConsent {estimate_digest, confirmed}`, where the digest is the **digest of the estimate that was on
 * screen** — {@link consentOf} reads it from the estimate it is given and from nowhere else, so a start can never carry a digest
 * the reader did not see. A digest that is no longer the one the server computes is `409 comparison_estimate_stale`; the screen
 * then reads the estimate again and asks again ({@link reconsentRequired}).
 *
 * Money is integer micro-USD, as in the spend journal. Nothing here goes through a float on the way to the screen except the one
 * division that picks the hundredths, and that one rounds **up** so that a small spend never reads as free.
 */

import type { ComparisonAiConsent, ComparisonAiEstimate, ComparisonAiMethod } from '@/shared/api';

/** The consent line of each kind of start (the original's `CONSENT`, `projects.js:558`; the sheet's own, `sheet-changes.js:35`). */
export const CONSENT_LINES = {
  pair_check: 'Подтверждаю передачу листов и подсказок для проверки сомнительных пар исполнителю',
  sheet_changes: 'Подтверждаю передачу материалов исполнителю',
  sheet: 'Подтверждаю передачу этого листа исполнителю',
  spec: 'Подтверждаю передачу текста спецификаций исполнителю',
  report: 'Подтверждаю передачу текста сводки исполнителю',
} as const;

export type ConsentKind = keyof typeof CONSENT_LINES;

export function consentKindOf(method: ComparisonAiMethod, single = false): ConsentKind {
  return single && method === 'sheet_changes' ? 'sheet' : method;
}

/** What the confirm button of each kind says (`:142` «Передать и описать»; `projects.js:565-570`). */
export const CONFIRM_LABELS = {
  pair_check: 'Проверить',
  sheet_changes: 'Запустить',
  sheet: 'Передать и описать',
  spec: 'Запустить сравнение',
  report: 'Сформировать',
} as const;

/** «Описать заново» and «Сформировать заново» are the same starts with `restart`. */
export const RESTART_CONFIRM_LABELS = {
  sheet_changes: 'Описать заново',
  report: 'Сформировать заново',
} as const;

export const RETRY_FAILED_LABEL = 'Повторить листы с ошибкой';

/** The consent that goes with a start: the digest of the estimate **as shown**, confirmed. */
export function consentOf(shown: Pick<ComparisonAiEstimate, 'estimate_digest'>): ComparisonAiConsent {
  return { estimate_digest: shown.estimate_digest, confirmed: true };
}

// ------------------------------------------------------------------------------ money

const MICROS_PER_CENT = 10_000;

/** «3,45 долл.» for integer micro-USD; a spend under a hundredth is «меньше 0,01 долл.» and never «0,00». */
export function formatUsd(micros: number): string {
  if (micros <= 0) return '0,00 долл.';
  const cents = Math.ceil(micros / MICROS_PER_CENT);
  if (micros < MICROS_PER_CENT) return 'меньше 0,01 долл.';
  const whole = Math.floor(cents / 100);
  const fraction = String(cents % 100).padStart(2, '0');
  return `${whole.toLocaleString('ru-RU')},${fraction} долл.`;
}

export const NOT_METERED_LABEL = 'без учёта стоимости';
export const NOT_METERED_TITLE = 'Подключение идёт по подписке: деньги за обращения не считаются и потолки на него не действуют.';

export const BILLING_LABELS = {
  metered: 'с учётом стоимости',
  not_metered: NOT_METERED_LABEL,
} as const;

export function isNotMetered(estimate: Pick<ComparisonAiEstimate, 'route'>): boolean {
  return estimate.route.billing === 'not_metered';
}

/** «≈ 3,45 долл.» or «без учёта стоимости». */
export function costLine(estimate: ComparisonAiEstimate): string {
  return isNotMetered(estimate) ? NOT_METERED_LABEL : `≈ ${formatUsd(estimate.estimate_micros)}`;
}

/** The two ceilings of `Q-CMP-7`, said for a metered connection; a connection that is not metered has none. */
export const CEILINGS_LINE = 'Потолки: 10 долл. на одно задание и 50 долл. в день на установку; если расход выйдет больше чем в 1,2 раза за оценку, задание встанет на паузу.';
export const NO_CEILINGS_LINE = 'Потолки по деньгам на это подключение не действуют.';

/** A sentence ends with one full stop: «долл.» already has its own. */
function closed(text: string): string {
  return text.endsWith('.') ? text : `${text}.`;
}

export function ceilingsLine(estimate: ComparisonAiEstimate): string {
  if (isNotMetered(estimate)) return NO_CEILINGS_LINE;
  const left = estimate.day_remaining_micros === undefined ? '' : ` ${closed(`Сегодня ещё можно потратить ${formatUsd(estimate.day_remaining_micros)}`)}`;
  return `${CEILINGS_LINE}${left}`;
}

// ------------------------------------------------------------------------------ the figures

/** «1,5 МБ» from bytes, one decimal (the original's `mb`, `sheet-changes.js:229`). */
export function megabytes(bytes: number): string {
  const tenths = Math.round((bytes * 10) / 1_048_576);
  return `${Math.floor(tenths / 10)},${tenths % 10} МБ`;
}

function count(value: number): string {
  return value.toLocaleString('ru-RU');
}

/** What the estimate's units are called for each kind of start. */
function unitsLine(estimate: ComparisonAiEstimate): string {
  const parts: string[] = [];
  switch (estimate.method) {
    case 'pair_check':
      parts.push(`вопросов: ${count(estimate.questions ?? estimate.units)}`);
      if (estimate.pairs !== undefined) parts.push(`пар: ${count(estimate.pairs)}`);
      break;
    case 'sheet_changes':
      parts.push(`листов: ${count(estimate.sheets ?? estimate.units)}`);
      if (estimate.transitions !== undefined) parts.push(`переходов: ${count(estimate.transitions)}`);
      break;
    case 'spec':
      parts.push(`версий: ${count(estimate.versions ?? estimate.units)}`);
      break;
    case 'report':
      parts.push(`переходов: ${count(estimate.transitions ?? estimate.units)}`);
      break;
  }
  if (estimate.reused !== undefined && estimate.reused > 0) {
    parts.push(`уже есть готовый ответ и повторно не отправляются: ${count(estimate.reused)}`);
  }
  return parts.join(' · ');
}

export interface EstimateLine {
  readonly key: string;
  readonly text: string;
  readonly muted?: boolean;
}

/** The lines of the estimate, in the order the reader needs them: what, how much, to whom, at what price. */
export function estimateLines(estimate: ComparisonAiEstimate): readonly EstimateLine[] {
  return [
    { key: 'units', text: `Будет передано исполнителю: ${unitsLine(estimate)}.` },
    {
      key: 'calls',
      text:
        `Обращений к модели: ${count(estimate.calls)} · изображений: ${count(estimate.images)} (${megabytes(estimate.image_bytes)})` +
        ` · текст: ${count(estimate.prompt_chars)} знаков.`,
    },
    {
      key: 'tokens',
      text: `Оценка объёма: вход ≈ ${count(estimate.input_tokens)} токенов, выход ≈ ${count(estimate.output_tokens)} токенов.`,
      muted: true,
    },
    { key: 'model', text: `Модель: ${estimate.route.pinned_model} · ${BILLING_LABELS[estimate.route.billing]}.` },
    { key: 'cost', text: closed(`Оценка стоимости: ${costLine(estimate)}`) },
    { key: 'ceilings', text: ceilingsLine(estimate), muted: true },
  ];
}

/** The estimate would be refused for a ceiling: the start is not offered. */
export function isBlocked(estimate: Pick<ComparisonAiEstimate, 'blocked_by'>): boolean {
  return estimate.blocked_by !== undefined;
}

export const BLOCKED_SENTENCES = {
  job: 'Оценка выше потолка одного задания (10 долл.): запуск не предлагается. Сократите объём или обратитесь к администратору.',
  day: 'Вместе с тем, что установка уже потратила сегодня, оценка выше потолка дня (50 долл.): запуск не предлагается. Повторите завтра или сократите объём.',
} as const;

/** Nothing to send: every unit already has a stored answer under the same content key (seal §3: they are never re-sent). */
export function isNothingToSend(estimate: Pick<ComparisonAiEstimate, 'units' | 'reused' | 'calls'>): boolean {
  return estimate.calls === 0 && (estimate.units === 0 || (estimate.reused ?? 0) >= estimate.units);
}

export const NOTHING_TO_SEND_SENTENCE =
  'Отправлять нечего: на все единицы уже есть сохранённые ответы. Запуск не предлагается.';

// ------------------------------------------------------------------------------ the re-ask after a stale digest

/**
 * Whether the reader's agreement still stands. The checkbox belongs to **one estimate**: when the estimate the screen shows is
 * not the one that was agreed to (a stale refusal re-read it, the route changed), the agreement is void and the line is asked
 * again. `agreedDigest` is the digest the box was ticked against.
 */
export function agreementStands(agreedDigest: string | null, shown: Pick<ComparisonAiEstimate, 'estimate_digest'> | undefined): boolean {
  return agreedDigest !== null && shown !== undefined && agreedDigest === shown.estimate_digest;
}

/** The note shown when an estimate changed under a reader who had already agreed to the previous one. */
export const RECONSENT_NOTE =
  'Оценка изменилась, пока вы её читали (другая модель, потолок или объём). Прежнее согласие не действует: прочитайте новую оценку и подтвердите ещё раз.';

export function reconsentRequired(
  agreedDigest: string | null,
  shown: Pick<ComparisonAiEstimate, 'estimate_digest'> | undefined,
): boolean {
  return agreedDigest !== null && shown !== undefined && agreedDigest !== shown.estimate_digest;
}
