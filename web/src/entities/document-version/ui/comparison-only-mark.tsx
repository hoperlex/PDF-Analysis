/**
 * The mark «Загружено без пакета портала — только для сравнения» and the disabled run start
 * of a version admitted for comparison only (`CMP-VERSION-MARK-01`).
 *
 * Presentational. `ComparisonOnlyMark` takes the contract's optional `upload_kind` through the
 * version and draws nothing for any other value, so the row and the panel that carry it are
 * byte for byte what they were for a portal version. `ComparisonOnlyStart` is what a run list
 * draws in place of the start controls: the same label, disabled, and the reason beside it.
 * The server refuses the same start (`comparison_only_version`); this is the sentence said
 * before the press instead of after it.
 */

import { useId } from 'react';

import type { DocumentVersion } from '@/shared/api';

import {
  COMPARISON_ONLY_MARK,
  COMPARISON_ONLY_START_NOTE,
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

/** The run start of a comparison-only version: disabled, and the reason it is. */
export function ComparisonOnlyStart() {
  const noteId = useId();
  return (
    <div data-start-run-disabled="comparison_only_version">
      <button type="button" className="am-button" disabled aria-describedby={noteId}>
        Запустить прогон
      </button>
      <p className="am-note" id={noteId}>
        {COMPARISON_ONLY_START_NOTE}
      </p>
    </div>
  );
}
