/**
 * How a version reached the product, in a reviewer's words (`CMP-VERSION-MARK-01`).
 *
 * `DocumentVersion.upload_kind` is `portal_bundle` for a version published from a portal
 * bundle and `comparison_pdf` for a plain PDF admitted through comparison. A comparison
 * PDF has no portal companion; ordinary section analysis uses its native text and pages.
 *
 * The field is optional in the contract. Absent, and every value this client does not know,
 * is the ordinary version: only `comparison_pdf` adds the missing-portal mark.
 */

import type { DocumentVersion } from '@/shared/api';

/** The mark a comparison-only version carries on every screen that lists or opens it. */
export const COMPARISON_ONLY_MARK = 'PDF без пакета портала';

/** What the version panel adds under the mark: what the version is and what it is for. */
export const COMPARISON_ONLY_DETAIL =
  'Этот PDF загружен через сравнение. Анализ раздела выполняется по тексту и страницам PDF; ' +
  'структурированные данные портала отсутствуют.';

/** Why a portal-dependent operation is disabled on such a version. */
export const COMPARISON_ONLY_START_NOTE =
  'Для этой операции нужны структурированные данные пакета портала. ' +
  'Исходный PDF остаётся доступен для анализа раздела и сравнения.';

/**
 * Whether the version was admitted for comparison only. `upload_kind` is read, and nothing
 * else: a file name, a missing manifest entry or a missing classification says nothing here.
 */
export function isComparisonOnly(version: Pick<DocumentVersion, 'upload_kind'>): boolean {
  return version.upload_kind === 'comparison_pdf';
}
