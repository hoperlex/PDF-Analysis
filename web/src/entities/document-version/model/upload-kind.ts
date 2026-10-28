/**
 * How a version reached the product, in a reviewer's words (`CMP-VERSION-MARK-01`).
 *
 * `DocumentVersion.upload_kind` is `portal_bundle` for a version published from a portal
 * bundle and `comparison_pdf` for a plain PDF admitted for comparison only (`Q-CMP-5`,
 * ADR-0025 decisions 11 and 25). A comparison PDF has no portal bundle, so no section
 * analysis reads it: the server refuses the run start with `analysis_input_invalid`
 * (reason `comparison_only_version`). The screens do not wait for that refusal; they say
 * the same thing up front, from the field.
 *
 * The field is optional in the contract. Absent, and every value this client does not know,
 * is the ordinary version: only `comparison_pdf` changes any rendering, so a future value is
 * never read as a refusal the server did not make.
 */

import type { DocumentVersion } from '@/shared/api';

/** The mark a comparison-only version carries on every screen that lists or opens it. */
export const COMPARISON_ONLY_MARK = 'Загружено без пакета портала — только для сравнения';

/** What the version panel adds under the mark: what the version is and what it is for. */
export const COMPARISON_ONLY_DETAIL =
  'Это обычный PDF-файл, принятый только для сравнения. Его можно сравнивать с другими ' +
  'версиями комплекта; анализ по разделам для него не запускается.';

/** Why the run start is disabled on such a version. Nothing was sent; nothing will be. */
export const COMPARISON_ONLY_START_NOTE =
  'Запуск прогона недоступен: версия загружена без пакета портала и только для сравнения, ' +
  'а анализ по разделам читает пакет портала. Сервер отклонил бы такой запуск; эта версия ' +
  'остаётся доступной для сравнения с другими версиями.';

/**
 * Whether the version was admitted for comparison only. `upload_kind` is read, and nothing
 * else: a file name, a missing manifest entry or a missing classification says nothing here.
 */
export function isComparisonOnly(version: Pick<DocumentVersion, 'upload_kind'>): boolean {
  return version.upload_kind === 'comparison_pdf';
}
