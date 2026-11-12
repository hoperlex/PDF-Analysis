/**
 * The «Источник» of a finding on «Разбор»: where it comes from (`CRIT-SEAL-50`, contract 1.51.0, `Finding.origin`).
 *
 * `text` is the text analysis, `drawing` a drawing candidate of the extended review, `cross_check` the cross-check of sources.
 * The server leaves `origin` out for a text finding, so absent means `text`. The three words are the ones the Excel
 * export's «Источник» column carries (`exports/xlsx/labels.py`), so the screen and the file say the same thing.
 */

import type { Finding, FindingDetail, FindingOrigin } from '@/shared/api';

export const FINDING_ORIGIN_LABELS: Readonly<Record<FindingOrigin, string>> = {
  text: 'Текст',
  drawing: 'Чертёж',
  cross_check: 'Сверка',
};

/** The origin of a finding; a finding the server sent without one is a text finding. */
export function findingOriginOf(finding: Pick<Finding | FindingDetail, 'origin'>): FindingOrigin {
  return finding.origin ?? 'text';
}

/**
 * True when the run's findings are not all text: some finding comes from a drawing or a cross-check, or stands on a block.
 * Only a `one_list` run publishes such findings (a `text_only` run never does), and the contract does not carry the run's
 * publication mode, so the findings themselves are the evidence of it.
 */
export function runHasNonTextFindings(findings: readonly Pick<Finding, 'origin' | 'observation'>[]): boolean {
  return findings.some((finding) => findingOriginOf(finding) !== 'text' || finding.observation.grounding_kind === 'portal_block');
}
