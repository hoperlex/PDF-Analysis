'use client';

/**
 * «Стадия и раздел» — one version's classification panel on the version screen
 * (`W59-SECTION-UI-01`).
 *
 * It reads `getVersionSectionReview` on mount and renders exactly one of three answers:
 *
 *   - **confirmed** — the stage and section badges, who confirmed them and when, and «профиль
 *     анализа недоступен» when the review says the confirmed section has no registered
 *     analysis profile (so a run will be refused; nothing is analysed in its place). Since
 *     `CLASSIFICATION-CORRECTION-01` it also names the revision, lists the history (every
 *     earlier revision with its expert, time and reason) and, for an expert, offers
 *     «Исправить»: the correction form, based on the revision shown;
 *   - **not confirmed, and the reader is an expert** — the confirmation form
 *     (`features/classify-version`);
 *   - **not confirmed, and the reader is not an expert** — one read-only sentence, «Раздел ещё
 *     не подтверждён экспертом». An administrator without the expert role is in this branch,
 *     because the API refuses `admin` alone.
 *
 * The roles come from the session the route has just checked (`requireScreen`), the way
 * «Нормы» receives them; they only decide which control to draw, and the API still checks
 * the write. A `409` from the form flips this panel to the confirmed branch with a note
 * that the stored classification came from another decision; a correction a colleague made
 * first shows its own refusal inside the correction form and the panel reads the stored
 * classification again.
 *
 * The panel carries `id="version-classification"`, which is where the run control's refusal
 * links to (`routes.versionClassification`).
 *
 * `UIP-S04-04`: **a confirmed «Стадия и раздел» is one line** — the label, the section's colour and the stage and section badges,
 * «Подтверждено экспертом <когда>» (or «Исправлено экспертом»), and «Исправить» for an expert; the revision, the account's code and
 * the history are behind «Подробнее». What changes the next step stays on the page: the conflict, a section with no profile, and the
 * correction form itself, which opens under the line. The forms are as they were; only their place and the fold of the history
 * changed. The panel owns its frame (`version-classification.module.css`), so the page only chooses where it stands.
 */

import { useState } from 'react';

import type { Role, SectionReview } from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';
import { VERSION_CLASSIFICATION_ANCHOR, formatInstant } from '@/shared/lib';
import { failureMessage } from '@/shared/api/failure-message';
import { SectionDot } from '@/entities/project';
import type { VersionAddress } from '@/entities/document-version';
import {
  ClassificationBadges,
  ClassificationHistory,
  canClassifyVersion,
  canCorrectClassification,
  isCorrected,
  reviewOptionOf,
  revisionText,
  useSectionReview,
} from '@/entities/document-version';
import { ClassifyVersionForm } from '@/features/classify-version';
import { CorrectVersionClassificationForm } from '@/features/correct-version-classification';

import styles from './version-classification.module.css';

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
  /** Whether the correction form is open (`CLASSIFICATION-CORRECTION-01`). Closed when absent. */
  readonly correcting?: boolean | undefined;
  /** Open or close the correction form. */
  readonly onCorrecting?: ((open: boolean) => void) | undefined;
}

/** The three answers, from a review already in hand. Rendered by the static harness. */
export function VersionClassificationView({
  address,
  review,
  roles,
  conflict,
  onConflict,
  correcting = false,
  onCorrecting,
}: VersionClassificationViewProps) {
  const classification = review.classification;

  if (classification !== null) {
    const option = reviewOptionOf(review.options, classification.section_code);
    const profileUnavailable = option !== null && !option.executable;
    const mayCorrect = canCorrectClassification(roles) && onCorrecting !== undefined;
    return (
      <div className={styles.confirmed} data-classification-state="confirmed" data-classified-document={address.documentUid}>
        <div className={styles.row} data-classification-row="">
          <h2 className={styles.label}>Стадия и раздел</h2>
          <span className={styles.mark}>
            <SectionDot code={classification.section_code} />
            <ClassificationBadges classification={classification} profileUnavailable={profileUnavailable} />
          </span>
          <span className={styles.said} data-classification-confirmed="">
            {isCorrected(classification) ? 'Исправлено экспертом' : 'Подтверждено экспертом'}{' '}
            <time dateTime={classification.confirmed_at}>{formatInstant(classification.confirmed_at)}</time>
          </span>
          {mayCorrect && !correcting ? (
            <button
              type="button"
              className={`am-button am-button--small ${styles.correct}`}
              data-classification-correct=""
              onClick={() => onCorrecting(true)}
            >
              Исправить
            </button>
          ) : null}
        </div>
        {conflict ? (
          <p data-classification-conflict="">
            Стадия и раздел уже подтверждены другим решением — показана сохранённая
            классификация. Ваш выбор не применён; изменить её может эксперт кнопкой
            «Исправить» с указанием причины.
          </p>
        ) : null}
        {profileUnavailable ? (
          <p data-profile-unavailable-note="">
            Для этого раздела профиль анализа ещё не зарегистрирован: прогон по этой версии
            будет отклонён, пока профиль не появится. Анализ по другому разделу вместо него не
            запускается.
          </p>
        ) : null}
        {mayCorrect && correcting ? (
          <CorrectVersionClassificationForm
            address={address}
            review={review}
            current={classification}
            onDone={() => onCorrecting(false)}
            onCancel={() => onCorrecting(false)}
          />
        ) : null}
        <details className={styles.more} data-classification-more="">
          <summary>Подробнее</summary>
          <p data-classification-revision-line={classification.revision}>
            {revisionText(classification.revision)}. Учётная запись эксперта: <code>{classification.confirmed_by_user_uid}</code>.
          </p>
          <ClassificationHistory revisions={review.revisions} />
        </details>
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
  const [correcting, setCorrecting] = useState(false);

  let body;
  if (review.isPending) {
    body = <LoadingState what="стадию и раздел этой версии" />;
  } else if (review.isError) {
    const failure = failureMessage(review.error, {
      not_found: 'Такой версии в этом документе и объекте нет.',
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
        correcting={correcting}
        onCorrecting={setCorrecting}
      />
    );
  }

  // A confirmed section is the one-line row, which carries its own label; every other answer has the heading above it.
  const confirmed = review.isSuccess && review.data.classification !== null;
  return (
    <section
      id={VERSION_CLASSIFICATION_ANCHOR}
      className={confirmed ? `am-section ${styles.panel} ${styles.panelRow}` : `am-section ${styles.panel}`}
      data-classification-panel={address.versionUid}
    >
      {confirmed ? null : <h2>Стадия и раздел</h2>}
      {body}
    </section>
  );
}
