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
 *
 * `UIP-S05-04` (pair S05): over the table one line says where the models of the stages are set, because the name of this screen leads a person who
 * knows the original's «Конфигурация моделей» to look for them here. They are set in «Диспетчер», on its tab «Модели по этапам»; the word is the link.
 * It points and does nothing else: no model is chosen on this screen, and the table and the rest of it are as they were.
 */

import { useAnalysisProfiles } from '@/entities/analysis-profile';
import { STAGE_MODELS_TITLE } from '@/entities/stage-layout';
import { failureMessage } from '@/shared/api/failure-message';
import { routes } from '@/shared/lib';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ErrorState, LoadingState, PageShell } from '@/shared/ui';
import styles from './analysis-settings-page.module.css';

/** «Диспетчер → Модели по этапам»: the tab is a place in the address of the screen «Диспетчер». */
const MODELS_BY_STAGE_TAB = `${routes.workers()}?tab=models`;

export function AnalysisSettingsPage() {
  const profiles = useAnalysisProfiles();
  const failure = profiles.error === null ? null : failureMessage(profiles.error);
  return (
    <PageShell
      title="Настройки анализа"
      subtitle="Профиль анализа каждого раздела, с которым сервер выполняет прогон. Профили здесь только показываются, изменить их нельзя."
      actions={<button className="am-button am-button--quiet" type="button" onClick={() => void profiles.refetch()}>Обновить</button>}
    >
      <p className="am-note" data-models-pointer="">
        {`${STAGE_MODELS_TITLE} задаются в `}<a href={MODELS_BY_STAGE_TAB}>«Диспетчере»</a>.
      </p>
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
