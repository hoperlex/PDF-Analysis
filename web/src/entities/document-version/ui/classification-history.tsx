/**
 * A version's classification history (`CLASSIFICATION-CORRECTION-01`): every revision, newest
 * first -- the original confirmation as revision 1, then each correction with the expert who
 * made it, when, and why.
 *
 * Presentational. It reads `SectionReview.revisions` and nothing else, so the same list can
 * stand on the version screen and anywhere a later screen wants the audit trail. The reason is
 * the expert's own text, shown as written (line breaks kept) and never interpreted; the
 * original confirmation has none, and says so by being «подтверждение», not «исправление».
 */

import type { VersionClassificationRevision } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { revisionText, revisionsNewestFirst } from '../model/classification';
import { ClassificationBadges } from './classification-badges';
import styles from './classification-history.module.css';

export interface ClassificationHistoryProps {
  readonly revisions: readonly VersionClassificationRevision[];
}

export function ClassificationHistory({ revisions }: ClassificationHistoryProps) {
  if (revisions.length === 0) return null;
  const ordered = revisionsNewestFirst(revisions);
  return (
    <div data-classification-history={revisions.length}>
      <h3>История классификации</h3>
      <ol className={styles.list}>
        {ordered.map((entry) => {
          const original = entry.revision === 1;
          return (
            <li
              key={entry.revision}
              className={styles.entry}
              data-classification-revision={entry.revision}
              data-revision-kind={original ? 'confirmation' : 'correction'}
            >
              <div className={styles.head}>
                <strong>{revisionText(entry.revision)}</strong>
                <span>{original ? 'подтверждение' : 'исправление'}</span>
                <span>{formatInstant(entry.at)}</span>
                <code>{entry.actor_user_uid}</code>
              </div>
              <ClassificationBadges classification={entry} />
              {entry.reason === null ? null : (
                <p className={styles.reason} data-revision-reason="">
                  Причина: {entry.reason}
                </p>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
