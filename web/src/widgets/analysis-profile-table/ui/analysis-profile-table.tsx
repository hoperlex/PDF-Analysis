/**
 * «Настройки анализа» — the analysis profile of every section (`W59-ANALYSIS-SETTINGS-01`).
 *
 * One row per section, in the order the server answers (the project structure's, `S-5`). A
 * section with a profile shows its version, its status and the prompt-bundle hash; the
 * details hold the identities, both hashes in full and where the prompt came from — the
 * legacy repository, commit and files with their hashes, or that the profile was written in
 * this application. A section without one says «профиль не создан» and what follows from it.
 *
 * Read-only by construction: no control here writes anything, and the contract has no
 * operation that edits a profile or its status.
 */

import type { AnalysisProfileListItem, AnalysisProfileSummary } from '@/shared/api';
import {
  NO_PROFILE_CONSEQUENCE,
  NO_PROFILE_LABEL,
  analysisProfileStatusLabel,
  shortDigest,
} from '@/entities/analysis-profile';
import { projectSectionOf } from '@/entities/project';

import styles from './analysis-profile-table.module.css';

export interface AnalysisProfileTableProps {
  readonly items: readonly AnalysisProfileListItem[];
}

function ProfileDetails({ profile }: { readonly profile: AnalysisProfileSummary }) {
  const { source } = profile;
  return (
    <details className={styles.details} data-profile-details>
      <summary>Подробнее</summary>
      <dl className={styles.facts}>
        <dt>Идентификатор профиля</dt>
        <dd><code>{profile.analysis_profile_id}</code></dd>
        <dt>Набор подсказок</dt>
        <dd><code>{profile.prompt_bundle_id}</code></dd>
        <dt>Хэш набора подсказок</dt>
        <dd><code>{profile.prompt_bundle_sha256}</code></dd>
        <dt>Хэш профиля</dt>
        <dd><code>{profile.content_sha256}</code></dd>
        <dt>Источник</dt>
        {source === null ? (
          <dd data-profile-source="builtin">Написан в этом приложении, не перенесён из прежней системы.</dd>
        ) : (
          <dd data-profile-source="ported">
            <p>Перенесён из прежней системы: репозиторий <code>{source.repository}</code>, коммит <code>{source.commit}</code>.</p>
            <p>Исходные файлы и их хэши:</p>
            <ul className={styles.files}>
              {source.files.map((file) => (
                <li key={file.path}>
                  <code>{file.path}</code> — <code>{file.sha256}</code>
                </li>
              ))}
            </ul>
          </dd>
        )}
      </dl>
    </details>
  );
}

function SectionRow({ item }: { readonly item: AnalysisProfileListItem }) {
  const section = projectSectionOf(item.section_code);
  const { profile } = item;
  return (
    <tr data-section={item.section_code} data-profile={profile === null ? 'none' : profile.status}>
      <th scope="row" className={`${styles.cell} ${styles.section}`}>
        <strong>{section.abbr}</strong> <span>{item.section_name}</span>
      </th>
      {profile === null ? (
        <td className={styles.cell} colSpan={4}>
          <strong>{NO_PROFILE_LABEL}</strong>. {NO_PROFILE_CONSEQUENCE}
        </td>
      ) : (
        <>
          <td className={styles.cell}>версия {profile.profile_version}</td>
          <td className={styles.cell} data-profile-status={profile.status}>{analysisProfileStatusLabel(profile.status)}</td>
          <td className={styles.cell}><code title={profile.prompt_bundle_sha256}>{shortDigest(profile.prompt_bundle_sha256)}</code></td>
          <td className={styles.cell}><ProfileDetails profile={profile} /></td>
        </>
      )}
    </tr>
  );
}

export function AnalysisProfileTable({ items }: AnalysisProfileTableProps) {
  return (
    <div className={styles.frame}>
      <table className={styles.table} aria-label="Профили анализа по разделам">
        <thead>
          <tr>
            <th className={styles.cell} scope="col">Раздел</th>
            <th className={styles.cell} scope="col">Профиль</th>
            <th className={styles.cell} scope="col">Состояние</th>
            <th className={styles.cell} scope="col">Хэш набора подсказок</th>
            <th className={styles.cell} scope="col">Подробнее</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => <SectionRow key={item.section_code} item={item} />)}
        </tbody>
      </table>
    </div>
  );
}
