/**
 * The sign-in concept shows the destination shell. These are inert labels sourced from
 * registered screens: no links, navigation role, access decision or session data.
 */
import { SCREEN_REGISTRY } from '@/shared/config';

import { MENU_GROUP_LABELS } from './navigation';
import { NavigationGlyph } from './navigation-glyph';
import styles from './app-frame.module.css';

const previewLabels = {
  work: ['Проекты', 'Дашборд', 'Сравнение версий', 'Сравнение стадий'],
  knowledge: ['База знаний', 'Нормы'],
  system: ['Настройки анализа'],
} as const;

export function GuestNavigationPreview() {
  return (
    <div className={styles.guestPreview} aria-hidden="true" data-guest-preview="">
      <p className={styles.guestPreviewHeading}>Превью разделов</p>
      {Object.entries(previewLabels).map(([group, labels]) => {
        const rows = SCREEN_REGISTRY.filter((row) => row.inMenu && row.group === group && labels.some((label) => label === row.label));
        return (
          <div className={styles.guestPreviewGroup} key={group}>
            <p className={styles.guestPreviewGroupName}>{MENU_GROUP_LABELS[group as keyof typeof previewLabels]}</p>
            {rows.map((row) => (
              <span className={styles.guestPreviewRow} key={row.address}>
                <span className={styles.guestPreviewIcon}><NavigationGlyph label={row.label} /></span>
                <span className={styles.guestPreviewLabel}>{row.label}</span>
              </span>
            ))}
          </div>
        );
      })}
      <div className={styles.guestPreviewNote}>
        <span className={styles.guestPreviewNoteIcon}>↗</span>
        <strong>После входа</strong>
        <p>Рабочие разделы и проекты откроются после авторизации.</p>
        <span className={styles.guestPreviewPill}>Только превью</span>
      </div>
    </div>
  );
}
