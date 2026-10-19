/**
 * The comparison of two versions of one set, in a reviewer's words (`W59-VERSION-COMPARE-01`).
 *
 * Every label table is keyed by the contract's own closed union, so a new refusal reason,
 * sheet status or proposal kind fails to compile here instead of rendering a Latin word.
 * Nothing in this module decides anything: the server compares, refuses and proposes; this
 * module only orders the two chosen versions (older first, as the server requires) and says
 * whether the «Стадии П → Р» mode is meaningful for them.
 */

import type {
  ComparisonRefusal,
  DocumentVersion,
  FindingMatchProposal,
  SheetDiff,
  SheetPairing,
} from '@/shared/api';

type RefusalReason = ComparisonRefusal['reason'];
type RefusalSide = NonNullable<ComparisonRefusal['side']>;

/** «более ранней» / «более поздней»: which of the two chosen versions a reason is about. */
export const COMPARISON_SIDE_LABELS: Readonly<Record<RefusalSide, string>> = {
  source: 'более ранней',
  target: 'более поздней',
};

/**
 * Why two versions are not compared. A function per reason, because some name a side.
 * The path version is proved before any of these is possible, so the set-level reasons are
 * about the other version.
 */
const REFUSAL_TEXT: Readonly<Record<RefusalReason, (side: string) => string>> = {
  same_version: () => 'Выбрана та же самая версия — сравнивать её с собой нечего.',
  version_not_found: () => 'Выбранная версия не найдена.',
  different_set: () => 'Выбранная версия относится к другому комплекту документов.',
  foreign_project: () => 'Выбранная версия относится к другому проекту.',
  version_not_published: () => 'Одна из версий не опубликована.',
  version_order_invalid: () => 'Сначала должна идти более ранняя версия, затем более поздняя.',
  stage_unclassified: (side) => `У ${side} версии не указана стадия (П или Р).`,
  section_unconfirmed: (side) => `У ${side} версии раздел не подтверждён экспертом.`,
  project_stage_mismatch: () =>
    'Версии относятся к разным стадиям. Их можно сравнить в режиме «Стадии П → Р».',
  confirmed_section_mismatch: () => 'У версий подтверждены разные разделы.',
  stage_pair_invalid: () =>
    'Для сравнения стадий более ранняя версия должна быть стадии П, а более поздняя — стадии Р.',
  analysis_missing: (side) => `У ${side} версии нет завершённого анализа.`,
  run_not_of_version: (side) => `Указанный прогон не относится к ${side} версии.`,
  run_not_published: (side) => `Указанный прогон ${side} версии не завершён.`,
  text_unavailable: (side) => `Текстовый слой ${side} версии недоступен.`,
  text_too_large: (side) => `Текст ${side} версии больше допустимого для сравнения.`,
};

export function refusalText(refusal: ComparisonRefusal): string {
  const side = refusal.side === null ? 'одной из' : COMPARISON_SIDE_LABELS[refusal.side];
  return REFUSAL_TEXT[refusal.reason](side);
}

export const SHEET_STATUS_LABELS: Readonly<Record<SheetPairing['status'], string>> = {
  unchanged: 'без изменений',
  changed: 'изменён',
  removed: 'удалён',
  added: 'добавлен',
};

/** Why two sheets were paired — a proposal's evidence, never an approval. */
export function pairingBasisText(sheet: SheetPairing): string {
  if (sheet.pairing_basis === 'exact_text') return 'текст совпадает полностью';
  if (sheet.pairing_basis === 'similar_text') {
    const percent = Math.round((sheet.similarity_permille ?? 0) / 10);
    return `похожий текст: сходство ${percent} %, общих строк ${sheet.shared_line_count ?? 0}`;
  }
  return sheet.textless ? 'нет текстового слоя — сопоставить по тексту нельзя' : 'пары не найдено';
}

export const TOO_LARGE_TEXT: Readonly<Record<NonNullable<SheetDiff['too_large_reason']>, string>> = {
  source_text_too_large: 'Лист более ранней версии слишком велик для построчного сравнения.',
  source_text_too_many_lines: 'В листе более ранней версии слишком много строк для сравнения.',
  target_text_too_large: 'Лист более поздней версии слишком велик для построчного сравнения.',
  target_text_too_many_lines: 'В листе более поздней версии слишком много строк для сравнения.',
  text_not_utf8_encodable: 'Текст листа нельзя сравнить построчно.',
};

export const PROPOSAL_KIND_LABELS: Readonly<Record<FindingMatchProposal['kind'], string>> = {
  unchanged: 'Без изменений',
  probably_fixed: 'Вероятно, устранено',
  undetermined: 'Требует проверки',
  new: 'Новое',
};

export const PROPOSAL_BASIS_TEXT: Readonly<Record<FindingMatchProposal['basis'], string>> = {
  exact_issue_and_quotes: 'тот же текст замечания и те же цитаты на сопоставленном листе',
  quotes_absent_from_paired_sheets: 'цитируемого текста на сопоставленном листе больше нет',
  quote_still_on_paired_sheet: 'цитируемый текст остался, но замечание не повторено',
  evidence_sheet_unpaired: 'для листа с цитатой не найдено пары',
  evidence_over_limit: 'слишком много цитат для автоматического сопоставления',
  no_exact_source_match: 'в более ранней версии нет точного соответствия',
};

/** The two chosen versions, older first: the server compares source → target, never back. */
export function orderedPair(
  a: DocumentVersion,
  b: DocumentVersion,
): { readonly source: DocumentVersion; readonly target: DocumentVersion } {
  return a.version_ordinal <= b.version_ordinal ? { source: a, target: b } : { source: b, target: a };
}

/**
 * Whether «Стадии П → Р» means something for this pair: both versions confirmed, the older
 * at stage П and the newer at stage Р, one section. Anything else is still sent as asked and
 * refused by the server with its own reason; this only decides whether the switch is offered.
 */
export function stageModeOffered(source: DocumentVersion, target: DocumentVersion): boolean {
  const older = source.classification;
  const newer = target.classification;
  return (
    older !== undefined &&
    newer !== undefined &&
    older.project_stage === 'P' &&
    newer.project_stage === 'R' &&
    older.section_code === newer.section_code
  );
}

/** «Версия 2», by its display ordinal — a label, never an identity. */
export function versionLabel(version: DocumentVersion): string {
  return `Версия ${version.version_ordinal}`;
}
