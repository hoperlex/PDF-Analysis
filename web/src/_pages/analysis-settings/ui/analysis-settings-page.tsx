'use client';

/**
 * `/analysis-settings` — «Настройки анализа» (`R-66`, group «Система»; `W59-ANALYSIS-SETTINGS-01`).
 *
 * Graduated from the honest stub: `listAnalysisProfiles` answers the text-profile registry
 * the server routes runs through, so the screen lists the fifteen sections with the profile
 * each one runs with — or «профиль не создан» — for any account holding a role. It is
 * read-only: profiles are not edited, uploaded or reviewed here, and the contract has no
 * operation that would. A draft profile says in words that it still needs an expert's review.
 *
 * `HOSTS-WEB-01b`: «Пресеты запуска» (`ANALYSIS-PRESETS-01`) moved to the administrator's page `/workers/advanced`, so
 * the section is no longer drawn here and the presets are in one place only.
 */

import { useAnalysisProfiles } from '@/entities/analysis-profile';
import { failureMessage } from '@/shared/api/failure-message';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ErrorState, LoadingState, PageShell } from '@/shared/ui';
import styles from './analysis-settings-page.module.css';

export function AnalysisSettingsPage() {
  const profiles = useAnalysisProfiles();
  const failure = profiles.error === null ? null : failureMessage(profiles.error);
  return (
    <PageShell
      title="Настройки анализа"
      subtitle="Профиль анализа каждого раздела, с которым сервер выполняет прогон. Профили здесь только показываются, изменить их нельзя."
      actions={<button className="am-button am-button--quiet" type="button" onClick={() => void profiles.refetch()}>Обновить</button>}
    >
      {profiles.isPending ? <LoadingState what="профилей анализа" /> : null}
      {failure !== null ? (
        <div data-analysis-profiles-failure={failure.kind}>
          <ErrorState
            title="Профили анализа не прочитаны"
            detail={failure.detail}
            correlationId={failure.correlationId}
            onRetry={() => void profiles.refetch()}
          />
        </div>
      ) : null}
      {profiles.data !== undefined && failure === null ? (
        // The table keeps its own region Tab reaches, so this box does not scroll a second time.
        <div className={`${styles.panel} ${styles.flush}`}>
          <AnalysisProfileTable items={profiles.data.items} />
        </div>
      ) : null}
    </PageShell>
  );
}
