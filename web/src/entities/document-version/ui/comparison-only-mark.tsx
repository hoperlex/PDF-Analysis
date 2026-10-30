/**
 * Mark a PDF admitted through comparison without a portal companion.
 *
 * Presentational. `ComparisonOnlyMark` takes the contract's optional `upload_kind` through the
 * version and draws nothing for any other value. Ordinary runs use the PDF's native
 * text and pages; the mark says only that portal annotations are absent.
 */

import type { DocumentVersion } from '@/shared/api';

import {
  COMPARISON_ONLY_MARK,
  isComparisonOnly,
} from '../model/upload-kind';
import styles from './comparison-only-mark.module.css';

export interface ComparisonOnlyMarkProps {
  readonly version: Pick<DocumentVersion, 'upload_kind'>;
}
export function ComparisonOnlyMark({ version }: ComparisonOnlyMarkProps) {
  if (!isComparisonOnly(version)) return null;
  return (
    <span
      className={`am-badge am-badge--degraded ${styles.mark}`}
      data-upload-kind="comparison_pdf"
      data-comparison-only-mark=""
    >
      {COMPARISON_ONLY_MARK}
    </span>
  );
}
