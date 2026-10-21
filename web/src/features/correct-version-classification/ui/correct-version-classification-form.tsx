'use client';

/**
 * The expert's correction of one version's confirmed project stage and section
 * (`CLASSIFICATION-CORRECTION-01`).
 *
 * **What it offers.** The two stages and all fifteen sections, starting from the current
 * classification, and a reason in the expert's own words. The button stays held until the
 * pair differs from the current one, the reason is a real sentence (a letter or a digit, no
 * more than {@link CORRECTION_REASON_MAX_LENGTH} characters) and no request is in flight: the
 * server decides all three again, this only keeps the button honest.
 *
 * **What it says it does.** A correction adds a numbered revision and leaves every earlier one
 * in the history; runs already started keep the analysis profile they pinned, and re-auditing
 * the version is what applies the corrected section. It is based on the revision the screen
 * shows (`expectedRevision`), so a classification somebody else corrected meanwhile is
 * refused instead of overwritten.
 *
 * **One press, one request.** The button is disabled while the request is in flight, and a
 * synchronous gate (`../model/single-flight.ts`) refuses a second press that arrives before
 * React has re-rendered.
 *
 * **What a refusal shows.** Its own Russian sentence per kind (stale, unclassified, unchanged,
 * reason, role), or the shared reading with its correlation id; none offers an override.
 *
 * `CorrectVersionClassificationFormView` is the whole markup, driven by props, so every state
 * can be rendered by the static harness; `CorrectVersionClassificationForm` adds the state and
 * the command.
 */

import { useState } from 'react';

import type {
  ProjectSection as SectionCode,
  ProjectStage,
  SectionReview,
  VersionClassification,
} from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import type { CorrectionFailure, VersionAddress } from '@/entities/document-version';
import {
  CORRECTION_REASON_MAX_LENGTH,
  PROJECT_STAGES,
  correctionFailure,
  differsFromCurrent,
  orderSectionOptions,
  reasonProblem,
  reasonProblemText,
  revisionText,
  sectionTitleOf,
  stageChoiceText,
} from '@/entities/document-version';

import { createSingleFlight } from '../model/single-flight';
import { useCorrectVersionClassification } from '../model/use-correct-version-classification';
import styles from './correct-version-classification-form.module.css';

export interface CorrectVersionClassificationFormViewProps {
  readonly review: SectionReview;
  /** The classification the correction is based on (its `revision` is `expected_revision`). */
  readonly current: VersionClassification;
  readonly stage: ProjectStage | null;
  readonly section: SectionCode | null;
  readonly reason: string;
  readonly pending: boolean;
  readonly failure: CorrectionFailure | null;
  readonly onStage: (stage: ProjectStage) => void;
  readonly onSection: (section: SectionCode) => void;
  readonly onReason: (reason: string) => void;
  readonly onSubmit: () => void;
  readonly onCancel: () => void;
}

export function CorrectVersionClassificationFormView({
  review,
  current,
  stage,
  section,
  reason,
  pending,
  failure,
  onStage,
  onSection,
  onReason,
  onSubmit,
  onCancel,
}: CorrectVersionClassificationFormViewProps) {
  const { suggested, rest } = orderSectionOptions(review.options);
  const options = [...suggested, ...rest];
  const problem = reasonProblem(reason);
  const differs = differsFromCurrent(current, stage, section);
  const ready = differs && problem === null && !pending;

  return (
    <form
      className="am-form"
      data-classification-correction-form=""
      data-based-on-revision={current.revision}
      onSubmit={(event) => {
        event.preventDefault();
        if (ready) onSubmit();
      }}
    >
      <p className="am-form__hint">
        Исправление добавит новую ревизию ({revisionText(current.revision + 1)}); прежние ревизии
        останутся в истории. Уже запущенные прогоны сохраняют профиль анализа, с которым начались;
        чтобы применить исправленный раздел, перезапустите анализ версии.
      </p>

      <fieldset className={styles.group}>
        <legend className={styles.legend}>Стадия проекта</legend>
        {PROJECT_STAGES.map((value) => (
          <label key={value} className={styles.choice}>
            <input
              type="radio"
              name="classification-correction-stage"
              value={value}
              data-correction-stage={value}
              checked={stage === value}
              disabled={pending}
              onChange={() => onStage(value)}
            />
            <span className={styles.label}>{stageChoiceText(value)}</span>
          </label>
        ))}
      </fieldset>

      <div className={styles.group}>
        <label className={styles.legend} htmlFor="classification-correction-section">
          Раздел
        </label>
        <select
          id="classification-correction-section"
          data-correction-section=""
          value={section ?? ''}
          disabled={pending}
          onChange={(event) => {
            const chosen = options.find((option) => option.section_code === event.target.value);
            if (chosen !== undefined) onSection(chosen.section_code);
          }}
        >
          {options.map((option) => (
            <option key={option.section_code} value={option.section_code}>
              {sectionTitleOf(option.section_code)}
              {option.executable ? '' : ' — профиль анализа недоступен'}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.group}>
        <label className={styles.legend} htmlFor="classification-correction-reason">
          Причина исправления
        </label>
        <textarea
          id="classification-correction-reason"
          className={styles.reason}
          data-correction-reason=""
          rows={4}
          maxLength={CORRECTION_REASON_MAX_LENGTH}
          required
          value={reason}
          disabled={pending}
          aria-describedby="classification-correction-reason-hint"
          onChange={(event) => onReason(event.target.value)}
        />
        <p className="am-form__hint" id="classification-correction-reason-hint">
          Причина сохраняется в истории вместе с вашим именем и временем; изменить её потом нельзя.
          До {CORRECTION_REASON_MAX_LENGTH} символов.
        </p>
        {reason !== '' && problem !== null ? (
          <p className="am-form__problem" role="alert" data-correction-reason-problem={problem}>
            {reasonProblemText(problem)}
          </p>
        ) : null}
      </div>

      {differs || stage === null || section === null ? null : (
        <p className="am-form__hint" data-correction-unchanged="">
          Стадия и раздел совпадают с текущими. Измените хотя бы одно из значений.
        </p>
      )}

      <div className="am-form__row">
        <button type="submit" className="am-button" data-correction-submit="" disabled={!ready}>
          Сохранить исправление
        </button>
        <button
          type="button"
          className="am-button"
          data-correction-cancel=""
          disabled={pending}
          onClick={onCancel}
        >
          Отмена
        </button>
      </div>

      {pending ? <LoadingState what="сохранение исправления" /> : null}

      {failure === null ? null : (
        <p className="am-form__problem" role="alert" data-correction-failure={failure.kind}>
          {failure.detail}
          {failure.correlationId === null ? null : (
            <>
              {' '}
              Идентификатор корреляции <code>{failure.correlationId}</code>.
            </>
          )}
        </p>
      )}
    </form>
  );
}

export interface CorrectVersionClassificationFormProps {
  readonly address: VersionAddress;
  readonly review: SectionReview;
  readonly current: VersionClassification;
  /** Called after the correction is stored, so the panel can close the form. */
  readonly onDone: () => void;
  readonly onCancel: () => void;
}

export function CorrectVersionClassificationForm({
  address,
  review,
  current,
  onDone,
  onCancel,
}: CorrectVersionClassificationFormProps) {
  const [stage, setStage] = useState<ProjectStage | null>(current.project_stage);
  const [section, setSection] = useState<SectionCode | null>(current.section_code);
  const [reason, setReason] = useState('');
  const [flight] = useState(createSingleFlight);
  const mutation = useCorrectVersionClassification();

  const submit = () => {
    if (stage === null || section === null) return;
    flight.run(() =>
      mutation
        .mutateAsync({ ...address, stage, section, reason, expectedRevision: current.revision })
        .then(onDone, () => undefined),
    );
  };

  return (
    <CorrectVersionClassificationFormView
      review={review}
      current={current}
      stage={stage}
      section={section}
      reason={reason}
      pending={mutation.isPending}
      failure={mutation.error === null ? null : correctionFailure(mutation.error)}
      onStage={setStage}
      onSection={setSection}
      onReason={setReason}
      onSubmit={submit}
      onCancel={onCancel}
    />
  );
}
