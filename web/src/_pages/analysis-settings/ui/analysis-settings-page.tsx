'use client';

/**
 * `/analysis-settings` — «Настройки анализа» (`R-66`, group «Система»; `W59-ANALYSIS-SETTINGS-01`).
 *
 * Graduated from the honest stub: `listAnalysisProfiles` answers the text-profile registry
 * the server routes runs through, so the screen lists the fifteen sections with the profile
 * each one runs with — or «профиль не создан» — for any account holding a role. It is
 * read-only: profiles are not edited, uploaded or reviewed here, and the contract has no
 * operation that would. A draft profile says in words that it still needs an expert's review.
 */

import { useAnalysisProfiles } from '@/entities/analysis-profile';
import { failureMessage } from '@/shared/api/failure-message';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ArV3BetaStatus } from '@/widgets/ar-v3-beta-status';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';
import { ErrorState, LoadingState, PageShell } from '@/shared/ui';

export function AnalysisSettingsPage({ groupId = null }: { readonly groupId?: string | null }) {
  const profiles = useAnalysisProfiles();
  const failure = profiles.error === null ? null : failureMessage(profiles.error);
  return (
    <PageShell
      title="Настройки анализа"
      subtitle="Профиль анализа каждого раздела: с ним сервер выполняет прогон версии, раздел которой подтвердил эксперт. Экран только показывает профили — изменить их здесь нельзя."
      actions={<button className="am-button am-button--quiet" type="button" onClick={() => void profiles.refetch()}>Обновить</button>}
    >
      <ArV3BetaStatus />
      <ArV3BetaReview groupId={groupId} />
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
        <AnalysisProfileTable items={profiles.data.items} />
      ) : null}
    </PageShell>
  );
}
