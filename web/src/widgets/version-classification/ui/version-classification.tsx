'use client';

/**
 * «Стадия и раздел» — one version's classification panel on the version screen
 * (`W59-SECTION-UI-01`).
 *
 * It reads `getVersionSectionReview` on mount and renders exactly one of three answers:
 *
 *   - **confirmed** — the stage and section badges, who confirmed them and when, and «профиль
 *     анализа недоступен» when the review says the confirmed section has no registered
 *     analysis profile (so a run will be refused; nothing is analysed in its place);
 *   - **not confirmed, and the reader is an expert** — the confirmation form
 *     (`features/classify-version`);
 *   - **not confirmed, and the reader is not an expert** — one read-only sentence, «Раздел ещё
 *     не подтверждён экспертом». An administrator without the expert role is in this branch,
 *     because the API refuses `admin` alone.
 *
 * The roles come from the session the route has just checked (`requireScreen`), the way
 * «Нормы» receives them; they only decide which control to draw, and the API still checks
 * the write. A `409` from the form flips this panel to the confirmed branch with a note
 * that the stored classification came from another decision.
 *
 * The panel carries `id="version-classification"`, which is where the run control's refusal
 * links to (`routes.versionClassification`).
 */

import { useState } from 'react';

import type { Role, SectionReview } from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';
import { VERSION_CLASSIFICATION_ANCHOR, formatInstant } from '@/shared/lib';
import { failureMessage } from '@/shared/api/failure-message';
import type { VersionAddress } from '@/entities/document-version';
import {
  ClassificationBadges,
  canClassifyVersion,
  reviewOptionOf,
  useSectionReview,
} from '@/entities/document-version';
import { ClassifyVersionForm } from '@/features/classify-version';

export interface VersionClassificationProps {
  /** Built from the fetched version's own body, never from the address bar. */
  readonly address: VersionAddress;
  /** The session's roles, as the route's guard read them. */
  readonly roles: readonly Role[];
}

export interface VersionClassificationViewProps {
  readonly address: VersionAddress;
  readonly review: SectionReview;
  readonly roles: readonly Role[];
  /** Whether the reader's own confirmation was just refused with `409`. */
  readonly conflict: boolean;
  readonly onConflict: () => void;
}

/** The three answers, from a review already in hand. Rendered by the static harness. */
export function VersionClassificationView({
  address,
  review,
  roles,
  conflict,
  onConflict,
}: VersionClassificationViewProps) {
  const classification = review.classification;

  if (classification !== null) {
    const option = reviewOptionOf(review.options, classification.section_code);
    const profileUnavailable = option !== null && !option.executable;
    return (
      <div
        className="am-state"
        data-classification-state="confirmed"
        data-classified-document={address.documentUid}
      >
        <div className="am-state__title">
          <ClassificationBadges
            classification={classification}
            profileUnavailable={profileUnavailable}
          />
        </div>
        <div className="am-state__detail">
          {conflict ? (
            <p data-classification-conflict="">
              Стадия и раздел уже подтверждены другим решением — показана сохранённая
              классификация. Ваш выбор не применён, и исправить её пока нельзя.
            </p>
          ) : null}
          <p>
            Подтверждено экспертом {formatInstant(classification.confirmed_at)} (
            <code>{classification.confirmed_by_user_uid}</code>).
          </p>
          {profileUnavailable ? (
            <p data-profile-unavailable-note="">
              Для этого раздела профиль анализа ещё не зарегистрирован: прогон по этой версии
              будет отклонён, пока профиль не появится. Анализ по другому разделу вместо него не
              запускается.
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  if (canClassifyVersion(roles)) {
    return (
      <div data-classification-state="unconfirmed">
        <p className="am-note">
          Раздел ещё не подтверждён. Выберите стадию и раздел этой версии: прогон запускается
          только по подтверждённому разделу.
        </p>
        <ClassifyVersionForm address={address} review={review} onConflict={onConflict} />
      </div>
    );
  }

  return (
    <p className="am-note" data-classification-state="read-only">
      Раздел ещё не подтверждён экспертом. Подтвердить стадию и раздел может пользователь с ролью
      «Эксперт»; до этого прогон по этой версии не запускается.
    </p>
  );
}

export function VersionClassification({ address, roles }: VersionClassificationProps) {
  const review = useSectionReview(address);
  const [conflict, setConflict] = useState(false);

  let body;
  if (review.isPending) {
    body = <LoadingState what="стадию и раздел этой версии" />;
  } else if (review.isError) {
    const failure = failureMessage(review.error, {
      not_found: 'Такой версии в этом документе и проекте нет.',
    });
    body = (
      <ErrorState
        title="Стадию и раздел этой версии не удалось прочитать."
        detail={<span data-classification-read-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        onRetry={() => void review.refetch()}
      />
    );
  } else {
    body = (
      <VersionClassificationView
        address={address}
        review={review.data}
        roles={roles}
        conflict={conflict}
        onConflict={() => setConflict(true)}
      />
    );
  }

  return (
    <section
      id={VERSION_CLASSIFICATION_ANCHOR}
      className="am-section"
      data-classification-panel={address.versionUid}
    >
      <h2>Стадия и раздел</h2>
      {body}
    </section>
  );
}
