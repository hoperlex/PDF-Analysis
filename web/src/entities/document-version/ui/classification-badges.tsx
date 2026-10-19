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
  readonly classification: VersionClassification | null | undefined;
  /**
   * `true` only when the section review said, explicitly, that no analysis profile is
   * registered for the confirmed section. Absent or `false` adds nothing.
   */
  readonly profileUnavailable?: boolean | undefined;
}

export function ClassificationBadges({ classification, profileUnavailable }: ClassificationBadgesProps) {
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
      <span
        className={`am-badge am-badge--ok ${styles.badge}`}
        data-section-code={classification.section_code}
      >
        {sectionTitleOf(classification.section_code)}
      </span>
      {profileUnavailable === true ? (
        <span className={`am-badge am-badge--degraded ${styles.badge}`} data-profile-unavailable="">
          профиль анализа недоступен
        </span>
      ) : null}
    </span>
  );
}
