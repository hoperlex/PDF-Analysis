'use client';

/**
 * What the version of the address is, when it was admitted for comparison only
 * (`CMP-DEBT-261`, after `CMP-VERSION-MARK-01`).
 *
 * The screen compares this version with another one of its set, and a comparison-only version
 * (a plain PDF, `Q-CMP-5`) is exactly what that comparison is for, so it is neither hidden nor
 * disabled: it carries the shared mark and the sentence that says what the version is for. The
 * run comparison below it has nothing to compare for such a version, and this is why. Any other
 * version draws nothing, and so does a version that has not been read: the widget under this
 * note says that it is loading or why it was not read.
 *
 * The read is the one `widgets/version-comparison` makes (the same query key, so one request).
 */

import type { VersionUid } from '@/shared/api';
import {
  COMPARISON_ONLY_DETAIL,
  ComparisonOnlyMark,
  isComparisonOnly,
  useDocumentVersion,
} from '@/entities/document-version';

export interface ComparisonOnlyNoteProps {
  readonly versionUid: VersionUid;
}

export function ComparisonOnlyNote({ versionUid }: ComparisonOnlyNoteProps) {
  const version = useDocumentVersion(versionUid);
  if (version.data === undefined || !isComparisonOnly(version.data)) return null;
  return (
    <p data-comparison-only-version="">
      <ComparisonOnlyMark version={version.data} /> {COMPARISON_ONLY_DETAIL}
    </p>
  );
}
