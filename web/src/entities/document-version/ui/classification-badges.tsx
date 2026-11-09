/**
 * A version's confirmed stage and section, as badges: «Стадия: П» and «Архитектурные
 * решения (АР)», or one «Раздел не подтверждён» when no expert has confirmed them.
 *
 * Presentational. It takes the contract's optional `classification` and nothing else, so the
 * same badges stand on the version screen, in a document's version list and in the project
 * structure. It never shows a suggestion: an unconfirmed version is unconfirmed, whatever its
 * file name says.
 *
 * The machine values ride on `data-` attributes (`data-project-stage`, `data-section-code`)
 * for an instrument; the reader gets the Cyrillic marks.
 */

import type { VersionClassification } from '@/shared/api';

import { sectionTitleOf, stageBadgeText } from '../model/classification';
import styles from './classification-badges.module.css';

export interface ClassificationBadgesProps {
  /**
   * The pair to show: a version's classification, or one entry of its history
   * (`CLASSIFICATION-CORRECTION-01`) -- only the stage and the section are read.
   */
  readonly classification:
    | Pick<VersionClassification, 'project_stage' | 'section_code'>
    | null
    | undefined;
  /**
   * `true` only when the section review said, explicitly, that no analysis profile is
   * registered for the confirmed section. Absent or `false` adds nothing.
   */
  readonly profileUnavailable?: boolean | undefined;
  /**
   * What to draw. A card that already stands inside its section's group (the project page, the section page) passes
   * `'stage'`: the section is said by the group, and saying it again on every card is height spent on nothing.
   * `'none'` is for the group of documents without a classification, which the group's own heading says.
   */
  readonly shown?: 'both' | 'stage' | 'none' | undefined;
}

export function ClassificationBadges({ classification, profileUnavailable, shown = 'both' }: ClassificationBadgesProps) {
  if (shown === 'none') return null;
  if (classification === null || classification === undefined) {
    return (
      <span className={styles.badges} data-version-classification="unclassified">
        <span className={`am-badge am-badge--pending ${styles.badge}`}>Раздел не подтверждён</span>
      </span>
    );
  }
  return (
    <span
      className={styles.badges}
      data-version-classification={`${classification.project_stage}:${classification.section_code}`}
    >
      <span
        className={`am-badge am-badge--active ${styles.badge}`}
        data-project-stage={classification.project_stage}
      >
        {stageBadgeText(classification.project_stage)}
      </span>
      {shown === 'stage' ? null : (
        <span
          className={`am-badge am-badge--ok ${styles.badge}`}
          data-section-code={classification.section_code}
        >
          {sectionTitleOf(classification.section_code)}
        </span>
      )}
      {profileUnavailable === true ? (
        <span className={`am-badge am-badge--degraded ${styles.badge}`} data-profile-unavailable="">
          профиль анализа недоступен
        </span>
      ) : null}
    </span>
  );
}
